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
    <div className="rounded-lg border border-[#2A2A35] bg-[#111118] px-3 py-2 shadow-xl">
      <p className="text-xs font-bold text-accent-primary">
        {data.n} {data.n === 1 ? "Stock" : "Stocks"}
      </p>
      <p className="mt-1 text-xs text-text-secondary">
        R&sup2;:{" "}
        <span className="font-medium text-text-primary">
          {(data.rSquared * 100).toFixed(1)}%
        </span>
      </p>
      <p className="text-xs text-text-secondary">
        Marginal R&sup2;:{" "}
        <span className="font-medium text-text-primary">
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
  // Transform data for recharts (rSquared as percentage for display)
  const chartData = data.map((point) => ({
    ...point,
    rSquaredPct: point.rSquared,
  }));

  return (
    <div className="w-full">
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-text-secondary">
        Concentration Curve: R&sup2; vs Number of Stocks
      </h3>

      <ResponsiveContainer width="100%" height={360}>
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <defs>
            <linearGradient id="gradientRSquared" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00D4AA" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#00D4AA" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1A1A24"
            vertical={false}
          />

          <XAxis
            dataKey="n"
            tick={{ fill: "#888899", fontSize: 11 }}
            axisLine={{ stroke: "#1A1A24" }}
            tickLine={{ stroke: "#1A1A24" }}
            label={{
              value: "# of Stocks",
              position: "insideBottom",
              offset: -5,
              fill: "#555566",
              fontSize: 11,
            }}
          />

          <YAxis
            domain={[0, 1]}
            tick={{ fill: "#888899", fontSize: 11 }}
            axisLine={{ stroke: "#1A1A24" }}
            tickLine={{ stroke: "#1A1A24" }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            label={{
              value: "R-squared",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              fill: "#555566",
              fontSize: 11,
            }}
          />

          {/* 95% R-squared reference line */}
          <ReferenceLine
            y={0.95}
            stroke="#888899"
            strokeDasharray="6 4"
            label={{
              value: "95%",
              position: "right",
              fill: "#888899",
              fontSize: 10,
            }}
          />

          {/* 20 stocks reference line */}
          <ReferenceLine
            x={20}
            stroke="#888899"
            strokeDasharray="6 4"
            label={{
              value: "N=20",
              position: "top",
              fill: "#888899",
              fontSize: 10,
            }}
          />

          <RechartsTooltip content={<CustomTooltip />} />

          <Area
            type="monotone"
            dataKey="rSquaredPct"
            stroke="#00D4AA"
            strokeWidth={2}
            fill="url(#gradientRSquared)"
            dot={false}
            activeDot={{
              r: 4,
              fill: "#00D4AA",
              stroke: "#111118",
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ConcentrationChart;
