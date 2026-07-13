"""Tests for the turnover-based transaction cost model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.costs import TOTAL_COST_RATE, simulate_portfolio

IDX = pd.date_range("2022-01-03", periods=10, freq="B")


def _flat_returns(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame(0.0, index=IDX, columns=tickers)


def test_initial_buy_in_costs_one_way_rate() -> None:
    returns = _flat_returns(["A", "B"])
    targets = {IDX[0] - pd.Timedelta(days=1): pd.Series({"A": 0.5, "B": 0.5})}

    sim = simulate_portfolio(returns, targets)

    assert sim.loc[IDX[0], "turnover"] == pytest.approx(1.0)
    assert sim.loc[IDX[0], "cost"] == pytest.approx(TOTAL_COST_RATE)
    assert (sim["turnover"].iloc[1:] == 0).all()


def test_full_switch_costs_round_trip() -> None:
    returns = _flat_returns(["A", "B"])
    targets = {
        IDX[0] - pd.Timedelta(days=1): pd.Series({"A": 1.0}),
        IDX[4]: pd.Series({"B": 1.0}),  # trades on IDX[5]
    }

    sim = simulate_portfolio(returns, targets)

    assert sim.loc[IDX[5], "turnover"] == pytest.approx(2.0)
    assert sim.loc[IDX[5], "cost"] == pytest.approx(2.0 * TOTAL_COST_RATE)
    assert sim.loc[IDX[5], "net_return"] == pytest.approx(-2.0 * TOTAL_COST_RATE)


def test_zero_turnover_when_target_matches_drift() -> None:
    # Flat returns → no drift → re-declaring the same target trades nothing.
    returns = _flat_returns(["A", "B"])
    target = pd.Series({"A": 0.6, "B": 0.4})
    targets = {IDX[0] - pd.Timedelta(days=1): target, IDX[4]: target}

    sim = simulate_portfolio(returns, targets)

    assert sim.loc[IDX[5], "turnover"] == pytest.approx(0.0)
    assert sim.loc[IDX[5], "cost"] == pytest.approx(0.0)


def test_drift_matches_closed_form_two_asset_case() -> None:
    # A returns +10%/day, B flat, starting 50/50, no rebalance after entry.
    returns = _flat_returns(["A", "B"])
    returns["A"] = 0.10
    targets = {
        IDX[0] - pd.Timedelta(days=1): pd.Series({"A": 0.5, "B": 0.5}),
        IDX[2]: pd.Series({"A": 0.5, "B": 0.5}),  # rebalance back on IDX[3]
    }

    sim = simulate_portfolio(returns, targets)

    # Portfolio return each day: w_A × 10%.
    assert sim.loc[IDX[0], "gross_return"] == pytest.approx(0.05)
    w_a_day1 = 0.5 * 1.1 / 1.05
    assert sim.loc[IDX[1], "gross_return"] == pytest.approx(w_a_day1 * 0.10)

    # After 3 days of drift, weights are (0.5·1.1³, 0.5) normalised;
    # rebalancing back to 50/50 trades 2×|w_A − 0.5|.
    w_a = 0.5 * 1.1**3 / (0.5 * 1.1**3 + 0.5)
    expected_turnover = 2 * abs(w_a - 0.5)
    assert sim.loc[IDX[3], "turnover"] == pytest.approx(expected_turnover)


def test_net_nav_never_exceeds_gross_nav() -> None:
    rng = np.random.default_rng(7)
    idx = pd.date_range("2022-01-03", periods=200, freq="B")
    returns = pd.DataFrame(
        rng.normal(0.0005, 0.01, size=(len(idx), 3)), index=idx, columns=["A", "B", "C"]
    )
    targets = {
        idx[i]: pd.Series(rng.dirichlet(np.ones(3)), index=["A", "B", "C"])
        for i in range(0, 180, 21)
    }

    sim = simulate_portfolio(returns, targets)

    nav_net = (1 + sim["net_return"]).cumprod()
    nav_gross = (1 + sim["gross_return"]).cumprod()
    assert (nav_net <= nav_gross + 1e-12).all()

    total_cost = sim["cost"].sum()
    assert total_cost > 0
    assert total_cost == pytest.approx((sim["turnover"] * TOTAL_COST_RATE).sum())


def test_targets_are_normalised_and_unknown_tickers_dropped() -> None:
    returns = _flat_returns(["A", "B"])
    targets = {IDX[0] - pd.Timedelta(days=1): pd.Series({"A": 2.0, "B": 2.0, "ZZZ": 5.0})}

    sim = simulate_portfolio(returns, targets)
    # ZZZ dropped, A/B normalised to 0.5 each → initial turnover 1.0.
    assert sim.loc[IDX[0], "turnover"] == pytest.approx(1.0)


def test_no_rebalance_in_range_raises() -> None:
    returns = _flat_returns(["A"])
    with pytest.raises(ValueError, match="No rebalance date"):
        simulate_portfolio(returns, {IDX[-1] + pd.Timedelta(days=5): pd.Series({"A": 1.0})})
