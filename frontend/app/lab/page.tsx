import Link from "next/link";
import ResultsPanel from "@/components/results/ResultsPanel";

/* ================================================================
   Lab route -- analytics surface.

   The machine metaphor that used to gate this page is gone: data
   renders on load rather than after an 8.7s animation behind a
   switch that was invisible to assistive technology.

   Phase 3 replaces this route with the per-strategy fund pages
   under /funds/[strategy]; until then it renders the results
   directly so nothing is unreachable in the interim.
   ================================================================ */

export default function LabPage() {
  return (
    <main className="min-h-screen bg-ground">
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="label-micro transition-colors hover:text-ink"
          >
            &larr; Back
          </Link>
          <span className="label-micro">S&amp;P Index Lab</span>
          <div className="w-16" aria-hidden="true" />
        </div>
      </header>

      <ResultsPanel visible />
    </main>
  );
}
