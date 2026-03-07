"""Tests for the data pipeline: fetcher, storage, and validation."""

import pandas as pd
import pytest

from src.config import INCEPTION_DATE, TOP_50_TICKERS, DATA_DIR
from src.data.fetcher import (
    DataQualityError,
    _validate_prices,
    fetch_daily_prices,
    prices_to_long_format,
)
from src.data.storage import load_parquet, save_parquet


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
# Parquet round-trip
# ──────────────────────────────────────────────


class TestParquetStorage:
    def test_save_and_load_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
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
