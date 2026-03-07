"use client";

/* ================================================================
   AnimatedCounter -- Framer Motion animated number counter
   Counts from 0 to the target value when the component scrolls
   into the viewport. Animates only once.
   ================================================================ */

import React, { useEffect, useRef, useState } from "react";
import {
  useMotionValue,
  useSpring,
  useInView,
  useTransform,
  motion,
} from "framer-motion";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface AnimatedCounterProps {
  /** Target numeric value to count up to */
  value: number;
  /** Duration of the animation in seconds (default: 1.5) */
  duration?: number;
  /** Formatting function applied to the displayed number */
  format?: (n: number) => string;
  /** Additional CSS classes */
  className?: string;
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const AnimatedCounter: React.FC<AnimatedCounterProps> = ({
  value,
  duration = 1.5,
  format = (n) => n.toFixed(2),
  className = "",
}) => {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  const [hasAnimated, setHasAnimated] = useState(false);

  const motionValue = useMotionValue(0);
  const springValue = useSpring(motionValue, {
    duration: duration * 1000,
    bounce: 0,
  });

  const display = useTransform(springValue, (current) => format(current));
  const [displayText, setDisplayText] = useState(format(0));

  // Start counting when visible (only once)
  useEffect(() => {
    if (isInView && !hasAnimated) {
      motionValue.set(value);
      setHasAnimated(true);
    }
  }, [isInView, hasAnimated, motionValue, value]);

  // Subscribe to display changes
  useEffect(() => {
    const unsubscribe = display.on("change", (latest) => {
      setDisplayText(latest);
    });
    return unsubscribe;
  }, [display]);

  return (
    <motion.span ref={ref} className={className}>
      {displayText}
    </motion.span>
  );
};

export default AnimatedCounter;
