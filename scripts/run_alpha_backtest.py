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

import json

from src.backtest.engine import walk_forward_backtest
from src.backtest.metrics import compute_performance_metrics
from src.config import (
    BENCHMARK_TICKER,
    DATA_DIR,
    INCEPTION_DATE,
    SPN_MAX_STOCKS,
    TEST_WINDOW_DAYS,
    TRADING_DAYS_PER_YEAR,
    TRAIN_WINDOW_DAYS,
)
from src.data.storage import load_parquet, save_parquet
from src.data.universe import make_universe_fn
from src.proof.concentration import build_mirror_index
from src.strategies.dynamic_alpha import strategy_from_config
from src.utils.helpers import add_cash_column

RACE_RESULT_PATH = DATA_DIR / "research" / "race_result.json"

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

    if "symbol" in benchmark_df.columns:
        benchmark_df = benchmark_df[benchmark_df["symbol"] == BENCHMARK_TICKER]
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

    # Data before INCEPTION_DATE is ranking lookback only; NAVs and the
    # benchmark comparison start at inception.
    inception = pd.Timestamp(INCEPTION_DATE)
    benchmark_display = benchmark[benchmark.index >= inception]
    benchmark_nav = benchmark_display / benchmark_display.iloc[0]

    # Point-in-time top-20 universe (membership + anchored cap proxy on the
    # dividend-unadjusted ranking panel, loaded by make_universe_fn).
    universe_fn = make_universe_fn(20)

    # ------------------------------------------------------------------
    # Baseline indices (Mirror + Equal) — PIT universe, monthly rebalance,
    # net of transaction costs.
    # ------------------------------------------------------------------
    logger.info("Building baseline indices...")
    sp20_mirror_df = build_mirror_index(
        stock_prices, top_n=20, weighting="cap",
        universe_fn=universe_fn, start=inception,
    )
    sp20_equal_df = build_mirror_index(
        stock_prices, top_n=20, weighting="equal",
        universe_fn=universe_fn, start=inception,
    )

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
    # Walk-forward backtest for the retained SP-N Alpha: the self-adjusting
    # model selected on the development window (data/research/race_result.json
    # — equal-weight × concentration-elbow dynamic-N). It selects from the
    # cap-ranked top-SPN_MAX pool, so it needs its own wider universe_fn.
    # ------------------------------------------------------------------
    logger.info("Running walk-forward backtest: SP-N Alpha (self-adjusting) ...")
    market_indicators = load_parquet("market_indicators")
    if market_indicators.empty:
        logger.warning("No market_indicators parquet — regime/rf features fall back.")
        market_indicators = None

    race_config = json.loads(RACE_RESULT_PATH.read_text())
    logger.info(
        "  Frozen spec: %s",
        {k: race_config[k] for k in ("engine", "n_policy", "overlay")},
    )
    weights_fn, uses_cash = strategy_from_config(race_config, market_indicators)
    alpha_panel = add_cash_column(stock_prices) if uses_cash else stock_prices
    alpha_universe_fn = make_universe_fn(SPN_MAX_STOCKS)
    result = walk_forward_backtest(
        alpha_panel,
        benchmark_prices=benchmark,
        weights_fn=weights_fn,
        train_days=TRAIN_WINDOW_DAYS,
        test_days=TEST_WINDOW_DAYS,
        universe_fn=alpha_universe_fn,
    )
    alpha_nav = result.nav
    ann_turnover = result.turnover.sum() / (len(alpha_nav) / TRADING_DAYS_PER_YEAR)
    logger.info(
        "  SP-N Alpha backtest complete — %d out-of-sample days, "
        "annualised turnover %.2fx, total cost drag %.0f bps, "
        "optimizer fallback rate %.1f%%.",
        len(alpha_nav),
        ann_turnover,
        result.costs.sum() * 1e4,
        result.fallback_rate * 100,
    )
    if result.fallback_rate > 0.2:
        logger.error(
            "Optimizer fell back to equal weights in %.0f%% of splits — "
            "results reflect equal-weighting, not the optimizer. Investigate.",
            result.fallback_rate * 100,
        )

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
        "nav_gross": result.nav_gross.values,
    })
    save_parquet(alpha_nav_df, "alpha_nav")

    # ------------------------------------------------------------------
    # Save final weights (holdings) for the retained alpha strategy, using
    # its own point-in-time top-SPN_MAX universe at the latest date. These
    # are the live target weights the EMS would rebalance toward.
    # ------------------------------------------------------------------
    final_universe = alpha_universe_fn(alpha_panel.index[-1])
    final_train = alpha_panel[
        [c for c in final_universe if c in alpha_panel.columns]
    ].iloc[-TRAIN_WINDOW_DAYS:]
    final_bench = benchmark.iloc[-TRAIN_WINDOW_DAYS:]

    holdings_records: list[dict] = []

    final_weights = weights_fn(final_train, final_bench)
    for ticker, weight in final_weights.items():
        if weight > 0:
            holdings_records.append({
                "strategy": "spn_alpha",
                "ticker": str(ticker),
                "weight": float(weight),
            })

    holdings_df = pd.DataFrame(holdings_records)
    save_parquet(holdings_df, "strategy_holdings")

    logger.info("Done. Saved SP-N Alpha NAV and strategy holdings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
