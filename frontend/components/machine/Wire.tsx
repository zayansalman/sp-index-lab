"use client";

/* ================================================================
   Wire -- Animated SVG connection between machine components
   Three layers: base wire, active glow wire with dash animation,
   and a traveling particle.
   ================================================================ */

import React, { useId } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface WireProps {
  /** SVG path d-attribute describing the wire shape */
  pathData: string;
  /** Whether the wire is currently energized */
  isActive: boolean;
  /** Delay in seconds before the active animation starts */
  delay?: number;
}

const Wire: React.FC<WireProps> = ({ pathData, isActive, delay = 0 }) => {
  const uid = useId();
  const glowFilterId = `wire-glow-${uid}`;
  const motionPathId = `wire-path-${uid}`;

  return (
    <g>
      <defs>
        {/* Glow filter for active wire */}
        <filter id={glowFilterId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Path definition for animateMotion */}
        <path id={motionPathId} d={pathData} />
      </defs>

      {/* Layer 1: Base wire (always visible) */}
      <path
        d={pathData}
        fill="none"
        stroke="#2A2A35"
        strokeWidth={2}
        strokeLinecap="round"
      />

      {/* Layer 2: Active glow wire with dash animation */}
      <AnimatePresence>
        {isActive && (
          <motion.path
            d={pathData}
            fill="none"
            stroke="#00D4AA"
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray="8 12"
            filter={`url(#${glowFilterId})`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, delay }}
            style={{
              animation: isActive
                ? `electricFlow 1s linear ${delay}s infinite`
                : "none",
            }}
          />
        )}
      </AnimatePresence>

      {/* Layer 3: Traveling particle */}
      <AnimatePresence>
        {isActive && (
          <motion.circle
            r={3}
            fill="white"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.9, 0.9, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, delay }}
          >
            <animateMotion
              dur="2s"
              repeatCount="indefinite"
              begin={`${delay}s`}
            >
              <mpath href={`#${motionPathId}`} />
            </animateMotion>
          </motion.circle>
        )}
      </AnimatePresence>
    </g>
  );
};

export default Wire;
