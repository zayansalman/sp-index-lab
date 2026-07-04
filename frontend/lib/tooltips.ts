/* ================================================================
   S&P Index Lab -- Tooltip Content
   Rich contextual information for each machine component.
   Every tooltip includes what it does, WHY we built it that way,
   and a single standout insight.
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
      "Ingests 12+ years of daily prices for 50 S&P 500 stocks via yfinance. " +
      "Includes exponential backoff retries, rate limiting, and comprehensive " +
      "data validation (NaN detection, extreme return filtering, forward-fill).",
    thinking:
      "Raw market data is the foundation. We chose 50 stocks (not all 500) " +
      "because we're testing whether a small subset explains the index \u2014 " +
      "starting with the top 50 by market cap gives us the most likely " +
      "candidates. Data quality matters: one bad data point can cascade " +
      "through all analytics.",
    keyInsight:
      "3,062 trading days of clean, validated data from 2014 to present",
  },

  /* ── 2. Concentration Analyzer ────────────────────────────── */
  "concentration-analyzer": {
    id: "concentration-analyzer",
    title: "Concentration Analyzer",
    subtitle: "OLS regression-based variance decomposition",
    description:
      "Runs OLS regression of S&P 500 daily returns against top-N stock " +
      "returns, measuring how much variance each subset explains. Stocks " +
      "are ranked by absolute correlation with the benchmark and added " +
      "one-by-one.",
    thinking:
      "If the S&P 500 were truly diversified, removing any 20 stocks should " +
      "leave ~96% of variance unexplained. But we found the opposite \u2014 " +
      "20 stocks explain 95.1%. The concentration curve shows an 'elbow' " +
      "around 18\u201320 stocks where marginal R-squared drops below 0.5%, " +
      "proving the rest are effectively noise.",
    keyInsight:
      "20 stocks explain 95.1% of S&P 500 variance \u2014 the other 480 are noise",
  },

  /* ── 3. Mirror Index Builder ──────────────────────────────── */
  "mirror-builder": {
    id: "mirror-builder",
    title: "Mirror Index Builder",
    subtitle: "Cap-weighted and equal-weighted SP-20 construction",
    description:
      "Constructs a cap-weighted portfolio of the top-20 stocks, rebalanced " +
      "daily using price-proportional weights. NAV is normalized to 1.0 at " +
      "inception for direct comparison with the S&P 500.",
    thinking:
      "If 20 stocks explain the index, can we build a simpler version that " +
      "matches or beats it? The cap-weighted mirror uses yesterday's weights " +
      "for today's returns (avoiding look-ahead bias). Daily rebalancing is " +
      "expensive in practice but establishes the theoretical upper bound.",
    keyInsight:
      "The SP-20 Mirror achieved 19.2% CAGR vs 11.3% for the full S&P 500",
  },

  /* ── 4. Alpha Optimizer ───────────────────────────────────── */
  "alpha-optimizer": {
    id: "alpha-optimizer",
    title: "Alpha Optimizer",
    subtitle: "Walk-forward max-Sharpe portfolio optimization",
    description:
      "Runs the retained SP-N Alpha strategy: a walk-forward max-Sharpe " +
      "optimizer on the configured top-20 universe. It is exported only after " +
      "beating the Equal baseline on both CAGR and Sharpe.",
    thinking:
      "The mirror and equal portfolios are the clean benchmarks. The public " +
      "Alpha slot is reserved for the one optimizer that adds clear value in " +
      "walk-forward testing; experimental ML and hedged variants stay out of " +
      "the product surface until they earn their place.",
    keyInsight:
      "SP-N Alpha: 29.2% CAGR, Sharpe 1.17, Jensen alpha +13.9%",
  },

  /* ── 5. Performance Monitor ───────────────────────────────── */
  "performance-monitor": {
    id: "performance-monitor",
    title: "Performance Monitor",
    subtitle: "Comprehensive risk-adjusted metric computation",
    description:
      "Computes 15+ metrics including CAGR, Sharpe, Sortino, Maximum Drawdown, " +
      "Calmar, Beta, Alpha (Jensen's), Tracking Error, and Information Ratio. " +
      "All annualized using 252 trading days.",
    thinking:
      "A single metric tells one story. Sharpe captures risk-adjusted return, " +
      "but ignores the path (drawdowns matter for real portfolios). Sortino " +
      "penalizes only downside volatility. Tracking error shows how closely " +
      "we mirror the benchmark. Together, they paint the complete picture.",
    keyInsight:
      "SP-N Alpha leads the retained set: 29.2% CAGR, Sharpe 1.17, max drawdown -29.6%",
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
