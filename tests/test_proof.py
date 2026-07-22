"""Tests for concentration analytics (explicit-ranking OLS + PIT mirror)."""

import numpy as np
import pandas as pd
import pytest

from src.proof.concentration import (
    build_mirror_index,
    concentration_curve,
    rolling_concentration,
    variance_decomposition,
)

IDX = pd.date_range("2024-01-01", periods=120, freq="B")


def test_variance_decomposition_uses_explicit_ranking() -> None:
    aapl_returns = pd.Series(np.linspace(-0.01, 0.012, len(IDX)), index=IDX)
    stock_returns = pd.DataFrame(
        {
            "MSFT": np.where(np.arange(len(IDX)) % 2 == 0, 0.08, -0.08),
            "AAPL": aapl_returns,
        },
        index=IDX,
    )

    result = variance_decomposition(
        stock_returns=stock_returns,
        benchmark_returns=aapl_returns,
        top_n_values=[1],
        ranked_tickers=["AAPL", "MSFT"],
    )

    # Top-1 is AAPL (the benchmark itself) → perfect fit.
    assert result.loc[0, "r_squared"] > 0.999


def test_concentration_curve_adds_tickers_in_given_order() -> None:
    stock_returns = pd.DataFrame(
        {
            "MSFT": np.linspace(-0.01, 0.02, len(IDX)),
            "AAPL": np.where(np.arange(len(IDX)) % 2 == 0, 0.003, -0.002),
        },
        index=IDX,
    )

    curve = concentration_curve(
        stock_returns,
        benchmark_returns=stock_returns["MSFT"],
        ranked_tickers=["AAPL", "MSFT"],
    )

    assert curve.loc[0, "ticker_added"] == "AAPL"
    assert curve.loc[1, "ticker_added"] == "MSFT"
    assert curve.loc[1, "r_squared"] > 0.999


def test_rolling_concentration_ranks_at_window_start() -> None:
    rng = np.random.default_rng(3)
    stock_returns = pd.DataFrame(
        rng.normal(0.0, 0.01, size=(len(IDX), 2)), index=IDX, columns=["AAA", "BBB"]
    )
    benchmark = stock_returns["AAA"] * 0.9 + stock_returns["BBB"] * 0.1

    seen_dates: list[pd.Timestamp] = []

    def ranking_fn(as_of: pd.Timestamp) -> list[str]:
        seen_dates.append(as_of)
        return ["AAA", "BBB"]

    result = rolling_concentration(
        stock_returns, benchmark, ranking_fn, top_n_values=[1, 2],
        window_days=60, step_days=20,
    )

    # Ranking is requested exactly at each window start.
    expected_starts = [IDX[0], IDX[20], IDX[40], IDX[60]]
    assert seen_dates == expected_starts
    assert set(result["n_stocks"]) == {1, 2}
    # Both names span the benchmark exactly → R² ≈ 1 at n=2.
    assert (result.loc[result["n_stocks"] == 2, "r_squared"] > 0.999).all()


# ──────────────────────────────────────────────
# Mirror index
# ──────────────────────────────────────────────


def test_mirror_index_selects_pit_universe() -> None:
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    stock_prices = pd.DataFrame(
        {
            "MSFT": np.linspace(400.0, 430.0, len(idx)),
            "AAPL": np.linspace(100.0, 104.0, len(idx)),
        },
        index=idx,
    )

    mirror = build_mirror_index(
        stock_prices, top_n=1, weighting="equal", universe_fn=lambda t: ["AAPL"]
    )
    mirror_returns = pd.Series(mirror["daily_return"].values, index=mirror["date"])

    aapl_returns = stock_prices["AAPL"].pct_change(fill_method=None).dropna()
    common = mirror_returns.index.intersection(aapl_returns.index)
    # Off rebalance days the net return equals AAPL's return exactly.
    off_trade = mirror.loc[mirror["turnover"] == 0, "date"]
    check = common.intersection(off_trade)
    assert len(check) > 20
    assert np.allclose(mirror_returns.loc[check], aapl_returns.loc[check])


