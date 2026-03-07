"""Export all analytics data to static JSON files for the React frontend.

Bridges the Parquet data files and Python analytics functions to generate
JSON files consumed by the Next.js static frontend.

Usage:
    uv run python scripts/export_frontend_data.py
"""

import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import INCEPTION_DATE, TOP_20_TICKERS, TOP_50_TICKERS
from src.data.storage import load_parquet
from src.proof.concentration import (
    build_mirror_index,
    compute_performance_metrics,
    compute_tracking_error,
    concentration_curve,
    variance_decomposition,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
OUTPUT_DIR = PROJECT_ROOT / "frontend" / "public" / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_value(v: Any) -> Any:
    """Convert a single value to JSON-safe form.

    - NaN / Inf  ->  None  (becomes JSON null)
    - numpy scalars -> Python scalars
    - floats rounded to 6 decimal places
    - Timestamps / dates -> ISO-format strings
    """
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), 6)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if isinstance(v, np.ndarray):
        return [_clean_value(x) for x in v.tolist()]
    return v


def _clean_dict(d: dict) -> dict:
    """Recursively clean a dict for JSON serialization."""
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            cleaned[k] = _clean_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [_clean_value(x) if not isinstance(x, dict) else _clean_dict(x) for x in v]
        else:
            cleaned[k] = _clean_value(v)
    return cleaned


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to a list of cleaned dicts."""
    records = df.to_dict(orient="records")
    return [_clean_dict(r) for r in records]


def _write_json(data: Any, filename: str) -> Path:
    """Write data to a JSON file in the output directory.

    Returns the path to the written file.
    """
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def _file_size_str(path: Path) -> str:
    """Human-readable file size."""
    size = path.stat().st_size
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


# ---------------------------------------------------------------------------
# Data loading (mirrors app/Home.py lines 54-77)
# ---------------------------------------------------------------------------

def load_all_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load stock prices and benchmark from Parquet files.

    Returns:
        Tuple of (stock_prices DataFrame, benchmark Series).

    Raises:
        SystemExit: If required data files are empty or missing.
    """
    logger.info("Loading data from Parquet files...")

    prices_df = load_parquet("daily_prices")
    benchmark_df = load_parquet("benchmark_prices")

    if prices_df.empty:
        logger.error("daily_prices.parquet is empty or missing. Run backfill first.")
        sys.exit(1)

    if benchmark_df.empty:
        logger.error("benchmark_prices.parquet is empty or missing. Run backfill first.")
        sys.exit(1)

    # Parse dates
    prices_df["date"] = pd.to_datetime(prices_df["date"])

    # Handle both wide and long format
    if "symbol" in prices_df.columns:
        stock_prices = prices_df.pivot_table(
            index="date", columns="symbol", values="close"
        )
    else:
        stock_prices = prices_df.set_index("date")

    # Filter to known tickers and drop all-NaN rows
    stock_cols = [c for c in stock_prices.columns if c in TOP_50_TICKERS]
    stock_prices = stock_prices[stock_cols].dropna(how="all")

    # Benchmark
    benchmark_df["date"] = pd.to_datetime(benchmark_df["date"])
    benchmark = benchmark_df.set_index("date")["close"]
    benchmark.name = "sp500"

    logger.info(
        "Loaded %d trading days, %d tickers, benchmark range %s to %s",
        len(stock_prices),
        len(stock_cols),
        stock_prices.index.min().date(),
        stock_prices.index.max().date(),
    )

    return stock_prices, benchmark


# ---------------------------------------------------------------------------
# Exporters for each JSON file
# ---------------------------------------------------------------------------

