"""SP-N Alpha strategy factories.

This module provides factory functions that return ``WeightsFn`` callables
compatible with :func:`src.backtest.engine.walk_forward_backtest`.

The public SP-N Alpha export uses ``make_alpha_weights_fn("mvo_sharpe")``.
The ML ensemble factory remains available for research runs, but it is not
part of the retained frontend strategy set.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.features.factors import predict_forward_returns
from src.features.regime import detect_regime
from src.optimizer.ensemble import ensemble_weights
from src.optimizer.hrp import hrp_weights
from src.optimizer.mvo import mvo_max_sharpe_weights, mvo_min_vol_weights

if TYPE_CHECKING:
    from src.backtest.engine import WeightsFn

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

    OptimizerFn = Callable[[pd.DataFrame, float | None], pd.Series]

# All optimizers share the signature (train_prices, risk_free_rate=None);
# HRP/min-vol ignore the rate. Uniform signature keeps dispatch type-safe.
_OPTIMIZERS: dict[str, OptimizerFn] = {
    "hrp": hrp_weights,
    "mvo_sharpe": mvo_max_sharpe_weights,
    "mvo_minvol": mvo_min_vol_weights,
}


def trailing_risk_free(
    market_indicators: pd.DataFrame | None,
    as_of: pd.Timestamp,
    window: int = 21,
) -> float | None:
    """Trailing mean annualised risk-free rate as of a date.

    Args:
        market_indicators: DataFrame with ``date`` and ``risk_free`` columns
            (^IRX yield in percent, e.g. 3.66 = 3.66%). ``None`` → ``None``.
        as_of: Decision date; only rows on or before it are used.
        window: Trailing rows to average.

    Returns:
        Annualised rate as a decimal (0.0366), or ``None`` when unavailable.
    """
    if market_indicators is None or "risk_free" not in market_indicators.columns:
        return None
    mi = market_indicators
    dates = pd.to_datetime(mi["date"]) if "date" in mi.columns else mi.index
    values = mi["risk_free"].loc[pd.Series(dates).values <= pd.Timestamp(as_of)]
    if values.empty:
        return None
    return float(values.tail(window).mean()) / 100.0


def make_alpha_weights_fn(
    optimizer: str = "hrp",
    universe: list[str] | None = None,
    market_indicators: pd.DataFrame | None = None,
) -> WeightsFn:
    """Factory returning a weights_fn closure for walk-forward backtesting.

    Args:
        optimizer: One of ``"hrp"``, ``"mvo_sharpe"``, ``"mvo_minvol"``.
        universe: Optional explicit ticker list. Defaults to every column
            passed in — the engine's ``universe_fn`` owns selection
            (point-in-time top-N).
        market_indicators: Optional indicators frame (``date``,
            ``risk_free`` in percent). When provided, the trailing T-bill
            rate at each training window's end feeds the max-Sharpe
            objective instead of the hardcoded default.

    Returns:
        A callable ``(train_prices, train_bench) -> pd.Series`` of weights.

    Raises:
        ValueError: If *optimizer* is not recognised.
    """
    if optimizer not in _OPTIMIZERS:
        raise ValueError(
            f"Unknown optimizer {optimizer!r}. Choose from {list(_OPTIMIZERS)}."
        )

    opt_fn = _OPTIMIZERS[optimizer]

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        available = (
            [t for t in universe if t in train_prices.columns]
            if universe is not None
            else list(train_prices.columns)
        )
        if len(available) < 2:
            raise ValueError(
                f"Need ≥2 tickers in universe; only found {available} in price data."
            )

        filtered = train_prices[available]
        rf = trailing_risk_free(market_indicators, filtered.index.max())
        return opt_fn(filtered, rf)

    return weights_fn


def make_ml_alpha_weights_fn(
    market_indicators: pd.DataFrame,
    universe: list[str] | None = None,
    forward_days: int = 21,
) -> WeightsFn:
    """Factory returning a research-only ML-ensemble weights_fn.

    Uses HMM regime detection + LightGBM factor model + regime-weighted
    ensemble of HRP and factor-MVO.

    Args:
        market_indicators: Full market indicators DataFrame (``vix``,
            ``risk_free``, ``treasury_10y``, ``date``).  Will be sliced
            to the training window inside the closure.
        universe: Optional explicit ticker list. Defaults to every column
            passed in — the engine's ``universe_fn`` owns selection.
        forward_days: LightGBM prediction horizon in trading days.

    Returns:
        A callable ``(train_prices, train_bench) -> pd.Series`` of weights.
    """
    # Pre-process market indicators once
    mi = market_indicators.copy()
    if "date" in mi.columns:
        mi["date"] = pd.to_datetime(mi["date"])
        mi = mi.set_index("date")

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        available = (
            [t for t in universe if t in train_prices.columns]
            if universe is not None
            else list(train_prices.columns)
        )
        if len(available) < 2:
            raise ValueError(
                f"Need ≥2 tickers in universe; only found {available} in price data."
            )

        filtered = train_prices[available]

        # Slice market indicators to the training window
        train_mi = mi.loc[filtered.index.min():filtered.index.max()]

        # 1. Detect regime on training-window indicators
        regimes = detect_regime(
            train_mi.reset_index().rename(columns={train_mi.index.name or "index": "date"}),
        )
        current_regime = int(regimes.iloc[-1]) if len(regimes) > 0 else 0

        # 2. Predict forward returns via LightGBM
        predicted = predict_forward_returns(filtered, forward_days=forward_days)

        # 3. Ensemble: regime-weighted blend of factor-MVO + HRP
        w = ensemble_weights(filtered, current_regime, predicted)

        return w

    return weights_fn
