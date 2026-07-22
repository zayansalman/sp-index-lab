/* ================================================================
   S&P Index Lab -- Tooltip Content
   Rich contextual information for each machine component.
   Every tooltip includes what it does, WHY we built it that way,
   and a single standout insight.

   Keep these QUALITATIVE: specific performance numbers live in the
   exported data (meta.json headline, performance_metrics.json) and
   are rendered by data-driven components. Numbers written here go
   stale the moment the daily pipeline refreshes.
   ================================================================ */

import type { ComponentTooltip } from "./types";

/* ──────────────────────────────────────────────────────────────
   Tooltip Registry
   Keyed by component ID used in the machine SVG / diagram.
   ────────────────────────────────────────────────────────────── */

export const tooltips: Record<string, ComponentTooltip> = {
  /* ── 1. Data Pipeline ─────────────────────────────────────── */
  "data-pipeline": {
    id: "data-pipeline",
    title: "Data Pipeline",
    subtitle: "Market data ingestion and validation engine",
    description:
      "Ingests 13+ years of daily prices and volumes for ~90 current and " +
      "former S&P 500 large-caps via yfinance, plus the S&P 500 total-return " +
      "benchmark. Includes exponential backoff retries, rate limiting, and " +
      "comprehensive data validation (NaN detection, extreme return " +
      "filtering, forward-fill).",
    thinking:
      "Raw market data is the foundation. The candidate pool covers every " +
      "name that plausibly cracked the top 50 by market cap since 2014 — " +
      "you cannot rank what you did not fetch, and ranking only today's " +
      "winners would bake survivorship bias into every result downstream.",
    keyInsight:
      "Point-in-time universe: at each date, only the stocks that were " +
      "actually the largest at that moment are selectable",
  },

  /* ── 2. Concentration Analyzer ────────────────────────────── */
  "concentration-analyzer": {
    id: "concentration-analyzer",
    title: "Concentration Analyzer",
    subtitle: "OLS regression-based variance decomposition",
    description:
      "Runs OLS regressions of S&P 500 daily returns against top-N stock " +
      "returns over rolling one-year windows. Stocks are ranked by market " +
      "cap as of each window's start, so the selection never peeks at the " +
      "future.",
    thinking:
      "If the S&P 500 were truly diversified, 20 stocks should explain only " +
      "a sliver of its variance. Instead, the top-20 at each point in time " +
      "explain the overwhelming majority. The concentration curve shows an " +
      "'elbow' around 18–20 stocks where marginal R-squared collapses " +
      "— the rest of the index is effectively noise.",
    keyInsight:
      "The animated counter shows the rolling-window average R² at 20 " +
      "stocks, computed fresh from the latest data",
  },

  /* ── 3. Mirror Index Builder ──────────────────────────────── */
  "mirror-builder": {
    id: "mirror-builder",
    title: "Mirror Index Builder",
    subtitle: "Cap-weighted and equal-weighted SP-20 construction",
    description:
      "Constructs cap-weighted and equal-weighted portfolios of the " +
      "point-in-time top-20, rebalanced monthly with turnover-based " +
      "transaction costs. NAV is normalized to 1.0 at inception for direct " +
      "comparison with the S&P 500 total-return index.",
    thinking:
      "If 20 stocks explain the index, a portfolio of just those 20 should " +
      "track it closely. Between rebalances the portfolio drifts buy-and-hold " +
      "— which is exactly what cap-weighting does — so turnover is " +
      "only rank churn, and the cost drag stays small and honest.",
    keyInsight:
      "Both baselines are net of costs and point-in-time — no " +
      "survivorship, no free daily rebalancing",
  },

  /* ── 4. Alpha Optimizer ───────────────────────────────────── */
  "alpha-optimizer": {
    id: "alpha-optimizer",
    title: "Alpha Optimizer",
    subtitle: "Self-adjusting concentration-elbow portfolio",
    description:
      "Runs SP-N Alpha: each month it reads the concentration 'elbow' from " +
      "trailing data and equal-weights that many point-in-time top names " +
      "(dynamic N, 10–30), net of transaction costs. Selection uses only " +
      "data available at each rebalance, applied to the following month.",
    thinking:
      "Selected on a 2014–2023 development window against a locked 2024+ " +
      "holdout (deflated Sharpe 0.96 across 14 trials, so it is not selection " +
      "noise). It beat the S&P 500 out-of-sample but did not clear every " +
      "pre-registered bar vs SP-20 Equal — so all strategies are shown side " +
      "by side rather than one being crowned.",
    keyInsight:
      "Every number shown for SP-N Alpha is out-of-sample and net of costs " +
      "— see the results panel for current figures",
  },

  /* ── 5. Performance Monitor ───────────────────────────────── */
  "performance-monitor": {
    id: "performance-monitor",
    title: "Performance Monitor",
    subtitle: "Comprehensive risk-adjusted metric computation",
    description:
      "Computes 15+ metrics including CAGR, Sharpe, Sortino, Maximum Drawdown, " +
      "Calmar, Beta, Alpha (Jensen's), Tracking Error, and Information Ratio. " +
      "All annualized using 252 trading days, against the total-return " +
      "benchmark.",
    thinking:
      "A single metric tells one story. Sharpe captures risk-adjusted return, " +
      "but ignores the path (drawdowns matter for real portfolios). Sortino " +
      "penalizes only downside volatility. Tracking error shows how closely " +
      "we mirror the benchmark. Together, they paint the complete picture.",
    keyInsight:
      "Relative metrics are computed on overlapping dates only, so " +
      "walk-forward strategies are never flattered by window mismatches",
  },
} as const;

/* ──────────────────────────────────────────────────────────────
   Helper: get tooltip by component ID
   Returns undefined if no tooltip is registered for the given ID.
   ────────────────────────────────────────────────────────────── */

export function getTooltip(componentId: string): ComponentTooltip | undefined {
  return tooltips[componentId];
}

/* ──────────────────────────────────────────────────────────────
   All tooltip IDs (useful for iteration / validation)
   ────────────────────────────────────────────────────────────── */

export const tooltipIds = Object.keys(tooltips) as Array<keyof typeof tooltips>;
