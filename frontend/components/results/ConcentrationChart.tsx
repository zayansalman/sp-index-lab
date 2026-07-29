"use client";

/* ================================================================
   ConcentrationChart -- R-squared vs Number of Stocks
   Recharts AreaChart showing the concentration curve with
   reference lines at 95% R-squared and 20 stocks.
   ================================================================ */

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { ConcentrationPoint } from "@/lib/types";
import { chartTheme } from "@/lib/chartTheme";

/** Single-series chart: the accent carries the line, not a series colour. */
const ACCENT = chartTheme.accent;

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface ConcentrationChartProps {
  data: ConcentrationPoint[];
}

/* ──────────────────────────────────────────────────────────────
   Custom Tooltip
   ────────────────────────────────────────────────────────────── */

interface TooltipPayloadItem {
  value: number;
  payload: {
    n: number;
    rSquared: number;
    marginalRSquared: number;
  };
}

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: TooltipPayloadItem[];
}> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload;

  return (
    <div className="rounded-lg border border-border-strong bg-ground px-3 py-2 shadow-xl">
      <p className="text-xs font-bold text-accent">
        {data.n} {data.n === 1 ? "Stock" : "Stocks"}
      </p>
      <p className="mt-1 text-xs text-ink-secondary">
        R&sup2;:{" "}
        <span className="font-medium text-ink">
          {(data.rSquared * 100).toFixed(1)}%
        </span>
      </p>
      <p className="text-xs text-ink-secondary">
        Marginal R&sup2;:{" "}
        <span className="font-medium text-ink">
          {(data.marginalRSquared * 100).toFixed(2)}%
        </span>
      </p>
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const ConcentrationChart: React.FC<ConcentrationChartProps> = ({ data }) => {
  const rSquaredAtTwenty = data.find((p) => p.n === 20)?.rSquared;
  // Transform data for recharts (rSquared as percentage for display)
  const chartData = data.map((point) => ({
    ...point,
    rSquaredPct: point.rSquared,
  }));

  return (
    <div className="w-full">
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-ink-secondary">
        Concentration Curve: R&sup2; vs Number of Stocks
      </h3>

      <ResponsiveContainer width="100%" height={360}>
        {/* Right margin holds the derived R-squared label (e.g. "95.2%"),
            which is wider than the "95%" literal it replaced. */}
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 56, left: 10, bottom: 10 }}
        >
          <defs>
            <linearGradient id="gradientRSquared" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={ACCENT} stopOpacity={0.3} />
              <stop offset="100%" stopColor={ACCENT} stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chartTheme.grid.stroke}
            vertical={false}
          />

          <XAxis
            dataKey="n"
            tick={chartTheme.axis.tick}
            axisLine={{ stroke: chartTheme.axis.stroke }}
            tickLine={{ stroke: chartTheme.axis.tickStroke }}
            label={{
              value: "# of Stocks",
              position: "insideBottom",
              offset: -5,
              fill: chartTheme.axis.tick.fill,
              fontSize: 11,
            }}
          />

          <YAxis
            domain={[0, 1]}
            tick={chartTheme.axis.tick}
            axisLine={{ stroke: chartTheme.axis.stroke }}
            tickLine={{ stroke: chartTheme.axis.tickStroke }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            label={{
              value: "R-squared",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              fill: chartTheme.axis.tick.fill,
              fontSize: 11,
            }}
          />

          {/* 95% R-squared reference line */}
          {rSquaredAtTwenty !== undefined && (
            <ReferenceLine
              y={rSquaredAtTwenty}
              stroke={chartTheme.referenceLine.stroke}
              strokeDasharray="6 4"
              label={{
                value: `${(rSquaredAtTwenty * 100).toFixed(1)}%`,
                position: "right",
                fill: chartTheme.axis.tick.fill,
                fontSize: 10,
              }}
            />
          )}

          {/* 20 stocks reference line */}
          <ReferenceLine
            x={20}
            stroke={chartTheme.referenceLine.stroke}
            strokeDasharray="6 4"
            label={{
              value: "N=20 · reporting convention",
              position: "top",
              fill: chartTheme.axis.tick.fill,
              fontSize: 10,
            }}
          />

          <RechartsTooltip content={<CustomTooltip />} />

          <Area
            type="monotone"
            dataKey="rSquaredPct"
            stroke={ACCENT}
            strokeWidth={2}
            fill="url(#gradientRSquared)"
            dot={false}
            activeDot={{
              r: 4,
              fill: ACCENT,
              stroke: chartTheme.ground,
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ConcentrationChart;
