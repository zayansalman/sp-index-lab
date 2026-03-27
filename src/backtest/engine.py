"""Walk-forward backtesting engine (no look-ahead)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class WalkForwardSplit:
    """A single walk-forward split."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


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


def walk_forward_backtest(
    prices: pd.DataFrame,
    *,
    benchmark_prices: pd.Series | None = None,
    weights_fn: WeightsFn,
    train_days: int = 756,
    test_days: int = 21,
    step_days: int | None = None,
) -> pd.Series:
    """Run a walk-forward backtest producing an out-of-sample NAV series.

    This engine enforces no look-ahead by computing weights on *training* data
    only, then applying them to the subsequent *test* window returns.

    Args:
        prices: Wide price DataFrame indexed by date (DatetimeIndex).
        benchmark_prices: Optional benchmark price Series aligned by date.
        weights_fn: Function that maps (train_prices, train_benchmark_prices)
            to a weight Series indexed by ticker.
        train_days: Training window length in trading days.
        test_days: Test window length in trading days.
        step_days: Advance between splits; defaults to `test_days`.

    Returns:
        Out-of-sample NAV series indexed by date (normalized to 1.0 at start).
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

    # Precompute returns once.
    returns = prices.pct_change(fill_method=None)

    oos_returns: list[pd.Series] = []
    for s in splits:
        train_prices = prices.loc[s.train_start : s.train_end]
        test_returns = returns.loc[s.test_start : s.test_end].dropna(how="all")

        if benchmark_prices is not None:
            train_bench = benchmark_prices.loc[s.train_start : s.train_end]
        else:
            train_bench = None

        w = weights_fn(train_prices, train_bench)
        w = w.reindex(prices.columns).fillna(0.0)
        total = float(w.sum())
        if total == 0.0:
            raise ValueError("weights_fn returned all-zero weights.")
        w = w / total

        # Use fixed weights over the test window (rebalance at test start).
        test_portfolio = (test_returns * w).sum(axis=1)
        oos_returns.append(test_portfolio)

    out = pd.concat(oos_returns).sort_index()
    nav = (1 + out.fillna(0.0)).cumprod()
    nav = nav / nav.iloc[0]
    nav.name = "nav"
    return nav

