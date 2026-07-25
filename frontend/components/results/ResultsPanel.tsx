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
import type { LabData, PerformanceMetrics } from "@/lib/types";
import MetricCard from "./MetricCard";
import HoldingsTable from "./HoldingsTable";
import ThinkingPanel from "./ThinkingPanel";
import StrategyPlaybook from "./StrategyPlaybook";
import HoldoutEvidence from "./HoldoutEvidence";
import { SignificancePanel } from "./SignificancePanel";

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
   Helper: determine the best value index in a row
   ────────────────────────────────────────────────────────────── */

function getBestIndex(
  values: number[],
  higherIsBetter: boolean,
  excludeIndices: readonly number[] = [],
): number {
  const candidates = values
    .map((value, index) => ({ value, index }))
    .filter(({ index }) => !excludeIndices.includes(index));

  if (candidates.length === 0) return -1;

  // Drawdowns are all non-positive, where "best" means closest to zero, i.e.
  // the largest value — the opposite of the usual lower-is-better ordering.
  const allValuesAreNonPositive =
    !higherIsBetter && candidates.every(({ value }) => value <= 0);

  let best = candidates[0];
  for (const candidate of candidates.slice(1)) {
    const isBetter = higherIsBetter
      ? candidate.value > best.value
      : allValuesAreNonPositive
        ? candidate.value > best.value
        : candidate.value < best.value;
    if (isBetter) best = candidate;
  }
  return best.index;
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

  return [
    {
      title: "Why 20 Stocks?",
      content:
        "The S&P 500 is marketed as diversification across 500 companies, but regressing the index's " +
        `daily returns on its 20 largest constituents explains ${pct(h?.rSquaredAt20)} of daily variance ` +
        "on average across rolling one-year windows. The selection is point-in-time: each window uses the " +
        "stocks that were actually the largest at that moment, not today's winners projected backwards. " +
        "The concentration curve shows a clear 'elbow' around 18-20 stocks, where each additional stock " +
        "stops adding meaningful explanatory power.",
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

              <div
                className="rounded-xl border bg-surface p-6"
              >
                <ConcentrationChart data={data.concentrationCurve.curve} />
              </div>

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
                          {METRIC_ROWS.map((row, idx) => {
                            const values = metricsByColumn.map((m) => m[row.key]);

                            // Two cases where crowning a "winner" would mislead:
                            // a relative metric (the benchmark's own tracking
                            // error is 0.00% by construction), and a
                            // window-sensitive metric on unmatched columns.
                            const excluded = row.relativeToBenchmark
                              ? [benchmarkIdx]
                              : [];
                            const rankable = !(row.windowSensitive && !matched);
                            const bestIdx = rankable
                              ? getBestIndex(values, row.higherIsBetter, excluded)
                              : -1;

                            return (
                              <tr
                                key={row.key}
                                className={`border-b ${
                                  idx % 2 === 0 ? "bg-surface" : "bg-ground"
                                }`}
                              >
                                <td className="px-3 py-2.5 text-xs text-ink-secondary">
                                  {row.label}
                                </td>
                                {values.map((val, colIdx) => (
                                  <td
                                    key={columns[colIdx].exportKey}
                                    className={`px-3 py-2.5 text-right font-mono text-xs tabular-nums ${
                                      colIdx === bestIdx
                                        ? "font-semibold text-ink underline decoration-text-muted decoration-dotted underline-offset-4"
                                        : "text-ink"
                                    }`}
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
                            Underlining marks the leading value; it is not a
                            claim that the lead is real — see below.
                          </>
                        ) : (
                          <>
                            SP-N Alpha is out-of-sample walk-forward from{" "}
                            {source.spnAlpha?.windowStart} (
                            {source.spnAlpha?.windowYears?.toFixed(1)} years)
                            while the baselines start at{" "}
                            {source.sp500.windowStart ?? data.meta.startDate},
                            so these columns span different windows. Total
                            return is left unranked because a longer window
                            compounds more regardless of skill.
                          </>
                        )}
                      </p>
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
