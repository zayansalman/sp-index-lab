import numpy as np
import pandas as pd

from src.proof.concentration import (
    build_mirror_index,
    concentration_curve,
    variance_decomposition,
)


def test_variance_decomposition_uses_configured_market_cap_order() -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="B")
    aapl_returns = pd.Series(np.linspace(-0.01, 0.012, len(idx)), index=idx)
    stock_returns = pd.DataFrame(
        {
            "MSFT": np.where(np.arange(len(idx)) % 2 == 0, 0.08, -0.08),
            "AAPL": aapl_returns,
        },
        index=idx,
    )

    result = variance_decomposition(
        stock_returns=stock_returns,
        benchmark_returns=aapl_returns,
        top_n_values=[1],
    )

    assert result.loc[0, "r_squared"] > 0.999


def test_concentration_curve_adds_tickers_in_configured_market_cap_order() -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="B")
    stock_returns = pd.DataFrame(
        {
            "MSFT": np.linspace(-0.01, 0.02, len(idx)),
            "AAPL": np.where(np.arange(len(idx)) % 2 == 0, 0.003, -0.002),
        },
        index=idx,
    )

    curve = concentration_curve(stock_returns, benchmark_returns=stock_returns["MSFT"])

    assert curve.loc[0, "ticker_added"] == "AAPL"
    assert curve.loc[1, "ticker_added"] == "MSFT"


def test_mirror_index_selects_configured_top_tickers_not_highest_prices() -> None:
    idx = pd.date_range("2024-01-01", periods=5, freq="B")
    stock_prices = pd.DataFrame(
        {
            "MSFT": [400.0, 420.0, 390.0, 410.0, 430.0],
            "AAPL": [100.0, 101.0, 102.0, 103.0, 104.0],
        },
        index=idx,
    )

    mirror = build_mirror_index(stock_prices, top_n=1, weighting="equal")
    expected_aapl_returns = stock_prices["AAPL"].pct_change(fill_method=None).dropna()

    assert np.allclose(mirror["daily_return"].to_numpy(), expected_aapl_returns.to_numpy())
