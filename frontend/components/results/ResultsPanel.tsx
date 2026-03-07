"use client";

/* ================================================================
   ResultsPanel -- Main results container
   Assembles all result components (metrics, charts, holdings,
   thinking) into a single scrollable panel that appears when
   the machine animation completes.
   ================================================================ */

import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useLabData from "@/hooks/useLabData";
import {
  formatPercent,
  formatRatio,
} from "@/lib/formatters";
import type { PerformanceMetrics } from "@/lib/types";
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

interface MetricRowDef {
  label: string;
  key: keyof PerformanceMetrics;
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

  // For "lower is better" metrics like drawdown (negative values),
  // we need to consider absolute magnitude
  if (!higherIsBetter) {
    // For metrics where lower is better, the "best" is the one
    // closest to zero (least negative for drawdowns) or simply smallest
    let bestIdx = 0;
    // For drawdowns (negative values), less negative is better
    // For volatility/tracking error (positive values), lower is better
    for (let i = 1; i < values.length; i++) {
      if (values[i] > values[bestIdx]) {
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
              <SectionHeader>The Proof</SectionHeader>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard
                  label="R-squared"
                  value={data.concentrationCurve.elbowRSquared}
                  format={(n) => formatPercent(n, 1)}
                  subtitle="20 stocks vs S&P 500"
                />
                <MetricCard
                  label="CAGR"
                  value={data.performanceMetrics.sp20Mirror.cagr}
                  format={(n) => formatPercent(n, 1)}
                  subtitle="SP-20 Mirror"
                  delta={
                    data.performanceMetrics.sp20Mirror.cagr -
                    data.performanceMetrics.sp500.cagr
                  }
                  deltaFormat={(d) =>
                    `${d > 0 ? "+" : ""}${(d * 100).toFixed(1)}% vs S&P 500`
                  }
                />
                <MetricCard
                  label="Excess Return"
                  value={data.performanceMetrics.sp20Mirror.alpha}
                  format={(n) => formatPercent(n, 1)}
                  subtitle="Jensen's Alpha"
                />
                <MetricCard
                  label="Tracking Error"
                  value={data.performanceMetrics.sp20Mirror.trackingError}
                  format={(n) => formatPercent(n, 2)}
                  subtitle="vs S&P 500"
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
                <PerformanceChart data={data.performanceNav} />
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
                    </tr>
                  </thead>
                  <tbody>
                    {METRIC_ROWS.map((row, idx) => {
                      const sp500Val = data.performanceMetrics.sp500[row.key];
                      const mirrorVal = data.performanceMetrics.sp20Mirror[row.key];
                      const equalVal = data.performanceMetrics.sp20Equal[row.key];
                      const values = [sp500Val, mirrorVal, equalVal];
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
                <HoldingsTable holdings={data.holdings.sp20Mirror} />
              </motion.div>

              {/* ── Thinking Panel ──────────────────────────── */}
              <SectionHeader>The Thinking</SectionHeader>

              <ThinkingPanel />

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
