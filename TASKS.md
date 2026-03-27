# S&P Index Lab — Implementation Tasks

Ordered build plan. Checked items are complete. Each phase is tested before advancing.

---

## Phase 0: Project Setup ✅
- [x] **T0.1**: Initialize project with pyproject.toml, .gitignore, README.md
- [x] **T0.2**: Create directory structure (src/, app/, scripts/, data/, tests/)
- [x] **T0.3**: Create src/config.py with all constants (TOP_50_TICKERS, TOP_20_TICKERS, INCEPTION_DATE, thresholds)
- [x] **T0.4**: Create scripts/init_db.py — Supabase table creation
- [x] **T0.5**: Create .env.example and .github/workflows/daily_update.yml
- [x] **T0.6**: Create src/data/storage.py — Supabase + Parquet helpers

---

## Phase 1: Data Pipeline ✅
- [x] **T1.1**: Build src/data/fetcher.py with retry, rate limiting, validation
- [x] **T1.2**: Fetch 12+ years of daily data for 50 stocks + S&P 500
- [x] **T1.3**: Store as Parquet in data/ directory
- [ ] **T1.4**: Write tests for data pipeline (fixtures, round-trip)

---

## Phase 2: Proof Layer ✅
- [x] **T2.1**: Build src/proof/concentration.py — variance_decomposition(), concentration_curve()
- [x] **T2.2**: R² analysis at N = 1 through 50 (result: R² = 94.9% at N=20)
- [x] **T2.3**: Mirror index construction — build_mirror_index()
- [x] **T2.4**: Performance metrics — compute_performance_metrics() (15+ metrics)
- [ ] **T2.5**: Write tests for proof layer

---

## Phase 3: Frontend — Scaffolding ✅
- [x] **T3.1**: Create frontend/ with Next.js 16 + TypeScript + Tailwind CSS v4
- [x] **T3.2**: Install: framer-motion, recharts, @radix-ui/react-tooltip, clsx, tailwind-merge
- [x] **T3.3**: Configure custom dark theme tokens in globals.css (@theme inline)
- [x] **T3.4**: Create lib/types.ts with all TypeScript interfaces (LabData, MetaData, etc.)
- [x] **T3.5**: Create lib/constants.ts with colors, timing, stage configs, chart colors
- [x] **T3.6**: Create lib/formatters.ts (formatPercent, formatRatio, formatCurrency, etc.)
- [x] **T3.7**: Create lib/tooltips.ts with rich component descriptions ("The Thinking")

---

## Phase 4: Frontend — Data Bridge ✅
- [x] **T4.1**: Write scripts/export_frontend_data.py — Python → JSON bridge
- [x] **T4.2**: Generate 8 JSON files (meta, concentration, variance, NAV, metrics, holdings, drawdowns, deviations)
- [x] **T4.3**: Enrich holdings with company names (30 tickers) and GICS sectors
- [x] **T4.4**: Enrich metrics with beta, alpha, IR, best/worst day, win rate, avg daily return
- [x] **T4.5**: Add sp20_equal drawdown series
- [x] **T4.6**: Build hooks/useLabData.ts with 8 transform functions (snake_case → camelCase)
- [x] **T4.7**: Verify JSON values match Streamlit dashboard output

---

## Phase 5: Frontend — Landing Page ✅
- [x] **T5.1**: Root layout (Space Grotesk + Geist fonts, metadata, OpenGraph, dark theme)
- [x] **T5.2**: Hero component with Framer Motion staggered entrance
- [x] **T5.3**: StatsPreview with 3 animated cards (R² 94.9%, CAGR 15.3%, Alpha +4.0%)
- [x] **T5.4**: EnterButton with animated glow border → /lab navigation

---

## Phase 6: Frontend — Machine Visualization ✅
- [x] **T6.1**: MachineCanvas.tsx with SVG viewBox (0 0 800 600)
- [x] **T6.2**: ComponentNode.tsx base (rounded rect, icon, label, LightBulb)
- [x] **T6.3**: 5 machine components (DataPipeline, ConcentrationAnalyzer, MirrorIndexBuilder, AlphaOptimizer, PerformanceMonitor)
- [x] **T6.4**: Wire.tsx + WireSystem.tsx with animated electricity flow (CSS keyframes)
- [x] **T6.5**: FlipSwitch.tsx — physical toggle switch with motion animation
- [x] **T6.6**: useMachineState.ts — useReducer state machine (IDLE → 6 stages → COMPLETE)
- [x] **T6.7**: Wire electricity CSS keyframes, glow filters, drop-shadow effects

