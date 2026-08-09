/* ================================================================
   Chart theme -- the single source of truth for chart colour.

   Recharts holds colour inside component props (stroke, tick.fill,
   gradient stops, activeDot), which Tailwind classes cannot reach.
   Those values live here rather than being inlined per chart, so the
   palette can be changed in one place.

   Do NOT put `var(--color-…)` in recharts props. Recharts performs
   colour arithmetic for gradient stops and activeDot fills, and a
   `var()` string produces garbage rather than an error.
   ================================================================ */

import type { StrategyKey } from "./strategyMeta";

/* ──────────────────────────────────────────────────────────────
   Series palette -- tuned for a WHITE canvas.

   The four series separate in LUMINANCE, not only hue, so the page
   survives greyscale printing and monochromatic vision. Greyscale
   equivalents form a monotone ladder: 35 / 100 / 123 / 147.

   The benchmark is the only chromatically neutral series — it is a
   reference, not a competitor, and should never draw the eye.

   Contrast against #FFFFFF (3:1 is the non-text floor):
     spnAlpha   #10233D  15.79:1   grey 35
     sp20Mirror #1668A5   5.90:1   grey 100
     sp20Equal  #B26A12   4.23:1   grey 123
     sp500      #8C949E   3.07:1   grey 147
   ────────────────────────────────────────────────────────────── */

export const CHART_COLORS: Record<StrategyKey, string> = {
  spnAlpha: "#10233D",
  sp20Mirror: "#1668A5",
  sp20Equal: "#B26A12",
  sp500: "#8C949E",
} as const;

/** Measured relative luminance, asserted by the contrast test. */
export const CHART_LUMINANCE: Record<StrategyKey, number> = {
  spnAlpha: 0.0165,
  sp20Mirror: 0.1279,
  sp20Equal: 0.1982,
  sp500: 0.2922,
} as const;

export interface SeriesStyle {
  label: string;
  color: string;
  strokeWidth: number;
  /** SVG dash pattern; undefined means solid. */
  dash?: string;
  /** Raw key used by the exported JSON (snake_case). */
  exportKey: string;
  isBenchmark?: boolean;
}

/* The benchmark carries hue, weight AND dash as three redundant
   channels, so it stays distinguishable when any one fails. */
export const SERIES_STYLE: Record<StrategyKey, SeriesStyle> = {
  sp500: {
    label: "S&P 500 (TR)",
    color: CHART_COLORS.sp500,
    strokeWidth: 1.5,
    dash: "4 3",
    exportKey: "sp500",
    isBenchmark: true,
  },
  sp20Mirror: {
    label: "SP-20 Mirror",
    color: CHART_COLORS.sp20Mirror,
    strokeWidth: 1.75,
    exportKey: "sp20_mirror",
  },
  sp20Equal: {
    label: "SP-20 Equal",
    color: CHART_COLORS.sp20Equal,
    strokeWidth: 1.75,
    exportKey: "sp20_equal",
  },
  spnAlpha: {
    label: "SP-N Alpha",
    color: CHART_COLORS.spnAlpha,
    strokeWidth: 1.75,
    exportKey: "spn_alpha",
  },
} as const;

/** Emphasis for the strategy a page is about: darkest and heaviest. */
export const SELECTED_STROKE_WIDTH = 2.25;

/* ──────────────────────────────────────────────────────────────
   Chart chrome
   ────────────────────────────────────────────────────────────── */

export const chartTheme = {
  grid: {
    stroke: "#E3E7EB",
    strokeDasharray: "3 3",
    /** Horizontal rules only — vertical gridlines add noise on a time axis. */
    vertical: false,
  },
  axis: {
    stroke: "#C4CCD4",
    tickStroke: "#C4CCD4",
    tick: { fill: "#5C6875", fontSize: 11 },
  },
  referenceLine: {
    stroke: "#8C949E",
    strokeDasharray: "4 4",
  },
  /** Zero / parity rule — heavier than a gridline, it carries meaning. */
  zeroLine: "#0B1220",
  /** Page ground. Needed as a literal for activeDot rings and gradient stops. */
  ground: "#FFFFFF",
  /** Emphasis colour for annotation on charts that plot a single series. */
  accent: "#12395F",
  /** Tailwind classes for the tooltip surface (not a recharts prop). */
  tooltipSurface:
    "rounded border border-border-strong bg-ground px-3 py-2 shadow-md",
} as const;

/* ──────────────────────────────────────────────────────────────
   Helpers
   ────────────────────────────────────────────────────────────── */

/** Return an rgba() string from a hex colour and an alpha value. */
export function withAlpha(hex: string, alpha: number): string {
  const cleaned = hex.replace("#", "");
  const r = parseInt(cleaned.substring(0, 2), 16);
  const g = parseInt(cleaned.substring(2, 4), 16);
  const b = parseInt(cleaned.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Style for one series, emphasised when it is the page's subject. */
export function seriesStyle(key: StrategyKey, selected = false): SeriesStyle {
  const base = SERIES_STYLE[key];
  return selected ? { ...base, strokeWidth: SELECTED_STROKE_WIDTH } : base;
}
