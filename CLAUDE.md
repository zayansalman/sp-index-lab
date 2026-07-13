# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

S&P Index Lab proves the S&P 500 is effectively a ~20-stock index. Python backend computes analytics (OLS regression, variance decomposition, mirror index construction). React frontend displays results via an interactive machine-metaphor visualization. Static JSON bridge between the two — no Python at runtime.

Key results (point-in-time universe, net of transaction costs, vs S&P 500 total-return):
- R² = 95.6% with 20 stocks (mean across rolling 1-year windows, PIT top-20 per window)
- S&P 500 TR: CAGR 13.9% (2014–present)
- SP-20 Mirror: CAGR 18.4%, Sharpe 0.70, Jensen alpha +3.3%
- SP-20 Equal: CAGR 16.9%, Sharpe 0.71, Jensen alpha +2.8%
- SP-N Alpha (walk-forward max-Sharpe, out-of-sample 2016→): CAGR 20.9%, Sharpe 0.81, Jensen alpha +5.2%

Methodology guarantees (do not regress these):
- Universe selection is point-in-time: vendored S&P membership snapshots + anchored
  market-cap proxy (`src/data/universe.py`); never rank by full-sample statistics.
- All backtests are net of turnover-based costs (`src/backtest/costs.py`).
- Benchmark is ^SP500TR because stock prices are dividend-adjusted.
- The exact current numbers live in `frontend/public/data/meta.json` (`headline` block) —
  frontend components read them from there; never hardcode numbers in components or docs
  without noting they drift.

## Commands

```bash
# Python backend (run from repo root)
uv sync                                           # Install all deps
uv run python scripts/backfill.py --skip-supabase  # Full history download (prices+volumes)
uv run python scripts/run_alpha_backtest.py        # Walk-forward backtest (retained SP-N Alpha)
uv run python scripts/export_frontend_data.py      # Regenerate frontend JSON
uv run python scripts/daily_update.py              # Incremental daily refresh
uv run python scripts/update_shares_outstanding.py # Refresh cap-proxy shares anchor (rarely)
uv run pytest tests/ -v                            # Run tests (excludes @slow by default)
uv run pytest tests/test_metrics.py -v             # Run single test file
uv run pytest tests/test_data.py::test_validate_prices -v  # Run single test
uv run ruff check src/ scripts/ tests/             # Lint Python
uv run mypy src/                                   # Type check Python

# React frontend (run from frontend/)
cd frontend && npm ci                              # Install deps (prefer ci over install)
npm run dev                                        # Dev server on :3000
npm run build                                      # Production build (also serves as type-check gate)
npm run lint                                       # ESLint
```

## Architecture

### Data Pipeline
```
yfinance → data/*.parquet → scripts/export_frontend_data.py → frontend/public/data/*.json → Next.js → Vercel
```

The export script (`scripts/export_frontend_data.py`) calls analytics from `src/proof/concentration.py` and outputs 8 JSON files (~200KB total). The frontend hook `frontend/hooks/useLabData.ts` fetches these and transforms snake_case → camelCase.

### Two Codebases, One Repo
- **Python** (`src/`, `scripts/`, `tests/`): Analytics engine. Managed by `uv` via `pyproject.toml`. Entry points are scripts, not a package.
- **Frontend** (`frontend/`): Next.js 16 static site. Separate `package.json`. Routes: `/` (landing), `/lab` (machine visualization).

### Key Modules
- `src/config.py` — All constants, ticker lists, thresholds. Never hardcode these elsewhere.
- `src/data/fetcher.py` — All yfinance calls go through here. No direct yfinance elsewhere.
- `src/data/storage.py` — All Supabase/DB operations go through here.
- `src/data/universe.py` — Point-in-time universe: membership snapshots + anchored cap-proxy
  ranking (`get_top_n_at`, `make_universe_fn`). Reference data in `data/reference/`.
- `src/proof/concentration.py` — Core analytics: rolling PIT concentration, mirror index, R² curve.
- `src/backtest/engine.py` — Walk-forward engine (`universe_fn` + `WeightsFn`), returns
  `WalkForwardResult` with net/gross NAV, turnover, and costs.
