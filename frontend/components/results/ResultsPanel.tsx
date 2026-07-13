"use client";

/* ================================================================
   ResultsPanel -- Main results container
   Assembles all result components (metrics, charts, holdings,
   thinking) into a single scrollable panel that appears when
   the machine animation completes.
   ================================================================ */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useLabData from "@/hooks/useLabData";
import {
  formatPercent,
  formatRatio,
} from "@/lib/formatters";
import type { LabData, PerformanceMetrics } from "@/lib/types";
import GlowText from "@/components/ui/GlowText";
import MetricCard from "./MetricCard";
import ConcentrationChart from "./ConcentrationChart";
import PerformanceChart from "./PerformanceChart";
import DrawdownChart from "./DrawdownChart";
import HoldingsTable from "./HoldingsTable";
import ThinkingPanel from "./ThinkingPanel";

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
}

const METRIC_ROWS: MetricRowDef[] = [
  { label: "Total Return", key: "totalReturn", format: (v) => formatPercent(v, 1), higherIsBetter: true },
  { label: "CAGR", key: "cagr", format: (v) => formatPercent(v, 1), higherIsBetter: true },
  { label: "Annualised Volatility", key: "annualizedVolatility", format: (v) => formatPercent(v, 1), higherIsBetter: false },
  { label: "Sharpe Ratio", key: "sharpe", format: (v) => formatRatio(v), higherIsBetter: true },
  { label: "Sortino Ratio", key: "sortino", format: (v) => formatRatio(v), higherIsBetter: true },
  { label: "Max Drawdown", key: "maxDrawdown", format: (v) => formatPercent(v, 1), higherIsBetter: false },
  { label: "Calmar Ratio", key: "calmar", format: (v) => formatRatio(v), higherIsBetter: true },
  { label: "Beta", key: "beta", format: (v) => formatRatio(v), higherIsBetter: false },
  { label: "Alpha", key: "alpha", format: (v) => formatPercent(v, 1), higherIsBetter: true },
  { label: "Tracking Error", key: "trackingError", format: (v) => formatPercent(v, 2), higherIsBetter: false },
  { label: "Information Ratio", key: "informationRatio", format: (v) => formatRatio(v), higherIsBetter: true },
];

/* ──────────────────────────────────────────────────────────────
   Helper: determine the best value index in a row
   ────────────────────────────────────────────────────────────── */

function getBestIndex(
  values: number[],
  higherIsBetter: boolean,
): number {
  if (values.length === 0) return -1;

  if (!higherIsBetter) {
    const allValuesAreNonPositive = values.every((v) => v <= 0);
    let bestIdx = 0;
    for (let i = 1; i < values.length; i++) {
      const isBetter = allValuesAreNonPositive
        ? values[i] > values[bestIdx]
        : values[i] < values[bestIdx];
      if (isBetter) {
        bestIdx = i;
      }
    }
    return bestIdx;
  }

  // For higher is better
  let bestIdx = 0;
  for (let i = 1; i < values.length; i++) {
    if (values[i] > values[bestIdx]) {
      bestIdx = i;
    }
  }
  return bestIdx;
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
        "The public Alpha slot belongs to the single strategy that earns it in walk-forward testing: " +
        "max-Sharpe optimization over the point-in-time top-20 universe, with weights chosen using only " +
        `data available at each rebalance. Net of costs it reaches ${pct(m.spnAlpha?.cagr)} CAGR, ` +
        `${m.spnAlpha ? m.spnAlpha.sharpe.toFixed(2) : "—"} Sharpe, and ${pct(m.spnAlpha?.alpha, true)} ` +
        "Jensen alpha out-of-sample. Experimental ML and hedged variants stay out of the product surface " +
        "until they beat the retained strategy and the Equal baseline on the metrics that matter.",
    },
  ];
}

/* ──────────────────────────────────────────────────────────────
   Section Header
   ────────────────────────────────────────────────────────────── */

