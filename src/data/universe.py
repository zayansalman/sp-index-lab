"""Point-in-time S&P 500 universe: membership and market-cap-proxy ranking.

Historical universe selection must use only information available at the
time. Membership comes from vendored constituent snapshots
(``data/reference/sp500_membership.csv``); ranking uses trailing average
dollar volume (close × volume) as a market-cap proxy, since free sources do
not provide historical shares outstanding.

Every function that ranks or selects takes an ``as_of`` date and never reads
data after it — the no-look-ahead invariant is enforced by slicing before
computing and is covered by tests (``tests/test_universe.py``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pandas as pd

from src.config import REFERENCE_DIR, UNIVERSE_LOOKBACK_DAYS, UNIVERSE_MIN_OBS

logger = logging.getLogger(__name__)

MEMBERSHIP_CSV = REFERENCE_DIR / "sp500_membership.csv"
ALIASES_CSV = REFERENCE_DIR / "ticker_aliases.csv"
EXCLUSIONS_CSV = REFERENCE_DIR / "excluded_tickers.csv"

_membership_cache: dict[Path, pd.DataFrame] = {}


def _load_aliases(path: Path = ALIASES_CSV) -> dict[str, str]:
    """Load membership-ticker → yfinance-ticker alias map."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    return dict(zip(df["membership_ticker"], df["yf_ticker"]))


def _load_exclusions(path: Path = EXCLUSIONS_CSV) -> set[str]:
    """Load tickers whose history yfinance cannot serve."""
    if not path.exists():
        return set()
    return set(pd.read_csv(path)["ticker"])


def load_membership(
    path: Path = MEMBERSHIP_CSV,
    aliases_path: Path = ALIASES_CSV,
    exclusions_path: Path = EXCLUSIONS_CSV,
) -> pd.DataFrame:
    """Load constituent snapshots as a long DataFrame of [date, ticker].

    Tickers are normalised to yfinance symbols: class-share dots become
    dashes (BRK.B → BRK-B), renames/mergers map to the surviving symbol
    (FB → META), duplicate class shares collapse to one line per company,
    and unservable delisted names are dropped.

    Args:
        path: Snapshot CSV with columns ``date`` and comma-separated
            ``tickers``, one row per membership change date.
        aliases_path: Alias CSV (membership_ticker, yf_ticker, note).
        exclusions_path: Exclusion CSV (ticker, reason, last_date).

    Returns:
        DataFrame with columns ``date`` (Timestamp) and ``ticker`` (str),
        sorted by date; one row per (snapshot date, member).
    """
    raw = pd.read_csv(path, parse_dates=["date"])
    aliases = _load_aliases(aliases_path)
    exclusions = _load_exclusions(exclusions_path)

    long = raw.assign(ticker=raw["tickers"].str.split(",")).explode("ticker")
    long["ticker"] = long["ticker"].str.strip().str.replace(".", "-", regex=False)
    long["ticker"] = long["ticker"].map(lambda t: aliases.get(t, t))
    long = long[~long["ticker"].isin(exclusions)]
    long = long.drop_duplicates(subset=["date", "ticker"])

    return long[["date", "ticker"]].sort_values("date").reset_index(drop=True)


def _default_membership() -> pd.DataFrame:
    """Return the vendored membership table, cached per process."""
    if MEMBERSHIP_CSV not in _membership_cache:
        _membership_cache[MEMBERSHIP_CSV] = load_membership()
    return _membership_cache[MEMBERSHIP_CSV]


def get_members_at(
    as_of: pd.Timestamp,
    membership: pd.DataFrame | None = None,
) -> set[str]:
    """Return the S&P 500 member set as of a date.

    Uses the most recent snapshot on or before ``as_of``.

    Raises:
        ValueError: If ``as_of`` predates the first snapshot.
    """
    membership = membership if membership is not None else _default_membership()
    as_of = pd.Timestamp(as_of)

    snapshot_dates = membership["date"]
    eligible = snapshot_dates[snapshot_dates <= as_of]
    if eligible.empty:
        raise ValueError(
            f"No membership snapshot on or before {as_of.date()} "
            f"(earliest: {snapshot_dates.min().date()})"
        )
    snapshot = eligible.max()
    return set(membership.loc[membership["date"] == snapshot, "ticker"])


