"use client";

import { motion, type Variants } from "framer-motion";

/* ================================================================
   StatsPreview
   Three metric preview cards displayed in a horizontal row.
   Shows R-squared, CAGR, and Alpha stats with staggered animations.
   ================================================================ */

const stats = [
  { value: "94.9%", label: "R-squared at 20 stocks" },
  { value: "15.3%", label: "Mirror Index CAGR" },
  { value: "+4.0%", label: "Alpha vs S&P 500" },
] as const;

const containerVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.2,
      delayChildren: 0.6,
    },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" as const },
  },
};

export default function StatsPreview() {
  return (
    <motion.div
      className="flex w-full flex-col items-center justify-center gap-4 px-4 sm:flex-row sm:gap-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {stats.map((stat) => (
        <motion.div
          key={stat.label}
          className="group w-full rounded-xl border border-[#1A1A24] bg-bg-secondary px-8 py-6 transition-colors duration-300 hover:border-accent-primary/30 sm:w-auto"
          variants={cardVariants}
        >
          <p className="text-3xl font-bold text-accent-primary md:text-4xl">
            {stat.value}
          </p>
          <p className="mt-1 text-sm text-text-secondary">{stat.label}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}
