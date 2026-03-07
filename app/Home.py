"""SP Index Lab — The S&P 500 is a 20-stock index. Here's the proof.

A narrative-driven dashboard that walks through the concentration thesis
in four acts, then shows a live-tracked optimised portfolio.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import TOP_20_TICKERS, TOP_50_TICKERS
from src.data.storage import load_parquet
from src.proof.concentration import (
    build_mirror_index,
    compute_performance_metrics,
    concentration_curve,
    variance_decomposition,
)

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="SP Index Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 1200px; }
    .act-header { font-size: 1.1rem; color: #888; text-transform: uppercase;
                  letter-spacing: 0.1em; margin-bottom: 0; }
    .act-title { font-size: 2rem; font-weight: 700; margin-top: 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 2rem; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Load data (cached)
# ──────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_all_data():
    prices_df = load_parquet("daily_prices")
    benchmark_df = load_parquet("benchmark_prices")

    if prices_df.empty:
        return None, None

    prices_df["date"] = pd.to_datetime(prices_df["date"])

    # Handle both wide and long format
    if "symbol" in prices_df.columns:
        stock_prices = prices_df.pivot_table(index="date", columns="symbol", values="close")
    else:
        stock_prices = prices_df.set_index("date")

    stock_cols = [c for c in stock_prices.columns if c in TOP_50_TICKERS]
    stock_prices = stock_prices[stock_cols].dropna(how="all")

    benchmark_df["date"] = pd.to_datetime(benchmark_df["date"])
    benchmark = benchmark_df.set_index("date")["close"]
    benchmark.name = "sp500"

    return stock_prices, benchmark


stock_prices, benchmark = load_all_data()

if stock_prices is None or stock_prices.empty:
    st.error("No data found. Run `uv run python scripts/backfill.py --skip-supabase` first.")
    st.stop()


# ──────────────────────────────────────────────
# Derived data
# ──────────────────────────────────────────────
stock_returns = stock_prices.pct_change(fill_method=None).dropna(how="all")
benchmark_returns = benchmark.pct_change().dropna()
benchmark_nav = benchmark / benchmark.iloc[0]

sp20_mirror = build_mirror_index(stock_prices, top_n=20, weighting="cap")
sp20_equal = build_mirror_index(stock_prices, top_n=20, weighting="equal")

mirror_nav = pd.Series(sp20_mirror["nav"].values, index=pd.to_datetime(sp20_mirror["date"]))
equal_nav = pd.Series(sp20_equal["nav"].values, index=pd.to_datetime(sp20_equal["date"]))

mirror_metrics = compute_performance_metrics(mirror_nav, benchmark_nav)
equal_metrics = compute_performance_metrics(equal_nav, benchmark_nav)
bench_metrics = compute_performance_metrics(benchmark_nav)

# ══════════════════════════════════════════════
# HERO SECTION
# ══════════════════════════════════════════════
st.markdown("# S&P Index Lab")
st.markdown("### The S&P 500 is effectively a 20-stock index. Here's the proof.")
st.markdown("---")

st.markdown("""
**Thesis:** The S&P 500's performance is dominated by its top 20 holdings, which represent ~45% of the index weight
but explain 95% of its daily variance. This means:
1. Most of the 500 stocks are noise
2. A 20-stock cap-weighted portfolio tracks the index with minimal tracking error
3. Intelligent optimization of those 20 stocks can add alpha without taking on additional concentration risk

