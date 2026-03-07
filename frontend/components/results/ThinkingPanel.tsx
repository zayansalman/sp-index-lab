"use client";

/* ================================================================
   ThinkingPanel -- Collapsible methodology/rationale sections
   Uses Framer Motion AnimatePresence for smooth expand/collapse
   with rotating chevron indicators.
   ================================================================ */

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface ThinkingSection {
  title: string;
  content: string;
}

interface ThinkingPanelProps {
  sections?: ThinkingSection[];
}

/* ──────────────────────────────────────────────────────────────
   Default content
   ────────────────────────────────────────────────────────────── */

const DEFAULT_SECTIONS: ThinkingSection[] = [
  {
    title: "Why 20 Stocks?",
    content:
      "The S&P 500 is marketed as diversification across 500 companies, but our OLS regression analysis reveals " +
      "that just 20 stocks explain 94.9% of the index's daily variance. The concentration curve shows a clear " +
      "'elbow' at around 18-20 stocks, where the marginal R-squared contribution of each additional stock drops " +
      "below 0.5%. Beyond that point, you're adding complexity without meaningful diversification. The remaining " +
      "480 stocks collectively contribute less than 5% of the index's movement -- they're effectively noise. " +
      "This isn't a temporary phenomenon; it's a structural feature of cap-weighted indices where the largest " +
      "companies dominate by design.",
  },
  {
    title: "Why This Beats the S&P 500",
    content:
      "The SP-20 Mirror achieves a 15.3% CAGR vs the S&P 500's 11.3% -- a +4.0% alpha -- with a comparable " +
      "risk profile (Sharpe of 0.68 vs 0.54). The outperformance comes from two sources: (1) concentration " +
      "amplifies the returns of the stocks that actually drive the index, removing the 'dead weight' of 480 " +
      "low-impact holdings; and (2) the equal-weighted variant further reduces mega-cap concentration risk by " +
      "giving each of the 20 stocks an equal 5% allocation, capturing more of the broader large-cap premium. " +
      "The key insight is that you're not taking more risk -- the tracking error is modest because these 20 " +
      "stocks ARE the index for all practical purposes.",
  },
  {
    title: "The Path to Further Alpha",
    content:
      "The static mirror index proves the thesis, but real alpha comes from dynamic adaptation. Our planned " +
      "optimizer uses three layers: (1) Hierarchical Risk Parity (HRP) for robust weight allocation that avoids " +
      "the instability of mean-variance optimization; (2) a LightGBM factor model that scores stocks on momentum, " +
      "value, quality, and volatility factors to identify the optimal N stocks (10-30) for current conditions; " +
      "and (3) a Hidden Markov Model regime detector that shifts between concentrated (trending markets) and " +
      "diversified (volatile/uncertain markets) postures. The goal: dynamically select both WHICH stocks and " +
      "HOW MANY to hold, adapting to market conditions in real time.",
  },
];

/* ──────────────────────────────────────────────────────────────
   Chevron Icon
   ────────────────────────────────────────────────────────────── */

const ChevronIcon: React.FC<{ isOpen: boolean }> = ({ isOpen }) => (
  <motion.svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    animate={{ rotate: isOpen ? 180 : 0 }}
    transition={{ duration: 0.25, ease: "easeInOut" }}
    className="shrink-0"
  >
    <path
      d="M4 6L8 10L12 6"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </motion.svg>
);

/* ──────────────────────────────────────────────────────────────
   Single collapsible section
   ────────────────────────────────────────────────────────────── */

const CollapsibleSection: React.FC<{
  section: ThinkingSection;
  index: number;
}> = ({ section, index }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-30px" }}
      transition={{ duration: 0.4, delay: index * 0.1, ease: "easeOut" }}
      className="overflow-hidden rounded-xl border border-[#1A1A24] bg-bg-secondary"
    >
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-bg-tertiary"
      >
        <span className="text-sm font-semibold text-text-primary">
          {section.title}
        </span>
        <span className="text-text-muted">
          <ChevronIcon isOpen={isOpen} />
        </span>
      </button>

      {/* Expandable body */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-[#1A1A24] px-5 py-4">
              <p className="text-sm leading-relaxed text-text-secondary">
                {section.content}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

/* ──────────────────────────────────────────────────────────────
   ThinkingPanel Component
   ────────────────────────────────────────────────────────────── */

const ThinkingPanel: React.FC<ThinkingPanelProps> = ({
  sections = DEFAULT_SECTIONS,
}) => {
  return (
    <div className="flex flex-col gap-3">
      {sections.map((section, index) => (
        <CollapsibleSection
          key={section.title}
          section={section}
          index={index}
        />
      ))}
    </div>
  );
};

export default ThinkingPanel;
