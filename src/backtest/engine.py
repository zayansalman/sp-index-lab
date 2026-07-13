"""Walk-forward backtesting engine (no look-ahead, net of costs)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from src.backtest.costs import simulate_portfolio


@dataclass(frozen=True)
class WalkForwardSplit:
    """A single walk-forward split."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


@dataclass(frozen=True)
class WalkForwardResult:
    """Output of a walk-forward backtest.

    ``nav`` is net of transaction costs and is the canonical series;
    ``nav_gross`` is the frictionless counterpart. ``turnover`` and
    ``costs`` are indexed by trade date (each test-window start).
    """

    nav: pd.Series
    nav_gross: pd.Series
    turnover: pd.Series
    costs: pd.Series
    splits: list[WalkForwardSplit]


def generate_walk_forward_splits(
    dates: pd.DatetimeIndex,
    *,
    train_days: int = 756,
    test_days: int = 21,
    step_days: int | None = None,
) -> list[WalkForwardSplit]:
    """Generate expanding-window walk-forward splits.

    Splits are defined on an ordered trading-day index. The training window is
    the prior `train_days` observations immediately before the test window.
    The test window is the next `test_days` observations.

    Args:
        dates: Sorted DatetimeIndex (trading days).
        train_days: Number of observations in each training window.
        test_days: Number of observations in each test window.
        step_days: How far to advance between splits. Defaults to `test_days`.

    Returns:
        List of walk-forward splits.
    """
    if step_days is None:
        step_days = test_days
    if train_days <= 0 or test_days <= 0 or step_days <= 0:
        raise ValueError("train_days, test_days, and step_days must be positive.")

    dates = pd.DatetimeIndex(dates).sort_values()
    if len(dates) < train_days + test_days:
        return []

    splits: list[WalkForwardSplit] = []
    test_start_i = train_days
    while test_start_i + test_days <= len(dates):
        train_start_i = test_start_i - train_days
        train_end_i = test_start_i - 1
        test_end_i = test_start_i + test_days - 1

        splits.append(
            WalkForwardSplit(
                train_start=dates[train_start_i],
                train_end=dates[train_end_i],
                test_start=dates[test_start_i],
                test_end=dates[test_end_i],
            )
        )

        test_start_i += step_days

    return splits


WeightsFn = Callable[[pd.DataFrame, pd.Series | None], pd.Series]
UniverseFn = Callable[[pd.Timestamp], "list[str]"]


def walk_forward_backtest(
    prices: pd.DataFrame,
    *,
    benchmark_prices: pd.Series | None = None,
    weights_fn: WeightsFn,
    train_days: int = 756,
    test_days: int = 21,
    step_days: int | None = None,
    universe_fn: UniverseFn | None = None,
) -> WalkForwardResult:
    """Run a walk-forward backtest producing out-of-sample net/gross NAVs.

    No look-ahead by construction: the tradable universe is evaluated at
    each training window's end, weights are computed on training data only,
    and both apply to the subsequent test window. Between rebalances the
    portfolio drifts buy-and-hold; each rebalance is charged turnover-based
    transaction costs (see :mod:`src.backtest.costs`).

    Args:
        prices: Wide price DataFrame indexed by date (DatetimeIndex).
        benchmark_prices: Optional benchmark price Series aligned by date.
        weights_fn: Function that maps (train_prices, train_benchmark_prices)
            to a weight Series indexed by ticker.
        train_days: Training window length in trading days.
        test_days: Test window length in trading days.
        step_days: Advance between splits; defaults to `test_days`.
        universe_fn: Optional ``as_of → tickers`` callable (e.g. from
            :func:`src.data.universe.make_universe_fn`). Called with each
            split's ``train_end``; the training slice passed to
            ``weights_fn`` is restricted to those columns.

    Returns:
        WalkForwardResult with net/gross NAV series (both normalised to 1.0
        at the first out-of-sample date), per-rebalance turnover and costs,
        and the splits used.
    """
    if prices.empty:
        raise ValueError("prices is empty.")
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise TypeError("prices must be indexed by a DatetimeIndex.")

    prices = prices.sort_index()
    dates = prices.index
    splits = generate_walk_forward_splits(
        dates, train_days=train_days, test_days=test_days, step_days=step_days
    )
    if not splits:
        raise ValueError("Not enough data to generate walk-forward splits.")

    rebalance_targets: dict[pd.Timestamp, pd.Series] = {}
    for s in splits:
        train_prices = prices.loc[s.train_start : s.train_end]

        if universe_fn is not None:
            universe = [t for t in universe_fn(s.train_end) if t in prices.columns]
            if not universe:
                raise ValueError(f"universe_fn returned no tradable tickers at {s.train_end}.")
            train_prices = train_prices[universe]

        if benchmark_prices is not None:
            train_bench = benchmark_prices.loc[s.train_start : s.train_end]
        else:
            train_bench = None

        w = weights_fn(train_prices, train_bench)
        w = w[w != 0.0].dropna()
        total = float(w.sum())
        if total == 0.0:
            raise ValueError("weights_fn returned all-zero weights.")
        rebalance_targets[s.train_end] = w / total

    returns = prices.pct_change(fill_method=None)
    oos_returns = returns.loc[splits[0].test_start : splits[-1].test_end]

    sim = simulate_portfolio(oos_returns, rebalance_targets)

    nav = (1 + sim["net_return"]).cumprod()
    nav = nav / nav.iloc[0]
    nav.name = "nav"

    nav_gross = (1 + sim["gross_return"]).cumprod()
    nav_gross = nav_gross / nav_gross.iloc[0]
    nav_gross.name = "nav_gross"

    trade_days = sim.index[sim["turnover"] > 0]
    return WalkForwardResult(
        nav=nav,
        nav_gross=nav_gross,
        turnover=sim.loc[trade_days, "turnover"],
        costs=sim.loc[trade_days, "cost"],
        splits=splits,
    )

