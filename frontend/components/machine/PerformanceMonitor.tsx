"use client";

/* ================================================================
   PerformanceMonitor -- Gauge / speedometer icon
   When active, the needle sweeps from left to right.
   ================================================================ */

import React from "react";
import { motion } from "framer-motion";
import ComponentNode from "./ComponentNode";

interface PerformanceMonitorProps {
  isActive: boolean;
}

/* ── Gauge / speedometer icon ─────────────────────────────── */
const GaugeIcon: React.FC<{ isActive: boolean }> = ({ isActive }) => {
  // Gauge arc: semicircle from 180deg to 0deg (left to right)
  const gaugeR = 16;
  const cx = 0;
  const cy = 4;

  // SVG arc for the semicircle (180deg -> 0deg)
  const arcPath = `M ${cx - gaugeR} ${cy} A ${gaugeR} ${gaugeR} 0 0 1 ${cx + gaugeR} ${cy}`;

  // Tick marks along the arc
  const ticks = [0.0, 0.25, 0.5, 0.75, 1.0];
  const tickElements = ticks.map((t, i) => {
    const angle = Math.PI * (1 - t); // 180deg at t=0, 0deg at t=1
    const innerR = gaugeR - 3;
    const outerR = gaugeR + 1;
    const x1 = cx + Math.cos(angle) * innerR;
    const y1 = cy - Math.sin(angle) * innerR;
    const x2 = cx + Math.cos(angle) * outerR;
    const y2 = cy - Math.sin(angle) * outerR;
    return (
      <line
        key={i}
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke="#888899"
        strokeWidth={1}
        opacity={0.6}
      />
    );
  });

  // Needle: pivots from center point
  // Resting position ~ 200deg (pointing left-down), active ~ 30deg (pointing right)
  const needleLen = gaugeR - 2;
  const restAngle = 160; // degrees from right (pointing left-ish)
  const activeAngle = 25; // degrees from right (pointing up-right)

  return (
    <g>
      {/* Gauge background arc */}
      <path
        d={arcPath}
        fill="none"
        stroke="#2A2A35"
        strokeWidth={3}
        strokeLinecap="round"
      />

      {/* Active portion (colored arc that fills up) */}
      <motion.path
        d={arcPath}
        fill="none"
        stroke="#00D4AA"
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={`${Math.PI * gaugeR}`}
        initial={{ strokeDashoffset: Math.PI * gaugeR }}
        animate={{
          strokeDashoffset: isActive ? Math.PI * gaugeR * 0.3 : Math.PI * gaugeR,
        }}
        transition={{ duration: 1.2, ease: "easeOut" }}
        opacity={0.8}
      />

      {/* Tick marks */}
      {tickElements}

      {/* Needle */}
      <motion.g
        style={{ originX: `${cx}px`, originY: `${cy}px` }}
        initial={{ rotate: -restAngle }}
        animate={{ rotate: isActive ? -activeAngle : -restAngle }}
        transition={
          isActive
            ? { duration: 1, ease: "easeOut", delay: 0.1 }
            : { duration: 0.6, ease: "easeIn" }
        }
      >
        <line
          x1={cx}
          y1={cy}
          x2={cx + needleLen}
          y2={cy}
          stroke="#F0F0F0"
          strokeWidth={1.5}
          strokeLinecap="round"
        />
      </motion.g>

      {/* Center pivot dot */}
      <circle cx={cx} cy={cy} r={2.5} fill="#F0F0F0" />

      {/* Base line */}
      <line
        x1={cx - gaugeR - 2}
        y1={cy + 1}
        x2={cx + gaugeR + 2}
        y2={cy + 1}
        stroke="#2A2A35"
        strokeWidth={1}
      />
    </g>
  );
};

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  isActive,
}) => {
  return (
    <ComponentNode
      id="performance-monitor"
      x={250}
      y={640}
      width={300}
      height={100}
      label="PERFORMANCE MONITOR"
      sublabel="Risk-Adjusted Metrics"
      isActive={isActive}
      icon={<GaugeIcon isActive={isActive} />}
    />
  );
};

export default PerformanceMonitor;
