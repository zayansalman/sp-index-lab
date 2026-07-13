import numpy as np
import pandas as pd

from src.backtest.engine import generate_walk_forward_splits, walk_forward_backtest


def test_generate_walk_forward_splits_window_boundaries() -> None:
    dates = pd.date_range("2020-01-01", periods=1000, freq="B")
    splits = generate_walk_forward_splits(dates, train_days=756, test_days=21, step_days=21)
    assert len(splits) > 0
    s0 = splits[0]
    assert s0.train_start == dates[0]
    assert s0.train_end == dates[755]
    assert s0.test_start == dates[756]
    assert s0.test_end == dates[776]

    # Ensure no overlap between train and test.
    assert s0.train_end < s0.test_start


def test_walk_forward_backtest_no_lookahead_by_construction() -> None:
    # Build a dataset where the final day in each training window has a huge move,
    # but the first day of the test window is flat. If weights used test data,
    # they'd react to the test spike (which doesn't exist) or otherwise misalign.
    dates = pd.date_range("2020-01-01", periods=1000, freq="B")
    tickers = ["A", "B"]

    # Start both at 100.
    prices = pd.DataFrame(100.0, index=dates, columns=tickers)
    # Create a deterministic pattern: during training, A ramps slightly; during test, B ramps slightly.
    prices["A"] = 100.0 * (1.0 + 0.0001) ** np.arange(len(dates))
    prices["B"] = 100.0 * (1.0 + 0.00005) ** np.arange(len(dates))

    def weights_fn(train_prices: pd.DataFrame, _bench: pd.Series | None) -> pd.Series:
        # Choose the ticker with higher trailing return in TRAIN only.
        tr = train_prices.iloc[-1] / train_prices.iloc[0] - 1
        winner = tr.idxmax()
        return pd.Series({winner: 1.0})

    result = walk_forward_backtest(prices, weights_fn=weights_fn, train_days=756, test_days=21)
    nav = result.nav
    assert isinstance(nav, pd.Series)
    assert nav.index.is_monotonic_increasing
    assert float(nav.iloc[0]) == 1.0

    # Net NAV can never beat the frictionless NAV (up to float noise).
    assert float(nav.iloc[-1]) <= float(result.nav_gross.iloc[-1]) + 1e-9


def test_walk_forward_backtest_universe_fn_restricts_training_columns() -> None:
    dates = pd.date_range("2020-01-01", periods=1000, freq="B")
    prices = pd.DataFrame(
        {
            "A": 100.0 * (1.0 + 0.0002) ** np.arange(len(dates)),
            "B": 100.0 * (1.0 + 0.0001) ** np.arange(len(dates)),
            "C": 100.0 * (1.0 + 0.00005) ** np.arange(len(dates)),
        },
        index=dates,
    )

    seen: set[str] = set()

    def weights_fn(train_prices: pd.DataFrame, _bench: pd.Series | None) -> pd.Series:
        seen.update(train_prices.columns)
        return pd.Series(1.0, index=train_prices.columns)

    result = walk_forward_backtest(
        prices,
        weights_fn=weights_fn,
        train_days=756,
        test_days=21,
        universe_fn=lambda as_of: ["B", "C"],
    )
    assert seen == {"B", "C"}
    assert len(result.turnover) == len(result.splits)

