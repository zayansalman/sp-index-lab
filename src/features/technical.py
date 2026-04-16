"""Technical feature computation for the factor model.

All functions accept a wide-format price DataFrame (DatetimeIndex × tickers)
and return a similarly-shaped DataFrame of feature values.  Computations are
fully vectorised — no ``iterrows``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_momentum(
    prices: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Trailing total-return momentum over multiple lookback windows.

    Args:
        prices: Adjusted-close prices (DatetimeIndex × tickers).
        windows: Lookback windows in trading days.  Defaults to
            [21, 63, 126, 252] (~1M, 3M, 6M, 12M).

    Returns:
        DataFrame with MultiIndex columns (ticker, window) containing the
        percentage return over each lookback.
    """
    if windows is None:
        windows = [21, 63, 126, 252]

    parts: dict[int, pd.DataFrame] = {}
    for w in windows:
        parts[w] = prices.pct_change(periods=w)

    return pd.concat(parts, axis=1, names=["window", "ticker"])


def compute_realized_vol(
    prices: pd.DataFrame,
    window: int = 21,
) -> pd.DataFrame:
    """Rolling annualised realised volatility.

    Args:
        prices: Adjusted-close prices.
        window: Lookback window in trading days (default 21 ≈ 1 month).

    Returns:
        DataFrame of annualised volatility per ticker.
    """
    daily_returns = prices.pct_change()
    return daily_returns.rolling(window).std() * np.sqrt(252)


def compute_rsi(
    prices: pd.DataFrame,
    window: int = 14,
) -> pd.DataFrame:
    """Relative Strength Index (Wilder smoothing).

    Args:
        prices: Adjusted-close prices.
        window: RSI lookback (default 14).

    Returns:
        DataFrame of RSI values in [0, 100].
    """
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_ma_distance(
    prices: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Percentage distance of price from moving averages.

    Args:
        prices: Adjusted-close prices.
        windows: MA periods.  Defaults to [50, 200].

    Returns:
        DataFrame with MultiIndex columns (ticker, window) where values are
        ``(price - MA) / MA`` as a fraction.
    """
    if windows is None:
        windows = [50, 200]

    parts: dict[int, pd.DataFrame] = {}
    for w in windows:
        ma = prices.rolling(w).mean()
        parts[w] = (prices - ma) / ma

    return pd.concat(parts, axis=1, names=["window", "ticker"])


def build_feature_matrix(
    prices: pd.DataFrame,
    *,
    momentum_windows: list[int] | None = None,
    vol_window: int = 21,
    rsi_window: int = 14,
    ma_windows: list[int] | None = None,
) -> pd.DataFrame:
    """Build a flat feature matrix suitable for cross-sectional ML models.

    Stacks all tickers into rows with columns for each feature.  The returned
    DataFrame is indexed by ``(date, ticker)`` and has one column per feature.

    Args:
        prices: Wide price DataFrame (DatetimeIndex × tickers).
        momentum_windows: Passed to :func:`compute_momentum`.
        vol_window: Passed to :func:`compute_realized_vol`.
        rsi_window: Passed to :func:`compute_rsi`.
        ma_windows: Passed to :func:`compute_ma_distance`.

    Returns:
        Long-format DataFrame indexed by ``(date, ticker)`` with feature
        columns: ``mom_21, mom_63, …, vol_21, rsi_14, ma_dist_50, …``
    """
    if momentum_windows is None:
        momentum_windows = [21, 63, 126, 252]
    if ma_windows is None:
        ma_windows = [50, 200]

    tickers = prices.columns.tolist()
    dates = prices.index

    # Momentum — multi-window
    mom = compute_momentum(prices, momentum_windows)

    # Volatility
    vol = compute_realized_vol(prices, vol_window)

    # RSI
    rsi = compute_rsi(prices, rsi_window)

    # MA distance — multi-window
    ma_dist = compute_ma_distance(prices, ma_windows)

    # Stack into long format (date, ticker) rows
    records: list[pd.DataFrame] = []

    for ticker in tickers:
        df = pd.DataFrame(index=dates)
        for w in momentum_windows:
            df[f"mom_{w}"] = mom[(w, ticker)]
        df[f"vol_{vol_window}"] = vol[ticker]
        df[f"rsi_{rsi_window}"] = rsi[ticker]
        for w in ma_windows:
            df[f"ma_dist_{w}"] = ma_dist[(w, ticker)]
        df["ticker"] = ticker
        records.append(df)

    result = pd.concat(records)
    result.index.name = "date"
    result = result.reset_index().set_index(["date", "ticker"]).sort_index()
    return result
