# S&P Index Lab — Architecture & Infrastructure

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
