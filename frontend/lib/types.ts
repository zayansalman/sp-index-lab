/* ================================================================
   S&P Index Lab -- TypeScript Type Definitions
   All data shapes for JSON payloads, component props, and state.
   ================================================================ */

/* ──────────────────────────────────────────────────────────────
   Meta
   Source: /data/meta.json
   ────────────────────────────────────────────────────────────── */

/**
 * Headline stats exported by the pipeline — the single source of truth
 * for every number displayed outside the charts. Components must read
 * these instead of hardcoding values that drift when data refreshes.
 */
export interface HeadlineStats {
  /** Mean R² of benchmark on PIT top-20 across rolling 1y windows */
  rSquaredAt20: number;
  /** S&P 500 (total return) CAGR over the display window */
  sp500Cagr: number;
  /** SP-20 Mirror CAGR, net of costs */
  mirrorCagr: number;
  /** SP-20 Mirror Jensen alpha, net of costs */
  mirrorAlpha: number;
  /** SP-20 Equal CAGR, net of costs */
  equalCagr: number;
  /** SP-20 Equal Jensen alpha, net of costs */
  equalAlpha: number;
  /** SP-N Alpha CAGR, net of costs (out-of-sample) */
  alphaCagr?: number;
  /** SP-N Alpha Sharpe ratio, net of costs */
  alphaSharpe?: number;
  /** SP-N Alpha Jensen alpha, net of costs */
  alphaJensen?: number;
  /** SP-N Alpha max drawdown */
  alphaMaxDrawdown?: number;
  /** True when every strategy CAGR/alpha is reported net of transaction costs */
  netOfCosts?: boolean;
}

export interface MetaData {
  /** ISO date of the last pipeline run */
  lastUpdated: string;
  /** Total trading days in the dataset */
  tradingDays: number;
  /** Start date of the backtest window */
  startDate: string;
  /** End date of the backtest window */
  endDate: string;
  /** Number of stocks analysed */
  totalStocks: number;
  /** Top-N stocks selected for the mirror index */
  topN: number;
  /** S&P 500 benchmark ticker */
  benchmark: string;
  /** Universe construction method (e.g. "pit_membership_cap_proxy") */
  universeMethod?: string;
  /** Headline stats (data-driven numbers for the UI) */
  headline?: HeadlineStats;
  /** Honest dev/holdout research provenance (the pre-registered proof) */
  research?: ResearchHoldout;
  /** Pipeline version identifier */
  version?: string;
}

/* ──────────────────────────────────────────────────────────────
   Research provenance — the pre-registered honest-evaluation block
   Source: /data/meta.json → research
   Records the dev/holdout split, multiple-testing discount, and the
   one-shot holdout outcome so the site can prove out-of-sample edge
   WITHOUT crowning a single winner.
   ────────────────────────────────────────────────────────────── */

/** The three pre-registered pass/fail checks (committed before selection). */
export interface HoldoutChecks {
  /** Beat S&P 500 TR on both CAGR and Sharpe, net of costs */
  beatSp500CagrAndSharpe: boolean;
  /** Beat SP-20 Equal on both CAGR and Sharpe, net of costs */
  beatEqualCagrAndSharpe: boolean;
  /** Max drawdown within 1.2× the index's max drawdown */
  maxDrawdownWithinMultiple: boolean;
}

/** The frozen strategy's out-of-sample scorecard on the locked holdout. */
export interface HoldoutScore {
  /** First out-of-sample date (ISO) */
  windowStart: string;
  /** Last out-of-sample date (ISO) */
  windowEnd: string;
  /** Number of out-of-sample trading days */
  nDays: number;
  /** Net CAGR over the holdout */
  cagr: number;
  /** Annualised volatility */
  annVol: number;
  /** Sharpe ratio */
  sharpe: number;
  /** Sortino ratio */
  sortino: number;
  /** Max drawdown (negative) */
  maxDrawdown: number;
  /** Annualised turnover (multiple of NAV) */
  annTurnover: number;
  /** Realised cost drag in basis points */
  costDragBps: number;
  /** Excess CAGR vs each benchmark (decimal, e.g. 0.105 = +10.5pp) */
  excessCagr: { sp500: number; sp20Equal: number };
  /** t-stat of the excess return vs each benchmark (significance signal) */
  excessTStat: { sp500: number; sp20Equal: number };
  /** Whether it beat each benchmark on the pre-registered criteria */
  beats: { sp500: boolean; sp20Equal: boolean };
}

export interface ResearchHoldout {
  /** Frozen dev-window winner spec (engine × N-policy × overlay) */
  devWinnerSpec?: { engine: string; nPolicy: string; overlay: string };
  /** Number of trials that fed selection (multiple-testing count) */
  devTrialCount?: number;
  /** Dev/holdout split boundary (ISO); holdout is everything after */
  devEnd?: string;
  /** Locked holdout window [start, end] (ISO) */
  window?: [string, string];
  /** Whether the frozen spec cleared EVERY pre-registered criterion */
  passed?: boolean;
  /** Per-criterion pass/fail booleans */
  checks?: HoldoutChecks;
  /** Deflated Sharpe on the dev window given the trial count */
  deflatedSharpe?: number;
  /** Out-of-sample scorecard */
  score?: HoldoutScore;
  /** The index's own max drawdown over the holdout (drawdown-cap basis) */
  indexMaxDrawdown?: number;
}

