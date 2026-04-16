"""Tests for src.features.sentiment."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.sentiment import (
    build_sentiment_features,
    compute_sentiment_proxy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sample_prices() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.bdate_range("2020-01-01", periods=200)
    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
    returns = np.random.normal(0.0005, 0.02, (200, 5))
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


# ---------------------------------------------------------------------------
# Sentiment proxy
# ---------------------------------------------------------------------------

class TestSentimentProxy:
    def test_output_shape(self) -> None:
        prices = _sample_prices()
        sentiment = compute_sentiment_proxy(prices)
        assert sentiment.shape == prices.shape

    def test_cross_sectional_standardised(self) -> None:
        """After cross-sectional z-scoring, each row should have ~zero mean."""
        prices = _sample_prices()
        sentiment = compute_sentiment_proxy(prices)
        valid = sentiment.dropna()
        row_means = valid.mean(axis=1)
        assert (row_means.abs() < 1e-10).all()

    def test_with_volume(self) -> None:
        prices = _sample_prices()
        np.random.seed(99)
        volumes = pd.DataFrame(
            np.random.randint(1_000_000, 10_000_000, prices.shape),
            index=prices.index,
            columns=prices.columns,
            dtype=float,
        )
        sentiment = compute_sentiment_proxy(prices, volumes)
        assert sentiment.shape == prices.shape
        valid = sentiment.dropna()
        assert len(valid) > 100


# ---------------------------------------------------------------------------
# Long-format features
# ---------------------------------------------------------------------------

class TestSentimentFeatures:
    def test_multiindex(self) -> None:
        prices = _sample_prices()
        features = build_sentiment_features(prices)
        assert features.index.names == ["date", "ticker"]
        assert "sentiment" in features.columns

    def test_all_tickers_present(self) -> None:
        prices = _sample_prices()
        features = build_sentiment_features(prices)
        tickers_in = set(features.index.get_level_values("ticker"))
        assert tickers_in == set(prices.columns)
