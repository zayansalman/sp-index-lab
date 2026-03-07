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

from src.config import TRADING_DAYS_PER_YEAR

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
    """Compute annualized tracking error between an index and benchmark.

    Args:
        index_returns: Daily returns of the constructed index.
        benchmark_returns: Daily returns of the benchmark.
        annualize: Whether to annualize (default True).

    Returns:
        Tracking error (annualized standard deviation of return difference).
    """
    common = index_returns.index.intersection(benchmark_returns.index)
    diff = index_returns.loc[common] - benchmark_returns.loc[common]
    te = diff.std()
    if annualize:
        te *= np.sqrt(TRADING_DAYS_PER_YEAR)
    return float(te)


def compute_performance_metrics(
    nav: pd.Series,
    benchmark_nav: pd.Series | None = None,
    risk_free_rate: float = 0.04,
) -> dict:
    """Compute comprehensive performance metrics for a NAV series.

    Args:
        nav: NAV series (normalised, starting at 1.0).
        benchmark_nav: Optional benchmark NAV for relative metrics.
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino.

    Returns:
        Dict of metric_name → value.
    """
    returns = nav.pct_change().dropna()
    n_years = len(returns) / TRADING_DAYS_PER_YEAR

    # Absolute metrics
    total_return = (nav.iloc[-1] / nav.iloc[0]) - 1
    cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
    ann_vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (cagr - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0

    # Downside
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sortino = (cagr - risk_free_rate) / downside_vol if downside_vol > 0 else 0.0

    # Max drawdown
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    max_dd = drawdown.min()

    # Calmar ratio
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0

    metrics = {
        "total_return": total_return,
        "cagr": cagr,
        "annualised_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "calmar_ratio": calmar,
        "n_years": n_years,
    }

    # Relative metrics (vs benchmark)
    if benchmark_nav is not None:
        bench_returns = benchmark_nav.pct_change().dropna()
        common = returns.index.intersection(bench_returns.index)

        bench_total = (benchmark_nav.iloc[-1] / benchmark_nav.iloc[0]) - 1
        bench_cagr = (1 + bench_total) ** (1 / n_years) - 1 if n_years > 0 else 0.0

        excess_return = cagr - bench_cagr
        te = compute_tracking_error(returns.loc[common], bench_returns.loc[common])
        info_ratio = excess_return / te if te > 0 else 0.0

        # Beta
        if len(common) > 1:
            cov = np.cov(returns.loc[common].values, bench_returns.loc[common].values)
            beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1.0
            alpha = cagr - (risk_free_rate + beta * (bench_cagr - risk_free_rate))
        else:
            beta = 1.0
            alpha = 0.0

        metrics.update({
            "excess_return": excess_return,
            "tracking_error": te,
            "information_ratio": info_ratio,
            "beta": beta,
            "alpha": alpha,
        })

    return metrics
