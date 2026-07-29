/* ================================================================
   PlainEnglish -- explanatory copy for readers who do not already
   know the vocabulary.

   Built on native <details>/<summary>: keyboard operable, works on
   touch, survives no-JS, and is announced correctly by screen
   readers — none of which is true of a hover tooltip, which is what
   this replaces.
   ================================================================ */

import React from "react";
import { GLOSSARY, type GlossaryEntry } from "@/lib/glossary";

/* ──────────────────────────────────────────────────────────────
   Explainer -- an always-open prose block for a term that the
   reader must understand to read the section at all.
   ────────────────────────────────────────────────────────────── */

interface ExplainerProps {
  /** Key into GLOSSARY. */
  entry: keyof typeof GLOSSARY;
  /** Optional figures paragraph rendered after the definition. */
  children?: React.ReactNode;
}

export const Explainer: React.FC<ExplainerProps> = ({ entry, children }) => {
  const g: GlossaryEntry = GLOSSARY[entry];

  return (
    <section
      aria-label={`What ${g.term} means`}
      className="border-l-2 border-border-strong bg-surface px-5 py-4"
    >
      <h3 className="label-micro">In plain English: {g.term}</h3>

      <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink">
        {g.long}
      </p>

      {g.notThis && (
        <p className="mt-3 max-w-[68ch] text-sm leading-relaxed text-ink-secondary">
          <span className="font-semibold text-ink">What it does not mean.</span>{" "}
          {g.notThis}
        </p>
      )}

      {children && (
        <div className="mt-3 max-w-[68ch] text-sm leading-relaxed text-ink-secondary">
          {children}
        </div>
      )}
    </section>
  );
};

/* ──────────────────────────────────────────────────────────────
   GlossaryList -- collapsed definitions for a table's columns.
   Closed by default: a reader who knows the terms should not have
   to scroll past them, and one who doesn't must be able to find
   them without leaving the page.
   ────────────────────────────────────────────────────────────── */

interface GlossaryListProps {
  /** Keys into GLOSSARY, in the order the table presents them. */
  entries: readonly (keyof typeof GLOSSARY)[];
  /** Summary label. */
  label?: string;
}

export const GlossaryList: React.FC<GlossaryListProps> = ({
  entries,
  label = "What these terms mean",
}) => (
  <details className="group border-t">
    <summary className="cursor-pointer list-none px-1 py-3 text-sm font-medium text-ink-secondary transition-colors hover:text-ink">
      <span className="inline-block w-4 text-ink-muted transition-transform group-open:rotate-90">
        &rsaquo;
      </span>
      {label}
    </summary>

    <dl className="grid gap-x-8 gap-y-4 px-1 pb-5 pt-1 sm:grid-cols-2">
      {entries.map((key) => {
        const g = GLOSSARY[key];
        if (!g) return null;
        return (
          <div key={key}>
            <dt className="text-sm font-semibold text-ink">{g.term}</dt>
            <dd className="mt-0.5 max-w-[52ch] text-sm leading-relaxed text-ink-secondary">
              {g.short}
            </dd>
          </div>
        );
      })}
    </dl>
  </details>
);
