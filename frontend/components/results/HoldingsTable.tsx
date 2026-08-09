"use client";

/* ================================================================
   HoldingsTable -- Top-20 current holdings display
   Dark-themed table with weight bars, sorted by weight descending.
   ================================================================ */

import React from "react";
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
    <div
      className="w-full overflow-x-auto"
    >
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b">
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              #
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Ticker
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Name
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Sector
            </th>
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Weight (%)
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((holding, index) => (
            <tr
              key={holding.ticker}
              className={`border-b transition-colors hover:bg-surface-sunken ${
                index % 2 === 0 ? "bg-surface" : "bg-ground"
              }`}
            >
              {/* Rank */}
              <td className="px-3 py-2.5 text-xs tabular-nums text-ink-muted">
                {index + 1}
              </td>

              {/* Ticker */}
              <td className="px-3 py-2.5 font-mono text-xs font-bold text-accent">
                {holding.ticker}
              </td>

              {/* Company Name */}
              <td className="px-3 py-2.5 text-xs text-ink-secondary">
                {holding.name}
              </td>

              {/* Sector */}
              <td className="px-3 py-2.5 text-xs text-ink-muted">
                {holding.sector}
              </td>

              {/* Weight with proportional bar */}
              <td className="px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="min-w-[48px] text-right font-mono text-xs tabular-nums text-ink">
                    {(holding.weight * 100).toFixed(2)}%
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                    <div
                      className="h-full rounded-full bg-accent transition-all duration-700"
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
    </div>
  );
};

export default HoldingsTable;
