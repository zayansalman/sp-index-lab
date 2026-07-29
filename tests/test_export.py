"""Tests for frontend export honesty (no fabricated NAV tails)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts import export_frontend_data as export


@pytest.fixture()
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Capture payloads instead of writing JSON to frontend/public/data."""
    box: dict[str, Any] = {}

    def fake_write(data: Any, filename: str) -> Path:
        box[filename] = data
        return Path("/dev/null")

    monkeypatch.setattr(export, "_write_json", fake_write)
    return box


def _nav(dates: pd.DatetimeIndex, drift: float, name: str) -> pd.Series:
    return pd.Series(
        np.cumprod(np.full(len(dates), 1.0 + drift)), index=dates, name=name
    )


def test_performance_nav_truncates_at_last_real_datapoint(
    captured: dict[str, Any],
) -> None:
    dates = pd.bdate_range("2024-01-01", periods=100)
    benchmark_nav = _nav(dates, 0.0004, "sp500")
    mirror_nav = _nav(dates, 0.0005, "sp20_mirror")
    equal_nav = _nav(dates, 0.0005, "sp20_equal")
    # Alpha's data ends 10 trading days before the rest.
    alpha_nav = _nav(dates[:90], 0.0006, "spn_alpha")

    export.export_performance_nav(
        stock_prices=pd.DataFrame(index=dates),
        benchmark=benchmark_nav,
        sp20_mirror=pd.DataFrame(),
        sp20_equal=pd.DataFrame(),
        benchmark_nav=benchmark_nav,
        mirror_nav=mirror_nav,
        equal_nav=equal_nav,
        alpha_nav=alpha_nav,
    )

    payload = captured["performance_nav.json"]
    last_date = max(r["date"] for r in payload["weekly"])
    assert last_date == str(dates[89].date()), (
        "export must truncate at the last REAL datapoint of the stalest "
        "series, not forward-fill a fabricated flat tail"
    )


def test_drawdowns_truncate_at_last_real_datapoint(captured: dict[str, Any]) -> None:
    dates = pd.bdate_range("2024-01-01", periods=100)
    benchmark_nav = _nav(dates, 0.0004, "sp500")
    mirror_nav = _nav(dates, 0.0005, "sp20_mirror")
    equal_nav = _nav(dates, 0.0005, "sp20_equal")
    alpha_nav = _nav(dates[:90], 0.0006, "spn_alpha")

    export.export_drawdowns(benchmark_nav, mirror_nav, equal_nav, alpha_nav=alpha_nav)

    payload = captured["drawdowns.json"]
    last_date = max(r["date"] for r in payload["weekly"])
    assert last_date == str(dates[89].date())


# ──────────────────────────────────────────────────────────────
# Matched-window comparison
#
# The per-strategy metric blocks each span that strategy's own history, so
# reading them as columns of one table is not apples-to-apples. These guard
# the block that fixes it — and, just as importantly, guard the significance
# flag against silently degenerating to a constant.
# ──────────────────────────────────────────────────────────────


def test_matched_window_starts_at_first_shared_date() -> None:
    """Baselines start earlier; the matched window must begin where all overlap."""
    dates = pd.bdate_range("2020-01-01", periods=800)
    navs = {
        "sp500": _nav(dates, 0.0004, "sp500"),
        "sp20_mirror": _nav(dates, 0.0005, "sp20_mirror"),
        "sp20_equal": _nav(dates, 0.0005, "sp20_equal"),
        # Walk-forward strategy only exists from day 300 onward.
        "spn_alpha": _nav(dates[300:], 0.0006, "spn_alpha"),
    }

    matched = export._matched_window_comparison(navs)

    assert matched["window"]["start"] == str(dates[300].date())
    assert matched["window"]["end"] == str(dates[-1].date())


def test_matched_window_reranks_total_return_fairly() -> None:
    """A shorter, faster-compounding series must not lose on total return.

    This is the exact defect the block exists to fix: measured over its own
    longer window a slower series can post a larger total return purely by
    having compounded for more years.
    """
    dates = pd.bdate_range("2020-01-01", periods=800)
    # 800 days at 6bps/day compounds to ~1.62x; 500 days at 9bps/day to ~1.57x.
    # The slower series leads on raw total return purely on window length.
    slow_long = _nav(dates, 0.0006, "sp20_mirror")
    fast_short = _nav(dates[300:], 0.0009, "spn_alpha")

    # Unmatched, the slower series wins on raw total return...
    assert slow_long.iloc[-1] / slow_long.iloc[0] > fast_short.iloc[-1] / fast_short.iloc[0]

    matched = export._matched_window_comparison(
        {
            "sp500": _nav(dates, 0.0004, "sp500"),
            "sp20_mirror": slow_long,
            "sp20_equal": _nav(dates, 0.0005, "sp20_equal"),
            "spn_alpha": fast_short,
        }
    )

    # ...but on the shared window the faster compounder is correctly ahead.
    assert (
        matched["metrics"]["spn_alpha"]["total_return"]
        > matched["metrics"]["sp20_mirror"]["total_return"]
    )


