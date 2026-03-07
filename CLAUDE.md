# S&P Index Lab

## Overview
AI-powered portfolio analytics platform proving the S&P 500 is effectively a ~20-stock index. Features a Python analytics backend (OLS regression, variance decomposition, mirror index construction) and a React frontend with an interactive machine-metaphor visualization. Pre-computed analytics are exported as static JSON and served via a Next.js static site on Vercel.

## Tech Stack

### Python Backend
- **Language**: Python 3.11+ with type hints, Google-style docstrings
- **Analytics**: pandas, numpy, statsmodels, scikit-learn (LinearRegression)
- **Optimization**: PyPortfolioOpt (HRP, Black-Litterman), LightGBM, hmmlearn
- **Data**: yfinance (market data), Supabase (PostgreSQL), DuckDB, Parquet
- **Dashboard**: Streamlit + Plotly (legacy, replaced by frontend)
- **Package Manager**: uv
- **Scheduling**: GitHub Actions (daily cron, weekdays 22:30 UTC)

### React Frontend
- **Framework**: Next.js 16 (App Router), React 19, TypeScript strict
- **Styling**: Tailwind CSS v4 (`@theme inline`, custom dark tokens)
- **Animation**: Framer Motion 12+ (page transitions, spring physics)
- **Charts**: Recharts 3 (line, area, bar)
- **Tooltips**: @radix-ui/react-tooltip (HTML overlay on SVG)
- **Utilities**: clsx, tailwind-merge

## Project Structure
```
sp/
├── src/                          # Python source
│   ├── config.py                 # Constants, tickers, thresholds
│   ├── data/                     # fetcher.py, storage.py
│   ├── proof/                    # concentration.py (core analytics)
│   ├── indices/                  # Index construction (planned)
│   ├── optimizer/                # ML optimization (planned)
│   └── utils/                    # helpers.py
├── scripts/
│   ├── export_frontend_data.py   # Python → JSON bridge
│   └── daily_update.py           # GitHub Actions entry point
├── frontend/                     # Next.js application
│   ├── app/                      # Routes: / (landing), /lab (machine)
│   ├── components/               # landing/, machine/, results/, ui/
│   ├── hooks/                    # useLabData.ts, useMachineState.ts
│   ├── lib/                      # types.ts, constants.ts, tooltips.ts
│   └── public/data/              # Pre-computed JSON (8 files, ~200KB)
├── data/                         # Parquet cache (gitignored)
├── tests/                        # pytest test suite
└── app/                          # Streamlit dashboard (legacy)
```

## Code Conventions

### Python
- Type hints on all function signatures
- `logging` module, never `print()`
- Vectorized pandas/numpy, never `iterrows()`
- All data fetching through `src/data/fetcher.py`
- All DB operations through `src/data/storage.py`
- No look-ahead bias in calculations
- Financial values rounded to 4 decimal places

### TypeScript/React
- Strict TypeScript with all data typed in `lib/types.ts`
- Snake_case JSON → camelCase TS via transform layer in `useLabData.ts`
- Components: `components/{feature}/{ComponentName}.tsx`
- Design tokens in `lib/constants.ts` — no hardcoded colors/timing
- CSS custom properties for theme in `globals.css`

## Key Commands
```bash
# Python backend
uv sync                                          # Install deps
uv run python scripts/export_frontend_data.py     # Generate JSON
uv run python scripts/daily_update.py             # Daily refresh
pytest tests/ -v                                  # Run tests

# React frontend
cd frontend && npm install                        # Install deps
npm run dev                                       # Dev server :3000
npm run build                                     # Production build
npm run lint                                      # ESLint
```

## Environment Variables
```
SUPABASE_URL=         # Supabase project URL
SUPABASE_KEY=         # Supabase anon key
SUPABASE_SERVICE_KEY= # Supabase service role key (CI only)
```

## Data Pipeline
```
yfinance → Parquet → export_frontend_data.py → JSON → Next.js → Vercel
```

## Key Results
- R² = 94.9% — 20 stocks explain S&P 500 variance
- SP-20 Mirror CAGR = 15.3% vs S&P 500 = 11.3%
- Alpha = +4.0% annualized excess return
- Dataset: 2014-01-02 to present, 3,062+ trading days, 50 stocks

## Constraints
- Free tier: Supabase 500MB, GitHub Actions 2000 min/month
- Transaction costs: 5 bps round-trip for backtesting
- Frontend is purely static — no Python runtime at serve time
- Time series downsampled to weekly (~620 points) for chart performance

## References
- [PRD.md](PRD.md) — Product requirements and index specifications
- [ARCHITECTURE.md](ARCHITECTURE.md) — Stack, data flow, infrastructure
- [TASKS.md](TASKS.md) — Build plan with completion status
- [FRONTEND.md](FRONTEND.md) — Visual spec, components, animations
- [RESEARCH.md](RESEARCH.md) — Concentration thesis and sources
