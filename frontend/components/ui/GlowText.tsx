"use client";

/* ================================================================
   GlowText -- Text element with a subtle green glow effect
   ================================================================ */

import React from "react";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface GlowTextProps {
  children: React.ReactNode;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p" | "span";
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const GlowText: React.FC<GlowTextProps> = ({
  children,
  className = "",
  as: Tag = "span",
}) => {
  return (
    <Tag
      className={className}
      style={{
        textShadow:
          "0 0 40px rgba(0, 212, 170, 0.15), 0 0 80px rgba(0, 212, 170, 0.08)",
      }}
    >
      {children}
    </Tag>
  );
};

export default GlowText;
