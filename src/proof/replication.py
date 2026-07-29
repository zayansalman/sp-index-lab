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
eq. 5). An earlier real-data probe with an independent implementation measured
max weight change ~7e-4 across λ ∈ [0, 100]; in this module the penalty
reduces to a constant, so solutions are identical to solver precision (~1e-12),
which the regression test asserts. The l1_penalty parameter below exists
solely so that test can prove this inertness.
"""

import logging
from typing import cast

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
        grad_l1 = l1_penalty * np.ones_like(w) if l1_penalty > 0 else np.zeros_like(w)
        return xtx @ w - xty + grad_l1  # type: ignore[no-any-return]

    result = minimize(
        objective, w0, jac=gradient, method="SLSQP",
        bounds=[(0.0, 1.0)] * p,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        raise RuntimeError(f"simplex LS failed: {result.message}")
    w = np.clip(cast(np.ndarray, result.x), 0.0, None)
    return w / w.sum()  # type: ignore[no-any-return]


def _cardinality_weights(X: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    """Two-pass: dense solve, restrict to top-k support, re-solve."""
    dense = solve_simplex_ls(X, y)
    if int((dense > 1e-6).sum()) <= k:
        return dense  # type: ignore[no-any-return]
    support = np.argsort(dense)[-k:]
    sparse = np.zeros_like(dense)
    sparse[support] = solve_simplex_ls(X[:, support], y)
    return sparse  # type: ignore[no-any-return]


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
            except RuntimeError as exc:
                logger.warning(
                    "simplex LS failed at window %d (k=%d): %s — "
                    "falling back to equal-weighted top-k by trailing mean return",
                    lo, k, exc,
                )
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
