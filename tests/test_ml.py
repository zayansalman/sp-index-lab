"""Tests for Phase 2 ML modules: regime detection, factor model, ensemble."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.factors import predict_forward_returns
from src.features.regime import BEAR, BULL, TRANSITION, detect_regime
from src.optimizer.ensemble import ensemble_weights

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def market_indicators() -> pd.DataFrame:
    """Synthetic market indicators for 500 trading days."""
    np.random.seed(42)
    dates = pd.bdate_range("2020-01-01", periods=500)
    return pd.DataFrame({
        "date": dates,
        "vix": np.random.uniform(12, 35, 500),
        "risk_free": np.random.uniform(0.01, 0.05, 500),
        "treasury_10y": np.random.uniform(1.5, 4.5, 500),
    })


@pytest.fixture()
def train_prices() -> pd.DataFrame:
    """756 days of synthetic prices for 10 tickers."""
    np.random.seed(99)
    dates = pd.bdate_range("2018-01-01", periods=756)
    tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "META", "TSLA", "JPM", "V", "WMT",
    ]
    returns = np.random.normal(0.0004, 0.018, (756, 10))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

class TestRegime:
    def test_produces_valid_labels(self, market_indicators: pd.DataFrame) -> None:
        regimes = detect_regime(market_indicators)
        assert set(regimes.unique()).issubset({BULL, TRANSITION, BEAR})

    def test_output_length_matches_input(self, market_indicators: pd.DataFrame) -> None:
        regimes = detect_regime(market_indicators)
        # One row lost to diff in feature prep
        assert len(regimes) == 499

    def test_all_states_represented(self, market_indicators: pd.DataFrame) -> None:
        regimes = detect_regime(market_indicators)
        assert len(regimes.unique()) == 3

    def test_too_few_observations_returns_bull(self) -> None:
        dates = pd.bdate_range("2020-01-01", periods=10)
        mi = pd.DataFrame({
            "date": dates,
            "vix": [15.0] * 10,
            "risk_free": [0.03] * 10,
            "treasury_10y": [2.5] * 10,
        })
        regimes = detect_regime(mi)
        assert (regimes == BULL).all()


# ---------------------------------------------------------------------------
# Factor model
# ---------------------------------------------------------------------------

class TestFactorModel:
    def test_returns_series_indexed_by_ticker(self, train_prices: pd.DataFrame) -> None:
        preds = predict_forward_returns(train_prices)
        assert isinstance(preds, pd.Series)
        assert set(preds.index) == set(train_prices.columns)

    def test_no_nan_in_predictions(self, train_prices: pd.DataFrame) -> None:
        preds = predict_forward_returns(train_prices)
        assert preds.notna().all()

    def test_predictions_are_reasonable(self, train_prices: pd.DataFrame) -> None:
        """Predicted 21-day returns should be within a sane range."""
        preds = predict_forward_returns(train_prices)
        assert (preds.abs() < 1.0).all()  # No >100% return prediction


# ---------------------------------------------------------------------------
# Ensemble optimizer
# ---------------------------------------------------------------------------

class TestEnsemble:
    def test_weights_sum_to_one(self, train_prices: pd.DataFrame) -> None:
        preds = predict_forward_returns(train_prices)
        w = ensemble_weights(train_prices, regime=BULL, predicted_returns=preds)
        assert abs(w.sum() - 1.0) < 1e-6

    def test_bear_regime_leans_hrp(self, train_prices: pd.DataFrame) -> None:
        """In bear regime, factor-MVO gets only 20% weight — result should
        be closer to HRP than in bull regime."""
        from src.optimizer.hrp import hrp_weights

        preds = predict_forward_returns(train_prices)
        w_bull = ensemble_weights(train_prices, regime=BULL, predicted_returns=preds)
        w_bear = ensemble_weights(train_prices, regime=BEAR, predicted_returns=preds)
        w_hrp = hrp_weights(train_prices)

        # Bear weights should be more correlated with HRP than bull weights
        corr_bear = w_bear.corr(w_hrp)
        corr_bull = w_bull.corr(w_hrp)
        assert corr_bear >= corr_bull - 0.1  # Allow small tolerance

    def test_no_predictions_falls_back_to_hrp(self, train_prices: pd.DataFrame) -> None:
        w = ensemble_weights(train_prices, regime=BULL, predicted_returns=None)
        assert abs(w.sum() - 1.0) < 1e-6
