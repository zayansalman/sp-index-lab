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
