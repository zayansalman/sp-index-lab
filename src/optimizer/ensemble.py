"""Regime-weighted ensemble optimizer.

Blends HRP (risk-parity) and factor-driven MVO weights according to the
current market regime detected by the HMM.  In bull markets, the blend
tilts toward the factor model's return predictions; in bear markets, it
tilts toward the more stable HRP allocation.
"""

from __future__ import annotations

import logging

import pandas as pd
from pypfopt import EfficientFrontier, risk_models

from src.config import MAX_POSITION_WEIGHT, MIN_POSITION_WEIGHT
from src.optimizer.constraints import prune_and_renormalize
from src.optimizer.hrp import hrp_weights

logger = logging.getLogger(__name__)

# Default regime blend ratios: {regime_id: (factor_mvo_weight, hrp_weight)}
DEFAULT_REGIME_BLENDS: dict[int, tuple[float, float]] = {
    0: (0.7, 0.3),   # Bull  — lean on factor model
    1: (0.5, 0.5),   # Transition — balanced
    2: (0.2, 0.8),   # Bear  — lean on HRP (defensive)
}


def _factor_mvo_weights(
    train_prices: pd.DataFrame,
    predicted_returns: pd.Series,
) -> pd.Series:
    """Run MVO using LightGBM predicted returns as expected returns.

    Falls back to HRP if MVO fails.
    """
    tickers = train_prices.columns.tolist()

    try:
        mu = predicted_returns.reindex(tickers, fill_value=0.0)

        # Annualise the 21-day predicted returns
        mu_annual = mu * (252 / 21)

        cov = risk_models.CovarianceShrinkage(train_prices).ledoit_wolf()

        ef = EfficientFrontier(
            mu_annual,
            cov,
            weight_bounds=(MIN_POSITION_WEIGHT, MAX_POSITION_WEIGHT),
        )
        ef.max_sharpe(risk_free_rate=0.04)
        raw = ef.clean_weights()
        w = pd.Series(raw, dtype=float)
        total = w.sum()
        if total > 0:
            w = w / total
        return w

    except Exception:
        logger.warning("Factor-MVO failed — falling back to HRP.", exc_info=True)
        return hrp_weights(train_prices)


def ensemble_weights(
    train_prices: pd.DataFrame,
    regime: int,
    predicted_returns: pd.Series | None = None,
    regime_blends: dict[int, tuple[float, float]] | None = None,
) -> pd.Series:
    """Compute regime-weighted ensemble portfolio weights.

    Args:
        train_prices: Wide price DataFrame for the training window.
        regime: Current regime label (0=bull, 1=transition, 2=bear).
        predicted_returns: LightGBM predicted forward returns per ticker.
            If ``None``, uses pure HRP.
        regime_blends: Override blend ratios per regime.

    Returns:
        Portfolio weights indexed by ticker, summing to 1.0.
    """
    blends = regime_blends or DEFAULT_REGIME_BLENDS

    # Get blend ratio for the current regime (default to balanced)
    factor_w, hrp_w = blends.get(regime, (0.5, 0.5))

    # HRP weights (always computed — it's the stable backbone)
    w_hrp = hrp_weights(train_prices)

    if predicted_returns is not None and factor_w > 0:
        # Factor-MVO weights using predicted returns
        w_factor = _factor_mvo_weights(train_prices, predicted_returns)

        # Blend
        w = factor_w * w_factor + hrp_w * w_hrp
    else:
        w = w_hrp

    # Renormalise
    total = w.sum()
    if total > 0:
        w = w / total

    # Apply position constraints. prune_and_renormalize holds the 15% cap
    # through renormalisation (a plain clip-then-divide re-inflates past it).
    w = w.clip(lower=0.0)
    if (w > 0).sum() >= 2:
        w = prune_and_renormalize(w)

    logger.info(
        "Ensemble: regime=%d, blend=(%.0f%% factor, %.0f%% HRP), %d active positions",
        regime,
        factor_w * 100,
        hrp_w * 100,
        int((w > 0).sum()),
    )

    return w
