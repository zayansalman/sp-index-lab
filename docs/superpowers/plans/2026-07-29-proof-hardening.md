# Proof Hardening (Tier A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the replication evidence layer — investable-basket tracking quality, the R² ladder, a cardinality-constrained tracking frontier, honest N exports, and the doc corrections — with zero registry cost.

**Architecture:** All new analytics live in `src/proof/` (descriptive, benchmark-relative, tracking-only) and flow through `scripts/export_frontend_data.py` into the existing static-JSON bridge. Nothing touches `src/research/`, `data/research/`, or any strategy selection path. Frontend consumes new JSON blocks as optional fields (same pattern as `matched_window`).

**Tech Stack:** Python 3.11 / pandas / numpy / scipy (SLSQP), pytest; Next.js 16 + strict TypeScript on the existing light-institutional UI (tokens in `globals.css`, chart colours ONLY via `frontend/lib/chartTheme.ts` — a CI guard rejects hardcoded colour literals).

## Global Constraints

- **Zero registry cost:** nothing calls `src/research/registry.py::run_experiment`, writes `data/research/*`, or emits CAGR/Sharpe/excess-return from new code. `data/research/trials.jsonl` must be byte-identical at the end.
- **No hardcoded numbers** in components, copy, or docs — every figure computed at export time.
- **Baselines untouched:** SP-20 Mirror/Equal stay at `top_n=20`.
- **Committed JSON untouched:** local export runs use `--out-dir` (never commit regenerated `frontend/public/data/*.json`; the daily cron owns it).
- **Branch:** `feat/proof-hardening` off `develop`; push to `develop` via PR when green. Never touch `main`.
- **Gates before every push:** `uv run ruff check src scripts tests` · `rm -rf .mypy_cache && uv run mypy src scripts tests` · `uv run pytest tests/ -q` · `cd frontend && npm run lint && npm run build`.
- Python: type hints on all signatures, Google docstrings, `logging` not `print`, vectorized pandas, financial values rounded 4dp, imports stdlib→third-party→local.
- Frontend: all data typed in `lib/types.ts`; snake→camel in `hooks/useLabData.ts`; no colour literals in components (use tokens / `chartTheme.ts`).

---

### Task 1: `rolling_replication_quality` — TE and replication R² of investable baskets

**Files:**
- Modify: `src/proof/concentration.py` (append after `build_mirror_index`)
- Test: `tests/test_proof.py` (append)

**Interfaces:**
- Consumes: `build_mirror_index(stock_prices, top_n, weighting, *, universe_fn, start, ...) -> pd.DataFrame` (existing; returns columns `date, nav, nav_gross, turnover`), `TRADING_DAYS_PER_YEAR` from `src.config`.
- Produces: `rolling_replication_quality(stock_prices, benchmark, *, universe_fn, top_n_values, weightings, window_days=252, step_days=21, start=None) -> dict` with the exact shape shown in Step 3. Task 2 exports this dict verbatim.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_proof.py`; reuse that file's existing synthetic-price fixtures/conventions — read its top first and match them):

```python
def _synth_panel(n_days=800, n_stocks=30, seed=7):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    market = rng.normal(0.0004, 0.01, n_days)
    prices = {}
    for i in range(n_stocks):
        beta = 0.8 + 0.4 * rng.random()
        idio = rng.normal(0, 0.008, n_days)
        prices[f"S{i:02d}"] = 100 * np.cumprod(1 + beta * market + idio)
    panel = pd.DataFrame(prices, index=dates)
    bench = pd.Series(1000 * np.cumprod(1 + market), index=dates, name="bench")
    return panel, bench


def _rank_by_trailing_price(prices: pd.DataFrame, as_of, n: int) -> list[str]:
    hist = prices.loc[prices.index <= as_of]
    return list(hist.tail(63).mean().nlargest(n).index)


def test_replication_quality_shape_and_ceiling():
    panel, bench = _synth_panel()
    out = rolling_replication_quality(
        panel, bench, universe_fn=_rank_by_trailing_price,
        top_n_values=[10, 20], weightings=["cap", "equal"],
    )
    assert set(out) == {"method", "window_days", "step_days", "ladder", "by_n"}
    keys = {(r["n"], r["weighting"]) for r in out["by_n"]}
    assert keys == {(10, "cap"), (10, "equal"), (20, "cap"), (20, "equal")}
    for row in out["by_n"]:
        # replication R² is a fraction; TE annualised and positive
        assert 0.0 < row["replication_r2"] <= 1.0
        assert row["tracking_error"] > 0.0
        assert row["te_min"] <= row["tracking_error"] <= row["te_max"]
    # more names must not track worse on this clean synthetic panel
    r10 = next(r for r in out["by_n"] if r["n"] == 10 and r["weighting"] == "cap")
    r20 = next(r for r in out["by_n"] if r["n"] == 20 and r["weighting"] == "cap")
    assert r20["tracking_error"] <= r10["tracking_error"] + 0.02


