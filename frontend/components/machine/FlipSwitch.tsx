"use client";

/* ================================================================
   FlipSwitch -- Physical toggle switch at the top of the machine
   Metal plate background, sliding toggle handle, LED indicator,
   and optional spark particles on toggle.
   ================================================================ */

import React, { useId, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface FlipSwitchProps {
  /** Whether the switch is in the ON position */
  isOn: boolean;
  /** Callback when the switch is toggled */
  onToggle: () => void;
}

/* ── Spark particle that appears briefly on toggle ──────── */
const Spark: React.FC<{ cx: number; cy: number; delay: number }> = ({
  cx,
  cy,
  delay,
}) => (
  <motion.circle
    cx={cx}
    cy={cy}
    r={2}
    fill="#FFD700"
    initial={{ scale: 0, opacity: 1 }}
    animate={{ scale: [0, 1.5, 0], opacity: [1, 0.8, 0] }}
    transition={{ duration: 0.4, delay, ease: "easeOut" }}
  />
);

const FlipSwitch: React.FC<FlipSwitchProps> = ({ isOn, onToggle }) => {
  const uid = useId();
  const plateGradientId = `plate-grad-${uid}`;
  const trackGradientId = `track-grad-${uid}`;
  const handleGradientId = `handle-grad-${uid}`;

  const [showSparks, setShowSparks] = useState(false);

  // Dimensions
  const plateX = 350;
  const plateY = 20;
  const plateW = 100;
  const plateH = 60;
  const trackX = plateX + 20;
  const trackY = plateY + 16;
  const trackW = 60;
  const trackH = 28;
  const handleR = 11;

  // Handle positions
  const handleOffX = trackX + handleR + 4;
  const handleOnX = trackX + trackW - handleR - 4;
  const handleCY = trackY + trackH / 2;

  const handleClick = () => {
    setShowSparks(true);
    onToggle();
    // Clear sparks after animation
    setTimeout(() => setShowSparks(false), 500);
  };

  return (
    <g
      id="power-switch"
      onClick={handleClick}
      style={{ cursor: "pointer" }}
    >
      <defs>
        {/* Metal plate gradient */}
        <linearGradient id={plateGradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2A2A35" />
          <stop offset="50%" stopColor="#1E1E28" />
          <stop offset="100%" stopColor="#16161F" />
        </linearGradient>

        {/* Track interior gradient */}
        <linearGradient id={trackGradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0A0A0F" />
          <stop offset="100%" stopColor="#111118" />
        </linearGradient>

        {/* Handle gradient */}
        <radialGradient id={handleGradientId} cx="40%" cy="35%">
          <stop offset="0%" stopColor="#555566" />
          <stop offset="100%" stopColor="#333340" />
        </radialGradient>
      </defs>

      {/* Metal plate background */}
      <rect
        x={plateX}
        y={plateY}
        width={plateW}
        height={plateH}
        rx={8}
        ry={8}
        fill={`url(#${plateGradientId})`}
        stroke="#3A3A45"
        strokeWidth={1}
      />

      {/* Plate screws (decorative) */}
      <circle cx={plateX + 8} cy={plateY + 8} r={2} fill="#1A1A24" stroke="#3A3A45" strokeWidth={0.5} />
      <circle cx={plateX + plateW - 8} cy={plateY + 8} r={2} fill="#1A1A24" stroke="#3A3A45" strokeWidth={0.5} />
      <circle cx={plateX + 8} cy={plateY + plateH - 8} r={2} fill="#1A1A24" stroke="#3A3A45" strokeWidth={0.5} />
      <circle cx={plateX + plateW - 8} cy={plateY + plateH - 8} r={2} fill="#1A1A24" stroke="#3A3A45" strokeWidth={0.5} />

      {/* OFF label */}
      <text
        x={trackX - 2}
        y={handleCY + 1}
        textAnchor="end"
        fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"
        fontSize={7}
        fontWeight={600}
        fill={isOn ? "#555566" : "#888899"}
        dominantBaseline="middle"
      >
        OFF
      </text>

      {/* ON label */}
      <text
        x={trackX + trackW + 2}
        y={handleCY + 1}
        textAnchor="start"
        fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"
        fontSize={7}
        fontWeight={600}
        fill={isOn ? "#00D4AA" : "#555566"}
        dominantBaseline="middle"
      >
        ON
      </text>

      {/* Toggle track */}
      <rect
        x={trackX}
        y={trackY}
        width={trackW}
        height={trackH}
        rx={trackH / 2}
        ry={trackH / 2}
        fill={`url(#${trackGradientId})`}
        stroke="#2A2A35"
        strokeWidth={1.5}
      />

      {/* Active track highlight */}
      <motion.rect
        x={trackX}
        y={trackY}
        width={trackW}
        height={trackH}
        rx={trackH / 2}
        ry={trackH / 2}
        fill="none"
        stroke="#00D4AA"
        strokeWidth={1}
        initial={{ opacity: 0 }}
        animate={{ opacity: isOn ? 0.5 : 0 }}
        transition={{ duration: 0.3 }}
      />

      {/* Toggle handle (animated circle) */}
      <motion.circle
        cy={handleCY}
        r={handleR}
        fill={`url(#${handleGradientId})`}
        stroke={isOn ? "#00D4AA" : "#3A3A45"}
        strokeWidth={1.5}
        initial={false}
        animate={{
          cx: isOn ? handleOnX : handleOffX,
        }}
        transition={{
          type: "spring",
          stiffness: 500,
          damping: 30,
        }}
      />

      {/* Handle highlight (glossy spot) */}
      <motion.circle
        cy={handleCY - 3}
        r={3}
        fill="white"
        opacity={0.08}
        animate={{
          cx: isOn ? handleOnX - 2 : handleOffX - 2,
        }}
        transition={{
          type: "spring",
          stiffness: 500,
          damping: 30,
        }}
      />

      {/* LED indicator */}
      <motion.circle
        cx={plateX + plateW / 2}
        cy={plateY + 8}
        r={3}
        initial={false}
        animate={{
          fill: isOn ? "#00D4AA" : "#661111",
        }}
        transition={{ duration: 0.3 }}
      />
      <motion.circle
        cx={plateX + plateW / 2}
        cy={plateY + 8}
        r={5}
        fill="none"
        initial={false}
        animate={{
          stroke: isOn ? "#00D4AA" : "#661111",
          opacity: isOn ? 0.3 : 0.1,
        }}
        transition={{ duration: 0.3 }}
      />

      {/* Spark particles (shown briefly on toggle) */}
      <AnimatePresence>
        {showSparks && (
          <g>
            <Spark cx={isOn ? handleOnX + 8 : handleOffX - 8} cy={handleCY - 10} delay={0} />
            <Spark cx={isOn ? handleOnX + 12 : handleOffX - 12} cy={handleCY} delay={0.05} />
            <Spark cx={isOn ? handleOnX + 6 : handleOffX - 6} cy={handleCY + 8} delay={0.1} />
            <Spark cx={isOn ? handleOnX - 4 : handleOffX + 4} cy={handleCY - 12} delay={0.08} />
          </g>
        )}
      </AnimatePresence>
    </g>
  );
};

export default FlipSwitch;
