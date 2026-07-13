"""Concentration proof analytics — the statistical backbone.

Proves that the S&P 500 is effectively a ~20-stock index:
- Variance decomposition: how much of S&P variance is explained by top N
- Concentration curve: cumulative R² as ranked stocks are added
- Rolling concentration: the same R², point-in-time, across rolling windows
- Mirror index: investable top-N portfolio, point-in-time, net of costs

All ranking is explicit: static functions take a ``ranked_tickers`` list,
rolling/portfolio functions take a point-in-time ``ranking_fn``/
``universe_fn`` (see :mod:`src.data.universe`). Nothing in this module
ranks by full-sample statistics — that was the survivorship bug.
"""

import logging
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.backtest.costs import simulate_portfolio
from src.backtest.metrics import (
    compute_performance_metrics as _compute_performance_metrics,
)
from src.backtest.metrics import (
    compute_tracking_error as _compute_tracking_error,
)
from src.config import MIRROR_REBALANCE_FREQ
from src.data.universe import (
    load_ranking_prices,
    load_shares_outstanding,
    rank_by_cap_proxy,
)

logger = logging.getLogger(__name__)

RankingFn = Callable[[pd.Timestamp], "list[str]"]


def variance_decomposition(
    stock_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
    top_n_values: list[int] | None = None,
    *,
    ranked_tickers: list[str],
) -> pd.DataFrame:
    """Compute R² of top-N stocks explaining benchmark variance.

    For each N in top_n_values, fits a linear regression of the benchmark
    returns on the first N tickers of ``ranked_tickers`` and records R².

    Args:
        stock_returns: Daily returns for each stock.
        benchmark_returns: Daily returns for the benchmark (S&P 500).
        top_n_values: List of N values to test. Defaults to
            [5, 10, 15, 20, 25, 30, 40, 50].
        ranked_tickers: Tickers in descending importance order (e.g. a
            point-in-time market-cap ranking).

    Returns:
        DataFrame with columns: n_stocks, r_squared, adj_r_squared.
    """
    if top_n_values is None:
        top_n_values = [5, 10, 15, 20, 25, 30, 40, 50]

    # Align data
    common_idx = stock_returns.index.intersection(benchmark_returns.index)
    X_all = stock_returns.loc[common_idx]
    y = benchmark_returns.loc[common_idx].values
    ranked = [t for t in ranked_tickers if t in X_all.columns]

    results = []
    for n in top_n_values:
        if n > len(ranked):
            continue
        top_n_tickers = ranked[:n]
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
    *,
    ranked_tickers: list[str],
) -> pd.DataFrame:
    """Build the concentration curve: cumulative R² as stocks are added.

    Adds one stock at a time in ``ranked_tickers`` order and tracks
    cumulative R² — showing diminishing marginal contribution.

    Args:
        stock_returns: Daily returns for each stock.
        benchmark_returns: Daily returns for the benchmark.
        ranked_tickers: Tickers in descending importance order.

    Returns:
        DataFrame with columns: n_stocks, ticker_added, r_squared,
        marginal_r_squared.
    """
    common_idx = stock_returns.index.intersection(benchmark_returns.index)
    X_all = stock_returns.loc[common_idx]
    y = benchmark_returns.loc[common_idx].values
    mask = ~np.isnan(y)

    ranked = [t for t in ranked_tickers if t in X_all.columns]

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


def rolling_concentration(
    stock_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
    ranking_fn: RankingFn,
    top_n_values: list[int] | None = None,
    window_days: int = 252,
    step_days: int = 21,
) -> pd.DataFrame:
    """Point-in-time concentration R² across rolling windows.

    For each rolling window, ranks stocks as of the window *start* (using
    only prior data via ``ranking_fn``) and regresses benchmark returns on
    the top-N within the window. The published headline is the mean across
    windows — "on average, the 20 largest stocks *at the time* explain X%
    of daily variance" — with no survivorship in the selection.

    Args:
        stock_returns: Daily returns for each stock.
        benchmark_returns: Daily returns for the benchmark.
        ranking_fn: ``as_of → ordered tickers`` (point-in-time ranking).
        top_n_values: N values per window. Defaults to
            [5, 10, 15, 20, 25, 30, 40, 50].
        window_days: Regression window length in trading days.
        step_days: Step between window starts.

    Returns:
        Long DataFrame with columns: window_start, window_end, n_stocks,
        r_squared.
    """
    if top_n_values is None:
        top_n_values = [5, 10, 15, 20, 25, 30, 40, 50]

    common_idx = stock_returns.index.intersection(benchmark_returns.index)
    X_all = stock_returns.loc[common_idx]
    y_all = benchmark_returns.loc[common_idx]

    records = []
    for start_i in range(0, len(common_idx) - window_days + 1, step_days):
        window_idx = common_idx[start_i : start_i + window_days]
        window_start = window_idx[0]

        ranked = [t for t in ranking_fn(window_start) if t in X_all.columns]
        if not ranked:
            continue

        X_window = X_all.loc[window_idx]
        y = y_all.loc[window_idx].values
        y_mask = ~np.isnan(y)

        for n in top_n_values:
            if n > len(ranked):
                continue
            X = X_window[ranked[:n]].values
            mask = y_mask & ~np.isnan(X).any(axis=1)
            if mask.sum() < n + 2:
                continue
            r2 = LinearRegression().fit(X[mask], y[mask]).score(X[mask], y[mask])
            records.append({
                "window_start": window_start,
                "window_end": window_idx[-1],
                "n_stocks": n,
                "r_squared": r2,
            })

    return pd.DataFrame(records)


