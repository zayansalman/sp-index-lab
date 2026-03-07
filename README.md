# S&P Index Lab

**20 stocks. 94.9% of the S&P 500. Better returns.**

An AI-powered portfolio analytics platform that proves the S&P 500 is effectively a ~20-stock index, then builds optimized derived indices that outperform it. Features an interactive machine-metaphor visualization built with React, and a Python analytics backend powered by OLS regression and variance decomposition.

> **Live demo**: [sp-index-lab.vercel.app](https://sp-index-lab.vercel.app)

---

## The Thesis

The top 20 S&P 500 stocks account for ~47% of total index weight. Using OLS regression across 3,062 trading days (2014-2026), we prove these 20 stocks explain **94.9%** of S&P 500 variance. The other 480 stocks contribute less than 5% of explanatory power.

A cap-weighted mirror portfolio of just 20 stocks achieved **15.3% CAGR** vs the S&P 500's **11.3%** — a **+4.0% annualized alpha** with a higher Sharpe ratio (0.68 vs 0.54).

## Key Results

| Metric | S&P 500 | SP-20 Mirror | SP-20 Equal |
|--------|---------|-------------|-------------|
| CAGR | 11.3% | **15.3%** | 14.2% |
| Sharpe | 0.54 | **0.68** | 0.63 |
| Max Drawdown | -33.7% | -37.4% | -39.8% |
| Beta | 1.00 | 1.12 | 1.09 |
| Alpha | — | **+4.0%** | +2.9% |

## Architecture

```
┌──────────────────────────────────┐
│   Vercel (CDN)                    │
│   Next.js 16 · React 19 · TS     │
│   Framer Motion · Recharts        │
│   Static JSON ← /public/data/    │
└──────────────┬───────────────────┘
               │ Pre-computed
┌──────────────┴───────────────────┐
│   Python Analytics Backend        │
│   pandas · scikit-learn · numpy   │
│   OLS regression · NAV calc       │
│   scripts/export_frontend_data.py │
└──────────────┬───────────────────┘
               │
┌──────────────┴───────────────────┐
│   Data Layer                      │
│   yfinance → Parquet files        │
│   Supabase (PostgreSQL)           │
│   GitHub Actions (daily cron)     │
└──────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Animation | Framer Motion 12, CSS keyframes (SVG wire electricity) |
| Charts | Recharts 3 (line, area, bar) |
| Analytics | Python 3.11, pandas, numpy, scikit-learn |
| Optimization | PyPortfolioOpt, LightGBM, hmmlearn (planned) |
| Data | yfinance, Supabase, Parquet, DuckDB |
| CI/CD | GitHub Actions (daily cron), Vercel (auto-deploy) |
| Package Mgmt | uv (Python), npm (JavaScript) |

## Quick Start

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Backend (Python)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Fill in SUPABASE_URL and SUPABASE_KEY

# Generate frontend data
uv run python scripts/export_frontend_data.py

# Run legacy Streamlit dashboard
uv run streamlit run app/Home.py
```

### Full Pipeline

```bash
# Daily data update (also runs via GitHub Actions)
uv run python scripts/daily_update.py

# Re-export JSON for frontend
uv run python scripts/export_frontend_data.py

# Build frontend for production
cd frontend && npm run build
```

## Project Structure

```
sp/
├── frontend/                 # Next.js application
│   ├── app/                  # Routes: / (landing), /lab (machine)
│   ├── components/           # 25 React components
│   │   ├── landing/          # Hero, StatsPreview, EnterButton
│   │   ├── machine/          # SVG machine, wires, switch, 5 nodes
│   │   ├── results/          # Charts, metrics, tables, thinking panels
│   │   └── ui/               # AnimatedCounter, GlowText, Tooltip
│   ├── hooks/                # useLabData, useMachineState
│   ├── lib/                  # types, constants, tooltips, formatters
│   └── public/data/          # 8 pre-computed JSON files (~200KB)
├── src/                      # Python analytics
│   ├── config.py             # Constants (50 tickers, dates, thresholds)
│   ├── data/                 # fetcher.py, storage.py
│   └── proof/                # concentration.py (core analytics)
├── scripts/
│   ├── export_frontend_data.py  # Python → JSON bridge
│   └── daily_update.py          # GitHub Actions entry point
├── .github/workflows/        # Daily cron job
├── CLAUDE.md                 # AI assistant context
├── ARCHITECTURE.md           # Full stack architecture
├── PRD.md                    # Product requirements
├── FRONTEND.md               # Frontend visual spec
├── RESEARCH.md               # Concentration thesis & sources
└── TASKS.md                  # Build plan with status
```

## Documentation

| File | Purpose |
|------|---------|
| [CLAUDE.md](CLAUDE.md) | AI assistant context — tech stack, conventions, commands |
| [PRD.md](PRD.md) | Product requirements — indices, metrics, success criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack decisions, data flow, security, infrastructure |
| [FRONTEND.md](FRONTEND.md) | Visual spec — colors, components, animations, responsive |
| [RESEARCH.md](RESEARCH.md) | Concentration thesis — academic sources, methodology |
| [TASKS.md](TASKS.md) | Implementation plan — phased build with completion status |

## How It Works

1. **Data Pipeline**: yfinance fetches 12+ years of daily prices for 50 S&P 500 stocks
2. **Concentration Proof**: OLS regression measures how many stocks explain S&P 500 variance
3. **Mirror Index**: Cap-weighted portfolio of top 20 stocks, NAV normalized to $1 at inception
4. **Export**: Python analytics serialized to static JSON files
5. **Visualization**: React frontend renders an interactive machine with SVG animations
6. **Results**: Charts, metrics, and methodology panels appear after the machine "runs"

## AI-Assisted Development

This project demonstrates enterprise-quality AI-assisted development:

- **Structured documentation** guides AI context (CLAUDE.md → PRD → ARCHITECTURE → TASKS)
- **Type safety** end-to-end: Python type hints + TypeScript strict mode
- **Deterministic analytics**: all financial calculations are reproducible
- **Clean architecture**: separation of concerns, single-responsibility modules
- **Comprehensive testing**: production builds pass with zero errors

Built with [Claude Code](https://claude.ai/code) as a co-developer.

## License

MIT
