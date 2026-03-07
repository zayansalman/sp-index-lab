"use client";

/* ================================================================
   HoldingsTable -- Top-20 current holdings display
   Dark-themed table with weight bars, sorted by weight descending.
   ================================================================ */

import React from "react";
import { motion } from "framer-motion";
import type { Holding } from "@/lib/types";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface HoldingsTableProps {
  holdings: Holding[];
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const HoldingsTable: React.FC<HoldingsTableProps> = ({ holdings }) => {
  // Sort by weight descending
  const sorted = [...holdings].sort((a, b) => b.weight - a.weight);

  // Max weight for proportional bar width
  const maxWeight = sorted.length > 0 ? sorted[0].weight : 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="w-full overflow-x-auto"
    >
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[#1A1A24]">
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
              #
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
              Ticker
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
              Name
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
              Sector
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
              Weight (%)
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((holding, index) => (
            <tr
              key={holding.ticker}
              className={`border-b border-[#1A1A24] transition-colors hover:bg-bg-tertiary ${
                index % 2 === 0 ? "bg-bg-secondary" : "bg-bg-primary"
              }`}
            >
              {/* Rank */}
              <td className="px-3 py-2.5 text-xs tabular-nums text-text-muted">
                {index + 1}
              </td>

              {/* Ticker */}
              <td className="px-3 py-2.5 font-mono text-xs font-bold text-accent-primary">
                {holding.ticker}
              </td>

              {/* Company Name */}
              <td className="px-3 py-2.5 text-xs text-text-secondary">
                {holding.name}
              </td>

              {/* Sector */}
              <td className="px-3 py-2.5 text-xs text-text-muted">
                {holding.sector}
              </td>

              {/* Weight with proportional bar */}
              <td className="px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="min-w-[48px] text-right font-mono text-xs tabular-nums text-text-primary">
                    {(holding.weight * 100).toFixed(2)}%
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-bg-tertiary">
                    <div
                      className="h-full rounded-full bg-accent-primary transition-all duration-700"
                      style={{
                        width: `${(holding.weight / maxWeight) * 100}%`,
                        opacity: 0.6,
                      }}
                    />
                  </div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
};

export default HoldingsTable;
