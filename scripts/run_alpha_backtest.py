"""Run walk-forward backtest for SP-N Alpha strategies.

Compares HRP, MVO max-Sharpe, and MVO min-vol against SP-20 Mirror,
SP-20 Equal, and the S&P 500 benchmark.

Usage:
    uv run python scripts/run_alpha_backtest.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.engine import walk_forward_backtest
from src.backtest.metrics import compute_performance_metrics
from src.config import TRAIN_WINDOW_DAYS, TEST_WINDOW_DAYS
from src.data.storage import load_parquet, save_parquet
from src.proof.concentration import build_mirror_index
from src.strategies.alpha import make_alpha_weights_fn, make_ml_alpha_weights_fn
from src.strategies.hedged import make_hedged_weights_fn
from src.utils.helpers import add_cash_column

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _load_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load stock prices (wide) and benchmark Series."""
    prices_df = load_parquet("daily_prices")
    benchmark_df = load_parquet("benchmark_prices")

    if prices_df.empty or benchmark_df.empty:
        logger.error("Missing parquet data. Run scripts/backfill.py first.")
        sys.exit(1)

    prices_df["date"] = pd.to_datetime(prices_df["date"])
    if "symbol" in prices_df.columns:
        stock_prices = prices_df.pivot_table(
            index="date", columns="symbol", values="close"
        )
    else:
        stock_prices = prices_df.set_index("date")

    benchmark_df["date"] = pd.to_datetime(benchmark_df["date"])
    benchmark = benchmark_df.set_index("date")["close"]
    benchmark.name = "sp500"

    return stock_prices, benchmark