/* ──────────────────────────────────────────────────────────────
   Concentration Curve
   Source: /data/concentration_curve.json
   ────────────────────────────────────────────────────────────── */

export interface ConcentrationPoint {
  /** Number of stocks included (1..N) */
  n: number;
  /** R-squared value at this N */
  rSquared: number;
  /** Marginal R-squared gain from adding the Nth stock */
  marginalRSquared: number;
  /** Tickers included at this step */
  tickers: string[];
}

export interface ConcentrationCurveData {
  /** Ordered array of concentration measurements */
  curve: ConcentrationPoint[];
  /**
   * Mean R-squared at a FIXED N=20, across rolling one-year windows.
   *
   * Named for what it measures. This is not "R-squared at the elbow": the
   * strategy's elbow solver (`make_elbow_n`) stops at the first N whose
   * marginal R-squared falls below 0.5%, and it has selected a median of 11
   * names — never 20 — across 126 monthly rebalances. The two numbers answer
   * different questions and must not be conflated.
   */
  rSquaredAt20: number;
}

/* ──────────────────────────────────────────────────────────────
   Variance Decomposition
   Source: /data/variance_decomposition.json
   ────────────────────────────────────────────────────────────── */

export interface VarianceDecompositionPoint {
  /** Stock ticker (or group label) */
  ticker: string;
  /** Company display name */
  name: string;
  /** Variance explained (R-squared at this grouping) */
  varianceExplained: number;
  /** Cumulative variance explained when ranked */
  cumulativeVariance: number;
  /** Absolute correlation with S&P 500 */
  correlation: number;
  /** Beta vs S&P 500 */
  beta: number;
  /** Sector classification */
  sector: string;
}

/* ──────────────────────────────────────────────────────────────
   Performance -- NAV Time Series
   Source: /data/performance_nav.json
   ────────────────────────────────────────────────────────────── */

export interface PerformanceNavPoint {
  /** ISO date string (YYYY-MM-DD) */
  date: string;
  /** S&P 500 normalised NAV */
  sp500: number;
  /** SP-20 Mirror (cap-weighted) normalised NAV */
  sp20Mirror: number;
  /** SP-20 Equal-weighted normalised NAV */
  sp20Equal: number;
  /** SP-N Alpha (self-adjusting concentration-elbow, equal-weight) normalised NAV */
  spnAlpha?: number;
}

export type PerformanceNavData = PerformanceNavPoint[];

/**
 * NAV series at both granularities for interactive time-range switching.
 * `weekly` covers the full backtest; `daily` is the trailing ~1 year at
 * daily resolution.
 */
export interface PerformanceNavBundle {
  weekly: PerformanceNavData;
  daily: PerformanceNavData;
}

/* ──────────────────────────────────────────────────────────────
   Performance -- Metrics
   Source: /data/performance_metrics.json
   ────────────────────────────────────────────────────────────── */

export interface PerformanceMetrics {
  /** Total cumulative return */
  totalReturn: number;
  /** Compound annual growth rate */
  cagr: number;
  /** Annualised volatility */
  annualizedVolatility: number;
  /** Sharpe ratio (annualised, rf = 0) */
  sharpe: number;
  /** Sortino ratio */
  sortino: number;
  /** Maximum drawdown (negative) */
  maxDrawdown: number;
  /** Calmar ratio (CAGR / |maxDrawdown|) */
  calmar: number;
  /** Beta vs S&P 500 */
  beta: number;
  /** Jensen's alpha (annualised) */
  alpha: number;
  /** Tracking error vs S&P 500 */
  trackingError: number;
  /** Information ratio */
  informationRatio: number;
  /** Best single-day return */
  bestDay: number;
  /** Worst single-day return */
  worstDay: number;
  /** Win rate (% of positive-return days) */
  winRate: number;
  /** Average daily return */
  avgDailyReturn: number;
  /** First date of this strategy's window (ISO) */
  windowStart?: string;
  /** Window length in years (walk-forward strategies are shorter) */
  windowYears?: number;
  /** Gross-of-costs CAGR (net is canonical; gross shows the cost drag) */
  grossCagr?: number;
  /** Gross-of-costs Sharpe ratio */
  grossSharpe?: number;
  /** Annualised turnover (multiple of NAV traded per year) */
  annualizedTurnover?: number;
}

export interface StrategyMetricSet {
  sp500: PerformanceMetrics;
  sp20Mirror: PerformanceMetrics;
  sp20Equal: PerformanceMetrics;
  spnAlpha?: PerformanceMetrics;
}

