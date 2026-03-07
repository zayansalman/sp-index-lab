"use client";

import { motion } from "framer-motion";

/* ================================================================
   Hero
   Main hero section for the landing page.
   Displays the title with a green glow effect and a two-line tagline.
   ================================================================ */

export default function Hero() {
  return (
    <div className="flex flex-col items-center text-center">
      {/* ── Title ─────────────────────────────────────────────── */}
      <motion.h1
        className="font-heading text-5xl font-light tracking-wider text-text-primary md:text-7xl"
        style={{
          textShadow:
            "0 0 40px rgba(0, 212, 170, 0.15), 0 0 80px rgba(0, 212, 170, 0.08)",
        }}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        S&P INDEX LAB
      </motion.h1>

      {/* ── Tagline ───────────────────────────────────────────── */}
      <motion.div
        className="mt-6 flex flex-col gap-1"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut", delay: 0.3 }}
      >
        <p className="text-lg text-text-secondary md:text-xl">
          The S&P 500 is a 20-stock index.
        </p>
        <p className="text-lg text-text-secondary md:text-xl">
          Here&apos;s the machine that proves it.
        </p>
      </motion.div>
    </div>
  );
}
