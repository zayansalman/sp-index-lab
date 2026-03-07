"use client";

/* ================================================================
   ConcentrationAnalyzer -- Prism / light-refraction icon
   When active, shows an R-squared value counting up.
   ================================================================ */

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ComponentNode from "./ComponentNode";

interface ConcentrationAnalyzerProps {
  isActive: boolean;
}

/* ── Prism icon with refracting light rays ────────────────── */
const PrismIcon: React.FC = () => (
  <g>
    {/* Triangular prism */}
    <polygon
      points="0,-16 -18,14 18,14"
      fill="none"
      stroke="#00D4AA"
      strokeWidth={1.4}
      strokeLinejoin="round"
      opacity={0.9}
    />

    {/* Incoming light ray (white, single beam) */}
    <line
      x1={-32}
      y1={0}
      x2={-10}
      y2={0}
      stroke="#F0F0F0"
      strokeWidth={1.2}
      opacity={0.6}
    />

    {/* Refracted rays (fanning out to the right) */}
    <line x1={10} y1={-4} x2={32} y2={-12} stroke="#00D4AA" strokeWidth={0.8} opacity={0.7} />
    <line x1={10} y1={0} x2={32} y2={0} stroke="#6366F1" strokeWidth={0.8} opacity={0.7} />
    <line x1={10} y1={4} x2={32} y2={12} stroke="#FFD700" strokeWidth={0.8} opacity={0.7} />
  </g>
);

/* ── R-squared counter animation ──────────────────────────── */
const RSquaredCounter: React.FC<{
  isActive: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
}> = ({ isActive, x, y, width, height }) => {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const TARGET = 94.9;
  const DURATION = 1200; // ms

  useEffect(() => {
    if (!isActive) {
      setValue(0);
      return;
    }

    startTimeRef.current = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTimeRef.current;
      const progress = Math.min(elapsed / DURATION, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(eased * TARGET);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [isActive]);

  return (
    <AnimatePresence>
      {isActive && (
        <motion.text
          x={x + width / 2}
          y={y + height - 14}
          textAnchor="middle"
          fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"
          fontSize={11}
          fontWeight={600}
          fill="#00D4AA"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.8 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          R&sup2; = {value.toFixed(1)}%
        </motion.text>
      )}
    </AnimatePresence>
  );
};

const ConcentrationAnalyzer: React.FC<ConcentrationAnalyzerProps> = ({
  isActive,
}) => {
  const x = 250;
  const y = 310;
  const width = 300;
  const height = 110;

  return (
    <ComponentNode
      id="concentration-analyzer"
      x={x}
      y={y}
      width={width}
      height={height}
      label="CONCENTRATION ANALYZER"
      sublabel="Variance Decomposition"
      isActive={isActive}
      icon={<PrismIcon />}
    >
      <RSquaredCounter
        isActive={isActive}
        x={x}
        y={y}
        width={width}
        height={height}
      />
    </ComponentNode>
  );
};

export default ConcentrationAnalyzer;