/** Significance of one strategy's active return against a reference series. */
export interface ActiveReturnStats {
  /** Annualised mean active return vs the reference */
  annualisedActiveReturn: number;
  /** Annualised standard deviation of the active return */
  trackingError: number;
  /** Information ratio (active return / tracking error) */
  informationRatio: number;
  /** t-statistic of the mean daily active return */
  tStat: number;
  /** Whether |t| clears the multiple-testing hurdle (Harvey-Liu-Zhu, t > 3) */
  significant: boolean;
  /** Years of data this IR would need to reach the hurdle; null if IR <= 0 */
  yearsForHurdle: number | null;
  /** Overlapping observations behind the estimate */
  nDays: number;
}

/**
 * Every strategy measured on the window they all share.
 *
 * The top-level metrics each span that strategy's own history (baselines from
 * 2014, SP-N Alpha from 2016 once its first walk-forward window closes), so
 * reading them as columns of one table is not apples-to-apples. This block is
 * the honest comparison, plus the pairwise t-stats needed to say whether any
 * gap is distinguishable from noise.
 */
export interface MatchedWindowComparison {
  windowStart: string;
  windowEnd: string;
  windowYears: number;
  /** Series key used as the regression benchmark (e.g. "sp500") */
  benchmark: string;
  /** |t| required to call a difference real */
  tHurdle: number;
  /** True if ANY pairwise comparison clears the hurdle */
  anySignificant: boolean;
  metrics: StrategyMetricSet;
  /** significance[strategyKey][referenceKey], keyed by raw export keys */
  significance: Record<string, Record<string, ActiveReturnStats>>;
}

export interface AllPerformanceMetrics extends StrategyMetricSet {
  /** Present once the export has regenerated; absent on older data bundles. */
  matchedWindow?: MatchedWindowComparison;
}

/* ──────────────────────────────────────────────────────────────
   Holdings
   Source: /data/holdings.json
   ────────────────────────────────────────────────────────────── */

export interface Holding {
  /** Stock ticker */
  ticker: string;
  /** Company name */
  name: string;
  /** Portfolio weight (0-1) */
  weight: number;
  /** GICS sector */
  sector: string;
  /** Contribution to total return over the period (optional) */
  returnContribution?: number;
  /** Rank by weight (1 = largest) */
  rank?: number;
}

export interface HoldingsData {
  /** Cap-weighted mirror holdings */
  sp20Mirror: Holding[];
  /** Equal-weighted holdings */
  sp20Equal: Holding[];
  /** Strategy-specific holdings keyed by strategy identifier */
  strategies?: Record<string, Holding[]>;
}

/* ──────────────────────────────────────────────────────────────
   Drawdown
   Source: /data/drawdowns.json
   ────────────────────────────────────────────────────────────── */

export interface DrawdownPoint {
  /** ISO date string */
  date: string;
  /** S&P 500 drawdown from peak (negative) */
  sp500: number;
  /** SP-20 Mirror drawdown from peak */
  sp20Mirror: number;
  /** SP-20 Equal drawdown from peak (optional) */
  sp20Equal?: number;
  /** SP-N Alpha (canonical) drawdown from peak */
  spnAlpha?: number;
}

export type DrawdownData = DrawdownPoint[];

/* ──────────────────────────────────────────────────────────────
   Return Deviation Histogram
   Source: /data/daily_deviations.json
   ────────────────────────────────────────────────────────────── */

export interface DeviationBin {
  /** Bin centre (e.g., -0.005 for -0.5%) */
  bin: number;
  /** Frequency / count of observations in this bin */
  count: number;
  /** Label for display */
  label: string;
}

export interface DeviationData {
  /** SP-20 Mirror minus S&P 500 daily return deviation */
  sp20Mirror: DeviationBin[];
  /** SP-20 Equal minus S&P 500 daily return deviation */
  sp20Equal: DeviationBin[];
  /** Mean daily deviation for mirror */
  meanDeviationMirror: number;
  /** Mean daily deviation for equal */
  meanDeviationEqual: number;
  /** Standard deviation of daily deviation for mirror */
  stdDeviationMirror: number;
  /** Standard deviation of daily deviation for equal */
  stdDeviationEqual: number;
}

/* ──────────────────────────────────────────────────────────────
   Aggregated Lab Data (returned by useLabData hook)
   ────────────────────────────────────────────────────────────── */

export interface LabData {
  meta: MetaData;
  concentrationCurve: ConcentrationCurveData;
  varianceDecomposition: VarianceDecompositionPoint[];
  /** Backward-compat weekly series (default chart data) */
  performanceNav: PerformanceNavData;
  /** Both granularities for time-range switching */
  performanceNavBundle: PerformanceNavBundle;
  performanceMetrics: AllPerformanceMetrics;
  holdings: HoldingsData;
  drawdown: DrawdownData;
  deviation: DeviationData;
}
