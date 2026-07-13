"""Trial registry + sanctioned dev-window experiment runner.

Every backtest run during development goes through :func:`run_experiment`,
which (1) truncates data to the development window (``DEV_END``) so the
holdout is never touched, (2) scores on a matched window, and (3) appends an
immutable line to ``data/research/trials.jsonl``. The trial count is the
denominator for the deflated Sharpe ratio — under-counting trials is exactly
how v1's alpha looked significant, so logging is automatic, not optional.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest.engine import WalkForwardResult, WeightsFn, walk_forward_backtest
from src.config import DATA_DIR, DEV_END, TEST_WINDOW_DAYS, TRAIN_WINDOW_DAYS
from src.research.scoring import StrategyScore, score_strategy

logger = logging.getLogger(__name__)

TRIALS_PATH = DATA_DIR / "research" / "trials.jsonl"


@dataclass
class Trial:
    """One logged backtest attempt."""

    name: str
    split: str  # "dev" or "holdout"
    config: dict[str, Any]
    score: dict[str, Any]
    fallback_rate: float
    n_splits: int
    git_sha: str
    timestamp: str
    notes: str


def _git_sha() -> str:
    """Short git SHA of the working tree, or 'unknown'."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def log_trial(trial: Trial, path: Path | None = None) -> None:
    """Append a trial as one JSON line (registry is append-only).

    ``path`` defaults to the module-level ``TRIALS_PATH`` resolved at call
    time, so tests can redirect the registry via monkeypatch.
    """
    path = path or TRIALS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(asdict(trial)) + "\n")
    logger.info("Logged trial %r (%s) → %s", trial.name, trial.split, path.name)


def load_trials(path: Path | None = None) -> list[dict]:
    """Load all logged trials (empty list if none)."""
    path = path or TRIALS_PATH
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def dev_trial_count(path: Path | None = None) -> int:
    """Number of distinct development trials logged (deflated-Sharpe N)."""
    return sum(1 for t in load_trials(path) if t.get("split") == "dev")


def run_experiment(
    name: str,
    weights_fn: WeightsFn,
    *,
    prices: pd.DataFrame,
    benchmark: pd.Series,
    references: dict[str, pd.Series],
    universe_fn: Any | None = None,
    train_days: int = TRAIN_WINDOW_DAYS,
    test_days: int = TEST_WINDOW_DAYS,
    execution_lag_days: int = 0,
    config: dict[str, Any] | None = None,
    notes: str = "",
    log: bool = True,
    timestamp: str | None = None,
) -> tuple[StrategyScore, WalkForwardResult]:
    """Run a walk-forward backtest on the DEV window, score, and log it.

    Data is hard-truncated at ``DEV_END`` before anything runs — a candidate
    developed here has, by construction, never seen the holdout. Scoring is
    matched-window against ``references``.

    Args:
        name: Strategy label (appears in the registry).
        weights_fn: Walk-forward weights function.
        prices: Full wide price panel (truncated internally).
        benchmark: Full benchmark price series (truncated internally).
        references: ``{name: nav}`` to score against (e.g. sp500, sp20_equal),
            each truncated internally.
        universe_fn: Optional PIT ``as_of → tickers`` callable.
        train_days, test_days: Walk-forward window lengths.
        execution_lag_days: Extra decision-to-fill lag (robustness runs).
        config: Arbitrary reproducibility metadata (engine, n_policy, ...).
        notes: Free-text note.
        log: Whether to append to the registry (False for dry checks).
        timestamp: ISO timestamp override (else now, UTC).

    Returns:
        ``(StrategyScore, WalkForwardResult)`` on the dev window.
    """
    dev_end = pd.Timestamp(DEV_END)
    prices_dev = prices.loc[prices.index <= dev_end]
    benchmark_dev = benchmark.loc[benchmark.index <= dev_end]
    refs_dev = {k: v.loc[v.index <= dev_end] for k, v in references.items()}

    result = walk_forward_backtest(
        prices_dev,
        benchmark_prices=benchmark_dev,
        weights_fn=weights_fn,
        train_days=train_days,
        test_days=test_days,
        universe_fn=universe_fn,
        execution_lag_days=execution_lag_days,
    )

    score = score_strategy(
        name,
        result.nav,
        refs_dev,
        turnover=result.turnover,
        costs=result.costs,
    )

    if log:
        trial = Trial(
            name=name,
            split="dev",
            config=config or {},
            score=score.to_dict(),
            fallback_rate=result.fallback_rate,
            n_splits=len(result.splits),
            git_sha=_git_sha(),
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            notes=notes,
        )
        log_trial(trial)

    return score, result
