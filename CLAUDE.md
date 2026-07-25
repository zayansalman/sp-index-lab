# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

S&P Index Lab proves the S&P 500 is effectively a ~20-stock index. Python backend computes analytics (OLS regression, variance decomposition, mirror index construction). React frontend displays results via an interactive machine-metaphor visualization. Static JSON bridge between the two — no Python at runtime.

**Primary mandate (owner, 2026-07-26).** SP-N: hold N stocks selected from the S&P 500 —
N *solved* per rebalance, never hand-fixed — targeting maximum return with minimum
volatility and drawdown, net of costs, re-run and rebalanced on the index's own schedule
(S&P quarterly rebalance effective dates + membership-change events; the pipeline's current
monthly month-end cadence is the finer-grained superset — aligning to quarterly is a spec
change that must be pre-registered, not slipped in). Benchmarks are ALWAYS all three:
`^SP500TR`, SP-20 Mirror, SP-20 Equal. "Max return, min risk" is not simultaneously
optimizable; it is operationalized as the pre-registered multi-objective bar — beat
benchmarks on CAGR **and** Sharpe with max drawdown ≤ 1.2× the index's. The concentration
proof is step one (it establishes a small-N portfolio can carry the index); the active
mandate is step two and is judged with IR/t-stats and full multiple-testing disclosure.
Under this objective the dev-window record reads differently than under the old
return-first criteria: `s3:equal:elbow:voltgt15` (trial 10) posted the highest Sharpe of
all 14 trials (0.666) with maxDD −21.2%, and was eliminated only for giving up CAGR vs
Equal — but dev has been SEEN, so any re-selection must validate on post-2026 data or
forward paper-trading, with the peek disclosed.

Key results (point-in-time universe, net of transaction costs, vs S&P 500 total-return).
No single strategy is crowned — the site shows all four side by side:
- R² ≈ 95.2% with 20 stocks (mean across rolling 1-year windows, PIT top-20 per window).
  This is the project's one statistically strong claim.
- **"20" is a reporting convention, not a solved answer — never write copy implying it was
  discovered.** Two different questions get conflated constantly:
  (a) *how much do the 20 largest explain?* → 95.2% mean R² at a FIXED N=20 (`r_squared_at_20`);
  (b) *what is the smallest N worth holding?* → `make_elbow_n` solves this per rebalance and
  has selected a **median of 11** (mean 11.2, range 10–16) across 126 rebalances, choosing 20
  **zero times**, sitting on the `SPN_MIN_STOCKS`=10 floor 38.9% of the time. Current live
  holding is 16 names. ~87% of dynamic-N's edge is a *level* effect (hold ~11 not 20); the
  *timing* component is +0.32pp/yr at t = 0.34.
- **The concentration claim is a REPLICATION claim; the strategy claims are ACTIVE claims.**
  They take different metrics and different bars. Replication is judged on R²/tracking error
  and is already solid; active is judged on IR with the t > 3 hurdle and is not significant.
  Applying the active bar to the replication finding understates the project's strongest
  result — keep the two separate in docs and UI.
- **Always quote the matched window** (2016-01-04→present, ~10.5y — the first date all four
  series exist), from the `matched_window` block in `performance_metrics.json`:
  S&P 500 ~15.4% CAGR · SP-20 Mirror ~19.3% · SP-20 Equal ~17.5% · SP-N Alpha ~20.3%.
  The per-strategy blocks each span that strategy's OWN history (baselines from 2014,
  SP-N Alpha from 2016 once its first walk-forward window closes). Comparing across those
  is not apples-to-apples: it understates the S&P by ~1.5pp CAGR and lets a longer window
  win on total return purely by compounding longer.
- **No pairwise difference is statistically significant.** On the matched window, SP-N Alpha
  beats the Mirror by only ~+0.9pp/yr (TE ~3.9%, IR ~0.22, t ≈ 0.7) — it would need ~178
  years of data to clear the t > 3.0 multiple-testing hurdle. Even Alpha vs the S&P 500 is
  t ≈ 2.0 (~25 years needed). Never describe any strategy as "beating" another without
  this caveat; the ranking is real in the data and indistinguishable from luck.
- Root cause is breadth, not costs: cost drag is only ~6–15 bps/yr (Mirror 0.83x turnover,
  Equal 1.15x, Alpha ~1.8–2.0x) and mega-cap capacity is effectively unbounded. Grinold's
  IR ≈ IC×√breadth caps what 20 names × 12 rebalances can demonstrate.

Honest-evaluation protocol (the point of the project — do not regress these):
- **Dev/holdout split**: `DEV_END=2023-12-31`. All development, tuning, and variant
  selection happens on the dev window via `src/research/registry.py::run_experiment`
  (hard-truncates at DEV_END, logs every trial to `data/research/trials.jsonl`). The
  holdout (2024+) is touched exactly once by `scripts/run_holdout.py`.
- **Multiple-testing disclosure**: deflated Sharpe (`src/backtest/metrics.py`) reported
  against the true trial count. SP-N Alpha's dev DSR is 0.96 across 14 trials.
- **Pre-registered holdout** (`data/research/holdout_criteria.yaml`, committed before any
  candidate chosen): SP-N Alpha beat the S&P 500 out-of-sample (+10.5pp CAGR, 2024–26) but
  did NOT clear every bar vs SP-20 Equal (lost on Sharpe, breached the drawdown cap) → the
  contract's outcome is "no single winner"; strategies are shown side by side.
- Universe selection is point-in-time: membership snapshots + anchored market-cap proxy on
  the **dividend-unadjusted** `daily_prices_raw` panel (`src/data/universe.py`). Returns
  use the dividend-adjusted panel. Never rank by full-sample statistics.
- All backtests net of turnover costs (`src/backtest/costs.py`). Benchmark is ^SP500TR.
- **Significance hurdle**: `MULTIPLE_TESTING_T_HURDLE = 3.0` (`src/config.py`), per Harvey,
  Liu & Zhu (2016) — with 14 logged dev trials the conventional t > 1.96 is invalid. The
  `matched_window.significance` block reports the t-stat of every pairwise comparison and
  `years_for_hurdle` (t = IR × √years), surfaced by `SignificancePanel.tsx`.
- **SP-20 Mirror has never been a research reference.** All 14 dev trials scored only
  against `^SP500TR` and `sp20_equal`, so no candidate has a dev-window excess-vs-Mirror
  record. Any new race targeting the Mirror must add it to `references` and pre-register
  updated criteria BEFORE selecting a candidate.
- Exact current numbers live in `frontend/public/data/meta.json` (`headline` + `research`
  blocks) and `performance_metrics.json` (`matched_window`); components read them — never
  hardcode numbers in components or docs.

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
- `src/strategies/dynamic_alpha.py` — Retained SP-N Alpha: self-adjusting concentration-elbow,
  equal-weighted dynamic-N (`strategy_from_config`, frozen via `data/research/race_result.json`).
- `src/strategies/alpha.py` — Legacy SP-N Alpha strategy factories (mvo_sharpe, ML ensemble);
  research-only, NOT the retained public strategy.
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
