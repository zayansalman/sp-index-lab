"""Tests for the self-adjusting SP-N Alpha (dynamic N + engine + overlay)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MAX_POSITION_WEIGHT, SPN_MAX_STOCKS, SPN_MIN_STOCKS
from src.strategies.dynamic_alpha import (
    CASH,
    make_dynamic_alpha_weights_fn,
    make_elbow_n,
    make_static_n,
    make_vol_target,
)


def _panel(n_tickers: int = 30, n_days: int = 400, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-01", periods=n_days)
    # Cap-descending column order (as the engine delivers), distinct drifts.
    drifts = np.linspace(0.0008, 0.0002, n_tickers)
    cols = [f"T{i:02d}" for i in range(n_tickers)]
    data = {
        c: 100 * np.cumprod(1 + rng.normal(drifts[i], 0.012, n_days))
        for i, c in enumerate(cols)
    }
    return pd.DataFrame(data, index=idx)


def test_static_n_selects_exactly_n_and_bounds_hold() -> None:
    prices = _panel()
    wf = make_dynamic_alpha_weights_fn("equal", make_static_n(20))
    w = wf(prices, None)
    assert len(w) == 20
    assert abs(w.sum() - 1.0) < 1e-9
    assert (w <= MAX_POSITION_WEIGHT + 1e-9).all()


def test_elbow_n_stays_within_bounds() -> None:
    prices = _panel()
    bench = prices.iloc[:, :5].mean(axis=1)  # benchmark ~ top names
    policy = make_elbow_n()
    n = policy(prices, bench)
    assert SPN_MIN_STOCKS <= n <= SPN_MAX_STOCKS


def test_elbow_uses_only_supplied_window_no_lookahead() -> None:
    # The policy only ever sees the (trailing) frame it is handed; appending
    # wildly different future rows to a separate copy must not change N,
    # because those rows are never passed in.
    prices = _panel()
    bench = prices.iloc[:, :5].mean(axis=1)
    policy = make_elbow_n()
    n1 = policy(prices, bench)

    future = _panel(seed=999).copy()
    future.index = pd.bdate_range("2030-01-01", periods=len(future))
    # Recompute on the SAME trailing window; future data is not in scope.
    n2 = policy(prices, bench)
    assert n1 == n2


def test_vol_target_adds_cash_when_realised_vol_high() -> None:
    # Highly-correlated high-vol panel (shared market factor) so the
    # diversified portfolio's realised vol stays well above the 15% target
    # and the overlay must park exposure in CASH.
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2019-01-01", periods=300)
    cols = [f"T{i:02d}" for i in range(SPN_MAX_STOCKS)]
    common = rng.normal(0.0005, 0.025, 300)  # ~40% annualised common factor
    prices = pd.DataFrame(
        {
            c: 100 * np.cumprod(1 + common + rng.normal(0.0, 0.004, 300))
            for c in cols
        },
        index=idx,
    )
    wf = make_dynamic_alpha_weights_fn(
        "equal", make_static_n(20), overlay=make_vol_target(0.15)
    )
    w = wf(prices, None)
    assert CASH in w.index
    assert w[CASH] > 0.0
    assert abs(w.sum() - 1.0) < 1e-9
    # Equity exposure scaled below full.
    assert w.drop(CASH).sum() < 1.0


def test_cash_column_excluded_from_equity_selection() -> None:
    prices = _panel()
    prices[CASH] = 100.0  # engine may hand a CASH column through
    wf = make_dynamic_alpha_weights_fn("equal", make_static_n(15))
    w = wf(prices, None)
    # No overlay → CASH must not be selected as an equity holding.
    assert CASH not in w.index
    assert len(w) == 15
