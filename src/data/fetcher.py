"""Market data fetcher with retries, rate limiting, and validation.

Single source of truth for all external data. Wraps yfinance with
production-grade error handling, data quality checks, and logging.
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from src.config import (
    BENCHMARK_TICKER,
    INCEPTION_DATE,
    RISK_FREE_TICKER,
    TOP_50_TICKERS,
    TRADING_DAYS_PER_YEAR,
    TREASURY_10Y_TICKER,
    VIX_TICKER,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # Exponential backoff: 2s, 4s, 8s
_RATE_LIMIT_DELAY = 0.25  # Seconds between consecutive API calls
_LAST_CALL_TIME: float = 0.0

# Data quality thresholds
_MAX_CONSECUTIVE_NANS = 5
_MAX_NAN_RATIO = 0.05  # 5% of rows
_MIN_PRICE = 0.01
_MAX_DAILY_RETURN = 1.0  # 100% single-day move is suspicious


# ──────────────────────────────────────────────
# Rate limiting
# ──────────────────────────────────────────────


def _rate_limit() -> None:
    """Enforce minimum delay between API calls."""
    global _LAST_CALL_TIME
    elapsed = time.monotonic() - _LAST_CALL_TIME
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    _LAST_CALL_TIME = time.monotonic()


# ──────────────────────────────────────────────
# Core fetch with retries
# ──────────────────────────────────────────────


def _fetch_with_retries(
    tickers: list[str],
    start: str,
    end: str,
    **kwargs: Any,
) -> pd.DataFrame:
    """Download data from yfinance with exponential backoff retries.

    Args:
        tickers: List of ticker symbols.
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).
        **kwargs: Additional arguments passed to yf.download.

    Returns:
        Raw DataFrame from yfinance.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            _rate_limit()
            logger.info(
                "Fetching %d tickers (%s to %s), attempt %d/%d",
                len(tickers),
                start,
                end,
                attempt,
                _MAX_RETRIES,
            )
            df = yf.download(
                tickers=tickers,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
                threads=False,  # Sequential for reliability
                **kwargs,
            )
            if df.empty:
                raise ValueError("yfinance returned an empty DataFrame")
            return df

        except Exception as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "Attempt %d failed: %s. Retrying in %.1fs...",
                    attempt,
                    str(e),
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error("All %d attempts failed for tickers: %s", _MAX_RETRIES, tickers)

    raise RuntimeError(
        f"Failed to fetch data after {_MAX_RETRIES} attempts: {last_error}"
    )


# ──────────────────────────────────────────────
# Data validation
# ──────────────────────────────────────────────


class DataQualityError(Exception):
    """Raised when fetched data fails quality checks."""


