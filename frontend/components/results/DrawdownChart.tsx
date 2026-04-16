"use client";

/* ================================================================
   DrawdownChart -- Drawdown analysis with interactive legend
   Recharts AreaChart; click any pill to toggle that series.
   ================================================================ */

import React, { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import type { DrawdownPoint } from "@/lib/types";
import { CHART_COLORS, CHART_LABELS } from "@/lib/constants";

/* ──────────────────────────────────────────────────────────────
   Props + series config
   ────────────────────────────────────────────────────────────── */

interface DrawdownChartProps {
  data: DrawdownPoint[];
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
  gradientId: string;
  defaultVisible: boolean;
}

const SERIES_CONFIG: SeriesConfig[] = [
  { key: "sp500",             label: CHART_LABELS.sp500,             color: CHART_COLORS.sp500,             gradientId: "ddSp500",       defaultVisible: true },
  { key: "sp20Mirror",        label: CHART_LABELS.sp20Mirror,        color: "#EF4444",                      gradientId: "ddMirror",      defaultVisible: true },
  { key: "sp20Equal",         label: CHART_LABELS.sp20Equal,         color: CHART_COLORS.sp20Equal,         gradientId: "ddEqual",       defaultVisible: false },
  { key: "spnAlpha",          label: CHART_LABELS.spnAlpha,          color: CHART_COLORS.spnAlpha,          gradientId: "ddAlpha",       defaultVisible: true },
  { key: "spnAlphaHrp",       label: CHART_LABELS.spnAlphaHrp,       color: CHART_COLORS.spnAlphaHrp,       gradientId: "ddAlphaHrp",    defaultVisible: false },
  { key: "spnAlphaMvoSharpe", label: CHART_LABELS.spnAlphaMvoSharpe, color: CHART_COLORS.spnAlphaMvoSharpe, gradientId: "ddAlphaSharpe", defaultVisible: false },
  { key: "spnHedged",         label: CHART_LABELS.spnHedged,         color: CHART_COLORS.spnHedged,         gradientId: "ddHedged",      defaultVisible: true },
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
            {((entry.value ?? 0) * 100).toFixed(1)}%
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

const DrawdownChart: React.FC<DrawdownChartProps> = ({ data }) => {
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

  const thinned =
    data.length > 500
      ? data.filter(
          (_, i) =>
            i % Math.ceil(data.length / 500) === 0 || i === data.length - 1,
        )
      : data;

  // Dynamic Y-axis: use only the visible series to determine range
  const visibleKeys = availableSeries.filter((s) => visibility[s.key]).map((s) => s.key);
  let minDrawdown = 0;
  data.forEach((d) => {
    visibleKeys.forEach((k) => {
      const v = d[k];
      if (typeof v === "number" && v < minDrawdown) minDrawdown = v;
    });
  });
  const yMin = Math.floor(minDrawdown * 10) / 10;

  return (
    <div className="w-full">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide text-text-secondary">
          Drawdown Analysis
        </h3>
        <span className="text-xs text-text-muted">Click pills to toggle</span>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <AreaChart
          data={thinned}
          margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
        >
          <defs>
            {SERIES_CONFIG.map((s) => (
              <linearGradient
                key={s.gradientId}
                id={s.gradientId}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={s.color} stopOpacity={0.05} />
                <stop offset="100%" stopColor={s.color} stopOpacity={0.25} />
              </linearGradient>
            ))}
          </defs>

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
            domain={[yMin, 0]}
            tick={{ fill: "#888899", fontSize: 11 }}
            axisLine={{ stroke: "#1A1A24" }}
            tickLine={{ stroke: "#1A1A24" }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          />
          <RechartsTooltip content={<CustomTooltip />} />

          {availableSeries.map((s) =>
            visibility[s.key] ? (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={1.5}
                fill={`url(#${s.gradientId})`}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ) : null,
          )}
        </AreaChart>
      </ResponsiveContainer>

      <InteractiveLegend
        series={availableSeries}
        visibility={visibility}
        onToggle={toggle}
      />
    </div>
  );
};

export default DrawdownChart;
