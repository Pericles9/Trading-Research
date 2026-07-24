"""
Phase 6c A7.1 - charts 01-03 (population-level diagnostic views, all 55
events with defined r1'/r2'). Read-only against event_minute_bars_dev_v2
(dev-tier, already materialized - not a full-table pass) and the
already-committed A6.1/T2 artifacts. No reclassification here - the 7
residuals keep their T2 label (or 'unexplained' is left as-is); the 48
non-residual events are labeled 'passing' for color purposes only.
"""
import json

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

A61_ARTIFACT = "results/phase_6b/artifacts/a61_basis_confirmation_rerun.json"
T2_ARTIFACT = "results/phase_6c/artifacts/t2_residual_classification.json"
DB_PATH = "data/duckdb/main.duckdb"
DEV_BARS_TABLE = "event_minute_bars_dev_v2"
OUT_SUMMARY = "results/phase_6c/artifacts/a71_chartpack_summary.json"

COLORS = {
    "passing": "rgba(120,120,120,0.55)",
    "band_margin": "rgb(31,119,180)",
    "coverage_gap": "rgb(214,39,40)",
    "unexplained": "rgb(255,140,0)",
}


def symlog(x, linthresh=0.02):
    """sign(x) * log10(1 + |x|/linthresh) * linthresh - linear within
    +-linthresh, logarithmic beyond it. Used for chart 02/03's y-axes
    per the amendment's 'symlog y' spec (plotly has no native symlog
    axis type)."""
    x = np.asarray(x, dtype=float)
    return np.sign(x) * linthresh * np.log10(1.0 + np.abs(x) / linthresh)


def symlog_ticks(values, linthresh=0.02):
    vals = sorted(set(values))
    return [symlog(v, linthresh) for v in vals], [f"{v:g}" for v in vals]


def band_count(offset, con, full):
    rows = []
    for row in full.itertuples(index=False):
        d = pd.Timestamp(row.event_date_canonical).date()
        n = con.execute(f"""
            SELECT COUNT(*) FROM {DEV_BARS_TABLE}
            WHERE ticker=? AND event_date_canonical=? AND ROUND(momentum_pct,2)=ROUND(?,2)
              AND session_offset=? AND segment='rth'
        """, [row.ticker, d, row.momentum_pct, offset]).fetchone()[0]
        rows.append(n)
    return rows


