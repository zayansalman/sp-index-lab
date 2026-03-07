"""Storage helpers for Supabase (remote) and Parquet (local cache).

All database reads/writes go through this module. The dashboard reads
from Parquet for speed; the daily update writes to both Supabase and Parquet.
"""

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

from src.config import DATA_DIR, PARQUET_FILES

load_dotenv()

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Supabase client
# ──────────────────────────────────────────────

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Return a cached Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment or .env file."
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


# ──────────────────────────────────────────────
# Supabase read / write
# ──────────────────────────────────────────────


def upsert_rows(table: str, rows: list[dict[str, Any]]) -> None:
    """Upsert rows into a Supabase table.

    Args:
        table: Name of the Supabase table.
        rows: List of dicts matching the table schema.
    """
    if not rows:
        return
    client = get_supabase_client()
    # Supabase upsert handles INSERT ... ON CONFLICT UPDATE
    client.table(table).upsert(rows).execute()
    logger.info("Upserted %d rows into %s", len(rows), table)


def fetch_table(
    table: str,
    columns: str = "*",
    filters: dict[str, Any] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Fetch rows from a Supabase table into a DataFrame.

    Args:
        table: Name of the Supabase table.
        columns: Comma-separated column names (default "*").
        filters: Dict of {column: value} equality filters.
        order_by: Column to order by (prefix with "-" for desc).
        limit: Max rows to return.

    Returns:
        DataFrame with the query results.
    """
    client = get_supabase_client()
    query = client.table(table).select(columns)

    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)

    if order_by:
        desc = order_by.startswith("-")
        col = order_by.lstrip("-")
        query = query.order(col, desc=desc)

    if limit:
        query = query.limit(limit)

    response = query.execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()


# ──────────────────────────────────────────────
# Parquet read / write
# ──────────────────────────────────────────────


def save_parquet(df: pd.DataFrame, name: str) -> Path:
    """Save a DataFrame to the project's Parquet cache.

    Args:
        df: DataFrame to save.
        name: Key from PARQUET_FILES (e.g. "daily_prices") or a full Path.

    Returns:
        Path to the written file.
    """
    path = PARQUET_FILES.get(name, DATA_DIR / f"{name}.parquet")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow")
    logger.info("Saved %d rows to %s", len(df), path)
    return path


def load_parquet(name: str) -> pd.DataFrame:
    """Load a DataFrame from the project's Parquet cache.

    Args:
        name: Key from PARQUET_FILES (e.g. "daily_prices") or a filename.

    Returns:
        DataFrame read from Parquet. Empty DataFrame if file does not exist.
    """
    path = PARQUET_FILES.get(name, DATA_DIR / f"{name}.parquet")
    if not path.exists():
        logger.warning("Parquet file not found: %s", path)
        return pd.DataFrame()
    df = pd.read_parquet(path, engine="pyarrow")
    logger.info("Loaded %d rows from %s", len(df), path)
    return df


# ──────────────────────────────────────────────
# Convenience: sync Supabase → Parquet
# ──────────────────────────────────────────────


def sync_table_to_parquet(table: str) -> Path:
    """Fetch an entire Supabase table and save it as Parquet.

    Args:
        table: Name of the Supabase table (must also be a PARQUET_FILES key).

    Returns:
        Path to the written Parquet file.
    """
    df = fetch_table(table)
    return save_parquet(df, table)


def df_to_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to a list of dicts suitable for Supabase upsert.

    Handles NaN → None conversion and date serialisation.
    """
    # Replace NaN with None for JSON compatibility
    df = df.where(pd.notnull(df), None)
    rows = df.to_dict(orient="records")
    # Convert date/datetime objects to ISO strings
    for row in rows:
        for k, v in row.items():
            if isinstance(v, (pd.Timestamp,)):
                row[k] = v.isoformat()
    return rows
