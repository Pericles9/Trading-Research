"""
Phase 1b T5c - chart 01: trades vs momentum flags.
"""
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

BLUE = "#2a78d6"
GREEN = "#008300"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

with open("results/phase_1b/artifacts/bivariate_outlier_flag_summary.json") as f:
    fit_summary = json.load(f)
beta0 = fit_summary["quantreg_params"]["Intercept"]
beta1 = fit_summary["quantreg_params"]["log_trades"]
q = fit_summary["q_outlier"]

con = duckdb.connect(read_only=False)
flags = con.execute("SELECT * FROM read_parquet('results/phase_1b/artifacts/event_flags.parquet')").fetchdf()
cls = con.execute("SELECT ticker, class AS instrument_class FROM read_parquet('results/phase_1b/artifacts/instrument_classification.parquet')").fetchdf()
df = flags.merge(cls, on="ticker", how="left")

con_db = duckdb.connect(database="data/duckdb/main.duckdb", read_only=True)
bad_denom = con_db.execute(
    "SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, "
    "(prev_close < 0.01 OR momentum_pct >= 10000) AS flag_bad_denominator FROM momentum_events"
).fetchdf()
con_db.close()
bad_denom["event_date_str"] = bad_denom["event_date_canonical"].astype(str)
df["event_date_str"] = df["event_date_canonical"].astype(str)
df = df.merge(bad_denom[["ticker", "event_date_str", "flag_bad_denominator"]], on=["ticker", "event_date_str"], how="left")

fit_pop = df[
    df["instrument_class"].isin(["common", "common_adr"])
    & ~df["flag_bad_denominator"].fillna(False)
    & (df["n_trades_event_day"].fillna(0) > 0)
].copy()

def group(row):
    if row.get("flag_trades_mom_outlier"):
        return "bivariate"
    return "unflagged"

fit_pop["group"] = fit_pop.apply(group, axis=1)

# event_flags.parquet structurally excludes flag_bad_denominator=TRUE rows
# (T5's population query filtered them out before computing n_trades_event_day
# for anyone) - compute their true-calendar-day trade counts fresh here.
con_db2 = duckdb.connect(database="data/duckdb/main.duckdb", read_only=True)
mechanism = con_db2.execute(
    """
    SELECT me.ticker, COALESCE(me.date, me.event_date) AS event_date_canonical, me.momentum_pct,
           (SELECT COUNT(*) FROM filtered_trades ft
            WHERE ft.ticker = me.ticker AND ft.event_date = COALESCE(me.date, me.event_date)
              AND CAST(TO_TIMESTAMP(ft.sip_timestamp/1e9) AS DATE) = COALESCE(me.date, me.event_date)) AS n_trades_event_day
    FROM momentum_events me
    JOIN read_parquet('results/phase_1b/artifacts/instrument_classification.parquet') ic ON me.ticker = ic.ticker
    WHERE (me.prev_close < 0.01 OR me.momentum_pct >= 10000)
      AND ic.class IN ('common', 'common_adr')
    """
).fetchdf()
con_db2.close()
mechanism = mechanism[mechanism["n_trades_event_day"].fillna(0) > 0]

fig = go.Figure(layout=dict(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=13),
    height=640,
    title=dict(
        text=(f"Do the two outlier flags catch the artifact corner and only that corner? | "
              f"total n={len(fit_pop) + len(mechanism):,}"),
        x=0.02, xanchor="left", font=dict(size=15),
    ),
    xaxis=dict(type="log", title="n_trades_event_day (log)", gridcolor=GRID, rangeslider=dict(visible=True)),
    yaxis=dict(type="log", title="momentum_pct (log)", gridcolor=GRID),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=60, l=70, r=30),
))

unflagged = fit_pop[fit_pop["group"] == "unflagged"]
bivariate = fit_pop[fit_pop["group"] == "bivariate"]

fig.add_trace(go.Scattergl(
    x=unflagged["n_trades_event_day"], y=unflagged["momentum_pct"], mode="markers",
    marker=dict(color=BLUE, size=4, opacity=0.35), name=f"unflagged (n={len(unflagged):,})",
))
fig.add_trace(go.Scattergl(
    x=mechanism["n_trades_event_day"], y=mechanism["momentum_pct"], mode="markers",
    marker=dict(color=GREEN, size=6, opacity=0.7, symbol="diamond"), name=f"mechanism (n={len(mechanism):,})",
))
fig.add_trace(go.Scattergl(
    x=bivariate["n_trades_event_day"], y=bivariate["momentum_pct"], mode="markers",
    marker=dict(color=RED, size=6, opacity=0.8, symbol="x"), name=f"bivariate (n={len(bivariate):,})",
))

x_line = np.logspace(np.log10(fit_pop["n_trades_event_day"].min()), np.log10(fit_pop["n_trades_event_day"].max()), 200)
y_line = np.exp(beta0 + beta1 * np.log(x_line))
fig.add_trace(go.Scatter(
    x=x_line, y=y_line, mode="lines", line=dict(color=INK, width=2, dash="dash"),
    name=f"q={q} fitted line",
))

fig.update_layout(
    annotations=[
        dict(
            text=(f"n per flag group in legend. Fit: log(momentum_pct) ~ log(n_trades_event_day), "
                  f"q={q}, Intercept={beta0:.3f}, slope={beta1:.3f}. mechanism = flag_bad_denominator "
                  f"(prev_close<0.01 or momentum_pct>=10000); bivariate = above the fitted line. "
                  f"source: results/phase_1b/artifacts/bivariate_outlier_flag_summary.json"),
            xref="paper", yref="paper", x=0.02, y=-0.14, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1b/charts/01_trades_vs_momentum_flags.html", include_plotlyjs="inline")
print(f"chart 01 written: unflagged={len(unflagged)}, mechanism={len(mechanism)}, bivariate={len(bivariate)}")
