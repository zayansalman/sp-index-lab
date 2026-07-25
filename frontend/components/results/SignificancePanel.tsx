"use client";

/**
 * SignificancePanel — the honest reading of the comparison table.
 *
 * A performance table invites the eye to rank columns. With ~10 years of one
 * highly-correlated mega-cap universe, those gaps are mostly noise: the
 * strategies share the same ~20 names, so their active returns are small
 * relative to their tracking error. This panel states that outright rather
 * than leaving a bold number to imply an edge that the data cannot support.
 *
 * The hurdle is |t| > 3.0, not the conventional 1.96 — Harvey, Liu & Zhu
 * (2016) show that after extensive search across strategy variants the usual
 * threshold is meaningless. This project has logged 14 dev trials, so the
 * stricter bar is the correct one.
 */


import type { ActiveReturnStats, MatchedWindowComparison } from "@/lib/types";

/** Comparisons worth showing. Reversed pairs are omitted: "S&P 500 vs Mirror"
 *  is just the negation of "Mirror vs S&P 500" and adds no information. */
const COMPARISONS: { strategy: string; reference: string; label: string }[] = [
  { strategy: "sp20_mirror", reference: "sp500", label: "SP-20 Mirror vs S&P 500" },
  { strategy: "sp20_equal", reference: "sp500", label: "SP-20 Equal vs S&P 500" },
  { strategy: "spn_alpha", reference: "sp500", label: "SP-N Alpha vs S&P 500" },
  { strategy: "sp20_mirror", reference: "sp20_equal", label: "SP-20 Mirror vs SP-20 Equal" },
  { strategy: "spn_alpha", reference: "sp20_equal", label: "SP-N Alpha vs SP-20 Equal" },
  { strategy: "spn_alpha", reference: "sp20_mirror", label: "SP-N Alpha vs SP-20 Mirror" },
];

function formatYears(years: number | null): string {
  if (years === null) return "—";
  return years >= 1000 ? "1000+" : `~${Math.round(years)}`;
}

interface SignificancePanelProps {
  matched: MatchedWindowComparison;
}

export function SignificancePanel({ matched }: SignificancePanelProps) {
  const rows = COMPARISONS.map((comparison) => ({
    ...comparison,
    stats: matched.significance[comparison.strategy]?.[comparison.reference],
  })).filter(
    (row): row is typeof row & { stats: ActiveReturnStats } => !!row.stats,
  );

  if (rows.length === 0) return null;

  const significantCount = rows.filter((row) => row.stats.significant).length;

  return (
    <div
      className="mt-6 overflow-x-auto rounded-xl border bg-surface p-6"
    >
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold tracking-wide text-ink-secondary">
          Is any of that difference real?
        </h3>
        <span className="font-mono text-[11px] text-ink-muted">
          hurdle |t| &gt; {matched.tHurdle.toFixed(1)} · {matched.windowYears.toFixed(1)}y of data
        </span>
      </div>

      <p className="mb-4 max-w-3xl text-xs leading-relaxed text-ink-secondary">
        {significantCount === 0 ? (
          <>
            No. <span className="text-ink">Not one</span> of these
            comparisons clears the significance hurdle — every ranking in the
            table above is statistically indistinguishable from luck. The
            strategies hold overlapping slices of the same ~20 mega-caps, so
            their active returns are small next to their tracking error, and{" "}
            {matched.windowYears.toFixed(1)} years is nowhere near enough data
            to tell them apart.
          </>
        ) : (
          <>
            {significantCount} of {rows.length} comparisons clear the hurdle.
            The rest are statistically indistinguishable from luck.
          </>
        )}
      </p>

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b">
            <th className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Comparison
            </th>
            <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Active Return
            </th>
            <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Tracking Error
            </th>
            <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Info Ratio
            </th>
            <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-ink-muted">
              t-stat
            </th>
            <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Years to Prove
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={`${row.strategy}-${row.reference}`}
              className={`border-b ${
                idx % 2 === 0 ? "bg-surface" : "bg-ground"
              }`}
            >
              <td className="px-3 py-2.5 text-xs text-ink-secondary">
                {row.label}
              </td>
              <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums text-ink">
                {row.stats.annualisedActiveReturn >= 0 ? "+" : ""}
                {(row.stats.annualisedActiveReturn * 100).toFixed(2)}%
              </td>
              <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums text-ink">
                {(row.stats.trackingError * 100).toFixed(2)}%
              </td>
              <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums text-ink">
                {row.stats.informationRatio.toFixed(2)}
              </td>
              <td
                className={`px-3 py-2.5 text-right font-mono text-xs tabular-nums ${
                  row.stats.significant
                    ? "font-bold text-accent"
                    : "text-ink-muted"
                }`}
              >
                {row.stats.tStat >= 0 ? "+" : ""}
                {row.stats.tStat.toFixed(2)}
              </td>
              <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums text-ink-muted">
                {formatYears(row.stats.yearsForHurdle)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-3 max-w-3xl text-[11px] leading-relaxed text-ink-muted">
        Measured on daily active returns over the matched window (
        {matched.windowStart} → {matched.windowEnd}). The information ratio here
        is arithmetic (mean daily active return over its own volatility) so that
        t = IR × √years holds exactly; the table above reports the canonical
        CAGR-excess-over-tracking-error version, so the two differ slightly.
        &ldquo;Years to Prove&rdquo;
        is how long this information ratio would need to run to reach |t| &gt;{" "}
        {matched.tHurdle.toFixed(1)}, since t = IR × √years; it is shown as
        &ldquo;&mdash;&rdquo; where the strategy trails its reference, because no
        amount of data would make a negative edge significant. The
        hurdle follows Harvey, Liu &amp; Zhu (2016), who show the conventional
        t &gt; 1.96 is invalid once many variants have been searched over. This
        project has logged 14 development trials, so the stricter bar applies.
      </p>
    </div>
  );
}
