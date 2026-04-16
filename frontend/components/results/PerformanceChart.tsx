"use client";

/* ================================================================
   PerformanceChart -- Growth of $1 with time range + legend toggles
   ================================================================ */

import React, { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceNavPoint, PerformanceNavBundle } from "@/lib/types";
import { CHART_COLORS, CHART_LABELS } from "@/lib/constants";
import TimeRangeSelector, { type TimeRange } from "./TimeRangeSelector";

/* ──────────────────────────────────────────────────────────────
   Time-range logic
   ────────────────────────────────────────────────────────────── */

/** How many days of history each range represents (approx trading days). */
const RANGE_DAYS: Record<TimeRange, number | null> = {
  "1M": 21,
  "3M": 63,
  "6M": 126,
  "1Y": 252,
  "2Y": 504,
  "5Y": 1260,
  ALL: null,
};

/** Shorter ranges use daily resolution; longer ranges use weekly. */
function useRangeData(
  bundle: PerformanceNavBundle,
  range: TimeRange,
): PerformanceNavPoint[] {
  return useMemo(() => {
    const windowDays = RANGE_DAYS[range];
    const useDaily = windowDays !== null && windowDays <= 252;
    const source = useDaily ? bundle.daily : bundle.weekly;

    if (source.length === 0) return [];
    if (windowDays === null) return source;

    // Each weekly point is ~5 trading days; each daily point ~1.
    const pointsPerDay = useDaily ? 1 : 1 / 5;
    const keepPoints = Math.ceil(windowDays * pointsPerDay);
    return source.slice(Math.max(0, source.length - keepPoints));
  }, [bundle, range]);
}

/** Re-normalise every series so it starts at $1 on the first row. */
function normaliseToOne(points: PerformanceNavPoint[]): PerformanceNavPoint[] {
  if (points.length === 0) return points;
  const first = points[0];
  const baselines: Record<string, number> = {};
  Object.entries(first).forEach(([k, v]) => {
    if (k !== "date" && typeof v === "number" && v > 0) baselines[k] = v;
  });
  return points.map((p) => {
    const out: PerformanceNavPoint = { date: p.date, sp500: 0, sp20Mirror: 0, sp20Equal: 0 };
    Object.entries(p).forEach(([k, v]) => {
      if (k === "date") return;
      const base = baselines[k];
      if (typeof v === "number" && base) {
        (out as unknown as Record<string, number>)[k] = v / base;
      }
    });
    return out;
  });
}

/* ──────────────────────────────────────────────────────────────
   Props + series config
   ────────────────────────────────────────────────────────────── */

interface PerformanceChartProps {
  /** Bundle with both weekly and daily series for time-range switching. */
  bundle: PerformanceNavBundle;
}

type SeriesKey =
  | "sp500"
  | "sp20Mirror"
  | "sp20Equal"
  | "spnAlpha"
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
  { key: "spnAlphaMvoSharpe", label: CHART_LABELS.spnAlphaMvoSharpe, color: CHART_COLORS.spnAlphaMvoSharpe, strokeWidth: 2.5, defaultVisible: true },
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

function formatDateTick(dateStr: string, showMonth: boolean): string {
  if (!dateStr) return "";
  if (!showMonth) return dateStr.substring(0, 4);
  // YYYY-MM-DD → "Mmm 'YY" or "Mmm DD"
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.substring(0, 7);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
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

const PerformanceChart: React.FC<PerformanceChartProps> = ({ bundle }) => {
  const [range, setRange] = useState<TimeRange>("5Y");
  const rangeData = useRangeData(bundle, range);
  const data = useMemo(() => normaliseToOne(rangeData), [rangeData]);

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
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold tracking-wide text-text-secondary">
          Growth of $1: All Portfolios
        </h3>
        <TimeRangeSelector value={range} onChange={setRange} />
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
            tickFormatter={(v: string) =>
              formatDateTick(v, range === "1M" || range === "3M" || range === "6M")
            }
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
