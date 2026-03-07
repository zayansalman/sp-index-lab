"""Central configuration for SP Index Lab."""

from datetime import date
from pathlib import Path

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# ──────────────────────────────────────────────
# Tickers
# ──────────────────────────────────────────────
# Top 50 S&P 500 stocks by market cap (candidates for SP-N Alpha).
# Updated periodically — source of truth for the project.
TOP_50_TICKERS: list[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "BRK-B", "AVGO", "LLY",
    "JPM", "V", "WMT", "UNH", "MA",
    "XOM", "COST", "HD", "PG", "JNJ",
    "NFLX", "ABBV", "CRM", "BAC", "CVX",
    "ORCL", "MRK", "KO", "WFC", "CSCO",
    "AMD", "ACN", "NOW", "ADBE", "LIN",
    "IBM", "MCD", "PM", "TMO", "ABT",
    "DIS", "ISRG", "GE", "TXN", "INTU",
    "CAT", "QCOM", "AMGN", "PFE", "BKNG",
]

# Top 20 derived from TOP_50 (first 20 by current market cap ranking).
TOP_20_TICKERS: list[str] = TOP_50_TICKERS[:20]

# Index identifiers used across the project.
INDEX_NAMES: list[str] = [
    "sp500",
    "sp20_mirror",
    "sp20_equal",
    "sp20_alpha",
    "spn_alpha",
]

# ──────────────────────────────────────────────
# Market data tickers
# ──────────────────────────────────────────────
BENCHMARK_TICKER = "^GSPC"          # S&P 500 index
RISK_FREE_TICKER = "^IRX"           # 13-week Treasury bill yield
VIX_TICKER = "^VIX"                 # CBOE Volatility Index
TREASURY_10Y_TICKER = "^TNX"        # 10-year Treasury yield

# ──────────────────────────────────────────────
# Dates
# ──────────────────────────────────────────────
INCEPTION_DATE = date(2014, 1, 2)   # First trading day of 2014; NAV normalised to 1.0 here

# ──────────────────────────────────────────────
# Portfolio constraints
# ──────────────────────────────────────────────
REBALANCE_DRIFT_THRESHOLD = 0.02    # 2% absolute drift triggers rebalance check
MAX_POSITION_WEIGHT = 0.15          # No single stock > 15%
MIN_POSITION_WEIGHT = 0.01          # No stock < 1%
TRANSACTION_COST_BPS = 5            # 5 basis points round-trip cost
SLIPPAGE_BPS = 2                    # 2 basis points slippage assumption

# ──────────────────────────────────────────────
# Backtesting
# ──────────────────────────────────────────────
TRAIN_WINDOW_DAYS = 756             # ~3 years of trading days
TEST_WINDOW_DAYS = 21               # ~1 month of trading days
TRADING_DAYS_PER_YEAR = 252

# ──────────────────────────────────────────────
# SP-N Alpha bounds
# ──────────────────────────────────────────────
SPN_MIN_STOCKS = 10
SPN_MAX_STOCKS = 30

# ──────────────────────────────────────────────
# Database / storage
# ──────────────────────────────────────────────
PARQUET_FILES = {
    "daily_prices": DATA_DIR / "daily_prices.parquet",
    "index_values": DATA_DIR / "index_values.parquet",
    "portfolio_weights": DATA_DIR / "portfolio_weights.parquet",
    "rebalance_log": DATA_DIR / "rebalance_log.parquet",
    "backtest_results": DATA_DIR / "backtest_results.parquet",
    "proof_stats": DATA_DIR / "proof_stats.parquet",
}
