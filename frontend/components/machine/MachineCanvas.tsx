"use client";

/* ================================================================
   MachineCanvas -- Main SVG assembly for the S&P Index Lab machine
   Composes all machine components, wires, and the flip switch
   into a single responsive SVG canvas with HTML tooltip overlays.
   ================================================================ */

import React, { useMemo, useRef, useState, useEffect } from "react";
import type { MachineStage } from "@/lib/types";
import FlipSwitch from "./FlipSwitch";
import WireSystem from "./WireSystem";
import DataPipeline from "./DataPipeline";
import ConcentrationAnalyzer from "./ConcentrationAnalyzer";
import MirrorIndexBuilder from "./MirrorIndexBuilder";
import AlphaOptimizer from "./AlphaOptimizer";
import PerformanceMonitor from "./PerformanceMonitor";
import Tooltip from "@/components/ui/Tooltip";
import { tooltips } from "@/lib/tooltips";

interface MachineCanvasProps {
  /** Whether the machine power switch is ON */
  isOn: boolean;
  /** Current stage of the machine animation */
  stage: MachineStage;
  /** Set of currently active component IDs */
  activeComponents: Set<string>;
  /** Set of currently active wire IDs */
  activeWires: Set<string>;
  /** Callback when the flip switch is toggled */
  onToggle: () => void;
}

/* ── Component positions in SVG viewBox coords (x, y, w, h) ── */
const COMPONENT_RECTS: Record<
  string,
  { x: number; y: number; w: number; h: number }
> = {
  "data-pipeline": { x: 250, y: 140, w: 300, h: 110 },
  "concentration-analyzer": { x: 250, y: 310, w: 300, h: 110 },
  "mirror-builder": { x: 100, y: 480, w: 270, h: 100 },
  "alpha-optimizer": { x: 430, y: 480, w: 270, h: 100 },
  "performance-monitor": { x: 250, y: 640, w: 300, h: 100 },
};

/* Pipeline order used for the mobile stage list (below md). */
const STAGE_IDS = Object.keys(COMPONENT_RECTS);

const MachineCanvas: React.FC<MachineCanvasProps> = ({
  isOn,
  activeComponents,
  activeWires,
  onToggle,
}) => {
  const wireSet = useMemo(() => activeWires, [activeWires]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  // Track SVG-to-pixel scale for tooltip overlay positioning
  useEffect(() => {
    const updateScale = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.offsetWidth;
        setScale(containerWidth / 800); // viewBox width is 800
      }
    };
    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  return (
    <>
      {/* ── Mobile fallback (below md) ─────────────────────
          The 800×780 SVG machine overflows and its labels become
          illegible on small screens, so below md we hide it and show
          an accessible power toggle plus a vertical stage list. */}
      <div className="mx-auto w-full max-w-md md:hidden">
        <button
          type="button"
          role="switch"
          aria-checked={isOn}
          aria-label={isOn ? "Stop analysis engine" : "Start analysis engine"}
          onClick={onToggle}
          className="mb-6 flex w-full items-center justify-between rounded-xl border border-wire-inactive bg-bg-secondary px-4 py-3 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent-primary"
        >
          <span className="heading-font text-xs uppercase tracking-widest text-text-secondary">
            Power
          </span>
          <span
            className={`text-sm font-semibold ${
              isOn ? "text-accent-primary" : "text-text-muted"
            }`}
          >
            {isOn ? "● ON" : "○ OFF"}
          </span>
        </button>

        <ol className="space-y-2">
          {STAGE_IDS.map((id, i) => {
            const tip = tooltips[id];
            if (!tip) return null;
            const active = activeComponents.has(id);
            return (
              <li
                key={id}
                className={`rounded-lg border p-3 transition-colors ${
                  active
                    ? "border-accent-primary/40 bg-accent-primary/5"
                    : "border-wire-inactive bg-bg-secondary"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`flex h-5 w-5 flex-none items-center justify-center rounded-full text-[10px] font-bold ${
                      active
                        ? "bg-accent-primary/20 text-accent-primary"
                        : "bg-bg-tertiary text-text-muted"
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span
                    className={`text-sm font-semibold ${
                      active ? "text-accent-primary" : "text-text-primary"
                    }`}
                  >
                    {tip.title}
                  </span>
                </div>
                <p className="mt-1 pl-[30px] text-xs leading-relaxed text-text-secondary">
                  {tip.subtitle}
                </p>
              </li>
            );
          })}
        </ol>
      </div>

      {/* ── Desktop machine (md and up) ───────────────────── */}
      <div
        ref={containerRef}
        className="hidden md:block"
        style={{
          width: "100%",
          maxWidth: 800,
          margin: "0 auto",
          position: "relative",
        }}
      >
      {/* ── SVG Machine ──────────────────────────────────── */}
      <svg
        viewBox="0 0 800 780"
        width="100%"
        height="100%"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="Analysis engine diagram: a data pipeline feeds a concentration analyzer, which drives a mirror-index builder and an alpha optimizer, both feeding a performance monitor."
        style={{ overflow: "visible", display: "block" }}
      >
        <defs>
          <filter
            id="machine-glow"
            x="-30%"
            y="-30%"
            width="160%"
            height="160%"
          >
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <style>{`
            @keyframes electricFlow {
              from { stroke-dashoffset: 20; }
              to { stroke-dashoffset: 0; }
            }
          `}</style>
        </defs>

        <WireSystem activeWires={wireSet} />
        <FlipSwitch isOn={isOn} onToggle={onToggle} />

        <DataPipeline isActive={activeComponents.has("data-pipeline")} />
        <ConcentrationAnalyzer
          isActive={activeComponents.has("concentration-analyzer")}
        />
        <MirrorIndexBuilder
          isActive={activeComponents.has("mirror-builder")}
        />
        <AlphaOptimizer
          isActive={activeComponents.has("alpha-optimizer")}
        />
        <PerformanceMonitor
          isActive={activeComponents.has("performance-monitor")}
        />
      </svg>

      {/* ── HTML Tooltip Overlay ──────────────────────────── */}
      {/* Invisible hotspots positioned over each SVG component */}
      {Object.entries(COMPONENT_RECTS).map(([id, rect]) => {
        const tip = tooltips[id];
        if (!tip) return null;

        return (
          <Tooltip key={id} content={tip} side="right" delayDuration={200}>
            <div
              role="button"
              tabIndex={0}
              aria-label={tip.title}
              className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
              style={{
                position: "absolute",
                left: rect.x * scale,
                top: rect.y * scale,
                width: rect.w * scale,
                height: rect.h * scale,
                cursor: "pointer",
              }}
            />
          </Tooltip>
        );
      })}
      </div>
    </>
  );
};

export default MachineCanvas;
