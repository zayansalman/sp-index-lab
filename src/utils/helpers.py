"""Shared utility functions for SP Index Lab."""

from __future__ import annotations

import pandas as pd


def add_cash_column(
    prices: pd.DataFrame,
    risk_free_rate: float = 0.04,
) -> pd.DataFrame:
    """Add a synthetic CASH column that earns the daily risk-free rate.

    This allows the walk-forward engine (which normalises weights to sum
    to 1.0) to handle partial equity allocation: the hedged strategy
    assigns weight to CASH, and the engine treats it like any ticker.

    Args:
        prices: Wide price DataFrame (DatetimeIndex × tickers).
        risk_free_rate: Annual risk-free rate (default 4%).

    Returns:
        Copy of *prices* with an additional ``CASH`` column.
    """
    daily_rf = (1 + risk_free_rate) ** (1 / 252) - 1

    # Build a compounding cash price series starting at 100
    n = len(prices)
    cash_values = [100.0]
    for _ in range(n - 1):
        cash_values.append(cash_values[-1] * (1 + daily_rf))

    result = prices.copy()
    result["CASH"] = cash_values
    return result