def test_matched_window_rebases_every_series_to_one() -> None:
    dates = pd.bdate_range("2020-01-01", periods=800)
    navs = {
        "sp500": _nav(dates, 0.0004, "sp500") * 7.0,  # arbitrary starting level
        "sp20_mirror": _nav(dates, 0.0005, "sp20_mirror"),
        "sp20_equal": _nav(dates, 0.0005, "sp20_equal"),
    }

    matched = export._matched_window_comparison(navs)

    # A pure scale factor must not change any return-based metric.
    assert matched["metrics"]["sp500"]["cagr"] == pytest.approx(
        (1.0004**252) - 1, rel=1e-3
    )


def test_matched_window_skipped_when_overlap_too_short() -> None:
    """Under a year of overlap, report nothing rather than a noisy comparison."""
    dates = pd.bdate_range("2024-01-01", periods=200)
    navs = {
        "sp500": _nav(dates, 0.0004, "sp500"),
        "sp20_mirror": _nav(dates, 0.0005, "sp20_mirror"),
        "sp20_equal": _nav(dates, 0.0005, "sp20_equal"),
    }

    assert export._matched_window_comparison(navs) == {}


def test_active_return_stats_rejects_noise_dominated_edge() -> None:
    """A small edge buried in noise must NOT clear the t > 3 hurdle."""
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2016-01-01", periods=2646)  # ~10.5y, as shipped
    bench_returns = rng.normal(0.0005, 0.011, len(dates))
    # +3bps/day of edge, swamped by 60bps/day of independent tracking noise.
    strat_returns = bench_returns + 0.00003 + rng.normal(0, 0.006, len(dates))

    benchmark = pd.Series(np.cumprod(1 + bench_returns), index=dates)
    strategy = pd.Series(np.cumprod(1 + strat_returns), index=dates)

    stats = export._active_return_stats(strategy, benchmark)

    assert not stats["significant"]
    assert abs(stats["t_stat"]) < 3.0
    assert stats["years_for_hurdle"] is None or stats["years_for_hurdle"] > 10.5


def test_active_return_stats_detects_a_genuine_edge() -> None:
    """Guard against the flag degenerating to a constant False."""
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2016-01-01", periods=2646)
    bench_returns = rng.normal(0.0005, 0.011, len(dates))
    # Same edge, but with an order of magnitude less tracking noise.
    strat_returns = bench_returns + 0.0004 + rng.normal(0, 0.0008, len(dates))

    benchmark = pd.Series(np.cumprod(1 + bench_returns), index=dates)
    strategy = pd.Series(np.cumprod(1 + strat_returns), index=dates)

    stats = export._active_return_stats(strategy, benchmark)

    assert stats["significant"]
    assert stats["t_stat"] > 3.0
    assert stats["years_for_hurdle"] is not None


def test_active_return_stats_needs_enough_overlap() -> None:
    dates = pd.bdate_range("2024-01-01", periods=20)
    series = _nav(dates, 0.0005, "a")
    assert export._active_return_stats(series, _nav(dates, 0.0004, "b")) == {}


def test_variance_decomposition_carries_replication_block(
    captured: dict[str, Any],
) -> None:
    rolling = pd.DataFrame({
        "n_stocks": [20, 20], "r_squared": [0.95, 0.96],
        "window_start": pd.to_datetime(["2020-01-01", "2020-02-01"]),
        "window_end": pd.to_datetime(["2020-12-31", "2021-01-31"]),
    })
    replication = {
        "method": "pit_investable_baskets_rolling",
        "window_days": 252, "step_days": 21,
        "ladder": {"investable_cap": 0.91, "investable_equal": 0.94},
        "by_n": [{"n": 20, "weighting": "equal", "tracking_error": 0.04,
                  "replication_r2": 0.94, "te_min": 0.03, "te_max": 0.06,
                  "n_windows": 100}],
    }
    export.export_variance_decomposition(rolling, replication=replication)

    payload = captured["variance_decomposition.json"]
    rep = payload["replication"]
    # export must stamp the OLS ceiling next to the investable numbers
    assert rep["ladder"]["ols_ceiling"] == pytest.approx(0.955)
    assert rep["ladder"]["investable_equal"] == 0.94
    assert rep["ladder"]["investable_equal"] <= rep["ladder"]["ols_ceiling"]


def test_variance_decomposition_replication_optional(
    captured: dict[str, Any],
) -> None:
    """Absent replication data must not break the existing export."""
    rolling = pd.DataFrame({
        "n_stocks": [20], "r_squared": [0.95],
        "window_start": pd.to_datetime(["2020-01-01"]),
        "window_end": pd.to_datetime(["2020-12-31"]),
    })
    export.export_variance_decomposition(rolling)
    assert "replication" not in captured["variance_decomposition.json"]
