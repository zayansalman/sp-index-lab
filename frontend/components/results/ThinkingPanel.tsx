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

/*
  Qualitative fallback only — every specific number lives in the exported
  data. ResultsPanel passes data-driven sections; these render only if it
  doesn't.
*/
const DEFAULT_SECTIONS: ThinkingSection[] = [
  {
    title: "Why 20 Stocks?",
    content:
      "The S&P 500 is marketed as diversification across 500 companies, but regressing the index's daily " +
      "returns on its largest constituents shows that roughly 20 stocks explain the overwhelming majority " +
      "of its variance. The concentration curve shows a clear 'elbow' around 18-20 stocks, where each " +
      "additional stock stops adding meaningful explanatory power. The selection is point-in-time: each " +
      "rolling window uses the stocks that were actually the largest at that moment, not today's winners " +
      "projected backwards.",
  },
  {
    title: "Why The Baselines Stay",
    content:
      "The SP-20 Mirror and SP-20 Equal portfolios are the two honest baselines. Mirror holds the " +
      "point-in-time top-20 at cap weights, rebalanced monthly; Equal gives each of the 20 names an equal " +
      "allocation. Both are net of transaction costs and benchmarked against the S&P 500 total-return " +
      "index. They stay because they make the concentration thesis testable without hiding behind " +
      "optimizer complexity.",
  },
  {
    title: "The Self-Adjusting Alpha",
    content:
      "SP-N Alpha adapts how many stocks it holds. Each month it reads the concentration 'elbow' from " +
      "trailing data and equal-weights however many names still add explanatory power — as few as 10 when " +
      "the index is top-heavy, up to 30 when breadth widens. It was chosen on a 2014–2023 development " +
      "window (14 strategies tried; deflated Sharpe 0.96, so the edge survives multiple-testing) and never " +
      "saw the 2024–present holdout until one pre-registered evaluation. On that holdout it beat the S&P 500 " +
      "by a wide margin but did not clear every pre-committed bar against SP-20 Equal — so no strategy is " +
      "crowned. All four are shown side by side, net of costs, for you to judge.",
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
