"""SP-N Alpha strategy — AI/ML-optimised portfolio weights.

This module provides factory functions that return ``WeightsFn`` callables
compatible with :func:`src.backtest.engine.walk_forward_backtest`.

Phase 1 (classical): HRP, MVO max-Sharpe, MVO min-vol.
Phase 2 (ML): Ensemble with LightGBM factor model + HMM regime detection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from src.config import TOP_20_TICKERS
from src.features.factors import predict_forward_returns
from src.features.regime import detect_regime
from src.optimizer.ensemble import ensemble_weights
from src.optimizer.hrp import hrp_weights
from src.optimizer.mvo import mvo_max_sharpe_weights, mvo_min_vol_weights

if TYPE_CHECKING:
    from src.backtest.engine import WeightsFn

logger = logging.getLogger(__name__)

_OPTIMIZERS = {
    "hrp": hrp_weights,
    "mvo_sharpe": mvo_max_sharpe_weights,
    "mvo_minvol": mvo_min_vol_weights,
}


def make_alpha_weights_fn(
    optimizer: str = "hrp",
    universe: list[str] | None = None,
) -> WeightsFn:
    """Factory returning a weights_fn closure for walk-forward backtesting.

    Args:
        optimizer: One of ``"hrp"``, ``"mvo_sharpe"``, ``"mvo_minvol"``.
        universe: Tickers to include.  Defaults to :data:`TOP_20_TICKERS`.

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
    tickers = list(universe or TOP_20_TICKERS)

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        # Filter to our universe — ignore tickers not in the price data
        available = [t for t in tickers if t in train_prices.columns]
        if len(available) < 2:
            raise ValueError(
                f"Need ≥2 tickers in universe; only found {available} in price data."
            )

        filtered = train_prices[available]
        w = opt_fn(filtered)
        return w

    return weights_fn


def make_ml_alpha_weights_fn(
    market_indicators: pd.DataFrame,
    universe: list[str] | None = None,
    forward_days: int = 21,
) -> WeightsFn:
    """Factory returning a ML-ensemble weights_fn for walk-forward backtesting.

    Uses HMM regime detection + LightGBM factor model + regime-weighted
    ensemble of HRP and factor-MVO.

    Args:
        market_indicators: Full market indicators DataFrame (``vix``,
            ``risk_free``, ``treasury_10y``, ``date``).  Will be sliced
            to the training window inside the closure.
        universe: Tickers to include.  Defaults to :data:`TOP_20_TICKERS`.
        forward_days: LightGBM prediction horizon in trading days.

    Returns:
        A callable ``(train_prices, train_bench) -> pd.Series`` of weights.
    """
    tickers = list(universe or TOP_20_TICKERS)

    # Pre-process market indicators once
    mi = market_indicators.copy()
    if "date" in mi.columns:
        mi["date"] = pd.to_datetime(mi["date"])
        mi = mi.set_index("date")

    def weights_fn(
        train_prices: pd.DataFrame,
        train_bench: pd.Series | None,
    ) -> pd.Series:
        available = [t for t in tickers if t in train_prices.columns]
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
