"""Hierarchical Risk Parity (HRP) portfolio optimizer.

Wraps PyPortfolioOpt's HRP implementation with position-size constraints
from ``src.config``.
"""

from __future__ import annotations

import logging

import pandas as pd
from pypfopt import HRPOpt

from src.optimizer.constraints import prune_and_renormalize

logger = logging.getLogger(__name__)


def hrp_weights(
    train_prices: pd.DataFrame,
    risk_free_rate: float | None = None,
) -> pd.Series:
    """Compute HRP portfolio weights from training-window prices.

    Args:
        train_prices: Wide price DataFrame (DatetimeIndex × tickers) covering
            the training window only.
        risk_free_rate: Accepted for a uniform optimizer signature; unused
            (HRP has no return-estimate input).

    Returns:
        Series of portfolio weights indexed by ticker, summing to 1.0, each
        within the configured position bounds.
    """
    returns = train_prices.pct_change().dropna(how="all")

    # Drop tickers with insufficient data (>50% NaN)
    valid_cols = returns.columns[returns.notna().mean() > 0.5]
    if len(valid_cols) < 2:
        logger.warning("HRP: fewer than 2 valid tickers — returning equal weights.")
        n = len(train_prices.columns)
        w = pd.Series(1.0 / n, index=train_prices.columns)
        w.attrs["fallback"] = True
        return w

    returns = returns[valid_cols].dropna()

    opt = HRPOpt(returns)
    raw = opt.optimize()
    w = pd.Series(raw, dtype=float)

    # Enforce bounds. The previous clip-then-renormalise re-inflated capped
    # names above the cap; prune_and_renormalize redistributes excess so the
    # 15% cap actually holds.
    return prune_and_renormalize(w)
