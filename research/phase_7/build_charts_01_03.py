"""
Phase 7 charts 01-03. Standalone Plotly HTML, one per file, n annotated,
config-hash caption (Agent_Prompt_Standard SS9). dataviz palette (light):
series blue #2a78d6, orange #eb6834, aqua #1baf7a; ink #0b0b0b / #52514e;
gridline #e1e0d9; surface #fcfcfb.

All curves re-pool Phase 6's per-event artifacts by membership (same method
as T3, scan-free). Flag membership = 736-key set == view flag_eth_dominant_t0.
"""
import hashlib
import json

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_6 import measurements as M

ART = "results/phase_6_rth_only/artifacts"
ETH_SRC = f"{ART}/t3_excluded_t0_rows.parquet"
PER_MINUTE = f"{ART}/opportunity_decay_per_minute.parquet"
PER_MINUTE_SENS = f"{ART}/opportunity_decay_per_minute_sens.parquet"
MIN_WINDOW = f"{ART}/min_window_stats.parquet"
OUT = "results/phase_7/charts"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
THRESHOLD = 0.5


def cfg_hash():
    with open("config/phase_7.json", "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def _keyframe(df):
    out = df.copy()
    out["_key"] = list(zip(out["ticker"],
                           pd.to_datetime(out["event_date_canonical"]).dt.strftime("%Y-%m-%d"),
                           out["momentum_pct"].round(2)))
    return out


def load_flagged_keys():
    con = duckdb.connect()
    f = con.execute(f"""
        SELECT ticker, CAST(CAST(event_date_canonical AS DATE) AS VARCHAR) d, ROUND(momentum_pct,2) m, excluded_share
        FROM read_parquet('{ETH_SRC}') WHERE excluded_share > {THRESHOLD}
    """).fetchdf()
    con.close()
    return f, set(zip(f["ticker"], f["d"], f["m"]))


def chart_01(flagged_df):
    """ECDF + histogram of t0_eth_row_share over the 736, x in [0.5,1.0], top-10 labeled."""
    s = flagged_df["excluded_share"].to_numpy()
    s_sorted = np.sort(s)
    ecdf = np.arange(1, len(s_sorted) + 1) / len(s_sorted)
    top10 = flagged_df.sort_values("excluded_share", ascending=False).head(10)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # histogram (bars, left y)
    fig.add_trace(go.Histogram(
        x=s, xbins=dict(start=0.5, end=1.0, size=0.02), marker=dict(color=BLUE, line=dict(color=SURFACE, width=1)),
        opacity=0.55, name="histogram (count/bin)", hovertemplate="share %{x}<br>count=%{y}<extra></extra>",
    ), secondary_y=False)
    # ECDF (line, right y)
    fig.add_trace(go.Scatter(
        x=s_sorted, y=ecdf, mode="lines", line=dict(color=ORANGE, width=2), name="ECDF",
        hovertemplate="share %{x:.3f}<br>ECDF=%{y:.3f}<extra></extra>",
    ), secondary_y=True)
    fig.add_vline(x=THRESHOLD, line=dict(color=INK, dash="dash", width=1.5),
                  annotation_text="threshold 0.5", annotation_position="top left")
    # top-10 as a single clean text block in the empty upper-middle region
    top10_lines = "<br>".join(
        f"{i+1:>2}. {r.ticker} {r.d}  {r.excluded_share:.3f}"
        for i, r in enumerate(top10.itertuples(index=False))
    )
    fig.add_annotation(
        x=0.66, y=0.97, xref="x", yref="paper",
        text="<b>Top 10 by share</b><br>" + top10_lines, showarrow=False,
        align="left", font=dict(size=9, color=INK2, family="monospace"),
        bordercolor=GRID, borderwidth=1, borderpad=6, bgcolor="rgba(252,252,251,0.85)",
        xanchor="left", yanchor="top",
    )
    fig.update_layout(
        title=f"Flagged ETH-dominant T=0 events: excluded-row-share distribution (n=736)",
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=560, width=1100,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        bargap=0.05,
    )
    fig.update_xaxes(title="t0_eth_row_share (T=0 tick rows outside RTH / total)", range=[0.5, 1.0], gridcolor=GRID)
    fig.update_yaxes(title_text="count per 0.02 bin", secondary_y=False, gridcolor=GRID)
    fig.update_yaxes(title_text="ECDF", secondary_y=True, range=[0, 1.02])
    fig.add_annotation(text=f"n=736 | threshold 0.5 sits on a declining shoulder, not a mode | source: {ETH_SRC} (excluded_share > 0.5) | config {cfg_hash()}",
                       xref="paper", yref="paper", x=0, y=-0.16, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "01_t0_eth_share_flagged")


def _pooled(pm_kf, keys=None, exclude=False):
    if keys is not None:
        pm_kf = pm_kf[~pm_kf["_key"].isin(keys)] if exclude else pm_kf[pm_kf["_key"].isin(keys)]
    return M.pooled_per_minute_quantiles(pm_kf)


def chart_02(flagged_keys):
    """Pooled median + IQR opportunity decay, 4 curves, 4 crossings annotated."""
    pm = _keyframe(pd.read_parquet(PER_MINUTE))
    pm_s = _keyframe(pd.read_parquet(PER_MINUTE_SENS))
    n_full = pm[["ticker", "event_date_canonical", "momentum_pct"]].drop_duplicates().shape[0]
    n_excl = pm[~pm["_key"].isin(flagged_keys)][["ticker", "event_date_canonical", "momentum_pct"]].drop_duplicates().shape[0]

    curves = {
        "full, with min 0": (_pooled(pm), BLUE, "solid", n_full),
        "full, excl min 0": (_pooled(pm_s), BLUE, "dash", n_full),
        "excl-flagged, with min 0": (_pooled(pm, flagged_keys, exclude=True), ORANGE, "solid", n_excl),
        "excl-flagged, excl min 0": (_pooled(pm_s, flagged_keys, exclude=True), ORANGE, "dash", n_excl),
    }
    fig = go.Figure()
    for name, (pooled, color, dash, n) in curves.items():
        p = pooled.sort_values("minute_index")
        # IQR band only for the two "with min 0" curves to avoid clutter
        if dash == "solid":
            fig.add_trace(go.Scatter(x=list(p["minute_index"]) + list(p["minute_index"][::-1]),
                                     y=list(p["q75"]) + list(p["q25"][::-1]), fill="toself",
                                     fillcolor=color.replace(")", ",0.10)").replace("#", "rgba(") if False else _rgba(color, 0.10),
                                     line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=p["minute_index"], y=p["median"], mode="lines",
                                 line=dict(color=color, width=2, dash=dash), name=f"{name} (n={n})",
                                 hovertemplate=name + "<br>min %{x}<br>median frac=%{y:.3f}<extra></extra>"))
        cx = M.pooled_median_crossing_minute(pooled)
        if not np.isnan(cx):
            fig.add_annotation(x=cx, y=0.5, text=f"{int(cx)}", showarrow=True, arrowhead=2, ax=0, ay=-25 if dash == "solid" else 25,
                               font=dict(size=11, color=color), arrowcolor=color)
    fig.add_hline(y=0.5, line=dict(color=INK, dash="dot", width=1), annotation_text="50% realized move")
    fig.update_layout(
        title="Opportunity decay: pooled median realized-move-fraction, full vs. excl-flagged",
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=600, width=1150,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(title="minutes since T=0 session open", range=[0, 180], gridcolor=GRID)
    fig.update_yaxes(title="pooled median realized-move-fraction (IQR band on 'with min 0')", range=[0, 1.2], gridcolor=GRID)
    fig.add_annotation(text=f"n full={n_full}, excl-flagged={n_excl} | crossings with min0: 52->54; excl min0: 57->58 (both < 5-min escalation) | config {cfg_hash()}",
                       xref="paper", yref="paper", x=0, y=-0.15, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "02_decay_sensitivity")


def chart_03(flagged_keys):
    """25/50/75% min-window CDFs, full vs excl-flagged (6 curves), medians marked."""
    mw = _keyframe(pd.read_parquet(MIN_WINDOW))
    mw_ex = mw[~mw["_key"].isin(flagged_keys)]
    n_full = mw.shape[0]; n_excl = mw_ex.shape[0]
    cols = {"25pct": ("min_window_25pct_minutes", BLUE), "50pct": ("min_window_50pct_minutes", ORANGE), "75pct": ("min_window_75pct_minutes", AQUA)}

    fig = go.Figure()
    for label, (col, color) in cols.items():
        for pop, df, dash in [("full", mw, "solid"), ("excl-flagged", mw_ex, "dash")]:
            v = np.sort(df[col].to_numpy())
            cdf = np.arange(1, len(v) + 1) / len(v)
            fig.add_trace(go.Scatter(x=v, y=cdf, mode="lines", line=dict(color=color, width=2, dash=dash),
                                     name=f"{label} {pop}", hovertemplate=f"{label} {pop}<br>minutes=%{{x}}<br>CDF=%{{y:.3f}}<extra></extra>"))
            med = float(np.median(df[col]))
            fig.add_vline(x=med, line=dict(color=color, dash=dash, width=1), opacity=0.4)
    fig.update_layout(
        title=f"Minimum-window CDFs (25/50/75% of T=0 volume): full (n={n_full}) vs. excl-flagged (n={n_excl})",
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=600, width=1150,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(title="minimum contiguous window (minutes, log)", type="log", gridcolor=GRID)
    fig.update_yaxes(title="CDF over events", range=[0, 1.02], gridcolor=GRID)
    fig.add_annotation(text=f"solid=full, dashed=excl-flagged; vertical lines = medians | source: {MIN_WINDOW} (with min 0 variant) | config {cfg_hash()}",
                       xref="paper", yref="paper", x=0, y=-0.15, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "03_min_window_cdf_sensitivity")


def _rgba(hexc, a):
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def _write(fig, name):
    path = f"{OUT}/{name}.html"
    fig.write_html(path)
    try:
        fig.write_image(f"{OUT}/{name}.png", scale=1.4)
    except Exception as e:
        print(f"  png export failed ({name}, non-fatal): {e}")
    print(f"wrote {path}")


def main():
    flagged_df, flagged_keys = load_flagged_keys()
    chart_01(flagged_df)
    chart_02(flagged_keys)
    chart_03(flagged_keys)


if __name__ == "__main__":
    main()
