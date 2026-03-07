# Build Workflow: Claude Code + Cursor

## Step-by-Step: How to Build This Project

### Prerequisites
1. Install Claude Code: `npm install -g @anthropic-ai/claude-code`
2. Install Cursor: https://cursor.com
3. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
4. Create free Supabase project: https://supabase.com
5. Create GitHub repo: `sp-index-lab` (public)

---

## Step 1: Scaffold with Claude Code (30 min)

Open terminal in your empty project directory:

```bash
cd sp-index-lab

# Copy CLAUDE.md, PRD.md, ARCHITECTURE.md, TASKS.md, .cursorrules into this directory

# Start Claude Code
claude

# Give it the project context and ask it to scaffold
```

**Prompt for Claude Code:**
```
Read CLAUDE.md, PRD.md, ARCHITECTURE.md, and TASKS.md. 
Then execute Phase 0 from TASKS.md completely:
- Initialize pyproject.toml with all dependencies
- Create the full directory structure
- Create src/config.py with all constants
- Create scripts/init_db.py
- Create .env.example
- Create .github/workflows/daily_update.yml stub
- Create src/data/storage.py with Supabase + Parquet helpers
- Make sure `uv sync` works
```

**Verify:** `uv sync` completes without errors. Directory structure matches CLAUDE.md.

---

## Step 2: Data Pipeline with Claude Code (1 hour)

**Prompt:**
```
Execute Phase 1 from TASKS.md:
- Build src/data/fetcher.py with all functions specified
- Build src/data/constituents.py
- Build the initial data load script
- Write tests for the data pipeline
- Run the tests and fix any failures
```

**Verify:** `uv run pytest tests/test_fetcher.py -v` passes. 
`uv run python -c "from src.data.fetcher import fetch_sp500_index; print(fetch_sp500_index('2024-01-01', '2024-01-31').shape)"` returns data.

---

## Step 3: Proof Layer with Claude Code (1 hour)

**Prompt:**
```
Execute Phase 2 from TASKS.md:
- Build all four proof modules (variance decomposition, R², contribution, tracking error)
- Write tests
- Run the proof calculations on 5 years of data and print key results:
  - What % of S&P 500 variance do the top 20 stocks explain?
  - What is the R² of top 20 portfolio vs S&P 500?
  - What is the tracking error of top 20 cap-weighted vs S&P 500?
```

**Verify:** Numbers are reasonable (R² > 0.9 for top 20, tracking error < 5%).

---

## Step 4: Index Construction with Claude Code (1 hour)

**Prompt:**
```
Execute Phase 3 from TASKS.md:
- Build base.py abstract class
- Build sp20_mirror.py and sp20_equal.py
- Build NAV computation pipeline
- Compute NAV series for SP-20 Mirror and SP-20 Equal from 2014 to today
- Store in Parquet
- Write tests
- Print: total return, annualized return, Sharpe ratio for both indices vs S&P 500
```

**Verify:** SP-20 Mirror closely tracks S&P 500. Both indices have reasonable returns.

**Note:** sp20_alpha.py and spn_alpha.py will be completed after Phase 4 (optimizer).

---

## Step 5: ML Optimizer with Claude Code (2-3 hours)

This is the most complex phase. Break it into sub-prompts:

**Prompt 5a (Classical Optimizers):**
```
Execute T4.1 from TASKS.md:
- Build src/optimizer/classical.py with HRP, Black-Litterman, and min-variance
- Use PyPortfolioOpt
- All must respect position constraints (1% min, 15% max)
- Write tests that verify weights sum to 1.0 and respect constraints
```

**Prompt 5b (Factor Model):**
```
Execute T4.2 from TASKS.md:
- Build src/optimizer/factor_model.py
- Compute all features specified in PRD
- Train LightGBM with walk-forward CV
- Score current stocks
- Write tests for feature computation and model output
```

**Prompt 5c (Regime Detection):**
```
Execute T4.3 from TASKS.md:
- Build src/optimizer/regime.py with 3-state HMM
- Features: S&P returns, realized vol, VIX, yield curve
- Write tests
- Run on historical data and print regime timeline
```

