"use client";

/* ================================================================
   StrategyPlaybook -- per-portfolio "how it works" cards
   For each of the four portfolios, shows three labeled rows:
     • How it works  — selection universe + weighting
     • Rebalance     — cadence, cost model, measured turnover
     • Track record  — CAGR / Sharpe / Jensen α / Max DD, net of costs
   Structural facts come from STRATEGY_MECHANICS (definitional);
   every performance number is read from the exported metrics/research
   so the copy can never drift from the charts.
   ================================================================ */

import React from "react";
import { motion } from "framer-motion";
import { CHART_COLORS } from "@/lib/constants";
import {
  STRATEGY_MECHANICS,
  STRATEGY_ORDER,
  type StrategyKey,
} from "@/lib/strategyMeta";
import { formatPercent, formatRatio, formatSigned } from "@/lib/formatters";
import type {
  AllPerformanceMetrics,
  PerformanceMetrics,
  ResearchHoldout,
} from "@/lib/types";

interface StrategyPlaybookProps {
  metrics: AllPerformanceMetrics;
  /** Supplies SP-N Alpha's out-of-sample turnover (not in its metrics JSON). */
  research?: ResearchHoldout;
}

function metricsFor(
  key: StrategyKey,
  m: AllPerformanceMetrics,
): PerformanceMetrics | undefined {
  switch (key) {
    case "sp500":
      return m.sp500;
    case "sp20Mirror":
      return m.sp20Mirror;
    case "sp20Equal":
      return m.sp20Equal;
    case "spnAlpha":
      return m.spnAlpha;
  }
}

/** Small labeled stat used in the track-record row. */
const Stat: React.FC<{ label: string; value: string; muted?: boolean }> = ({
  label,
  value,
  muted,
}) => (
  <div className="flex flex-col">
    <span className="text-[10px] uppercase tracking-wider text-text-muted">
      {label}
    </span>
    <span
      className={`font-mono text-sm tabular-nums ${
        muted ? "text-text-muted" : "text-text-primary"
      }`}
    >
      {value}
    </span>
  </div>
);

/** One "How it works / Rebalance" definition row. */
const DefRow: React.FC<{ label: string; children: React.ReactNode }> = ({
  label,
  children,
}) => (
  <div className="grid grid-cols-[92px_1fr] gap-3 py-1.5">
    <span className="pt-0.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
      {label}
    </span>
    <span className="text-xs leading-relaxed text-text-secondary">
      {children}
    </span>
  </div>
);

const StrategyCard: React.FC<{
  index: number;
  strategyKey: StrategyKey;
  metrics?: PerformanceMetrics;
  turnover?: number;
  turnoverNote?: string;
}> = ({ index, strategyKey, metrics, turnover, turnoverNote }) => {
  const mech = STRATEGY_MECHANICS[strategyKey];
  const color = CHART_COLORS[strategyKey as keyof typeof CHART_COLORS];
  const isBenchmark = mech.isBenchmark;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.45, ease: "easeOut", delay: index * 0.06 }}
      className="flex flex-col rounded-xl border border-[#1A1A24] bg-bg-secondary p-5"
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-2.5">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
          aria-hidden="true"
        />
        <h3 className="text-sm font-bold tracking-wide text-text-primary">
          {mech.label}
        </h3>
        {isBenchmark && (
          <span className="rounded-full border border-[#2A2A38] px-2 py-0.5 text-[9px] uppercase tracking-wider text-text-muted">
            Benchmark
          </span>
        )}
      </div>
      <p className="mb-3 text-xs italic leading-relaxed text-text-muted">
        {mech.tagline}
      </p>

      {/* How it works + Rebalance */}
      <div className="border-t border-[#1A1A24] pt-2">
        <DefRow label="Universe">{mech.universe}</DefRow>
        <DefRow label="Weighting">{mech.weighting}</DefRow>
        <DefRow label="Rebalance">{mech.rebalance}</DefRow>
        <DefRow label="Costs">
          {mech.cost}
          {turnover !== undefined && (
            <>
              {" · "}
              <span className="text-text-secondary">
                {formatRatio(turnover)}×/yr turnover
              </span>
              {turnoverNote && (
                <span className="text-text-muted"> {turnoverNote}</span>
              )}
            </>
          )}
        </DefRow>
      </div>

      {/* Track record */}
      {metrics && (
        <div className="mt-3 grid grid-cols-4 gap-3 border-t border-[#1A1A24] pt-3">
          <Stat label="CAGR" value={formatPercent(metrics.cagr, 1)} />
          <Stat label="Sharpe" value={formatRatio(metrics.sharpe)} />
          <Stat
            label="Jensen α"
            value={isBenchmark ? "—" : formatSigned(metrics.alpha, (v) => formatPercent(v, 1))}
            muted={isBenchmark}
          />
          <Stat label="Max DD" value={formatPercent(metrics.maxDrawdown, 1)} />
        </div>
      )}
    </motion.div>
  );
};

const StrategyPlaybook: React.FC<StrategyPlaybookProps> = ({
  metrics,
  research,
}) => {
  const alphaTurnover = research?.score?.annTurnover;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {STRATEGY_ORDER.map((key, i) => {
        const m = metricsFor(key, metrics);
        // Only strategies we trade carry a turnover figure. Mirror/Equal
        // report full-sample turnover; SP-N Alpha's isn't in its metrics
        // JSON, so we surface its out-of-sample (holdout-window) turnover.
        let turnover: number | undefined;
        let turnoverNote: string | undefined;
        if (key === "sp20Mirror" || key === "sp20Equal") {
          turnover = m?.annualizedTurnover;
        } else if (key === "spnAlpha") {
          turnover = alphaTurnover;
          turnoverNote = alphaTurnover !== undefined ? "(OOS)" : undefined;
        }

        // Skip a strategy only if it has neither mechanics metrics nor a card
        // reason to render (spnAlpha may be absent before the alpha backtest).
        if (key === "spnAlpha" && !m) return null;

        return (
          <StrategyCard
            key={key}
            index={i}
            strategyKey={key}
            metrics={m}
            turnover={turnover}
            turnoverNote={turnoverNote}
          />
        );
      })}
    </div>
  );
};

export default StrategyPlaybook;
