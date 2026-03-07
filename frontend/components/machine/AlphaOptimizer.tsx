"use client";

/* ================================================================
   AlphaOptimizer -- Brain / neural-network icon
   When active, neural connection lines pulse and glow.
   ================================================================ */

import React, { useId } from "react";
import { motion } from "framer-motion";
import ComponentNode from "./ComponentNode";

interface AlphaOptimizerProps {
  isActive: boolean;
}

/* ── Neural network / brain icon ──────────────────────────── */
const BrainIcon: React.FC<{ isActive: boolean }> = ({ isActive }) => {
  const filterId = useId();
  const pulseGlowId = `brain-pulse-${filterId}`;

  // Node positions (simplified brain layout)
  const nodes = [
    // Left column (inputs)
    { x: -22, y: -10 },
    { x: -22, y: 4 },
    { x: -22, y: 18 },
    // Middle column (hidden)
    { x: -4, y: -14 },
    { x: -4, y: 0 },
    { x: -4, y: 14 },
    // Right column (outputs)
    { x: 14, y: -6 },
    { x: 14, y: 8 },
  ];

  // Connection pairs (from -> to)
  const connections = [
    [0, 3], [0, 4], [1, 3], [1, 4], [1, 5],
    [2, 4], [2, 5], [3, 6], [3, 7], [4, 6],
    [4, 7], [5, 6], [5, 7],
  ];

  return (
    <g>
      <defs>
        <filter id={pulseGlowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Brain outline (simplified hemisphere shape) */}
      <path
        d="M -6,-20 C -20,-20 -28,-10 -28,2 C -28,14 -20,22 -6,22 C 2,22 8,20 14,16 C 22,10 24,2 24,-4 C 24,-14 18,-20 6,-20 Z"
        fill="none"
        stroke="#00D4AA"
        strokeWidth={1}
        opacity={0.3}
      />

      {/* Neural connections */}
      {connections.map(([from, to], i) => (
        <motion.line
          key={i}
          x1={nodes[from].x}
          y1={nodes[from].y}
          x2={nodes[to].x}
          y2={nodes[to].y}
          stroke="#00D4AA"
          strokeWidth={0.8}
          initial={{ opacity: 0.15 }}
          animate={
            isActive
              ? {
                  opacity: [0.15, 0.7, 0.15],
                  strokeWidth: [0.8, 1.4, 0.8],
                }
              : { opacity: 0.15, strokeWidth: 0.8 }
          }
          transition={
            isActive
              ? {
                  duration: 1.5,
                  repeat: Infinity,
                  delay: i * 0.1,
                  ease: "easeInOut",
                }
              : { duration: 0.4 }
          }
        />
      ))}

      {/* Neuron nodes */}
      {nodes.map((node, i) => (
        <motion.circle
          key={i}
          cx={node.x}
          cy={node.y}
          r={2.5}
          fill="#00D4AA"
          initial={{ opacity: 0.3 }}
          animate={
            isActive
              ? { opacity: [0.3, 1, 0.3] }
              : { opacity: 0.3 }
          }
          transition={
            isActive
              ? {
                  duration: 2,
                  repeat: Infinity,
                  delay: i * 0.15,
                  ease: "easeInOut",
                }
              : { duration: 0.4 }
          }
          filter={isActive ? `url(#${pulseGlowId})` : undefined}
        />
      ))}
    </g>
  );
};

const AlphaOptimizer: React.FC<AlphaOptimizerProps> = ({ isActive }) => {
  return (
    <ComponentNode
      id="alpha-optimizer"
      x={430}
      y={480}
      width={270}
      height={100}
      label="ALPHA OPTIMIZER"
      sublabel="Dynamic Weight Engine"
      isActive={isActive}
      icon={<BrainIcon isActive={isActive} />}
    />
  );
};

export default AlphaOptimizer;
