"""Tests for point-in-time universe selection (membership + ranking)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.storage import load_parquet
from src.data.universe import (
    MEMBERSHIP_CSV,
    build_universe_schedule,
    get_members_at,
    get_top_n_at,
    load_membership,
    rank_by_dollar_volume,
)

# ──────────────────────────────────────────────
# Synthetic fixtures
# ──────────────────────────────────────────────

IDX = pd.date_range("2020-01-01", periods=300, freq="B")


@pytest.fixture
def prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "AAA": np.full(len(IDX), 100.0),
            "BBB": np.full(len(IDX), 50.0),
            "CCC": np.full(len(IDX), 10.0),
        },
        index=IDX,
    )


@pytest.fixture
def volumes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "AAA": np.full(len(IDX), 1_000.0),      # $100k/day
            "BBB": np.full(len(IDX), 10_000.0),     # $500k/day
            "CCC": np.full(len(IDX), 2_000.0),      # $20k/day
        },
        index=IDX,
    )


@pytest.fixture
def membership(tmp_path: Path) -> pd.DataFrame:
    csv = tmp_path / "membership.csv"
    csv.write_text(
        "date,tickers\n"
        '2019-01-01,"AAA,BBB"\n'
        '2021-01-04,"AAA,BBB,CCC"\n'
    )
    return load_membership(csv, aliases_path=tmp_path / "x", exclusions_path=tmp_path / "y")


# ──────────────────────────────────────────────
# Membership parsing
# ──────────────────────────────────────────────


def test_membership_snapshot_selection(membership: pd.DataFrame) -> None:
    assert get_members_at(pd.Timestamp("2020-01-15"), membership) == {"AAA", "BBB"}
    assert get_members_at(pd.Timestamp("2021-01-15"), membership) == {"AAA", "BBB", "CCC"}


def test_membership_before_first_snapshot_raises(membership: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="No membership snapshot"):
        get_members_at(pd.Timestamp("2018-01-01"), membership)


def test_membership_normalisation(tmp_path: Path) -> None:
    csv = tmp_path / "membership.csv"
    csv.write_text('date,tickers\n2020-01-01,"BRK.B,FB,GOOG,GOOGL,AGN,AAPL"\n')
    aliases = tmp_path / "aliases.csv"
    aliases.write_text(
        "membership_ticker,yf_ticker,note\nFB,META,rename\nGOOG,GOOGL,dedupe\n"
    )
    exclusions = tmp_path / "exclusions.csv"
    exclusions.write_text("ticker,reason,last_date\nAGN,delisted,2020-05-08\n")

    members = get_members_at(
        pd.Timestamp("2020-02-01"),
        load_membership(csv, aliases_path=aliases, exclusions_path=exclusions),
    )
    assert members == {"BRK-B", "META", "GOOGL", "AAPL"}


# ──────────────────────────────────────────────
# Ranking
# ──────────────────────────────────────────────


def test_ranking_follows_dollar_volume(prices: pd.DataFrame, volumes: pd.DataFrame) -> None:
    ranked = rank_by_dollar_volume(prices, volumes, as_of=IDX[-1])
    assert list(ranked.index) == ["BBB", "AAA", "CCC"]


def test_ranking_requires_min_observations(prices: pd.DataFrame, volumes: pd.DataFrame) -> None:
    prices = prices.copy()
    prices.loc[prices.index[:-10], "CCC"] = np.nan  # only 10 valid days
    ranked = rank_by_dollar_volume(prices, volumes, as_of=IDX[-1], min_obs=126)
    assert "CCC" not in ranked.index


def test_top_n_respects_membership(
    prices: pd.DataFrame, volumes: pd.DataFrame, membership: pd.DataFrame
) -> None:
    # Before 2021-01-04, CCC is not a member even though it has data.
    top = get_top_n_at(
        pd.Timestamp("2020-12-01"), 3, prices=prices, volumes=volumes, membership=membership
    )
    assert top == ["BBB", "AAA"]


# ──────────────────────────────────────────────
# No look-ahead (the critical invariant)
# ──────────────────────────────────────────────


def test_no_lookahead_future_data_cannot_change_selection(
    prices: pd.DataFrame, volumes: pd.DataFrame, membership: pd.DataFrame
) -> None:
    as_of = IDX[150]
    before = get_top_n_at(as_of, 2, prices=prices, volumes=volumes, membership=membership)

    # Mutate everything strictly after as_of by 100x — selection must not move.
    mutated_p = prices.copy()
    mutated_v = volumes.copy()
    mutated_p.loc[mutated_p.index > as_of] *= 100.0
    mutated_v.loc[mutated_v.index > as_of] *= 100.0

    after = get_top_n_at(as_of, 2, prices=mutated_p, volumes=mutated_v, membership=membership)
    assert before == after


def test_universe_schedule_shape_and_no_lookahead(
    prices: pd.DataFrame, volumes: pd.DataFrame, membership: pd.DataFrame
) -> None:
    rebalance_dates = pd.DatetimeIndex([IDX[150], IDX[250]])
    schedule = build_universe_schedule(
        rebalance_dates, 2, prices=prices, volumes=volumes, membership=membership
    )
    assert set(schedule.columns) == {"rebalance_date", "rank", "ticker", "avg_dollar_volume"}
    assert len(schedule) == 4  # 2 dates × top-2

    mutated_p = prices.copy()
    mutated_p.loc[mutated_p.index > IDX[250]] *= 100.0
    schedule2 = build_universe_schedule(
        rebalance_dates, 2, prices=mutated_p, volumes=volumes, membership=membership
    )
    pd.testing.assert_frame_equal(schedule, schedule2)


# ──────────────────────────────────────────────
# Real vendored data
# ──────────────────────────────────────────────


def test_vendored_membership_sanity() -> None:
    membership = load_membership()
    assert membership["date"].is_monotonic_increasing

    members_2020 = get_members_at(pd.Timestamp("2020-01-02"), membership)
    assert "AAPL" in members_2020
    assert "META" in members_2020  # FB alias applied
    assert 480 <= len(members_2020) <= 515


@pytest.mark.slow
def test_dollar_volume_proxy_matches_historical_top20() -> None:
    """Proxy ranking should broadly agree with known historical top-20 lists."""
    prices_df = load_parquet("daily_prices")
    volumes_df = load_parquet("daily_volumes")
    if prices_df.empty or volumes_df.empty:
        pytest.skip("requires backfilled daily_prices/daily_volumes parquet")

    prices = prices_df.set_index("date")
    prices.index = pd.to_datetime(prices.index)
    volumes = volumes_df.set_index("date")
    volumes.index = pd.to_datetime(volumes.index)

    snapshots = pd.read_csv(MEMBERSHIP_CSV.parent / "topn_snapshots.csv", parse_dates=["as_of"])
    for row in snapshots.itertuples():
        expected = set(row.tickers.split(","))
        actual = set(get_top_n_at(row.as_of, 20, prices=prices, volumes=volumes))
        overlap = len(expected & actual) / 20
        assert overlap >= 0.6, (
            f"{row.as_of.date()}: only {overlap:.0%} overlap with historical top-20; "
            f"proxy-only: {sorted(actual - expected)}, missing: {sorted(expected - actual)}"
        )
