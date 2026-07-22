"""Mean-Variance Optimization (MVO) portfolio optimizer.

Wraps PyPortfolioOpt's Efficient Frontier with covariance shrinkage and
position-size constraints.  Falls back to equal weights when the optimizer
fails (MVO is notoriously sensitive to return estimates).
"""

from __future__ import annotations

import logging

import pandas as pd
from pypfopt import EfficientFrontier, expected_returns, risk_models

from src.config import MAX_POSITION_WEIGHT
from src.optimizer.constraints import prune_and_renormalize

logger = logging.getLogger(__name__)

__all__ = [
    "mvo_max_sharpe_weights",
    "mvo_min_vol_weights",
    "prune_and_renormalize",
]

DEFAULT_RISK_FREE_RATE = 0.04


def _equal_weights(tickers: list[str]) -> pd.Series:
    """Fallback: uniform weights across all tickers, flagged via attrs."""
    n = len(tickers)
    w = pd.Series(1.0 / n, index=tickers)
    w.attrs["fallback"] = True
    return w


def _run_mvo(
    train_prices: pd.DataFrame,
    objective: str,
    risk_free_rate: float | None = None,
) -> pd.Series:
    """Run MVO with the given objective, returning cleaned weights.

    Args:
        train_prices: Wide price DataFrame for the training window.
        objective: ``"max_sharpe"`` or ``"min_volatility"``.
        risk_free_rate: Annualised risk-free rate for the max-Sharpe
            objective. ``None`` falls back to ``DEFAULT_RISK_FREE_RATE``
            (callers should pass the trailing T-bill rate instead).

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0. On solver
        failure returns equal weights with ``attrs["fallback"] = True`` so
        the backtest engine can surface the fallback rate.
    """
    tickers = train_prices.columns.tolist()
    if risk_free_rate is None:
        logger.debug(
            "No risk_free_rate provided — using default %.2f%%.",
            DEFAULT_RISK_FREE_RATE * 100,
        )
        risk_free_rate = DEFAULT_RISK_FREE_RATE

    # Names without enough history in the window (recent IPOs / new index
    # members) would NaN-poison the covariance and silently trigger the
    # equal-weight fallback for the whole window — drop them instead.
    coverage = train_prices.notna().mean()
    usable = coverage[coverage >= 0.6].index.tolist()
    if len(usable) >= 2:
        train_prices = train_prices[usable].dropna()

    try:
        mu = expected_returns.mean_historical_return(train_prices)
        cov = risk_models.CovarianceShrinkage(train_prices).ledoit_wolf()

        # Lower bound 0 (not MIN_POSITION_WEIGHT): the optimizer must be
        # able to exit a name entirely. Dust positions are pruned after.
        ef = EfficientFrontier(
            mu,
            cov,
            weight_bounds=(0.0, MAX_POSITION_WEIGHT),
        )

        if objective == "max_sharpe":
            ef.max_sharpe(risk_free_rate=risk_free_rate)
        else:
            ef.min_volatility()

        w = pd.Series(ef.clean_weights(), dtype=float)
        return prune_and_renormalize(w)

    except Exception:
        logger.warning(
            "MVO (%s) failed — falling back to equal weights.",
            objective,
            exc_info=True,
        )
        return _equal_weights(tickers)


def mvo_max_sharpe_weights(
    train_prices: pd.DataFrame,
    risk_free_rate: float | None = None,
) -> pd.Series:
    """MVO weights maximising the Sharpe ratio.

    Args:
        train_prices: Wide price DataFrame for the training window.
        risk_free_rate: Annualised risk-free rate; pass the trailing T-bill
            rate at the decision date. ``None`` uses the documented default.

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0.
    """
    return _run_mvo(train_prices, "max_sharpe", risk_free_rate=risk_free_rate)


def mvo_min_vol_weights(
    train_prices: pd.DataFrame,
    risk_free_rate: float | None = None,
) -> pd.Series:
    """MVO weights minimising portfolio volatility.

    Args:
        train_prices: Wide price DataFrame for the training window.
        risk_free_rate: Accepted for interface uniformity; unused.

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0.
    """
    return _run_mvo(train_prices, "min_volatility")