- `src/backtest/costs.py` — Shared drifting-portfolio simulator; turnover-based cost model.
- `src/backtest/metrics.py` — Performance metrics (CAGR, Sharpe, Sortino, alpha, beta, etc.).
- `src/features/technical.py` — Momentum, volatility, RSI, MA distance features.
- `src/features/regime.py` — 3-state HMM regime detection (bull/transition/bear) on VIX + yield spread.
- `src/features/factors.py` — LightGBM cross-sectional forward return predictor.
- `src/features/sentiment.py` — FinBERT sentiment (live via HuggingFace) + backtest proxy.
- `src/features/beta.py` — Rolling stock betas and portfolio beta calculation.
- `src/optimizer/hrp.py` — Hierarchical Risk Parity weights via PyPortfolioOpt.
- `src/optimizer/mvo.py` — Mean-Variance Optimization (max-Sharpe, min-vol) with fallback.
- `src/optimizer/ensemble.py` — Regime-weighted blend of factor-MVO + HRP.
- `src/strategies/alpha.py` — SP-N Alpha strategy factories (retained: mvo_sharpe; ML ensemble is research-only).
- `src/strategies/hedged.py` — Archived hedged strategy prototype (research only, not exported).
- `src/utils/helpers.py` — CASH pseudo-ticker for research strategies' engine compatibility.
- `frontend/lib/types.ts` — All TypeScript data types. Props and data must be typed here.
- `frontend/lib/constants.ts` — Design tokens (colors, timing, thresholds). No inline magic numbers.
- `frontend/hooks/useMachineState.ts` — useReducer state machine: IDLE → stages → COMPLETE.

## Code Conventions

### Python
- Python 3.11+, type hints on all signatures, Google-style docstrings
- `logging` module, never `print()`
- Vectorized pandas/numpy, never `iterrows()`
- Financial values rounded to 4 decimal places
- No look-ahead bias — only past data at decision time
- Imports: stdlib → third-party → local, separated by blank lines
- Ruff config: line-length 100, rules E/F/I/N/W

### TypeScript/React
- Strict TypeScript, all data typed in `lib/types.ts`
- Components: `components/{feature}/{ComponentName}.tsx`
- Framer Motion for animations — use spring physics, not duration-based
- Tailwind CSS v4 with `@theme inline` syntax, custom dark tokens in `globals.css`

## CI/CD

**PR checks** (`.github/workflows/ci.yml`): ruff → mypy → pytest (Python) + lint → build (frontend). Both timeout at 15 min.

**Daily update** (`.github/workflows/daily_update.yml`): Cron weekdays 22:30 UTC. Fetches fresh market data, regenerates parquet, auto-commits.

## Environment Variables
```
SUPABASE_URL=         # Supabase project URL
SUPABASE_KEY=         # Supabase anon key
SUPABASE_SERVICE_KEY= # Supabase service role key (CI only)
HF_TOKEN=             # HuggingFace API token (for live FinBERT sentiment)
```

## Constraints
- Free tier: Supabase 500MB, GitHub Actions 2000 min/month
- Transaction costs: 7 bps per unit of one-way traded notional (5 cost + 2 slippage), charged on turnover at every rebalance in all backtests
- Frontend is purely static — pre-compute everything, never calculate on render
- Time series downsampled to weekly (~620 points) for chart performance

## References
- [ARCHITECTURE.md](ARCHITECTURE.md) — 10-layer fund stack design, security, costs
- [RESEARCH.md](RESEARCH.md) — Concentration thesis, R² methodology, HMM/HRP rationale
- [PRD.md](PRD.md) — Product requirements and index specifications
- [TASKS.md](TASKS.md) — Build plan with phase completion status
- [FRONTEND.md](FRONTEND.md) — Visual spec, components, animations
- [EXECUTION_PLAN.md](EXECUTION_PLAN.md) — Sprint prioritization (1-6 core, 11-12 deferred)
