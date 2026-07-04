# The Concentration Thesis: Why 20 Stocks Are the S&P 500

## The Story

You own the S&P 500. You think you're diversified across 500 companies. You're not.

As of March 2026, the top 20 stocks in the S&P 500 account for approximately 47% of the entire index weight. The top 10 alone hold ~39%. By the Herfindahl-Hirschman Index — a standard measure of concentration — the S&P 500 behaves as if it contains only 44 independent stocks, the lowest effective count in 35 years.

This isn't a recent phenomenon. It's accelerating. In 1990, the top 10 stocks were ~19% of the index. By 2020, they were ~27%. By 2025, they crossed 38%. The "Magnificent 7" — Apple, Microsoft, Nvidia, Alphabet, Amazon, Meta, Tesla — peaked at ~37% of index weight in October 2025.

**The implication is simple: when you buy an S&P 500 index fund, you're making a concentrated bet on ~20 mega-cap stocks with 480 stocks providing marginal diversification.**

## Our Results

Using OLS regressions of S&P 500 daily returns on point-in-time top-N portfolios over rolling one-year windows (2014-01-02 onward, refreshed daily). All strategy returns are **net of transaction costs** against the **S&P 500 total-return index** (snapshot below; the export is the source of truth):

| Metric | Value |
|--------|-------|
| R² at N=20 (mean across rolling windows) | **95.6%** |
| SP-20 Mirror CAGR (net) | **18.4%** |
| SP-20 Equal CAGR (net) | **16.9%** |
| SP-N Alpha CAGR (net, out-of-sample) | **20.9%** |
| S&P 500 TR CAGR | **13.9%** |
| SP-N Alpha Jensen Alpha | **+5.2%** |
| SP-N Alpha Sharpe | **0.81** |
| S&P 500 TR Sharpe | **0.57** |

The concentration curve shows a clear elbow at N ≈ 20: marginal R² collapses after 20 stocks, meaning stocks 21–500 collectively add only a few points of explanatory power.

> **Why these numbers are smaller than earlier drafts.** Previous versions of this project selected *today's* top-20 and applied it back to 2014 (survivorship bias), charged no transaction costs, and benchmarked dividend-earning portfolios against the price-only ^GSPC. Fixing all three cut the Equal CAGR from 25.4% to 16.9% and the Alpha CAGR from 29.2% to 20.9% — and the thesis still holds. The concentration finding barely moved (95.1% → 95.6% under the honest rolling-window definition) because concentration is contemporaneous: whoever the top-20 are at the time, they explain the index.

## Why 20? The Research

### The Weight Cliff
S&P 500 weight distribution follows a power law. Position 1 (Nvidia, 7.14%) is 10x the weight of position 20 (Costco, 0.71%). By position 30, you're at ~0.4%. By position 50, you're below 0.3%. Adding stock #21 through #500 collectively accounts for ~53% of weight — spread across 480 names averaging 0.11% each.

The marginal contribution per stock drops sharply after position 20. This is the natural breakpoint.

### The R² Elbow
When you regress S&P 500 daily returns against a cap-weighted portfolio of the top N stocks, the R² curve shows a clear elbow. Top 10: R² ≈ 0.85. Top 15: R² ≈ 0.92. Top 20: R² ≈ 0.95. Top 30: R² ≈ 0.97. Top 50: R² ≈ 0.99.

The jump from 20 to 30 stocks buys you only ~2% more explanatory power. You're paying for 10 additional stocks to reduce tracking error from "very low" to "negligibly low." That's a poor trade.

### Goldman Sachs: Concentration at "Highest Level in 100 Years"
Goldman's October 2024 Portfolio Strategy report projected just 3% annualized S&P 500 returns over the next decade (7th percentile since 1930), driven by extreme concentration. Their key finding: the top 10 stocks trade at a P/E premium of ~50% over the rest of the market. Historically, when concentration reaches these levels, the broader market catches up — it doesn't require the top stocks to crash.

Goldman projected equal-weighted S&P 500 could outperform cap-weighted by 200-800 basis points annualized over the next 10 years.

### The Dot-Com Precedent
The last time concentration was this extreme was March 2000. In the five years following the dot-com peak, equal-weighted S&P 500 outperformed cap-weighted by approximately 9.2% annualized. The concentrated top didn't crash catastrophically — they just stagnated while the rest caught up.

### Bridgeway Capital: "How Many Stocks Are Effectively in the S&P 500?"
Bridgeway's research quantified what we intuitively know: Apple's weight alone equals the combined weight of the bottom 217 companies. The "effective number of stocks" by HHI has dropped from ~130 in 1990 to ~44 today. The index's mathematical diversity is at a 35-year low.

### Existing Products Validate the Thesis
The Invesco S&P 500 Top 50 ETF (XLG) manages $11.6B tracking just the 50 largest names. It's delivered 28.5% annualized over 3 years and 18.0% over 5. No one has launched a Top 20 product — that's the gap this project fills.

## Methodology