def test_replication_ladder_below_ols_ceiling():
    """Investable replication R² can never beat hindsight OLS R² (D2)."""
    panel, bench = _synth_panel()
    rets = panel.pct_change().dropna()
    bench_rets = bench.pct_change().dropna()
    roll = rolling_concentration(rets, bench_rets, _rank_by_trailing_price,
                                 top_n_values=[20])
    ols_r2 = roll[roll["n_stocks"] == 20]["r_squared"].mean()
    out = rolling_replication_quality(
        panel, bench, universe_fn=_rank_by_trailing_price,
        top_n_values=[20], weightings=["equal"],
    )
    inv = out["ladder"]["investable_equal"]
    assert inv <= ols_r2 + 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_proof.py -k replication -v`
Expected: FAIL / ERROR with `NameError: rolling_replication_quality is not defined` (fix imports at the top of the test file: `from src.proof.concentration import rolling_concentration, rolling_replication_quality` — match the file's existing import style).

- [ ] **Step 3: Implement** (append to `src/proof/concentration.py`):

```python
def rolling_replication_quality(
    stock_prices: pd.DataFrame,
    benchmark: pd.Series,
    *,
    universe_fn: RankingFn,
    top_n_values: list[int] | None = None,
    weightings: list[str] | None = None,
    window_days: int = 252,
    step_days: int = 21,
    start: pd.Timestamp | str | None = None,
) -> dict:
    """Tracking quality of INVESTABLE top-N baskets, per rolling window.

    The OLS numbers from ``rolling_concentration`` are an explanatory
    ceiling: hindsight-fitted, sign-unconstrained coefficients no portfolio
    can hold. This measures what an implementable basket — the exact
    construction ``build_mirror_index`` trades, net of costs — actually
    achieves: annualised tracking error vs the benchmark and the
    replication R² it implies (1 − TE²/σ²_index), window by window.

    Returns a JSON-ready dict:
        {"method", "window_days", "step_days",
         "ladder": {"investable_cap": float, "investable_equal": float},
         "by_n": [{"n", "weighting", "tracking_error", "replication_r2",
                   "te_min", "te_max", "n_windows"}]}
    ``ladder`` holds the N=20 replication R² per weighting (the headline
    companions to the OLS ceiling); ``by_n`` covers the full grid.
    """
    top_n_values = top_n_values or DEFAULT_TOP_N_VALUES
    weightings = weightings or ["cap", "equal"]

    bench_rets = benchmark.pct_change().dropna()
    by_n: list[dict] = []
    ladder: dict[str, float] = {}

    for weighting in weightings:
        for n in top_n_values:
            mirror = build_mirror_index(
                stock_prices, top_n=n, weighting=weighting,
                universe_fn=universe_fn, start=start,
            )
            nav = pd.Series(
                mirror["nav"].values,
                index=pd.to_datetime(mirror["date"]),
            )
            active = (nav.pct_change() - bench_rets).dropna()
            if len(active) < window_days:
                logger.warning(
                    "replication_quality: %s N=%d has %d obs < window %d — skipped",
                    weighting, n, len(active), window_days,
                )
                continue

            te_windows: list[float] = []
            r2_windows: list[float] = []
            for lo in range(0, len(active) - window_days + 1, step_days):
                chunk = active.iloc[lo:lo + window_days]
                bench_chunk = bench_rets.loc[chunk.index]
                te = float(chunk.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
                sigma = float(bench_chunk.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
                te_windows.append(te)
                r2_windows.append(max(0.0, 1.0 - (te / sigma) ** 2) if sigma > 0 else 0.0)

            row = {
                "n": n,
                "weighting": weighting,
                "tracking_error": round(float(np.mean(te_windows)), 4),
                "replication_r2": round(float(np.mean(r2_windows)), 4),
                "te_min": round(float(np.min(te_windows)), 4),
                "te_max": round(float(np.max(te_windows)), 4),
                "n_windows": len(te_windows),
            }
            by_n.append(row)
            if n == 20:
                ladder[f"investable_{weighting}"] = row["replication_r2"]

    return {
        "method": "pit_investable_baskets_rolling",
        "window_days": window_days,
        "step_days": step_days,
        "ladder": ladder,
        "by_n": by_n,
    }
```

Note: `DEFAULT_TOP_N_VALUES` — the module already defines the grid `[5, 10, 15, 20, 25, 30, 40, 50]` (used by `rolling_concentration`); reuse whatever name it has there (grep `top_n_values` defaults in the module). If it's inlined, hoist it to a module constant `DEFAULT_TOP_N_VALUES` and use it in both places.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_proof.py -k replication -v` → PASS (2 tests).
Also run the whole file: `uv run pytest tests/test_proof.py -q` → no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/proof/concentration.py tests/test_proof.py
git commit -m "feat(proof): rolling replication quality of investable top-N baskets"
```

---

### Task 2: Export the `replication` block (R² ladder included)

**Files:**
- Modify: `scripts/export_frontend_data.py` — function `export_variance_decomposition` and its call site in `main()`
- Test: `tests/test_export.py` (append)

**Interfaces:**
- Consumes: Task 1's `rolling_replication_quality` dict; existing `_write_json`, `_clean_dict`, captured-payload test fixture in `tests/test_export.py`.
- Produces: `variance_decomposition.json` gains a top-level `"replication"` key: `{...Task-1 dict, "ladder": {"ols_ceiling": <r_squared_at_20>, "investable_cap": ..., "investable_equal": ...}}`. Task 7 (frontend types) consumes exactly this shape.

- [ ] **Step 1: Write the failing test** (append to `tests/test_export.py`):

```python
def test_variance_decomposition_carries_replication_block(
    captured: dict[str, Any],
) -> None:
    rolling = pd.DataFrame({
        "n_stocks": [20, 20], "r_squared": [0.95, 0.96],
        "window_start": pd.to_datetime(["2020-01-01", "2020-02-01"]),
        "window_end": pd.to_datetime(["2020-12-31", "2021-01-31"]),
    })
    replication = {
        "method": "pit_investable_baskets_rolling",
        "window_days": 252, "step_days": 21,
        "ladder": {"investable_cap": 0.91, "investable_equal": 0.94},
        "by_n": [{"n": 20, "weighting": "equal", "tracking_error": 0.04,
                  "replication_r2": 0.94, "te_min": 0.03, "te_max": 0.06,
                  "n_windows": 100}],
    }
    export.export_variance_decomposition(rolling, replication=replication)

    payload = captured["variance_decomposition.json"]
    rep = payload["replication"]
    # export must stamp the OLS ceiling next to the investable numbers
    assert rep["ladder"]["ols_ceiling"] == pytest.approx(0.955)
    assert rep["ladder"]["investable_equal"] == 0.94
    assert rep["ladder"]["investable_equal"] <= rep["ladder"]["ols_ceiling"]


def test_variance_decomposition_replication_optional(
    captured: dict[str, Any],
) -> None:
    """Absent replication data must not break the existing export."""
    rolling = pd.DataFrame({
        "n_stocks": [20], "r_squared": [0.95],
        "window_start": pd.to_datetime(["2020-01-01"]),
        "window_end": pd.to_datetime(["2020-12-31"]),
    })
    export.export_variance_decomposition(rolling)
    assert "replication" not in captured["variance_decomposition.json"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export.py -k variance_decomposition -v`
Expected: FAIL — `export_variance_decomposition() got an unexpected keyword argument 'replication'`.

- [ ] **Step 3: Implement.** In `scripts/export_frontend_data.py`, change the signature of `export_variance_decomposition(rolling)` to `export_variance_decomposition(rolling: pd.DataFrame, replication: dict | None = None)`. Inside, before `_write_json`, add:

```python
    if replication:
        ladder = dict(replication.get("ladder", {}))
        # The hindsight-OLS mean at N=20 — the ceiling the investable
        # numbers sit under. Same aggregation as the headline.
        at20 = rolling[rolling["n_stocks"] == 20]
        if not at20.empty:
            ladder["ols_ceiling"] = round(float(at20["r_squared"].mean()), 6)
        payload["replication"] = _clean_dict({**replication, "ladder": ladder})
```

In `main()`, after `rolling = rolling_concentration(...)`, add the call and thread it through:

```python
    logger.info("Computing investable replication quality...")
    replication = rolling_replication_quality(
        stock_prices, benchmark_display,
        universe_fn=universe_fn, start=inception,
    )
```
and change the existing `export_variance_decomposition(rolling)` call to `export_variance_decomposition(rolling, replication=replication)`. Import `rolling_replication_quality` in the existing `from src.proof.concentration import (...)` block.

- [ ] **Step 4: Run tests + full-file**

`uv run pytest tests/test_export.py -q` → all pass.

- [ ] **Step 5: End-to-end verification with `--out-dir`** (data exists in this checkout):

```bash
uv run python scripts/export_frontend_data.py --out-dir /tmp/proof-hardening-check
python3 -c "
import json; d=json.load(open('/tmp/proof-hardening-check/variance_decomposition.json'))
r=d['replication']; l=r['ladder']
assert l['investable_equal'] <= l['ols_ceiling'], l
assert l['investable_cap'] <= l['ols_ceiling'], l
print('ladder:', l); print('rows:', len(r['by_n']))"
git status --short frontend/public/data/   # MUST be empty
```

- [ ] **Step 6: Commit**

```bash
git add scripts/export_frontend_data.py tests/test_export.py
git commit -m "feat(export): replication block with R-squared ladder (ceiling vs investable)"
```

---

### Task 3: `src/proof/replication.py` — simplex-LS solver + tracking frontier (+ L1-inertness and guard tests)

**Files:**
- Create: `src/proof/replication.py`
- Create: `tests/test_replication.py`

**Interfaces:**
- Consumes: nothing project-specific beyond `src.config.TRADING_DAYS_PER_YEAR`.
- Produces: `solve_simplex_ls(X: np.ndarray, y: np.ndarray, l1_penalty: float = 0.0) -> np.ndarray` (dense long-only budget-constrained LS) and `tracking_frontier(stock_prices, benchmark, *, k_values, train_days=252, test_days=21) -> dict`. Task 4 exports the frontier dict.

- [ ] **Step 1: Write the failing tests** (`tests/test_replication.py`):

```python
"""Tests for the descriptive replication module.

This module is PROOF infrastructure, not a strategy: it computes tracking
quantities only. The guard test at the bottom enforces that boundary.
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from src.proof import replication
from src.proof.replication import solve_simplex_ls, tracking_frontier


def _tracking_problem(t=252, p=40, seed=3):
    rng = np.random.default_rng(seed)
    X = rng.normal(0.0004, 0.01, (t, p))
    w_true = np.zeros(p); w_true[:8] = 1 / 8
    y = X @ w_true + rng.normal(0, 0.0005, t)
    return X, y


def test_simplex_ls_is_feasible_and_tracks():
    X, y = _tracking_problem()
    w = solve_simplex_ls(X, y)
    assert w.shape == (X.shape[1],)
    assert np.all(w >= -1e-9)
    assert np.isclose(w.sum(), 1.0, atol=1e-6)
    # must beat naive 1/p tracking on a problem with an 8-name generator
    resid_opt = np.std(y - X @ w)
    resid_naive = np.std(y - X @ (np.ones(X.shape[1]) / X.shape[1]))
    assert resid_opt < resid_naive


def test_l1_penalty_is_inert_under_simplex_constraints():
    """Brodie et al. (PNAS 2009, eq. 5): with w >= 0 and sum(w) = 1 the
    L1 norm is identically 1, so the penalty cannot change the argmin.
    This test exists so LASSO-for-sparsity can never be reintroduced here
    by assertion — it was measured inert (max |dw| ~ 7e-4) on real data."""
    X, y = _tracking_problem()
    w0 = solve_simplex_ls(X, y, l1_penalty=0.0)
    w100 = solve_simplex_ls(X, y, l1_penalty=100.0)
    assert np.max(np.abs(w0 - w100)) < 1e-3


def test_tracking_frontier_shape_and_monotonicity():
    rng = np.random.default_rng(11)
    dates = pd.bdate_range("2020-01-01", periods=600)
    market = rng.normal(0.0004, 0.01, len(dates))
    panel = pd.DataFrame(
        {f"S{i:02d}": 100 * np.cumprod(
            1 + (0.8 + 0.4 * rng.random()) * market
            + rng.normal(0, 0.008, len(dates)))
         for i in range(40)}, index=dates)
    bench = pd.Series(1000 * np.cumprod(1 + market), index=dates)

    out = tracking_frontier(panel, bench, k_values=[5, 20])
    assert set(out) == {"method", "train_days", "test_days", "frontier",
                       "n_fallback_windows"}
    by_k = {r["k"]: r for r in out["frontier"]}
    assert set(by_k) == {5, 20}
    for r in by_k.values():
        assert r["te_oos"] > 0
        assert 0 <= r["replication_r2_oos"] <= 1
        assert 0 <= r["mean_monthly_churn"] <= 1
        assert r["n_windows"] > 5
    # more names -> tighter tracking, with slack for noise
    assert by_k[20]["te_oos"] <= by_k[5]["te_oos"] + 0.01


def test_module_emits_no_performance_metrics():
    """Guard (spec D4): this module must stay descriptive. If you need
    return metrics from these weights you are building a STRATEGY — that
    is Tier B: registry, pre-registration, trial logging. Not here."""
    src = inspect.getsource(replication).lower()
    for forbidden in ("sharpe", "cagr", "sortino", "excess_return"):
        assert forbidden not in src, f"replication.py must not compute {forbidden}"
```

- [ ] **Step 2: Run to verify failure**

`uv run pytest tests/test_replication.py -v` → ERROR: `ModuleNotFoundError: No module named 'src.proof.replication'`.

- [ ] **Step 3: Implement** (`src/proof/replication.py`):

```python
"""Cardinality-constrained index replication — descriptive proof only.

Answers one question: how tightly can k long-only, fully-invested names
track the benchmark, out of sample? The formulation is simplex-constrained
least squares (min ||y - Xw||^2, w >= 0, sum w = 1) with cardinality via a
two-pass heuristic: dense solve, keep the top-k support, re-solve on it
(Benidis, Feng & Palomar, IEEE TSP 2018).

This module is PROOF infrastructure, not a strategy. It computes tracking
error and replication R-squared only — never return-based performance. A
raced version of these weights would be a new strategy candidate and must
go through src/research/registry.py with pre-registered criteria instead.
tests/test_replication.py enforces this boundary.

Why no LASSO: under w >= 0 and sum(w) = 1 the L1 norm is identically 1, so
an L1 penalty is a constant and selects nothing (Brodie et al., PNAS 2009,
eq. 5; verified numerically on this data — max weight change 7e-4 across
lambda 0..100). The l1_penalty parameter below exists solely so the
regression test can prove that inertness.
"""

import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.config import TRADING_DAYS_PER_YEAR

logger = logging.getLogger(__name__)

DEFAULT_K_VALUES = [10, 15, 20, 25, 30, 40]


def solve_simplex_ls(
    X: np.ndarray,
    y: np.ndarray,
    l1_penalty: float = 0.0,
) -> np.ndarray:
    """Long-only, fully-invested least-squares tracking weights.

    Minimises 0.5·||y − Xw||² (+ l1_penalty·||w||₁, provably inert — see
    module docstring) subject to w ≥ 0 and Σw = 1.
    """
    t, p = X.shape
    w0 = np.full(p, 1.0 / p)
    xtx = X.T @ X
    xty = X.T @ y

    def objective(w: np.ndarray) -> float:
        resid = X @ w - y
        return 0.5 * float(resid @ resid) + l1_penalty * float(np.abs(w).sum())

    def gradient(w: np.ndarray) -> np.ndarray:
        return xtx @ w - xty + l1_penalty * np.sign(w)

    result = minimize(
        objective, w0, jac=gradient, method="SLSQP",
        bounds=[(0.0, 1.0)] * p,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        raise RuntimeError(f"simplex LS failed: {result.message}")
    w = np.clip(result.x, 0.0, None)
    return w / w.sum()


def _cardinality_weights(X: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    """Two-pass: dense solve, restrict to top-k support, re-solve."""
    dense = solve_simplex_ls(X, y)
    if int((dense > 1e-6).sum()) <= k:
        return dense
    support = np.argsort(dense)[-k:]
    sparse = np.zeros_like(dense)
    sparse[support] = solve_simplex_ls(X[:, support], y)
    return sparse


def tracking_frontier(
    stock_prices: pd.DataFrame,
    benchmark: pd.Series,
    *,
    k_values: list[int] | None = None,
    train_days: int = 252,
    test_days: int = 21,
) -> dict:
    """Walk-forward OOS tracking quality per cardinality k.

    For each step: fit weights on the trailing ``train_days`` of returns
    (eligible names = full non-NaN history in the window), hold them for
    the next ``test_days``, record realised daily active returns. Pooled
    across all steps this yields the out-of-sample tracking error, the
    replication R² it implies, monthly selection churn, and the largest
    weight — per k. Returns a JSON-ready dict.
    """
    k_values = k_values or DEFAULT_K_VALUES
    returns = stock_prices.pct_change(fill_method=None)
    bench_rets = benchmark.pct_change().dropna()
    common = returns.index.intersection(bench_rets.index)
    returns, bench_rets = returns.loc[common], bench_rets.loc[common]

    frontier: list[dict] = []
    n_fallback = 0
    starts = range(train_days, len(common) - test_days, test_days)

    for k in k_values:
        active_oos: list[pd.Series] = []
        bench_oos: list[pd.Series] = []
        churns: list[float] = []
        max_ws: list[float] = []
        prev_support: set[str] | None = None

        for lo in starts:
            train = returns.iloc[lo - train_days:lo]
            eligible = train.columns[train.notna().all()]
            if len(eligible) <= k:
                continue
            X = train[eligible].to_numpy()
            y = bench_rets.iloc[lo - train_days:lo].to_numpy()
            try:
                w = _cardinality_weights(X, y, k)
            except RuntimeError:
                # cap-proxy-free fallback: equal weight the k largest
                # trailing-mean-return names; counted, never silent
                n_fallback += 1
                w = np.zeros(len(eligible))
                top = np.argsort(np.nanmean(X, axis=0))[-k:]
                w[top] = 1.0 / k
            weights = pd.Series(w, index=eligible)
            support = set(weights[weights > 1e-6].index)
            if prev_support is not None and support and prev_support:
                churns.append(
                    len(support.symmetric_difference(prev_support))
                    / (2 * max(len(support), 1))
                )
            prev_support = support
            max_ws.append(float(weights.max()))

            test = returns.iloc[lo:lo + test_days]
            port = (test[eligible].fillna(0.0) @ weights.values)
            bench_chunk = bench_rets.iloc[lo:lo + test_days]
            active_oos.append(port - bench_chunk)
            bench_oos.append(bench_chunk)

        if not active_oos:
            continue
        pooled = pd.concat(active_oos)
        pooled_bench = pd.concat(bench_oos)
        te = float(pooled.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        sigma = float(pooled_bench.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        frontier.append({
            "k": k,
            "te_oos": round(te, 4),
            "replication_r2_oos": round(max(0.0, 1 - (te / sigma) ** 2), 4)
            if sigma > 0 else 0.0,
            "mean_monthly_churn": round(float(np.mean(churns)), 4) if churns else 0.0,
            "max_weight": round(float(np.mean(max_ws)), 4),
            "n_windows": len(active_oos),
        })

    return {
        "method": "simplex_ls_topk_walkforward",
        "train_days": train_days,
        "test_days": test_days,
        "frontier": frontier,
        "n_fallback_windows": n_fallback,
    }
```

- [ ] **Step 4: Run tests**

`uv run pytest tests/test_replication.py -v` → 4 PASS. (The frontier test runs ~16 solves of a 40-var problem; if it exceeds ~60s, reduce the test panel to 500 days — do not mark it `@slow`.)

- [ ] **Step 5: Commit**

```bash
git add src/proof/replication.py tests/test_replication.py
git commit -m "feat(proof): simplex-LS tracking frontier with L1-inertness and no-performance guards"
```

---

### Task 4: Export the `tracking_frontier` block

**Files:**
- Modify: `scripts/export_frontend_data.py` (extend `export_variance_decomposition` + `main()`)
- Test: `tests/test_export.py` (append)

**Interfaces:**
- Consumes: Task 3's `tracking_frontier` dict; Task 2's `replication=` keyword pattern.
- Produces: `variance_decomposition.json` top-level key `"tracking_frontier"` with Task 3's exact dict. Task 7 consumes it.

- [ ] **Step 1: Failing test** (append to `tests/test_export.py`):

```python
def test_variance_decomposition_carries_tracking_frontier(
    captured: dict[str, Any],
) -> None:
    rolling = pd.DataFrame({
        "n_stocks": [20], "r_squared": [0.95],
        "window_start": pd.to_datetime(["2020-01-01"]),
        "window_end": pd.to_datetime(["2020-12-31"]),
    })
    frontier = {
        "method": "simplex_ls_topk_walkforward",
        "train_days": 252, "test_days": 21,
        "frontier": [{"k": 20, "te_oos": 0.033, "replication_r2_oos": 0.964,
                      "mean_monthly_churn": 0.2, "max_weight": 0.1,
                      "n_windows": 100}],
        "n_fallback_windows": 0,
    }
    export.export_variance_decomposition(rolling, tracking_frontier=frontier)
    payload = captured["variance_decomposition.json"]
    assert payload["tracking_frontier"]["frontier"][0]["k"] == 20
```

- [ ] **Step 2: Verify failure** — `uv run pytest tests/test_export.py -k frontier -v` → unexpected keyword.

- [ ] **Step 3: Implement.** Add `tracking_frontier: dict | None = None` to `export_variance_decomposition`; before `_write_json`: `if tracking_frontier: payload["tracking_frontier"] = _clean_dict(tracking_frontier)`. In `main()`:

```python
    logger.info("Computing simplex-LS tracking frontier...")
    frontier = tracking_frontier_fn(stock_prices, benchmark_display)
```
where the import is `from src.proof.replication import tracking_frontier as tracking_frontier_fn` (aliased to avoid shadowing the local variable), threaded into the same `export_variance_decomposition(...)` call. Guard runtime: log elapsed time; if > 5 min on the real panel, cut `k_values` to `[10, 15, 20, 30]` and say so in the log line.

- [ ] **Step 4: Tests + end-to-end**

`uv run pytest tests/test_export.py -q` → pass. Re-run the `--out-dir` verification from Task 2 Step 5 and additionally check `tracking_frontier.frontier` is non-empty and TE decreases from k=10 to k=40. Confirm `git status --short frontend/public/data/` is empty and `git diff --stat data/research/` is empty.

- [ ] **Step 5: Commit**

```bash
git add scripts/export_frontend_data.py tests/test_export.py
git commit -m "feat(export): simplex-LS tracking frontier block"
```

---

### Task 5: Solved-N series — stamp, collect, persist

**Files:**
- Modify: `src/strategies/dynamic_alpha.py` (end of `weights_fn` in `make_dynamic_alpha_weights_fn`)
- Modify: `src/backtest/engine.py` (`WalkForwardResult` + collection loop)
- Modify: `src/config.py` (`PARQUET_FILES`)
- Modify: `scripts/run_alpha_backtest.py` (persist)
- Test: `tests/test_dynamic_alpha.py`, `tests/test_walk_forward_engine.py` (append)

**Interfaces:**
- Consumes: existing `w.attrs["fallback"]` side-channel precedent (`engine.py:172-174`).
- Produces: `WalkForwardResult.n_selected: pd.Series` (index = train_end dates, int values; empty Series when the strategy never stamps); parquet `alpha_n_series` with columns `[date, n]`. Task 6 exports it.

- [ ] **Step 1: Failing tests.** In `tests/test_dynamic_alpha.py` (match its existing fixtures for prices/benchmark — read the file first; it has synthetic panels for the elbow tests):

```python
def test_weights_fn_stamps_n_selected():
    # reuse the file's existing synthetic panel + benchmark fixtures
    fn = make_dynamic_alpha_weights_fn("equal", make_static_n(12))
    w = fn(prices_panel, benchmark_series)   # adapt names to the fixtures
    assert w.attrs["n_selected"] == 12


def test_n_selected_survives_vol_target_overlay():
    """pd.concat drops .attrs — the stamp must be applied AFTER the overlay."""
    mi = market_indicators_fixture   # the file's HMM/vol fixtures
    fn = make_dynamic_alpha_weights_fn(
        "equal", make_static_n(12),
        overlay=make_vol_target(target_vol=0.05, window=21), market_indicators=mi,
    )
    w = fn(prices_panel_with_cash, benchmark_series)
    assert w.attrs["n_selected"] == 12
```

In `tests/test_walk_forward_engine.py` (match its existing walk-forward fixture style):

```python
def test_engine_collects_n_selected():
    def stamping_weights(train_prices, train_bench):
        w = pd.Series(1.0 / train_prices.shape[1], index=train_prices.columns)
        w.attrs["n_selected"] = train_prices.shape[1]
        return w

    result = run_walk_forward(  # use the file's existing invocation pattern
        prices, benchmark, stamping_weights, train_days=60, test_days=20,
    )
    assert isinstance(result.n_selected, pd.Series)
    assert len(result.n_selected) == len(result.splits)
    assert (result.n_selected == prices.shape[1]).all()


def test_engine_n_selected_empty_when_not_stamped():
    result = run_walk_forward(prices, benchmark, plain_equal_weights,
                              train_days=60, test_days=20)
    assert result.n_selected.empty
```

- [ ] **Step 2: Verify failure** — attribute/kwarg errors as appropriate.

- [ ] **Step 3: Implement.**

`src/strategies/dynamic_alpha.py`, at the end of the inner `weights_fn` (currently `return overlay_fn(base, equity, train_bench)`):

```python
        out = overlay_fn(base, equity, train_bench)
        # Stamped AFTER the overlay: pd.concat inside the cash overlay does
        # not propagate .attrs, so stamping `base` earlier would silently
        # drop the value on every overlay path.
        out.attrs["n_selected"] = int(n_t)
        return out
```

`src/backtest/engine.py`: add to `WalkForwardResult`:

```python
    n_selected: pd.Series = field(default_factory=lambda: pd.Series(dtype=int))
```
(document in the class docstring: "``n_selected`` is the per-rebalance holding count for strategies that stamp ``weights.attrs['n_selected']``; empty otherwise.") In the loop next to the fallback check:

```python
        if (n_sel := w.attrs.get("n_selected")) is not None:
            n_selected_map[s.train_end] = int(n_sel)
```
with `n_selected_map: dict[pd.Timestamp, int] = {}` initialised beside `fallback_dates`, and in the result construction: `n_selected=pd.Series(n_selected_map, dtype=int)`.

`src/config.py`: add `"alpha_n_series": DATA_DIR / "alpha_n_series.parquet",` to `PARQUET_FILES`.

`scripts/run_alpha_backtest.py`: next to the existing `alpha_nav` persistence (the `alpha_nav_df` block around line 206):

```python
    if not result.n_selected.empty:
        n_series_df = pd.DataFrame({
            "date": result.n_selected.index,
            "n": result.n_selected.values,
        })
        save_parquet(n_series_df, "alpha_n_series")
        logger.info(
            "Saved solved-N series: %d rebalances, median N=%d",
            len(n_series_df), int(result.n_selected.median()),
        )
```

- [ ] **Step 4: Run all four test files**

`uv run pytest tests/test_dynamic_alpha.py tests/test_walk_forward_engine.py -q` → pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/dynamic_alpha.py src/backtest/engine.py src/config.py scripts/run_alpha_backtest.py tests/
git commit -m "feat(alpha): stamp and persist the solved-N series"
```

---

### Task 6: Export solved-N + universe rotation

**Files:**
- Modify: `scripts/export_frontend_data.py` (two new export functions + `main()` wiring)
- Test: `tests/test_export.py` (append)

**Interfaces:**
- Consumes: `load_parquet("alpha_n_series")` (Task 5; may be missing → skip gracefully), `build_universe_schedule(rebalance_dates, n, ...)` from `src.data.universe` (existing, returns long DF `rebalance_date, rank, ticker, cap_proxy`).
- Produces: `alpha_n_series.json` = `{"series": [{"date","n"}], "mean", "median", "min", "max", "share_at_floor", "floor", "cap", "distribution": {"10": 49, ...}}`; `universe_rotation.json` = `{"summary": {...}, "events": [...], "schedule": [...]}`. Task 7 consumes both.

- [ ] **Step 1: Failing tests** (append to `tests/test_export.py`):

```python
def test_export_alpha_n_series(captured: dict[str, Any]) -> None:
    df = pd.DataFrame({
        "date": pd.bdate_range("2020-01-31", periods=6, freq="21B"),
        "n": [10, 10, 11, 12, 11, 16],
    })
    export.export_alpha_n_series(df)
    p = captured["alpha_n_series.json"]
    assert p["median"] == 11
    assert p["min"] == 10 and p["max"] == 16
    assert p["floor"] == 10 and p["cap"] == 30          # SPN bounds from config
    assert p["share_at_floor"] == pytest.approx(2 / 6)
    assert p["distribution"]["10"] == 2
    assert len(p["series"]) == 6


def test_export_universe_rotation(captured: dict[str, Any]) -> None:
    sched = pd.DataFrame({
        "rebalance_date": pd.to_datetime(
            ["2020-01-31"] * 3 + ["2020-02-28"] * 3),
        "rank": [1, 2, 3, 1, 2, 3],
        "ticker": ["A", "B", "C", "A", "B", "D"],
        "cap_proxy": [3.0, 2.0, 1.0, 3.1, 2.1, 1.1],
    })
    export.export_universe_rotation(sched)
    p = captured["universe_rotation.json"]
    s = p["summary"]
    assert s["distinct_tickers"] == 4
    assert s["n_rebalances"] == 2
    assert s["entries"] == 1 and s["exits"] == 1
    assert s["never_left"] == ["A", "B"]
    ev = p["events"]
    assert ev == [{"date": "2020-02-28", "entered": ["D"], "exited": ["C"]}]
```

- [ ] **Step 2: Verify failure** — `AttributeError: module ... has no attribute 'export_alpha_n_series'`.

- [ ] **Step 3: Implement** in `scripts/export_frontend_data.py` (import `SPN_MIN_STOCKS, SPN_MAX_STOCKS` in the config import block):

```python
def export_alpha_n_series(n_df: pd.DataFrame) -> Path:
    """Publish the solved-N series — the number the strategy ACTUALLY holds.

    Exists to kill the fabricated-elbow problem at the root: the UI once
    hardcoded `elbowN: 20` while the solver's median was 11. The chart's
    reference line reads this export from now on.
    """
    n = n_df["n"].astype(int)
    payload = {
        "series": [
            {"date": str(pd.Timestamp(d).date()), "n": int(v)}
            for d, v in zip(n_df["date"], n)
        ],
        "mean": round(float(n.mean()), 2),
        "median": int(n.median()),
        "min": int(n.min()),
        "max": int(n.max()),
        "floor": SPN_MIN_STOCKS,
        "cap": SPN_MAX_STOCKS,
        "share_at_floor": round(float((n == SPN_MIN_STOCKS).mean()), 4),
        "distribution": {
            str(k): int(v) for k, v in n.value_counts().sort_index().items()
        },
    }
    return _write_json(payload, "alpha_n_series.json")


def export_universe_rotation(schedule: pd.DataFrame) -> Path:
    """Membership rotation of the point-in-time top-N THIS PROJECT trades.

    Framing rule (accuracy): this is the cap-proxy universe the backtests
    actually hold — 80-90% overlap with the true historical S&P top-20 —
    so copy must say "the universe this project trades", never "the
    S&P 500's actual top 20".
    """
    dates = sorted(schedule["rebalance_date"].unique())
    sets = {d: set(schedule.loc[schedule["rebalance_date"] == d, "ticker"])
            for d in dates}
    events = []
    entries = exits = 0
    for prev, cur in zip(dates, dates[1:]):
        entered = sorted(sets[cur] - sets[prev])
        exited = sorted(sets[prev] - sets[cur])
        if entered or exited:
            events.append({
                "date": str(pd.Timestamp(cur).date()),
                "entered": entered, "exited": exited,
            })
            entries += len(entered)
            exits += len(exited)
    ever = set().union(*sets.values())
    always = sorted(t for t in ever if all(t in s for s in sets.values()))
    span_years = (
        (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days / 365.25
        if len(dates) > 1 else 0.0
    )
    payload = {
        "summary": {
            "n_rebalances": len(dates),
            "first": str(pd.Timestamp(dates[0]).date()),
            "last": str(pd.Timestamp(dates[-1]).date()),
            "distinct_tickers": len(ever),
            "entries": entries,
            "exits": exits,
            "avg_names_replaced_per_year": round(entries / span_years, 2)
            if span_years > 0 else None,
            "never_left": always,
        },
        "events": events,
        "schedule": [
            {"date": str(pd.Timestamp(d).date()), "tickers": sorted(sets[d])}
            for d in dates
        ],
    }
    return _write_json(payload, "universe_rotation.json")
```

Wire into `main()` after the holdings exports:

```python
    n_df = load_parquet("alpha_n_series")
    if not n_df.empty:
        n_df["date"] = pd.to_datetime(n_df["date"])
        written_files.append(export_alpha_n_series(n_df))
    else:
        logger.info("No alpha_n_series parquet — run run_alpha_backtest.py first")

    logger.info("Building universe rotation schedule...")
    month_ends = stock_prices.index.to_series().groupby(
        stock_prices.index.to_period("M")).max()
    rotation_dates = pd.DatetimeIndex(
        month_ends[month_ends >= pd.Timestamp(INCEPTION_DATE)])
    rotation = build_universe_schedule(rotation_dates, 20)
    written_files.append(export_universe_rotation(rotation))
```
(`build_universe_schedule` import goes in the existing `from src.data.universe import (...)` block. Match the surrounding `written_files.append(...)` idiom — read `main()`'s tail first; if it appends differently, follow it.)

- [ ] **Step 4: Tests + end-to-end**

`uv run pytest tests/test_export.py -q` → pass. Full run: `uv run python scripts/export_frontend_data.py --out-dir /tmp/proof-hardening-check` — verify `universe_rotation.json` summary shows ~40+ distinct tickers and a handful of never-left names, and (after running `uv run python scripts/run_alpha_backtest.py` once locally to produce the parquet) `alpha_n_series.json` shows median ≈ 11, never 20. `git status --short frontend/public/data/ data/research/` → empty (parquet under `data/` is gitignored).

- [ ] **Step 5: Commit**

```bash
git add scripts/export_frontend_data.py tests/test_export.py
git commit -m "feat(export): solved-N series and universe rotation"
```

---

### Task 7: Frontend types + transforms for all new blocks

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/hooks/useLabData.ts`

**Interfaces:**
- Consumes: JSON shapes from Tasks 2, 4, 6 (exact keys as written there).
- Produces: `VarianceDecompositionData.replication?: ReplicationQuality`, `.trackingFrontier?: TrackingFrontier`; new fetch slices `alphaNSeries?: AlphaNSeries`, `universeRotation?: UniverseRotation` on `LabData`. Task 8 consumes these names exactly.

- [ ] **Step 1: Add types** (`frontend/lib/types.ts` — place next to the variance-decomposition types; follow the file's doc-comment style):

```typescript
/** Tracking quality of an investable top-N basket (mean across windows). */
export interface ReplicationRow {
  n: number;
  weighting: "cap" | "equal";
  trackingError: number;
  replicationR2: number;
  teMin: number;
  teMax: number;
  nWindows: number;
}

/** The R² ladder: hindsight ceiling vs what an implementable basket achieves. */
export interface ReplicationLadder {
  olsCeiling?: number;
  investableCap?: number;
  investableEqual?: number;
}

export interface ReplicationQuality {
  ladder: ReplicationLadder;
  byN: ReplicationRow[];
}

/** One point of the cardinality-vs-tracking frontier (out of sample). */
export interface FrontierPoint {
  k: number;
  teOos: number;
  replicationR2Oos: number;
  meanMonthlyChurn: number;
  maxWeight: number;
  nWindows: number;
}

export interface TrackingFrontier {
  frontier: FrontierPoint[];
  nFallbackWindows: number;
}

/** The solved-N series — what the strategy's N-rule actually held. */
export interface AlphaNSeries {
  series: { date: string; n: number }[];
  mean: number;
  median: number;
  min: number;
  max: number;
  floor: number;
  cap: number;
  shareAtFloor: number;
}

/** Membership rotation of the point-in-time universe this project trades. */
export interface UniverseRotation {
  summary: {
    nRebalances: number;
    distinctTickers: number;
    entries: number;
    exits: number;
    avgNamesReplacedPerYear: number | null;
    neverLeft: string[];
  };
  events: { date: string; entered: string[]; exited: string[] }[];
}
```
Extend the existing variance-decomposition data interface (grep `varianceDecomposition` in `types.ts` for its name) with `replication?: ReplicationQuality; trackingFrontier?: TrackingFrontier;`, and add `alphaNSeries?: AlphaNSeries; universeRotation?: UniverseRotation;` to `LabData`.

- [ ] **Step 2: Transforms** (`frontend/hooks/useLabData.ts`). Add the two new files to the `DATA_FILES` map (`alphaNSeries: "alpha_n_series.json"`, `universeRotation: "universe_rotation.json"`) marked optional the same way the hook currently handles missing files (read how `strategyHoldings`/optional fetches are handled and copy that pattern — a 404 must not break the page). Transform snake→camel:

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformReplication(raw: any): ReplicationQuality | undefined {
  if (!raw?.by_n) return undefined;
  return {
    ladder: {
      olsCeiling: raw.ladder?.ols_ceiling,
      investableCap: raw.ladder?.investable_cap,
      investableEqual: raw.ladder?.investable_equal,
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    byN: raw.by_n.map((r: any) => ({
      n: r.n, weighting: r.weighting,
      trackingError: r.tracking_error, replicationR2: r.replication_r2,
      teMin: r.te_min, teMax: r.te_max, nWindows: r.n_windows,
    })),
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformTrackingFrontier(raw: any): TrackingFrontier | undefined {
  if (!raw?.frontier) return undefined;
  return {
    nFallbackWindows: raw.n_fallback_windows ?? 0,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    frontier: raw.frontier.map((r: any) => ({
      k: r.k, teOos: r.te_oos, replicationR2Oos: r.replication_r2_oos,
      meanMonthlyChurn: r.mean_monthly_churn, maxWeight: r.max_weight,
      nWindows: r.n_windows,
    })),
  };
}
```
(plus analogous `transformAlphaNSeries` / `transformUniverseRotation` — same mechanical mapping as the payload keys in Task 6). Wire them where `transformVarianceDecomposition` and the top-level assembly run. **PR #84 guard:** where the variance-decomposition transform is invoked, add:

```typescript
if (process.env.NODE_ENV !== "production" && rawVd?.replication && !vd.replication) {
  console.warn("useLabData: replication block present in JSON but dropped by transform");
}
```

- [ ] **Step 3: Gate** — `cd frontend && npm run lint && npm run build` → clean. (Build is the type-check; there is no frontend test harness.)

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/types.ts frontend/hooks/useLabData.ts
git commit -m "feat(frontend): types + transforms for replication, frontier, solved-N, rotation"
```

---

### Task 8: Surface the evidence in the lab UI (minimal, current-design idiom)

**Files:**
- Modify: `frontend/components/results/ResultsPanel.tsx` (concentration section)
- Modify: `frontend/components/results/ConcentrationChart.tsx` (solved-N reference line)
- Modify: `frontend/components/results/SignificancePanel.tsx` (Kremer citation)

**Interfaces:**
- Consumes: Task 7's `data.varianceDecomposition.replication`, `.trackingFrontier`, `data.alphaNSeries`.
- Produces: user-visible ladder + frontier line + citation. No new numbers hardcoded anywhere.

**Read first:** the current (redesigned) `ResultsPanel.tsx` concentration section and `PlainEnglish.tsx` to match tone and structure; `chartTheme.ts` for any colour needs. All styling via existing tokens (`text-ink*`, `bg-surface`, `border`) — the CI colour-guard will reject literals.

- [ ] **Step 1: R² ladder line.** In the concentration section of `ResultsPanel.tsx`, directly under the ConcentrationChart, render (only when the block exists):

```tsx
{data.varianceDecomposition?.replication?.ladder && (
  <p className="mt-3 max-w-3xl text-xs leading-relaxed text-ink-secondary">
    {(() => {
      const l = data.varianceDecomposition.replication.ladder;
      const pct = (v?: number) =>
        v !== undefined ? `${(v * 100).toFixed(1)}%` : "—";
      return (
        <>
          Three readings of the same claim, in descending honesty of
          hindsight: with perfect-hindsight regression weights the top 20
          explain <span className="font-mono">{pct(l.olsCeiling)}</span> of
          daily variance (a ceiling, not a portfolio); an investable
          equal-weight basket of the same names replicates{" "}
          <span className="font-mono">{pct(l.investableEqual)}</span> with
          one free parameter; cap-weighted,{" "}
          <span className="font-mono">{pct(l.investableCap)}</span>.
        </>
      );
    })()}
  </p>
)}
```

- [ ] **Step 2: Frontier note.** Beneath the ladder (same conditional pattern, `data.varianceDecomposition?.trackingFrontier`): find the k=20 point and render one sentence: "A cardinality-constrained optimiser (long-only least squares, top-k re-solve) tracks the index at `{(p.teOos*100).toFixed(2)}%` out-of-sample tracking error with 20 names — replication R² `{(p.replicationR2Oos*100).toFixed(1)}%` — and the full frontier runs k={min}…{max}." If a designer-grade frontier chart is wanted later it belongs to the landing-page project; here it is one honest sentence.

- [ ] **Step 3: Solved-N line on the chart.** In `ConcentrationChart.tsx`, accept an optional prop `solvedMedianN?: number` and, when present, render a second `ReferenceLine` at `x={solvedMedianN}` labelled `` `N=${solvedMedianN} · solver median` `` styled identically to the existing `x={20}` line (which stays, labelled "reporting convention"). Pass `solvedMedianN={data.alphaNSeries?.median}` from `ResultsPanel`. Colours: reuse whatever the existing reference line takes from `chartTheme.ts`.

- [ ] **Step 4: Kremer citation.** In `SignificancePanel.tsx`, append to the existing footnote paragraph (keep the current token classes):

```tsx
{" "}This ceiling is not unique to this project: Kremer, Lee, Bogdan &
Paterlini (2020) ran nine portfolio constructions on S&P 500 stocks over
2004–2016 and concluded that no strategy was statistically significantly
different from any other.
```

- [ ] **Step 5: Verify in browser.** `npm run lint && npm run build` → clean. Then preview (use the session's preview tooling with the dev server; if port 3000 is busy another session owns it — `autoPort` is already configured): load `/lab`, confirm (a) ladder paragraph renders when `replication` present and disappears gracefully with baseline JSON (it will be absent until the cron runs — that absence path MUST render nothing, not crash), (b) no console errors either way. Use the `--out-dir` JSON copied over `frontend/public/data` in a THROWAWAY `git stash`-able state or point a local fetch at it — do not commit it.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/results/
git commit -m "feat(lab): R-squared ladder, tracking-frontier note, solver-median line, Kremer citation"
```

---

### Task 9: Docs pass — corrections, honest naming, LASSO retirement

**Files:**
- Modify: `RESEARCH.md`, `frontend/lib/tooltips.ts`, `frontend/components/results/ThinkingPanel.tsx` (and `buildThinkingSections` in `ResultsPanel.tsx`)

Anchors are given as grep strings (line numbers have drifted); every replacement is exact text.

- [ ] **Step 1: RESEARCH.md — regression description (C1).** Grep `cap-weighted portfolio of the top N`. Replace that sentence with:

> When you regress S&P 500 daily returns on the individual top-N stocks' returns — coefficients fitted freely, in-sample, per rolling window — the R² curve is an *explanatory ceiling*: it says how much of the index's variance the names can account for with hindsight weights, not what a portfolio achieves. The investable counterparts (the exact baskets the Mirror and Equal indices trade) are published alongside it in the replication block, and sit a few points below the ceiling.

- [ ] **Step 2: RESEARCH.md — IR definition (C2).** Grep `mean(excess)` (or `√252` / `x 252`) in the IR passage. Rewrite to match the code:

> Information ratio in the headline tables is excess CAGR over annualised tracking error (`src/backtest/metrics.py`). The significance block uses the arithmetic variant — mean daily active return over its own volatility — because t = IR × √years holds exactly in that form; the two differ slightly and each table states which it uses.

- [ ] **Step 3: RESEARCH.md — Kremer + LASSO retirement (C3, C6).** Add a short subsection at the end of the significance discussion:

> **The ceiling is the field's, not ours.** Kremer, Lee, Bogdan & Paterlini (*Sparse Portfolio Selection via the Sorted ℓ₁-Norm*, arXiv:1710.02435) ran nine portfolio constructions on S&P 500 individual stocks over 2004–2016 and found "no strategy is statistically significantly different from each other."
>
> **Why there is no LASSO in this project.** Under long-only, fully-invested constraints the L1 norm of the weights is identically 1, so an L1 penalty is a constant and selects nothing (Brodie et al., PNAS 2009, eq. 5). Measured on this data: max weight change 7e-4 across λ ∈ [0, 100]. The two-stage escape (select unconstrained, refit) tracked at 8.9% OOS TE versus 3.8% for naive equal-weight top-20 — worse in 109 of 109 windows. `tests/test_replication.py::test_l1_penalty_is_inert_under_simplex_constraints` enforces this permanently. The working formulation is cardinality-constrained simplex least squares (`src/proof/replication.py`), kept descriptive by `test_module_emits_no_performance_metrics`.

- [ ] **Step 4: Elbow honesty (C4).** Grep `18-20 stocks` and `18–20 stocks` across `RESEARCH.md`, `frontend/lib/tooltips.ts`, `ThinkingPanel.tsx`, `ResultsPanel.tsx` (`buildThinkingSections`). Replace each claim that the elbow sits "around 18–20" with the data-true statement (adjust per surrounding sentence, no numbers beyond these):

> the solver's stopping rule — four pre-set parameters, not a fit — has held between 10 and 16 names (median 11), sitting on its N=10 floor roughly two-fifths of the time; 20 is the reporting convention for the concentration claim, not the solver's answer

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check src scripts tests && cd frontend && npm run lint && npm run build && cd ..
git add RESEARCH.md frontend/lib/tooltips.ts frontend/components/results/
git commit -m "docs: ceiling-vs-investable framing, IR definitions, Kremer citation, LASSO retirement, elbow honesty"
```

---

### Task 10: Full gate, registry byte-check, PR to develop

- [ ] **Step 1: Full verification suite**

```bash
uv run ruff check src scripts tests
rm -rf .mypy_cache && uv run mypy src scripts tests
uv run pytest tests/ -q
cd frontend && npm run lint && npm run build && cd ..
git diff --stat develop -- data/research/        # MUST print nothing
git status --short frontend/public/data/         # MUST print nothing
uv run python scripts/export_frontend_data.py --out-dir /tmp/proof-final && \
python3 - <<'EOF'
import json
vd = json.load(open('/tmp/proof-final/variance_decomposition.json'))
l = vd['replication']['ladder']
assert l['investable_equal'] <= l['ols_ceiling']
f = vd['tracking_frontier']['frontier']
tes = [p['te_oos'] for p in sorted(f, key=lambda p: p['k'])]
assert tes == sorted(tes, reverse=True), f"frontier not monotone: {tes}"
rot = json.load(open('/tmp/proof-final/universe_rotation.json'))
assert rot['summary']['distinct_tickers'] > 30
print('ladder', l)
print('frontier', {p['k']: p['te_oos'] for p in f})
print('rotation', rot['summary']['distinct_tickers'], 'tickers,',
      rot['summary']['entries'], 'entries')
EOF
```

- [ ] **Step 2: Push and open PR (base `develop`)**

```bash
git push -u origin feat/proof-hardening
gh pr create --base develop --title "feat: proof hardening — replication evidence layer (Tier A)" --body "Implements docs/superpowers/specs/2026-07-26-proof-hardening-design.md. Zero registry cost: trials.jsonl byte-identical, no research writes, all new analytics descriptive (tracking-only, guarded by tests). New exports: replication ladder, simplex-LS tracking frontier, solved-N series, universe rotation. Docs corrected (ceiling-vs-investable, IR definitions, elbow honesty, LASSO retirement with permanent regression test).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 3: Watch CI to green** (Monitor on `gh pr checks`; fix and re-push if red — remember CI runs `mypy src scripts tests` and builds the merge commit against `develop`).

---

## Self-Review Notes

- **Spec coverage:** A1→T1, A2→T2, A3→T7, B1→T3, B2/B3→T4, C1/C2/C3/C4/C6→T9, C5→T8 (ladder sentence carries the Equal result), D1/D2/D4→T1+T3 tests, D3→covered by T2's end-to-end ladder check plus T1's ceiling test (a strict numeric cross-check against `performance_metrics.json` tracking_error is convention-sensitive — windowed mean vs full-period — so the plan verifies ordering, not equality; if implementing D3 strictly, compare full-period TE from A1 run with `window_days=len(series)` in a follow-up), D5→T5+T6+T8, D6→T6+T8.
- **Fixture caveat:** Tasks 1/5 reference existing synthetic fixtures by intent, not name — the implementer MUST read the target test file first and adapt names; the test *bodies* given here are the contract.
- **Types:** `ReplicationQuality`/`TrackingFrontier`/`AlphaNSeries`/`UniverseRotation` defined in T7 and consumed with identical names in T8. Export keys in T2/T4/T6 match the transforms in T7 key-for-key.
