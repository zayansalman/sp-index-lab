"use client";

/* ================================================================
   DrawdownChart -- Drawdown analysis area chart
   Recharts AreaChart showing S&P 500 and SP-20 Mirror drawdowns
   from peak with inverted Y-axis (0% at top, negative at bottom).
   ================================================================ */

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { DrawdownPoint } from "@/lib/types";
import { CHART_COLORS, CHART_LABELS } from "@/lib/constants";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface DrawdownChartProps {
  data: DrawdownPoint[];
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
            {(entry.value * 100).toFixed(1)}%
          </span>
        </p>
      ))}
    </div>
  );
};

/* ──────────────────────────────────────────────────────────────
   Date tick formatter
   ────────────────────────────────────────────────────────────── */

function formatDateTick(dateStr: string): string {
  if (!dateStr) return "";
  return dateStr.substring(0, 4);
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const DrawdownChart: React.FC<DrawdownChartProps> = ({ data }) => {
  // Thin out data for performance
  const thinned =
    data.length > 500
      ? data.filter(
          (_, i) =>
            i % Math.ceil(data.length / 500) === 0 || i === data.length - 1,
        )
      : data;

  // Calculate the minimum drawdown for Y-axis domain
  const minDrawdown = Math.min(
    ...data.map((d) => Math.min(d.sp500, d.sp20Mirror)),
  );
  const yMin = Math.floor(minDrawdown * 10) / 10; // Round down to nearest 10%

  return (
    <div className="w-full">
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-text-secondary">
        Drawdown Analysis
      </h3>

      <ResponsiveContainer width="100%" height={320}>
        <AreaChart
          data={thinned}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <defs>
            <linearGradient id="gradientSp500DD" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.sp500} stopOpacity={0.05} />
              <stop offset="100%" stopColor={CHART_COLORS.sp500} stopOpacity={0.2} />
            </linearGradient>
            <linearGradient id="gradientMirrorDD" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#EF4444" stopOpacity={0.05} />
              <stop offset="100%" stopColor="#EF4444" stopOpacity={0.2} />
            </linearGradient>
          </defs>

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
            domain={[yMin, 0]}
            tick={{ fill: "#888899", fontSize: 11 }}
            axisLine={{ stroke: "#1A1A24" }}
            tickLine={{ stroke: "#1A1A24" }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            reversed={false}
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

          <Area
            type="monotone"
            dataKey="sp500"
            name={CHART_LABELS.sp500}
            stroke={CHART_COLORS.sp500}
            strokeWidth={1}
            fill="url(#gradientSp500DD)"
            dot={false}
          />

          <Area
            type="monotone"
            dataKey="sp20Mirror"
            name={CHART_LABELS.sp20Mirror}
            stroke="#EF4444"
            strokeWidth={1}
            fill="url(#gradientMirrorDD)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DrawdownChart;
