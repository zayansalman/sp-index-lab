"""Tests for src.optimizer.hrp and src.optimizer.mvo."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import MAX_POSITION_WEIGHT, MIN_POSITION_WEIGHT
from src.optimizer.hrp import hrp_weights
from src.optimizer.mvo import (
    mvo_max_sharpe_weights,
    mvo_min_vol_weights,
    prune_and_renormalize,
)
from src.strategies.alpha import make_alpha_weights_fn, trailing_risk_free

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


# ---------------------------------------------------------------------------
# Pruning / renormalisation
# ---------------------------------------------------------------------------

class TestPruneAndRenormalize:
    def test_drops_dust_and_sums_to_one(self) -> None:
        w = pd.Series({"A": 0.5, "B": 0.495, "C": 0.005})
        pruned = prune_and_renormalize(w, min_weight=0.01, max_weight=0.6)
        assert "C" not in pruned.index
        assert abs(pruned.sum() - 1.0) < 1e-9

    def test_cap_survives_renormalisation(self) -> None:
        # After dropping dust, renormalisation would push A above the cap —
        # the excess must redistribute, not breach it.
        w = pd.Series({"A": 0.15, "B": 0.14, "C": 0.68, "D": 0.03})
        pruned = prune_and_renormalize(w, min_weight=0.05, max_weight=0.70)
        assert abs(pruned.sum() - 1.0) < 1e-9
        assert (pruned <= 0.70 + 1e-9).all()
        assert "D" not in pruned.index

    def test_all_dust_returns_normalised_input(self) -> None:
        w = pd.Series({"A": 0.004, "B": 0.006})
        pruned = prune_and_renormalize(w, min_weight=0.01, max_weight=0.15)
        assert abs(pruned.sum() - 1.0) < 1e-9
        assert set(pruned.index) == {"A", "B"}


# ---------------------------------------------------------------------------
# Fallback surfacing + risk-free feed
# ---------------------------------------------------------------------------

class TestFallbackAndRiskFree:
    def test_fallback_flagged_via_attrs(self) -> None:
        # Constant prices → zero expected returns below the risk-free rate →
        # max_sharpe raises → equal-weight fallback, flagged in attrs.
        dates = pd.bdate_range("2020-01-01", periods=300)
        prices = pd.DataFrame(
            {"A": np.full(300, 100.0), "B": np.full(300, 50.0)}, index=dates
        )
        w = mvo_max_sharpe_weights(prices)
        assert w.attrs.get("fallback") is True
        assert abs(w.sum() - 1.0) < 1e-9

    def test_solved_weights_not_flagged(self, train_prices: pd.DataFrame) -> None:
        w = mvo_max_sharpe_weights(train_prices)
        assert not w.attrs.get("fallback", False)

    def test_trailing_risk_free_units_and_slicing(self) -> None:
        mi = pd.DataFrame({
            "date": pd.bdate_range("2024-01-01", periods=50),
            "risk_free": [4.0] * 40 + [99.0] * 10,  # spike after as_of
        })
        rf = trailing_risk_free(mi, mi["date"].iloc[39], window=21)
        assert rf is not None
        assert abs(rf - 0.04) < 1e-9  # percent → decimal; spike excluded

    def test_trailing_risk_free_none_when_unavailable(self) -> None:
        assert trailing_risk_free(None, pd.Timestamp("2024-01-01")) is None
        mi = pd.DataFrame({
            "date": pd.bdate_range("2024-06-01", periods=5),
            "risk_free": [4.0] * 5,
        })
        assert trailing_risk_free(mi, pd.Timestamp("2024-01-01")) is None
