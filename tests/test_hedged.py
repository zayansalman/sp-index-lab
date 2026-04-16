"""Tests for Phase 4: beta calculator, cash utility, hedged strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.beta import compute_portfolio_beta, compute_stock_betas
from src.strategies.hedged import _apply_defensive_tilt
from src.utils.helpers import add_cash_column

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sample_prices(n_days: int = 500, n_tickers: int = 10) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "META", "TSLA", "JPM", "V", "WMT",
    ][:n_tickers]
    returns = np.random.normal(0.0004, 0.018, (n_days, n_tickers))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


def _sample_benchmark(n_days: int = 500) -> pd.Series:
    np.random.seed(99)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    returns = np.random.normal(0.0003, 0.012, n_days)
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=dates, name="sp500")


# ---------------------------------------------------------------------------
# Beta calculator
# ---------------------------------------------------------------------------

class TestBeta:
    def test_stock_betas_shape(self) -> None:
        prices = _sample_prices()
        bench = _sample_benchmark()
        betas = compute_stock_betas(prices, bench, window=63)
        assert betas.shape == prices.shape

    def test_portfolio_beta_scalar(self) -> None:
        prices = _sample_prices()
        bench = _sample_benchmark()
        weights = pd.Series(0.1, index=prices.columns)
        beta = compute_portfolio_beta(prices, bench, weights, window=63)
        assert isinstance(beta, float)
        # Beta should be in a reasonable range
        assert -2.0 < beta < 5.0

    def test_equal_weights_beta_finite(self) -> None:
        """With random data, equal-weighted portfolio beta should be finite."""
        prices = _sample_prices()
        bench = _sample_benchmark()
        weights = pd.Series(1.0 / len(prices.columns), index=prices.columns)
        beta = compute_portfolio_beta(prices, bench, weights)
        # With independent random data, beta can be near zero or slightly negative
        assert -3.0 < beta < 5.0


# ---------------------------------------------------------------------------
# Cash utility
# ---------------------------------------------------------------------------

class TestCashColumn:
    def test_adds_cash_column(self) -> None:
        prices = _sample_prices(n_days=100, n_tickers=3)
        result = add_cash_column(prices)
        assert "CASH" in result.columns
        assert len(result.columns) == 4  # 3 tickers + CASH

    def test_cash_monotonically_increasing(self) -> None:
        prices = _sample_prices(n_days=100, n_tickers=3)
        result = add_cash_column(prices, risk_free_rate=0.04)
        cash = result["CASH"]
        assert (cash.diff().dropna() > 0).all()

    def test_cash_starts_at_100(self) -> None:
        prices = _sample_prices(n_days=100, n_tickers=3)
        result = add_cash_column(prices)
        assert result["CASH"].iloc[0] == 100.0

    def test_original_prices_unchanged(self) -> None:
        prices = _sample_prices(n_days=100, n_tickers=3)
        original_cols = list(prices.columns)
        _ = add_cash_column(prices)
        assert list(prices.columns) == original_cols  # No mutation


# ---------------------------------------------------------------------------
# Defensive tilt
# ---------------------------------------------------------------------------

class TestDefensiveTilt:
    def test_no_tilt_in_bull(self) -> None:
        weights = pd.Series(0.1, index=["A", "B", "C", "D", "E"])
        betas = pd.Series([1.5, 1.2, 0.8, 0.5, 1.0], index=["A", "B", "C", "D", "E"])
        tilted = _apply_defensive_tilt(weights, betas, regime=0)
        assert (tilted == weights).all()

    def test_bear_tilts_toward_low_beta(self) -> None:
        weights = pd.Series(0.2, index=["HIGH", "LOW"])
        betas = pd.Series([2.0, 0.5], index=["HIGH", "LOW"])
        tilted = _apply_defensive_tilt(weights, betas, regime=2, tilt_strength=0.5)
        # Low-beta stock should get higher weight after tilt
        assert tilted["LOW"] > tilted["HIGH"]

    def test_tilted_weights_sum_to_one(self) -> None:
        weights = pd.Series([0.3, 0.2, 0.3, 0.2], index=["A", "B", "C", "D"])
        betas = pd.Series([1.5, 0.5, 1.2, 0.8], index=["A", "B", "C", "D"])
        tilted = _apply_defensive_tilt(weights, betas, regime=2)
        assert abs(tilted.sum() - 1.0) < 1e-6
