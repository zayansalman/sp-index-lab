"""Tests for the anti-selection-bias research harness."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.metrics import (
    deflated_sharpe,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
)
from src.config import DEV_END
from src.research import registry
from src.research.scoring import score_strategy

# ---------------------------------------------------------------------------
# Matched-window scoring
# ---------------------------------------------------------------------------

def test_score_strategy_aligns_to_common_window() -> None:
    # Strategy spans 2018-2020; benchmark spans 2016-2022. Scoring must use
    # only the overlap and renormalise both to 1.0 there.
    strat_idx = pd.bdate_range("2018-01-01", periods=500)
    bench_idx = pd.bdate_range("2016-01-01", periods=1500)
    strat = pd.Series(np.cumprod(np.full(500, 1.0005)), index=strat_idx)
    bench = pd.Series(np.cumprod(np.full(1500, 1.0003)), index=bench_idx)

    score = score_strategy("s", strat, {"sp500": bench})

    assert score.window_start == str(strat_idx[0].date())
    assert score.window_end == str(strat_idx[-1].date())
    assert score.n_days == 500
    # Strategy drifts up faster → positive excess CAGR.
    assert score.excess_cagr["sp500"] > 0


def test_score_strategy_requires_overlap() -> None:
    a = pd.Series([1.0, 1.1], index=pd.bdate_range("2018-01-01", periods=2))
    b = pd.Series([1.0, 1.1], index=pd.bdate_range("2020-01-01", periods=2))
    with pytest.raises(ValueError, match="common dates"):
        score_strategy("s", a, {"sp500": b})


# ---------------------------------------------------------------------------
# run_experiment: dev truncation + registry logging
# ---------------------------------------------------------------------------

def test_run_experiment_truncates_at_dev_end(tmp_path, monkeypatch) -> None:
    # Build a panel that extends well past DEV_END; the experiment must not
    # produce any out-of-sample NAV beyond it.
    idx = pd.bdate_range("2022-01-01", periods=700)  # runs into 2024 (past DEV_END)
    rng = np.random.default_rng(1)
    prices = pd.DataFrame(
        100 * np.cumprod(1 + rng.normal(0.0004, 0.01, (700, 3)), axis=0),
        index=idx,
        columns=["A", "B", "C"],
    )
    benchmark = pd.Series(
        100 * np.cumprod(1 + rng.normal(0.0003, 0.009, 700)), index=idx, name="sp500"
    )
    monkeypatch.setattr(registry, "TRIALS_PATH", tmp_path / "trials.jsonl")

    def equal_weights(train_prices, _bench):
        return pd.Series(1.0 / train_prices.shape[1], index=train_prices.columns)

    score, result = registry.run_experiment(
        "equal_test",
        equal_weights,
        prices=prices,
        benchmark=benchmark,
        references={"sp500": benchmark},
        train_days=120,
        test_days=21,
        config={"engine": "equal"},
    )

    assert result.nav.index.max() <= pd.Timestamp(DEV_END)
    trials = registry.load_trials(tmp_path / "trials.jsonl")
    assert len(trials) == 1
    assert trials[0]["name"] == "equal_test"
    assert trials[0]["split"] == "dev"
    assert registry.dev_trial_count(tmp_path / "trials.jsonl") == 1


# ---------------------------------------------------------------------------
# Deflated Sharpe
# ---------------------------------------------------------------------------

def test_expected_max_sharpe_grows_with_trials() -> None:
    e5 = expected_max_sharpe(5, 0.1)
    e50 = expected_max_sharpe(50, 0.1)
    assert e50 > e5 > 0
    assert expected_max_sharpe(1, 0.1) == 0.0
    assert expected_max_sharpe(50, 0.0) == 0.0


def test_probabilistic_sharpe_high_for_strong_steady_series() -> None:
    idx = pd.bdate_range("2018-01-01", periods=1000)
    rng = np.random.default_rng(3)
    # Strong positive drift, low vol → high, confident Sharpe.
    returns = pd.Series(rng.normal(0.001, 0.005, 1000), index=idx)
    psr = probabilistic_sharpe_ratio(returns, benchmark_sr=0.0)
    assert psr > 0.95


def test_deflated_sharpe_penalises_more_trials() -> None:
    idx = pd.bdate_range("2018-01-01", periods=1500)
    rng = np.random.default_rng(4)
    returns = pd.Series(rng.normal(0.0004, 0.01, 1500), index=idx)
    dsr_few = deflated_sharpe(returns, n_trials=2, sharpe_std=0.05)
    dsr_many = deflated_sharpe(returns, n_trials=100, sharpe_std=0.05)
    assert 0.0 <= dsr_many <= dsr_few <= 1.0
