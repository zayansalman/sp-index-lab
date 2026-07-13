"""Refresh the effective-shares-outstanding anchor for cap-proxy ranking.

Fetches today's market cap and price for every candidate-pool ticker and
stores effective shares (market_cap / price). The point-in-time universe
ranking multiplies these by historical adjusted closes to estimate
historical market caps. Effective shares capture multi-class structures
(BRK-B, GOOGL) that raw sharesOutstanding misses.

Run occasionally (shares drift ~1-3%/yr from buybacks/issuance) and commit
the refreshed CSV.

Usage:
    uv run python scripts/update_shares_outstanding.py
"""

import logging
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CANDIDATE_POOL_TICKERS, REFERENCE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_CSV = REFERENCE_DIR / "shares_outstanding.csv"


def main() -> int:
    """Fetch market caps and write the effective-shares anchor CSV."""
    records: list[dict[str, object]] = []
    as_of = date.today().isoformat()

    for ticker in CANDIDATE_POOL_TICKERS:
        try:
            fast = yf.Ticker(ticker).fast_info
            market_cap = float(fast["market_cap"])
            price = float(fast["last_price"])
            if market_cap <= 0 or price <= 0:
                raise ValueError(f"non-positive cap/price: {market_cap}, {price}")
            records.append({
                "ticker": ticker,
                "effective_shares": round(market_cap / price),
                "market_cap": round(market_cap),
                "as_of": as_of,
            })
            logger.info("%s: cap=%.0fB", ticker, market_cap / 1e9)
        except Exception:
            logger.exception("Failed to fetch %s — skipping", ticker)
        time.sleep(0.25)

    df = pd.DataFrame(records).sort_values("ticker")
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info("Wrote %d tickers to %s", len(df), OUTPUT_CSV)

    missing = set(CANDIDATE_POOL_TICKERS) - set(df["ticker"])
    if missing:
        logger.warning("Missing tickers (rerun or investigate): %s", sorted(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
