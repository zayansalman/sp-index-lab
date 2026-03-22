# SP Index Lab — Architecture & Infrastructure

> Two-tier architecture: public analytics site + private fund operations. Strictly separated — the public site never exposes NAV, positions, or trade data.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VERCEL (CDN)                              │
│                                                                  │
│   Next.js 16 Static Site ─── React 19 + TypeScript              │
│   ┌───────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│   │  Landing   │  │  Machine Lab │  │   Results Panel       │    │
│   │  Page (/)  │  │  Page (/lab) │  │  Charts + Metrics     │    │
│   └───────────┘  └──────┬───────┘  └──────────┬───────────┘    │
│                          │                      │                │
│                    Static JSON ──── /public/data/*.json          │
│                    (8 files, ~200KB)                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Pre-computed at build time
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                     BUILD PIPELINE                               │
│                                                                  │
│   scripts/export_frontend_data.py                                │
│   ├── Loads Parquet files from data/                             │
│   ├── Runs analytics (concentration, metrics, drawdowns)         │
│   ├── Serializes to JSON with weekly downsampling                │
│   └── Writes to frontend/public/data/                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                   DATA LAYER (Python)                             │
│                                                                  │
│   src/proof/concentration.py ── Core analytics engine            │
│   ├── variance_decomposition()  OLS regression R² at each N      │
│   ├── concentration_curve()     Cumulative R² with stock IDs     │
│   ├── build_mirror_index()      Cap-weighted NAV construction    │
│   └── compute_performance_metrics()  15+ risk-adjusted metrics   │
│                                                                  │
│   src/data/storage.py ── load_parquet() / save_parquet()        │
│   src/data/fetcher.py ── yfinance with retry + validation       │
│   src/config.py ── TOP_50_TICKERS, INCEPTION_DATE, thresholds   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                   AUTOMATION                                     │
│                                                                  │
│   GitHub Actions (.github/workflows/daily_update.yml)            │
│   ├── Cron: weekdays 22:30 UTC (6:30 PM ET)                    │
│   ├── Fetches latest prices from yfinance                       │
│   ├── Updates Parquet files in data/                            │
│   ├── Commits + pushes to GitHub                                │
│   └── (Planned) Triggers JSON export + Vercel redeploy          │
│                                                                  │
│   Supabase (PostgreSQL) ── Source of truth                      │
│   ├── daily_prices, index_values, portfolio_weights             │
│   ├── rebalance_log, backtest_results, proof_stats              │
│   └── 500MB free tier                                           │
└──────────────────────────────────────────────────────────────────┘
```

## Stack Decision Matrix

| Layer | Choice | Alternatives Considered | Why This One |
|-------|--------|------------------------|--------------|
| Frontend Framework | Next.js 16 | Vite + React, Astro | App Router, static export, Vercel-native, RSC support |
| UI Library | React 19 | Svelte, Vue | Ecosystem depth, Framer Motion, Recharts compatibility |
| Language | TypeScript strict | JavaScript | Type safety critical for financial data transforms |
| Styling | Tailwind CSS v4 | CSS Modules, styled-components | Utility-first, `@theme inline` for custom tokens, no runtime |
| Animation | Framer Motion 12 | GSAP, CSS-only | React-native API, AnimatePresence, spring physics |
| Charts | Recharts 3 | D3, Plotly.js, Nivo | Lightweight (~40KB), declarative, React components |
| Tooltips | Radix UI | Floating UI, custom | Accessible by default, headless, composable |
| Python Analytics | pandas + sklearn | Polars, R | Ecosystem maturity, yfinance integration |
| Portfolio Optimization | PyPortfolioOpt | cvxpy, custom | HRP + Black-Litterman + MVO out of the box |
| ML | LightGBM | XGBoost, PyTorch | Fast training, categorical features, tabular data |
| Regime Detection | hmmlearn | custom HMM | Gaussian HMM, scikit-learn compatible API |
| Database | Supabase | PlanetScale, Firebase | Free PostgreSQL, REST API, auth for future features |
| Deployment | Vercel | Netlify, Cloudflare Pages | Next.js-native, edge CDN, zero-config |
| CI/CD | GitHub Actions | CircleCI, GitLab CI | Free 2000 min/month, native GitHub integration |
| Package Manager | uv (Python), npm (JS) | pip, pnpm | uv: 10-100x faster than pip; npm: Next.js default |

## Data Flow

### Read Path (User visits site)
```
Browser → Vercel CDN → Static HTML/JS bundle
                     → fetch(/data/*.json) from CDN edge cache
                     → useLabData hook transforms snake_case → camelCase
                     → React renders charts + tables
```
**Latency**: < 200ms (all static, CDN-cached, no server round-trip)

### Write Path (Daily automation)
```
GitHub Actions cron (22:30 UTC, weekdays)
  → checkout repo
  → uv sync
  → python scripts/daily_update.py
    → yfinance.download(TOP_50_TICKERS + benchmarks)
    → Validate data (NaN, extremes, gaps)
    → Compute daily returns, update NAVs
    → Check rebalance triggers
    → Write updated Parquet to data/
  → python scripts/export_frontend_data.py
    → Load Parquet → run analytics → serialize JSON
    → Write to frontend/public/data/
  → git add + commit + push
  → Vercel auto-deploys on push
```

### Transform Layer (JSON → TypeScript)
```
Python snake_case JSON          TypeScript camelCase
─────────────────────           ─────────────────────
sp20_mirror        →            sp20Mirror
r_squared          →            rSquared
last_updated       →            lastUpdated
n_trading_days     →            tradingDays
annualised_volatility →         annualizedVolatility
sharpe_ratio       →            sharpe
max_drawdown       →            maxDrawdown
```
8 transform functions in `hooks/useLabData.ts` with nullish coalescing defaults.

## Security

### Secrets Management
| Secret | Where Stored | Who Accesses |
|--------|-------------|-------------|
| `SUPABASE_URL` | GitHub Secrets + `.env` | GitHub Actions, local dev |
| `SUPABASE_KEY` | GitHub Secrets + `.env` | GitHub Actions, local dev |
| `SUPABASE_SERVICE_KEY` | GitHub Secrets only | GitHub Actions only |

### Access Control
- Frontend is fully static — no server-side secrets exposed
- Supabase anon key has read-only access (RLS enforced)
- Service key used only in CI for write operations
- No API keys in client-side JavaScript
- `.env` is gitignored; `.env.example` provides template

### Data Integrity
- All financial calculations are deterministic (same inputs → same outputs)
- No look-ahead bias: each calculation uses only historically available data
- Parquet files are versioned in git (audit trail)
- JSON export includes `last_updated` timestamp for staleness detection

## Infrastructure Costs

| Service | Tier | Limit | Current Usage |
|---------|------|-------|---------------|
| Vercel | Hobby (free) | 100GB bandwidth/month | ~1GB |
| Supabase | Free | 500MB database, 1GB transfer | ~50MB |
| GitHub Actions | Free | 2000 min/month | ~100 min/month |
| yfinance | Free | No hard limit (rate-limited) | ~50 API calls/day |
| **Total** | | | **$0/month** |

## AI-Assisted Development

This project is built using AI-assisted development to enterprise quality standards:

- **Claude Code** for architecture design, implementation, and code review
- **Structured documentation** (CLAUDE.md, PRD.md, ARCHITECTURE.md, FRONTEND.md, RESEARCH.md) guides AI context
- **Type safety** end-to-end: Python type hints + TypeScript strict mode
- **Deterministic analytics**: all financial calculations are reproducible and testable
- **Code organization**: clear separation of concerns, single-responsibility modules
- **Version control discipline**: atomic commits, descriptive messages, no secrets in history

The documentation tier system ensures any AI assistant can onboard to the project:
1. **Tier 1** (AI reads first): CLAUDE.md → .cursorrules
2. **Tier 2** (AI references): PRD.md, ARCHITECTURE.md, TASKS.md, FRONTEND.md, RESEARCH.md
3. **Tier 3** (Standard): README.md, .env.example, .gitignore, pyproject.toml

## Monitoring & Observability

### Current
- GitHub Actions logs for daily pipeline runs
- Vercel deployment logs for frontend builds
- Browser console for client-side errors
- `console.error("[useLabData]")` for data loading failures

### Planned
- Sentry for frontend error tracking
- Supabase dashboard for database metrics
- Custom health check endpoint for data freshness

---

## Fund Infrastructure Architecture (10 Layers)

The fund layer is a separate private system running alongside the public site.

```
LAYER 0: DATA INGESTION
  yfinance (equity, daily)         →  data/daily_prices.parquet       [EXISTING]
  Polygon.io (options, intraday)   →  data/options_chains/            [Phase 2]
  FRED API (macro indicators)      →  data/macro_indicators.parquet   [Phase 2]

LAYER 1: FEATURE ENGINEERING
  src/features/technical.py           momentum 1M/3M/6M/12M, realized vol, RSI, MA distance

LAYER 2: ML SIGNAL GENERATION
  src/optimizer/classical.py          PyPortfolioOpt: HRP, MVO, Black-Litterman
  src/optimizer/regime.py             hmmlearn: 3-state HMM (bull/bear/transition)
  src/optimizer/factor_model.py       LightGBM: forward 21D return quintile predictor
  src/optimizer/ensemble.py           regime-weighted combination
  src/optimizer/rebalancer.py         drift (2%) + regime-change + quarterly calendar

LAYER 3: STRATEGY PODS
  src/strategies/pod_base.py          PodBase ABC + Signal dataclass
  src/strategies/passive_core.py      SP-N Alpha pod — 70% of fund NAV
  src/strategies/vol_overlay.py       Covered calls pod — 15% of NAV [Phase 2]
  src/strategies/active_trading.py    Pairs + dispersion pod — 15% of NAV [Phase 2]
  src/strategies/portfolio.py         FundPortfolio: aggregate + fund constraints

LAYER 4: EXECUTION ABSTRACTION
  src/execution/order.py              Order, Fill, Position dataclasses (pure data, no broker logic)
  src/execution/broker_base.py        BrokerInterface ABC (strategy code NEVER imports alpaca/ibkr)
  src/execution/paper_broker.py       PaperBroker: next-open fills, sqrt impact slippage model
  src/execution/alpaca_broker.py      AlpacaBroker [Phase 2]
  src/execution/ibkr_broker.py        IBKRBroker [Phase 3, for options]
  src/execution/order_router.py       target weights → Order list
  src/execution/__init__.py           get_broker(RUN_MODE) factory

LAYER 5: RISK MANAGEMENT
  src/risk/calculator.py              Historical VaR 95%, CVaR, portfolio beta, active share
  src/risk/limits.py                  RiskLimits dataclass (15% max DD, 5% VaR, 20% max position)
  src/risk/circuit_breaker.py         L1 HALT: drawdown>15% or VaR>5%NAV; L2 WARN: bear or DD>8%
  src/risk/monitor.py                 RiskSnapshot computed after every fill batch

LAYER 6: BACKTESTING ENGINE
  src/backtest/metrics.py             Standalone perf metrics (extracted from proof/)
  src/backtest/engine.py              Walk-forward: 756D train / 21D test
  src/backtest/simulator.py           Trade simulation with same slippage model as PaperBroker
  src/backtest/report.py              BacktestReport + 5-gate promotion check

LAYER 7: PORTFOLIO TRACKING
  src/portfolio/state.py              Live positions, cash, NAV
  src/portfolio/ledger.py             Immutable trade log (append-only Parquet — no UPDATE/DELETE)
  src/portfolio/reconciler.py         Broker vs internal state diff + alert [Phase 2]

LAYER 8: REPORTING
  src/reporting/tearsheet.py          Daily PDF via weasyprint + Jinja2 (7 sections)
  src/reporting/attribution.py        Brinson-Hood-Beebower: allocation + selection + interaction
  src/reporting/investor_report.py    Monthly PDF for F&F investors [Phase 3]
  src/reporting/templates/            Jinja2 HTML templates (professional PDF style)

LAYER 9: ORCHESTRATION SCRIPTS
  scripts/run_optimizer.py            Re-optimize on demand
  scripts/run_paper_trading.py        Nightly: features → signals → orders → fills → tearsheet
  scripts/run_live_trading.py         Same as paper, broker = AlpacaBroker(paper=False) [Phase 2]
  scripts/run_full_backtest.py        Walk-forward + 5-gate promotion check (exit 1 if fail)
  scripts/generate_tearsheet.py       Standalone PDF generation
  scripts/export_fund_data.py         JSON bridge for frontend-fund/

LAYER 10: FRONTENDS
  frontend/                           Public analytics site (existing, NEVER exposes fund data)
  frontend-fund/                      Private fund dashboard (password-protected Vercel deploy)
    app/page.tsx                      NAV, day P&L, regime badge, circuit breaker status
    app/dashboard/                    Positions table + pod attribution chart
    app/risk/                         VaR gauge, drawdown chart, beta tracker
    app/tearsheets/                   PDF archive + download
```

### Fund Data Flow

```
[EXISTING — daily batch, 22:30 UTC]
  yfinance → daily_update.py → Parquet → export_frontend_data.py → CDN JSON → public site

[NEW — nightly strategy pipeline, 23:00 UTC, paper_trading.yml]
  Parquet → features → regime → optimizer → target weights
  → rebalancer check → orders → PaperBroker (Phase 1) / AlpacaBroker (Phase 2)
  → fills → ledger (append-only) → portfolio state → risk snapshot
  → circuit breaker check → tearsheet PDF → export_fund_data.py
  → frontend-fund/public/fund-data/ → Vercel deploy (password-protected)

[RISK MONITORING — runs inside paper/live pipeline after every fill batch]
  positions + prices → circuit_breaker.check() → if halt: log + alert + exit 1
```

### Key Design Decisions

**1. BrokerInterface ABC (most critical)**

Strategy code never imports `alpaca` or `ibkr` directly. The factory pattern (`get_broker(RUN_MODE)`) means swapping from paper to live trading requires zero strategy code changes — only an env variable change.

**2. Immutable Ledger**

The trade ledger is append-only Parquet. No UPDATE or DELETE ever. Portfolio state is rebuilt by replaying fills. This gives a complete audit trail and makes the system crash-safe.

**3. Consistent slippage model**

`BacktestSimulator` and `PaperBroker` use the exact same slippage model: `base_bps + 5.0 × sqrt(participation_rate) × 100`. Any gap between backtest and paper results is attributable to signal quality, not modelling differences.

**4. Go-live gates**

Paper trading is blocked until 5 backtest gates pass. Live trading is blocked until a 90-day paper trading gate passes. The circuit breaker halts all trading programmatically — the human only needs to manually reset it after investigating.

**5. Two separate Vercel deployments**

`frontend/` and `frontend-fund/` are separate Vercel projects. The public site has no knowledge of fund data. Fund data JSON files are never committed to the public repo branch.

### Secrets Required

| Secret | Used by | Where stored |
|--------|---------|-------------|
| `SUPABASE_URL` + `SUPABASE_KEY` | daily_update.py | GitHub Secrets + .env |
| `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` | alpaca_broker.py | GitHub Secrets only |
| `RUN_MODE` | get_broker() factory | GitHub Secrets (prod), .env (local) |
| `FUND_INITIAL_CAPITAL` | config.py | .env |
| `POLYGON_API_KEY` | options_fetcher.py [Phase 2] | GitHub Secrets |
| `FRED_API_KEY` | macro_fetcher.py [Phase 2] | GitHub Secrets |
