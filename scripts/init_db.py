"""Initialize Supabase database tables for SP Index Lab.

Run once to create all required tables. Safe to re-run (uses IF NOT EXISTS).

Usage:
    uv run python scripts/init_db.py
"""

import logging
import os
import sys

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# SQL statements to create all project tables.
CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS daily_prices (
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        open NUMERIC(12, 4),
        high NUMERIC(12, 4),
        low NUMERIC(12, 4),
        close NUMERIC(12, 4),
        volume BIGINT,
        PRIMARY KEY (symbol, date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS index_values (
        index_name TEXT NOT NULL,
        date DATE NOT NULL,
        nav NUMERIC(12, 4),
        daily_return NUMERIC(10, 6),
        PRIMARY KEY (index_name, date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_weights (
        index_name TEXT NOT NULL,
        date DATE NOT NULL,
        symbol TEXT NOT NULL,
        weight NUMERIC(8, 6),
        PRIMARY KEY (index_name, date, symbol)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rebalance_log (
        id SERIAL PRIMARY KEY,
        index_name TEXT NOT NULL,
        date DATE NOT NULL,
        trigger_type TEXT,
        regime_state TEXT,
        notes TEXT,
        trades JSONB
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS backtest_results (
        index_name TEXT NOT NULL,
        metric TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        value NUMERIC(12, 6),
        PRIMARY KEY (index_name, metric, timeframe)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS proof_stats (
        stat_name TEXT PRIMARY KEY,
        value JSONB
    );
    """,
]


def init_database() -> None:
    """Create all tables in Supabase via the REST/RPC interface."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_KEY) must be set in .env")
        sys.exit(1)

    client: Client = create_client(url, key)
    logger.info("Connected to Supabase at %s", url)

    for sql in CREATE_TABLES_SQL:
        table_name = sql.split("IF NOT EXISTS")[1].split("(")[0].strip()
        try:
            client.postgrest.rpc("exec_sql", {"query": sql}).execute()
            logger.info("Created table: %s", table_name)
        except Exception:
            # If RPC isn't set up, log the SQL for manual execution
            logger.warning(
                "Could not execute via RPC. Run this SQL manually in the Supabase SQL editor:\n%s",
                sql,
            )

    logger.info("Database initialization complete.")
    logger.info(
        "If RPC failed, copy the SQL statements above into your Supabase SQL Editor "
        "(https://supabase.com/dashboard → SQL Editor) and run them manually."
    )


if __name__ == "__main__":
    init_database()
