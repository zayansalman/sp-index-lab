"use client";

/* ================================================================
   TimeRangeSelector -- reusable time-window pill group
   ================================================================ */

import React from "react";

export type TimeRange = "1M" | "3M" | "6M" | "1Y" | "2Y" | "5Y" | "ALL";

export const TIME_RANGES: { key: TimeRange; label: string }[] = [
  { key: "1M", label: "1M" },
  { key: "3M", label: "3M" },
  { key: "6M", label: "6M" },
  { key: "1Y", label: "1Y" },
  { key: "2Y", label: "2Y" },
  { key: "5Y", label: "5Y" },
  { key: "ALL", label: "All" },
];

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (r: TimeRange) => void;
  /** Which ranges to actually expose (default: all). */
  available?: TimeRange[];
}

const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
  value,
  onChange,
  available,
}) => {
  const ranges = available
    ? TIME_RANGES.filter((r) => available.includes(r.key))
    : TIME_RANGES;

  return (
    <div className="inline-flex items-center gap-1 rounded-lg border bg-ground p-1">
      {ranges.map((r) => {
        const isActive = r.key === value;
        return (
          <button
            key={r.key}
            type="button"
            onClick={() => onChange(r.key)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium tabular-nums transition-all ${
              isActive
                ? "bg-accent/15 text-accent"
                : "text-ink-muted hover:bg-surface hover:text-ink-secondary"
            }`}
            aria-pressed={isActive}
          >
            {r.label}
          </button>
        );
      })}
    </div>
  );
};

export default TimeRangeSelector;
