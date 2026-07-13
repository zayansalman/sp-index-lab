"""Hierarchical Risk Parity (HRP) portfolio optimizer.

Wraps PyPortfolioOpt's HRP implementation with position-size constraints
from ``src.config``.
"""

from __future__ import annotations

import logging

import pandas as pd
from pypfopt import HRPOpt

from src.config import MAX_POSITION_WEIGHT, MIN_POSITION_WEIGHT

logger = logging.getLogger(__name__)


def _clip_and_renormalise(
    weights: pd.Series,
    max_w: float = MAX_POSITION_WEIGHT,
    min_w: float = MIN_POSITION_WEIGHT,
) -> pd.Series:
    """Clip weights to [min_w, max_w] and renormalise to sum to 1."""
    w = weights.clip(lower=min_w, upper=max_w)
    return w / w.sum()


def hrp_weights(train_prices: pd.DataFrame) -> pd.Series:
    """Compute HRP portfolio weights from training-window prices.

    Args:
        train_prices: Wide price DataFrame (DatetimeIndex × tickers) covering
            the training window only.

    Returns:
        Series of portfolio weights indexed by ticker, summing to 1.0.
    """
    returns = train_prices.pct_change().dropna(how="all")

    # Drop tickers with insufficient data (>50% NaN)
    valid_cols = returns.columns[returns.notna().mean() > 0.5]
    if len(valid_cols) < 2:
        logger.warning("HRP: fewer than 2 valid tickers — returning equal weights.")
        n = len(train_prices.columns)
        return pd.Series(1.0 / n, index=train_prices.columns)

    returns = returns[valid_cols].dropna()

    opt = HRPOpt(returns)
    raw = opt.optimize()
    w = pd.Series(raw, dtype=float)

    # Re-index to full ticker list (zero weight for dropped tickers)
    w = w.reindex(train_prices.columns, fill_value=0.0)

    # Only constrain tickers that received weight
    active = w > 0
    if active.sum() >= 2:
        w[active] = _clip_and_renormalise(w[active])
        # Ensure inactive remain zero, then renormalise active
        w[~active] = 0.0
        if w.sum() > 0:
            w = w / w.sum()

    return w
