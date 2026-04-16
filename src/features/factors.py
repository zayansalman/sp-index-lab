"""LightGBM cross-sectional factor model for forward return prediction.

Trains a single LightGBM regressor on pooled (date, ticker) observations
to predict 21-day forward returns from technical features.  Used by the
ensemble optimizer to generate expected-return inputs for MVO.
"""

from __future__ import annotations

import logging

import lightgbm as lgb
import pandas as pd

from src.features.sentiment import build_sentiment_features
from src.features.technical import build_feature_matrix

logger = logging.getLogger(__name__)

# Defaults — overridden by config in Phase 2.5
_FORWARD_DAYS = 21
_N_ESTIMATORS = 100
_MAX_DEPTH = 5
_LEARNING_RATE = 0.05


def _build_targets(
    prices: pd.DataFrame,
    forward_days: int = _FORWARD_DAYS,
) -> pd.DataFrame:
    """Compute forward N-day returns for each ticker (long format).

    Returns:
        DataFrame indexed by ``(date, ticker)`` with a single column
        ``forward_return``.
    """
    fwd = prices.pct_change(periods=forward_days).shift(-forward_days)

    records: list[pd.DataFrame] = []
    for ticker in prices.columns:
        s = fwd[ticker].rename("forward_return").to_frame()
        s["ticker"] = ticker
        s.index.name = "date"
        records.append(s.reset_index().set_index(["date", "ticker"]))

    return pd.concat(records).sort_index()


def predict_forward_returns(
    train_prices: pd.DataFrame,
    forward_days: int = _FORWARD_DAYS,
    include_sentiment: bool = True,
) -> pd.Series:
    """Train LightGBM on historical features and predict latest forward returns.

    The model is trained on all (date, ticker) rows where both features and
    targets are available.  It then predicts the forward return for each ticker
    at the **latest available date** in the training window.

    Args:
        train_prices: Wide price DataFrame for the training window only.
        forward_days: Prediction horizon in trading days.
        include_sentiment: Whether to include sentiment proxy features.

    Returns:
        Series of predicted forward returns indexed by ticker.  If training
        fails (e.g. insufficient data), returns equal predictions (zeros).
    """
    tickers = train_prices.columns.tolist()

    # Build features (long format, indexed by (date, ticker))
    features = build_feature_matrix(train_prices)

    # Add sentiment proxy feature
    if include_sentiment:
        sentiment = build_sentiment_features(train_prices)
        features = features.join(sentiment, how="left")
        features["sentiment"] = features["sentiment"].fillna(0.0)

    # Build targets
    targets = _build_targets(train_prices, forward_days)

    # Join features and targets
    combined = features.join(targets, how="inner").dropna()

    if len(combined) < 100:
        logger.warning(
            "Factor model: only %d training rows — returning zero predictions.",
            len(combined),
        )
        return pd.Series(0.0, index=tickers, name="predicted_return")

    x_train = combined.drop(columns=["forward_return"])
    y = combined["forward_return"]

    # Train LightGBM
    model = lgb.LGBMRegressor(
        n_estimators=_N_ESTIMATORS,
        max_depth=_MAX_DEPTH,
        learning_rate=_LEARNING_RATE,
        subsample=0.8,
        colsample_bytree=0.8,
        verbose=-1,
    )
    model.fit(x_train, y)

    # Predict at the latest date for each ticker
    latest_date = features.index.get_level_values("date").max()
    latest_features = features.loc[latest_date]

    # Ensure all tickers are present
    available_tickers = latest_features.index.get_level_values("ticker") if hasattr(
        latest_features.index, "get_level_values"
    ) else latest_features.index

    predictions = pd.Series(
        model.predict(latest_features),
        index=available_tickers,
        name="predicted_return",
    )

    # Reindex to full ticker list
    predictions = predictions.reindex(tickers, fill_value=0.0)

    logger.info(
        "Factor model: trained on %d rows, predicted %d tickers (range %.4f to %.4f)",
        len(combined),
        len(predictions),
        predictions.min(),
        predictions.max(),
    )

    return predictions
