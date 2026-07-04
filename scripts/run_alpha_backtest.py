"""Run walk-forward backtest for the public SP-N Alpha strategy.

Compares the retained MVO max-Sharpe strategy against SP-20 Mirror,
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
from src.config import TEST_WINDOW_DAYS, TRAIN_WINDOW_DAYS
from src.data.storage import load_parquet, save_parquet
from src.proof.concentration import build_mirror_index
from src.strategies.alpha import make_alpha_weights_fn

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
    """Run the retained alpha backtest and print comparison."""
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
    # Walk-forward backtest for the one public optimized strategy.
    # Archived research variants are intentionally not exported because
    # they do not beat the SP-20 Equal baseline cleanly enough.
    # ------------------------------------------------------------------
    logger.info("Running walk-forward backtest: SP-N Alpha (mvo_sharpe) ...")
    weights_fn = make_alpha_weights_fn(optimizer="mvo_sharpe")
    alpha_nav = walk_forward_backtest(
        stock_prices,
        benchmark_prices=benchmark,
        weights_fn=weights_fn,
        train_days=TRAIN_WINDOW_DAYS,
        test_days=TEST_WINDOW_DAYS,
    )
    logger.info("  SP-N Alpha backtest complete — %d out-of-sample days.", len(alpha_nav))

    # ------------------------------------------------------------------
    # Compute metrics for all
    # ------------------------------------------------------------------
    all_metrics: dict[str, dict] = {}
    all_metrics["S&P 500"] = compute_performance_metrics(benchmark_nav)
    all_metrics["SP-20 Mirror"] = compute_performance_metrics(mirror_nav, benchmark_nav)
    all_metrics["SP-20 Equal"] = compute_performance_metrics(equal_nav, benchmark_nav)

    all_metrics["SP-N Alpha"] = compute_performance_metrics(alpha_nav, benchmark_nav)

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
    # Save canonical alpha NAV for the frontend.
    # ------------------------------------------------------------------
    alpha_nav_df = pd.DataFrame({
        "date": alpha_nav.index,
        "nav": alpha_nav.values,
    })
    save_parquet(alpha_nav_df, "alpha_nav")
    save_parquet(alpha_nav_df, "alpha_nav_mvo_sharpe")

    # ------------------------------------------------------------------
    # Save final weights (holdings) for the public alpha strategy.
    # ------------------------------------------------------------------
    # Use the most recent training window to compute final weights for each strategy
    final_train = stock_prices.iloc[-TRAIN_WINDOW_DAYS:]
    final_bench = benchmark.iloc[-TRAIN_WINDOW_DAYS:]

    holdings_records: list[dict] = []

    final_weights = weights_fn(final_train, final_bench)
    for ticker, weight in final_weights.items():
        if weight > 0:
            holdings_records.append({
                "strategy": "spn_alpha",
                "ticker": ticker,
                "weight": float(weight),
            })

    holdings_df = pd.DataFrame(holdings_records)
    save_parquet(holdings_df, "strategy_holdings")

    logger.info("Done. Saved SP-N Alpha NAV and strategy holdings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
