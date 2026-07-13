"""Tests for the data pipeline: fetcher, storage, and validation."""

from pathlib import Path

import pandas as pd
import pytest

from src.data import fetcher as fetcher_module
from src.data.fetcher import (
    DataQualityError,
    _validate_prices,
    fetch_daily_prices,
    fetch_incremental,
    prices_to_long_format,
)

# ──────────────────────────────────────────────
# Validation tests (unit — no network)
# ──────────────────────────────────────────────


class TestValidatePrices:
    """Unit tests for the _validate_prices function."""

    def _make_prices(self, tickers: list[str], n_rows: int = 100) -> pd.DataFrame:
        """Create a synthetic price DataFrame for testing."""
        import numpy as np

        dates = pd.bdate_range("2020-01-01", periods=n_rows)
        data = {
            t: 100.0 + i + np.cumsum(np.ones(n_rows) * 0.1)
            for i, t in enumerate(tickers)
        }
        return pd.DataFrame(data, index=dates)

    def test_valid_data_passes(self) -> None:
        df = self._make_prices(["AAPL", "MSFT"])
        result = _validate_prices(df, ["AAPL", "MSFT"])
        assert len(result) == 100
        assert list(result.columns) == ["AAPL", "MSFT"]

    def test_missing_ticker_warns_but_passes(self) -> None:
        df = self._make_prices(["AAPL"])
        result = _validate_prices(df, ["AAPL", "MISSING"])
        assert "AAPL" in result.columns
        assert "MISSING" not in result.columns

    def test_all_tickers_missing_raises(self) -> None:
        df = self._make_prices(["AAPL"])
        with pytest.raises(DataQualityError, match="No valid tickers"):
            _validate_prices(df, ["MISSING1", "MISSING2"])

    def test_small_nan_gaps_forward_filled(self) -> None:
        df = self._make_prices(["AAPL"], n_rows=50)
        df.iloc[10:13, 0] = float("nan")  # 3 consecutive NaNs
        result = _validate_prices(df, ["AAPL"])
        assert result["AAPL"].iloc[10:13].notna().all()

    def test_negative_prices_set_to_nan(self) -> None:
        df = self._make_prices(["AAPL"], n_rows=20)
        df.iloc[5, 0] = -10.0
        result = _validate_prices(df, ["AAPL"])
        # Negative price should have been removed
        assert (result["AAPL"].dropna() > 0).all()


# ──────────────────────────────────────────────
# Long format conversion
# ──────────────────────────────────────────────


class TestPricesToLongFormat:
    def test_conversion(self) -> None:
        dates = pd.bdate_range("2024-01-01", periods=5)
        wide = pd.DataFrame(
            {"AAPL": [150, 151, 152, 153, 154], "MSFT": [300, 301, 302, 303, 304]},
            index=dates,
        )
        wide.index.name = "date"
        long = prices_to_long_format(wide)

        assert set(long.columns) == {"date", "symbol", "close"}
        assert len(long) == 10
        assert set(long["symbol"].unique()) == {"AAPL", "MSFT"}


# ──────────────────────────────────────────────
# Incremental fetch: holiday/weekend gap handling
# ──────────────────────────────────────────────


class TestFetchIncremental:
    """fetch_incremental must not crash when a window spans only non-trading days.

    The T-1 fetch window self-corrects day to day, except on the trading day
    immediately after a weekday market holiday: the window then lands
    entirely on the holiday date and yfinance returns zero rows for every
    ticker. That is a calendar gap, not a fetch failure, and must not crash
    the daily cron. A genuine fetch failure (network, auth, rate limit) must
    still propagate.
    """

    def test_holiday_only_window_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_empty(**kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
            raise RuntimeError(
                "Failed to fetch data after 3 attempts: "
                "yfinance returned an empty DataFrame"
            )

        monkeypatch.setattr(
            fetcher_module, "fetch_daily_prices_and_volumes", _raise_empty
        )
        prices, volumes = fetch_incremental(tickers=["AAPL"], last_date="2025-12-31")
        assert prices.empty
        assert volumes.empty

    def test_genuine_fetch_failure_still_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_network(**kwargs: object) -> tuple[pd.DataFrame, pd.DataFrame]:
            raise RuntimeError(
                "Failed to fetch data after 3 attempts: Connection reset by peer"
            )

        monkeypatch.setattr(
            fetcher_module, "fetch_daily_prices_and_volumes", _raise_network
        )
        with pytest.raises(RuntimeError, match="Connection reset"):
            fetch_incremental(tickers=["AAPL"], last_date="2025-12-31")


# ──────────────────────────────────────────────
# Parquet round-trip
# ──────────────────────────────────────────────


class TestParquetStorage:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
        path = tmp_path / "test.parquet"
        df.to_parquet(path, index=False)
        loaded = pd.read_parquet(path)
        pd.testing.assert_frame_equal(df, loaded)


# ──────────────────────────────────────────────
# Integration test (requires network)
# ──────────────────────────────────────────────


@pytest.mark.slow
class TestFetchIntegration:
    """Integration tests that hit the yfinance API. Skip with: pytest -m 'not slow'"""

    def test_fetch_small_set(self) -> None:
        prices = fetch_daily_prices(
            tickers=["AAPL", "MSFT"],
            start="2024-01-01",
            end="2024-01-31",
        )
        assert not prices.empty
        assert "AAPL" in prices.columns
        assert "MSFT" in prices.columns
        assert len(prices) >= 15  # ~21 trading days in Jan
