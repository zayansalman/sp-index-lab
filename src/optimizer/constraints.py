"""Shared position-constraint helper for portfolio optimizers.

Both MVO and HRP must respect the same bounds: drop dust below
``MIN_POSITION_WEIGHT``, cap each name at ``MAX_POSITION_WEIGHT``, and sum to
1.0. The subtlety is that re-normalising after dropping names can push a
surviving name back above the cap — a naive ``clip(upper=cap) / sum`` does
NOT hold the cap (it re-inflates), which is why this redistributes excess
across uncapped names instead.
"""

from __future__ import annotations

import pandas as pd

from src.config import MAX_POSITION_WEIGHT, MIN_POSITION_WEIGHT


def prune_and_renormalize(
    weights: pd.Series,
    min_weight: float = MIN_POSITION_WEIGHT,
    max_weight: float = MAX_POSITION_WEIGHT,
    max_iterations: int = 10,
) -> pd.Series:
    """Drop dust positions and re-normalise without breaching the cap.

    Positions below ``min_weight`` are removed entirely (an optimizer may
    exit a name), then weights re-normalise to 1.0. Renormalisation can push
    a name above ``max_weight``, so excess is clipped and redistributed
    proportionally across uncapped names until no violation remains.

    Args:
        weights: Raw weights (may contain zeros / dust).
        min_weight: Positions strictly below this are dropped.
        max_weight: Hard per-position cap preserved through renormalisation.
        max_iterations: Safety bound on clip-redistribute passes.

    Returns:
        Weights summing to 1.0, each in [min_weight, max_weight] — or the
        input normalised unchanged if pruning would empty the portfolio.
    """
    kept = weights[weights >= min_weight]
    if kept.empty or kept.sum() <= 0:
        total = weights.sum()
        return weights / total if total > 0 else weights

    w = kept / kept.sum()
    for _ in range(max_iterations):
        over = w > max_weight
        if not over.any():
            break
        excess = (w[over] - max_weight).sum()
        w.loc[over] = max_weight
        under = ~over
        if not under.any() or w[under].sum() <= 0:
            break
        w.loc[under] += excess * w[under] / w[under].sum()
    return w