---

## Phase 7: Frontend — Tooltip System ✅
- [x] **T7.1**: Tooltip.tsx with Radix UI + custom dark styling
- [x] **T7.2**: HTML overlay positioning system (Radix can't render inside SVG foreignObject)
- [x] **T7.3**: Integrate tooltips into all 5 machine components with "The Thinking" content

---

## Phase 8: Frontend — Results Panel ✅
- [x] **T8.1**: ResultsPanel.tsx container with Framer Motion entrance
- [x] **T8.2**: MetricCard.tsx + AnimatedCounter.tsx (counting from 0 to target)
- [x] **T8.3**: ConcentrationChart.tsx (Recharts LineChart, R² vs N, reference lines at 20 & 95%)
- [x] **T8.4**: PerformanceChart.tsx (Growth of $1, 3 series, custom tooltip)
- [x] **T8.5**: Performance comparison table (11 metrics × 3 indices: S&P 500, Mirror, Equal)
- [x] **T8.6**: DrawdownChart.tsx (Recharts AreaChart, overlaid series)
- [x] **T8.7**: HoldingsTable.tsx (20 rows: rank, ticker, name, sector, weight with proportional bars)
- [x] **T8.8**: ThinkingPanel.tsx (3 collapsible methodology sections)

---

## Phase 9: Frontend — Testing & Bug Fixes ✅
- [x] **T9.1**: Fix JSON-to-TypeScript data shape mismatches (8 transform functions)
- [x] **T9.2**: Verify all charts render with correct data values
- [x] **T9.3**: Verify animation sequence runs end-to-end (switch → stages → results)
- [x] **T9.4**: Verify production build succeeds with zero TypeScript errors

---

## Phase 10: Documentation ✅
- [x] **T10.1**: Update CLAUDE.md — full-stack context (Python + React), under 200 lines
- [x] **T10.2**: Update .cursorrules — mirror CLAUDE.md with code patterns
- [x] **T10.3**: Update PRD.md — achieved results, frontend spec, success criteria
- [x] **T10.4**: Create FRONTEND.md — visual spec, color system, components, animations
- [x] **T10.5**: Update ARCHITECTURE.md — full-stack architecture, AI-assisted development
- [x] **T10.6**: Update TASKS.md — completion status reflecting reality
- [x] **T10.7**: Update README.md — project showcase with architecture overview
- [x] **T10.8**: Verify RESEARCH.md — concentration thesis unchanged

---

## Phase 11: Deployment 🔲
- [ ] **T11.1**: Deploy frontend to Vercel (root: `frontend/`, framework: Next.js)
- [ ] **T11.2**: Verify static JSON loads correctly on production URL
- [ ] **T11.3**: Update GitHub Actions to run `export_frontend_data.py` after daily Parquet update
- [ ] **T11.4**: Test full pipeline: data update → JSON export → git push → Vercel auto-deploy

---

## Phase 12: Polish & Responsive 🔲
- [ ] **T12.1**: Mobile machine layout (vertical card pipeline for < 768px)
- [ ] **T12.2**: Page transitions between landing ↔ lab (AnimatePresence)
- [ ] **T12.3**: Lazy-load charts below the fold (dynamic imports)
- [ ] **T12.4**: Accessibility audit (keyboard nav, ARIA labels, screen reader)
- [ ] **T12.5**: Open Graph image for social sharing
- [ ] **T12.6**: Lighthouse audit (target: Performance > 90, A11y > 90)

---

## Phase 13: ML Optimizer (Future) 🔲
- [ ] **T13.1**: Build src/optimizer/classical.py (HRP, Black-Litterman, MVO)
- [ ] **T13.2**: Build src/optimizer/factor_model.py (LightGBM scoring)
- [ ] **T13.3**: Build src/optimizer/regime.py (3-state HMM: bull/bear/transition)
- [ ] **T13.4**: Build src/optimizer/ensemble.py (regime-weighted combination)
- [ ] **T13.5**: Build src/optimizer/rebalancer.py (drift, regime, quarterly triggers)
- [ ] **T13.6**: Build src/indices/ (sp20_mirror, sp20_equal, sp20_alpha, spn_alpha classes)
- [ ] **T13.7**: Write optimizer tests (constraints, diversification, regime detection)

---

## Phase 14: Backtesting Engine (Future) 🔲
- [ ] **T14.1**: Build src/backtest/metrics.py (all portfolio metrics as standalone functions)
- [ ] **T14.2**: Build src/backtest/engine.py (walk-forward: 756-day train / 21-day test)
- [ ] **T14.3**: Build src/backtest/report.py (comparative analysis, attribution)
- [ ] **T14.4**: Build scripts/full_backtest.py (orchestrator for all 4 indices)
- [ ] **T14.5**: Write backtest tests (synthetic data, no look-ahead bias verification)

---

## Phase 15: Polish & Launch (Future) 🔲
- [ ] **T15.1**: Performance attribution (stock selection vs weighting vs timing)
- [ ] **T15.2**: Downloadable PDF research report
- [ ] **T15.3**: Comparison vs real ETFs (XLG, RSP, QQQ)
- [ ] **T15.4**: Blog post / social media announcement

---

# AI Alpha Hedge Fund — Sprint Roadmap (Phases 16–27)

*The following phases evolve SP Index Lab from an analytics tool into a live algorithmic trading fund.*

---

## Phase 16: Sprint 1 — Foundation 🔲 [CRITICAL]
*Unblocks all downstream sprints. Must complete before any new infrastructure.*
- [x] **S1.1**: Extract `compute_performance_metrics()` → `src/backtest/metrics.py` shared utility
- [ ] **S1.2**: Build walk-forward backtest engine (756D train / 21D test, using existing config.py constants)
- [ ] **S1.3**: Build classical optimizers: HRP, MVO, Black-Litterman via PyPortfolioOpt
- [ ] **S1.4**: Extend `src/config.py` with fund constants (RUN_MODE, POD_ALLOCATIONS, risk limits, new data paths)

---

## Phase 17: Sprint 2 — ML Signal Stack 🔲 [HIGH]
*Core "AI alpha" capability. Required before any pod can generate signals.*
- [ ] **S2.1**: Build `src/features/technical.py` — momentum (1M/3M/6M/12M), realized vol, RSI, MA distance
- [ ] **S2.2**: Build `src/optimizer/regime.py` — 3-state Gaussian HMM (bull/bear/transition)
- [ ] **S2.3**: Build `src/optimizer/factor_model.py` — LightGBM forward 21D return quintile predictor
- [ ] **S2.4**: Build `src/optimizer/ensemble.py` — regime-weighted combination (Bull: 40% HRP + 60% MVO; Bear: 70/30)
- [ ] **S2.5**: Build `src/optimizer/rebalancer.py` — drift-check (2%), regime-change trigger, quarterly calendar

---

## Phase 18: Sprint 3 — Strategy Pods 🔲 [HIGH]
- [ ] **S3.1**: Build `src/strategies/pod_base.py` — `PodBase` ABC + `Signal` dataclass
- [ ] **S3.2**: Build `src/strategies/passive_core.py` — SP-N Alpha pod (70% of fund NAV)
- [ ] **S3.3**: Build `src/strategies/portfolio.py` — `FundPortfolio`: aggregate pods, enforce fund constraints
- [ ] **S3.4**: Build `src/indices/` classes — `SP20Mirror`, `SP20Equal`, `SP20Alpha`, `SPNAlpha`

---

## Phase 19: Sprint 4 — Execution Abstraction 🔲 [HIGH]
*Design correct once, swap brokers forever.*
- [ ] **S4.1**: Build `src/execution/order.py` — `Order`, `Fill`, `Position` dataclasses
- [ ] **S4.2**: Build `src/execution/broker_base.py` — `BrokerInterface` ABC
- [ ] **S4.3**: Build `src/execution/paper_broker.py` — `PaperBroker` with sqrt impact slippage, next-open fills
- [ ] **S4.4**: Build `src/execution/order_router.py` — target weights → `Order` list
- [ ] **S4.5**: Build `src/execution/__init__.py` — `get_broker(RUN_MODE)` factory (paper/alpaca/ibkr)

---

## Phase 20: Sprint 5 — Risk Management 🔲 [HIGH]
- [ ] **S5.1**: Build `src/risk/calculator.py` — historical VaR 95%, CVaR, portfolio beta, active share
- [ ] **S5.2**: Build `src/risk/circuit_breaker.py` — halt: drawdown > 15% or VaR > 5% NAV
- [ ] **S5.3**: Build `src/risk/monitor.py` — `RiskSnapshot` computed after every fill batch
- [ ] **S5.4**: Build `src/portfolio/ledger.py` + `state.py` — immutable trade log + live NAV tracker

---

## Phase 21: Sprint 6 — Backtest Validation 🔲 [HIGH]
*Gate before paper trading. Nothing goes live until all 5 gates pass.*
- [ ] **S6.1**: Build `src/backtest/simulator.py` — trade simulation with realistic costs and slippage
- [ ] **S6.2**: Build `src/backtest/report.py` — `BacktestReport` with 5-gate promotion check
- [ ] **S6.3**: Build `scripts/run_full_backtest.py` — walk-forward orchestration, exit 1 on gate fail
- [ ] **S6.4**: Validate SP-N Alpha: Sharpe > 0.80, max DD < 25% out-of-sample — all gates must pass

---

## Phase 22: Sprint 7 — Reporting & Tearsheets 🔲 [MEDIUM]
- [ ] **S7.1**: Build `src/reporting/tearsheet.py` — daily PDF via weasyprint + Jinja2 (7 sections)
- [ ] **S7.2**: Build `src/reporting/attribution.py` — Brinson-Hood-Beebower attribution
- [ ] **S7.3**: Build `scripts/export_fund_data.py` — JSON bridge for fund dashboard (6 output files)
- [ ] **S7.4**: Build Jinja2 HTML templates in `src/reporting/templates/`

---

## Phase 23: Sprint 8 — Paper Trading Pipeline 🔲 [MEDIUM]
- [ ] **S8.1**: Build `scripts/run_paper_trading.py` — 16-step nightly end-to-end pipeline
- [ ] **S8.2**: Build `.github/workflows/paper_trading.yml` — nightly GitHub Actions (23:00 UTC)
- [ ] **S8.3**: Build `frontend-fund/` — private Next.js dashboard (NAV, positions, risk, tearsheets)
- [ ] **S8.4**: Paper trading validation — 90-day parallel run vs backtest expectation (±5% gate)

---

## Phase 24: Sprint 9 — Vol Overlay (Phase 2, ~Q3 2026) 🔲
- [ ] **S9.1**: Integrate Polygon.io options chain data — `src/data/options_fetcher.py`
- [ ] **S9.2**: Build `src/strategies/vol_overlay.py` — covered calls at 0.20–0.30 delta, 30–45 DTE
- [ ] **S9.3**: Vol overlay backtest — validate against BXM, confirm Sharpe improvement

---

## Phase 25: Sprint 10 — Active Trading (Phase 2, ~Q4 2026) 🔲
- [ ] **S10.1**: Build cointegration pair scanner — Engle-Granger on all 190 pairs, rank by ADF stat
- [ ] **S10.2**: Build `src/strategies/active_trading.py` — pairs trading (z-score entry > 2σ, exit < 0.5σ)
- [ ] **S10.3**: Build dispersion strategy — long single-stock vol, short index vol when dispersion > 30th pct
- [ ] **S10.4**: Active trading backtest — walk-forward Sharpe + market-neutral verification (beta < 0.10)

---

## Phase 26: Sprint 11 — Live Trading (After 90-day paper gate) 🔲
- [ ] **S11.1**: Build `src/execution/alpaca_broker.py` — `AlpacaBroker(BrokerInterface)` via alpaca-py
- [ ] **S11.2**: 30-day parallel run — Alpaca paper API vs internal PaperBroker (< 2% NAV difference)
- [ ] **S11.3**: Build `scripts/run_live_trading.py` — same as paper, swap `get_broker("alpaca_live")`
- [ ] **S11.4**: Create `LIVE_TRADING_CHECKLIST.md` — all gates signed off, secrets rotated, circuit breaker tested

---

## Phase 27: Sprint 12 — Fund Operations (Phase 3, F&F) 🔲
- [ ] **S12.1**: Build `src/reporting/investor_report.py` — monthly PDF for F&F investors
- [ ] **S12.2**: Add Supabase Auth to fund dashboard — replace Vercel password protection
- [ ] **S12.3**: Build `src/portfolio/reconciler.py` — broker vs internal ledger diff + alert
- [ ] **S12.4**: Add IBKR broker adapter — `src/execution/ibkr_broker.py` via ib_insync (enables options)
