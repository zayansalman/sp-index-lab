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
