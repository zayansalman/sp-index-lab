"use client";

/* ================================================================
   Tooltip -- Radix-based rich tooltip with dark theme
   Renders title, subtitle, description, thinking rationale,
   and a key insight for each machine component.
   ================================================================ */

import React from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import type { ComponentTooltip } from "@/lib/types";

/* ──────────────────────────────────────────────────────────────
   Props
   ────────────────────────────────────────────────────────────── */

interface TooltipProps {
  /** The trigger element that activates the tooltip on hover */
  children: React.ReactNode;
  /** Structured tooltip content matching ComponentTooltip shape */
  content: ComponentTooltip;
  /** Preferred placement side */
  side?: "top" | "right" | "bottom" | "left";
  /** Delay before showing tooltip in ms */
  delayDuration?: number;
}

/* ──────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────── */

const Tooltip: React.FC<TooltipProps> = ({
  children,
  content,
  side = "top",
  delayDuration = 300,
}) => {
  return (
    <RadixTooltip.Provider delayDuration={delayDuration}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>

        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={8}
            className="z-[9999] max-w-[380px] rounded-lg border border-[#2A2A35] bg-[#111118] px-4 py-3 shadow-xl animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95"
          >
            {/* Title */}
            <p className="text-sm font-bold text-accent-primary">
              {content.title}
            </p>

            {/* Subtitle */}
            <p className="mt-0.5 text-xs italic text-text-muted">
              {content.subtitle}
            </p>

            {/* Description */}
            <p className="mt-2 text-sm leading-relaxed text-text-secondary">
              {content.description}
            </p>

            {/* The Thinking -- separated by a top border */}
            <div className="mt-3 border-t border-[#2A2A35] pt-3">
              <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-accent-secondary">
                <span aria-hidden="true">&#x1F4A1;</span>
                <span>The Thinking</span>
              </p>
              <p className="text-xs leading-relaxed text-text-secondary">
                {content.thinking}
              </p>
            </div>

            {/* Key Insight */}
            <p className="mt-3 text-xs font-bold text-accent-primary">
              <span className="mr-1" aria-hidden="true">
                &rarr;
              </span>
              {content.keyInsight}
            </p>

            <RadixTooltip.Arrow className="fill-[#2A2A35]" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
};

export default Tooltip;
