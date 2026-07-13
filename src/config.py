"""Central configuration for SP Index Lab."""

from datetime import date
from pathlib import Path

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"

# ──────────────────────────────────────────────
# Tickers
# ──────────────────────────────────────────────
# Current top 50 S&P 500 stocks by market cap. Display/candidate use only —
# historical universe selection is point-in-time via src/data/universe.py.
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

# Every name fetched into the price/volume panel: the current top 50 plus
# everything that plausibly cracked the top 50 by market cap since 2014.
# The point-in-time universe (src/data/universe.py) selects from this pool;
# you cannot rank what you did not fetch.
CANDIDATE_POOL_TICKERS: list[str] = sorted(
    set(TOP_50_TICKERS)
    | {
        "T", "VZ", "INTC", "C", "GILD", "CMCSA", "PEP", "BA", "SLB", "MO",
        "UNP", "MMM", "HON", "AXP", "GS", "MS", "SCHW", "BLK", "NKE", "UPS",
        "USB", "COP", "MDT", "BMY", "CVS", "LOW", "SBUX", "TMUS", "NEE",
        "DHR", "ADP", "AIG", "KHC", "F", "GM", "RTX", "OXY", "UBER", "PLTR",
        "PYPL", "LMT", "CHTR", "AMT", "MU",
    }
)

# ──────────────────────────────────────────────
# Market data tickers
# ──────────────────────────────────────────────
# Total-return index: stock prices are dividend-adjusted (auto_adjust=True),
# so the benchmark must include dividends too or every strategy gets a free
# ~1.5%/yr "alpha" from the dividend mismatch.
BENCHMARK_TICKER = "^SP500TR"       # S&P 500 Total Return index
RISK_FREE_TICKER = "^IRX"           # 13-week Treasury bill yield
VIX_TICKER = "^VIX"                 # CBOE Volatility Index
TREASURY_10Y_TICKER = "^TNX"        # 10-year Treasury yield

# ──────────────────────────────────────────────
# Dates
# ──────────────────────────────────────────────
INCEPTION_DATE = date(2014, 1, 2)   # First trading day of 2014; NAV normalised to 1.0 here
# Fetch history starts one year earlier so point-in-time dollar-volume
# ranking (252-day lookback) has a full window at inception.
DATA_START_DATE = date(2013, 1, 2)

# ──────────────────────────────────────────────
# Research development / holdout split (anti-selection-bias)
# ──────────────────────────────────────────────
# All strategy development, tuning, and variant selection happens on data
# through DEV_END. HOLDOUT_START onward is LOCKED: touched exactly once, by
# scripts/run_holdout.py, for the final pre-registered evaluation of the one
# frozen candidate. Never fit, tune, or select on holdout data.
DEV_END = date(2023, 12, 31)
HOLDOUT_START = date(2024, 1, 1)

# ──────────────────────────────────────────────
# Portfolio constraints
# ──────────────────────────────────────────────
REBALANCE_DRIFT_THRESHOLD = 0.02    # 2% absolute drift triggers rebalance check
MAX_POSITION_WEIGHT = 0.15          # No single stock > 15%
MIN_POSITION_WEIGHT = 0.01          # No stock < 1%
TRANSACTION_COST_BPS = 5            # 5 basis points per unit of one-way traded notional
SLIPPAGE_BPS = 2                    # 2 basis points slippage assumption

# ──────────────────────────────────────────────
# Point-in-time universe
# ──────────────────────────────────────────────
UNIVERSE_LOOKBACK_DAYS = 63         # Trailing smoothing window for cap-proxy ranking
UNIVERSE_MIN_OBS = 20               # Min non-NaN days required to rank a ticker
MIRROR_REBALANCE_FREQ = "M"         # Mirror/Equal rebalance at month-end (period freq)

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
# Regime detection (HMM)
# ──────────────────────────────────────────────
HMM_N_STATES = 3

# ──────────────────────────────────────────────
# Factor model (LightGBM)
# ──────────────────────────────────────────────
LGBM_FORWARD_DAYS = 21
LGBM_N_ESTIMATORS = 100
LGBM_MAX_DEPTH = 5
LGBM_LEARNING_RATE = 0.05

# ──────────────────────────────────────────────
# Ensemble optimizer — blend ratios by regime
# {regime_id: (factor_mvo_weight, hrp_weight)}
# ──────────────────────────────────────────────
ENSEMBLE_REGIME_BLENDS: dict[int, tuple[float, float]] = {
    0: (0.7, 0.3),   # Bull
    1: (0.5, 0.5),   # Transition
    2: (0.2, 0.8),   # Bear
}

# ──────────────────────────────────────────────
# HuggingFace / Sentiment
# ──────────────────────────────────────────────
HF_MODEL_SENTIMENT = "ProsusAI/finbert"
SENTIMENT_CACHE_FILE = DATA_DIR / "sentiment_cache.parquet"

# ──────────────────────────────────────────────
# Database / storage
# ──────────────────────────────────────────────
PARQUET_FILES = {
    "daily_prices": DATA_DIR / "daily_prices.parquet",
    "daily_prices_raw": DATA_DIR / "daily_prices_raw.parquet",
    "daily_volumes": DATA_DIR / "daily_volumes.parquet",
    "universe_schedule": DATA_DIR / "universe_schedule.parquet",
    "index_values": DATA_DIR / "index_values.parquet",
    "portfolio_weights": DATA_DIR / "portfolio_weights.parquet",
    "rebalance_log": DATA_DIR / "rebalance_log.parquet",
    "backtest_results": DATA_DIR / "backtest_results.parquet",
    "proof_stats": DATA_DIR / "proof_stats.parquet",
}
