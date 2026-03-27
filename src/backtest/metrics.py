"""Performance and relative-risk metrics for NAV series."""

import numpy as np
import pandas as pd

from src.config import TRADING_DAYS_PER_YEAR


def compute_tracking_error(
    index_returns: pd.Series,
    benchmark_returns: pd.Series,
    annualize: bool = True,
) -> float:
    """Compute tracking error between an index and a benchmark.

    Args:
        index_returns: Period returns of the constructed index.
        benchmark_returns: Period returns of the benchmark.
        annualize: Whether to annualize by trading days per year.

    Returns:
        Tracking error as the standard deviation of return differences.
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
    """Compute absolute and relative performance metrics from a NAV series.

    Args:
        nav: NAV series (normalized, typically starting near 1.0).
        benchmark_nav: Optional benchmark NAV series for relative metrics.
        risk_free_rate: Annual risk-free rate used by Sharpe/Sortino/alpha.

    Returns:
        Dictionary with performance and risk metrics.
    """
    returns = nav.pct_change().dropna()
    n_years = len(returns) / TRADING_DAYS_PER_YEAR

    total_return = (nav.iloc[-1] / nav.iloc[0]) - 1
    cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
    ann_vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (cagr - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0

    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sortino = (cagr - risk_free_rate) / downside_vol if downside_vol > 0 else 0.0

    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    max_dd = drawdown.min()
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

    if benchmark_nav is not None:
        bench_returns = benchmark_nav.pct_change().dropna()
        common = returns.index.intersection(bench_returns.index)

        bench_total = (benchmark_nav.iloc[-1] / benchmark_nav.iloc[0]) - 1
        bench_cagr = (1 + bench_total) ** (1 / n_years) - 1 if n_years > 0 else 0.0

        excess_return = cagr - bench_cagr
        te = compute_tracking_error(returns.loc[common], bench_returns.loc[common])
        info_ratio = excess_return / te if te > 0 else 0.0

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