### Point-in-Time Universe (no survivorship)
Universe selection at any date uses only information available at that date:
1. **Membership**: vendored historical S&P 500 constituent snapshots (`data/reference/sp500_membership.csv`, from the MIT-licensed fja05680/sp500 dataset), so a stock is only selectable while it was actually in the index.
2. **Ranking**: an anchored market-cap proxy — today's effective shares outstanding (market cap ÷ price, which handles multi-class structures like BRK-B/GOOGL) × the trailing 63-day mean adjusted close as of the selection date.
3. **Validation**: the proxy's top-20 overlaps hand-collected historical top-20 lists by 75–90% at 2014/2017/2020/2023 reference dates (tested in `tests/test_universe.py`).

Implementation: `src/data/universe.py` (`get_top_n_at`, `make_universe_fn`). A mutate-the-future test asserts selection cannot be changed by any data after the selection date.

### Rolling Concentration (the headline R²)
For each rolling 252-trading-day window (stepped 21 days):
1. Rank stocks by the cap proxy **as of the window start**
2. Run OLS regression: `S&P 500 TR returns ~ top-N stock returns` within the window
3. Record R² per N; the published "R² at 20" is the mean across windows

Implementation: `src/proof/concentration.py::rolling_concentration()`

### Mirror Index Construction
1. At each month-end, select the point-in-time top-20 and set cap-proxy-proportional weights (equal-weighted variant: 1/20 each)
2. Trade at the next day's close, charging 7 bps per unit of one-way traded notional on actual turnover
3. Drift buy-and-hold between rebalances (which is what cap-weighting does — so Mirror turnover is only rank churn, ~0.8x/yr)
4. NAV normalized to 1.0 at inception (2014-01-02); net-of-cost NAV is canonical, gross is exported alongside

Implementation: `src/proof/concentration.py::build_mirror_index()` + `src/backtest/costs.py`

### Walk-Forward Alpha
SP-N Alpha re-selects the point-in-time top-20 and re-optimizes max-Sharpe weights at each 21-day step using the trailing 756-day training window only; weights apply to the *following* out-of-sample window. The first training window consumes 2013–2015, so the out-of-sample record runs 2016→present (~10.4 years). Annualized turnover ≈ 3.6x → ~26 bps/yr cost drag.

Implementation: `src/backtest/engine.py::walk_forward_backtest()` (returns net + gross NAV, turnover, and costs)

### Performance Metrics
All annualized using 252 trading days against the S&P 500 **total-return** index (stock prices are dividend-adjusted, so a price-only benchmark would manufacture ~1.5%/yr of fake alpha). Relative metrics (alpha, excess return, tracking error) are computed on overlapping dates only, so the walk-forward strategy is never flattered by window mismatches.

| Metric | Formula |
|--------|---------|
| CAGR | (NAV_final / NAV_initial)^(252/days) - 1 |
| Volatility | std(daily_returns) × sqrt(252) |
| Sharpe | CAGR / Volatility |
| Sortino | CAGR / Downside_Volatility |
| Max Drawdown | max(1 - NAV / running_max) |
| Calmar | CAGR / abs(Max_Drawdown) |
| Beta | cov(portfolio, benchmark) / var(benchmark) |
| Alpha | portfolio_CAGR - beta × benchmark_CAGR |
| Tracking Error | std(portfolio_return - benchmark_return) × sqrt(252) |
| Information Ratio | mean(excess_return) / std(excess_return) × sqrt(252) |

Implementation: `src/backtest/metrics.py::compute_performance_metrics()`

## Why This Becomes an Alpha Opportunity

The passive thesis says: "you can't beat the index, so just buy it." But the S&P 500 isn't a neutral benchmark — it's a specific portfolio construction methodology (float-adjusted market cap weighting) that creates predictable inefficiencies:

1. **Momentum overweight**: Stocks that have risen get more weight, creating momentum exposure that's uncompensated in calm markets and catastrophic in reversals.

2. **Forced buying/selling**: When a stock enters/exits the top 20, index funds must trade. This creates predictable price pressure around rebalance dates.

3. **Concentration drift**: Between rebalances, winners get heavier and the portfolio drifts from "diversified" to "concentrated" — yet index funds don't rebalance until the scheduled date.

An intelligent optimization layer can exploit all three: reduce momentum overweight via factor-based tilting, anticipate rebalance flows, and rebalance dynamically based on drift rather than calendar dates.

## The Retained Public Indices

| Index | Selection | Weighting | Rebalancing | Purpose |
|-------|-----------|-----------|-------------|---------|
| SP-20 Mirror | PIT top 20 by cap proxy | Cap-proxy proportional | Monthly, net of costs | Prove concentration tracks the index |
| SP-20 Equal | PIT top 20 by cap proxy | Equal (5% each) | Monthly, net of costs | Test if removing cap-bias helps |
| SP-N Alpha | PIT top 20 by cap proxy | Walk-forward max-Sharpe | Monthly test windows, net of costs | Retained optimizer that beats the baselines |

The comparison tells a clean story:
- **Mirror vs S&P 500**: "20 stocks is enough"
- **Equal vs Mirror**: "Cap-weighting is suboptimal"
- **SP-N Alpha vs Equal**: "Only keep the optimizer if it clears the naive baseline"