def rank_by_dollar_volume(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    as_of: pd.Timestamp,
    lookback: int = UNIVERSE_LOOKBACK_DAYS,
    min_obs: int = UNIVERSE_MIN_OBS,
) -> pd.Series:
    """Rank tickers by trailing average dollar volume using data ≤ as_of.

    Dollar volume (close × volume) is the market-cap proxy: it is computable
    from the data we already fetch, works identically for live and delisted
    names, and is monotone-ish in cap for mega-caps. Known distortion:
    over-ranks high-turnover names, under-ranks low-turnover giants (BRK-B).

    Args:
        prices: Wide close-price DataFrame (DatetimeIndex × tickers).
        volumes: Wide share-volume DataFrame, same shape.
        as_of: Ranking date; no data after this date is used.
        lookback: Trailing window length in trading days.
        min_obs: Minimum non-NaN days required to rank a ticker.

    Returns:
        Average dollar volume per ticker, descending; tickers with
        insufficient history are omitted.
    """
    as_of = pd.Timestamp(as_of)
    # Slice FIRST so nothing after as_of can influence the ranking.
    price_window = prices.loc[prices.index <= as_of].tail(lookback)
    volume_window = volumes.loc[volumes.index <= as_of].tail(lookback)

    common = price_window.columns.intersection(volume_window.columns)
    dollar = price_window[common] * volume_window[common]

    counts = dollar.notna().sum()
    avg = dollar.mean().where(counts >= min_obs)
    return avg.dropna().sort_values(ascending=False)


def get_top_n_at(
    as_of: pd.Timestamp,
    n: int,
    *,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    membership: pd.DataFrame | None = None,
    lookback: int = UNIVERSE_LOOKBACK_DAYS,
) -> list[str]:
    """Return the point-in-time top-N tickers as of a date.

    Intersects the fetched candidate columns with the S&P membership at
    ``as_of``, ranks by trailing dollar volume, and returns the first N.
    If fewer than N members have sufficient data (e.g. an unservable
    delisted name), the next-ranked names fill in and a warning is logged.
    """
    members = get_members_at(as_of, membership)
    ranked = rank_by_dollar_volume(prices, volumes, as_of, lookback=lookback)
    top = [t for t in ranked.index if t in members][:n]

    if len(top) < n:
        logger.warning(
            "Only %d of %d requested tickers available at %s "
            "(candidate pool or membership coverage gap)",
            len(top),
            n,
            pd.Timestamp(as_of).date(),
        )
    return top


def build_universe_schedule(
    rebalance_dates: pd.DatetimeIndex,
    n: int,
    *,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    membership: pd.DataFrame | None = None,
    lookback: int = UNIVERSE_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """Compute the top-N universe at each rebalance date.

    Returns:
        Long DataFrame with columns
        ``rebalance_date, rank, ticker, avg_dollar_volume`` — an auditable
        record of which names were selectable when.
    """
    membership = membership if membership is not None else _default_membership()
    records: list[dict[str, object]] = []

    for rebalance_date in rebalance_dates:
        members = get_members_at(rebalance_date, membership)
        ranked = rank_by_dollar_volume(prices, volumes, rebalance_date, lookback=lookback)
        member_ranked = ranked[ranked.index.isin(members)].head(n)
        for rank, (ticker, adv) in enumerate(member_ranked.items(), start=1):
            records.append({
                "rebalance_date": rebalance_date,
                "rank": rank,
                "ticker": ticker,
                "avg_dollar_volume": float(adv),
            })

    return pd.DataFrame(records)


def make_universe_fn(
    n: int,
    *,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    membership: pd.DataFrame | None = None,
    lookback: int = UNIVERSE_LOOKBACK_DAYS,
) -> Callable[[pd.Timestamp], list[str]]:
    """Return a memoised ``as_of → top-N tickers`` callable for backtests."""
    membership = membership if membership is not None else _default_membership()
    cache: dict[pd.Timestamp, list[str]] = {}

    def universe_fn(as_of: pd.Timestamp) -> list[str]:
        as_of = pd.Timestamp(as_of)
        if as_of not in cache:
            cache[as_of] = get_top_n_at(
                as_of,
                n,
                prices=prices,
                volumes=volumes,
                membership=membership,
                lookback=lookback,
            )
        return cache[as_of]

    return universe_fn
