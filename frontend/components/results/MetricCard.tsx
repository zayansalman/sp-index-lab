"use client";

/* ================================================================
   MetricCard -- Animated metric display card
   Shows a large number with AnimatedCounter, label, and
   optional delta indicator. Fades in when scrolled into view.
   ================================================================ */

import React from "react";
import { motion } from "framer-motion";
import AnimatedCounter from "@/components/ui/AnimatedCounter";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface MetricCardProps {
  /** Label below the number */
  label: string;
  /** Numeric value to animate */
  value: number;
  /** Formatting function for display */
  format: (n: number) => string;
  /** Optional subtitle text */
  subtitle?: string;
  /** Optional delta value (positive = green, negative = red) */
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
  const formattedDelta = delta !== undefined
    ? deltaFormat
      ? deltaFormat(delta)
      : `${delta > 0 ? "+" : ""}${(delta * 100).toFixed(1)}%`
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="rounded-xl border border-[#1A1A24] bg-bg-secondary p-5"
    >
      {/* Large animated number */}
      <AnimatedCounter
        value={value}
        format={format}
        duration={1.5}
        className="block text-3xl font-bold text-accent-primary"
      />

      {/* Label */}
      <p className="mt-2 text-sm text-text-secondary">{label}</p>

      {/* Subtitle */}
      {subtitle && (
        <p className="mt-1 text-xs text-text-muted">{subtitle}</p>
      )}

      {/* Delta indicator */}
      {formattedDelta !== null && delta !== undefined && (
        <p
          className={`mt-2 text-xs font-medium ${
            delta >= 0 ? "text-accent-primary" : "text-red-400"
          }`}
        >
          {formattedDelta}
        </p>
      )}
    </motion.div>
  );
};

export default MetricCard;
