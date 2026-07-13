"""Portfolio beta calculation.

Computes individual stock betas and weighted portfolio beta against a
benchmark index, using rolling OLS regression.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def compute_stock_betas(
    prices: pd.DataFrame,
    benchmark: pd.Series,
    window: int = 63,
) -> pd.DataFrame:
    """Compute rolling beta for each stock vs the benchmark.

    Args:
        prices: Wide price DataFrame (DatetimeIndex × tickers).
        benchmark: Benchmark price Series (e.g. S&P 500).
        window: Rolling window in trading days (default 63 ≈ 3 months).

    Returns:
        DataFrame of rolling betas (same shape as *prices*).
    """
    stock_returns = prices.pct_change()
    bench_returns = benchmark.pct_change()

    # Align indices
    common = stock_returns.index.intersection(bench_returns.index)
    stock_returns = stock_returns.loc[common]
    bench_returns = bench_returns.loc[common]

    bench_var = bench_returns.rolling(window).var()
    betas = pd.DataFrame(index=stock_returns.index, columns=stock_returns.columns, dtype=float)

    for ticker in stock_returns.columns:
        cov = stock_returns[ticker].rolling(window).cov(bench_returns)
        betas[ticker] = cov / bench_var.replace(0, float("nan"))

    return betas


def compute_portfolio_beta(
    prices: pd.DataFrame,
    benchmark: pd.Series,
    weights: pd.Series,
    window: int = 63,
) -> float:
    """Compute the weighted portfolio beta at the latest available date.

    Args:
        prices: Wide price DataFrame for the training window.
        benchmark: Benchmark price Series aligned to same dates.
        weights: Portfolio weights indexed by ticker.
        window: Rolling beta lookback (default 63 trading days).

    Returns:
        Scalar portfolio beta (weighted sum of individual betas).
    """
    betas = compute_stock_betas(prices, benchmark, window)

    # Use the latest row of betas
    latest = betas.iloc[-1]

    # Weighted sum — align weights to available betas
    aligned_w = weights.reindex(latest.index, fill_value=0.0)
    portfolio_beta = float((aligned_w * latest.fillna(1.0)).sum())

    return portfolio_beta
