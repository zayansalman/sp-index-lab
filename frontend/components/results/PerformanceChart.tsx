"use client";

/* ================================================================
   PerformanceChart -- Growth of $1 comparison
   Recharts LineChart with interactive legend: click any series to
   toggle its visibility.  Displays up to 7 portfolios side-by-side.
   ================================================================ */

import React, { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceNavPoint } from "@/lib/types";
import { CHART_COLORS, CHART_LABELS } from "@/lib/constants";

/* ──────────────────────────────────────────────────────────────
   Props + series config
   ────────────────────────────────────────────────────────────── */

interface PerformanceChartProps {
  data: PerformanceNavPoint[];
}

type SeriesKey =
  | "sp500"
  | "sp20Mirror"
  | "sp20Equal"
  | "spnAlpha"
  | "spnAlphaHrp"
  | "spnAlphaMvoSharpe"
  | "spnHedged";

interface SeriesConfig {
  key: SeriesKey;
  label: string;
  color: string;
  strokeWidth: number;
  /** Whether the series is shown by default.  Keep the chart legible
   *  out-of-the-box by only showing the headline lines. */
  defaultVisible: boolean;
}

const SERIES_CONFIG: SeriesConfig[] = [
  { key: "sp500",             label: CHART_LABELS.sp500,             color: CHART_COLORS.sp500,             strokeWidth: 1.5, defaultVisible: true },
  { key: "sp20Mirror",        label: CHART_LABELS.sp20Mirror,        color: CHART_COLORS.sp20Mirror,        strokeWidth: 1.5, defaultVisible: true },
  { key: "sp20Equal",         label: CHART_LABELS.sp20Equal,         color: CHART_COLORS.sp20Equal,         strokeWidth: 1.5, defaultVisible: true },
  { key: "spnAlpha",          label: CHART_LABELS.spnAlpha,          color: CHART_COLORS.spnAlpha,          strokeWidth: 2.5, defaultVisible: true },
  { key: "spnAlphaHrp",       label: CHART_LABELS.spnAlphaHrp,       color: CHART_COLORS.spnAlphaHrp,       strokeWidth: 1.5, defaultVisible: false },
  { key: "spnAlphaMvoSharpe", label: CHART_LABELS.spnAlphaMvoSharpe, color: CHART_COLORS.spnAlphaMvoSharpe, strokeWidth: 1.5, defaultVisible: false },
  { key: "spnHedged",         label: CHART_LABELS.spnHedged,         color: CHART_COLORS.spnHedged,         strokeWidth: 2.5, defaultVisible: true },
];

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
            ${entry.value?.toFixed?.(2) ?? "--"}
          </span>
        </p>
      ))}
    </div>
  );
};

function formatDateTick(dateStr: string): string {
  if (!dateStr) return "";
  return dateStr.substring(0, 4);
}

/* ──────────────────────────────────────────────────────────────
   Interactive Legend
   Click a pill to toggle the series on/off.
   ────────────────────────────────────────────────────────────── */

interface LegendProps {
  series: SeriesConfig[];
  visibility: Record<SeriesKey, boolean>;
  onToggle: (key: SeriesKey) => void;
}

const InteractiveLegend: React.FC<LegendProps> = ({ series, visibility, onToggle }) => (
  <div className="mt-3 flex flex-wrap gap-2">
    {series.map((s) => {
      const isOn = visibility[s.key];
      return (
        <button
          key={s.key}
          type="button"
          onClick={() => onToggle(s.key)}
          className={`group flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition-all ${
            isOn
              ? "border-[#2A2A35] bg-bg-secondary text-text-primary"
              : "border-[#1A1A24] bg-transparent text-text-muted opacity-50 hover:opacity-80"
          }`}
          aria-pressed={isOn}
          title={`${isOn ? "Hide" : "Show"} ${s.label}`}
        >
          <span
            className="inline-block h-2.5 w-2.5 rounded-full transition-transform group-hover:scale-125"
            style={{
              backgroundColor: isOn ? s.color : "transparent",
              border: isOn ? "none" : `1.5px solid ${s.color}`,
            }}
          />
          <span className="whitespace-nowrap">{s.label}</span>
        </button>
      );
    })}
  </div>
);

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const PerformanceChart: React.FC<PerformanceChartProps> = ({ data }) => {
  // Determine which series have actual data (non-null in at least 1 point)
  const availableSeries = SERIES_CONFIG.filter((s) =>
    data.some((d) => d[s.key] !== undefined && d[s.key] !== null),
  );

  const [visibility, setVisibility] = useState<Record<SeriesKey, boolean>>(() => {
    const init = {} as Record<SeriesKey, boolean>;
    SERIES_CONFIG.forEach((s) => {
      init[s.key] = s.defaultVisible;
    });
    return init;
  });

  const toggle = (key: SeriesKey) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Thin out data for performance: show every Nth point
  const thinned =
    data.length > 500
      ? data.filter((_, i) => i % Math.ceil(data.length / 500) === 0 || i === data.length - 1)
      : data;

  return (
    <div className="w-full">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide text-text-secondary">
          Growth of $1: All Portfolios
        </h3>
        <span className="text-xs text-text-muted">
          Click pills to toggle lines
        </span>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={thinned}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1A1A24" vertical={false} />
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

          {availableSeries.map((s) =>
            visibility[s.key] ? (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={s.strokeWidth}
                dot={false}
                activeDot={{ r: 3, fill: s.color }}
                connectNulls
                isAnimationActive={false}
              />
            ) : null,
          )}
        </LineChart>
      </ResponsiveContainer>

      <InteractiveLegend
        series={availableSeries}
        visibility={visibility}
        onToggle={toggle}
      />
    </div>
  );
};

export default PerformanceChart;