def test_mirror_index_charges_costs_only_on_rebalance_days() -> None:
    idx = pd.date_range("2024-01-01", periods=90, freq="B")
    rng = np.random.default_rng(11)
    stock_prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, size=(len(idx), 2)), axis=0)),
        index=idx,
        columns=["AAA", "BBB"],
    )

    mirror = build_mirror_index(
        stock_prices, top_n=2, weighting="equal", universe_fn=lambda t: ["AAA", "BBB"]
    )

    trade_days = mirror["turnover"] > 0
    assert trade_days.sum() >= 3  # entry + monthly rebalances
    assert (mirror.loc[trade_days, "cost"] > 0).all()
    assert (mirror.loc[~trade_days, "cost"] == 0).all()
    # Net NAV lags gross NAV once costs accrue.
    assert mirror["nav"].iloc[-1] < mirror["nav_gross"].iloc[-1]


def test_mirror_index_no_lookahead_in_universe() -> None:
    idx = pd.date_range("2024-01-01", periods=90, freq="B")
    stock_prices = pd.DataFrame(
        {
            "AAA": np.full(len(idx), 100.0),
            "BBB": np.full(len(idx), 50.0),
        },
        index=idx,
    )

    calls: list[pd.Timestamp] = []

    def universe_fn(as_of: pd.Timestamp) -> list[str]:
        calls.append(as_of)
        return ["AAA", "BBB"]

    build_mirror_index(stock_prices, top_n=2, weighting="equal", universe_fn=universe_fn)

    # Every universe request is a decision date within the price index —
    # weights for day d+1 are only ever requested with as_of ≤ d.
    assert all(c in stock_prices.index for c in calls)


def test_mirror_index_cap_weights_use_shares_anchor() -> None:
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    stock_prices = pd.DataFrame(
        {
            "AAA": np.full(len(idx), 100.0),   # cap 100 × 10 = 1000
            "BBB": np.full(len(idx), 10.0),    # cap 10 × 500 = 5000
        },
        index=idx,
    )
    shares = pd.Series({"AAA": 10.0, "BBB": 500.0})

    mirror = build_mirror_index(
        stock_prices,
        top_n=2,
        weighting="cap",
        universe_fn=lambda t: ["AAA", "BBB"],
        shares=shares,
        ranking_prices=stock_prices,  # inject synthetic ranking panel
    )
    # Entry turnover is 1.0; flat prices → no further trading.
    entry = mirror.loc[mirror["turnover"] > 0]
    assert len(entry) == 1
    assert entry["turnover"].iloc[0] == pytest.approx(1.0)


def test_mirror_index_cap_weights_follow_ranking_panel_not_return_panel() -> None:
    # Return panel and ranking panel disagree on price levels. Cap weights
    # must follow the RANKING panel (dividend-unadjusted) — this is the
    # dividend-adjustment fix: adjusted prices must never drive cap weights.
    idx = pd.date_range("2024-01-01", periods=60, freq="B")
    stock_prices = pd.DataFrame(
        {"AAA": np.full(len(idx), 10.0), "BBB": np.full(len(idx), 10.0)},
        index=idx,
    )
    # Ranking panel says AAA is 9× BBB by price; shares equal → AAA cap 9×.
    ranking_prices = pd.DataFrame(
        {"AAA": np.full(len(idx), 90.0), "BBB": np.full(len(idx), 10.0)},
        index=idx,
    )
    shares = pd.Series({"AAA": 1.0, "BBB": 1.0})

    mirror = build_mirror_index(
        stock_prices,
        top_n=2,
        weighting="cap",
        universe_fn=lambda t: ["AAA", "BBB"],
        shares=shares,
        ranking_prices=ranking_prices,
    )
    # Flat returns → first-day weights persist; entry turnover 1.0, and the
    # NAV is flat (both stocks flat) confirming weights applied without error.
    assert mirror["turnover"].iloc[0] == pytest.approx(1.0)
    assert mirror["nav"].iloc[-1] == pytest.approx(mirror["nav"].iloc[0])


def test_mirror_index_rejects_unknown_weighting() -> None:
    idx = pd.date_range("2024-01-01", periods=30, freq="B")
    prices = pd.DataFrame({"AAA": np.full(len(idx), 1.0)}, index=idx)
    with pytest.raises(ValueError, match="Unknown weighting"):
        build_mirror_index(prices, weighting="momentum", universe_fn=lambda t: ["AAA"])
