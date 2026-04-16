"""Tests for src.optimizer.hrp and src.optimizer.mvo."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import MAX_POSITION_WEIGHT, MIN_POSITION_WEIGHT
from src.optimizer.hrp import hrp_weights
from src.optimizer.mvo import mvo_max_sharpe_weights, mvo_min_vol_weights
from src.strategies.alpha import make_alpha_weights_fn

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def train_prices() -> pd.DataFrame:
    """Generate ~3 years of synthetic training prices for 20 tickers."""
    np.random.seed(123)
    dates = pd.bdate_range("2018-01-01", periods=756)
    tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "META", "TSLA", "BRK-B", "AVGO", "LLY",
        "JPM", "V", "WMT", "UNH", "MA",
        "XOM", "COST", "HD", "PG", "JNJ",
    ]
    returns = np.random.normal(0.0004, 0.018, (756, 20))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ---------------------------------------------------------------------------
# HRP
# ---------------------------------------------------------------------------

class TestHRP:
    def test_weights_sum_to_one(self, train_prices: pd.DataFrame) -> None:
        w = hrp_weights(train_prices)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_respects_position_limits(self, train_prices: pd.DataFrame) -> None:
        w = hrp_weights(train_prices)
        active = w[w > 0]
        assert (active <= MAX_POSITION_WEIGHT + 1e-6).all()
        assert (active >= MIN_POSITION_WEIGHT - 1e-6).all()

    def test_returns_series(self, train_prices: pd.DataFrame) -> None:
        w = hrp_weights(train_prices)
        assert isinstance(w, pd.Series)
        assert set(w.index) == set(train_prices.columns)

    def test_fallback_on_insufficient_tickers(self) -> None:
        dates = pd.bdate_range("2020-01-01", periods=100)
        prices = pd.DataFrame({"A": np.random.randn(100).cumsum() + 100}, index=dates)
        w = hrp_weights(prices)
        assert abs(w.sum() - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# MVO
# ---------------------------------------------------------------------------

class TestMVO:
    def test_max_sharpe_sums_to_one(self, train_prices: pd.DataFrame) -> None:
        w = mvo_max_sharpe_weights(train_prices)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_min_vol_sums_to_one(self, train_prices: pd.DataFrame) -> None:
        w = mvo_min_vol_weights(train_prices)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_respects_position_limits(self, train_prices: pd.DataFrame) -> None:
        w = mvo_max_sharpe_weights(train_prices)
        assert (w <= MAX_POSITION_WEIGHT + 1e-6).all()
        assert (w >= MIN_POSITION_WEIGHT - 1e-6).all()

    def test_returns_series(self, train_prices: pd.DataFrame) -> None:
        w = mvo_min_vol_weights(train_prices)
        assert isinstance(w, pd.Series)


# ---------------------------------------------------------------------------
# Alpha strategy factory
# ---------------------------------------------------------------------------

class TestAlphaStrategy:
    def test_factory_returns_callable(self) -> None:
        fn = make_alpha_weights_fn(optimizer="hrp")
        assert callable(fn)

    def test_invalid_optimizer_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown optimizer"):
            make_alpha_weights_fn(optimizer="nonexistent")

    def test_weights_fn_interface(self, train_prices: pd.DataFrame) -> None:
        fn = make_alpha_weights_fn(optimizer="hrp")
        w = fn(train_prices, None)
        assert isinstance(w, pd.Series)
        assert abs(w.sum() - 1.0) < 1e-6