def build_mirror_index(
    stock_prices: pd.DataFrame,
    top_n: int = 20,
    weighting: str = "cap",
    *,
    universe_fn: RankingFn,
    shares: pd.Series | None = None,
    ranking_prices: pd.DataFrame | None = None,
    start: pd.Timestamp | str | None = None,
    rebalance_freq: str = MIRROR_REBALANCE_FREQ,
) -> pd.DataFrame:
    """Build an investable top-N mirror index, point-in-time, net of costs.

    At each rebalance decision date (month-end trading day by default) the
    universe is re-selected via ``universe_fn`` and target weights are set;
    trading happens on the next trading day with turnover-based costs
    (see :mod:`src.backtest.costs`). Between rebalances the portfolio
    drifts buy-and-hold — which is exactly what cap-weighting does, so
    "cap" turnover is only rank churn.

    Args:
        stock_prices: Wide-format daily prices.
        top_n: Number of top stocks to include.
        weighting: "cap" for cap-proxy-weighted, "equal" for equal-weighted.
        universe_fn: ``as_of → ordered top tickers`` (point-in-time).
        shares: Effective shares outstanding for cap weights; defaults to
            the vendored anchor (``data/reference/shares_outstanding.csv``).
        ranking_prices: Split-adjusted, dividend-unadjusted closes for
            cap-weight computation (:func:`load_ranking_prices`). Defaults
            to that panel; ``stock_prices`` (dividend-adjusted) stays the
            return basis. Cap *weights* must use the raw panel for the same
            reason universe *selection* does.
        start: First NAV date (decision dates before it are skipped except
            the one immediately prior, so the portfolio exists at start).
            Defaults to the first price date.
        rebalance_freq: pandas period frequency for rebalance dates.

    Returns:
        DataFrame with columns: date, nav, daily_return, index_name,
        nav_gross, daily_return_gross, turnover, cost. ``nav`` is net of
        costs and normalised to 1.0 at the first date.
    """
    if weighting not in ("cap", "equal"):
        raise ValueError(f"Unknown weighting: {weighting}")

    idx = stock_prices.index
    start_ts = pd.Timestamp(start) if start is not None else idx[0]

    month_ends = idx.to_series().groupby(idx.to_period(rebalance_freq)).max()
    prior = month_ends[month_ends < start_ts]
    first_decision = prior.max() if not prior.empty else idx[0]
    decision_dates = pd.DatetimeIndex(
        [first_decision] + list(month_ends[month_ends >= start_ts])
    ).unique()

    if weighting == "cap":
        if shares is None:
            shares = load_shares_outstanding()
        if ranking_prices is None:
            ranking_prices = load_ranking_prices()

    targets: dict[pd.Timestamp, pd.Series] = {}
    for t in decision_dates:
        universe = [u for u in universe_fn(t)[:top_n] if u in stock_prices.columns]
        if not universe:
            logger.warning("No universe at %s — skipping rebalance", t.date())
            continue

        if weighting == "equal":
            targets[t] = pd.Series(1.0 / len(universe), index=universe)
        else:
            caps = rank_by_cap_proxy(ranking_prices, shares, t)
            w = caps.reindex(universe).dropna()
            if w.empty:
                logger.warning("No cap weights at %s — skipping rebalance", t.date())
                continue
            targets[t] = w / w.sum()

    returns = stock_prices.pct_change(fill_method=None)
    sim = simulate_portfolio(returns, targets)

    nav = (1 + sim["net_return"]).cumprod()
    nav = nav / nav.iloc[0]
    nav_gross = (1 + sim["gross_return"]).cumprod()
    nav_gross = nav_gross / nav_gross.iloc[0]

    index_name = f"sp{top_n}_mirror" if weighting == "cap" else f"sp{top_n}_equal"

    return pd.DataFrame({
        "date": sim.index,
        "nav": nav.values,
        "daily_return": sim["net_return"].values,
        "index_name": index_name,
        "nav_gross": nav_gross.values,
        "daily_return_gross": sim["gross_return"].values,
        "turnover": sim["turnover"].values,
        "cost": sim["cost"].values,
    })


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
