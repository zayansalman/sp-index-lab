# Reference data

Point-in-time S&P 500 membership and supporting lookup tables. These files are
committed (unlike `data/*.parquet`) because they are small, change rarely, and
the backtests are not reproducible without them.

## sp500_membership.csv

Historical S&P 500 constituent snapshots, one row per change date
(`date,tickers` with a comma-separated ticker list), 1996 → present.

- Source: <https://github.com/fja05680/sp500> —
  "S&P 500 Historical Components & Changes (Updated).csv"
- License: MIT
- Vendored: 2026-07-04 at upstream commit `b792557e915703398ef9a67e4b583a37c6ec80d5`
- Refresh: re-download from the raw GitHub URL and re-commit (membership
  changes ~quarterly; the daily pipeline does not need it fresh).

Tickers appear in the source's native form (e.g. `FB`, `BRK.B`);
`src/data/universe.py` normalises them to yfinance symbols via
`ticker_aliases.csv` and a generic dot→dash rule.

## ticker_aliases.csv

Maps membership tickers to the yfinance symbol that serves their full price
history (renames, mergers, class-share dedupe).

## excluded_tickers.csv

Former constituents whose price history yfinance cannot serve (delisted with
no surviving symbol). None was ever a top-20 constituent, so SP-20 products
are unaffected; top-50 coverage dips slightly in 2015–2019 windows. The
universe ranking substitutes the next-ranked name and logs it.

## topn_snapshots.csv

Hand-collected historical top-20-by-market-cap lists at reference dates
(public records: index factsheets, SlickCharts archives). Used only by the
validation test that checks the dollar-volume ranking proxy against reality
(`tests/test_universe.py`), never by the pipeline itself.
