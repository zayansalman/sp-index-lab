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
      "that just 20 stocks explain 95.1% of the index's daily variance. The concentration curve shows a clear " +
      "'elbow' at around 18-20 stocks, where the marginal R-squared contribution of each additional stock drops " +
      "below 0.5%. Beyond that point, you're adding complexity without meaningful diversification. The remaining " +
      "480 stocks collectively contribute less than 5% of the index's movement -- they're effectively noise. " +
      "This isn't a temporary phenomenon; it's a structural feature of cap-weighted indices where the largest " +
      "companies dominate by design.",
  },
  {
    title: "Why The Baselines Stay",
    content:
      "The SP-20 Mirror and SP-20 Equal portfolios are the two honest baselines. Mirror keeps the cap-weighted " +
      "shape of the index driver set and reaches a 19.2% CAGR vs the S&P 500's 11.3%. Equal gives each of the " +
      "20 names a 5% allocation and reaches a 25.4% CAGR with a 1.16 Sharpe. They stay because they make the " +
      "concentration thesis testable without hiding behind optimizer complexity.",
  },
  {
    title: "Why One Alpha",
    content:
      "The public Alpha slot now belongs to the single strategy that earns it in walk-forward testing: max-Sharpe " +
      "optimization over the configured top-20 universe. It reaches a 29.2% CAGR, 1.17 Sharpe, and +13.9% Jensen " +
      "alpha. The weaker ML and hedged variants are deliberately excluded from the app and data export until they " +
      "can beat the retained strategy and the Equal baseline on the metrics that matter.",
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
