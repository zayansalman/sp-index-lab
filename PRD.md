# S&P Index Lab - Product Requirements Document

## Executive Summary

S&P Index Lab is a live portfolio analytics platform that tests whether the S&P 500 can be explained and improved by a concentrated top-constituent universe.

**Primary mandate.** SP-N: hold N stocks selected from the S&P 500 — N solved per rebalance
by an algorithm, never hand-fixed — targeting maximum return with minimum volatility and
drawdown, net of transaction costs, re-run and rebalanced on the index's own schedule.
Benchmarked, always, against all three references: the S&P 500 total-return index
(`^SP500TR`), SP-20 Mirror (cap-weighted top-20 control), and SP-20 Equal (equal-weighted
top-20 control). Since "maximum return" and "minimum risk" cannot be optimized
simultaneously, the mandate is operationalized as the pre-registered bar: beat the
references on CAGR **and** Sharpe with max drawdown no worse than 1.2× the index's. The
concentration proof (step one) establishes that a small-N portfolio can carry the index's
behaviour; the active mandate (step two) is evaluated under the honest-evaluation protocol
— IR and t-stats against the multiple-testing hurdle, with the trial count disclosed.

The product has two parts:

- A Python analytics backend that fetches market data, computes concentration proof metrics, runs walk-forward strategy backtests, and exports static JSON.
- A Next.js frontend that presents the proof and strategy results through an interactive machine-metaphor lab.

The frontend is static at runtime. All financial analytics are precomputed before deployment.

## Target Audience

| Audience | Need |
|----------|------|
| Quant, finance, and engineering reviewers | Rigorous methodology, clear implementation, and reproducible results |
| Finance/tech community | A provocative market thesis backed by inspectable data |
| Personal research use | A reusable workflow for concentrated-index experimentation |

## Product Goals

| Goal | Metric | Status |
|------|--------|--------|
| Prove concentration thesis | Top 20 R² > 90% | Achieved: ~95.2% rolling-window mean (point-in-time) |
| Build simple concentrated baselines | SP-20 Mirror and Equal NAVs exported | Achieved |
| Keep only strategies that matter | Mirror, Equal, and one SP-N Alpha exported | Achieved |
| Interactive visualization | `/` landing and `/lab` machine/results flow | Built |
| Daily automated data refresh | Cron exports and commits frontend JSON | Implemented in workflow |
| Enterprise-quality codebase | Typed, linted, tested Python and strict TypeScript frontend | In progress |

## Product Surface

### Index 1: SP-20 Mirror

- **What**: Point-in-time top 20 S&P 500 names (membership snapshots + anchored cap proxy).
- **Weighting**: Cap-proxy proportional, rebalanced monthly, net of transaction costs.
- **Purpose**: Show how closely a concentrated top-constituent basket tracks the benchmark.
- **Current result**: CAGR ~17.2% net, Sharpe ~0.77, vs S&P 500 TR ~13.9%.

### Index 2: SP-20 Equal

- **What**: Same point-in-time top 20 names.
- **Weighting**: Equal weighted, rebalanced monthly, net of costs.
- **Purpose**: Test whether reducing mega-cap concentration improves risk-adjusted returns.
- **Current result**: CAGR ~15.7% net, Sharpe ~0.79.

### Index 3: SP-N Alpha

- **What**: Self-adjusting walk-forward strategy that reads the concentration "elbow" each
  month and equal-weights that many point-in-time top names (dynamic N, 10–30).
- **Construction**: Equal-weighted across a dynamic N chosen by the concentration elbow;
  the spec was selected on the development window (through 2023-12-31), then frozen.
- **Purpose**: Test whether a self-adjusting concentration strategy beats the baselines
  out-of-sample under a pre-registered holdout.
- **Current result**: CAGR ~20.3% net out-of-sample, Sharpe ~0.88, Jensen alpha ~+3.8%. On
  the locked 2024→26 holdout it beat the S&P 500 (+10.5pp CAGR) but did not clear every
  pre-registered bar vs SP-20 Equal — so no single strategy is crowned; all four are shown
  side by side.

## Proof Layer

| Capability | Status | Implementation |
|------------|--------|----------------|
| Variance decomposition | Built | `src/proof/concentration.py::variance_decomposition` |
| Concentration curve | Built | `src/proof/concentration.py::concentration_curve` |
| Mirror index construction | Built | `src/proof/concentration.py::build_mirror_index` |
| Performance metrics | Built | `src/backtest/metrics.py` |
| Holdings export | Built | `scripts/export_frontend_data.py` |

The proof layer uses the configured market-cap order from `src/config.py` for top-N selection.

## Frontend Experience

### Landing Page (`/`)

- Dark editorial landing page for the project.
- Hero introduces the concentration thesis.
- Primary CTA routes to `/lab`.

### Machine Lab (`/lab`)

- Interactive machine visualization with sequential animation stages.
- Results panel appears after completion.
- Results include concentration curve, NAV comparison, metrics table, drawdowns, holdings, and methodology notes.

## Data Pipeline

```text
GitHub Actions (weekdays 22:30 UTC)
  -> restore cached data/*.parquet
  -> scripts/daily_update.py
  -> yfinance fetch for configured stocks, benchmark, and indicators
  -> scripts/run_alpha_backtest.py
  -> scripts/export_frontend_data.py
  -> frontend/public/data/*.json
  -> commit and push changed JSON
  -> Vercel auto-deploy
```

Supabase sync is optional and depends on repository secrets. The static frontend does not require Supabase at runtime.

## Non-Functional Requirements

- Frontend loads from static JSON with no runtime Python or database calls.
- Public analytics data is downsampled for chart performance.
- Python functions include type hints on public signatures.
- TypeScript uses strict data types from `frontend/lib/types.ts`.
- CI gates include Python lint/type/tests and frontend lint/build.
- Strategy metrics must avoid look-ahead bias and align benchmark comparisons to overlapping dates.

## Success Criteria

| Criterion | Status |
|-----------|--------|
| SP-20 explains more than 90% of S&P 500 variance | Achieved |
| Static frontend communicates the thesis and results clearly | Achieved |
| Only the retained SP-N Alpha strategy is exported to frontend data | Achieved |
| Daily workflow refreshes frontend JSON end-to-end | Implemented; requires live workflow confirmation after merge |
| Docs match implemented code and commands | In progress |
| Future broker execution, paper trading, and fund operations | Roadmap |
