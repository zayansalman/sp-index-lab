"""Matched-window strategy scoring.

Every published or compared number must be computed on the *identical* date
window, net of costs, against the same references. v1's headline compared a
9-year strategy CAGR to a 12-year benchmark CAGR — this module makes that
class of error structurally impossible: align first, then measure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.backtest.metrics import compute_performance_metrics
from src.config import TRADING_DAYS_PER_YEAR


@dataclass
class StrategyScore:
    """Net-of-cost performance of one strategy on a matched window."""

    name: str
    window_start: str
    window_end: str
    n_days: int
    cagr: float
    ann_vol: float
    sharpe: float
    sortino: float
    max_drawdown: float
    ann_turnover: float
    cost_drag_bps: float
    # Relative to each reference (keyed by reference name):
    excess_cagr: dict[str, float] = field(default_factory=dict)
    excess_t_stat: dict[str, float] = field(default_factory=dict)
    beats: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """JSON-serialisable view for the trials registry."""
        return {
            "name": self.name,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "n_days": self.n_days,
            "cagr": self.cagr,
            "ann_vol": self.ann_vol,
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "max_drawdown": self.max_drawdown,
            "ann_turnover": self.ann_turnover,
            "cost_drag_bps": self.cost_drag_bps,
            "excess_cagr": self.excess_cagr,
            "excess_t_stat": self.excess_t_stat,
            "beats": self.beats,
        }


def _monthly_excess_t_stat(nav: pd.Series, ref_nav: pd.Series) -> float:
    """t-stat of monthly excess returns (monthly to tame autocorrelation)."""
    common = nav.index.intersection(ref_nav.index)
    if len(common) < 3:
        return 0.0
    m_strat = nav.loc[common].resample("ME").last().pct_change().dropna()
    m_ref = ref_nav.loc[common].resample("ME").last().pct_change().dropna()
    idx = m_strat.index.intersection(m_ref.index)
    excess = (m_strat.loc[idx] - m_ref.loc[idx]).dropna()
    if len(excess) < 3 or excess.std(ddof=1) == 0:
        return 0.0
    return float(excess.mean() / excess.std(ddof=1) * np.sqrt(len(excess)))


def score_strategy(
    name: str,
    nav: pd.Series,
    references: dict[str, pd.Series],
    *,
    turnover: pd.Series | None = None,
    costs: pd.Series | None = None,
    risk_free_rate: float = 0.04,
) -> StrategyScore:
    """Score a strategy NAV on the window it shares with all references.

    All series are intersected to a common date range and renormalised to
    1.0 at that shared start, so CAGR/Sharpe are strictly comparable. Excess
    CAGR and a monthly excess-return t-stat are reported against each
    reference.

    Args:
        name: Strategy label.
        nav: Net-of-cost NAV series (DatetimeIndex).
        references: ``{ref_name: ref_nav}`` (e.g. sp500, sp20_equal).
        turnover: Optional per-rebalance turnover for the annualised figure.
        costs: Optional per-rebalance cost fractions for total drag.
        risk_free_rate: Annual rate for Sharpe/Sortino.

    Returns:
        A :class:`StrategyScore`.
    """
    common = nav.dropna().index
    for ref in references.values():
        common = common.intersection(ref.dropna().index)
    if len(common) < 2:
        raise ValueError(f"{name}: <2 common dates across strategy and references.")

    window = nav.loc[common]
    window = window / window.iloc[0]
    metrics = compute_performance_metrics(window, risk_free_rate=risk_free_rate)

    n_years = len(common) / TRADING_DAYS_PER_YEAR
    ann_turnover = float(turnover.sum() / n_years) if turnover is not None and n_years > 0 else 0.0
    cost_drag_bps = float(costs.sum() * 1e4) if costs is not None else 0.0

    excess_cagr: dict[str, float] = {}
    excess_t: dict[str, float] = {}
    beats: dict[str, bool] = {}
    for ref_name, ref_nav in references.items():
        ref_window = ref_nav.loc[common]
        ref_window = ref_window / ref_window.iloc[0]
        ref_cagr = compute_performance_metrics(ref_window)["cagr"]
        excess_cagr[ref_name] = float(metrics["cagr"] - ref_cagr)
        excess_t[ref_name] = _monthly_excess_t_stat(window, ref_window)
        ref_sharpe = compute_performance_metrics(
            ref_window, risk_free_rate=risk_free_rate
        )["sharpe_ratio"]
        beats[ref_name] = bool(
            metrics["cagr"] > ref_cagr and metrics["sharpe_ratio"] > ref_sharpe
        )

    return StrategyScore(
        name=name,
        window_start=str(common[0].date()),
        window_end=str(common[-1].date()),
        n_days=len(common),
        cagr=float(metrics["cagr"]),
        ann_vol=float(metrics["annualised_volatility"]),
        sharpe=float(metrics["sharpe_ratio"]),
        sortino=float(metrics["sortino_ratio"]),
        max_drawdown=float(metrics["max_drawdown"]),
        ann_turnover=ann_turnover,
        cost_drag_bps=cost_drag_bps,
        excess_cagr=excess_cagr,
        excess_t_stat=excess_t,
        beats=beats,
    )
