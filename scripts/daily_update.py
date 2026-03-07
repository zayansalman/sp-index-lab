"""Daily incremental data update pipeline.

Fetches new market data since the last recorded date, appends to Parquet,
and optionally syncs to Supabase. Designed to run via GitHub Actions cron.

Usage:
    uv run python scripts/daily_update.py
    uv run python scripts/daily_update.py --skip-supabase
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import BENCHMARK_TICKER, TOP_50_TICKERS
from src.data.fetcher import (
    fetch_benchmark,
    fetch_incremental,
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


def _get_last_date(parquet_name: str, date_col: str = "date") -> date | None:
    """Get the most recent date from a Parquet file."""
    df = load_parquet(parquet_name)
    if df.empty:
        return None
    dates = pd.to_datetime(df[date_col])
    return dates.max().date()


def daily_update(skip_supabase: bool = False) -> None:
    """Run incremental daily update."""
    logger.info("=" * 60)
    logger.info("DAILY UPDATE: %s", date.today().isoformat())
    logger.info("=" * 60)

    # ── Stock prices ──────────────────────────────────
    last_price_date = _get_last_date("daily_prices")
    logger.info("Last price date in cache: %s", last_price_date)

    new_prices = fetch_incremental(tickers=TOP_50_TICKERS, last_date=last_price_date)

    if new_prices.empty:
        logger.info("No new price data available. Exiting.")
        return

    logger.info("Fetched %d new trading days", len(new_prices))

    # Append to existing Parquet
    existing = load_parquet("daily_prices")
    if not existing.empty:
        existing["date"] = pd.to_datetime(existing["date"])
        existing = existing.set_index("date")
        combined = pd.concat([existing, new_prices])
        combined = combined[~combined.index.duplicated(keep="last")]
    else:
        combined = new_prices

    save_parquet(combined.reset_index(), "daily_prices")

    # ── Benchmark ─────────────────────────────────────
    last_bench_date = _get_last_date("benchmark_prices")
    benchmark = fetch_benchmark(start=last_bench_date)
    if not benchmark.empty:
        bench_df = benchmark.reset_index()
        bench_df.columns = ["date", "close"]
        bench_df["symbol"] = "^GSPC"
        bench_df["date"] = bench_df["date"].dt.date

        existing_bench = load_parquet("benchmark_prices")
        if not existing_bench.empty:
            combined_bench = pd.concat([existing_bench, bench_df]).drop_duplicates(
                subset=["date", "symbol"], keep="last"
            )
        else:
            combined_bench = bench_df
        save_parquet(combined_bench, "benchmark_prices")

    # ── Market indicators ─────────────────────────────
    last_ind_date = _get_last_date("market_indicators")
    indicators = fetch_market_indicators(start=last_ind_date)
    if not indicators.empty:
        existing_ind = load_parquet("market_indicators")
        if not existing_ind.empty:
            existing_ind["date"] = pd.to_datetime(existing_ind["date"])
            existing_ind = existing_ind.set_index("date")
            combined_ind = pd.concat([existing_ind, indicators])
            combined_ind = combined_ind[~combined_ind.index.duplicated(keep="last")]
        else:
            combined_ind = indicators
        save_parquet(combined_ind.reset_index(), "market_indicators")

    # ── Supabase sync ─────────────────────────────────
    if not skip_supabase:
        try:
            prices_long = prices_to_long_format(new_prices)
            rows = df_to_rows(prices_long)
            batch_size = 1000
            for i in range(0, len(rows), batch_size):
                upsert_rows("daily_prices", rows[i : i + batch_size])
            logger.info("Supabase sync complete (%d rows)", len(rows))
        except Exception:
            logger.exception("Supabase sync failed. Local data is still updated.")
    else:
        logger.info("Skipping Supabase sync (--skip-supabase flag)")

    logger.info("=" * 60)
    logger.info("DAILY UPDATE COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily incremental data update")
    parser.add_argument("--skip-supabase", action="store_true")
    args = parser.parse_args()
    daily_update(skip_supabase=args.skip_supabase)
