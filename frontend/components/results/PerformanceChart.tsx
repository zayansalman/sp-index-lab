"use client";

/* ================================================================
   PerformanceChart -- Growth of $1 comparison
   Recharts LineChart showing S&P 500, SP-20 Mirror, and SP-20
   Equal NAV time series with dark theme styling.
   ================================================================ */

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceNavPoint } from "@/lib/types";
import { CHART_COLORS, CHART_LABELS } from "@/lib/constants";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface PerformanceChartProps {
  data: PerformanceNavPoint[];
}

/* ──────────────────────────────────────────────────────────────
   Custom Tooltip
   ────────────────────────────────────────────────────────────── */

interface TooltipPayloadItem {
  dataKey: string;
  value: number;
  color: string;
  name: string;
}

const CustomTooltip: React.FC<{
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-[#2A2A35] bg-[#111118] px-3 py-2 shadow-xl">
      <p className="mb-1.5 text-xs font-medium text-text-muted">{label}</p>
      {payload.map((entry) => (
        <p
          key={entry.dataKey}
          className="flex items-center gap-2 text-xs text-text-secondary"
        >
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span>{entry.name}:</span>
          <span className="font-medium text-text-primary">
            ${entry.value.toFixed(2)}
          </span>
        </p>
      ))}
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────
   Date tick formatter -- show year labels
   ────────────────────────────────────────────────────────────── */

function formatDateTick(dateStr: string): string {
  if (!dateStr) return "";
  const year = dateStr.substring(0, 4);
  return year;
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const PerformanceChart: React.FC<PerformanceChartProps> = ({ data }) => {
  // Thin out data for performance: show every Nth point
  const thinned =
    data.length > 500
      ? data.filter((_, i) => i % Math.ceil(data.length / 500) === 0 || i === data.length - 1)
      : data;

  return (
    <div className="w-full">
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-text-secondary">
        Growth of $1: S&P 500 vs S&P-20 Indices
      </h3>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={thinned}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1A1A24"
            vertical={false}
          />

          <XAxis
            dataKey="date"
            tick={{ fill: "#888899", fontSize: 11 }}
            axisLine={{ stroke: "#1A1A24" }}
            tickLine={{ stroke: "#1A1A24" }}
            tickFormatter={formatDateTick}
            interval="preserveStartEnd"
            minTickGap={60}
          />

          <YAxis
            tick={{ fill: "#888899", fontSize: 11 }}
            axisLine={{ stroke: "#1A1A24" }}
            tickLine={{ stroke: "#1A1A24" }}
            tickFormatter={(v: number) => `$${v.toFixed(2)}`}
          />

          <RechartsTooltip content={<CustomTooltip />} />

          <Legend
            verticalAlign="bottom"
            height={36}
            wrapperStyle={{ paddingTop: "16px" }}
            formatter={(value: string) => (
              <span className="text-xs text-text-secondary">{value}</span>
            )}
          />

          <Line
            type="monotone"
            dataKey="sp500"
            name={CHART_LABELS.sp500}
            stroke={CHART_COLORS.sp500}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: CHART_COLORS.sp500 }}
          />

          <Line
            type="monotone"
            dataKey="sp20Mirror"
            name={CHART_LABELS.sp20Mirror}
            stroke={CHART_COLORS.sp20Mirror}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: CHART_COLORS.sp20Mirror }}
          />

          <Line
            type="monotone"
            dataKey="sp20Equal"
            name={CHART_LABELS.sp20Equal}
            stroke={CHART_COLORS.sp20Equal}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: CHART_COLORS.sp20Equal }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceChart;
