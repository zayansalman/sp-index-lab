/* ================================================================
   S&P Index Lab -- Strategy Mechanics (structural definitions)
   ----------------------------------------------------------------
   These are the FIXED construction rules of each portfolio — they
   describe HOW a strategy is built and rebalanced, not its measured
   performance. Unlike CAGR/Sharpe/turnover (which drift with data and
   are read from JSON), these do not change on a data refresh, so they
   live here as typed constants rather than in the pipeline output.

   Source of truth for the numeric constants below is src/config.py:
     TRANSACTION_COST_BPS (5) + SLIPPAGE_BPS (2) = 7 bps / turnover
     MIRROR_REBALANCE_FREQ = "M" (month-end)
     REBALANCE_DRIFT_THRESHOLD = 0.02 (2% band)
     TRAIN_WINDOW_DAYS = 756 / TEST_WINDOW_DAYS = 21 (walk-forward)
     SPN_MIN_STOCKS = 10 / SPN_MAX_STOCKS = 30 (dynamic-N elbow)
   Keep these strings in sync if those config values change.
   ================================================================ */

/** Keys match the strategy identifiers used across the frontend. */
export type StrategyKey = "sp500" | "sp20Mirror" | "sp20Equal" | "spnAlpha";

export interface StrategyMechanics {
  /** Display name (matches CHART_LABELS). */
  label: string;
  /** One-line positioning: what this portfolio IS. */
  tagline: string;
  /** Selection universe rule. */
  universe: string;
  /** Weighting scheme. */
  weighting: string;
  /** Rebalance cadence + mechanism. */
  rebalance: string;
  /** Transaction-cost model applied on turnover ("—" for the raw index). */
  cost: string;
  /** True for the benchmark (no strategy construction of our own). */
  isBenchmark?: boolean;
}

/**
 * Ordered so the benchmark leads and strategies escalate in activeness:
 * passive mirror → equal-weight → self-adjusting alpha.
 */
export const STRATEGY_MECHANICS: Record<StrategyKey, StrategyMechanics> = {
  sp500: {
    label: "S&P 500 (TR)",
    tagline: "The market benchmark every strategy is measured against.",
    universe: "≈500 large-cap U.S. constituents",
    weighting: "Float-adjusted market-cap weighted",
    rebalance: "Index reconstitution (quarterly) — not traded by us",
    cost: "—",
    isBenchmark: true,
  },
  sp20Mirror: {
    label: "SP-20 Mirror",
    tagline: "The concentration thesis, made tradable and honest.",
    universe: "Point-in-time top-20 (membership + anchored cap-proxy)",
    weighting: "Cap-proxy weighted (mirrors the index's own tilt)",
    rebalance: "Monthly (month-end), 2% drift band",
    cost: "7 bps per one-way turnover",
  },
  sp20Equal: {
    label: "SP-20 Equal",
    tagline: "Same 20 names, stripped of the mega-cap tilt.",
    universe: "Point-in-time top-20 (membership + anchored cap-proxy)",
    weighting: "Equal-weighted (5% per name)",
    rebalance: "Monthly (month-end), 2% drift band",
    cost: "7 bps per one-way turnover",
  },
  spnAlpha: {
    label: "SP-N Alpha",
    tagline: "Lets the concentration 'elbow' decide how many stocks to hold.",
    universe: "Point-in-time cap-ranked pool (up to top-30)",
    weighting: "Equal-weighted across a dynamic N (10–30 via elbow)",
    rebalance: "Walk-forward monthly (756-day train → 21-day test)",
    cost: "7 bps per one-way turnover",
  },
};

/** Display order for playbook cards. */
export const STRATEGY_ORDER: StrategyKey[] = [
  "sp500",
  "sp20Mirror",
  "sp20Equal",
  "spnAlpha",
];
