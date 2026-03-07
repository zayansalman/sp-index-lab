"use client";

/* ================================================================
   ComponentNode -- Base SVG group for a machine component box
   Renders a rounded rectangle with icon, label, sublabel,
   and a LightBulb indicator. Glows when active.
   ================================================================ */

import React, { useId } from "react";
import { motion } from "framer-motion";
import LightBulb from "./LightBulb";

interface ComponentNodeProps {
  /** Unique identifier matching the machine state IDs */
  id: string;
  /** Top-left X coordinate */
  x: number;
  /** Top-left Y coordinate */
  y: number;
  /** Width of the component box */
  width: number;
  /** Height of the component box */
  height: number;
  /** Primary label text */
  label: string;
  /** Secondary label text */
  sublabel?: string;
  /** Whether this component is currently active */
  isActive: boolean;
  /** SVG content rendered as the icon */
  icon: React.ReactNode;
  /** Additional SVG children (animations, extras) */
  children?: React.ReactNode;
}

const ComponentNode: React.FC<ComponentNodeProps> = ({
  id,
  x,
  y,
  width,
  height,
  label,
  sublabel,
  isActive,
  icon,
  children,
}) => {
  const filterId = useId();
  const glowFilterId = `glow-node-${filterId}`;
  const innerGlowId = `inner-glow-${filterId}`;

  const centerX = x + width / 2;
  const iconCenterY = y + height * 0.35;
  const labelY = y + height * 0.65;
  const sublabelY = y + height * 0.82;

  return (
    <g id={id} data-component={id}>
      {/* Filter definitions */}
      <defs>
        {/* Active border glow */}
        <filter id={glowFilterId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Inner glow gradient */}
        <radialGradient id={innerGlowId} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#00D4AA" stopOpacity={0.06} />
          <stop offset="100%" stopColor="#00D4AA" stopOpacity={0} />
        </radialGradient>
      </defs>

      {/* Background rect */}
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={12}
        ry={12}
        fill="#111118"
      />

      {/* Inner glow overlay (visible when active) */}
      <motion.rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={12}
        ry={12}
        fill={`url(#${innerGlowId})`}
        initial={{ opacity: 0 }}
        animate={{ opacity: isActive ? 1 : 0 }}
        transition={{ duration: 0.5 }}
      />

      {/* Animated border */}
      <motion.rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={12}
        ry={12}
        fill="none"
        strokeWidth={1.5}
        initial={{ stroke: "#2A2A35" }}
        animate={{
          stroke: isActive ? "#00D4AA" : "#2A2A35",
        }}
        transition={{ duration: 0.5 }}
        filter={isActive ? `url(#${glowFilterId})` : undefined}
      />

      {/* Icon container -- translated to center */}
      <g
        transform={`translate(${centerX}, ${iconCenterY})`}
        opacity={isActive ? 1 : 0.5}
      >
        {icon}
      </g>

      {/* Primary label */}
      <text
        x={centerX}
        y={labelY}
        textAnchor="middle"
        fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"
        fontSize={12}
        fontWeight={600}
        letterSpacing="0.05em"
        fill="#F0F0F0"
      >
        {label}
      </text>

      {/* Sublabel */}
      {sublabel && (
        <text
          x={centerX}
          y={sublabelY}
          textAnchor="middle"
          fontFamily="ui-sans-serif, system-ui, sans-serif"
          fontSize={10}
          fill="#888899"
        >
          {sublabel}
        </text>
      )}

      {/* LightBulb indicator at top-right */}
      <LightBulb
        isActive={isActive}
        cx={x + width - 20}
        cy={y + 16}
        size={6}
      />

      {/* Extra children (custom animations, etc.) */}
      {children}
    </g>
  );
};

export default ComponentNode;
