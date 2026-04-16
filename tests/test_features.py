"""Tests for src.features.technical."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.technical import (
    build_feature_matrix,
    compute_ma_distance,
    compute_momentum,
    compute_realized_vol,
    compute_rsi,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_prices() -> pd.DataFrame:
    """Generate 500 days of synthetic prices for 5 tickers."""
    np.random.seed(42)
    dates = pd.bdate_range("2020-01-01", periods=500)
    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
    # Random walk prices starting at 100
    returns = np.random.normal(0.0005, 0.02, (500, 5))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

class TestMomentum:
    def test_output_shape(self, sample_prices: pd.DataFrame) -> None:
        mom = compute_momentum(sample_prices, windows=[21, 63])
        # MultiIndex columns: 2 windows × 5 tickers = 10 columns
        assert mom.shape == (500, 10)
        assert len(mom.index) == 500

    def test_no_nan_after_warmup(self, sample_prices: pd.DataFrame) -> None:
        mom = compute_momentum(sample_prices, windows=[21])
        # After 21 rows, no NaN expected
        assert mom.iloc[21:].notna().all().all()


# ---------------------------------------------------------------------------
# Realized volatility
# ---------------------------------------------------------------------------

class TestRealizedVol:
    def test_output_shape(self, sample_prices: pd.DataFrame) -> None:
        vol = compute_realized_vol(sample_prices, window=21)
        assert vol.shape == sample_prices.shape

    def test_positive_after_warmup(self, sample_prices: pd.DataFrame) -> None:
        vol = compute_realized_vol(sample_prices, window=21)
        valid = vol.iloc[22:]  # after warmup
        assert (valid > 0).all().all()


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

class TestRSI:
    def test_bounded(self, sample_prices: pd.DataFrame) -> None:
        rsi = compute_rsi(sample_prices, window=14)
        valid = rsi.dropna()
        assert (valid >= 0).all().all()
        assert (valid <= 100).all().all()

    def test_output_shape(self, sample_prices: pd.DataFrame) -> None:
        rsi = compute_rsi(sample_prices, window=14)
        assert rsi.shape == sample_prices.shape


# ---------------------------------------------------------------------------
# MA distance
# ---------------------------------------------------------------------------

class TestMADistance:
    def test_output_shape(self, sample_prices: pd.DataFrame) -> None:
        ma = compute_ma_distance(sample_prices, windows=[50])
        assert ma.shape == (500, 5)  # 1 window × 5 tickers

    def test_zero_at_ma(self) -> None:
        """Constant price should have zero distance from MA."""
        dates = pd.bdate_range("2020-01-01", periods=100)
        prices = pd.DataFrame({"A": 100.0}, index=dates)
        ma = compute_ma_distance(prices, windows=[10])
        valid = ma.iloc[10:]
        assert np.allclose(valid.values, 0.0, atol=1e-10)


# ---------------------------------------------------------------------------
# Feature matrix
# ---------------------------------------------------------------------------

class TestFeatureMatrix:
    def test_multiindex(self, sample_prices: pd.DataFrame) -> None:
        fm = build_feature_matrix(sample_prices, momentum_windows=[21], ma_windows=[50])
        assert fm.index.names == ["date", "ticker"]

    def test_expected_columns(self, sample_prices: pd.DataFrame) -> None:
        fm = build_feature_matrix(
            sample_prices,
            momentum_windows=[21, 63],
            ma_windows=[50],
        )
        expected = {"mom_21", "mom_63", "vol_21", "rsi_14", "ma_dist_50"}
        assert expected == set(fm.columns)
