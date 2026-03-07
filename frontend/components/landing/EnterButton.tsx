"use client";

import { motion } from "framer-motion";
import Link from "next/link";

/* ================================================================
   EnterButton
   CTA button that navigates the user into the lab (/lab).
   Features a pulsing glow animation and hover effects.
   ================================================================ */

export default function EnterButton() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut", delay: 1.2 }}
    >
      <Link
        href="/lab"
        className="button-pulse inline-block rounded-lg border border-accent-primary/50 bg-transparent px-10 py-4 font-heading text-sm uppercase tracking-widest text-accent-primary transition-all duration-300 hover:border-accent-primary hover:bg-accent-primary/10"
      >
        Enter the Lab &rarr;
      </Link>
    </motion.div>
  );
}
