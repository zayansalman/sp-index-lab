# S&P Index Lab — Product Requirements Document

## Executive Summary
S&P Index Lab is a live portfolio analytics platform that proves the S&P 500 is effectively a ~20-stock index, then builds AI-optimized derived indices that beat it. The platform consists of a Python analytics backend and an interactive React frontend that communicates the concentration thesis through a machine-metaphor visualization.

**Core thesis**: The top 20 S&P 500 stocks explain 94.9% of index variance (R² = 0.949). A concentrated, intelligently-weighted portfolio of these stocks delivers superior risk-adjusted returns.

## Target Audience
1. **Hiring managers** at quant firms, MBB consulting, and tech companies — want to see rigorous methodology, clean code, independent thinking
2. **Finance/tech community** — want a provocative claim backed by data with a live tracker
3. **Personal use** — genuine alpha generation and portfolio tracking

## Product Goals
| Goal | Metric | Status |
|------|--------|--------|
| Prove concentration thesis | R² > 90% for top 20 | **Achieved: 94.9%** |
| Build mirror index that beats S&P | Mirror CAGR > S&P CAGR | **Achieved: 15.3% vs 11.3%** |
| Interactive web visualization | < 3s load, all animations smooth | **Built** |
| Daily automated data updates | GitHub Actions cron running | **Configured** |
| Enterprise-quality codebase | Typed, documented, tested | **In progress** |

## The Four Indices

### Index 1: SP-20 Mirror (Built)
- **What**: Top 20 S&P 500 stocks by market cap, weighted proportionally
- **Rebalancing**: Daily (price-proportional weights)
- **Purpose**: Prove that 20 stocks closely track a 500-stock index
- **Results**: CAGR 15.3%, Sharpe 0.68, R² 94.9% vs S&P 500

### Index 2: SP-20 Equal (Built)
- **What**: Same top 20 stocks, equal weight (5% each)
- **Rebalancing**: Daily reset to equal
- **Purpose**: Test whether removing mega-cap concentration bias improves returns
- **Results**: CAGR 14.2%, Sharpe 0.63

### Index 3: SP-20 Alpha (Planned)
- **What**: Fixed 20 stocks, AI-optimized weights
- **Rebalancing**: Dynamic — drift > 2%, regime change, or quarterly
- **Optimization**: Ensemble of HRP + factor model + regime-aware tilts
- **Constraints**: No stock > 15%, no stock < 1%

### Index 4: SP-N Alpha (Planned)
- **What**: AI selects both N (10-30) stocks and weights from top 50
- **Rebalancing**: Dynamic (same triggers as SP-20 Alpha)
- **Purpose**: Fully autonomous flagship index

## The Proof Layer

### P1: Variance Decomposition (Built)
- OLS regression of S&P 500 returns against top-N stock returns
- R² curve shows elbow at N ≈ 20 (R² = 94.9%)
- Marginal R² drops below 0.5% after 20 stocks

### P2: Concentration Curve (Built)
- Cumulative R² plotted against number of stocks (1 to 50)
- Clear visual inflection point at ~20 stocks
- Interactive chart with tooltips showing which stock was added at each step

### P3: Performance Comparison (Built)
- Growth of $1 chart: S&P 500 vs SP-20 Mirror vs SP-20 Equal
- 15+ metrics computed: CAGR, Sharpe, Sortino, Max DD, Calmar, Beta, Alpha, TE, IR
- Drawdown analysis with overlaid series

### P4: Holdings Analysis (Built)
- Top 20 holdings with ticker, company name, sector, weight
- Cap-weighted vs equal-weighted weight comparison
- Sector concentration visualization

## Frontend Experience

### Landing Page (`/`)
- Dark cinematic background (`#0A0A0F`) with subtle grid and radial glow
- Hero: "S&P INDEX LAB" with animated entrance
- Three stat preview cards (R² 94.9%, CAGR 15.3%, Alpha +4.0%)
- Glowing CTA: "Enter the Lab" → `/lab`

### Machine Lab (`/lab`)
- Full-viewport SVG machine with 5 interconnected components
- Flip switch triggers sequential animation (~8 seconds)
- Each component has rich tooltips explaining methodology ("The Thinking")
- Results panel slides in after machine completes with all charts and metrics

### Animation Sequence
| Stage | Duration | Component |
|-------|----------|-----------|
| 1 | 1.2s | Powering Up — circuits initialize |
| 2 | 1.5s | Data Pipeline — ticker scroll effect |
| 3 | 1.5s | Concentration Analyzer — R² counter |
| 4 | 1.5s | Mirror Index Builder — gears activate |
| 5 | 1.5s | Alpha Optimizer — brain pulses |
| 6 | 1.5s | Performance Monitor — gauges swing |
| 7 | 0s | Complete — results panel appears |

## ML/AI Optimization Engine (Planned)

### Factor Model
- Features: momentum (1M-12M), volatility (20D/60D), mean reversion (RSI, MA distance), quality (ROE, D/E), beta, correlation
- Model: LightGBM with walk-forward cross-validation
- Target: forward 1-month return quintile

### Classical Optimization
- HRP (Hierarchical Risk Parity) — most robust
- Mean-Variance with Black-Litterman views
- Minimum Variance with factor tilt
- Ensemble: regime-weighted average

### Regime Detection
- 3-state HMM (bull/bear/transition)
- Features: S&P 500 returns, realized vol, VIX, yield curve
- Influences optimizer ensemble weights and position limits

## Data Pipeline
```
GitHub Actions (weekdays 22:30 UTC)
  → scripts/daily_update.py
  → yfinance fetch (50 stocks + benchmarks)
  → Compute daily returns & index NAVs
  → Check rebalance triggers
  → Write to Supabase + Parquet
  → scripts/export_frontend_data.py
  → Generate 8 JSON files → frontend/public/data/
  → Commit + push → Vercel auto-deploys
```

## Non-Functional Requirements
- Frontend loads in < 3 seconds (static JSON, no API calls)
- Daily update completes in < 5 minutes
- All Python code has type hints and docstrings
- TypeScript strict mode with no `any` in component props
- Accessible: keyboard navigation, ARIA labels, screen reader support
- Responsive: desktop, tablet, mobile breakpoints

## Success Criteria
1. ✅ SP-20 Mirror tracks S&P 500 with high R² (achieved: 94.9%)
2. ✅ SP-20 Mirror outperforms S&P 500 CAGR (achieved: 15.3% vs 11.3%)
3. ✅ Interactive frontend communicates thesis visually
4. ✅ Proof layer demonstrates top 20 explain > 90% variance
5. ⬜ SP-20 Alpha achieves higher Sharpe than S&P 500
6. ⬜ SP-N Alpha achieves highest risk-adjusted return
7. ⬜ Daily automation running end-to-end
8. ⬜ GitHub repo showcases enterprise-quality AI-assisted development
