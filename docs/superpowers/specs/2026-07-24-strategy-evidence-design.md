# Strategy Evidence — Design Spec

**Date:** 2026-07-24
**Branch:** `feat/strategy-evidence`
**Goal:** In the `/lab` web app, prove — per portfolio — (1) **how each works**, (2) its
**rebalance mechanism**, and (3) **honest evidence it beats the market**, all data-driven
(zero hardcoded numbers) and without regressing the honest-evaluation protocol.

## Non-negotiable constraints

1. **Numbers come from data, never hardcoded** in components or copy. Source of truth:
   `frontend/public/data/meta.json` (`headline`, `research`) + `performance_metrics.json`.
2. **Do not regress the honesty protocol.** The pre-registered holdout says **no single
   winner**: SP-N Alpha beat the S&P 500 out-of-sample (+10.5pp CAGR) but lost to SP-20
   Equal on Sharpe and breached the 1.2× drawdown cap → `passed:false`. "Beats the market"
   means *beat the S&P 500 benchmark, out-of-sample, net of costs, with disclosed caveats* —
   never a future guarantee. The excess-return **t-stat vs S&P 500 is 1.34** (not significant
   at 95%); this uncertainty must be shown.

## Key discovery (drives the plan)

The pipeline **already exports** everything needed for goals 2 & 3, but the frontend
transforms silently drop it:

- `meta.json → research.holdout` — full pre-registered result (window, `passed`, three
  `checks`, `deflated_sharpe` 0.962, `dev_trial_count` 14, `score` with `excess_cagr`,
  `excess_t_stat`, `beats`, `ann_turnover`, `cost_drag_bps`). **`transformMeta`
  (`useLabData.ts:86-111`) never reads `research`.** No type exists.
- `performance_metrics.json` — per-strategy `gross_cagr`, `gross_sharpe`,
  `annualized_turnover` (Mirror 0.83, Equal 1.15). **`transformSingleMetrics`
  (`useLabData.ts:199-219`) drops all three.**

So the highest-leverage step is **wiring**, not recomputation. **No backtest re-run** →
no number-shifting, no honesty risk.

## Integrity bug to fix (found in audit)

SP-N Alpha is described two contradictory ways. `tooltips.ts:89-92` correctly says
*dynamic-N concentration-elbow, equal-weight* (the retained spec `{engine:equal,
n_policy:elbow}`), but `ResultsPanel.tsx:146-149` "Why One Alpha" still says *"max-Sharpe
optimization over the PIT top-20"* — the **discredited MVO variant that beat neither
baseline**. Fix the copy to the retained elbow/equal description.

## Deliverables

### A. Data-layer wiring (no recompute)
1. `types.ts` — add `ResearchHoldout` type (+ nested `score`, `checks`) and a
   `research?: ResearchHoldout` field on `MetaData`; add `grossCagr?`, `grossSharpe?`,
   `annualizedTurnover?` to `PerformanceMetrics`; add `universeMethod`, `netOfCosts` to
   `HeadlineStats`/`MetaData`.
2. `useLabData.ts` — extend `transformMeta` to read `research`, `universe_method`,
   `headline.net_of_costs`; extend `transformSingleMetrics` to read `gross_cagr`,
   `gross_sharpe`, `annualized_turnover`.

### B. Per-strategy mechanics block (config-sourced, no magic numbers in JSON)
3. `export_frontend_data.py` — add a static-but-config-derived `mechanics` block per
   strategy (universe rule, weighting, rebalance freq, drift threshold, cost bps, N policy)
   read from `src/config.py`, written into `performance_metrics.json`. SP-N Alpha turnover
   is surfaced from the **holdout window** (`research.holdout.score.ann_turnover`, 1.99×),
   explicitly labeled out-of-sample; Mirror/Equal use their full-sample `annualized_turnover`.
   (Full-sample SP-N Alpha turnover persistence is a separate follow-up — out of scope here
   to avoid a backtest re-run and number drift.)

### C. Presentation components
4. `StrategyPlaybook.tsx` — one card per portfolio × three rows: **How it works** /
   **Rebalance** / **Track record** (net-of-costs CAGR·Sharpe·α·maxDD).
5. `HoldoutEvidence.tsx` — "The Proof": pre-registered contract, SP-N Alpha 2024→26 holdout
   (+10.5pp vs S&P 500), pass/fail scorecard (S&P 500 ✓ · Equal ✗ · DD-cap ✗), t-stat 1.34
   → "not yet significant", DSR 0.96 / 14 trials, verdict banner "no single winner".
6. Wire both into `ResultsPanel` (new sections, existing tokens/components). Fix the
   "Why One Alpha" copy bug.

## Testing / verification
- `npm run build` (type-check gate) + `npm run lint` green.
- `uv run pytest tests/test_export.py` green; add an assertion that `mechanics` +
  `research` survive the export round-trip.
- Browser check on `/lab`: playbook + proof render, numbers match `meta.json`, mobile width.
- Re-run integrity audit: zero hardcoded numbers, no "max-Sharpe" description of the
  retained alpha, all copy consistent with `meta.json`.

## Out of scope (explicitly deferred)
- Re-running the walk-forward backtest / persisting full-sample SP-N Alpha turnover.
- The Phase 18–27 "AI Alpha Hedge Fund" live-trading pivot.
- Phase 12 responsive/a11y polish beyond what these new components need.
