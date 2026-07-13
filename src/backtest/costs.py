"""Turnover-based transaction cost model and drifting-portfolio simulator.

One implementation shared by the walk-forward engine and the mirror-index
builder. Semantics:

- Between rebalances the portfolio is buy-and-hold: weights drift with
  returns (``w_i ← w_i(1+r_i) / (1+r_p)``).
- At a rebalance, turnover = Σ|target − drifted| (buys + sells, ∈ [0, 2])
  and the cost ``turnover × (TRANSACTION_COST_BPS + SLIPPAGE_BPS)`` is
  deducted from that day's return. A full liquidate-and-reinvest
  (turnover = 2) therefore costs 14 bps — the "round-trip" in the config
  comment. The initial buy-in (turnover = 1) costs 7 bps once.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import SLIPPAGE_BPS, TRANSACTION_COST_BPS

TOTAL_COST_RATE = (TRANSACTION_COST_BPS + SLIPPAGE_BPS) / 1e4


def simulate_portfolio(
    returns: pd.DataFrame,
    rebalance_targets: dict[pd.Timestamp, pd.Series],
    cost_rate: float = TOTAL_COST_RATE,
) -> pd.DataFrame:
    """Simulate a drifting portfolio with turnover costs at rebalances.

    Weights decided at date *t* (using data through t's close) take effect
    on the first trading day strictly after *t*; the trade cost is charged
    against that day's return. Between rebalances the portfolio drifts.

    Args:
        returns: Wide daily returns (DatetimeIndex × tickers). NaN is
            treated as 0 (halted/absent name holds its weight).
        rebalance_targets: ``{decision_date: target_weights}``; weights are
            normalised to sum to 1. Tickers missing from ``returns`` are
            dropped before normalising.
        cost_rate: Cost per unit of one-way traded notional.

    Returns:
        DataFrame indexed by date from the first trade day through the last
        return date, columns ``gross_return, net_return, turnover, cost``
        (turnover/cost are nonzero only on trade days).

    Raises:
        ValueError: If no rebalance falls within the return index, or a
            target has no overlap with the return columns.
    """
    cols = returns.columns
    matrix = returns.fillna(0.0).to_numpy()
    dates = returns.index

    trade_by_day: dict[int, np.ndarray] = {}
    for decision_date, target in sorted(rebalance_targets.items()):
        day = int(dates.searchsorted(pd.Timestamp(decision_date), side="right"))
        if day >= len(dates):
            continue
        aligned = target.reindex(cols).fillna(0.0)
        total = float(aligned.sum())
        if total <= 0:
            raise ValueError(
                f"Rebalance target at {pd.Timestamp(decision_date).date()} has no "
                "overlap with return columns."
            )
        trade_by_day[day] = (aligned / total).to_numpy()

    if not trade_by_day:
        raise ValueError("No rebalance date falls within the return index.")

    first_day = min(trade_by_day)
    weights = np.zeros(len(cols))
    records: list[tuple[pd.Timestamp, float, float, float, float]] = []

    for i in range(first_day, len(dates)):
        target = trade_by_day.get(i)
        if target is not None:
            day_turnover = float(np.abs(target - weights).sum())
            day_cost = day_turnover * cost_rate
            weights = target.copy()
        else:
            day_turnover = 0.0
            day_cost = 0.0

        gross = float(matrix[i] @ weights)
        records.append((dates[i], gross, gross - day_cost, day_turnover, day_cost))

        # Drift: buy-and-hold until the next rebalance.
        grown = weights * (1.0 + matrix[i])
        total_value = grown.sum()
        if total_value > 0:
            weights = grown / total_value

    out = pd.DataFrame(
        records, columns=["date", "gross_return", "net_return", "turnover", "cost"]
    )
    return out.set_index("date")
