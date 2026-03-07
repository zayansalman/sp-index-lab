"use client";

/* ================================================================
   LightBulb -- Small SVG indicator light
   Shows active/inactive state with a glow effect when lit.
   ================================================================ */

import React, { useId } from "react";
import { motion } from "framer-motion";

interface LightBulbProps {
  /** Whether the light is on */
  isActive: boolean;
  /** X center coordinate */
  cx: number;
  /** Y center coordinate */
  cy: number;
  /** Radius of the light (default 8) */
  size?: number;
}

const LightBulb: React.FC<LightBulbProps> = ({
  isActive,
  cx,
  cy,
  size = 8,
}) => {
  const filterId = useId();
  const glowId = `glow-bulb-${filterId}`;

  return (
    <g>
      {/* Glow filter definition */}
      <defs>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Outer glow ring (visible only when active) */}
      <motion.circle
        cx={cx}
        cy={cy}
        r={size + 2}
        fill="none"
        stroke="#00D4AA"
        strokeWidth={1}
        initial={{ opacity: 0 }}
        animate={{ opacity: isActive ? 0.3 : 0 }}
        transition={{ duration: 0.5 }}
      />

      {/* Main indicator circle */}
      <motion.circle
        cx={cx}
        cy={cy}
        r={size}
        initial={{ fill: "#2A2A35", opacity: 0.6 }}
        animate={{
          fill: isActive ? "#00D4AA" : "#2A2A35",
          opacity: isActive ? 1 : 0.6,
        }}
        transition={{ duration: 0.5 }}
        filter={isActive ? `url(#${glowId})` : undefined}
      />
    </g>
  );
};

export default LightBulb;
