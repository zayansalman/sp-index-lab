"""Archived hedged strategy prototype.

This module is kept for research experiments and unit coverage around cash
allocation logic. It is not part of the retained public strategy set and is
not exported to the frontend.

Defense triggers:
1. **Bear regime**: HMM detects bear → 20% cash.
2. **VIX spike**: VIX > 25 → 12% cash; VIX > 35 (panic) → 30% cash.
3. **Portfolio drawdown**: if recent drawdown > 10% → 8-20% cash.

Each trigger adds independently to the cash allocation (capped at 60%).
In calm bull markets → 0% cash, full MVO-Sharpe exposure.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.features.regime import BEAR, detect_regime
from src.optimizer.mvo import mvo_max_sharpe_weights

if TYPE_CHECKING:
    from src.backtest.engine import WeightsFn

logger = logging.getLogger(__name__)

# Thresholds
VIX_ELEVATED = 20.0
VIX_SPIKE = 25.0
VIX_PANIC = 35.0

# Maximum cash allocation (never go fully defensive — stay in the market)
MAX_CASH_WEIGHT = 0.60

# Drawdown lookback for the trailing-stop trigger
DD_LOOKBACK_DAYS = 60
DD_THRESHOLD = 0.08  # 8% drawdown over lookback → trim


def _compute_alpha_recent_drawdown(
    train_prices: pd.DataFrame,
    weights: pd.Series,
    lookback: int = DD_LOOKBACK_DAYS,
) -> float:
    """Estimate the alpha portfolio's recent max drawdown.

    Returns a non-negative float (0.0 if no drawdown).
    """
    if len(train_prices) < lookback + 1:
        return 0.0

    recent_prices = train_prices.iloc[-(lookback + 1):]
    returns = recent_prices.pct_change().dropna()

    # Align weights
    w = weights.reindex(recent_prices.columns, fill_value=0.0)
    portfolio_returns = (returns * w).sum(axis=1)

    nav = (1 + portfolio_returns).cumprod()
    if len(nav) == 0:
        return 0.0

    dd = (nav / nav.cummax() - 1).min()
    return abs(float(dd))


def _compute_cash_allocation(
    regime: int,
    current_vix: float,
    recent_drawdown: float,
) -> float:
    """Compute total cash allocation based on defense triggers.

    Archived experiment tuned to keep drawdown materially below the index.
    Transition-regime cash is removed (let alpha work) and VIX-elevated
    threshold is raised so we only hedge when markets are genuinely stressed.
    """
    cash = 0.0

    # Trigger 1: Only hedge in confirmed bear regime.  Transition is too
    # noisy — the ensemble optimizer already leans toward HRP there, so
    # extra cash is pure drag.
    if regime == BEAR:
        cash += 0.20

    # Trigger 2: VIX-based defense — only on real stress, not routine dips
    if current_vix >= VIX_PANIC:
        cash += 0.30  # panic mode
    elif current_vix >= VIX_SPIKE:
        cash += 0.12
    # VIX_ELEVATED (20-25) no longer triggers cash — too common, drags CAGR

    # Trigger 3: Alpha portfolio drawdown (trailing stop).  Kick in only
    # after a genuine 10% drawdown; scale up from there.
    dd_threshold = 0.10  # raised from 8% to avoid false triggers
    if recent_drawdown >= dd_threshold:
        cash += min(0.20, (recent_drawdown - dd_threshold) * 2.0 + 0.08)

    return min(cash, MAX_CASH_WEIGHT)


def make_hedged_weights_fn(
    market_indicators: pd.DataFrame,
    benchmark_prices: pd.Series | None = None,
    universe: list[str] | None = None,
) -> WeightsFn:
    """Factory returning a hedged weights_fn for walk-forward backtesting.

    Args:
        market_indicators: Full market indicators DataFrame (``vix``,
            ``risk_free``, ``treasury_10y``, ``date``).
        benchmark_prices: Kept for API compatibility; unused in the new design.
        universe: Optional explicit ticker list. Defaults to every column
            passed in (excluding CASH) — the engine's ``universe_fn``
            owns selection.

    Returns:
        A callable ``(train_prices, train_bench) -> pd.Series`` of weights
        including a ``CASH`` allocation.
    """
    # Pre-process market indicators
    mi = market_indicators.copy()
    if "date" in mi.columns:
        mi["date"] = pd.to_datetime(mi["date"])
        mi = mi.set_index("date")

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        # Filter to equity tickers (exclude CASH from optimization)
        candidates = (
            [t for t in universe if t in train_prices.columns]
            if universe is not None
            else list(train_prices.columns)
        )
        equity_tickers = [t for t in candidates if t != "CASH"]
        if len(equity_tickers) < 2:
            raise ValueError(
                f"Need ≥2 equity tickers; only found {equity_tickers}."
            )

        equity_prices = train_prices[equity_tickers]

        # --- 1. Detect regime ---
        train_mi = mi.loc[equity_prices.index.min():equity_prices.index.max()]
        regimes = detect_regime(
            train_mi.reset_index().rename(columns={train_mi.index.name or "index": "date"}),
        )
        current_regime = int(regimes.iloc[-1]) if len(regimes) > 0 else 0
        current_vix = float(train_mi["vix"].iloc[-1]) if len(train_mi) > 0 else 15.0

        # --- 2. MVO max-Sharpe weights (the highest-return base) ---
        alpha_w = mvo_max_sharpe_weights(equity_prices)

        # --- 3. Compute alpha's recent drawdown (used as a defense trigger) ---
        recent_dd = _compute_alpha_recent_drawdown(equity_prices, alpha_w)

        # --- 4. Determine cash allocation from all triggers ---
        cash_weight = _compute_cash_allocation(current_regime, current_vix, recent_dd)
        equity_weight = 1.0 - cash_weight

        # --- 5. Scale alpha weights by the equity fraction ---
        scaled_equity = alpha_w * equity_weight

        # --- 6. Construct final weight vector including CASH ---
        full_weights = scaled_equity.copy()
        if "CASH" in train_prices.columns:
            full_weights["CASH"] = cash_weight

        # Ensure exact normalisation
        total = full_weights.sum()
        if total > 0:
            full_weights = full_weights / total

        logger.info(
            "Hedged: regime=%d, VIX=%.1f, alpha_dd=%.1f%%, equity=%.0f%%, cash=%.0f%%",
            current_regime,
            current_vix,
            recent_dd * 100,
            equity_weight * 100,
            cash_weight * 100,
        )

        return full_weights

    return weights_fn
