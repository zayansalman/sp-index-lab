"""Staged development race for the self-adjusting SP-N Alpha (dev window only).

Every backtest goes through ``run_experiment`` → data hard-truncated at
DEV_END, scored matched-window vs ^SP500TR and SP-20 Equal, logged to
``data/research/trials.jsonl``. The staged structure caps the trial count
on purpose: grid-searching everything is exactly how v1's edge turned out to
be selection noise.

Stage 1: weighting engines at static N=20        → keep top 2 by net Sharpe
Stage 2: N policies on those engines             → keep best
Stage 3: risk overlays on the best of stage 2    → pick the candidate

The winner is written to data/research/race_result.json (NOT the public
export — that waits for the pre-registered holdout in scripts/run_holdout.py).

Usage:
    uv run python scripts/run_research_race.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    DATA_DIR,
    DEV_END,
    INCEPTION_DATE,
    SPN_MAX_STOCKS,
    TEST_WINDOW_DAYS,
    TRAIN_WINDOW_DAYS,
)
from src.data.storage import load_parquet
from src.data.universe import make_universe_fn
from src.proof.concentration import build_mirror_index
from src.research.registry import dev_trial_count, run_experiment
from src.strategies.dynamic_alpha import (
    make_dynamic_alpha_weights_fn,
    make_elbow_n,
    make_regime_n,
    make_static_n,
    make_vol_target,
)
from src.utils.helpers import add_cash_column

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("race")
for noisy in ("src.features.regime", "src.optimizer", "pypfopt"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

RESULT_PATH = DATA_DIR / "research" / "race_result.json"


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
        f"CAGR {score.cagr:6.1%}  Sharpe {score.sharpe:5.2f}  "
        f"maxDD {score.max_drawdown:6.1%}  turn {score.ann_turnover:4.1f}x  "
        f"vs500 {score.excess_cagr.get('sp500', 0):+.1%}  "
        f"vsEq {score.excess_cagr.get('sp20_equal', 0):+.1%}  "
        f"beatsBoth {score.beats.get('sp500') and score.beats.get('sp20_equal')}"
    )


def main() -> int:
    prices, bench, mi = _load()
    inception = pd.Timestamp(INCEPTION_DATE)

    # Universe fn over the top SPN_MAX pool; columns arrive cap-ranked so the
    # dynamic-N policies can take columns[:N]. CASH-augmented panel lets
    # vol-target overlays hold cash.
    universe_fn = make_universe_fn(SPN_MAX_STOCKS)
    prices_cash = add_cash_column(prices)

    # References (dev-truncated inside run_experiment): S&P 500 TR + SP-20 Equal.
    bench_dev = bench[(bench.index >= inception)]
    bench_nav = bench_dev / bench_dev.iloc[0]
    equal_df = build_mirror_index(
        prices, top_n=20, weighting="equal", universe_fn=make_universe_fn(20),
        start=inception,
    )
    equal_nav = pd.Series(
        equal_df["nav"].values, index=pd.to_datetime(equal_df["date"]), name="sp20_equal"
    )
    references = {"sp500": bench_nav, "sp20_equal": equal_nav}

    common = dict(
        prices=prices,
        benchmark=bench,
        references=references,
        universe_fn=universe_fn,
        train_days=TRAIN_WINDOW_DAYS,
        test_days=TEST_WINDOW_DAYS,
    )
    common_cash = {**common, "prices": prices_cash}

    logger.info("=" * 78)
    logger.info("SP-N Alpha v2 development race — dev window through %s", DEV_END)
    logger.info("=" * 78)

    # ---- Stage 1: weighting engines, static N=20 ----------------------------
    logger.info("\nSTAGE 1 — weighting engines (static N=20)")
    stage1 = {}
    for eng in ["equal", "inverse_vol", "momentum_tilt", "mvo_sharpe", "hrp"]:
        wf = make_dynamic_alpha_weights_fn(eng, make_static_n(20), market_indicators=mi)
        score, _ = run_experiment(
            f"s1:{eng}:N20", wf, config={"stage": 1, "engine": eng, "n": 20},
            notes="stage1 engine screen", **common,
        )
        stage1[eng] = score
        logger.info("  %-14s %s", eng, _fmt(score))

    top2 = sorted(stage1, key=lambda e: stage1[e].sharpe, reverse=True)[:2]
    logger.info("  → top 2 engines by net Sharpe: %s", top2)

    # ---- Stage 2: N policies on the top-2 engines ---------------------------
    logger.info("\nSTAGE 2 — N policies on %s", top2)
    stage2 = {}
    n_policies = {
        "static20": lambda: make_static_n(20),
        "elbow": lambda: make_elbow_n(),
        "regime": lambda: make_regime_n(mi),
    }
    for eng in top2:
        for pname, pmake in n_policies.items():
            if pname == "static20":
                stage2[(eng, pname)] = stage1[eng]  # already run in stage 1
                logger.info("  %-14s %-9s %s", eng, pname, _fmt(stage1[eng]))
                continue
            wf = make_dynamic_alpha_weights_fn(eng, pmake(), market_indicators=mi)
            score, _ = run_experiment(
                f"s2:{eng}:{pname}", wf,
                config={"stage": 2, "engine": eng, "n_policy": pname},
                notes="stage2 N policy", **common,
            )
            stage2[(eng, pname)] = score
            logger.info("  %-14s %-9s %s", eng, pname, _fmt(score))

    best_eng, best_np = max(stage2, key=lambda k: stage2[k].sharpe)
    logger.info("  → best engine/N: %s / %s", best_eng, best_np)

    # ---- Stage 3: risk overlays on the best engine/N ------------------------
    logger.info("\nSTAGE 3 — risk overlays on %s/%s", best_eng, best_np)

    def _npolicy(name):
        return n_policies[name]()

    stage3 = {"none": stage2[(best_eng, best_np)]}
    logger.info("  %-18s %s", "none", _fmt(stage3["none"]))
    overlays = {
        "voltgt15": lambda: make_vol_target(0.15),
        "voltgt_regime": lambda: make_vol_target(0.15, regime_gated=True, market_indicators=mi),
    }
    for oname, omake in overlays.items():
        wf = make_dynamic_alpha_weights_fn(
            best_eng, _npolicy(best_np), overlay=omake(), market_indicators=mi
        )
        score, _ = run_experiment(
            f"s3:{best_eng}:{best_np}:{oname}", wf,
            config={"stage": 3, "engine": best_eng, "n_policy": best_np, "overlay": oname},
            notes="stage3 overlay", **common_cash,
        )
        stage3[oname] = score
        logger.info("  %-18s %s", oname, _fmt(score))

    # ---- Winner (dev-window) ------------------------------------------------
    # Eligibility mirrors the pre-registered holdout contract: must beat BOTH
    # ^SP500TR and SP-20 Equal (on CAGR and Sharpe). SP-20 Equal is the floor
    # the project must clear — a lower-vol variant that undershoots Equal does
    # not qualify. Among eligible, rank by Sharpe then lower drawdown.
    def _eligible(s) -> bool:
        return bool(s.beats.get("sp500") and s.beats.get("sp20_equal"))

    ranked = sorted(stage3.values(), key=lambda s: (s.sharpe, -abs(s.max_drawdown)), reverse=True)
    eligible = [s for s in ranked if _eligible(s)]
    winner = eligible[0] if eligible else ranked[0]
    best_overlay = next(o for o, s in stage3.items() if s is winner)

    n_trials = dev_trial_count()
    logger.info("\n" + "=" * 78)
    logger.info("WINNER (dev): %s / %s / overlay=%s", best_eng, best_np, best_overlay)
    logger.info("  %s", _fmt(winner))
    logger.info("  dev trials logged so far: %d", n_trials)
    logger.info("=" * 78)

    result = {
        "engine": best_eng,
        "n_policy": best_np,
        "overlay": best_overlay,
        "uses_cash": best_overlay != "none",
        "dev_score": winner.to_dict(),
        "dev_trial_count": n_trials,
        "dev_end": str(DEV_END),
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2))
    logger.info("Wrote %s", RESULT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
