"""Concentration proof analytics — the statistical backbone.

Proves that the S&P 500 is effectively a ~20-stock index:
- Variance decomposition: how much of S&P variance is explained by top N
- R² analysis: rolling and cumulative R² of top-N vs full index
- Concentration curve: cumulative weight vs cumulative variance explained
- Tracking error: top-N mirror vs S&P 500
"""

import logging

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.backtest.metrics import (
    compute_performance_metrics as _compute_performance_metrics,
    compute_tracking_error as _compute_tracking_error,
)

logger = logging.getLogger(__name__)


def compute_market_cap_weights(prices: pd.DataFrame) -> pd.DataFrame:
    """Approximate market-cap weights from price levels.

    In absence of real shares outstanding, we use price as a proxy
    (valid for relative ranking within our universe). For the actual
    S&P 500 weights, we'd need market cap data, but this captures
    the concentration structure.

    Args:
        prices: Wide-format daily prices (DatetimeIndex × tickers).

    Returns:
        DataFrame of normalized weights (rows sum to 1.0).
    """
    weights = prices.div(prices.sum(axis=1), axis=0)
    return weights


def variance_decomposition(
    stock_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
    top_n_values: list[int] | None = None,
) -> pd.DataFrame:
    """Compute R² of top-N stocks explaining benchmark variance.

    For each N in top_n_values, fits a linear regression of the benchmark
    returns on the top-N stock returns (by average weight) and records R².

    Args:
        stock_returns: Daily returns for each stock.
        benchmark_returns: Daily returns for the benchmark (S&P 500).
        top_n_values: List of N values to test. Defaults to [5, 10, 15, 20, 25, 30, 40, 50].

    Returns:
        DataFrame with columns: n_stocks, r_squared, adj_r_squared.
    """
    if top_n_values is None:
        top_n_values = [5, 10, 15, 20, 25, 30, 40, 50]

    # Rank stocks by average return magnitude as proxy for importance
    avg_abs_return = stock_returns.abs().mean().sort_values(ascending=False)
    ranked_tickers = avg_abs_return.index.tolist()

    # Align data
    common_idx = stock_returns.index.intersection(benchmark_returns.index)
    X_all = stock_returns.loc[common_idx]
    y = benchmark_returns.loc[common_idx].values

    results = []
    for n in top_n_values:
        if n > len(ranked_tickers):
            continue
        top_n_tickers = ranked_tickers[:n]
        X = X_all[top_n_tickers].values
        mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
        X_clean, y_clean = X[mask], y[mask]

        if len(y_clean) < n + 1:
            continue

        model = LinearRegression().fit(X_clean, y_clean)
        r2 = model.score(X_clean, y_clean)
        adj_r2 = 1 - (1 - r2) * (len(y_clean) - 1) / (len(y_clean) - n - 1)

        results.append({"n_stocks": n, "r_squared": r2, "adj_r_squared": adj_r2})

    return pd.DataFrame(results)


def concentration_curve(
    stock_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
) -> pd.DataFrame:
    """Build the concentration curve: cumulative R² as stocks are added.

    Adds one stock at a time (ranked by contribution) and tracks
    cumulative R² — showing diminishing marginal contribution.

    Args:
        stock_returns: Daily returns for each stock.
        benchmark_returns: Daily returns for the benchmark.

    Returns:
        DataFrame with columns: n_stocks, r_squared, marginal_r_squared.
    """
    common_idx = stock_returns.index.intersection(benchmark_returns.index)
    X_all = stock_returns.loc[common_idx]
    y = benchmark_returns.loc[common_idx].values
    mask = ~np.isnan(y)

    # Rank by correlation with benchmark
    correlations = X_all.corrwith(benchmark_returns.loc[common_idx]).abs()
    ranked = correlations.sort_values(ascending=False).index.tolist()

    results = []
    prev_r2 = 0.0
    for i, ticker in enumerate(ranked, 1):
        top_tickers = ranked[:i]
        X = X_all[top_tickers].values
        row_mask = mask & ~np.isnan(X).any(axis=1)
        X_clean, y_clean = X[row_mask], y[row_mask]

        if len(y_clean) < i + 1:
            break

        model = LinearRegression().fit(X_clean, y_clean)
        r2 = model.score(X_clean, y_clean)
        marginal = r2 - prev_r2

        results.append({
            "n_stocks": i,
            "ticker_added": ticker,
            "r_squared": r2,
            "marginal_r_squared": marginal,
        })
        prev_r2 = r2

        if i >= 50:  # Cap at 50 for performance
            break

    return pd.DataFrame(results)


def build_mirror_index(
    stock_prices: pd.DataFrame,
    top_n: int = 20,
    weighting: str = "cap",
) -> pd.DataFrame:
    """Build a mirror index from the top-N stocks.

    Args:
        stock_prices: Wide-format daily prices.
        top_n: Number of top stocks to include.
        weighting: "cap" for cap-weighted, "equal" for equal-weighted.

    Returns:
        DataFrame with columns: date, nav, daily_return, index_name.
    """
    returns = stock_prices.pct_change(fill_method=None).dropna(how="all")

    # Rank by average price level (proxy for market cap)
    avg_price = stock_prices.mean()
    top_tickers = avg_price.nlargest(top_n).index.tolist()
    top_returns = returns[top_tickers]

    if weighting == "equal":
        portfolio_returns = top_returns.mean(axis=1)
        index_name = f"sp{top_n}_equal"
    elif weighting == "cap":
        # Cap-weighted: use price-proportional weights, rebalanced daily
        weights = stock_prices[top_tickers].div(
            stock_prices[top_tickers].sum(axis=1), axis=0
        )
        # Shift weights by 1 day (use yesterday's weights for today's return)
        weights = weights.shift(1).dropna(how="all")
        aligned = top_returns.loc[weights.index]
        portfolio_returns = (aligned * weights).sum(axis=1)
        index_name = f"sp{top_n}_mirror"
    else:
        raise ValueError(f"Unknown weighting: {weighting}")

    # Build NAV (normalised to 1.0 at inception)
    nav = (1 + portfolio_returns).cumprod()
    nav = nav / nav.iloc[0]  # Normalize to 1.0

    result = pd.DataFrame({
        "date": nav.index,
        "nav": nav.values,
        "daily_return": portfolio_returns.values,
        "index_name": index_name,
    })

    return result


def compute_tracking_error(
    index_returns: pd.Series,
    benchmark_returns: pd.Series,
    annualize: bool = True,
) -> float:
    """Compatibility wrapper for tracking error metrics utility."""
    return _compute_tracking_error(
        index_returns=index_returns,
        benchmark_returns=benchmark_returns,
        annualize=annualize,
    )


def compute_performance_metrics(
    nav: pd.Series,
    benchmark_nav: pd.Series | None = None,
    risk_free_rate: float = 0.04,
) -> dict:
    """Compatibility wrapper for shared backtest performance metrics."""
    return _compute_performance_metrics(
        nav=nav,
        benchmark_nav=benchmark_nav,
        risk_free_rate=risk_free_rate,
    )


