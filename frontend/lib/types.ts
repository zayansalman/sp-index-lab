/* ================================================================
   S&P Index Lab -- TypeScript Type Definitions
   All data shapes for JSON payloads, component props, and state.
   ================================================================ */

/* ──────────────────────────────────────────────────────────────
   Meta
   Source: /data/meta.json
   ────────────────────────────────────────────────────────────── */

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
  /** Pipeline version identifier */
  version?: string;
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
  /** The elbow point N where marginal gain drops below threshold */
  elbowN: number;
  /** R-squared at the elbow */
  elbowRSquared: number;
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
}

export type PerformanceNavData = PerformanceNavPoint[];

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
}

export interface AllPerformanceMetrics {
  sp500: PerformanceMetrics;
  sp20Mirror: PerformanceMetrics;
  sp20Equal: PerformanceMetrics;
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
   Machine / Animation State
   ────────────────────────────────────────────────────────────── */

export type MachineStage =
  | "idle"
  | "powering_up"
  | "data_pipeline"
  | "concentration"
  | "building"
  | "optimizing"
  | "monitoring"
  | "complete";

export interface MachineStageConfig {
  /** Stage identifier */
  id: MachineStage;
  /** Human-readable label */
  name: string;
  /** Duration in milliseconds before advancing to the next stage */
  duration: number;
  /** Short description shown during animation */
  description: string;
  /** 0-based index for ordering */
  order: number;
}

/* ──────────────────────────────────────────────────────────────
   Component Tooltip
   ────────────────────────────────────────────────────────────── */

export interface ComponentTooltip {
  /** Component identifier matching the machine diagram */
  id: string;
  /** Display title */
  title: string;
  /** One-line subtitle */
  subtitle: string;
  /** Multi-sentence technical description */
  description: string;
  /** Methodology rationale ("why we did it this way") */
  thinking: string;
  /** Single standout insight */
  keyInsight: string;
}

/* ──────────────────────────────────────────────────────────────
   Aggregated Lab Data (returned by useLabData hook)
   ────────────────────────────────────────────────────────────── */

export interface LabData {
  meta: MetaData;
  concentrationCurve: ConcentrationCurveData;
  varianceDecomposition: VarianceDecompositionPoint[];
  performanceNav: PerformanceNavData;
  performanceMetrics: AllPerformanceMetrics;
  holdings: HoldingsData;
  drawdown: DrawdownData;
  deviation: DeviationData;
}
