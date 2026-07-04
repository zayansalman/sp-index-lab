# SP Index Lab

**20 stocks. 95.1% of the S&P 500. Optimized to beat it.**

SP Index Lab is a research and portfolio analytics project proving that the S&P 500 is largely explained by its largest constituents. A Python backend computes the proof, walk-forward strategy backtests, and static JSON exports; a Next.js frontend presents the results as an interactive lab experience.

> **Live demo**: [sp-index-lab.vercel.app](https://sp-index-lab.vercel.app)

---

## Current Results

The top 20 configured S&P 500 names explain **95.1%** of benchmark return variance across the current local dataset, which spans **2014-01-02 to 2026-03-06**.

| Metric | S&P 500 | SP-20 Mirror | SP-20 Equal | SP-N Alpha |
|--------|---------|--------------|-------------|------------|
| CAGR | 11.3% | 19.2% | 25.4% | **29.2%** |
| Sharpe | 0.42 | 0.86 | 1.16 | **1.17** |
| Max Drawdown | -33.9% | -29.7% | -30.3% | **-29.6%** |
| Alpha | - | +6.8% | +12.1% | **+13.9%** |

Metrics are generated from `frontend/public/data/performance_metrics.json` by `scripts/export_frontend_data.py`. The public site keeps only the two simple baselines and the one optimized strategy that clears SP-20 Equal on both CAGR and Sharpe.

---

## Implemented Strategies

| Portfolio | Strategy | Status |
|-----------|----------|--------|
| SP-20 Mirror | Configured top-20 universe, price-proportional daily weights | Built |
| SP-20 Equal | Same top-20 universe, equal weighted | Built |
| SP-N Alpha | Walk-forward max-Sharpe optimizer on the configured top-20 universe | Built |

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