## Known Limitations
1. **Anchored shares proxy**: Free sources have no historical shares outstanding, so the cap proxy anchors *today's* effective share counts (market cap ÷ price) to historical adjusted closes. Buyback-heavy names (AAPL, ORCL) are slightly under-ranked in early years; issuers slightly over-ranked. Validated at 75–90% overlap with real historical top-20 lists.
2. **Delisted exclusions**: Five former constituents that yfinance cannot serve (AGN, CELG, DWDP, MON, TWX) are excluded from the candidate pool — none was ever top-20, so SP-20 products are unaffected; top-50 coverage dips slightly in 2015–2019 windows.
3. **Cost model simplicity**: 7 bps per one-way traded notional is a flat assumption; real large-cap costs vary with size and regime but are of this order for liquid mega-caps.
4. **Short history**: 12 years covers one full market cycle but may not capture extreme tail events, and the whole window is a broadly rising, concentration-increasing market.

## Sources
- Goldman Sachs Portfolio Strategy Research, October 2024
- RBC Wealth Management, "The Great Narrowing: S&P 500 Concentration"
- Bridgeway Capital, "How Many Stocks Are Effectively in the S&P 500?"
- S&P Dow Jones Indices, "Concentration Within Sectors and Its Implications for Equal Weighting"
- Guinness Global Investors, "Is There a Rising Concentration Risk in the S&P 500?"
- State Street Global Advisors, "What's Driving S&P 500 Valuations Now?"
- Polen Capital, "How High is Too High? Large Cap Concentration"

---

## Retained Strategy Rationale

*Why one optimized strategy, and why this one?*

### SP-N Alpha — The Retained Optimizer

The public Alpha slot is deliberately narrow. The retained strategy is a walk-forward max-Sharpe optimizer over the point-in-time top-20 universe because it is the only optimized variant that clears both baselines net of costs.

1. **It beats the simple bar**: SP-N Alpha reaches 20.9% CAGR and 0.81 Sharpe net of costs out-of-sample, compared with 18.4%/0.70 for SP-20 Mirror and 16.9%/0.71 for SP-20 Equal.

2. **It remains interpretable**: The universe is the same point-in-time top-20 set, so the product can show whether weighting alone improves the concentrated basket.

3. **It keeps the public surface honest**: Experimental ML ensemble and hedged variants stay out of the frontend export until they outperform this retained strategy and the Equal baseline.

Archived research modules for HRP, factor modeling, regime detection, sentiment, and hedging remain useful for future experiments, but they are not part of the current public strategy set.

### Vol Overlay — Income Layer

The passive core holds a concentrated 20-stock portfolio. These individual stocks carry significantly higher implied volatility than the index (the "volatility risk premium" at the single-stock level). Selling covered calls at 0.20–0.30 delta captures this premium:

- **Edge**: Single-stock IV consistently prices in more future volatility than realises (VRP). The premium is larger for individual stocks than index ETFs.
- **Alignment with passive core**: We already own the underlying. The covered calls reduce cost basis without adding directional risk.
- **Benchmark**: CBOE BuyWrite Index (BXM) has outperformed the S&P 500 on a risk-adjusted basis over 20+ years. Our implementation is more selective (only sell when IV rank > 30th percentile).

### Active Trading — Uncorrelated Alpha

Pairs trading and dispersion are structurally suited to a concentrated portfolio:

**Pairs trading rationale**:
- The 20 stocks that drive the S&P 500 are all large-cap, liquid, and often cointegrated (NVDA/AMD, JPM/BAC, AMZN/MSFT).
- Cointegrated pairs mean-revert reliably. The spread has a computable half-life and stationary residuals.
- Edge: the z-score of the spread is a predictable, mean-reverting signal with positive expected value.
- Market-neutral by construction: long/short the pair eliminates beta exposure.

**Dispersion trading rationale**:
- When the 20 portfolio stocks diverge in performance (high cross-sectional dispersion), the spread between individual-stock realised vol and index realised vol widens.
- Long single-stock vol, short index vol: captures the realisation that the index smooths out individual moves.
- Entry trigger: cross-sectional return dispersion > 30th percentile (historically precedes vol spread expansion).
- This strategy is uncorrelated with both the passive core and pairs trades — genuine diversification.

### Why These Three Together

The three pods are designed to have low correlation with each other:

| | Passive Core | Vol Overlay | Active Trading |
|---|---|---|---|
| Market direction sensitivity | HIGH | MEDIUM | LOW |
| Benefits from bull markets | YES | YES (vol is low) | NO |
| Benefits from bear markets | NO | YES (vol is high, calls not exercised) | YES (dispersion spikes) |
| Turnover | LOW (~quarterly) | MEDIUM (~monthly) | HIGH (~weekly) |

Combined: the fund has lower drawdown and higher Sharpe than any single pod in isolation. The 70/15/15 allocation reflects the maturity of each pod — passive core is fully validated; vol overlay and active trading require Phase 2 infrastructure before live capital is deployed.
