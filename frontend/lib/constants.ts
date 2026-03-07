/* ================================================================
   S&P Index Lab -- Design Tokens & Constants
   Single source of truth for colours, timing, and stage configs.
   ================================================================ */

import type { MachineStage, MachineStageConfig } from "./types";

/* ──────────────────────────────────────────────────────────────
   Colour Palette
   Mirrors the CSS custom properties in globals.css so that
   components using inline styles or JS-driven animations can
   reference the same palette.
   ────────────────────────────────────────────────────────────── */

export const colors = {
  bg: {
    primary: "#0A0A0F",
    secondary: "#111118",
    tertiary: "#1A1A24",
  },
  accent: {
    primary: "#00D4AA",
    secondary: "#FFD700",
    tertiary: "#6366F1",
  },
  text: {
    primary: "#F0F0F0",
    secondary: "#888899",
    muted: "#555566",
  },
  wire: {
    inactive: "#2A2A35",
    active: "#00D4AA",
  },
} as const;

/* ──────────────────────────────────────────────────────────────
   Colour with Alpha helper
   ────────────────────────────────────────────────────────────── */

/**
 * Return an rgba() string from a hex colour and an alpha value.
 *
 * @param hex  6-character hex colour (with or without leading #)
 * @param alpha  Opacity between 0 and 1
 */
