"""Sentiment feature for the factor model.

Two modes:
  - **Backtest proxy**: Computes a sentiment-like score from abnormal volume
    and short-term momentum.  No external API calls — suitable for historical
    walk-forward backtesting.
  - **Live mode**: Calls HuggingFace Inference API with FinBERT to score
    real news headlines per ticker.  Requires ``HF_TOKEN`` environment variable.

The proxy is designed to correlate with real sentiment: high abnormal volume
+ negative short-term return → bearish; high abnormal volume + positive
short-term return → bullish.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
import pandas as pd

from src.config import DATA_DIR

logger = logging.getLogger(__name__)

# HuggingFace model for live sentiment
HF_MODEL_SENTIMENT = "ProsusAI/finbert"
SENTIMENT_CACHE_FILE = DATA_DIR / "sentiment_cache.parquet"


# ---------------------------------------------------------------------------
# Backtest proxy sentiment
# ---------------------------------------------------------------------------

def compute_sentiment_proxy(
    prices: pd.DataFrame,
    volumes: pd.DataFrame | None = None,
    momentum_window: int = 5,
    vol_window: int = 21,
) -> pd.DataFrame:
    """Compute a sentiment proxy from price action and volume.

    The proxy combines:
    1. Short-term momentum (5-day return) — captures directional sentiment
    2. Abnormal volume ratio (current / 21-day MA) — captures attention/conviction
    3. Return acceleration (5-day mom minus 21-day mom) — captures sentiment shifts

    The composite is standardised cross-sectionally per date to produce a
    z-score-like sentiment signal in approximately [-3, +3].

    Args:
        prices: Wide price DataFrame (DatetimeIndex × tickers).
        volumes: Optional volume DataFrame.  If ``None``, only price-based
            signals are used.
        momentum_window: Short-term momentum lookback (default 5 days).
        vol_window: Volume normalisation window (default 21 days).

    Returns:
        DataFrame of sentiment proxy scores (same shape as *prices*), where
        positive = bullish, negative = bearish.
    """
    # Short-term momentum (5-day return)
    short_mom = prices.pct_change(periods=momentum_window)

    # Medium-term momentum (21-day return)
    med_mom = prices.pct_change(periods=vol_window)

    # Momentum acceleration (sentiment shift)
    mom_accel = short_mom - med_mom

    # Combine signals
    if volumes is not None and not volumes.empty:
        # Abnormal volume ratio
        avg_vol = volumes.rolling(vol_window).mean()
        abnormal_vol = volumes / avg_vol.replace(0, np.nan) - 1.0

        # Sign the volume by price direction (bullish volume vs bearish volume)
        signed_vol = abnormal_vol * np.sign(short_mom)

        # Composite: equal weight of momentum, acceleration, signed volume
        raw = (short_mom + mom_accel + signed_vol) / 3.0
    else:
        # Price-only proxy
        raw = (short_mom + mom_accel) / 2.0

    # Cross-sectional standardisation (z-score per date)
    row_mean = raw.mean(axis=1)
    row_std = raw.std(axis=1).replace(0, 1)
    sentiment = raw.sub(row_mean, axis=0).div(row_std, axis=0)

    return sentiment


def build_sentiment_features(
    prices: pd.DataFrame,
    volumes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build sentiment features in long format for the factor model.

    Returns:
        DataFrame indexed by ``(date, ticker)`` with a single column
        ``sentiment``.
    """
    proxy = compute_sentiment_proxy(prices, volumes)

    records: list[pd.DataFrame] = []
    for ticker in proxy.columns:
        s = proxy[ticker].rename("sentiment").to_frame()
        s["ticker"] = ticker
        s.index.name = "date"
        records.append(s.reset_index().set_index(["date", "ticker"]))

    return pd.concat(records).sort_index()


# ---------------------------------------------------------------------------
# Live sentiment via HuggingFace FinBERT
# ---------------------------------------------------------------------------

def _get_hf_token() -> str | None:
    """Read HF_TOKEN from environment."""
    return os.environ.get("HF_TOKEN")


def score_headlines_finbert(
    headlines: list[str],
    hf_token: str | None = None,
) -> list[dict[str, Any]]:
    """Score a batch of headlines using FinBERT via HuggingFace Inference API.

    Args:
        headlines: List of news headline strings.
        hf_token: HuggingFace API token.  Falls back to ``HF_TOKEN`` env var.

    Returns:
        List of dicts with keys ``positive``, ``negative``, ``neutral``
        (probabilities) and ``sentiment_score`` (positive − negative).
    """
    token = hf_token or _get_hf_token()
    if not token:
        logger.warning("No HF_TOKEN found — cannot run FinBERT.")
        return [{"positive": 0.33, "negative": 0.33, "neutral": 0.34, "sentiment_score": 0.0}
                for _ in headlines]

    try:
        from huggingface_hub import InferenceClient

        client = InferenceClient(model=HF_MODEL_SENTIMENT, token=token)
        results: list[dict[str, Any]] = []

        for headline in headlines:
            output = client.text_classification(headline)

            # Parse FinBERT output: list of {label, score} dicts
            probs: dict[str, float] = {}
            for item in output:
                probs[item.label.lower()] = item.score

            results.append({
                "positive": probs.get("positive", 0.0),
                "negative": probs.get("negative", 0.0),
                "neutral": probs.get("neutral", 0.0),
                "sentiment_score": probs.get("positive", 0.0) - probs.get("negative", 0.0),
            })

        return results

    except Exception:
        logger.warning("FinBERT inference failed.", exc_info=True)
        return [{"positive": 0.33, "negative": 0.33, "neutral": 0.34, "sentiment_score": 0.0}
                for _ in headlines]


def score_ticker_sentiment(
    ticker: str,
    headlines: list[str],
    hf_token: str | None = None,
) -> float:
    """Aggregate sentiment score for a single ticker from multiple headlines.

    Args:
        ticker: Stock ticker symbol.
        headlines: News headlines related to this ticker.
        hf_token: HuggingFace API token.

    Returns:
        Aggregate sentiment score in [-1, +1].  Positive = bullish.
    """
    if not headlines:
        return 0.0

    scores = score_headlines_finbert(headlines, hf_token)
    sentiment_scores = [s["sentiment_score"] for s in scores]
    return float(np.mean(sentiment_scores))
