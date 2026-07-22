"""Self-adjusting SP-N Alpha: dynamic N + weighting engine + risk overlay.

The strategy the project exists to build — it adapts *both* how many stocks
to hold (N, in [SPN_MIN_STOCKS, SPN_MAX_STOCKS]) and how to weight and
risk-scale them, to beat the S&P 500 net of costs with controlled risk.

Composed from three orthogonal, independently-testable pieces:

- **weighting engine** — how to weight a chosen set of names
  (equal / inverse-vol / momentum-tilt / MVO max-Sharpe / HRP).
- **N policy** — how many names to hold, as of each decision date
  (static / concentration-elbow / regime-conditional). Uses only trailing
  data, so it is point-in-time by construction.
- **risk overlay** — how much equity exposure to run, parking the rest in
  CASH (none / volatility-target / regime-gated volatility-target).

The walk-forward engine restricts each training slice to the cap-ranked
top-``SPN_MAX_STOCKS`` (via ``universe_fn``); columns arrive in
cap-descending order, so ``columns[:N]`` is the point-in-time top-N. Overlays
that hold CASH require the price panel passed to the engine to include a
``CASH`` column (see :func:`src.utils.helpers.add_cash_column`).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

import numpy as np
import pandas as pd

from src.config import (
    HMM_N_STATES,
    SPN_MAX_STOCKS,
    SPN_MIN_STOCKS,
    TRADING_DAYS_PER_YEAR,
)
from src.features.regime import BEAR, BULL, detect_regime
from src.optimizer.constraints import prune_and_renormalize
from src.optimizer.hrp import hrp_weights
from src.optimizer.mvo import mvo_max_sharpe_weights
from src.strategies.alpha import trailing_risk_free

if TYPE_CHECKING:
    from src.backtest.engine import WeightsFn

logger = logging.getLogger(__name__)

CASH = "CASH"

# ---------------------------------------------------------------------------
# Weighting engines: (prices_of_selected_names, risk_free_rate) -> weights
# ---------------------------------------------------------------------------


def _equal_engine(prices: pd.DataFrame, risk_free_rate: float | None = None) -> pd.Series:
    n = prices.shape[1]
    return pd.Series(1.0 / n, index=prices.columns)


def _inverse_vol_engine(
    prices: pd.DataFrame, risk_free_rate: float | None = None
) -> pd.Series:
    """Weights inversely proportional to trailing daily-return volatility."""
    vol = prices.pct_change().std()
    inv = 1.0 / vol.replace(0.0, np.nan)
    inv = inv.dropna()
    if inv.empty:
        return _equal_engine(prices)
    return prune_and_renormalize(inv / inv.sum())


def _momentum_tilt_engine(
    prices: pd.DataFrame, risk_free_rate: float | None = None
) -> pd.Series:
    """Equal base tilted by 12-1 momentum (skip the most recent month).

    Score = return from ~12 months ago to ~1 month ago. Tilt multiplies an
    equal base by ``1 + clip(score)`` so winners are overweighted and losers
    underweighted without going short; then bounds are enforced.
    """
    lookback = min(len(prices) - 1, 252)
    skip = 21
    if lookback <= skip + 5:
        return _equal_engine(prices)
    past = prices.iloc[-lookback]
    recent = prices.iloc[-skip]
    momentum = (recent / past - 1.0).clip(-0.5, 1.0)
    base = 1.0 / prices.shape[1]
    tilt = base * (1.0 + momentum)
    tilt = tilt.clip(lower=0.0)
    if tilt.sum() <= 0:
        return _equal_engine(prices)
    return prune_and_renormalize(tilt / tilt.sum())


ENGINES: dict[str, Callable[[pd.DataFrame, float | None], pd.Series]] = {
    "equal": _equal_engine,
    "inverse_vol": _inverse_vol_engine,
    "momentum_tilt": _momentum_tilt_engine,
    "mvo_sharpe": mvo_max_sharpe_weights,
    "hrp": hrp_weights,
}


# ---------------------------------------------------------------------------
# N policies: decide how many names to hold at a decision date
# ---------------------------------------------------------------------------

NPolicyFn = Callable[[pd.DataFrame, "pd.Series | None"], int]


def _clamp_n(n: int) -> int:
    return int(max(SPN_MIN_STOCKS, min(SPN_MAX_STOCKS, n)))


def make_static_n(n: int) -> NPolicyFn:
    """Fixed N regardless of conditions."""
    target = _clamp_n(n)

    def policy(train_prices: pd.DataFrame, train_bench: pd.Series | None) -> int:
        return int(min(target, train_prices.shape[1]))

    return policy


def make_elbow_n(
    marginal_threshold: float = 0.005,
    window: int = TRADING_DAYS_PER_YEAR,
) -> NPolicyFn:
    """Concentration-elbow N: smallest N whose marginal R² < threshold.

    Regresses trailing benchmark returns on the cumulative top-1..K stock
    returns (columns arrive cap-ranked) over the trailing ``window`` days and
    finds where adding the next stock stops explaining ≥ ``marginal_threshold``
    of variance — the empirical "elbow". Falls back to SPN_MAX when the
    benchmark is unavailable or the window is too short.
    """
    from sklearn.linear_model import LinearRegression

    def policy(train_prices: pd.DataFrame, train_bench: pd.Series | None) -> int:
        if train_bench is None:
            return _clamp_n(SPN_MAX_STOCKS)
        stock_ret = train_prices.pct_change().tail(window)
        bench_ret = train_bench.pct_change().reindex(stock_ret.index)
        aligned = pd.concat([stock_ret, bench_ret.rename("_bench")], axis=1).dropna()
        if len(aligned) < SPN_MIN_STOCKS + 5:
            return _clamp_n(SPN_MAX_STOCKS)
        y = aligned["_bench"].values
        cols = [c for c in train_prices.columns if c in aligned.columns]

        prev_r2 = 0.0
        chosen = SPN_MIN_STOCKS
        for n in range(1, min(len(cols), SPN_MAX_STOCKS) + 1):
            x = aligned[cols[:n]].values
            r2 = LinearRegression().fit(x, y).score(x, y)
            marginal = r2 - prev_r2
            prev_r2 = r2
            if n >= SPN_MIN_STOCKS and marginal < marginal_threshold:
                chosen = n
                break
            chosen = n
        return _clamp_n(chosen)

    return policy


def make_regime_n(
    market_indicators: pd.DataFrame,
    bull_n: int = SPN_MIN_STOCKS,
    transition_n: int = 20,
    bear_n: int = SPN_MAX_STOCKS,
) -> NPolicyFn:
    """Regime-conditional N: concentrate in calm regimes, diversify in stress.

    Fewer names when the HMM (refit on the trailing window) reads bull,
    more when it reads bear — diversification is protective when volatility
    and dispersion rise.
    """
    mi = market_indicators.copy()
    if "date" in mi.columns:
        mi["date"] = pd.to_datetime(mi["date"])
        mi = mi.set_index("date")
    by_regime = {BULL: bull_n, 1: transition_n, BEAR: bear_n}

    def policy(train_prices: pd.DataFrame, train_bench: pd.Series | None) -> int:
        as_of = train_prices.index.max()
        window = mi.loc[:as_of]
        if len(window) < 50:
            return _clamp_n(transition_n)
        regimes = detect_regime(window.reset_index(), n_states=HMM_N_STATES)
        current = int(regimes.iloc[-1]) if len(regimes) else BULL
        return _clamp_n(by_regime.get(current, transition_n))

    return policy


# ---------------------------------------------------------------------------
# Risk overlays: scale equity exposure, park remainder in CASH
# ---------------------------------------------------------------------------

OverlayFn = Callable[[pd.Series, pd.DataFrame, "pd.Series | None"], pd.Series]


def no_overlay() -> OverlayFn:
    def overlay(
        weights: pd.Series, train_prices: pd.DataFrame, train_bench: pd.Series | None
    ) -> pd.Series:
        return weights

    return overlay


def _scale_to_cash(weights: pd.Series, equity_fraction: float) -> pd.Series:
    """Scale equity weights to ``equity_fraction`` and hold the rest as CASH."""
    frac = float(min(1.0, max(0.0, equity_fraction)))
    scaled = weights * frac
    cash = 1.0 - frac
    if cash > 1e-9:
        scaled = pd.concat([scaled, pd.Series({CASH: cash})])
    return scaled


def make_vol_target(
    target_vol: float = 0.15,
    window: int = 63,
    regime_gated: bool = False,
    market_indicators: pd.DataFrame | None = None,
) -> OverlayFn:
    """Volatility-target overlay: scale exposure to a target annual vol.

    Realised portfolio vol over the trailing ``window`` is estimated from the
    base weights; equity exposure = min(1, target/realised), remainder CASH.
    With ``regime_gated`` the overlay only de-risks in transition/bear
    regimes (full exposure in bull), which avoids capping upside in calm
    markets while still cutting risk in stress.
    """
    mi = None
    if regime_gated and market_indicators is not None:
        mi = market_indicators.copy()
        if "date" in mi.columns:
            mi["date"] = pd.to_datetime(mi["date"])
            mi = mi.set_index("date")

    def overlay(
        weights: pd.Series, train_prices: pd.DataFrame, train_bench: pd.Series | None
    ) -> pd.Series:
        cols = [c for c in weights.index if c in train_prices.columns]
        rets = train_prices[cols].pct_change().tail(window)
        if len(rets) < 5:
            return weights
        port_ret = (rets * weights.reindex(cols).fillna(0.0)).sum(axis=1)
        realised = float(port_ret.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        if realised <= 0:
            return weights

        if regime_gated and mi is not None:
            as_of = train_prices.index.max()
            window_mi = mi.loc[:as_of]
            if len(window_mi) >= 50:
                regimes = detect_regime(window_mi.reset_index(), n_states=HMM_N_STATES)
                if len(regimes) and int(regimes.iloc[-1]) == BULL:
                    return weights  # full exposure in calm markets

        equity_fraction = target_vol / realised
        return _scale_to_cash(weights, equity_fraction)

    return overlay


# ---------------------------------------------------------------------------
# Factory: compose engine + N policy + overlay into a WeightsFn
# ---------------------------------------------------------------------------


def strategy_from_config(
    config: dict,
    market_indicators: pd.DataFrame | None = None,
) -> tuple[WeightsFn, bool]:
    """Reconstruct the frozen weights_fn from a race-winner config dict.

    Single source of truth for turning ``{engine, n_policy, overlay}`` (as
    written to ``data/research/race_result.json``) into a runnable strategy,
    shared by the holdout evaluation and the production export so they cannot
    drift apart.

    Args:
        config: Keys ``engine``, ``n_policy`` (static20|elbow|regime),
            ``overlay`` (none|voltgt15|voltgt_regime).
        market_indicators: Indicators frame for rf / regime / vol-target.

    Returns:
        ``(weights_fn, uses_cash)`` — ``uses_cash`` is True when the overlay
        can hold CASH, so the caller knows to pass a CASH-augmented panel.
    """
    n_name = config["n_policy"]
    if n_name == "static20":
        n_policy: NPolicyFn = make_static_n(20)
    elif n_name == "elbow":
        n_policy = make_elbow_n()
    elif n_name == "regime":
        n_policy = make_regime_n(market_indicators)
    else:
        raise ValueError(f"Unknown n_policy {n_name!r}.")

    o_name = config.get("overlay", "none")
    if o_name == "none":
        overlay: OverlayFn = no_overlay()
    elif o_name == "voltgt15":
        overlay = make_vol_target(0.15)
    elif o_name == "voltgt_regime":
        overlay = make_vol_target(0.15, regime_gated=True, market_indicators=market_indicators)
    else:
        raise ValueError(f"Unknown overlay {o_name!r}.")

    weights_fn = make_dynamic_alpha_weights_fn(
        config["engine"], n_policy, overlay=overlay, market_indicators=market_indicators
    )
    return weights_fn, o_name != "none"


def make_dynamic_alpha_weights_fn(
    engine: str,
    n_policy: NPolicyFn,
    overlay: OverlayFn | None = None,
    market_indicators: pd.DataFrame | None = None,
) -> WeightsFn:
    """Compose a self-adjusting SP-N Alpha weights function.

    Args:
        engine: Key into :data:`ENGINES`.
        n_policy: N-selection policy (see ``make_*_n``).
        overlay: Risk overlay (defaults to :func:`no_overlay`). Overlays that
            hold CASH require the engine's price panel to carry a CASH column.
        market_indicators: Indicators frame for the trailing risk-free rate
            fed to return-estimate engines (MVO). N-policy/overlay closures
            capture their own indicators if regime-aware.

    Returns:
        ``(train_prices, train_bench) -> weights`` for
        :func:`src.backtest.engine.walk_forward_backtest`.

    Raises:
        ValueError: If *engine* is unknown.
    """
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine {engine!r}. Choose from {list(ENGINES)}.")
    engine_fn = ENGINES[engine]
    overlay_fn = overlay or no_overlay()

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        # Columns arrive cap-ranked (top SPN_MAX from universe_fn); exclude
        # any CASH column from equity selection.
        equity = train_prices[[c for c in train_prices.columns if c != CASH]]
        if equity.shape[1] < SPN_MIN_STOCKS:
            raise ValueError(
                f"Need ≥{SPN_MIN_STOCKS} candidates; got {equity.shape[1]}."
            )

        n_t = n_policy(equity, train_bench)
        selected = list(equity.columns)[:n_t]

        rf = trailing_risk_free(market_indicators, equity.index.max())
        base = engine_fn(equity[selected], rf)
        base = base[base > 0].dropna()
        if base.empty:
            raise ValueError("Weighting engine produced no positive weights.")
        base = base / base.sum()

        return overlay_fn(base, equity, train_bench)

    return weights_fn
