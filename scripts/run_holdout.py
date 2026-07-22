"""One-shot pre-registered holdout evaluation of the frozen SP-N Alpha.

This is the moment of truth. The dev-window winner (data/research/
race_result.json) is run once on the LOCKED holdout window
(HOLDOUT_START .. present) and graded against the criteria committed in
data/research/holdout_criteria.yaml BEFORE any candidate was chosen.

Guards against accidental re-evaluation / peeking:
- requires --confirm,
- requires the working tree to be tagged (the frozen spec must be a real,
  referenceable commit),
- refuses to run twice for the same (git description) unless --force.

Also reports the deflated Sharpe of the DEV result given the true trial
count, so multiple-testing is disclosed alongside the holdout outcome.

Usage:
    git tag spn-alpha-v2-registered
    uv run python scripts/run_holdout.py --confirm
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml  # type: ignore[import-untyped]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.engine import walk_forward_backtest
from src.backtest.metrics import deflated_sharpe
from src.config import (
    DATA_DIR,
    HOLDOUT_START,
    INCEPTION_DATE,
    SPN_MAX_STOCKS,
    TEST_WINDOW_DAYS,
    TRAIN_WINDOW_DAYS,
)
from src.data.storage import load_parquet
from src.data.universe import make_universe_fn
from src.proof.concentration import build_mirror_index
from src.research.registry import load_trials
from src.research.scoring import score_strategy
from src.strategies.dynamic_alpha import strategy_from_config
from src.utils.helpers import add_cash_column

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("holdout")
for noisy in ("src.features", "src.optimizer", "pypfopt"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

RESULT_PATH = DATA_DIR / "research" / "race_result.json"
CRITERIA_PATH = DATA_DIR / "research" / "holdout_criteria.yaml"
HOLDOUT_LOG = DATA_DIR / "research" / "holdout_results.jsonl"


def _git_describe() -> str | None:
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def _load():
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


def _dev_deflated_sharpe(winner_dev_returns: pd.Series) -> tuple[float, int, float]:
    """DSR of the dev result given the logged trial count and Sharpe spread."""
    trials = [t for t in load_trials() if t.get("split") == "dev"]
    sharpes = [t["score"]["sharpe"] for t in trials if "score" in t]
    n = len(trials)
    sharpe_std = float(np.std(sharpes, ddof=1)) if len(sharpes) > 1 else 0.0
    # Convert annualised-Sharpe spread to per-period for the PSR benchmark.
    per_period_std = sharpe_std / np.sqrt(252)
    dsr = deflated_sharpe(winner_dev_returns, n_trials=n, sharpe_std=per_period_std)
    return dsr, n, sharpe_std


def main() -> int:
    parser = argparse.ArgumentParser(description="One-shot holdout evaluation")
    parser.add_argument("--confirm", action="store_true", help="Required to run the evaluation.")
    parser.add_argument("--force", action="store_true", help="Re-run for an already-logged tag.")
    args = parser.parse_args()

    if not args.confirm:
        logger.error("Refusing to run without --confirm (this is the one-shot holdout).")
        return 1

    tag = _git_describe()
    if tag is None:
        logger.error(
            "Working tree is not on an exact tag. Freeze the spec first: "
            "`git tag spn-alpha-v2-registered` then re-run."
        )
        return 1

    if HOLDOUT_LOG.exists() and not args.force:
        prior = [json.loads(x) for x in HOLDOUT_LOG.read_text().splitlines() if x.strip()]
        if any(p.get("tag") == tag for p in prior):
            logger.error(
                "Holdout already evaluated for tag %s. The point of a holdout is "
                "one shot — use --force only if you understand you are burning it.",
                tag,
            )
            return 1

    config = json.loads(RESULT_PATH.read_text())
    criteria = yaml.safe_load(CRITERIA_PATH.read_text())["criteria"]
    spec = {k: config[k] for k in ("engine", "n_policy", "overlay")}
    logger.info("Frozen spec (tag %s): %s", tag, spec)

    prices, bench, mi = _load()
    inception = pd.Timestamp(INCEPTION_DATE)
    holdout_start = pd.Timestamp(HOLDOUT_START)

    weights_fn, uses_cash = strategy_from_config(config, market_indicators=mi)
    panel = add_cash_column(prices) if uses_cash else prices
    universe_fn = make_universe_fn(SPN_MAX_STOCKS)

    # Run on the FULL panel; the strategy is PIT so 2024+ decisions used only
    # trailing data. Split the resulting NAV into dev / holdout portions.
    result = walk_forward_backtest(
        panel, benchmark_prices=bench, weights_fn=weights_fn,
        train_days=TRAIN_WINDOW_DAYS, test_days=TEST_WINDOW_DAYS, universe_fn=universe_fn,
    )
    nav = result.nav

    # References over the full window.
    bench_nav = (bench[bench.index >= inception] / bench[bench.index >= inception].iloc[0])
    equal_df = build_mirror_index(
        prices, top_n=20, weighting="equal", universe_fn=make_universe_fn(20), start=inception,
    )
    equal_nav = pd.Series(
        equal_df["nav"].values, index=pd.to_datetime(equal_df["date"]), name="sp20_equal"
    )

    # Deflated Sharpe on the dev portion (multiple-testing disclosure).
    dev_returns = nav[nav.index <= pd.Timestamp("2023-12-31")].pct_change().dropna()
    dsr, n_trials, sharpe_std = _dev_deflated_sharpe(dev_returns)

    # Score on the holdout window only.
    hold_nav = nav[nav.index >= holdout_start]
    turn = result.turnover[result.turnover.index >= holdout_start]
    cost = result.costs[result.costs.index >= holdout_start]
    score = score_strategy(
        "spn_alpha_holdout", hold_nav,
        {"sp500": bench_nav, "sp20_equal": equal_nav}, turnover=turn, costs=cost,
    )

    # Index max drawdown over the matched holdout window (both series sliced
    # to the strategy's common dates, then renormalised).
    idx_window = bench_nav[
        (bench_nav.index >= pd.Timestamp(score.window_start))
        & (bench_nav.index <= pd.Timestamp(score.window_end))
    ]
    idx_window = idx_window / idx_window.iloc[0]
    idx_dd = float((idx_window / idx_window.cummax() - 1).min())

    # Grade against the pre-registered contract. `score.beats[ref]` is True
    # only when the strategy beats that reference on BOTH CAGR and Sharpe.
    checks = {
        "beat_sp500_cagr_and_sharpe": score.beats.get("sp500", False),
        "beat_equal_cagr_and_sharpe": score.beats.get("sp20_equal", False),
        "max_drawdown_within_multiple": (
            score.max_drawdown >= criteria["max_drawdown_multiple"] * idx_dd
        ),
    }
    passed = all(checks.values())

    logger.info("=" * 78)
    logger.info("HOLDOUT RESULT (%s .. %s)", score.window_start, score.window_end)
    logger.info("  SP-N Alpha : CAGR %.1f%%  Sharpe %.2f  maxDD %.1f%%  turnover %.1fx",
                score.cagr * 100, score.sharpe, score.max_drawdown * 100, score.ann_turnover)
    logger.info("  vs ^SP500TR: %+.1f%% CAGR   vs SP-20 Equal: %+.1f%% CAGR",
                score.excess_cagr["sp500"] * 100, score.excess_cagr["sp20_equal"] * 100)
    logger.info("  index maxDD over window: %.1f%%", idx_dd * 100)
    for name, ok in checks.items():
        logger.info("    [%s] %s", "PASS" if ok else "FAIL", name)
    logger.info(
        "  Dev deflated Sharpe: %.3f (N=%d trials, Sharpe std=%.3f)", dsr, n_trials, sharpe_std
    )
    logger.info("  OUTCOME: %s", "PASS — SP-N Alpha earns the public slot" if passed
                else "FAIL — SP-20 Equal remains the retained result")
    logger.info("=" * 78)

    record = {
        "tag": tag,
        "config": {k: config[k] for k in ("engine", "n_policy", "overlay")},
        "holdout_window": [score.window_start, score.window_end],
        "score": score.to_dict(),
        "index_max_drawdown": idx_dd,
        "checks": checks,
        "passed": passed,
        "dev_deflated_sharpe": dsr,
        "dev_trial_count": n_trials,
        "dev_sharpe_std": sharpe_std,
    }
    HOLDOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HOLDOUT_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")
    logger.info("Logged holdout result → %s", HOLDOUT_LOG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
