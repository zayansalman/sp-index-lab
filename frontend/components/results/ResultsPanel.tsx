"use client";

/* ================================================================
   ResultsPanel -- Main results container
   Assembles all result components (metrics, charts, holdings,
   thinking) into a single scrollable panel that appears when
   the machine animation completes.
   ================================================================ */

import React, { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { AnimatePresence } from "framer-motion";
import useLabData from "@/hooks/useLabData";
import {
  formatPercent,
  formatRatio,
} from "@/lib/formatters";
import type {
  ConcentrationCurveData,
  FrontierPoint,
  LabData,
  PerformanceMetrics,
  ReplicationLadder,
} from "@/lib/types";
import MetricCard from "./MetricCard";
import HoldingsTable from "./HoldingsTable";
import ThinkingPanel from "./ThinkingPanel";
import StrategyPlaybook from "./StrategyPlaybook";
import HoldoutEvidence from "./HoldoutEvidence";
import { SignificancePanel } from "./SignificancePanel";
import { Explainer, GlossaryList } from "./PlainEnglish";
import { COMPARISON_GLOSSARY_KEYS } from "@/lib/glossary";
import { chartTheme, withAlpha } from "@/lib/chartTheme";

/* ──────────────────────────────────────────────────────────────
   Charts are code-split (next/dynamic) so the heavy Recharts bundle
   only loads once results are revealed, keeping the initial payload
   small. A shimmer placeholder holds the layout while each loads.
   ────────────────────────────────────────────────────────────── */

const ChartSkeleton: React.FC = () => (
  <div className="shimmer h-80 w-full rounded-lg" />
);

const ConcentrationChart = dynamic(() => import("./ConcentrationChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});
const PerformanceChart = dynamic(() => import("./PerformanceChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});
const DrawdownChart = dynamic(() => import("./DrawdownChart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface ResultsPanelProps {
  /** Whether the results panel should be visible */
  visible: boolean;
}

/* ──────────────────────────────────────────────────────────────
   Performance Metrics Table Row Definition
   ────────────────────────────────────────────────────────────── */

/** Keys of PerformanceMetrics whose values are plain numbers (table-safe). */
type NumericMetricKey = NonNullable<
  {
    [K in keyof PerformanceMetrics]-?: PerformanceMetrics[K] extends number
      ? K
      : never;
  }[keyof PerformanceMetrics]
>;

interface MetricRowDef {
  label: string;
  key: NumericMetricKey;
  format: (v: number) => string;
  /** Higher is better (true) or lower is better (false, e.g., drawdown) */
  higherIsBetter: boolean;
  /**
   * Metric defined *relative to* the benchmark, where the benchmark's own
   * value is definitional rather than earned (its tracking error is 0.00% and
   * its information ratio 0.00 by construction). Marking those as the "best"
   * value is meaningless, so the benchmark column is excluded from ranking.
   */
  relativeToBenchmark?: boolean;
  /**
   * Metric that scales with window length rather than skill. Total return
   * compounds, so a longer-running series can top the column purely by having
   * existed longer — never rank it while the columns span different windows.
   */
  windowSensitive?: boolean;
}

const METRIC_ROWS: MetricRowDef[] = [
  { label: "Total Return", key: "totalReturn", format: (v) => formatPercent(v, 1), higherIsBetter: true, windowSensitive: true },
  { label: "CAGR", key: "cagr", format: (v) => formatPercent(v, 1), higherIsBetter: true },
  { label: "Annualised Volatility", key: "annualizedVolatility", format: (v) => formatPercent(v, 1), higherIsBetter: false },
  { label: "Sharpe Ratio", key: "sharpe", format: (v) => formatRatio(v), higherIsBetter: true },
  { label: "Sortino Ratio", key: "sortino", format: (v) => formatRatio(v), higherIsBetter: true },
  { label: "Max Drawdown", key: "maxDrawdown", format: (v) => formatPercent(v, 1), higherIsBetter: false },
  { label: "Calmar Ratio", key: "calmar", format: (v) => formatRatio(v), higherIsBetter: true },
  { label: "Beta", key: "beta", format: (v) => formatRatio(v), higherIsBetter: false, relativeToBenchmark: true },
  { label: "Alpha", key: "alpha", format: (v) => formatPercent(v, 1), higherIsBetter: true, relativeToBenchmark: true },
  { label: "Tracking Error", key: "trackingError", format: (v) => formatPercent(v, 2), higherIsBetter: false, relativeToBenchmark: true },
  { label: "Information Ratio", key: "informationRatio", format: (v) => formatRatio(v), higherIsBetter: true, relativeToBenchmark: true },
];

/** Column order of the comparison table, paired with raw export keys so the
 *  significance lookup (which is keyed by export key) can find each column. */
const COMPARISON_COLUMNS = [
  { label: "S&P 500", exportKey: "sp500" },
  { label: "SP-20 Mirror", exportKey: "sp20_mirror" },
  { label: "SP-20 Equal", exportKey: "sp20_equal" },
  { label: "SP-N Alpha", exportKey: "spn_alpha" },
] as const;

/* ──────────────────────────────────────────────────────────────
   Helper: per-row heatmap intensity

   Replaces the previous "underline the winner" treatment. A binary
   crown is the strongest possible claim a table can make, and this
   one sits on a page whose own significance block reports that no
   pairwise difference clears the t > 3 hurdle — the ranking is real
   in the arithmetic and indistinguishable from luck.

   A continuous ramp is the honest form of the same information: it
   shows where a value sits in the row's spread without declaring a
   victor. Single hue, no red/green, so nothing carries a verdict.
   ────────────────────────────────────────────────────────────── */

/** Peak tint. Ink stays >15:1 on it, so shading never costs legibility. */
const HEATMAP_MAX_ALPHA = 0.16;

function rowIntensities(
  values: number[],
  higherIsBetter: boolean,
  excludeIndices: readonly number[] = [],
): number[] {
  const included = values
    .map((value, index) => ({ value, index }))
    .filter(({ index }) => !excludeIndices.includes(index));

  if (included.length < 2) return values.map(() => 0);

  // Drawdowns are all non-positive, where "better" means closer to zero —
  // the opposite of the usual lower-is-better ordering.
  const allNonPositive =
    !higherIsBetter && included.every(({ value }) => value <= 0);
  const betterIsLarger = higherIsBetter || allNonPositive;

  const nums = included.map((c) => c.value);
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min;

  return values.map((value, index) => {
    if (excludeIndices.includes(index)) return 0;
    if (span === 0) return 0;
    const position = (value - min) / span;
    return betterIsLarger ? position : 1 - position;
  });
}

/* ──────────────────────────────────────────────────────────────
   Helper: data-driven "The Thinking" sections
   Every number comes from the exported data so the prose can never
   contradict the charts after a data refresh.
   ────────────────────────────────────────────────────────────── */

function buildThinkingSections(
  data: LabData,
): { title: string; content: string }[] {
  const pct = (v: number | undefined, signed = false): string => {
    if (v === undefined || v === null) return "—";
    const s = (v * 100).toFixed(1);
    return signed && v >= 0 ? `+${s}%` : `${s}%`;
  };
  const h = data.meta.headline;
  const m = data.performanceMetrics;
  const n = data.alphaNSeries;

  return [
    {
      title: "Why 20 Stocks?",
      content:
        "The S&P 500 is marketed as diversification across 500 companies, but regressing the index's " +
        `daily returns on its 20 largest constituents explains ${pct(h?.rSquaredAt20)} of daily variance ` +
        "on average across rolling one-year windows. The selection is point-in-time: each window uses the " +
        "stocks that were actually the largest at that moment, not today's winners projected backwards. " +
        "Twenty is a reporting convention for that fixed-N read, not a discovered answer: the strategy's " +
        `own live stopping rule has held between ${n?.min ?? "—"} and ${n?.max ?? "—"} names ` +
        `(median ${n?.median ?? "—"}), sitting on its floor ${pct(n?.shareAtFloor)} of the time.`,
    },
    {
      title: "Why The Baselines Stay",
      content:
        "The SP-20 Mirror and SP-20 Equal portfolios are the two honest baselines, both net of transaction " +
        "costs and benchmarked against the S&P 500 total-return index " +
        `(${pct(m.sp500.cagr)} CAGR). Mirror holds the point-in-time top-20 at cap weights, rebalanced ` +
        `monthly, and reaches ${pct(m.sp20Mirror.cagr)} CAGR (${pct(m.sp20Mirror.alpha, true)} Jensen ` +
        `alpha). Equal gives each name an equal allocation and reaches ${pct(m.sp20Equal.cagr)} CAGR. ` +
        "They stay because they make the concentration thesis testable without hiding behind optimizer " +
        "complexity.",
    },
    {
      title: "Why One Alpha",
      content:
        "The public Alpha slot belongs to the self-adjusting strategy selected on the development window: " +
        "it reads the concentration 'elbow' each month and equal-weights that many point-in-time top names " +
        "(dynamic N, 10-30), using only data available at each rebalance. Net of costs it reaches " +
        `${pct(m.spnAlpha?.cagr)} CAGR, ${m.spnAlpha ? m.spnAlpha.sharpe.toFixed(2) : "—"} Sharpe, and ` +
        `${pct(m.spnAlpha?.alpha, true)} Jensen alpha out-of-sample. Experimental ML, mean-variance, and ` +
        "hedged variants stay out of the product surface until they beat this retained strategy and the " +
        "Equal baseline on the metrics that matter.",
    },
  ];
}

/* ──────────────────────────────────────────────────────────────
   Section Header
   ────────────────────────────────────────────────────────────── */

const SectionHeader: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <h2
    className="mb-6 mt-12 text-lg font-bold tracking-wide text-ink"
  >
    {children}
  </h2>
);

/* ──────────────────────────────────────────────────────────────
   Loading Skeleton
   ────────────────────────────────────────────────────────────── */

const LoadingSkeleton: React.FC = () => (
  <div className="mx-auto max-w-5xl space-y-6 px-6 py-12">
    <div className="shimmer h-8 w-64 rounded-lg" />
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="shimmer h-28 rounded-xl" />
      ))}
    </div>
    <div className="shimmer h-80 rounded-xl" />
    <div className="shimmer h-96 rounded-xl" />
  </div>
);

/* ──────────────────────────────────────────────────────────────
   HoldingsSelector -- tabs to switch between portfolio holdings
   ────────────────────────────────────────────────────────────── */

interface HoldingsSelectorProps {
  holdings: NonNullable<ReturnType<typeof useLabData>["data"]>["holdings"];
}

const STRATEGY_LABELS: Record<string, string> = {
  sp20Mirror: "SP-20 Mirror",
  sp20Equal: "SP-20 Equal",
  spn_alpha: "SP-N Alpha",
};

const HoldingsSelector: React.FC<HoldingsSelectorProps> = ({ holdings }) => {
  // Build a list of available portfolios with their holdings
  const options = useMemo(() => {
    const opts: { key: string; label: string; data: typeof holdings.sp20Mirror }[] = [
      { key: "sp20Mirror", label: STRATEGY_LABELS.sp20Mirror, data: holdings.sp20Mirror },
      { key: "sp20Equal", label: STRATEGY_LABELS.sp20Equal, data: holdings.sp20Equal },
    ];
    if (holdings.strategies) {
      const key = "spn_alpha";
      if (holdings.strategies[key]) {
        opts.push({
          key,
          label: STRATEGY_LABELS[key],
          data: holdings.strategies[key],
        });
      }
    }
    return opts;
  }, [holdings]);

  const [selectedKey, setSelectedKey] = useState(options[0]?.key ?? "sp20Mirror");

  const selected = options.find((o) => o.key === selectedKey) ?? options[0];

  return (
    <div className="space-y-4">
      {/* Portfolio tabs */}
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const isActive = opt.key === selectedKey;
          return (
            <button
              key={opt.key}
              type="button"
              onClick={() => setSelectedKey(opt.key)}
              className={`rounded-full border px-3 py-1 text-xs transition-all ${
                isActive
                  ? "border-accent bg-accent/10 text-accent"
                  : "bg-ground text-ink-muted hover:text-ink"
              }`}
              aria-pressed={isActive}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* Active holdings table */}
      {selected && <HoldingsTable holdings={selected.data} />}
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────
   ConcentrationFigures -- how the headline R-squared was measured,
   and the dispersion the mean hides.

   Every figure is read from the export. The mean alone reads as a
   constant; the range and the latest window are what stop it being
   quoted as "this is true right now".
   ────────────────────────────────────────────────────────────── */

const ConcentrationFigures: React.FC<{ curve: ConcentrationCurveData }> = ({
  curve,
}) => {
  const pct = (v: number | undefined) =>
    v === undefined ? "—" : formatPercent(v, 1);
  const at = (n: number) => curve.curve.find((p) => p.n === n)?.rSquared;
  const range = curve.rSquaredAt20Range;

  return (
    <>
      <p>
        <span className="font-semibold text-ink">How it is measured.</span>{" "}
        Rolling one-year windows, stepped about a month apart
        {curve.nWindows ? ` — ${curve.nWindows} of them` : ""}. Within each
        window the 20 largest companies <em>as of that date</em> are picked
        using only information available at the time, so the test never
        benefits from knowing which companies later became the giants.
      </p>
      <p className="mt-2">
        <span className="font-semibold text-ink">What comes out.</span> The
        average across those windows is{" "}
        <span className="num font-semibold text-ink">
          {pct(curve.rSquaredAt20)}
        </span>
        {range
          ? `, but individual windows run from ${pct(range.min)} to ${pct(range.max)}`
          : ""}
        {curve.rSquaredAt20Latest !== undefined
          ? `, and the most recent window is ${pct(curve.rSquaredAt20Latest)}`
          : ""}
        . The headline is an average over a decade, not a reading of today.
      </p>
      <p className="mt-2">
        <span className="font-semibold text-ink">Why twenty.</span> The number
        climbs smoothly as you add companies —{" "}
        <span className="num">{pct(at(5))}</span> at 5,{" "}
        <span className="num">{pct(at(10))}</span> at 10,{" "}
        <span className="num">{pct(at(20))}</span> at 20,{" "}
        <span className="num">{pct(at(50))}</span> at 50. There is no sharp
        kink at 20; it is a round number chosen for reporting, not a boundary
        discovered in the data.
      </p>
    </>
  );
};

/* ──────────────────────────────────────────────────────────────
   ReplicationLadderNote -- three readings of the same R-squared
   claim, in descending honesty of hindsight. `ladder` is absent on
   data bundles exported before the replication block existed (the
   committed JSON, until the daily cron regenerates it) — renders
   nothing rather than throwing.
   ────────────────────────────────────────────────────────────── */

const ReplicationLadderNote: React.FC<{ ladder?: ReplicationLadder }> = ({
  ladder,
}) => {
  if (!ladder) return null;

  const pct = (v?: number) =>
    v !== undefined ? `${(v * 100).toFixed(1)}%` : "—";

  return (
    <p className="mt-3 max-w-3xl text-xs leading-relaxed text-ink-secondary">
      Three readings of the same claim, in descending honesty of hindsight:
      with perfect-hindsight regression weights the top 20 explain{" "}
      <span className="font-mono">{pct(ladder.olsCeiling)}</span> of daily
      variance (a ceiling, not a portfolio); an investable equal-weight
      basket of the same names replicates{" "}
      <span className="font-mono">{pct(ladder.investableEqual)}</span> with
      one free parameter; cap-weighted,{" "}
      <span className="font-mono">{pct(ladder.investableCap)}</span>.
    </p>
  );
};

/* ──────────────────────────────────────────────────────────────
   TrackingFrontierNote -- one honest sentence on what a
   cardinality-constrained optimiser achieves at k=20, out of
   sample. `frontier` is absent on data bundles exported before the
   tracking-frontier block existed — renders nothing rather than
   throwing, and also degrades gracefully if k=20 isn't present.
   ────────────────────────────────────────────────────────────── */

const TrackingFrontierNote: React.FC<{ frontier?: FrontierPoint[] }> = ({
  frontier,
}) => {
  if (!frontier || frontier.length === 0) return null;

  const p20 = frontier.find((f) => f.k === 20);
  if (!p20) return null;

  const ks = frontier.map((f) => f.k);
  const min = Math.min(...ks);
  const max = Math.max(...ks);

  return (
    <p className="mt-2 max-w-3xl text-xs leading-relaxed text-ink-secondary">
      A cardinality-constrained optimiser (long-only least squares, top-k
      re-solve) tracks the index at{" "}
      <span className="font-mono">{(p20.teOos * 100).toFixed(2)}%</span>{" "}
      out-of-sample tracking error with 20 names — replication R&sup2;{" "}
      <span className="font-mono">
        {(p20.replicationR2Oos * 100).toFixed(1)}%
      </span>{" "}
      — and the full frontier runs k={min}…{max}.
    </p>
  );
};

/* ──────────────────────────────────────────────────────────────
   ResultsPanel Component
   ────────────────────────────────────────────────────────────── */

const ResultsPanel: React.FC<ResultsPanelProps> = ({ visible }) => {
  const { data, isLoading, error } = useLabData();

  // The panel used to scroll itself into view when the machine finished
  // its animation, and to fade up on mount. Both existed to choreograph
  // that reveal. With the machine gone the panel IS the page, so a
  // self-scroll just hides the heading the reader arrived at.

  return (
    <AnimatePresence>
      {visible && (
        <div className="w-full">
          {/* Loading state */}
          {isLoading && <LoadingSkeleton />}

          {/* Error state */}
          {error && (
            <div className="mx-auto max-w-5xl px-6 py-12">
              <div className="rounded-xl border border-fail/30 bg-fail-bg p-6">
                <p className="text-sm text-fail">
                  Failed to load analysis data: {error}
                </p>
              </div>
            </div>
          )}

          {/* Results content */}
          {data && !isLoading && (
            <div className="mx-auto max-w-5xl px-6 pb-24 pt-8">
              {/* ── Header ──────────────────────────────────── */}
              {/* Was "Analysis Complete" with a tick — the machine's
                  completion ceremony. A fund page states what it is. */}
              <div className="mb-8 border-b pb-6">
                <p className="label-micro">
                  {data.meta.startDate} &ndash; {data.meta.endDate} &middot;{" "}
                  net of costs &middot; benchmark {data.meta.benchmark}
                </p>
                <h1 className="mt-3 text-balance text-3xl font-normal tracking-tight text-ink">
                  Four portfolios on the concentration thesis
                </h1>
              </div>

              {/* ── Key Metrics ─────────────────────────────── */}
              <SectionHeader>Headline Metrics</SectionHeader>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard
                  label="R-squared"
                  value={data.concentrationCurve.rSquaredAt20}
                  format={(n) => formatPercent(n, 1)}
                  subtitle="20 stocks vs S&P 500"
                />
                <MetricCard
                  label="CAGR"
                  value={
                    data.performanceMetrics.spnAlpha?.cagr ??
                    data.performanceMetrics.sp20Equal.cagr
                  }
                  format={(n) => formatPercent(n, 1)}
                  subtitle="SP-N Alpha"
                  delta={
                    (data.performanceMetrics.spnAlpha?.cagr ??
                      data.performanceMetrics.sp20Equal.cagr) -
                    data.performanceMetrics.sp500.cagr
                  }
                  deltaFormat={(d) =>
                    `${d > 0 ? "+" : ""}${(d * 100).toFixed(1)}% vs S&P 500`
                  }
                />
                <MetricCard
                  label="Sharpe Ratio"
                  value={
                    data.performanceMetrics.spnAlpha?.sharpe ??
                    data.performanceMetrics.sp20Equal.sharpe
                  }
                  format={(n) => formatRatio(n)}
                  subtitle="SP-N Alpha"
                />
                <MetricCard
                  label="Alpha"
                  value={
                    data.performanceMetrics.spnAlpha?.alpha ??
                    data.performanceMetrics.sp20Equal.alpha
                  }
                  format={(n) => formatPercent(n, 1)}
                  subtitle="Jensen's Alpha"
                />
              </div>

              {/* ── Concentration Curve ──────────────────────── */}
              <SectionHeader>Concentration Analysis</SectionHeader>

              {/* R-squared is the one number the whole thesis rests on, and
                  it was previously shown with no explanation anywhere. */}
              <Explainer entry="rSquared">
                <ConcentrationFigures curve={data.concentrationCurve} />
              </Explainer>

              <div className="mt-4 rounded-xl border bg-surface p-6">
                <ConcentrationChart
                  data={data.concentrationCurve.curve}
                  solvedMedianN={data.alphaNSeries?.median}
                />
              </div>

              {/* R-squared ladder: three readings of the same claim, from
                  hindsight ceiling down to what an investable basket holds.
                  Absent until the export regenerates with the replication
                  block (Task 7); must render nothing, not crash, until then. */}
              <ReplicationLadderNote
                ladder={data.varianceDecomposition.replication?.ladder}
              />

              {/* Tracking-frontier note: one honest sentence on what a
                  cardinality-constrained optimiser achieves at k=20,
                  out-of-sample. Same absence rule as the ladder above. */}
              <TrackingFrontierNote
                frontier={data.varianceDecomposition.trackingFrontier?.frontier}
              />

              {/* ── Performance Chart ────────────────────────── */}
              <SectionHeader>Performance</SectionHeader>

              <div
                className="rounded-xl border bg-surface p-6"
              >
                <PerformanceChart bundle={data.performanceNavBundle} />
              </div>

              {/* ── Performance Comparison Table ──────────────── */}
              <div
                className="mt-6 overflow-x-auto rounded-xl border bg-surface p-6"
              >
                {(() => {
                  const matched = data.performanceMetrics.matchedWindow;
                  // Prefer the matched-window block: every series re-based to
                  // the first date they all share. Without it we fall back to
                  // each strategy's own window, which is NOT comparable — the
                  // rendering below suppresses window-sensitive ranking then.
                  const source = matched?.metrics ?? data.performanceMetrics;
                  const columns = COMPARISON_COLUMNS.filter(
                    (col) => col.exportKey !== "spn_alpha" || source.spnAlpha,
                  );
                  const metricsByColumn: PerformanceMetrics[] = columns.map(
                    (col) =>
                      col.exportKey === "sp500"
                        ? source.sp500
                        : col.exportKey === "sp20_mirror"
                          ? source.sp20Mirror
                          : col.exportKey === "sp20_equal"
                            ? source.sp20Equal
                            : source.spnAlpha!,
                  );
                  const benchmarkIdx = columns.findIndex(
                    (col) => col.exportKey === (matched?.benchmark ?? "sp500"),
                  );

                  return (
                    <>
                      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className="text-sm font-semibold tracking-wide text-ink-secondary">
                          Performance Comparison
                        </h3>
                        <span className="font-mono text-[11px] text-ink-muted">
                          {matched
                            ? `matched window ${matched.windowStart} → ${matched.windowEnd} (${matched.windowYears.toFixed(1)}y)`
                            : "each column spans its own window — not directly comparable"}
                        </span>
                      </div>

                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
                              Metric
                            </th>
                            {columns.map((col) => (
                              <th
                                key={col.exportKey}
                                className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-ink-muted"
                              >
                                {col.label}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {METRIC_ROWS.map((row) => {
                            const values = metricsByColumn.map((m) => m[row.key]);

                            // Two cases where shading would mislead: a relative
                            // metric (the benchmark's own tracking error is
                            // 0.00% by construction), and a window-sensitive
                            // metric on unmatched columns.
                            const excluded = row.relativeToBenchmark
                              ? [benchmarkIdx]
                              : [];
                            const rankable = !(row.windowSensitive && !matched);
                            const intensities = rowIntensities(
                              values,
                              row.higherIsBetter,
                              rankable ? excluded : values.map((_, i) => i),
                            );

                            return (
                              <tr key={row.key} className="border-b">
                                <td className="py-2.5 pr-3 text-xs text-ink-secondary">
                                  {row.label}
                                </td>
                                {values.map((val, colIdx) => (
                                  <td
                                    key={columns[colIdx].exportKey}
                                    className="px-3 py-2.5 text-right font-mono text-xs tabular-nums text-ink"
                                    style={
                                      intensities[colIdx] > 0
                                        ? {
                                            backgroundColor: withAlpha(
                                              chartTheme.accent,
                                              intensities[colIdx] * HEATMAP_MAX_ALPHA,
                                            ),
                                          }
                                        : undefined
                                    }
                                  >
                                    {row.format(val)}
                                  </td>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>

                      <p className="mt-3 text-[11px] leading-relaxed text-ink-muted">
                        All strategy returns are net of transaction costs (7 bps
                        per one-way traded notional) on a point-in-time universe,
                        benchmarked against the S&amp;P 500 total-return index.
                        The two baselines hold the top 20 by construction; SP-N
                        Alpha selects from the top 30 and its concentration-elbow
                        solver decides how many of those to hold at each
                        rebalance.{" "}
                        {matched ? (
                          <>
                            Every column is re-based to{" "}
                            {matched.windowStart}, the first date all four
                            series exist, so the comparison is like-for-like.
                          </>
                        ) : (
                          <>
                            SP-N Alpha is out-of-sample walk-forward from{" "}
                            {source.spnAlpha?.windowStart} (
                            {source.spnAlpha?.windowYears?.toFixed(1)} years)
                            while the baselines start at{" "}
                            {source.sp500.windowStart ?? data.meta.startDate},
                            so these columns span different windows. Total
                            return is left unshaded because a longer window
                            compounds more regardless of skill.
                          </>
                        )}{" "}
                        Shading shows where each value sits within its own row —
                        darker is the more favourable end. It ranks the
                        arithmetic, not the evidence: no difference between any
                        two of these strategies clears the significance bar this
                        project holds itself to.
                      </p>

                      <div className="mt-5">
                        <GlossaryList entries={COMPARISON_GLOSSARY_KEYS} />
                      </div>
                    </>
                  );
                })()}
              </div>

              {/* ── Is any of it real? ────────────────────────── */}
              {data.performanceMetrics.matchedWindow && (
                <SignificancePanel matched={data.performanceMetrics.matchedWindow} />
              )}

              {/* ── How Each Portfolio Works ──────────────────── */}
              <SectionHeader>How Each Portfolio Works</SectionHeader>

              <StrategyPlaybook
                metrics={data.performanceMetrics}
                research={data.meta.research}
              />

              {/* ── The Proof: out-of-sample holdout ──────────── */}
              {data.meta.research?.score && (
                <>
                  <SectionHeader>The Proof — Out-of-Sample Holdout</SectionHeader>
                  <HoldoutEvidence research={data.meta.research} />
                </>
              )}

              {/* ── Drawdown Chart ───────────────────────────── */}
              <SectionHeader>Risk Analysis</SectionHeader>

              <div
                className="rounded-xl border bg-surface p-6"
              >
                <DrawdownChart data={data.drawdown} />
              </div>

              {/* ── Holdings Table ───────────────────────────── */}
              <SectionHeader>Current Holdings</SectionHeader>

              <div
                className="rounded-xl border bg-surface p-4"
              >
                <HoldingsSelector holdings={data.holdings} />
              </div>

              {/* ── Thinking Panel ──────────────────────────── */}
              <SectionHeader>The Thinking</SectionHeader>

              <ThinkingPanel sections={buildThinkingSections(data)} />

              {/* ── Footer ──────────────────────────────────── */}
              <div
                className="mt-16 border-t pt-6 text-center"
              >
                <p className="text-xs text-ink-muted">
                  Data from {data.meta.startDate} to {data.meta.endDate}{" "}
                  &middot; {data.meta.tradingDays} trading days &middot;{" "}
                  {data.meta.totalStocks} stocks analysed
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </AnimatePresence>
  );
};

export default ResultsPanel;