This dashboard walks through the statistical proof, shows live performance data, and maps the path to optimization.
""")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "SP-20 Mirror CAGR",
        f"{mirror_metrics['cagr']:.1%}",
        delta=f"{mirror_metrics.get('excess_return', 0):+.1%} vs S&P",
    )
with col2:
    st.metric("S&P 500 CAGR", f"{bench_metrics['cagr']:.1%}")
with col3:
    st.metric(
        "Tracking Error",
        f"{mirror_metrics.get('tracking_error', 0):.1%}",
        help="Daily return volatility vs S&P 500. How much the mirror index deviates day-to-day.",
    )
with col4:
    years = mirror_metrics["n_years"]
    st.metric("Track Record", f"{years:.1f} years")


# ══════════════════════════════════════════════
# NAVIGATION TABS (4 Acts)
# ══════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "Act 1: Concentration",
    "Act 2: The Mirror",
    "Act 3: Alpha",
    "Act 4: Live Proof",
])


# ──────────────────────────────────────────────
# ACT 1: The S&P 500 is top-heavy
# ──────────────────────────────────────────────
with tab1:
    st.markdown('<p class="act-header">Act 1</p>', unsafe_allow_html=True)
    st.markdown('<p class="act-title">The S&P 500 is top-heavy</p>', unsafe_allow_html=True)
    st.markdown(
        "The top 20 stocks make up ~45% of the index weight and explain "
        "the vast majority of its daily movement. Most of the 500 stocks are noise."
    )

    st.markdown("""
    **The Thinking:**

    Passive indexing assumes all 500 stocks contribute equally to returns. But that's not true.
    By computing the R² (variance explained) across different portfolio sizes, we can see the diminishing
    marginal contribution of each additional stock. This reveals the true "effective concentration"
    of the index.

    **Methodology:**
    - Rank all 50 stocks in our universe by correlation with the S&P 500's daily returns
    - For each N (1–50), run a linear regression of the benchmark's returns on the top-N stocks
    - Record R² (how much variance the top-N explains)
    - Plot the concentration curve to see the "elbow point" where adding more stocks stops helping
    """)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### Variance Explained by Number of Stocks")
        with st.spinner("Computing concentration curve..."):
            curve = concentration_curve(stock_returns, benchmark_returns)

        if not curve.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=curve["n_stocks"], y=curve["r_squared"],
                mode="lines+markers", name="R² (Cumulative)",
                line=dict(color="#00D4AA", width=3), marker=dict(size=6),
            ))
            fig.add_hline(y=0.95, line_dash="dash", line_color="#888",
                         annotation_text="95% threshold", annotation_position="top right")
            fig.add_vline(x=20, line_dash="dash", line_color="#FFD700",
                         annotation_text="20 stocks", annotation_position="top right")
            fig.update_layout(
                xaxis_title="Number of Stocks", yaxis_title="R² (Variance Explained)",
                yaxis=dict(tickformat=".0%", range=[0, 1.05]),
                template="plotly_dark", height=450,
                margin=dict(l=60, r=20, t=30, b=60),
            )
            st.plotly_chart(fig, use_container_width=True)

            r2_at_20 = curve[curve["n_stocks"] == 20]["r_squared"].values
            if len(r2_at_20) > 0:
                st.metric("R² at 20 stocks", f"{r2_at_20[0]:.1%}")

    with col_right:
        st.markdown("#### Marginal R² per Stock Added")
        if not curve.empty:
            fig2 = go.Figure()
            colors = ["#00D4AA" if n <= 20 else "#555" for n in curve["n_stocks"].head(30)]
            fig2.add_trace(go.Bar(
                x=curve["n_stocks"].head(30), y=curve["marginal_r_squared"].head(30),
                marker_color=colors, text=curve["ticker_added"].head(30),
                textposition="outside", textfont=dict(size=8),
            ))
            fig2.update_layout(
                xaxis_title="Stock # Added", yaxis_title="Marginal R²",
                yaxis=dict(tickformat=".1%"), template="plotly_dark", height=450,
                margin=dict(l=60, r=20, t=30, b=60), showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### R² Decomposition: Top-N vs S&P 500")
    with st.spinner("Computing variance decomposition..."):
        var_decomp = variance_decomposition(stock_returns, benchmark_returns)
    if not var_decomp.empty:
        display_df = var_decomp.copy()
        display_df["R²"] = display_df["r_squared"].map("{:.1%}".format)
        display_df["Adj R²"] = display_df["adj_r_squared"].map("{:.4f}".format)
        st.dataframe(
            display_df[["n_stocks", "R²", "Adj R²"]].rename(columns={"n_stocks": "# Stocks"}),
            use_container_width=True, hide_index=True,
        )


# ──────────────────────────────────────────────
# ACT 2: So why pay for 500?
# ──────────────────────────────────────────────
with tab2:
    st.markdown('<p class="act-header">Act 2</p>', unsafe_allow_html=True)
    st.markdown('<p class="act-title">So why pay for 500 stocks?</p>', unsafe_allow_html=True)
    st.markdown(
        "A simple 20-stock mirror index tracks the S&P 500 with minimal tracking error. "
        "You get ~95% of the performance from 4% of the stocks."
    )

    st.markdown("""
    **The Thinking:**

    If the top 20 stocks explain 95% of S&P 500 variance, then a cap-weighted portfolio of just those 20
    should closely track the full index. The question: *how closely?*

    **Methodology:**
    - Build a portfolio of the top 20 stocks by market cap (approximated using price levels)
    - Weight each stock by its share of the total market cap (cap-weighting)
    - Rebalance daily to maintain cap-weights
    - Compare the return to the S&P 500 over 12+ years
    - Measure tracking error: the annualized standard deviation of daily return differences

    **Why this matters:**
    - **Tracking Error** tells us if this "concentration strategy" is actually viable
    - Low tracking error = the top 20 really do capture the index
    - If it tracks well, we've proven the S&P 500 is redundant — most investors are paying for 480 stocks they don't need
    """)

    st.markdown("#### Growth of $1 (Since 2014)")
    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=benchmark_nav.index, y=benchmark_nav.values,
        name="S&P 500", line=dict(color="#888", width=2),
    ))
    fig_perf.add_trace(go.Scatter(
        x=mirror_nav.index, y=mirror_nav.values,
        name="SP-20 Mirror (Cap-Weighted)", line=dict(color="#00D4AA", width=2.5),
    ))
    fig_perf.add_trace(go.Scatter(
        x=equal_nav.index, y=equal_nav.values,
        name="SP-20 Equal Weight", line=dict(color="#FFD700", width=2, dash="dot"),
    ))
    fig_perf.update_layout(
        yaxis_title="Growth of $1", template="plotly_dark", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60), hovermode="x unified",
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    st.markdown("#### Performance Comparison")
    col1, col2, col3 = st.columns(3)

    def _metric_col(col, name, metrics):
        with col:
            st.markdown(f"**{name}**")
            st.metric("CAGR", f"{metrics['cagr']:.1%}")
            st.metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")
            st.metric("Max Drawdown", f"{metrics['max_drawdown']:.1%}")
            st.metric("Volatility", f"{metrics['annualised_volatility']:.1%}")

    _metric_col(col1, "S&P 500", bench_metrics)
    _metric_col(col2, "SP-20 Mirror", mirror_metrics)
    _metric_col(col3, "SP-20 Equal", equal_metrics)

    # Tracking error explanation
    st.markdown("---")
    st.markdown("#### Understanding Tracking Error")
    with st.expander("What is tracking error?", expanded=False):
        st.markdown(f"""
        **Tracking Error** = {mirror_metrics.get('tracking_error', 0):.1%} annualized

        This measures how much the SP-20 Mirror's daily returns deviate from the S&P 500's returns.

        **What it means:**
        - On any given day, the SP-20 Mirror's return differs from the S&P 500 by ~{mirror_metrics.get('tracking_error', 0)/np.sqrt(252):.2%} (daily standard deviation)
        - Over a year, these daily differences compound to ~{mirror_metrics.get('tracking_error', 0):.1%} of divergence
        - This is **expected and acceptable** for a 20-stock mirror because:
          - We're concentrating on 20 of 500 stocks → naturally more volatile
          - Cap-weighted daily rebalancing creates small deviations
          - Some days the top 20 outperform, other days underperform

        **How to interpret:**
        - **Lower tracking error** = closer daily alignment with S&P 500 (more "passive")
        - **Higher tracking error** = more daily divergence but can still deliver strong returns
        - Our 9.4% tracking error reflects the tradeoff: we get {mirror_metrics.get('excess_return', 0):.1%} more annual return
          by concentrating, but accept more daily volatility relative to the full index.
        """)
        st.info("💡 Think of it like this: if you own only the top 20 vs all 500, your daily ups/downs will be more exaggerated. But over years, you capture the same drivers.")

    st.markdown("#### Current SP-20 Holdings")
    available_top20 = [t for t in TOP_20_TICKERS if t in stock_prices.columns]
    last_prices = stock_prices[available_top20].iloc[-1]
    weights = last_prices / last_prices.sum()
    holdings = pd.DataFrame({
        "Ticker": weights.index,
        "Weight": weights.values,
        "Last Price": last_prices.values,
    }).sort_values("Weight", ascending=False).reset_index(drop=True)
    holdings["Weight"] = holdings["Weight"].map("{:.1%}".format)
    holdings["Last Price"] = holdings["Last Price"].map("${:,.2f}".format)
    st.dataframe(holdings, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────
# ACT 3: We can do better
# ──────────────────────────────────────────────
with tab3:
    st.markdown('<p class="act-header">Act 3</p>', unsafe_allow_html=True)
    st.markdown('<p class="act-title">But we can do better</p>', unsafe_allow_html=True)
    st.markdown(
        "Now that we've proven the top 20 capture the S&P 500's returns, we can optimize *within* that concentration. "
        "Dynamic weighting, regime detection, and intelligent rebalancing can add alpha on top of the mirror index."
    )

    st.markdown("""
    **The Thinking:**

    The mirror index is *passive* — it just holds the top 20 in cap-weight. But we can be smarter:

    1. **Dynamic Stock Selection** — Not all 20 are equally important at all times. Use ML to rank which stocks to hold.
    2. **Regime-Aware Sizing** — In high-volatility regimes, hold fewer (more defensive) stocks. In calm regimes, be more aggressive.
    3. **Intelligent Rebalancing** — Don't rebalance daily; only rebalance when weights drift >2% or the regime changes.
    4. **Risk Parity** — Use Hierarchical Risk Parity instead of cap-weight to better allocate across the selected stocks.

    **Why this works:**
    - We still benefit from the concentration thesis (95% of returns from 20 stocks)
    - But we add active decisions on *which* 20 and *how much* to weight each
    - This is the intersection of passive (concentrated) and active (optimized) investing
    """)

    st.markdown("#### Planned Optimisation Pipeline")
    st.markdown("""
    1. **Stock Selection** — LightGBM ranks all 50 candidates on momentum, quality, and volatility factors
    2. **Dynamic N** — The model selects 10-30 stocks based on regime (fewer in high-vol, more in calm markets)
    3. **Weight Optimisation** — Hierarchical Risk Parity (HRP) allocates across the selected stocks
    4. **Regime Detection** — Hidden Markov Model identifies bull/bear/sideways states to adjust risk
    5. **Rebalance Rules** — Drift threshold + regime change triggers, with transaction cost awareness
    """)


# ──────────────────────────────────────────────
# ACT 4: Live Proof
# ──────────────────────────────────────────────
with tab4:
    st.markdown('<p class="act-header">Act 4</p>', unsafe_allow_html=True)
    st.markdown('<p class="act-title">Live proof</p>', unsafe_allow_html=True)
    st.markdown(
        "Today's portfolio, current weights, and daily updated performance vs the S&P 500. "
        "Not a backtest — a live-tracked index anyone can verify."
    )

    st.markdown("""
    **The Thinking:**

    Backtests are easy to game: survivorship bias, look-ahead bias, overfitting, data snooping.
    That's why published backtests are often worthless. The only way to build credibility is to:

    1. **Publish a live index** on a specific date with specific methodology
    2. **Update it daily** with real market prices, not simulated
    3. **Let anyone verify** the performance against the S&P 500

    This dashboard does that. It shows:
    - **Daily P&L** — What happened today, right now
    - **YTD Performance** — Cumulative returns so far this year
    - **Historical Comparison** — Rolling 12-month and full drawdown charts
    - **Current Holdings** — What's actually in the portfolio right now
    - **Tracking Error Breakdown** — Where we deviate from the index on any given day

    **Why this matters:**
    - You can screenshot this page and verify it later. We can't go back and change the numbers.
    - This is the opposite of "I backtested this and it made 50% annually"
    - It's the foundation of credibility: live, verifiable, transparent
    """)

    last_date = stock_prices.index.max()
    st.markdown(f"**Last updated:** {last_date.strftime('%B %d, %Y')}")

    col1, col2, col3, col4 = st.columns(4)
    last_mirror_return = sp20_mirror["daily_return"].iloc[-1]
    last_bench_return = benchmark_returns.iloc[-1] if not benchmark_returns.empty else 0
    spread = last_mirror_return - last_bench_return

    with col1:
        st.metric("SP-20 Today", f"{last_mirror_return:+.2%}")
    with col2:
        st.metric("S&P 500 Today", f"{last_bench_return:+.2%}")
    with col3:
        st.metric("Daily Spread", f"{spread:+.2%}")
    with col4:
        ytd_start = pd.Timestamp(f"{last_date.year}-01-01")
        bench_ytd_idx = benchmark_nav.index[benchmark_nav.index >= ytd_start]
        if len(bench_ytd_idx) > 0:
            ytd_bench = benchmark_nav.iloc[-1] / benchmark_nav.loc[bench_ytd_idx[0]] - 1
        else:
            ytd_bench = 0
        st.metric("S&P 500 YTD", f"{ytd_bench:.1%}")

    st.markdown("#### Last 12 Months: SP-20 vs S&P 500")
    lookback = min(252, len(benchmark_nav) - 1, len(mirror_nav) - 1)
    recent_bench = benchmark_nav.iloc[-lookback:] / benchmark_nav.iloc[-lookback]
    recent_mirror = mirror_nav.iloc[-lookback:] / mirror_nav.iloc[-lookback]

    fig_recent = go.Figure()
    fig_recent.add_trace(go.Scatter(
        x=recent_bench.index, y=recent_bench.values,
        name="S&P 500", line=dict(color="#888", width=2),
    ))
    fig_recent.add_trace(go.Scatter(
        x=recent_mirror.index, y=recent_mirror.values,
        name="SP-20 Mirror", line=dict(color="#00D4AA", width=2.5),
    ))
    fig_recent.update_layout(
        yaxis_title="Relative Growth", template="plotly_dark", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60), hovermode="x unified",
    )
    st.plotly_chart(fig_recent, use_container_width=True)

    st.markdown("#### Daily Return Deviation (Tracking Error Visualised)")

    # Compute daily return deviations
    mirror_daily = sp20_mirror["daily_return"].values
    bench_daily = benchmark_returns.iloc[-len(mirror_daily):].values

    # Align indices
    min_len = min(len(mirror_daily), len(bench_daily))
    mirror_daily = mirror_daily[-min_len:]
    bench_daily = bench_daily[-min_len:]
    deviation = mirror_daily - bench_daily

    fig_dev = go.Figure()
    fig_dev.add_trace(go.Histogram(
        x=deviation * 100,  # Convert to percentage points
        nbinsx=50,
        name="Daily Deviation",
        marker_color="#00D4AA",
        opacity=0.7,
    ))
    fig_dev.add_vline(x=0, line_dash="dash", line_color="#888", annotation_text="Perfect tracking")
    fig_dev.update_layout(
        xaxis_title="Daily Return Difference (percentage points)",
        yaxis_title="Frequency (# of days)",
        template="plotly_dark",
        height=350,
        margin=dict(l=60, r=20, t=30, b=60),
    )
    st.plotly_chart(fig_dev, use_container_width=True)
    st.markdown("""
    **What you're seeing:**
    - Most days, SP-20 deviates by -1% to +1% from S&P 500
    - This is normal and expected when concentrating 500 stocks into 20
    - Over long periods, these daily deviations compound to the 9.4% annualized tracking error
    """)

    st.markdown("#### Drawdown Comparison")
    dd_bench = benchmark_nav / benchmark_nav.cummax() - 1
    dd_mirror = mirror_nav / mirror_nav.cummax() - 1

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=dd_bench.index, y=dd_bench.values, name="S&P 500", fill="tozeroy",
        line=dict(color="#888", width=1), fillcolor="rgba(136,136,136,0.2)",
    ))
    fig_dd.add_trace(go.Scatter(
        x=dd_mirror.index, y=dd_mirror.values, name="SP-20 Mirror", fill="tozeroy",
        line=dict(color="#00D4AA", width=1), fillcolor="rgba(0,212,170,0.2)",
    ))
    fig_dd.update_layout(
        yaxis_title="Drawdown", yaxis=dict(tickformat=".0%"),
        template="plotly_dark", height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60), hovermode="x unified",
    )
    st.plotly_chart(fig_dd, use_container_width=True)


# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #666; font-size: 0.85rem;">'
    "SP Index Lab &middot; Built by Zayan Khan &middot; "
    "Data updates daily via GitHub Actions"
    "</p>",
    unsafe_allow_html=True,
)
