"""Quantify dividend-adjustment bias in the cap-proxy universe ranking.

The PIT universe ranks by ``adjusted close × today's effective shares``.
Adjusted closes embed each stock's *future* dividends (auto_adjust=True
divides history by the cumulative dividend factor), so high-yield names'
early market caps are understated relative to low-yield names — a residual
look-ahead channel in universe selection.

The correct counterfactual is ``split-only-adjusted close × shares``. This
script fetches as-traded closes + split actions, builds split-only-adjusted
prices, recomputes the monthly PIT top-20 schedule both ways, and reports
how often membership differs.

Dev-only; writes data/research/cap_proxy_bias.json. Not part of CI or cron.

Usage:
    uv run python scripts/check_cap_proxy_bias.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CANDIDATE_POOL_TICKERS, DATA_DIR, DATA_START_DATE
from src.data.storage import load_parquet
from src.data.universe import get_members_at, load_shares_outstanding, rank_by_cap_proxy

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

RESEARCH_DIR = DATA_DIR / "research"
TOP_N = 20


def fetch_split_adjusted_closes(tickers: list[str]) -> pd.DataFrame:
    """Split-only-adjusted closes (no dividend adjustment).

    Yahoo's chart data is ALWAYS split-adjusted at source; yfinance's
    ``auto_adjust`` flag only controls the additional dividend adjustment.
    So ``Close`` with ``auto_adjust=False`` is exactly the split-adjusted,
    dividend-unadjusted series the cap proxy needs (verified: AAPL
    2015-01-30 Close = 29.29 = as-traded 117.16 ÷ the 2020 4:1 split).
    Do NOT divide by split factors again — that double-applies them.
    """
    logger.info("Fetching split-adjusted closes for %d tickers...", len(tickers))
    raw = yf.download(
        tickers,
        start=str(DATA_START_DATE),
        auto_adjust=False,
        progress=False,
        group_by="column",
    )
    return raw["Close"]


def monthly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last trading day of each month from 2014 onward."""
    s = pd.Series(index, index=index)
    month_ends = s.groupby(index.to_period("M")).max()
    return pd.DatetimeIndex(month_ends[month_ends >= "2014-01-01"])


def main() -> int:
    prices_df = load_parquet("daily_prices")
    prices_df["date"] = pd.to_datetime(prices_df["date"])
    adjusted = (
        prices_df.pivot_table(index="date", columns="symbol", values="close")
        if "symbol" in prices_df.columns
        else prices_df.set_index("date")
    )

    split_only = fetch_split_adjusted_closes(CANDIDATE_POOL_TICKERS)
    split_only = split_only.reindex(adjusted.index).dropna(how="all")

    shares = load_shares_outstanding()
    dates = monthly_rebalance_dates(adjusted.index)

    diffs: list[dict] = []
    n_diff_months = 0
    affected: dict[str, int] = {}

    for dt in dates:
        members = get_members_at(dt)
        rank_adj = rank_by_cap_proxy(adjusted, shares, dt)
        rank_raw = rank_by_cap_proxy(split_only, shares, dt)
        top_adj = [t for t in rank_adj.index if t in members][:TOP_N]
        top_raw = [t for t in rank_raw.index if t in members][:TOP_N]

        only_adj = sorted(set(top_adj) - set(top_raw))
        only_raw = sorted(set(top_raw) - set(top_adj))
        if only_adj or only_raw:
            n_diff_months += 1
            for t in only_adj + only_raw:
                affected[t] = affected.get(t, 0) + 1
            diffs.append({
                "date": str(dt.date()),
                "in_adjusted_only": only_adj,
                "in_split_only_only": only_raw,
            })

    summary = {
        "top_n": TOP_N,
        "n_months": len(dates),
        "n_months_with_membership_diff": n_diff_months,
        "pct_months_differing": round(n_diff_months / len(dates) * 100, 1),
        "total_name_month_swaps": sum(len(d["in_adjusted_only"]) for d in diffs),
        "affected_names": dict(sorted(affected.items(), key=lambda kv: -kv[1])),
        "diffs": diffs,
    }

    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out = RESEARCH_DIR / "cap_proxy_bias.json"
    out.write_text(json.dumps(summary, indent=2))

    logger.info(
        "Top-%d membership differs in %d of %d months (%.1f%%); "
        "%d name-month swaps total. Written to %s",
        TOP_N,
        n_diff_months,
        len(dates),
        summary["pct_months_differing"],
        summary["total_name_month_swaps"],
        out,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
