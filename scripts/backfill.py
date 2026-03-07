"""Backfill historical market data from inception.

Downloads 10+ years of daily prices for all tracked tickers, the S&P 500
benchmark, and market indicators. Saves to both Parquet (local cache) and
optionally to Supabase.

Usage:
    uv run python scripts/backfill.py
    uv run python scripts/backfill.py --skip-supabase
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    BENCHMARK_TICKER,
    INCEPTION_DATE,
    TOP_50_TICKERS,
)
from src.data.fetcher import (
    fetch_benchmark,
    fetch_daily_prices,
    fetch_market_indicators,
    prices_to_long_format,
)
from src.data.storage import (
    df_to_rows,
    load_parquet,
    save_parquet,
    upsert_rows,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def backfill(skip_supabase: bool = False) -> None:
    """Run full historical data backfill.

    Steps:
        1. Fetch daily close prices for TOP_50 tickers since inception.
        2. Fetch S&P 500 benchmark prices.
        3. Fetch market indicators (VIX, risk-free, 10Y Treasury).
        4. Save everything to Parquet.
        5. Optionally upsert to Supabase.
    """
    logger.info("=" * 60)
    logger.info("BACKFILL: Starting historical data download")
    logger.info("Inception date: %s", INCEPTION_DATE)
    logger.info("Tickers: %d stocks + benchmark + indicators", len(TOP_50_TICKERS))
    logger.info("=" * 60)

    # ── Step 1: Stock prices ──────────────────────────
    logger.info("Step 1/4: Fetching daily prices for %d tickers...", len(TOP_50_TICKERS))
    prices_wide = fetch_daily_prices(
        tickers=TOP_50_TICKERS,
        start=INCEPTION_DATE,
    )
    logger.info(
        "Received %d rows x %d tickers (date range: %s to %s)",
        len(prices_wide),
        len(prices_wide.columns),
        prices_wide.index.min().strftime("%Y-%m-%d"),
        prices_wide.index.max().strftime("%Y-%m-%d"),
    )

    # Save wide format for fast local analysis
    save_parquet(prices_wide.reset_index(), "daily_prices")

    # Convert to long format for database
    prices_long = prices_to_long_format(prices_wide)
    logger.info("Long format: %d rows", len(prices_long))

    # ── Step 2: Benchmark ─────────────────────────────
    logger.info("Step 2/4: Fetching S&P 500 benchmark...")
    benchmark = fetch_benchmark(start=INCEPTION_DATE)
    benchmark_df = benchmark.reset_index()
    benchmark_df.columns = ["date", "close"]
    benchmark_df["symbol"] = "^GSPC"
    benchmark_df["date"] = benchmark_df["date"].dt.date
    save_parquet(benchmark_df, "benchmark_prices")
    logger.info("Benchmark: %d rows", len(benchmark_df))

    # ── Step 3: Market indicators ─────────────────────
    logger.info("Step 3/4: Fetching market indicators (VIX, rates)...")
    indicators = fetch_market_indicators(start=INCEPTION_DATE)
    save_parquet(indicators.reset_index(), "market_indicators")
    logger.info("Indicators: %d rows", len(indicators))

    # ── Step 4: Supabase upsert ───────────────────────
    if not skip_supabase:
        logger.info("Step 4/4: Upserting to Supabase...")
        try:
            # Combine stock prices and benchmark into one table
            all_prices = prices_long.copy()
            benchmark_long = benchmark_df[["date", "symbol", "close"]].copy()
            all_prices = all_prices.astype({"date": str})
            benchmark_long = benchmark_long.astype({"date": str})

            combined = (
                all_prices[["date", "symbol", "close"]]
                ._append(benchmark_long, ignore_index=True)
            )

            # Upsert in batches to avoid payload limits
            batch_size = 1000
            rows = df_to_rows(combined)
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                upsert_rows("daily_prices", batch)
                logger.info(
                    "Upserted batch %d/%d (%d rows)",
                    i // batch_size + 1,
                    (len(rows) + batch_size - 1) // batch_size,
                    len(batch),
                )
            logger.info("Supabase upsert complete.")
        except Exception:
            logger.exception("Supabase upsert failed. Local Parquet files are still valid.")
    else:
        logger.info("Step 4/4: Skipping Supabase (--skip-supabase flag)")

    # ── Summary ───────────────────────────────────────
    logger.info("=" * 60)
    logger.info("BACKFILL COMPLETE")
    logger.info("  Stocks:     %d tickers, %d trading days", len(prices_wide.columns), len(prices_wide))
    logger.info("  Benchmark:  %d trading days", len(benchmark_df))
    logger.info("  Indicators: %d trading days", len(indicators))
    logger.info("  Parquet:    data/daily_prices.parquet")
    logger.info("  Parquet:    data/benchmark_prices.parquet")
    logger.info("  Parquet:    data/market_indicators.parquet")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill historical market data")
    parser.add_argument(
        "--skip-supabase",
        action="store_true",
        help="Skip Supabase upsert (save to Parquet only)",
    )
    args = parser.parse_args()
    backfill(skip_supabase=args.skip_supabase)
