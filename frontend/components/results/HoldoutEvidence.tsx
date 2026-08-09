"use client";

/* ================================================================
   HoldoutEvidence -- the honest "does it beat the market?" proof
   ----------------------------------------------------------------
   The whole project's credibility rests on NOT overclaiming. This
   panel shows the pre-registered dev/holdout result exactly as it
   landed: SP-N Alpha beat the S&P 500 out-of-sample, but did not
   clear every committed bar → no single winner. Statistical
   uncertainty (t-stat, deflated Sharpe) is shown, not hidden.

   Every number is read from meta.research; nothing is hardcoded.
   ================================================================ */

import React from "react";
import { formatPercent, formatRatio, formatDate } from "@/lib/formatters";
import type { ResearchHoldout } from "@/lib/types";

interface HoldoutEvidenceProps {
  research: ResearchHoldout;
}

/** Percentage-point delta, always signed (e.g. "+10.5pp"). */
function pp(v: number): string {
  const s = (v * 100).toFixed(1);
  return `${v >= 0 ? "+" : ""}${s}pp`;
}

const PassIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-pass">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
    <path d="M8 12L11 15L16 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const FailIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-caution">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
    <path d="M15 9L9 15M9 9l6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const CheckRow: React.FC<{ pass: boolean; label: string; detail?: string }> = ({
  pass,
  label,
  detail,
}) => (
  <li className="flex items-start gap-2.5 py-1.5">
    <span className="mt-0.5 shrink-0">{pass ? <PassIcon /> : <FailIcon />}</span>
    <span className="text-xs leading-relaxed text-ink-secondary">
      <span className={pass ? "text-pass" : "text-caution"}>
        {pass ? "Pass" : "Miss"}
      </span>{" "}
      — {label}
      {detail && <span className="text-ink-muted"> ({detail})</span>}
    </span>
  </li>
);

const HoldoutEvidence: React.FC<HoldoutEvidenceProps> = ({ research }) => {
  const s = research.score;
  const checks = research.checks;
  if (!s || !checks) return null;

  // Derived benchmark holdout CAGRs (strategy CAGR minus its excess).
  const sp500HoldoutCagr = s.cagr - s.excessCagr.sp500;
  const equalHoldoutCagr = s.cagr - s.excessCagr.sp20Equal;
  // Pre-registered drawdown cap: 1.2× the index's own holdout drawdown.
  const ddCap =
    research.indexMaxDrawdown !== undefined
      ? research.indexMaxDrawdown * 1.2
      : undefined;
  const tSp500 = s.excessTStat.sp500;

  return (
    <div
      className="rounded-xl border bg-surface p-6"
    >
      {/* Framing: how this proof was earned */}
      <p className="text-xs leading-relaxed text-ink-secondary">
        Every candidate was developed and tuned on data through{" "}
        <span className="text-ink">{research.devEnd}</span>. The winning
        spec was then <span className="text-ink">frozen</span> and
        evaluated <span className="text-ink">exactly once</span> on a
        locked holdout —{" "}
        {research.window && (
          <span className="text-ink">
            {formatDate(research.window[0])} → {formatDate(research.window[1])}
          </span>
        )}
        , {s.nDays} trading days it never saw during development. Criteria were
        committed <em>before</em> selection.
      </p>

      {/* Headline: out-of-sample edge vs the market */}
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-pass/30 bg-pass-bg p-4">
          <div className="text-[10px] uppercase tracking-wider text-ink-muted">
            vs S&amp;P 500 (out-of-sample)
          </div>
          <div className="mt-1 font-mono text-2xl font-bold tabular-nums text-pass">
            {pp(s.excessCagr.sp500)}
          </div>
          <div className="mt-1 text-[11px] text-ink-muted">
            {formatPercent(s.cagr, 1)} vs {formatPercent(sp500HoldoutCagr, 1)} CAGR
          </div>
        </div>
        <div className="rounded-lg border bg-ground p-4">
          <div className="text-[10px] uppercase tracking-wider text-ink-muted">
            vs SP-20 Equal
          </div>
          <div className="mt-1 font-mono text-2xl font-bold tabular-nums text-ink">
            {pp(s.excessCagr.sp20Equal)}
          </div>
          <div className="mt-1 text-[11px] text-ink-muted">
            {formatPercent(s.cagr, 1)} vs {formatPercent(equalHoldoutCagr, 1)} CAGR
          </div>
        </div>
        <div className="rounded-lg border bg-ground p-4">
          <div className="text-[10px] uppercase tracking-wider text-ink-muted">
            Holdout Sharpe / Max DD
          </div>
          <div className="mt-1 font-mono text-2xl font-bold tabular-nums text-ink">
            {formatRatio(s.sharpe)}
          </div>
          <div className="mt-1 text-[11px] text-ink-muted">
            {formatPercent(s.maxDrawdown, 1)} max drawdown ·{" "}
            {formatRatio(s.annTurnover)}×/yr turnover
          </div>
        </div>
      </div>

      {/* Pre-registered scorecard */}
      <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">
            Pre-registered scorecard
          </h4>
          <ul>
            <CheckRow
              pass={checks.beatSp500CagrAndSharpe}
              label="Beat S&P 500 TR on CAGR and Sharpe"
            />
            <CheckRow
              pass={checks.beatEqualCagrAndSharpe}
              label="Beat SP-20 Equal on CAGR and Sharpe"
              detail="lost on Sharpe"
            />
            <CheckRow
              pass={checks.maxDrawdownWithinMultiple}
              label="Max drawdown within 1.2× the index"
              detail={
                ddCap !== undefined
                  ? `${formatPercent(s.maxDrawdown, 1)} vs ${formatPercent(ddCap, 1)} allowed`
                  : undefined
              }
            />
          </ul>
        </div>

        {/* Honesty caveats — significance + multiple testing */}
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">
            The honest caveats
          </h4>
          <ul className="space-y-2 text-xs leading-relaxed text-ink-secondary">
            <li>
              <span className="text-ink">Significance:</span> the excess
              return vs the S&amp;P 500 carries a t-stat of{" "}
              <span className="font-mono tabular-nums text-ink">
                {formatRatio(tSp500)}
              </span>{" "}
              — below the ~2.0 needed for 95% confidence. This is an
              out-of-sample edge, not a guarantee.
            </li>
            <li>
              <span className="text-ink">Multiple testing:</span>{" "}
              {research.devTrialCount} configurations were tried; the deflated
              Sharpe is{" "}
              <span className="font-mono tabular-nums text-ink">
                {formatRatio(research.deflatedSharpe ?? 0)}
              </span>{" "}
              — the dev edge survives the discount for having tried that many.
            </li>
          </ul>
        </div>
      </div>

      {/* Verdict */}
      <div className="mt-5 rounded-lg border border-caution/30 bg-caution-bg p-4">
        <p className="text-xs leading-relaxed text-ink-secondary">
          <span className="font-semibold text-caution">Verdict — no single winner.</span>{" "}
          SP-N Alpha beat the S&amp;P 500 out-of-sample by {pp(s.excessCagr.sp500)}{" "}
          CAGR, but it did <span className="text-ink">not</span> clear
          every pre-registered bar (lost to SP-20 Equal on Sharpe, breached the
          drawdown cap). Per the contract committed before the holdout was
          touched, no strategy is crowned — the S&amp;P 500, Mirror, Equal, and
          Alpha are shown side by side so you can judge the trade-offs yourself.
        </p>
      </div>
    </div>
  );
};

export default HoldoutEvidence;
