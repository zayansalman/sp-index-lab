"""Mean-Variance Optimization (MVO) portfolio optimizer.

Wraps PyPortfolioOpt's Efficient Frontier with covariance shrinkage and
position-size constraints.  Falls back to equal weights when the optimizer
fails (MVO is notoriously sensitive to return estimates).
"""

from __future__ import annotations

import logging

import pandas as pd
from pypfopt import EfficientFrontier, expected_returns, risk_models

from src.config import MAX_POSITION_WEIGHT, MIN_POSITION_WEIGHT

logger = logging.getLogger(__name__)


def _equal_weights(tickers: list[str]) -> pd.Series:
    """Fallback: uniform weights across all tickers."""
    n = len(tickers)
    return pd.Series(1.0 / n, index=tickers)


def _run_mvo(
    train_prices: pd.DataFrame,
    objective: str,
) -> pd.Series:
    """Run MVO with the given objective, returning cleaned weights.

    Args:
        train_prices: Wide price DataFrame for the training window.
        objective: ``"max_sharpe"`` or ``"min_volatility"``.

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0.
    """
    tickers = train_prices.columns.tolist()

    try:
        mu = expected_returns.mean_historical_return(train_prices)
        cov = risk_models.CovarianceShrinkage(train_prices).ledoit_wolf()

        ef = EfficientFrontier(
            mu,
            cov,
            weight_bounds=(MIN_POSITION_WEIGHT, MAX_POSITION_WEIGHT),
        )

        if objective == "max_sharpe":
            ef.max_sharpe(risk_free_rate=0.04)
        else:
            ef.min_volatility()

        raw = ef.clean_weights()
        w = pd.Series(raw, dtype=float)
        total = w.sum()
        if total > 0:
            w = w / total
        return w

    except Exception:
        logger.warning(
            "MVO (%s) failed — falling back to equal weights.",
            objective,
            exc_info=True,
        )
        return _equal_weights(tickers)


def mvo_max_sharpe_weights(train_prices: pd.DataFrame) -> pd.Series:
    """MVO weights maximising the Sharpe ratio.

    Args:
        train_prices: Wide price DataFrame for the training window.

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0.
    """
    return _run_mvo(train_prices, "max_sharpe")


def mvo_min_vol_weights(train_prices: pd.DataFrame) -> pd.Series:
    """MVO weights minimising portfolio volatility.

    Args:
        train_prices: Wide price DataFrame for the training window.

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0.
    """
    return _run_mvo(train_prices, "min_volatility")
