/* ================================================================
   MetricCard -- a single figure with its label and optional delta.

   No count-up animation and no scroll reveal: on a fund page a
   figure is a fact, not an event, and animating one reads as
   marketing. Content is present at first paint.
   ================================================================ */

import React from "react";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface MetricCardProps {
  /** Label below the number */
  label: string;
  /** Numeric value to display */
  value: number;
  /** Formatting function for display */
  format: (n: number) => string;
  /** Optional subtitle text */
  subtitle?: string;
  /** Optional delta value */
  delta?: number;
  /** Optional delta formatting function */
  deltaFormat?: (n: number) => string;
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  format,
  subtitle,
  delta,
  deltaFormat,
}) => {
  const formattedDelta =
    delta !== undefined
      ? deltaFormat
        ? deltaFormat(delta)
        : `${delta > 0 ? "+" : ""}${(delta * 100).toFixed(1)}%`
      : null;

  return (
    <div className="border bg-ground p-5">
      <span className="num block text-3xl font-normal tracking-tight text-ink">
        {format(value)}
      </span>

      <p className="mt-2 text-sm text-ink-secondary">{label}</p>

      {subtitle && <p className="mt-1 text-xs text-ink-muted">{subtitle}</p>}

      {/* Deltas are stated, not celebrated — no green/red on a figure
          whose difference from the benchmark is not significant. */}
      {formattedDelta !== null && delta !== undefined && (
        <p className="num mt-2 text-xs font-medium text-ink-muted">
          {formattedDelta}
        </p>
      )}
    </div>
  );
};

export default MetricCard;
