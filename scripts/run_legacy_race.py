"""Re-race archived legacy variants under the honest methodology (dev window).

HRP and MVO max-Sharpe already competed as engines in run_research_race.py.
This adds the remaining discarded variants — MVO min-vol, the LightGBM/HMM ML
ensemble, and the hedged cash strategy — through the same harness so:

- RESEARCH.md's "these were tried and dropped" claim is reproducible, and
- the deflated-Sharpe trial count reflects every strategy genuinely tried.

These are research-grade (the code review flagged real validity caveats in
the ML and hedged paths); they are logged for the record, not for selection.

Usage:
    uv run python scripts/run_legacy_race.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    INCEPTION_DATE,
    SPN_MAX_STOCKS,
    TEST_WINDOW_DAYS,
    TRAIN_WINDOW_DAYS,
)
from src.data.storage import load_parquet
from src.data.universe import make_universe_fn
from src.proof.concentration import build_mirror_index
from src.research.registry import dev_trial_count, run_experiment
from src.strategies.alpha import make_alpha_weights_fn, make_ml_alpha_weights_fn
from src.strategies.hedged import make_hedged_weights_fn
from src.utils.helpers import add_cash_column

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("legacy")
for noisy in ("src.features", "src.optimizer", "pypfopt", "lightgbm"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def _load() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    prices = load_parquet("daily_prices")
    prices["date"] = pd.to_datetime(prices["date"])
    prices = (
        prices.pivot_table(index="date", columns="symbol", values="close")
        if "symbol" in prices.columns
        else prices.set_index("date")
    )
    bench = load_parquet("benchmark_prices")
    bench["date"] = pd.to_datetime(bench["date"])
    bench = bench.set_index("date")["close"]
    mi = load_parquet("market_indicators")
    return prices, bench, mi


def _fmt(score) -> str:
    return (
        f"CAGR {score.cagr:6.1%}  Sharpe {score.sharpe:5.2f}  maxDD {score.max_drawdown:6.1%}  "
        f"vs500 {score.excess_cagr.get('sp500', 0):+.1%}  "
        f"vsEq {score.excess_cagr.get('sp20_equal', 0):+.1%}  "
        f"beatsBoth {score.beats.get('sp500') and score.beats.get('sp20_equal')}"
    )


def main() -> int:
    prices, bench, mi = _load()
    inception = pd.Timestamp(INCEPTION_DATE)
    universe_fn = make_universe_fn(SPN_MAX_STOCKS)
    prices_cash = add_cash_column(prices)

    bench_dev = bench[bench.index >= inception]
    bench_nav = bench_dev / bench_dev.iloc[0]
    equal_df = build_mirror_index(
        prices, top_n=20, weighting="equal", universe_fn=make_universe_fn(20), start=inception,
    )
    equal_nav = pd.Series(
        equal_df["nav"].values, index=pd.to_datetime(equal_df["date"]), name="sp20_equal"
    )
    references = {"sp500": bench_nav, "sp20_equal": equal_nav}
    base = dict(
        benchmark=bench, references=references, universe_fn=universe_fn,
        train_days=TRAIN_WINDOW_DAYS, test_days=TEST_WINDOW_DAYS,
    )

    logger.info("=" * 78)
    logger.info("Legacy variant re-race (honest methodology, dev window)")
    logger.info("=" * 78)

    # MVO min-vol
    score, _ = run_experiment(
        "legacy:mvo_minvol",
        make_alpha_weights_fn("mvo_minvol", market_indicators=mi),
        prices=prices, config={"stage": "legacy", "variant": "mvo_minvol"},
        notes="legacy re-race", **base,
    )
    logger.info("  %-16s %s", "mvo_minvol", _fmt(score))

    # ML ensemble (LightGBM factor + HMM regime blend) — research-grade
    score, _ = run_experiment(
        "legacy:ml_ensemble",
        make_ml_alpha_weights_fn(mi),
        prices=prices, config={"stage": "legacy", "variant": "ml_ensemble"},
        notes="legacy re-race; research-grade (see code review caveats)", **base,
    )
    logger.info("  %-16s %s", "ml_ensemble", _fmt(score))

    # Hedged (dynamic beta + cash) — needs the CASH-augmented panel
    base_cash = {**base, "prices": prices_cash}
    score, _ = run_experiment(
        "legacy:hedged",
        make_hedged_weights_fn(mi),
        config={"stage": "legacy", "variant": "hedged"},
        notes="legacy re-race; research-grade (see code review caveats)", **base_cash,
    )
    logger.info("  %-16s %s", "hedged", _fmt(score))

    logger.info("=" * 78)
    logger.info("Total dev trials logged: %d", dev_trial_count())
    logger.info("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