const SectionHeader: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <motion.h2
    initial={{ opacity: 0, y: 12 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-30px" }}
    transition={{ duration: 0.5, ease: "easeOut" }}
    className="mb-6 mt-12 text-lg font-bold tracking-wide text-text-primary"
  >
    {children}
  </motion.h2>
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
   Check Icon SVG
   ────────────────────────────────────────────────────────────── */

const CheckIcon: React.FC = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="text-accent-primary"
  >
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
    <path
      d="M8 12L11 15L16 9"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
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
                  ? "border-accent-primary bg-accent-primary/10 text-accent-primary"
                  : "border-[#1A1A24] bg-bg-primary text-text-muted hover:text-text-secondary"
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
  const panelRef = useRef<HTMLDivElement>(null);

  // Scroll to results when they become visible
  useEffect(() => {
    if (visible && panelRef.current) {
      const timer = setTimeout(() => {
        panelRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [visible]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 40 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="w-full"
        >
          {/* Loading state */}
          {isLoading && <LoadingSkeleton />}

          {/* Error state */}
          {error && (
            <div className="mx-auto max-w-5xl px-6 py-12">
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
                <p className="text-sm text-red-400">
                  Failed to load analysis data: {error}
                </p>
              </div>
            </div>
          )}

          {/* Results content */}
          {data && !isLoading && (
            <div className="mx-auto max-w-5xl px-6 pb-24 pt-8">
              {/* ── Header ──────────────────────────────────── */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="mb-8 flex items-center gap-3"
              >
                <CheckIcon />
                <GlowText
                  as="h1"
                  className="text-2xl font-bold text-accent-primary"
                >
                  Analysis Complete
                </GlowText>
              </motion.div>

              {/* ── Key Metrics ─────────────────────────────── */}
              <SectionHeader>Retained Result</SectionHeader>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard
                  label="R-squared"
                  value={data.concentrationCurve.elbowRSquared}
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

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="rounded-xl border border-[#1A1A24] bg-bg-secondary p-6"
              >
                <ConcentrationChart data={data.concentrationCurve.curve} />
              </motion.div>

              {/* ── Performance Chart ────────────────────────── */}
              <SectionHeader>Performance</SectionHeader>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="rounded-xl border border-[#1A1A24] bg-bg-secondary p-6"
              >
                <PerformanceChart bundle={data.performanceNavBundle} />
              </motion.div>

              {/* ── Performance Comparison Table ──────────────── */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="mt-6 overflow-x-auto rounded-xl border border-[#1A1A24] bg-bg-secondary p-6"
              >
                <h3 className="mb-4 text-sm font-semibold tracking-wide text-text-secondary">
                  Performance Comparison
                </h3>

                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-[#1A1A24]">
                      <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
                        Metric
                      </th>
                      <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                        S&P 500
                      </th>
                      <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                        SP-20 Mirror
                      </th>
                      <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                        SP-20 Equal
                      </th>
                      {data.performanceMetrics.spnAlpha && (
                        <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                          SP-N Alpha*
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {METRIC_ROWS.map((row, idx) => {
                      const sp500Val = data.performanceMetrics.sp500[row.key];
                      const mirrorVal = data.performanceMetrics.sp20Mirror[row.key];
                      const equalVal = data.performanceMetrics.sp20Equal[row.key];
                      const alphaVal = data.performanceMetrics.spnAlpha?.[row.key];

                      const values: number[] = [sp500Val, mirrorVal, equalVal];
                      if (alphaVal !== undefined) values.push(alphaVal);

                      const bestIdx = getBestIndex(values, row.higherIsBetter);

                      return (
                        <tr
                          key={row.key}
                          className={`border-b border-[#1A1A24] ${
                            idx % 2 === 0 ? "bg-bg-secondary" : "bg-bg-primary"
                          }`}
                        >
                          <td className="px-3 py-2.5 text-xs text-text-secondary">
                            {row.label}
                          </td>
                          {values.map((val, colIdx) => (
                            <td
                              key={colIdx}
                              className={`px-3 py-2.5 text-right font-mono text-xs tabular-nums ${
                                colIdx === bestIdx
                                  ? "font-bold text-accent-primary"
                                  : "text-text-primary"
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

                <p className="mt-3 text-[11px] leading-relaxed text-text-muted">
                  All strategy returns are net of transaction costs (7 bps per
                  one-way traded notional) on a point-in-time top-20 universe,
                  benchmarked against the S&amp;P 500 total-return index.
                  {data.performanceMetrics.spnAlpha?.windowStart && (
                    <>
                      {" "}
                      *SP-N Alpha is out-of-sample walk-forward from{" "}
                      {data.performanceMetrics.spnAlpha.windowStart} (
                      {data.performanceMetrics.spnAlpha.windowYears?.toFixed(1)}{" "}
                      years); baseline columns start at{" "}
                      {data.performanceMetrics.sp500.windowStart ??
                        data.meta.startDate}
                      , so CAGRs span different windows — relative metrics
                      (alpha, tracking error) are computed on overlapping dates.
                    </>
                  )}
                </p>
              </motion.div>

              {/* ── Drawdown Chart ───────────────────────────── */}
              <SectionHeader>Risk Analysis</SectionHeader>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="rounded-xl border border-[#1A1A24] bg-bg-secondary p-6"
              >
                <DrawdownChart data={data.drawdown} />
              </motion.div>

              {/* ── Holdings Table ───────────────────────────── */}
              <SectionHeader>Current Holdings</SectionHeader>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="rounded-xl border border-[#1A1A24] bg-bg-secondary p-4"
              >
                <HoldingsSelector holdings={data.holdings} />
              </motion.div>

              {/* ── Thinking Panel ──────────────────────────── */}
              <SectionHeader>The Thinking</SectionHeader>

              <ThinkingPanel sections={buildThinkingSections(data)} />

              {/* ── Footer ──────────────────────────────────── */}
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="mt-16 border-t border-[#1A1A24] pt-6 text-center"
              >
                <p className="text-xs text-text-muted">
                  Data from {data.meta.startDate} to {data.meta.endDate}{" "}
                  &middot; {data.meta.tradingDays} trading days &middot;{" "}
                  {data.meta.totalStocks} stocks analysed
                </p>
              </motion.div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default ResultsPanel;
