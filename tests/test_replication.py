"""Tests for the descriptive replication module.

This module is PROOF infrastructure, not a strategy: it computes tracking
quantities only. The guard test at the bottom enforces that boundary.
"""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

from src.proof import replication
from src.proof.replication import solve_simplex_ls, tracking_frontier


def _tracking_problem(t=252, p=40, seed=3):
    rng = np.random.default_rng(seed)
    X = rng.normal(0.0004, 0.01, (t, p))
    w_true = np.zeros(p)
    w_true[:8] = 1 / 8
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
    An earlier real-data probe with an independent implementation measured
    max weight change ~7e-4 across λ ∈ [0, 100]; in this module the penalty
    reduces to a constant, so solutions are identical up to solver
    tolerance — this test bounds the difference at 1e-3. LASSO-for-sparsity
    can never be reintroduced here by assertion."""
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
