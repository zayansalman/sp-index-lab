import Link from "next/link";
import StatsPreview from "@/components/landing/StatsPreview";

/* ================================================================
   Landing page -- interim.

   Phase 3 replaces this with the fund-page masthead and the
   per-strategy routes. Until then it states the thesis and links
   through, without the cinematic dark treatment or the glowing
   "ENTER THE LAB" gate.
   ================================================================ */

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
      <p className="label-micro">Point-in-time universe · net of costs · benchmark ^SP500TR</p>

      <h1 className="mt-4 text-balance text-4xl font-normal leading-tight tracking-tight">
        The S&amp;P 500 is effectively a 20-stock index.
      </h1>

      <p className="mt-4 max-w-xl text-lg text-ink-secondary">
        Twenty point-in-time constituents explain most of its daily variance.
        Four portfolios built on that fact are shown side by side — and none is
        crowned, because none of the differences between them clears the
        significance hurdle this project holds itself to.
      </p>

      <div className="mt-10">
        <StatsPreview />
      </div>

      <div className="mt-10">
        <Link
          href="/lab"
          className="inline-flex items-center gap-2 border border-border-strong px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-surface"
        >
          View the analysis <span aria-hidden="true">&rarr;</span>
        </Link>
      </div>

      <p className="mt-16 text-xs text-ink-muted">
        A research artifact by Zayan Khan. It manages no capital and is not
        investment advice.
      </p>
    </main>
  );
}
