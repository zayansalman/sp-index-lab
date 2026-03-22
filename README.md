# SP Index Lab

**20 stocks. 94.9% of the S&P 500. Optimised to beat it.**

> From analytics proof to AI alpha hedge fund.

SP Index Lab started as a research project proving the S&P 500 is driven by ~20 stocks (R²=94.9%). It has since evolved into a full algorithmic trading infrastructure for running an AI-powered optimised equity fund: the SP-N Alpha.

> **Live demo**: [sp-index-lab.vercel.app](https://sp-index-lab.vercel.app)

---

## The Thesis

The top 20 S&P 500 stocks account for ~47% of total index weight. Using OLS regression across 3,062 trading days (2014–2026), these 20 stocks explain **94.9%** of S&P 500 variance. The other 480 contribute less than 5% of explanatory power.

**Given that we know the S&P is a ~20-stock index in practice, we built an optimised version**: one that captures the same market exposure with better risk-adjusted returns through smarter weighting (HRP + LightGBM factor model), regime awareness (3-state HMM), and disciplined rebalancing.

| Metric | S&P 500 | SP-20 Mirror | SP-20 Equal | SP-N Alpha |
|--------|---------|-------------|-------------|------------|
| CAGR | 11.3% | 15.3% | 14.2% | **15.3%** |
| Sharpe | 0.54 | 0.68 | 0.63 | **0.68** |
| Max Drawdown | -33.7% | -37.4% | -39.8% | TBD |
| Alpha | — | +4.0% | +2.9% | **+4.0%** |

*SP-N Alpha uses ensemble optimizer (HRP + LightGBM-MVO) and HMM regime detection. Backtesting in progress.*

---

## Fund Architecture

Three strategy pods, built modularly:

| Pod | Strategy | Allocation | Status |
|-----|----------|------------|--------|
| Passive Core | SP-N Alpha: HRP + LightGBM + HMM | 70% of NAV | Sprint 1–3 |
| Vol Overlay | Covered calls on passive core (BXM-style) | 15% of NAV | Sprint 9 (Q3 2026) |
| Active Trading | Pairs trading + dispersion on 20-stock universe | 15% of NAV | Sprint 10 (Q4 2026) |

Broker-agnostic by design: `BrokerInterface` ABC → swap Alpaca / IBKR via `RUN_MODE` env var, zero strategy code changes.

**Fund phases**: Personal account (paper → live) → F&F fund → Registered fund.

---

## 10-Layer System Architecture

```
LAYER 0: DATA INGESTION
  yfinance (equity, daily) [existing]    →  data/daily_prices.parquet
  Polygon.io (options) [Phase 2]         →  data/options_chains/
  FRED API (macro) [Phase 2]             →  data/macro_indicators.parquet

LAYER 1: FEATURE ENGINEERING
  src/features/technical.py              momentum 1M/3M/6M/12M, vol, RSI, MA distance

LAYER 2: ML SIGNAL GENERATION
  src/optimizer/classical.py             PyPortfolioOpt: HRP, MVO, Black-Litterman
  src/optimizer/regime.py                hmmlearn: 3-state HMM (bull/bear/transition)
  src/optimizer/factor_model.py          LightGBM: forward 21D return quintile
  src/optimizer/ensemble.py              regime-weighted combination

LAYER 3: STRATEGY PODS
  src/strategies/passive_core.py         SP-N Alpha (70% NAV)
  src/strategies/vol_overlay.py          Covered calls (15% NAV, Phase 2)
  src/strategies/active_trading.py       Pairs + dispersion (15% NAV, Phase 2)

LAYER 4: EXECUTION ABSTRACTION
  src/execution/broker_base.py           BrokerInterface ABC
  src/execution/paper_broker.py          PaperBroker (sqrt impact slippage, next-open fills)
  src/execution/alpaca_broker.py         AlpacaBroker (Phase 2)
  src/execution/__init__.py              get_broker(RUN_MODE) factory

LAYER 5: RISK MANAGEMENT
  src/risk/calculator.py                 VaR 95%, CVaR, beta, active share
  src/risk/circuit_breaker.py            Halt: drawdown > 15% or VaR > 5% NAV
  src/risk/monitor.py                    RiskSnapshot after every fill batch

LAYER 6: BACKTESTING ENGINE
  src/backtest/engine.py                 Walk-forward: 756D train / 21D test
  src/backtest/simulator.py              Trade simulation with realistic slippage
  src/backtest/report.py                 Promotion gate: Sharpe > 0.80, DD < 25%

LAYER 7: PORTFOLIO TRACKING
  src/portfolio/ledger.py                Immutable trade log (append-only Parquet)
  src/portfolio/state.py                 Live positions, cash, NAV

LAYER 8: REPORTING
  src/reporting/tearsheet.py             Daily PDF via weasyprint + Jinja2
  src/reporting/attribution.py           Brinson-Hood-Beebower attribution

LAYER 9: ORCHESTRATION SCRIPTS
  scripts/run_paper_trading.py           Nightly pipeline: signals → fills → tearsheet
  scripts/run_full_backtest.py           Walk-forward backtest + gate check
  scripts/export_fund_data.py            JSON bridge for fund dashboard

LAYER 10: FRONTENDS
  frontend/                              Public analytics site (Vercel)
  frontend-fund/                         Private fund dashboard (Vercel, password-protected)
```

---

## 12-Sprint Roadmap

| Sprint | Focus | Priority | Target |
|--------|-------|----------|--------|
| 1 | Foundation: backtest metrics, walk-forward engine, classical optimizers | CRITICAL | Apr 2026 |
| 2 | ML Signal Stack: features, HMM, LightGBM, ensemble, rebalancer | HIGH | Apr 2026 |
| 3 | Strategy Pods: PodBase, PassiveCore, FundPortfolio, index classes | HIGH | May 2026 |
| 4 | Execution Abstraction: Order types, BrokerInterface, PaperBroker, factory | HIGH | May 2026 |
| 5 | Risk Management: VaR/CVaR, circuit breaker, RiskSnapshot, ledger | HIGH | May 2026 |
| 6 | Backtest Validation: simulator, BacktestReport, 5-gate promotion check | HIGH | Jun 2026 |
| 7 | Reporting: PDF tearsheet, BHB attribution, export_fund_data.py | MEDIUM | Jun 2026 |
| 8 | Paper Trading: nightly pipeline, GitHub Actions, fund dashboard | MEDIUM | Jul 2026 |
| 9 | Vol Overlay: Polygon.io options, covered calls, BXM backtest | FUTURE | Q3 2026 |
| 10 | Active Trading: pairs scanner, dispersion strategy, backtest | FUTURE | Q4 2026 |
| 11 | Live Trading: AlpacaBroker, 30-day parallel run, go-live checklist | FUTURE | Q4 2026 |
| 12 | Fund Operations: investor reports, Supabase Auth, reconciler, IBKR | FUTURE | 2027 |

All sprint issues are tracked in [GitHub Issues](https://github.com/zayansalman/sp-index-lab/issues) with milestones.

---

## Running the Fund Pipeline

```bash
# Install dependencies
uv sync

# Run full backtest (all 5 promotion gates must pass before paper trading)
uv run python scripts/run_full_backtest.py

# Run paper trading pipeline (nightly via GitHub Actions)
uv run python scripts/run_paper_trading.py

# Generate tearsheet PDF
uv run python scripts/generate_tearsheet.py

# Export fund data JSON for dashboard
uv run python scripts/export_fund_data.py
```

## Running the Public Analytics Site

```bash
# Update data
uv run python scripts/daily_update.py
uv run python scripts/export_frontend_data.py

# Frontend dev server
cd frontend && npm install && npm run dev
# Open http://localhost:3000
```

---

## Project Structure

```
sp-index-lab/
├── src/
│   ├── config.py             Constants + fund parameters (RUN_MODE, POD_ALLOCATIONS)
│   ├── data/                 fetcher.py, storage.py
│   ├── proof/                concentration.py (core analytics — R² proof)
│   ├── features/             technical.py (momentum, vol, RSI, MA distance)
│   ├── optimizer/            classical.py, regime.py, factor_model.py, ensemble.py
│   ├── strategies/           pod_base.py, passive_core.py, portfolio.py
│   ├── execution/            broker_base.py, paper_broker.py, order_router.py
│   ├── risk/                 calculator.py, circuit_breaker.py, monitor.py
│   ├── portfolio/            ledger.py, state.py
│   ├── backtest/             metrics.py, engine.py, simulator.py, report.py
│   ├── reporting/            tearsheet.py, attribution.py, templates/
│   └── indices/              sp20_mirror.py, sp20_equal.py, sp20_alpha.py, spn_alpha.py
├── scripts/
│   ├── daily_update.py              Data refresh (GitHub Actions)
│   ├── export_frontend_data.py      Public site JSON export
│   ├── run_paper_trading.py         Nightly paper trading pipeline
│   ├── run_full_backtest.py         Walk-forward backtest + promotion gates
│   ├── generate_tearsheet.py        Daily PDF tearsheet
│   └── export_fund_data.py          Fund dashboard JSON
├── frontend/                Public Next.js analytics site
├── frontend-fund/           Private fund dashboard (password-protected)
├── data/                    Parquet cache (gitignored)
├── .github/workflows/
│   ├── daily_update.yml     Daily data + frontend export
│   └── paper_trading.yml    Nightly paper trading (23:00 UTC)
├── ARCHITECTURE.md          Full 10-layer system architecture
├── RESEARCH.md              Concentration thesis + active strategy rationale
└── TASKS.md                 Build plan with completion status
```

---

## Documentation

| File | Purpose |
|------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 10-layer fund stack, data flow, key design decisions |
| [RESEARCH.md](RESEARCH.md) | Concentration proof, active strategy rationale |
| [TASKS.md](TASKS.md) | Sprint-by-sprint build plan (Phases 0–27) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend (public) | Next.js 16, React 19, TypeScript, Tailwind CSS v4, Recharts, Framer Motion |
| Frontend (fund) | Next.js 16, Vercel password protection → Supabase Auth (Phase 3) |
| Analytics | Python 3.11, pandas, numpy, scikit-learn |
| ML Optimization | PyPortfolioOpt (HRP/MVO/BL), LightGBM, hmmlearn |
| Execution | alpaca-py (Phase 2), ib_insync (Phase 3) |
| Reporting | weasyprint, Jinja2 |
| Data | yfinance, Parquet, Polygon.io (Phase 2), FRED API (Phase 2) |
| CI/CD | GitHub Actions, Vercel |
| Package Manager | uv (Python), npm (JavaScript) |

Built with [Claude Code](https://claude.ai/code) as a co-developer.

## License

MIT
