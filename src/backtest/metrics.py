"""Performance and relative-risk metrics for NAV series."""

import numpy as np
import pandas as pd
from scipy import stats

from src.config import TRADING_DAYS_PER_YEAR

_EULER_MASCHERONI = 0.5772156649015329


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

        if len(common) > 0:
            strategy_common_returns = returns.loc[common]
            bench_common_returns = bench_returns.loc[common]
            relative_n_years = len(common) / TRADING_DAYS_PER_YEAR

            strategy_total = (1 + strategy_common_returns).prod() - 1
            bench_total = (1 + bench_common_returns).prod() - 1
            strategy_cagr = (
                (1 + strategy_total) ** (1 / relative_n_years) - 1
                if relative_n_years > 0
                else 0.0
            )
            bench_cagr = (
                (1 + bench_total) ** (1 / relative_n_years) - 1
                if relative_n_years > 0
                else 0.0
            )
        else:
            strategy_common_returns = pd.Series(dtype=float)
            bench_common_returns = pd.Series(dtype=float)
            strategy_cagr = cagr
            bench_cagr = 0.0

        excess_return = strategy_cagr - bench_cagr
        te = compute_tracking_error(strategy_common_returns, bench_common_returns)
        info_ratio = excess_return / te if te > 0 else 0.0

        if len(common) > 1:
            cov = np.cov(strategy_common_returns.values, bench_common_returns.values)
            beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1.0
            alpha = strategy_cagr - (
                risk_free_rate + beta * (bench_cagr - risk_free_rate)
            )
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


def expected_max_sharpe(
    n_trials: int,
    sharpe_std: float,
) -> float:
    """Expected maximum Sharpe across N independent zero-edge trials.

    Bailey & López de Prado's estimate of the best Sharpe you'd expect to
    see from ``n_trials`` strategies that all have *no* true edge, purely
    from selection noise. If an observed Sharpe doesn't clear this bar, it's
    indistinguishable from having picked the luckiest backtest.

    Args:
        n_trials: Number of strategy configurations tried.
        sharpe_std: Std dev of the Sharpe ratios across those trials
            (per-period, matching the frequency used in
            :func:`deflated_sharpe`).

    Returns:
        Expected maximum Sharpe under the null. 0.0 if inputs are degenerate.
    """
    if n_trials <= 1 or sharpe_std <= 0:
        return 0.0
    e = 1.0 - _EULER_MASCHERONI
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(sharpe_std * (e * z1 + _EULER_MASCHERONI * z2))


def probabilistic_sharpe_ratio(
    returns: pd.Series,
    benchmark_sr: float = 0.0,
) -> float:
    """Probability that the true Sharpe exceeds ``benchmark_sr``.

    PSR (Bailey & López de Prado) corrects the Sharpe estimate for sample
    length, skew, and kurtosis of the return distribution.

    Args:
        returns: Per-period (e.g. daily) returns.
        benchmark_sr: Per-period Sharpe threshold to beat.

    Returns:
        P(true SR > benchmark_sr) in [0, 1].
    """
    r = returns.dropna()
    n = len(r)
    if n < 3 or r.std(ddof=1) == 0:
        return 0.0
    sr = r.mean() / r.std(ddof=1)
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))  # non-excess
    denom = np.sqrt(1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2)
    if denom <= 0:
        return 0.0
    z = (sr - benchmark_sr) * np.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z))


def deflated_sharpe(
    returns: pd.Series,
    n_trials: int,
    sharpe_std: float,
) -> float:
    """Deflated Sharpe Ratio: PSR against the selection-adjusted benchmark.

    Combines :func:`probabilistic_sharpe_ratio` with
    :func:`expected_max_sharpe` — the probability the strategy's true Sharpe
    beats what ``n_trials`` of pure noise would have produced. A DSR near 1
    means the edge survives multiple-testing scrutiny; near 0.5 or below
    means it's consistent with selection luck.

    Args:
        returns: Per-period (daily) returns of the selected strategy.
        n_trials: Number of configurations tried before selecting it.
        sharpe_std: Std dev of per-period Sharpe across those trials.

    Returns:
        Deflated Sharpe Ratio in [0, 1].
    """
    sr_star = expected_max_sharpe(n_trials, sharpe_std)
    return probabilistic_sharpe_ratio(returns, benchmark_sr=sr_star)
