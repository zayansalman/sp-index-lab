"use client";

/* ================================================================
   DataPipeline -- Server-rack / database icon machine component
   When active, shows scrolling ticker symbols.
   ================================================================ */

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import ComponentNode from "./ComponentNode";

interface DataPipelineProps {
  isActive: boolean;
}

/* ── Server rack icon (3 stacked bars with indicator dots) ──── */
const ServerIcon: React.FC = () => (
  <g>
    {/* Three horizontal server bars */}
    {[-12, 0, 12].map((dy, i) => (
      <g key={i}>
        <rect
          x={-20}
          y={dy - 4}
          width={40}
          height={8}
          rx={2}
          fill="none"
          stroke="#00D4AA"
          strokeWidth={1.2}
          opacity={0.8}
        />
        {/* Status dots */}
        <circle cx={14} cy={dy} r={1.5} fill="#00D4AA" opacity={0.9} />
        <circle cx={10} cy={dy} r={1.5} fill="#00D4AA" opacity={0.5} />
        {/* Horizontal lines inside bar */}
        <line
          x1={-15}
          y1={dy}
          x2={5}
          y2={dy}
          stroke="#00D4AA"
          strokeWidth={0.6}
          opacity={0.3}
        />
      </g>
    ))}
  </g>
);

/* ── Scrolling tickers animation ────────────────────────────── */
const TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK.B", "JPM"];

const ScrollingTickers: React.FC<{ isActive: boolean; x: number; y: number; width: number }> = ({
  isActive,
  x,
  y,
  width,
}) => (
  <AnimatePresence>
    {isActive && (
      <g>
        {/* Clip rect so tickers stay inside the component */}
        <defs>
          <clipPath id="ticker-clip">
            <rect x={x + 10} y={y} width={width - 20} height={20} />
          </clipPath>
        </defs>
        <g clipPath="url(#ticker-clip)">
          {TICKERS.map((ticker, i) => (
            <motion.text
              key={ticker}
              x={x + width + i * 55}
              y={y + 14}
              fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, monospace"
              fontSize={9}
              fill="#00D4AA"
              opacity={0.6}
              initial={{ x: x + width + i * 55 }}
              animate={{ x: x - 60 + i * 55 - TICKERS.length * 55 }}
              transition={{
                duration: 8,
                repeat: Infinity,
                ease: "linear",
                delay: 0,
              }}
            >
              {ticker}
            </motion.text>
          ))}
        </g>
      </g>
    )}
  </AnimatePresence>
);

const DataPipeline: React.FC<DataPipelineProps> = ({ isActive }) => {
  const x = 250;
  const y = 140;
  const width = 300;
  const height = 110;

  return (
    <ComponentNode
      id="data-pipeline"
      x={x}
      y={y}
      width={width}
      height={height}
      label="DATA PIPELINE"
      sublabel="Market Data Ingestion"
      isActive={isActive}
      icon={<ServerIcon />}
    >
      <ScrollingTickers isActive={isActive} x={x} y={y + height - 22} width={width} />
    </ComponentNode>
  );
};

export default DataPipeline;