**Prompt 5d (Ensemble + Rebalancer):**
```
Execute T4.4 and T4.5 from TASKS.md:
- Build ensemble.py combining all optimizers with regime-aware weighting
- Build rebalancer.py with all trigger checks
- Now complete sp20_alpha.py and spn_alpha.py using the optimizer
- Write tests
- Run optimizer on current data and print recommended weights for all indices
```

**Verify:** All four indices now produce weights. Optimizer respects constraints.

---

## Step 6: Backtesting with Claude Code (1-2 hours)

**Prompt:**
```
Execute Phase 5 from TASKS.md:
- Build metrics.py, engine.py, report.py
- Build scripts/full_backtest.py
- Run the full walk-forward backtest from 2014 to present for all 4 indices
- Save results to Parquet
- Print comparison table: total return, ann. return, Sharpe, max drawdown, win rate vs S&P 500
```

**Verify:** Backtest completes. SP-20 Alpha and SP-N Alpha show higher Sharpe than S&P 500. If not, iterate on optimizer parameters.

---

## Step 7: Switch to Cursor for Dashboard (2-3 hours)

This is where you switch tools. Open the project in Cursor.

**Why switch:** Dashboard work is iterative — you'll want to see changes instantly, tweak layouts, adjust chart formatting. Cursor's inline editing and visual feedback loop is faster for this.

**In Cursor, use Composer mode (Cmd+I) with prompts like:**

```
Build app/Home.py — the Streamlit home page. 
Read PRD.md "Dashboard Pages > Home Page" section for requirements.
Load data from Parquet files in data/ directory using @st.cache_data.
Use Plotly for all charts.
Wide layout, dark-compatible theme.
```

Then iterate page by page:
- `Build app/pages/1_Proof.py per the PRD spec`
- `Build app/pages/2_Indices.py per the PRD spec`
- `Build app/pages/3_Alpha.py per the PRD spec`
- `Build app/pages/4_Backtest.py per the PRD spec`
- `Build app/pages/5_Holdings.py per the PRD spec`

**Use Cmd+K for quick refinements:**
- "Make this chart use a dark background"
- "Add a timeframe selector: 1Y, 3Y, 5Y, 10Y, All"
- "Make the metrics cards show green/red based on positive/negative"

**Verify:** `uv run streamlit run app/Home.py` — dashboard loads fast, all pages work.

---

## Step 8: Back to Claude Code for Automation (30 min)

**Prompt:**
```
Execute Phase 7 from TASKS.md:
- Build scripts/daily_update.py — the full daily pipeline
- Configure .github/workflows/daily_update.yml with proper cron and secrets
- Make the daily update idempotent and well-logged
- Write a comprehensive README.md with screenshots section, architecture overview, live demo link, and setup instructions
```

---

## Step 9: Deploy (30 min, manual)

1. Push to GitHub
2. Go to share.streamlit.io
3. Connect repo, set `app/Home.py` as main file
4. Add secrets (SUPABASE_URL, SUPABASE_KEY)
5. Deploy
6. Add repository secrets to GitHub for Actions
7. Verify daily workflow runs on next trading day

---

## Ongoing: Iterate in Cursor

After v1 is live, use Cursor for:
- Tuning chart aesthetics
- Adding new metrics
- Improving factor model features
- A/B testing optimizer parameters
- Bug fixes from daily runs

Use Claude Code for:
- Major refactors (e.g., adding a new index type)
- Infrastructure changes (e.g., adding Redis cache)
- Test suite expansion
- CI/CD pipeline improvements

---

## Time Estimate

| Phase | Tool | Time |
|-------|------|------|
| 0: Setup | Claude Code | 30 min |
| 1: Data Pipeline | Claude Code | 1 hour |
| 2: Proof Layer | Claude Code | 1 hour |
| 3: Index Construction | Claude Code | 1 hour |
| 4: ML Optimizer | Claude Code | 2-3 hours |
| 5: Backtesting | Claude Code | 1-2 hours |
| 6: Dashboard | Cursor | 2-3 hours |
| 7: Automation | Claude Code | 30 min |
| 8: Deploy | Manual | 30 min |
| **Total** | | **~10-14 hours** |

This is elapsed time assuming you're reviewing Claude Code's output and course-correcting. Actual coding by you: minimal. Most of your time goes into reviewing results, verifying numbers make sense, and making design decisions when Claude Code asks.
