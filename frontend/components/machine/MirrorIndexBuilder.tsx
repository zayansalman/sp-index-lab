"use client";

/* ================================================================
   MirrorIndexBuilder -- Interlocking gears icon
   When active, the gears rotate in opposite directions.
   ================================================================ */

import React from "react";
import { motion } from "framer-motion";
import ComponentNode from "./ComponentNode";

interface MirrorIndexBuilderProps {
  isActive: boolean;
}

/* ── Gear shape helper ────────────────────────────────────── */
const GearPath: React.FC<{
  cx: number;
  cy: number;
  outerR: number;
  innerR: number;
  teeth: number;
}> = ({ cx, cy, outerR, innerR, teeth }) => {
  // Build a gear path with specified teeth count
  const points: string[] = [];
  const step = (Math.PI * 2) / teeth;
  const halfStep = step / 2;
  const toothDepth = (outerR - innerR) * 0.5;

  for (let i = 0; i < teeth; i++) {
    const angle = i * step - Math.PI / 2;
    // Outer tooth tip
    const ox1 = cx + Math.cos(angle - halfStep * 0.3) * outerR;
    const oy1 = cy + Math.sin(angle - halfStep * 0.3) * outerR;
    const ox2 = cx + Math.cos(angle + halfStep * 0.3) * outerR;
    const oy2 = cy + Math.sin(angle + halfStep * 0.3) * outerR;
    // Inner valley
    const ix1 = cx + Math.cos(angle + halfStep * 0.7) * (outerR - toothDepth);
    const iy1 = cy + Math.sin(angle + halfStep * 0.7) * (outerR - toothDepth);
    const ix2 = cx + Math.cos(angle + halfStep * 1.3) * (outerR - toothDepth);
    const iy2 = cy + Math.sin(angle + halfStep * 1.3) * (outerR - toothDepth);

    if (i === 0) {
      points.push(`M ${ox1} ${oy1}`);
    } else {
      points.push(`L ${ox1} ${oy1}`);
    }
    points.push(`L ${ox2} ${oy2}`);
    points.push(`L ${ix1} ${iy1}`);
    points.push(`L ${ix2} ${iy2}`);
  }
  points.push("Z");

  return (
    <path
      d={points.join(" ")}
      fill="none"
      stroke="#00D4AA"
      strokeWidth={1.2}
      opacity={0.85}
    />
  );
};

/* ── Interlocking gears icon ──────────────────────────────── */
const GearsIcon: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <g>
    {/* Left gear (rotates clockwise) */}
    <motion.g
      animate={isActive ? { rotate: 360 } : { rotate: 0 }}
      transition={
        isActive
          ? { duration: 4, repeat: Infinity, ease: "linear" }
          : { duration: 0.5 }
      }
      style={{ originX: "-8px", originY: "0px" }}
    >
      <GearPath cx={-8} cy={0} outerR={13} innerR={8} teeth={8} />
      <circle cx={-8} cy={0} r={3} fill="none" stroke="#00D4AA" strokeWidth={1} opacity={0.6} />
    </motion.g>

    {/* Right gear (rotates counter-clockwise) */}
    <motion.g
      animate={isActive ? { rotate: -360 } : { rotate: 0 }}
      transition={
        isActive
          ? { duration: 4, repeat: Infinity, ease: "linear" }
          : { duration: 0.5 }
      }
      style={{ originX: "10px", originY: "2px" }}
    >
      <GearPath cx={10} cy={2} outerR={10} innerR={6} teeth={6} />
      <circle cx={10} cy={2} r={2.5} fill="none" stroke="#00D4AA" strokeWidth={1} opacity={0.6} />
    </motion.g>
  </g>
);

const MirrorIndexBuilder: React.FC<MirrorIndexBuilderProps> = ({
  isActive,
}) => {
  return (
    <ComponentNode
      id="mirror-builder"
      x={100}
      y={480}
      width={270}
      height={100}
      label="MIRROR INDEX BUILDER"
      sublabel="Cap-Weighted Portfolio"
      isActive={isActive}
      icon={<GearsIcon isActive={isActive} />}
    />
  );
};

export default MirrorIndexBuilder;
