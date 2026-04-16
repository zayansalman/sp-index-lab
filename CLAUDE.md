# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

S&P Index Lab proves the S&P 500 is effectively a ~20-stock index. Python backend computes analytics (OLS regression, variance decomposition, mirror index construction). React frontend displays results via an interactive machine-metaphor visualization. Static JSON bridge between the two — no Python at runtime.

Key results:
- R² = 94.9% with 20 stocks
- SP-N Alpha (ML ensemble): CAGR 23.4%, Sharpe 1.11, Alpha +9.4%
- SP-N Hedged: Sharpe 1.38, Max DD -6.7%, Alpha +5.1%

## Commands

```bash
# Python backend (run from repo root)
uv sync                                           # Install all deps
uv run python scripts/export_frontend_data.py      # Regenerate frontend JSON
uv run python scripts/run_alpha_backtest.py        # Walk-forward backtest for all strategies
uv run python scripts/daily_update.py              # Full daily refresh pipeline
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
- `src/proof/concentration.py` — Core analytics: variance decomposition, mirror index, R² curve.
- `src/backtest/engine.py` — Walk-forward backtesting engine. `WeightsFn` interface for all strategies.
- `src/backtest/metrics.py` — Performance metrics (CAGR, Sharpe, Sortino, alpha, beta, etc.).
- `src/features/technical.py` — Momentum, volatility, RSI, MA distance features.
- `src/features/regime.py` — 3-state HMM regime detection (bull/transition/bear) on VIX + yield spread.
- `src/features/factors.py` — LightGBM cross-sectional forward return predictor.
- `src/features/sentiment.py` — FinBERT sentiment (live via HuggingFace) + backtest proxy.
- `src/features/beta.py` — Rolling stock betas and portfolio beta calculation.
- `src/optimizer/hrp.py` — Hierarchical Risk Parity weights via PyPortfolioOpt.
- `src/optimizer/mvo.py` — Mean-Variance Optimization (max-Sharpe, min-vol) with fallback.
- `src/optimizer/ensemble.py` — Regime-weighted blend of factor-MVO + HRP.
- `src/strategies/alpha.py` — SP-N Alpha strategy factory (classical + ML ensemble).
- `src/strategies/hedged.py` — SP-N Hedged strategy (dynamic beta targeting + cash allocation).
- `src/utils/helpers.py` — CASH pseudo-ticker for hedged portfolio engine compatibility.
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
- Transaction costs: 5 bps round-trip assumed in backtesting
- Frontend is purely static — pre-compute everything, never calculate on render
- Time series downsampled to weekly (~620 points) for chart performance

## References
- [ARCHITECTURE.md](ARCHITECTURE.md) — 10-layer fund stack design, security, costs
- [RESEARCH.md](RESEARCH.md) — Concentration thesis, R² methodology, HMM/HRP rationale
- [PRD.md](PRD.md) — Product requirements and index specifications
- [TASKS.md](TASKS.md) — Build plan with phase completion status
- [FRONTEND.md](FRONTEND.md) — Visual spec, components, animations
- [EXECUTION_PLAN.md](EXECUTION_PLAN.md) — Sprint prioritization (1-6 core, 11-12 deferred)