def export_meta(
    stock_prices: pd.DataFrame,
    benchmark: pd.Series,
) -> Path:
    """Generate meta.json with dataset metadata."""
    logger.info("Generating meta.json...")

    start_date = stock_prices.index.min()
    end_date = stock_prices.index.max()
    available_top20 = [t for t in TOP_20_TICKERS if t in stock_prices.columns]

    meta = {
        "last_updated": str(end_date.date()),
        "inception_date": str(INCEPTION_DATE),
        "n_trading_days": len(stock_prices),
        "date_range": {
            "start": str(start_date.date()),
            "end": str(end_date.date()),
        },
        "top_20_tickers": available_top20,
        "top_50_tickers": [t for t in TOP_50_TICKERS if t in stock_prices.columns],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return _write_json(meta, "meta.json")


def export_concentration_curve(
    stock_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
) -> Path:
    """Generate concentration_curve.json."""
    logger.info("Computing concentration curve...")

    curve = concentration_curve(stock_returns, benchmark_returns)

    if curve.empty:
        logger.warning("Concentration curve returned empty DataFrame")
        return _write_json({"curve": [], "r_squared_at_20": None}, "concentration_curve.json")

    # Extract R-squared at 20 stocks
    r2_at_20_rows = curve[curve["n_stocks"] == 20]["r_squared"]
    r2_at_20 = round(float(r2_at_20_rows.values[0]), 6) if len(r2_at_20_rows) > 0 else None

    payload = {
        "curve": _df_to_records(curve),
        "r_squared_at_20": r2_at_20,
    }

    return _write_json(payload, "concentration_curve.json")


def export_variance_decomposition(
    stock_returns: pd.DataFrame,
    benchmark_returns: pd.Series,
) -> Path:
    """Generate variance_decomposition.json."""
    logger.info("Computing variance decomposition...")

    var_decomp = variance_decomposition(stock_returns, benchmark_returns)

    if var_decomp.empty:
        logger.warning("Variance decomposition returned empty DataFrame")
        return _write_json({"decomposition": []}, "variance_decomposition.json")

    payload = {
        "decomposition": _df_to_records(var_decomp),
    }

    return _write_json(payload, "variance_decomposition.json")


def export_performance_nav(
    stock_prices: pd.DataFrame,
    benchmark: pd.Series,
    sp20_mirror: pd.DataFrame,
    sp20_equal: pd.DataFrame,
    benchmark_nav: pd.Series,
    mirror_nav: pd.Series,
    equal_nav: pd.Series,
) -> Path:
    """Generate performance_nav.json with weekly and recent daily NAV series."""
    logger.info("Building performance NAV data...")

    # --- Build combined NAV DataFrame (aligned on common dates) ---
    all_navs = pd.DataFrame({
        "sp500": benchmark_nav,
        "sp20_mirror": mirror_nav,
        "sp20_equal": equal_nav,
    }).dropna(how="all")

    # Forward-fill small gaps, then drop any remaining NaN rows
    all_navs = all_navs.ffill().dropna()

    # --- Weekly downsample: take every 5th trading day ---
    weekly_indices = list(range(0, len(all_navs), 5))
    # Always include the last data point
    if weekly_indices[-1] != len(all_navs) - 1:
        weekly_indices.append(len(all_navs) - 1)
    weekly = all_navs.iloc[weekly_indices].copy()

    weekly_records = []
    for date_val, row in weekly.iterrows():
        weekly_records.append({
            "date": str(date_val.date()),
            "sp500": _clean_value(row["sp500"]),
            "sp20_mirror": _clean_value(row["sp20_mirror"]),
            "sp20_equal": _clean_value(row["sp20_equal"]),
        })

    # --- Recent daily: last 252 trading days ---
    recent_n = min(252, len(all_navs))
    recent = all_navs.iloc[-recent_n:].copy()

    recent_records = []
    for date_val, row in recent.iterrows():
        recent_records.append({
            "date": str(date_val.date()),
            "sp500": _clean_value(row["sp500"]),
            "sp20_mirror": _clean_value(row["sp20_mirror"]),
            "sp20_equal": _clean_value(row["sp20_equal"]),
        })

    payload = {
        "weekly": weekly_records,
        "recent_daily": recent_records,
        "n_total_days": len(all_navs),
        "n_weekly_points": len(weekly_records),
        "n_recent_daily_points": len(recent_records),
    }

    return _write_json(payload, "performance_nav.json")


def _compute_extra_metrics(
    nav: pd.Series,
    benchmark_nav: pd.Series | None = None,
) -> dict:
    """Compute additional daily-return metrics not in compute_performance_metrics.

    Returns dict with keys: beta, alpha, information_ratio, best_day,
    worst_day, win_rate, avg_daily_return.
    """
    daily_returns = nav.pct_change().dropna()

    best_day = float(daily_returns.max()) if len(daily_returns) > 0 else 0.0
    worst_day = float(daily_returns.min()) if len(daily_returns) > 0 else 0.0
    win_rate = float((daily_returns > 0).mean()) if len(daily_returns) > 0 else 0.0
    avg_daily_return = float(daily_returns.mean()) if len(daily_returns) > 0 else 0.0

    beta = 1.0
    alpha = 0.0
    information_ratio = 0.0

    if benchmark_nav is not None:
        bench_returns = benchmark_nav.pct_change().dropna()
        # Align on common index
        common = daily_returns.index.intersection(bench_returns.index)
        if len(common) > 10:
            dr = daily_returns.loc[common]
            br = bench_returns.loc[common]
            bench_var = br.var()
            if bench_var > 0:
                beta = float(dr.cov(br) / bench_var)
            excess = dr - br
            excess_mean = float(excess.mean())
            excess_std = float(excess.std())
            alpha = excess_mean * 252  # annualised
            if excess_std > 0:
                information_ratio = (excess_mean / excess_std) * (252 ** 0.5)

    return {
        "beta": round(beta, 6),
        "alpha": round(alpha, 6),
        "information_ratio": round(information_ratio, 6),
        "best_day": round(best_day, 6),
        "worst_day": round(worst_day, 6),
        "win_rate": round(win_rate, 6),
        "avg_daily_return": round(avg_daily_return, 8),
    }


def export_performance_metrics(
    mirror_nav: pd.Series,
    equal_nav: pd.Series,
    benchmark_nav: pd.Series,
) -> Path:
    """Generate performance_metrics.json for all three indices."""
    logger.info("Computing performance metrics...")

    mirror_metrics = compute_performance_metrics(mirror_nav, benchmark_nav)
    equal_metrics = compute_performance_metrics(equal_nav, benchmark_nav)
    bench_metrics = compute_performance_metrics(benchmark_nav)

    # Enrich with extra daily-return metrics
    bench_extra = _compute_extra_metrics(benchmark_nav, None)
    mirror_extra = _compute_extra_metrics(mirror_nav, benchmark_nav)
    equal_extra = _compute_extra_metrics(equal_nav, benchmark_nav)

    bench_metrics.update(bench_extra)
    mirror_metrics.update(mirror_extra)
    equal_metrics.update(equal_extra)

    payload = {
        "sp500": _clean_dict(bench_metrics),
        "sp20_mirror": _clean_dict(mirror_metrics),
        "sp20_equal": _clean_dict(equal_metrics),
    }

    return _write_json(payload, "performance_metrics.json")


def export_holdings(stock_prices: pd.DataFrame) -> Path:
    """Generate holdings.json with current top-20 holdings and weights."""
    logger.info("Computing current holdings...")

    # Company names and sectors for display
    COMPANY_NAMES: dict[str, str] = {
        "AAPL": "Apple Inc.", "MSFT": "Microsoft Corp.", "NVDA": "NVIDIA Corp.",
        "AMZN": "Amazon.com Inc.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms Inc.",
        "BRK-B": "Berkshire Hathaway Inc.", "LLY": "Eli Lilly and Co.",
        "AVGO": "Broadcom Inc.", "JPM": "JPMorgan Chase & Co.", "TSLA": "Tesla Inc.",
        "UNH": "UnitedHealth Group Inc.", "V": "Visa Inc.", "XOM": "Exxon Mobil Corp.",
        "MA": "Mastercard Inc.", "COST": "Costco Wholesale Corp.",
        "PG": "Procter & Gamble Co.", "HD": "The Home Depot Inc.",
        "JNJ": "Johnson & Johnson", "WMT": "Walmart Inc.",
        "NFLX": "Netflix Inc.", "CRM": "Salesforce Inc.", "BAC": "Bank of America Corp.",
        "ABBV": "AbbVie Inc.", "CVX": "Chevron Corp.", "MRK": "Merck & Co. Inc.",
        "KO": "The Coca-Cola Co.", "AMD": "Advanced Micro Devices Inc.",
        "PEP": "PepsiCo Inc.", "TMO": "Thermo Fisher Scientific Inc.",
    }
    SECTORS: dict[str, str] = {
        "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
        "AMZN": "Consumer Discretionary", "GOOGL": "Communication Services",
        "META": "Communication Services", "BRK-B": "Financials",
        "LLY": "Health Care", "AVGO": "Technology", "JPM": "Financials",
        "TSLA": "Consumer Discretionary", "UNH": "Health Care",
        "V": "Financials", "XOM": "Energy", "MA": "Financials",
        "COST": "Consumer Staples", "PG": "Consumer Staples",
        "HD": "Consumer Discretionary", "JNJ": "Health Care",
        "WMT": "Consumer Staples", "NFLX": "Communication Services",
        "CRM": "Technology", "BAC": "Financials", "ABBV": "Health Care",
        "CVX": "Energy", "MRK": "Health Care", "KO": "Consumer Staples",
        "AMD": "Technology", "PEP": "Consumer Staples", "TMO": "Health Care",
    }

    available_top20 = [t for t in TOP_20_TICKERS if t in stock_prices.columns]
    last_prices = stock_prices[available_top20].iloc[-1]
    weights = last_prices / last_prices.sum()

    holdings = []
    for ticker in weights.sort_values(ascending=False).index:
        holdings.append({
            "ticker": ticker,
            "name": COMPANY_NAMES.get(ticker, ticker),
            "weight": _clean_value(weights[ticker]),
            "sector": SECTORS.get(ticker, ""),
            "last_price": _clean_value(last_prices[ticker]),
        })

    payload = {
        "as_of": str(stock_prices.index.max().date()),
        "n_holdings": len(holdings),
        "holdings": holdings,
    }

    return _write_json(payload, "holdings.json")


def export_drawdowns(
    benchmark_nav: pd.Series,
    mirror_nav: pd.Series,
    equal_nav: pd.Series,
) -> Path:
    """Generate drawdowns.json with weekly-downsampled drawdown series."""
    logger.info("Computing drawdown series...")

    # Compute drawdown from peak
    dd_bench = benchmark_nav / benchmark_nav.cummax() - 1
    dd_mirror = mirror_nav / mirror_nav.cummax() - 1
    dd_equal = equal_nav / equal_nav.cummax() - 1

    # Align on common dates
    dd = pd.DataFrame({
        "sp500": dd_bench,
        "sp20_mirror": dd_mirror,
        "sp20_equal": dd_equal,
    }).dropna(how="all").ffill().dropna()

    # Downsample to weekly (every 5th trading day)
    weekly_indices = list(range(0, len(dd), 5))
    if weekly_indices[-1] != len(dd) - 1:
        weekly_indices.append(len(dd) - 1)
    weekly_dd = dd.iloc[weekly_indices]

    records = []
    for date_val, row in weekly_dd.iterrows():
        records.append({
            "date": str(date_val.date()),
            "sp500": _clean_value(row["sp500"]),
            "sp20_mirror": _clean_value(row["sp20_mirror"]),
            "sp20_equal": _clean_value(row["sp20_equal"]),
        })

    # Summary stats
    payload = {
        "weekly": records,
        "n_points": len(records),
        "max_drawdown_sp500": _clean_value(dd["sp500"].min()),
        "max_drawdown_sp20_mirror": _clean_value(dd["sp20_mirror"].min()),
        "max_drawdown_sp20_equal": _clean_value(dd["sp20_equal"].min()),
        "max_drawdown_date_sp500": str(dd["sp500"].idxmin().date()),
        "max_drawdown_date_sp20_mirror": str(dd["sp20_mirror"].idxmin().date()),
    }

    return _write_json(payload, "drawdowns.json")


def export_daily_deviations(
    sp20_mirror: pd.DataFrame,
    benchmark_returns: pd.Series,
) -> Path:
    """Generate daily_deviations.json with histogram of daily return differences."""
    logger.info("Computing daily deviation histogram...")

    # Extract mirror daily returns
    mirror_daily = sp20_mirror.set_index(
        pd.to_datetime(sp20_mirror["date"])
    )["daily_return"]

    # Align with benchmark returns on common dates
    common_idx = mirror_daily.index.intersection(benchmark_returns.index)
    mirror_aligned = mirror_daily.loc[common_idx].values
    bench_aligned = benchmark_returns.loc[common_idx].values

    # Compute deviations
    deviations = mirror_aligned - bench_aligned

    # Remove NaN values
    deviations = deviations[~np.isnan(deviations)]

    # Convert to percentage points for readability
    deviations_pct = deviations * 100.0

    # Compute histogram with numpy
    n_bins = 50
    counts, bin_edges = np.histogram(deviations_pct, bins=n_bins)

    # Build bin centers and records
    bins = []
    for i in range(len(counts)):
        bins.append({
            "bin_start": round(float(bin_edges[i]), 4),
            "bin_end": round(float(bin_edges[i + 1]), 4),
            "bin_center": round(float((bin_edges[i] + bin_edges[i + 1]) / 2), 4),
            "count": int(counts[i]),
        })

    # Summary statistics on the deviation (in percentage points)
    payload = {
        "bins": bins,
        "n_observations": int(len(deviations)),
        "unit": "percentage_points",
        "stats": {
            "mean": round(float(np.mean(deviations_pct)), 4),
            "std": round(float(np.std(deviations_pct)), 4),
            "median": round(float(np.median(deviations_pct)), 4),
            "min": round(float(np.min(deviations_pct)), 4),
            "max": round(float(np.max(deviations_pct)), 4),
            "skewness": round(float(pd.Series(deviations_pct).skew()), 4),
            "kurtosis": round(float(pd.Series(deviations_pct).kurtosis()), 4),
        },
    }

    return _write_json(payload, "daily_deviations.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run all data exports and print a summary."""
    logger.info("=" * 60)
    logger.info("SP Index Lab -- Frontend Data Export")
    logger.info("=" * 60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", OUTPUT_DIR)

    # ------------------------------------------------------------------
    # 1. Load raw data
    # ------------------------------------------------------------------
    stock_prices, benchmark = load_all_data()

    # ------------------------------------------------------------------
    # 2. Compute derived data (mirrors app/Home.py)
    # ------------------------------------------------------------------
    stock_returns = stock_prices.pct_change(fill_method=None).dropna(how="all")
    benchmark_returns = benchmark.pct_change().dropna()
    benchmark_nav = benchmark / benchmark.iloc[0]

    logger.info("Building SP-20 Mirror (cap-weighted)...")
    sp20_mirror = build_mirror_index(stock_prices, top_n=20, weighting="cap")

    logger.info("Building SP-20 Equal (equal-weighted)...")
    sp20_equal = build_mirror_index(stock_prices, top_n=20, weighting="equal")

    # Build NAV Series with DatetimeIndex for alignment
    mirror_nav = pd.Series(
        sp20_mirror["nav"].values,
        index=pd.to_datetime(sp20_mirror["date"]),
        name="sp20_mirror",
    )
    equal_nav = pd.Series(
        sp20_equal["nav"].values,
        index=pd.to_datetime(sp20_equal["date"]),
        name="sp20_equal",
    )

    # ------------------------------------------------------------------
    # 3. Export each JSON file
    # ------------------------------------------------------------------
    written_files: list[Path] = []

    written_files.append(export_meta(stock_prices, benchmark))
    written_files.append(
        export_concentration_curve(stock_returns, benchmark_returns)
    )
    written_files.append(
        export_variance_decomposition(stock_returns, benchmark_returns)
    )
    written_files.append(
        export_performance_nav(
            stock_prices, benchmark,
            sp20_mirror, sp20_equal,
            benchmark_nav, mirror_nav, equal_nav,
        )
    )
    written_files.append(
        export_performance_metrics(mirror_nav, equal_nav, benchmark_nav)
    )
    written_files.append(export_holdings(stock_prices))
    written_files.append(export_drawdowns(benchmark_nav, mirror_nav, equal_nav))
    written_files.append(
        export_daily_deviations(sp20_mirror, benchmark_returns)
    )

    # ------------------------------------------------------------------
    # 4. Print summary
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("=" * 60)
    logger.info("Export complete. Files written:")
    logger.info("=" * 60)

    total_size = 0
    for fpath in written_files:
        size_str = _file_size_str(fpath)
        total_size += fpath.stat().st_size
        logger.info("  %-35s  %s", fpath.name, size_str)

    if total_size < 1024 * 1024:
        total_str = f"{total_size / 1024:.1f} KB"
    else:
        total_str = f"{total_size / (1024 * 1024):.1f} MB"

    logger.info("-" * 60)
    logger.info("  %-35s  %s", "TOTAL", total_str)
    logger.info("=" * 60)
    logger.info("Output directory: %s", OUTPUT_DIR)

    return 0


if __name__ == "__main__":
    sys.exit(main())
