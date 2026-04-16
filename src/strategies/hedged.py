"""SP-N Hedged strategy — market-neutral portfolio aiming for all-weather returns.

Uses three mechanisms to reduce market exposure:
1. **Dynamic beta targeting**: Scale equity weights to achieve a target beta
   that varies by regime (lower in bear markets).
2. **Regime-driven cash allocation**: Reduce total equity exposure in
   bear/transition regimes, parking the remainder in cash (risk-free).
3. **Defensive tilt**: In bear regimes, overweight historically low-beta
   stocks and underweight high-beta stocks.

The CASH pseudo-ticker (from ``src.utils.helpers.add_cash_column``) lets
this strategy work with the walk-forward engine's weight normalisation
(weights always sum to 1.0, but some weight goes to CASH).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.config import TOP_20_TICKERS
from src.features.beta import compute_portfolio_beta, compute_stock_betas
from src.features.factors import predict_forward_returns
from src.features.regime import detect_regime
from src.optimizer.ensemble import ensemble_weights

if TYPE_CHECKING:
    from src.backtest.engine import WeightsFn

logger = logging.getLogger(__name__)

# Target beta by regime: lower beta = more hedged
HEDGED_TARGET_BETA: dict[int, float] = {
    0: 0.5,    # Bull  — moderate exposure
    1: 0.25,   # Transition — cautious
    2: 0.05,   # Bear  — near-zero market exposure
}

# Max equity allocation by regime (rest goes to CASH)
HEDGED_EQUITY_ALLOCATION: dict[int, float] = {
    0: 0.90,   # Bull  — 90% invested
    1: 0.60,   # Transition — 60% invested
    2: 0.30,   # Bear  — 30% invested (very defensive)
}

# Known low-beta defensive stocks in the top-20 universe
DEFENSIVE_TICKERS = {"XOM", "JNJ", "PG", "WMT", "COST", "HD", "V", "MA"}


def _apply_defensive_tilt(
    weights: pd.Series,
    stock_betas: pd.Series,
    regime: int,
    tilt_strength: float = 0.3,
) -> pd.Series:
    """Tilt weights toward low-beta stocks in bear/transition regimes.

    In bull regime, no tilt is applied.  In bear, stocks with below-median
    beta get their weight boosted; stocks with above-median beta get reduced.

    Args:
        weights: Starting weights indexed by ticker.
        stock_betas: Latest rolling beta per ticker.
        regime: Current regime (0=bull, 1=transition, 2=bear).
        tilt_strength: How aggressively to tilt (0=none, 1=full).

    Returns:
        Tilted weights (still summing to 1.0 among equity tickers).
    """
    if regime == 0:
        return weights

    # Scale tilt by regime severity
    scale = tilt_strength if regime == 2 else tilt_strength * 0.5

    active = weights[weights > 0].copy()
    if len(active) < 2:
        return weights

    # Get betas for active tickers
    betas = stock_betas.reindex(active.index, fill_value=1.0)
    median_beta = betas.median()

    # Tilt: reduce high-beta, boost low-beta
    adjustment = 1.0 - scale * (betas - median_beta) / max(betas.std(), 0.01)
    adjustment = adjustment.clip(lower=0.3)  # Never reduce below 30% of original

    tilted = active * adjustment
    tilted = tilted / tilted.sum()  # Renormalise

    result = weights.copy()
    result[tilted.index] = tilted
    return result


def make_hedged_weights_fn(
    market_indicators: pd.DataFrame,
    benchmark_prices: pd.Series | None = None,
    universe: list[str] | None = None,
) -> WeightsFn:
    """Factory returning a hedged weights_fn for walk-forward backtesting.

    The hedged strategy:
    1. Computes ensemble alpha weights (same as SP-N Alpha)
    2. Detects current regime
    3. Applies defensive tilt in bear/transition
    4. Scales equity exposure by regime
    5. Allocates remaining weight to CASH

    Args:
        market_indicators: Full market indicators DataFrame.
        benchmark_prices: Benchmark price Series (for beta calculation).
        universe: Tickers to include.  Defaults to :data:`TOP_20_TICKERS`.

    Returns:
        A callable ``(train_prices, train_bench) -> pd.Series`` of weights.
        The returned weights include a ``CASH`` ticker.
    """
    tickers = list(universe or TOP_20_TICKERS)

    # Pre-process market indicators
    mi = market_indicators.copy()
    if "date" in mi.columns:
        mi["date"] = pd.to_datetime(mi["date"])
        mi = mi.set_index("date")

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        # Filter to available tickers (excluding CASH for now)
        equity_tickers = [t for t in tickers if t in train_prices.columns and t != "CASH"]
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

        # --- 2. Get base alpha weights from ensemble ---
        predicted = predict_forward_returns(equity_prices)
        alpha_w = ensemble_weights(equity_prices, current_regime, predicted)

        # --- 3. Apply defensive tilt in bear/transition ---
        if train_bench is not None and current_regime > 0:
            betas_df = compute_stock_betas(equity_prices, train_bench, window=63)
            latest_betas = betas_df.iloc[-1].fillna(1.0)
            alpha_w = _apply_defensive_tilt(alpha_w, latest_betas, current_regime)

        # --- 4. Scale equity exposure by regime ---
        max_equity = HEDGED_EQUITY_ALLOCATION.get(current_regime, 0.6)

        # Also scale by target beta if benchmark available
        if train_bench is not None:
            current_beta = compute_portfolio_beta(
                equity_prices, train_bench, alpha_w, window=63,
            )
            target_beta = HEDGED_TARGET_BETA.get(current_regime, 0.3)

            if current_beta > 0:
                beta_scale = min(target_beta / current_beta, 1.0)
            else:
                beta_scale = 1.0

            # Use the more conservative of beta-scaling and regime allocation
            equity_fraction = min(max_equity, beta_scale)
        else:
            equity_fraction = max_equity

        # --- 5. Construct final weights with CASH ---
        equity_w = alpha_w * equity_fraction
        cash_weight = 1.0 - equity_w.sum()

        # Build full weight vector including CASH
        full_weights = equity_w.copy()
        if "CASH" in train_prices.columns:
            full_weights["CASH"] = max(cash_weight, 0.0)
        else:
            # If no CASH column, just return scaled equity weights
            # (the engine will renormalise to 1.0)
            pass

        # Renormalise to exactly 1.0
        total = full_weights.sum()
        if total > 0:
            full_weights = full_weights / total

        logger.info(
            "Hedged: regime=%d, equity=%.0f%%, cash=%.0f%%, beta_target=%.2f",
            current_regime,
            equity_fraction * 100,
            (1 - equity_fraction) * 100,
            HEDGED_TARGET_BETA.get(current_regime, 0.3),
        )

        return full_weights

    return weights_fn
