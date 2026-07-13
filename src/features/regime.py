"""Regime detection via Hidden Markov Model.

Uses a 3-state Gaussian HMM fitted on VIX level, VIX change, and the
term-structure spread (10Y Treasury − risk-free rate).  States are labelled
bull / transition / bear by sorting on mean VIX level per state.
"""

from __future__ import annotations

import logging
import warnings

import pandas as pd
from hmmlearn.hmm import GaussianHMM

logger = logging.getLogger(__name__)

# Regime labels (assigned after fitting by VIX ordering)
BULL = 0
TRANSITION = 1
BEAR = 2
REGIME_LABELS = {BULL: "bull", TRANSITION: "transition", BEAR: "bear"}


def _prepare_features(market_indicators: pd.DataFrame) -> pd.DataFrame:
    """Build HMM feature matrix from raw market indicators.

    Features:
        1. VIX level (standardised)
        2. VIX daily change
        3. Yield spread: 10Y Treasury − risk-free rate

    Args:
        market_indicators: DataFrame with columns ``vix``, ``risk_free``,
            ``treasury_10y`` and a ``date`` column or DatetimeIndex.

    Returns:
        DataFrame indexed by date with columns ``vix_level``, ``vix_change``,
        ``yield_spread``.
    """
    df = market_indicators.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

    features = pd.DataFrame(index=df.index)
    features["vix_level"] = df["vix"]
    features["vix_change"] = df["vix"].diff()
    features["yield_spread"] = df["treasury_10y"] - df["risk_free"]

    return features.dropna()


def detect_regime(
    market_indicators: pd.DataFrame,
    n_states: int = 3,
    random_state: int = 42,
) -> pd.Series:
    """Fit a Gaussian HMM and return regime labels aligned to dates.

    Args:
        market_indicators: DataFrame with ``vix``, ``risk_free``,
            ``treasury_10y`` columns (and ``date`` column or DatetimeIndex).
        n_states: Number of hidden states (default 3).
        random_state: Seed for reproducibility.

    Returns:
        Series of regime labels (0=bull, 1=transition, 2=bear) indexed by date.
    """
    features = _prepare_features(market_indicators)

    if len(features) < 50:
        logger.warning("Too few observations (%d) for HMM — defaulting to bull.", len(features))
        return pd.Series(BULL, index=features.index, name="regime")

    # Standardise features for numerical stability
    means = features.mean()
    stds = features.std().replace(0, 1)
    x_scaled = ((features - means) / stds).values

    # Fit HMM
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # hmmlearn convergence warnings
        model = GaussianHMM(
            n_components=n_states,
            covariance_type="full",
            n_iter=200,
            random_state=random_state,
        )
        model.fit(x_scaled)
        raw_states = model.predict(x_scaled)

    # Map raw states to bull/transition/bear by mean VIX per state
    state_vix_means: dict[int, float] = {}
    for s in range(n_states):
        mask = raw_states == s
        if mask.any():
            state_vix_means[s] = float(features["vix_level"].values[mask].mean())
        else:
            state_vix_means[s] = 0.0

    # Sort states by VIX: lowest VIX = bull, highest = bear
    sorted_states = sorted(state_vix_means, key=lambda s: state_vix_means[s])
    state_map = {raw: label for label, raw in enumerate(sorted_states)}

    regimes = pd.Series(
        [state_map[s] for s in raw_states],
        index=features.index,
        name="regime",
        dtype=int,
    )

    # Log regime distribution
    for label_id, label_name in REGIME_LABELS.items():
        count = int((regimes == label_id).sum())
        pct = count / len(regimes) * 100
        mean_vix = float(features["vix_level"][regimes == label_id].mean()) if count > 0 else 0
        logger.info(
            "  Regime %d (%s): %d days (%.1f%%), mean VIX=%.1f",
            label_id, label_name, count, pct, mean_vix,
        )

    return regimes