export function withAlpha(hex: string, alpha: number): string {
  const cleaned = hex.replace("#", "");
  const r = parseInt(cleaned.substring(0, 2), 16);
  const g = parseInt(cleaned.substring(2, 4), 16);
  const b = parseInt(cleaned.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/* ──────────────────────────────────────────────────────────────
   Animation Timing
   ────────────────────────────────────────────────────────────── */

export const timing = {
  /** Duration for stage transitions in the machine animation (ms) */
  stageTransition: 1500,
  /** Duration for card entrance animations (ms) */
  cardEntrance: 400,
  /** Duration for chart draw-in animations (ms) */
  chartDraw: 800,
  /** Delay between sequential card reveals (ms) */
  staggerDelay: 100,
  /** Duration for wire activation animation (ms) */
  wireActivation: 600,
  /** Duration for tooltip fade-in (ms) */
  tooltipFade: 200,
  /** Duration for number counter animations (ms) */
  counterDuration: 1200,
  /** Spring stiffness for framer-motion layout animations */
  springStiffness: 300,
  /** Spring damping for framer-motion layout animations */
  springDamping: 30,
} as const;

/* ──────────────────────────────────────────────────────────────
   Per-stage Durations (ms)
   Used by the useMachineState hook to schedule transitions.
   ────────────────────────────────────────────────────────────── */

export const STAGE_DURATIONS: Record<MachineStage, number> = {
  idle: 0,
  powering_up: 1200,
  data_pipeline: 1500,
  concentration: 1500,
  building: 1500,
  optimizing: 1500,
  monitoring: 1500,
  complete: 0,
} as const;

/* ──────────────────────────────────────────────────────────────
   Machine Stage Configurations
   Ordered list describing every stage in the boot sequence.
   ────────────────────────────────────────────────────────────── */

export const machineStages: MachineStageConfig[] = [
  {
    id: "idle",
    name: "Standby",
    duration: STAGE_DURATIONS.idle,
    description: "Machine is powered off. Flip the switch to begin.",
    order: 0,
  },
  {
    id: "powering_up",
    name: "Powering Up",
    duration: STAGE_DURATIONS.powering_up,
    description: "Initialising circuits and loading configuration...",
    order: 1,
  },
  {
    id: "data_pipeline",
    name: "Data Pipeline",
    duration: STAGE_DURATIONS.data_pipeline,
    description: "Ingesting 12+ years of daily price data for 50 S&P 500 stocks...",
    order: 2,
  },
  {
    id: "concentration",
    name: "Concentration Analysis",
    duration: STAGE_DURATIONS.concentration,
    description: "Running OLS regressions to find the concentration elbow...",
    order: 3,
  },
  {
    id: "building",
    name: "Building Mirror Index",
    duration: STAGE_DURATIONS.building,
    description: "Constructing cap-weighted and equal-weighted SP-20 indices...",
    order: 4,
  },
  {
    id: "optimizing",
    name: "Alpha Optimizer",
    duration: STAGE_DURATIONS.optimizing,
    description: "Preparing HRP optimizer, factor model, and regime detector...",
    order: 5,
  },
  {
    id: "monitoring",
    name: "Performance Monitor",
    duration: STAGE_DURATIONS.monitoring,
    description: "Computing Sharpe, Sortino, drawdowns, and 15+ performance metrics...",
    order: 6,
  },
  {
    id: "complete",
    name: "Analysis Complete",
    duration: STAGE_DURATIONS.complete,
    description: "All systems nominal. Results are ready.",
    order: 7,
  },
] as const;

/* ──────────────────────────────────────────────────────────────
   Wire IDs per Stage
   Maps each stage to the set of SVG wire IDs that should be
   visually "active" (animated with electricFlow).
   ────────────────────────────────────────────────────────────── */

export const STAGE_WIRES: Record<MachineStage, string[]> = {
  idle: [],
  powering_up: ["wire-power"],
  data_pipeline: ["wire-power", "wire-data-in"],
  concentration: ["wire-power", "wire-data-in", "wire-concentration"],
  building: ["wire-power", "wire-data-in", "wire-concentration", "wire-builder"],
  optimizing: [
    "wire-power",
    "wire-data-in",
    "wire-concentration",
    "wire-builder",
    "wire-optimizer",
  ],
  monitoring: [
    "wire-power",
    "wire-data-in",
    "wire-concentration",
    "wire-builder",
    "wire-optimizer",
    "wire-monitor",
  ],
  complete: [
    "wire-power",
    "wire-data-in",
    "wire-concentration",
    "wire-builder",
    "wire-optimizer",
    "wire-monitor",
    "wire-output",
  ],
} as const;

/* ──────────────────────────────────────────────────────────────
   Component IDs per Stage
   Maps each stage to the machine components that should appear
   "active" (lit up, glowing, spinning gear, etc.).
   ────────────────────────────────────────────────────────────── */

export const STAGE_COMPONENTS: Record<MachineStage, string[]> = {
  idle: [],
  powering_up: ["power-switch"],
  data_pipeline: ["power-switch", "data-pipeline"],
  concentration: ["power-switch", "data-pipeline", "concentration-analyzer"],
  building: ["power-switch", "data-pipeline", "concentration-analyzer", "mirror-builder"],
  optimizing: [
    "power-switch",
    "data-pipeline",
    "concentration-analyzer",
    "mirror-builder",
    "alpha-optimizer",
  ],
  monitoring: [
    "power-switch",
    "data-pipeline",
    "concentration-analyzer",
    "mirror-builder",
    "alpha-optimizer",
    "performance-monitor",
  ],
  complete: [
    "power-switch",
    "data-pipeline",
    "concentration-analyzer",
    "mirror-builder",
    "alpha-optimizer",
    "performance-monitor",
  ],
} as const;

/* ──────────────────────────────────────────────────────────────
   Chart Colour Mapping
   Consistent colours for each index across all charts.
   ────────────────────────────────────────────────────────────── */

export const CHART_COLORS = {
  sp500: "#888899",
  sp20Mirror: "#00D4AA",
  sp20Equal: "#FFD700",
  sp20Alpha: "#6366F1",
} as const;

export const CHART_LABELS = {
  sp500: "S&P 500",
  sp20Mirror: "SP-20 Mirror",
  sp20Equal: "SP-20 Equal",
  sp20Alpha: "SP-20 Alpha",
} as const;

/* ──────────────────────────────────────────────────────────────
   Breakpoints (reference only -- Tailwind v4 uses defaults)
   ────────────────────────────────────────────────────────────── */

export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;
