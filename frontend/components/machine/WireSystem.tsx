"use client";

/* ================================================================
   WireSystem -- All wires connecting machine components
   Maps wire IDs from constants.ts to SVG path definitions
   and renders each Wire with the correct active state.
   ================================================================ */

import React from "react";
import Wire from "./Wire";

interface WireSystemProps {
  /** Set of currently active wire IDs */
  activeWires: Set<string>;
}

/* ──────────────────────────────────────────────────────────────
   Wire Definitions
   Each entry maps a wire ID (matching STAGE_WIRES in constants.ts)
   to an SVG path and optional animation delay.

   Wire IDs from constants.ts:
     wire-power, wire-data-in, wire-concentration,
     wire-builder, wire-optimizer, wire-monitor, wire-output
   ────────────────────────────────────────────────────────────── */

interface WireDef {
  id: string;
  path: string;
  delay: number;
}

const WIRE_DEFS: WireDef[] = [
  {
    // Flip switch (400,80) -> Data Pipeline top (400,140)
    id: "wire-power",
    path: "M 400 80 L 400 140",
    delay: 0,
  },
  {
    // Data Pipeline bottom (400,250) -> Concentration top (400,310)
    id: "wire-data-in",
    path: "M 400 250 L 400 310",
    delay: 0.1,
  },
  {
    // Concentration bottom-left (350,420) -> Mirror top (235,480)
    // Curved path bending down-left
    id: "wire-concentration",
    path: "M 350 420 C 350 450, 235 450, 235 480",
    delay: 0.15,
  },
  {
    // Concentration bottom-right (450,420) -> Optimizer top (565,480)
    // Curved path bending down-right
    // Note: wire-builder maps to the mirror-builder component
    id: "wire-builder",
    path: "M 450 420 C 450 450, 565 450, 565 480",
    delay: 0.15,
  },
  {
    // This wire is the optimizer side (Concentration -> Alpha Optimizer)
    // But in constants.ts, "wire-optimizer" is used for the optimizing stage.
    // Mirror bottom (235,580) -> Monitor top-left (350,640)
    id: "wire-optimizer",
    path: "M 235 580 C 235 610, 350 610, 350 640",
    delay: 0.2,
  },
  {
    // Optimizer bottom (565,580) -> Monitor top-right (450,640)
    id: "wire-monitor",
    path: "M 565 580 C 565 610, 450 610, 450 640",
    delay: 0.2,
  },
  {
    // Output wire from Performance Monitor bottom
    // Simple downward stub indicating output
    id: "wire-output",
    path: "M 400 740 L 400 770",
    delay: 0.25,
  },
];

const WireSystem: React.FC<WireSystemProps> = ({ activeWires }) => {
  return (
    <g id="wire-system">
      {WIRE_DEFS.map((wire) => (
        <Wire
          key={wire.id}
          pathData={wire.path}
          isActive={activeWires.has(wire.id)}
          delay={wire.delay}
        />
      ))}
    </g>
  );
};

export default WireSystem;
