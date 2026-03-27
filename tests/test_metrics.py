import numpy as np
import pandas as pd

from src.backtest.metrics import compute_performance_metrics, compute_tracking_error


def test_compute_tracking_error_zero_when_identical() -> None:
    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    r = pd.Series(np.random.default_rng(0).normal(0, 0.01, size=len(idx)), index=idx)
    te = compute_tracking_error(r, r, annualize=False)
    assert te == 0.0


def test_compute_performance_metrics_keys_and_sanity() -> None:
    idx = pd.date_range("2020-01-01", periods=252, freq="B")
    returns = pd.Series(0.001, index=idx)
    nav = (1 + returns).cumprod()

    metrics = compute_performance_metrics(nav)
    assert set(metrics.keys()) >= {
        "total_return",
        "cagr",
        "annualised_volatility",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "calmar_ratio",
        "n_years",
    }
    assert metrics["total_return"] > 0
    assert metrics["cagr"] > 0
    assert metrics["annualised_volatility"] == 0.0
    assert metrics["max_drawdown"] == 0.0


def test_compute_performance_metrics_relative_metrics_present() -> None:
    idx = pd.date_range("2020-01-01", periods=252, freq="B")
    nav = (1 + pd.Series(0.001, index=idx)).cumprod()
    bench = (1 + pd.Series(0.0005, index=idx)).cumprod()
    metrics = compute_performance_metrics(nav, benchmark_nav=bench)
    assert set(metrics.keys()) >= {
        "excess_return",
        "tracking_error",
        "information_ratio",
        "beta",
        "alpha",
    }