def main() -> int:
    """Run all alpha backtests and print comparison."""
    logger.info("=" * 70)
    logger.info("SP-N Alpha Walk-Forward Backtest")
    logger.info("=" * 70)

    stock_prices, benchmark = _load_data()
    benchmark_nav = benchmark / benchmark.iloc[0]

    # ------------------------------------------------------------------
    # Baseline indices (Mirror + Equal)
    # ------------------------------------------------------------------
    logger.info("Building baseline indices...")
    sp20_mirror_df = build_mirror_index(stock_prices, top_n=20, weighting="cap")
    sp20_equal_df = build_mirror_index(stock_prices, top_n=20, weighting="equal")

    mirror_nav = pd.Series(
        sp20_mirror_df["nav"].values,
        index=pd.to_datetime(sp20_mirror_df["date"]),
        name="sp20_mirror",
    )
    equal_nav = pd.Series(
        sp20_equal_df["nav"].values,
        index=pd.to_datetime(sp20_equal_df["date"]),
        name="sp20_equal",
    )

    # ------------------------------------------------------------------
    # Walk-forward backtests for classical optimizers.
    # NOTE: MVO Min-Vol and HRP dropped — both fail to clearly beat the
    # SP-20 Equal baseline on CAGR, so the complexity isn't earning its
    # keep relative to simple equal-weighting.
    # ------------------------------------------------------------------
    optimizers = ["mvo_sharpe"]
    alpha_navs: dict[str, pd.Series] = {}

    for opt_name in optimizers:
        logger.info("Running walk-forward backtest: %s ...", opt_name)
        weights_fn = make_alpha_weights_fn(optimizer=opt_name)

        nav = walk_forward_backtest(
            stock_prices,
            benchmark_prices=benchmark,
            weights_fn=weights_fn,
            train_days=TRAIN_WINDOW_DAYS,
            test_days=TEST_WINDOW_DAYS,
        )
        alpha_navs[opt_name] = nav
        logger.info("  %s backtest complete — %d out-of-sample days.", opt_name, len(nav))

    # ------------------------------------------------------------------
    # Walk-forward backtest for ML ensemble (LightGBM + HMM)
    # ------------------------------------------------------------------
    logger.info("Running walk-forward backtest: ml_ensemble ...")
    market_indicators = load_parquet("market_indicators")
    ml_weights_fn = make_ml_alpha_weights_fn(market_indicators)

    ml_nav = walk_forward_backtest(
        stock_prices,
        benchmark_prices=benchmark,
        weights_fn=ml_weights_fn,
        train_days=TRAIN_WINDOW_DAYS,
        test_days=TEST_WINDOW_DAYS,
    )
    alpha_navs["ml_ensemble"] = ml_nav
    logger.info("  ml_ensemble backtest complete — %d out-of-sample days.", len(ml_nav))

    # ------------------------------------------------------------------
    # Walk-forward backtest for SP-N Hedged
    # ------------------------------------------------------------------
    logger.info("Running walk-forward backtest: hedged ...")
    prices_with_cash = add_cash_column(stock_prices)
    hedged_weights_fn = make_hedged_weights_fn(
        market_indicators, benchmark_prices=benchmark,
    )

    hedged_nav = walk_forward_backtest(
        prices_with_cash,
        benchmark_prices=benchmark,
        weights_fn=hedged_weights_fn,
        train_days=TRAIN_WINDOW_DAYS,
        test_days=TEST_WINDOW_DAYS,
    )
    logger.info("  hedged backtest complete — %d out-of-sample days.", len(hedged_nav))

    # ------------------------------------------------------------------
    # Compute metrics for all
    # ------------------------------------------------------------------
    all_metrics: dict[str, dict] = {}
    all_metrics["S&P 500"] = compute_performance_metrics(benchmark_nav)
    all_metrics["SP-20 Mirror"] = compute_performance_metrics(mirror_nav, benchmark_nav)
    all_metrics["SP-20 Equal"] = compute_performance_metrics(equal_nav, benchmark_nav)

    for opt_name, nav in alpha_navs.items():
        label = f"SP-N Alpha ({opt_name})"
        all_metrics[label] = compute_performance_metrics(nav, benchmark_nav)

    all_metrics["SP-N Hedged"] = compute_performance_metrics(hedged_nav, benchmark_nav)

    # ------------------------------------------------------------------
    # Print comparison table
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("=" * 70)
    logger.info("PERFORMANCE COMPARISON")
    logger.info("=" * 70)

    header = f"{'Strategy':<25} {'CAGR':>8} {'Sharpe':>8} {'Sortino':>8} {'MaxDD':>8} {'Alpha':>8}"
    logger.info(header)
    logger.info("-" * 70)

    for name, m in all_metrics.items():
        cagr = f"{m.get('cagr', 0):.1%}"
        sharpe = f"{m.get('sharpe_ratio', 0):.2f}"
        sortino = f"{m.get('sortino_ratio', 0):.2f}"
        max_dd = f"{m.get('max_drawdown', 0):.1%}"
        alpha = f"{m.get('alpha', 0):.1%}" if "alpha" in m else "—"
        logger.info(f"{name:<25} {cagr:>8} {sharpe:>8} {sortino:>8} {max_dd:>8} {alpha:>8}")

    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Save all alpha NAVs individually for the frontend
    # ------------------------------------------------------------------
    reference_idx = alpha_navs["ml_ensemble"].index
    for opt_name, nav in alpha_navs.items():
        nav_df = pd.DataFrame({
            "date": nav.index,
            "nav": nav.values,
        })
        save_parquet(nav_df, f"alpha_nav_{opt_name}")

    # Canonical "SP-N Alpha" is the ML ensemble (matches the docs)
    ml_nav_df = pd.DataFrame({
        "date": alpha_navs["ml_ensemble"].index,
        "nav": alpha_navs["ml_ensemble"].values,
    })
    save_parquet(ml_nav_df, "alpha_nav")

    # ------------------------------------------------------------------
    # Save final weights (holdings) for each strategy variant
    # ------------------------------------------------------------------
    # Use the most recent training window to compute final weights for each strategy
    final_train = stock_prices.iloc[-TRAIN_WINDOW_DAYS:]
    final_bench = benchmark.iloc[-TRAIN_WINDOW_DAYS:]

    holdings_records: list[dict] = []

    # Classical variants (HRP and Min-Vol dropped — both fail to beat Equal)
    for opt_name in ["mvo_sharpe"]:
        fn = make_alpha_weights_fn(optimizer=opt_name)
        w = fn(final_train, final_bench)
        for ticker, weight in w.items():
            if weight > 0:
                holdings_records.append({
                    "strategy": f"spn_alpha_{opt_name}",
                    "ticker": ticker,
                    "weight": float(weight),
                })

    # ML ensemble variant
    ml_fn = make_ml_alpha_weights_fn(market_indicators)
    ml_w = ml_fn(final_train, final_bench)
    for ticker, weight in ml_w.items():
        if weight > 0:
            holdings_records.append({
                "strategy": "spn_alpha_ml_ensemble",
                "ticker": ticker,
                "weight": float(weight),
            })

    # Hedged variant (uses cash column)
    hedged_fn = make_hedged_weights_fn(market_indicators, benchmark_prices=benchmark)
    final_train_with_cash = add_cash_column(final_train)
    hedged_w = hedged_fn(final_train_with_cash, final_bench)
    for ticker, weight in hedged_w.items():
        if weight > 0:
            holdings_records.append({
                "strategy": "spn_hedged",
                "ticker": ticker,
                "weight": float(weight),
            })

    holdings_df = pd.DataFrame(holdings_records)
    save_parquet(holdings_df, "strategy_holdings")

    # ------------------------------------------------------------------
    # Save hedged NAV
    # ------------------------------------------------------------------
    hedged_df = pd.DataFrame({
        "date": hedged_nav.index,
        "nav": hedged_nav.values,
    })
    save_parquet(hedged_df, "hedged_nav")

    logger.info("Done. Saved alpha variants, hedged NAV, and strategy holdings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