def main():
    with open(A61_ARTIFACT) as f:
        a61 = json.load(f)
    with open(T2_ARTIFACT) as f:
        t2 = json.load(f)

    full = pd.DataFrame(a61["full_table"])
    full["event_date_canonical"] = pd.to_datetime(full["event_date_canonical"])
    both = full[full["r1p"].notna() & full["r2p"].notna()].copy()
    both["rel_diff"] = (both["r1p"] - both["r2p"]).abs() / both["r2p"]

    con = duckdb.connect(DB_PATH, read_only=True)
    both["rth_t0"] = band_count(0, con, both)
    both["rth_tm1"] = band_count(-1, con, both)
    con.close()
    both["min_rth"] = both[["rth_t0", "rth_tm1"]].min(axis=1)

    primary_median_min_rth = float(both[both["dev_cohort"] == "primary"]["min_rth"].median())

    class_by_ticker = {c["ticker"]: c["classification"] for c in t2["classifications"]}
    both["t2_class"] = both["ticker"].map(class_by_ticker).fillna("passing")
    both["geo_mean_dev"] = np.sqrt(both["r1p"] * both["r2p"]) - 1.0
    both["min_rth_pct_of_primary_median"] = 100.0 * both["min_rth"] / primary_median_min_rth
    residual_tickers = list(class_by_ticker.keys())

    # ---- Chart 01: |r1'-r2'|/r2' by cohort ----
    # Display floor at 1e-6: a handful of events land at machine-epsilon
    # (~1e-16, e.g. APLD 6.00/6.00 exact) - true value kept in hover text,
    # only the plotted y is floored so the log axis isn't dominated by
    # floating-point noise at the bottom.
    DISPLAY_FLOOR = 1e-6
    both["rel_diff_display"] = both["rel_diff"].clip(lower=DISPLAY_FLOOR)

    fig1 = go.Figure()
    for cohort, color in [("primary", "rgb(31,119,180)"), ("flagged_sidecar", "rgb(214,39,40)")]:
        sub = both[both["dev_cohort"] == cohort]
        x = np.full(len(sub), 0 if cohort == "primary" else 1) + np.random.default_rng(42).uniform(-0.08, 0.08, len(sub))
        fig1.add_trace(go.Scatter(
            x=x, y=sub["rel_diff_display"], mode="markers",
            marker=dict(color=color, size=8, opacity=0.6),
            name=f"{cohort} (n={len(sub)})",
            text=sub["ticker"], customdata=sub["rel_diff"], hovertemplate="%{text}<br>rel_diff=%{customdata:.2e}",
        ))
    residual_rows = both[both["ticker"].isin(residual_tickers)].sort_values("dev_cohort")
    ay_offsets_by_cohort = {}
    for _, row in residual_rows.iterrows():
        x0 = 0 if row["dev_cohort"] == "primary" else 1
        k = ay_offsets_by_cohort.get(row["dev_cohort"], 0)
        ay_offsets_by_cohort[row["dev_cohort"]] = k + 1
        fig1.add_annotation(x=x0, y=row["rel_diff_display"], text=row["ticker"], showarrow=True, arrowhead=1,
                             ax=35 + 20 * (k % 2), ay=-15 - 22 * k,
                             font=dict(size=10, color=COLORS[row["t2_class"]]))
    fig1.add_hline(y=0.02, line=dict(color="black", dash="dash"), annotation_text="2% band")
    fig1.update_xaxes(tickvals=[0, 1], ticktext=[f"primary (n={len(both[both.dev_cohort=='primary'])})", f"sidecar (n={len(both[both.dev_cohort=='flagged_sidecar'])})"], range=[-0.5, 1.7])
    fig1.update_yaxes(title_text="|r1' - r2'| / r2' (floored at 1e-6 for display)", type="log", range=[-6.3, 0.3])
    fig1.update_layout(title="Chart 01: r1'/r2' agreement by cohort (n=55)", height=600, width=950,
                        annotations=list(fig1.layout.annotations) + [dict(
                            text="Descriptive: each point is one event's ratio disagreement (true value in hover; y floored at 1e-6 for display only). Residuals labeled by name, color = T2 classification.",
                            xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color="gray"))])
    fig1.write_html("results/phase_6c/charts/01_r_agreement_by_cohort.html")
    fig1.write_image("results/phase_6c/charts/01_r_agreement_by_cohort.png", scale=1.5)

    # ---- Chart 02: deviation vs thinness (P2) ----
    LINTHRESH_02 = 0.02
    both["geo_mean_dev_symlog"] = symlog(both["geo_mean_dev"], LINTHRESH_02)

    fig2 = go.Figure()
    for cls, color in COLORS.items():
        sub = both[both["t2_class"] == cls]
        if len(sub) == 0:
            continue
        fig2.add_trace(go.Scatter(
            x=sub["min_rth_pct_of_primary_median"], y=sub["geo_mean_dev_symlog"], mode="markers",
            marker=dict(color=color, size=9, opacity=0.7), name=f"{cls} (n={len(sub)})",
            text=sub["ticker"], customdata=sub["geo_mean_dev"], hovertemplate="%{text}<br>thinness=%{x:.1f}%%<br>dev=%{customdata:.4f}",
        ))
    for _, row in both[both["ticker"].isin(residual_tickers)].iterrows():
        fig2.add_annotation(x=row["min_rth_pct_of_primary_median"], y=row["geo_mean_dev_symlog"], text=row["ticker"],
                             showarrow=True, arrowhead=1, ax=20, ay=-15, font=dict(size=10))
    fig2.add_shape(type="rect", xref="x domain", x0=0, x1=1, yref="y",
                   y0=symlog(-0.02, LINTHRESH_02), y1=symlog(0.02, LINTHRESH_02),
                   fillcolor="rgba(0,0,0,0.06)", line_width=0)
    fig2.add_annotation(text="2% band", xref="paper", x=0.01, yref="y", y=symlog(0.02, LINTHRESH_02), showarrow=False,
                        font=dict(size=10), xanchor="left", yanchor="bottom")
    x_lo, x_hi = both["min_rth_pct_of_primary_median"].min(), both["min_rth_pct_of_primary_median"].max()
    import math
    fig2.update_xaxes(title_text="min(T-1, T+0) RTH bar count, as % of primary-cohort median", type="log",
                       range=[math.log10(x_lo) - 0.15, math.log10(x_hi) + 0.15], autorange=False)
    ytickvals, yticktext = symlog_ticks([-0.5, -0.1, -0.02, 0, 0.02, 0.1, 1, 10, 100, 750], LINTHRESH_02)
    fig2.update_yaxes(title_text="geometric-mean ratio deviation: sqrt(r1'*r2') - 1 (symlog, linthresh=0.02)",
                       tickvals=ytickvals, ticktext=yticktext)
    fig2.update_layout(title=f"Chart 02: deviation vs. tape thinness (P2) - all events, n={len(both)}", height=600, width=950,
                        annotations=list(fig2.layout.annotations) + [dict(
                            text=f"Descriptive: primary-cohort median min_rth = {primary_median_min_rth:.1f} bars = 100% on x. P2 predicts deviation grows as thinness (x) falls.",
                            xref="paper", yref="paper", x=0, y=-0.14, showarrow=False, font=dict(size=10, color="gray"))])
    fig2.write_html("results/phase_6c/charts/02_deviation_vs_thinness.html")
    fig2.write_image("results/phase_6c/charts/02_deviation_vs_thinness.png", scale=1.5)

    # ---- Chart 03: leg direction (P1, P3) ----
    LINTHRESH_03 = 0.02
    both["r1p_m1_symlog"] = symlog(both["r1p"] - 1, LINTHRESH_03)
    both["r2p_m1_symlog"] = symlog(both["r2p"] - 1, LINTHRESH_03)

    fig3 = go.Figure()
    order = both.sort_values("geo_mean_dev").reset_index(drop=True)
    order["x"] = np.arange(len(order))
    for _, row in order.iterrows():
        color = COLORS[row["t2_class"]]
        fig3.add_trace(go.Scatter(x=[row["x"], row["x"]], y=[row["r1p_m1_symlog"], row["r2p_m1_symlog"]], mode="lines+markers",
                                   line=dict(color=color, width=1.5), marker=dict(size=5, color=color),
                                   showlegend=False,
                                   customdata=[[row["r1p"] - 1], [row["r2p"] - 1]],
                                   hovertemplate=f"{row['ticker']}" + "<br>value=%{customdata[0]:.3f}"))
    for cls, color in COLORS.items():
        fig3.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=color, width=3), name=cls))
    for _, row in order[order["ticker"].isin(residual_tickers)].iterrows():
        fig3.add_annotation(x=row["x"], y=max(row["r1p_m1_symlog"], row["r2p_m1_symlog"]), text=row["ticker"], showarrow=True,
                             arrowhead=1, ax=0, ay=-20, font=dict(size=10))
    fig3.add_hline(y=0, line=dict(color="black", dash="dot"))
    fig3.update_xaxes(title_text="events, sorted by geometric-mean deviation", showticklabels=False)
    ytickvals3, yticktext3 = symlog_ticks([-0.5, -0.1, -0.02, 0, 0.02, 0.1, 1, 10, 100, 750], LINTHRESH_03)
    fig3.update_yaxes(title_text="r1'-1 (bottom marker) / r2'-1 (top marker) per event (symlog, linthresh=0.02)",
                       tickvals=ytickvals3, ticktext=yticktext3)
    fig3.update_layout(title=f"Chart 03: leg direction, r1'-1 vs r2'-1 per event (P1, P3) - n={len(both)}", height=600, width=1100,
                        annotations=list(fig3.layout.annotations) + [dict(
                            text="Descriptive: each vertical segment connects one event's (r1'-1) and (r2'-1). P1 predicts residual segments stay >=0 (never below zero) if thinness-driven.",
                            xref="paper", yref="paper", x=0, y=-0.1, showarrow=False, font=dict(size=10, color="gray"))])
    fig3.write_html("results/phase_6c/charts/03_leg_direction.html")
    fig3.write_image("results/phase_6c/charts/03_leg_direction.png", scale=1.5)

    plotted = both[["ticker", "event_date_canonical", "dev_cohort", "t2_class", "r1p", "r2p", "rel_diff",
                    "rth_t0", "rth_tm1", "min_rth", "min_rth_pct_of_primary_median", "geo_mean_dev",
                    "geo_mean_dev_symlog", "r1p_m1_symlog", "r2p_m1_symlog"]].copy()
    plotted["event_date_canonical"] = plotted["event_date_canonical"].astype(str)
    summary = {
        "phase": "6c", "task": "A7.1", "primary_median_min_rth": primary_median_min_rth,
        "n_events_plotted": len(both),
        "plotted_values": plotted.to_dict(orient="records"),
        "source": "research/phase_6c/a71_charts_01_03.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"charts 01-03 written. primary_median_min_rth={primary_median_min_rth}")
    print(f"n_events={len(both)}")


if __name__ == "__main__":
    main()
