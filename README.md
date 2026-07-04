# SP Index Lab

**20 stocks. ~96% of the S&P 500's variance. Selected point-in-time, measured net of costs.**

SP Index Lab is a research and portfolio analytics project proving that the S&P 500 is largely explained by its largest constituents. A Python backend computes the proof, walk-forward strategy backtests, and static JSON exports; a Next.js frontend presents the results as an interactive lab experience.

> **Live demo**: [sp-index-lab.vercel.app](https://sp-index-lab.vercel.app)

---

## Current Results

The point-in-time top-20 S&P 500 names explain **95.6%** of benchmark daily-return variance on average across rolling one-year windows (2014-01-02 onward; data refreshes daily). All strategy returns below are **net of transaction costs** (7 bps per one-way traded notional) against the **S&P 500 total-return index**.

| Metric | S&P 500 (TR) | SP-20 Mirror | SP-20 Equal | SP-N Alpha* |
|--------|--------------|--------------|-------------|-------------|
| CAGR (net) | 13.9% | 18.4% | 16.9% | **20.9%** |
| Sharpe | 0.57 | 0.70 | 0.71 | **0.81** |
| Max Drawdown | -33.8% | -33.2% | -33.6% | **-31.0%** |
| Jensen Alpha | – | +3.3% | +2.8% | **+5.2%** |

\* SP-N Alpha is out-of-sample walk-forward (first 3 years feed the initial training window, so its column spans 2016→present); relative metrics are computed on overlapping dates only.

Metrics are generated into `frontend/public/data/performance_metrics.json` by `scripts/export_frontend_data.py` and refresh with the daily pipeline — the table above is a snapshot and the site always shows the current values. The public site keeps only the two simple baselines and the one optimized strategy that clears them.

### Methodology (what makes these numbers defensible)

- **Point-in-time universe** — at each monthly rebalance, the top-20 is selected from the stocks that were actually in the S&P 500 *and* largest at that moment (vendored membership snapshots + an anchored market-cap proxy). No survivorship bias: NVDA is not in the 2014 portfolio.
- **Transaction costs** — every rebalance is charged 7 bps per unit of one-way traded notional on actual turnover; portfolios drift buy-and-hold between rebalances.
- **Total-return benchmark** — stock prices are dividend-adjusted, so the benchmark is ^SP500TR, not the price-only ^GSPC.
- **Known limitations** — the cap proxy anchors today's share counts (buyback drift under-ranks repurchasers in early years; historical top-20 overlap is 75–90% at reference dates); five delisted ex-constituents are excluded (none was ever top-20). See [RESEARCH.md](RESEARCH.md).

---

## Implemented Strategies

| Portfolio | Strategy | Status |
|-----------|----------|--------|
| SP-20 Mirror | Point-in-time top-20, cap-proxy weights, monthly rebalance, net of costs | Built |
| SP-20 Equal | Same point-in-time top-20, equal weighted | Built |
| SP-N Alpha | Walk-forward max-Sharpe optimizer over the point-in-time top-20 | Built |

Deferred fund infrastructure such as broker execution, live paper trading, private fund dashboards, risk operations, and reporting remains roadmap work rather than implemented repo surface area.

---

## Architecture

```text
yfinance
  -> data/*.parquet
  -> scripts/run_alpha_backtest.py
  -> scripts/export_frontend_data.py
  -> frontend/public/data/*.json
  -> Next.js static frontend
  -> Vercel
```

Key modules:

| Path | Purpose |
|------|---------|
| `src/config.py` | Ticker universe, constants, backtest windows, risk and optimizer parameters |
| `src/data/fetcher.py` | yfinance data access |
| `src/data/storage.py` | Parquet and Supabase storage helpers |
| `src/proof/concentration.py` | R² curve, variance decomposition, mirror index construction |
| `src/backtest/engine.py` | Walk-forward backtest engine |
| `src/backtest/metrics.py` | Performance and relative-risk metrics |
| `src/features/` | Technical, regime, factor, sentiment, and beta research features |
| `src/optimizer/` | HRP, MVO, and ensemble optimizer research modules |
| `src/strategies/` | SP-N Alpha strategy factories |
| `scripts/daily_update.py` | Incremental market data refresh |
| `scripts/run_alpha_backtest.py` | Walk-forward strategy backtests and strategy holdings export |
| `scripts/export_frontend_data.py` | Static JSON bridge for the frontend |
| `frontend/` | Public Next.js 16 analytics site |

---

## Commands

Python backend:

```bash
uv sync
uv run python scripts/daily_update.py
uv run python scripts/run_alpha_backtest.py
uv run python scripts/export_frontend_data.py
uv run pytest tests/ -v
uv run ruff check src/ scripts/ tests/
uv run mypy src/
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
npm run lint
npm run build
```

The frontend dev server runs on [http://localhost:3000](http://localhost:3000).

---

## Automation

`.github/workflows/daily_update.yml` runs on weekdays at 22:30 UTC. The job restores cached parquet data, runs the daily market refresh, recomputes strategy backtests, exports `frontend/public/data/*.json`, and commits the generated frontend data when it changes.

---

## Documentation

| File | Purpose |
|------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Long-form architecture and fund-stack roadmap |
| [RESEARCH.md](RESEARCH.md) | Concentration thesis and methodology notes |
| [PRD.md](PRD.md) | Product requirements and current product scope |
| [TASKS.md](TASKS.md) | Build plan and sprint status |
| [FRONTEND.md](FRONTEND.md) | Frontend visual and interaction spec |
| [EXECUTION_PLAN.md](EXECUTION_PLAN.md) | Prioritized execution plan |

Roadmap documents may include future fund-management modules that are not yet implemented in the codebase.

## License

MIT