def _validate_prices(df: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Run quality checks on price data and return cleaned DataFrame.

    Checks performed:
        1. No missing tickers (warns, does not fail).
        2. NaN ratio within acceptable bounds.
        3. No consecutive NaN streaks beyond threshold.
        4. No negative or zero prices.
        5. No impossible single-day returns.
        6. Forward-fill small gaps, drop remaining NaNs.

    Args:
        df: Raw price DataFrame (DatetimeIndex, ticker columns).
        tickers: Expected ticker symbols.

    Returns:
        Validated and cleaned DataFrame.

    Raises:
        DataQualityError: If data fails critical quality checks.
    """
    issues: list[str] = []

    # Check for missing tickers
    present = set(df.columns.tolist())
    missing = set(tickers) - present
    if missing:
        logger.warning("Missing tickers in response: %s", sorted(missing))

    available_tickers = [t for t in tickers if t in present]
    if not available_tickers:
        raise DataQualityError("No valid tickers returned from API")

    df = df[available_tickers].copy()

    # Check NaN ratio per ticker
    for ticker in available_tickers:
        nan_ratio = df[ticker].isna().mean()
        if nan_ratio > _MAX_NAN_RATIO:
            issues.append(f"{ticker}: {nan_ratio:.1%} NaN values (threshold: {_MAX_NAN_RATIO:.0%})")

        # Check consecutive NaN streaks
        is_nan = df[ticker].isna()
        if is_nan.any() and not is_nan.all():
            # Group consecutive NaNs: label each run, filter to NaN runs, get max length
            groups = (~is_nan).cumsum()
            nan_runs = is_nan.groupby(groups).sum()
            max_streak = int(nan_runs.max()) if len(nan_runs) > 0 else 0
            if max_streak > _MAX_CONSECUTIVE_NANS:
                issues.append(
                    f"{ticker}: {max_streak} consecutive NaNs "
                    f"(threshold: {_MAX_CONSECUTIVE_NANS})"
                )

    if issues:
        for issue in issues:
            logger.warning("Data quality issue: %s", issue)

    # Forward-fill small gaps (weekends, holidays already excluded by yfinance)
    df = df.ffill(limit=3)

    # Check for non-positive prices
    negative_mask = df <= _MIN_PRICE
    if negative_mask.any().any():
        bad_tickers = df.columns[negative_mask.any()].tolist()
        logger.warning("Non-positive prices found in: %s. Setting to NaN.", bad_tickers)
        df = df.where(df > _MIN_PRICE)

    # Check for impossible daily returns
    returns = df.pct_change(fill_method=None).abs()
    extreme_mask = returns > _MAX_DAILY_RETURN
    if extreme_mask.any().any():
        for ticker in df.columns:
            extreme_dates = returns.index[extreme_mask[ticker]].tolist()
            if extreme_dates:
                logger.warning(
                    "%s: Extreme returns (>100%%) on %s. Review manually.",
                    ticker,
                    [d.strftime("%Y-%m-%d") for d in extreme_dates[:5]],
                )

    # Drop rows that are still NaN after forward-fill
    initial_rows = len(df)
    df = df.dropna(how="all")
    dropped = initial_rows - len(df)
    if dropped > 0:
        logger.info("Dropped %d all-NaN rows after cleaning", dropped)

    logger.info(
        "Validation complete: %d tickers, %d rows, %.2f%% NaN remaining",
        len(df.columns),
        len(df),
        df.isna().mean().mean() * 100,
    )

    return df


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def fetch_daily_prices(
    tickers: list[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
) -> pd.DataFrame:
    """Fetch adjusted daily close prices for the given tickers.

    Args:
        tickers: List of ticker symbols. Defaults to TOP_50_TICKERS.
        start: Start date. Defaults to INCEPTION_DATE.
        end: End date. Defaults to today.

    Returns:
        DataFrame with DatetimeIndex and one column per ticker (adjusted close).
    """
    tickers = tickers or TOP_50_TICKERS
    start_str = str(start or INCEPTION_DATE)
    end_str = str(end or date.today())

    raw = _fetch_with_retries(tickers, start_str, end_str)

    # yfinance returns MultiIndex columns for multiple tickers: (field, ticker)
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
    else:
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]}) if len(tickers) == 1 else raw

    # Ensure we have a clean DataFrame: DatetimeIndex + ticker columns
    if isinstance(prices.columns, pd.MultiIndex):
        prices.columns = prices.columns.get_level_values(-1)

    prices = _validate_prices(prices, tickers)
    prices.index.name = "date"
    return prices


def fetch_benchmark(
    start: date | str | None = None,
    end: date | str | None = None,
) -> pd.Series:
    """Fetch S&P 500 daily close prices.

    Returns:
        Series with DatetimeIndex named "sp500".
    """
    prices = fetch_daily_prices(
        tickers=[BENCHMARK_TICKER],
        start=start,
        end=end,
    )
    series = prices.iloc[:, 0]
    series.name = "sp500"
    return series


def fetch_market_indicators(
    start: date | str | None = None,
    end: date | str | None = None,
) -> pd.DataFrame:
    """Fetch VIX, risk-free rate, and 10Y Treasury yield.

    Returns:
        DataFrame with columns: vix, risk_free, treasury_10y.
    """
    tickers = [VIX_TICKER, RISK_FREE_TICKER, TREASURY_10Y_TICKER]
    raw = _fetch_with_retries(tickers, str(start or INCEPTION_DATE), str(end or date.today()))

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw

    rename_map = {
        VIX_TICKER: "vix",
        RISK_FREE_TICKER: "risk_free",
        TREASURY_10Y_TICKER: "treasury_10y",
    }
    # Handle both MultiIndex and flat columns
    if isinstance(prices.columns, pd.MultiIndex):
        prices.columns = prices.columns.get_level_values(-1)

    prices = prices.rename(columns=rename_map)
    prices = prices.ffill(limit=5)
    prices.index.name = "date"
    return prices


def fetch_incremental(
    tickers: list[str] | None = None,
    last_date: date | str | None = None,
) -> pd.DataFrame:
    """Fetch only new data since last_date.

    Used by the daily update pipeline to avoid re-downloading history.

    Args:
        tickers: Ticker symbols. Defaults to TOP_50_TICKERS.
        last_date: Last date already in the database. Fetches from the next day.

    Returns:
        DataFrame of new rows only (may be empty if already up to date).
    """
    tickers = tickers or TOP_50_TICKERS

    if last_date is None:
        start = INCEPTION_DATE
    elif isinstance(last_date, str):
        start = datetime.strptime(last_date, "%Y-%m-%d").date() + timedelta(days=1)
    else:
        start = last_date + timedelta(days=1)

    today = date.today()
    if start > today:
        logger.info("Data is already up to date (last: %s, today: %s)", last_date, today)
        return pd.DataFrame()

    return fetch_daily_prices(tickers=tickers, start=start, end=today)


def prices_to_long_format(prices_wide: pd.DataFrame) -> pd.DataFrame:
    """Convert wide price DataFrame to long format for database storage.

    Args:
        prices_wide: DataFrame with DatetimeIndex and ticker columns.

    Returns:
        DataFrame with columns: date, symbol, close.
    """
    df = prices_wide.reset_index().melt(
        id_vars="date",
        var_name="symbol",
        value_name="close",
    )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.dropna(subset=["close"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    return df
