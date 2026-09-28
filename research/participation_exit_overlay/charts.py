"""
T4 charts.

01 -- event timeline strip. Four timestamps per event, sorted by window_close - participation_end.
      The picture that shows the mismatch directly.
02 -- gap distribution ECDFs: window_close - participation_end (the headline) and
      tau - participation_onset.
03 -- Exit A vs Exit B markout ECDFs, both cost bars drawn. The decision chart.
04 -- markout in the gap: price change from window_close to participation_end.
05 -- Exit A vs B by detection-price decile.
06 -- Exit A vs B by move_at decile -- tests whether the deeper-entry penalty (T3 of the v2 run,
      and R0-T0c2) survives a participation-tracking exit.

Usage: .venv/Scripts/python.exe research/participation_exit_overlay/charts.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.participation_exit_overlay import chart_common as K  # noqa: E402
from research.participation_exit_overlay import common as C  # noqa: E402

T2 = f"{C.ART}/t2_overlay.parquet"
T3 = f"{C.ART}/t3_counterfactual_exit.parquet"


def chart_01(d: pd.DataFrame) -> str:
    ok = d[d["bars_available"].fillna(False)].copy()
    ok = ok.sort_values("windowclose_minus_end_sec", na_position="last").reset_index(drop=True)
    ok["y"] = np.arange(len(ok))
    hr = 3600.0

    fig = go.Figure()
    censored = ok["end_censored"].fillna(False)
    fig.add_trace(go.Scatter(
        x=ok["sec_from_t0_tau"] / hr, y=ok["y"], mode="markers", name="τ (EPG entry)",
        marker=dict(size=3, color=K.BLUE),
        hovertemplate="τ %{x:.2f} h<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=ok["sec_from_t0_window_close"] / hr, y=ok["y"], mode="markers", name="window close (EPG exit)",
        marker=dict(size=3, color=K.ORANGE),
        hovertemplate="window close %{x:.2f} h<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=ok.loc[~censored, "sec_from_t0_end"] / hr, y=ok.loc[~censored, "y"], mode="markers",
        name="participation end", marker=dict(size=3, color=K.RED),
        hovertemplate="participation end %{x:.2f} h<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=ok["sec_from_t0_onset"] / hr, y=ok["y"], mode="markers", name="participation onset",
        marker=dict(size=3, color=K.AQUA, symbol="diamond"),
        hovertemplate="onset %{x:.2f} h<extra></extra>"))

    fig.update_xaxes(title_text="hours from t0 (log-ish view via range; not log-scaled)",
                     range=[-0.2, 8])
    fig.update_yaxes(title_text=f"events, sorted by window_close − participation_end "
                                f"(n={len(ok):,}, {int(censored.sum())} censored not plotted "
                                f"on the red series)")
    cap = K.caption(
        sample=f"gap-gated first-window entries with bars available, n={len(ok):,}",
        filters="none — every event plotted; censored events (13.4%) have no red marker, which "
                "is itself the point: participation never decayed inside the session for them.",
        extra="Where the orange dot (window close) sits LEFT of the red dot (participation end), "
              "EPG exited while participation was still live. That is most of the picture.")
    K.base_layout(fig, "T4-01 · event timeline — τ, window close, participation onset/end",
                  cap, height=760, cap_y=-0.20, margin_b=210)
    return K.write(fig, "01_event_timeline_strip.html")


def ecdf(fig, v, label, color):
    v = np.sort(v[np.isfinite(v)])
    if v.size == 0:
        return
    y = np.arange(1, v.size + 1) / v.size
    fig.add_trace(go.Scatter(x=v, y=y, mode="lines", name=f"{label} (n={v.size:,}, "
                             f"median {np.quantile(v,.5):+,.0f})",
                             line=dict(color=color, width=2)))


def chart_02(d: pd.DataFrame) -> str:
    ok = d[d["bars_available"].fillna(False)]
    fig = go.Figure()
    ecdf(fig, ok["windowclose_minus_end_sec"].to_numpy() / 60.0,
        "window_close − participation_end (min)", K.RED)
    ecdf(fig, ok["tau_minus_onset_sec"].to_numpy() / 60.0,
        "τ − participation_onset (min)", K.BLUE)
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color=K.INK2)
    fig.update_xaxes(title_text="minutes (view window ±180 min)", range=[-180, 180])
    fig.update_yaxes(title_text="cumulative share", range=[0, 1])
    cap = K.caption(
        sample=f"n={int(ok['windowclose_minus_end_sec'].notna().sum()):,} for the headline "
               f"(782, 13.4% censored and excluded by construction), "
               f"n={int(ok['tau_minus_onset_sec'].notna().sum()):,} for the entry gap",
        filters="view window ±180 minutes for legibility; curves run flat past it, nothing "
                "clipped from the statistics.",
        extra="Red crosses zero far to the LEFT of 0.5 — most events exit before participation "
              "ends. Blue sits close to zero — EPG's entry timing is not the problem.")
    K.base_layout(fig, "T4-02 · the two gap distributions", cap, height=680, cap_y=-0.26,
                  margin_b=230)
    return K.write(fig, "02_gap_distributions_ecdf.html")


def chart_03(t3: pd.DataFrame, cost_bp: float) -> str:
    unc = t3[t3["priced"] & ~t3["exit_b_censored"].fillna(False)].copy()
    ga = (unc["exit_a_price_tick"] / unc["entry_price"] - 1) * 1e4
    gb = (unc["exit_b_price_tick"] / unc["entry_price"] - 1) * 1e4
    fig = go.Figure()
    ecdf(fig, ga.to_numpy(), "A · window close", K.BLUE)
    ecdf(fig, gb.to_numpy(), "B · participation decay", K.ORANGE)
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_vline(x=cost_bp, line_width=1.5, line_dash="dot", line_color=K.RED)
    fig.add_annotation(x=cost_bp, y=1.0, yref="paper", yanchor="bottom",
                       text=f"flat cost {cost_bp:.0f} bp", showarrow=False,
                       font=dict(size=10, color=K.RED))
    med_ps = float(np.nanmedian(unc["cost_cents_bp"]))
    fig.add_vline(x=med_ps, line_width=1.5, line_dash="dot", line_color=K.INK2)
    fig.add_annotation(x=med_ps, y=0.92, yref="paper", yanchor="bottom",
                       text=f"median per-share cost {med_ps:.0f} bp", showarrow=False,
                       font=dict(size=10, color=K.INK2))
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color=K.INK2)
    fig.update_xaxes(title_text="gross markout (bp; view window ±5,000)", range=[-5000, 5000])
    fig.update_yaxes(title_text="cumulative share of trades", range=[0, 1])
    cap = K.caption(
        sample=f"uncensored, like-for-like pair, n={len(unc):,}",
        filters="censored events (participation never decays in-session) excluded from this "
                "chart and reported as their own class in the report — a session-end hold is a "
                "different risk under D5.",
        extra="THE DECISION CHART. One round trip in each arm — B is the same cost amortised "
              "over a longer hold, not a second round trip.")
    K.base_layout(fig, "T4-03 · Exit A vs Exit B — the counterfactual", cap, height=700,
                  cap_y=-0.24, margin_b=240)
    return K.write(fig, "03_exit_a_vs_b_ecdf.html")


def chart_04(t3: pd.DataFrame) -> str:
    ok = t3[t3["priced"]].copy()
    gap = (ok["exit_b_price_tick"] / ok["exit_a_price_tick"] - 1) * 1e4
    v = np.sort(gap[np.isfinite(gap)].to_numpy())
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=v, nbinsx=80, marker_color=K.rgba(K.VIOLET, .75)))
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_vline(x=float(np.median(v)), line_width=2, line_dash="dot", line_color=K.RED)
    fig.update_xaxes(title_text="price change, window close → participation-decay exit (bp; "
                                "view window ±6,000)", range=[-6000, 6000])
    fig.update_yaxes(title_text="events (count)")
    cap = K.caption(
        sample=f"all priced events, n={v.size:,}, includes censored (exiting at the session-end "
               "horizon)",
        filters="view window ±6,000 bp for legibility; the distribution has a heavy right tail "
                "beyond it, not clipped from the median/mean reported in text.",
        extra="Positive = what EPG left on the table by exiting early. Negative = what EPG "
              "avoided by exiting early. Median is the dotted red line.")
    K.base_layout(fig, "T4-04 · markout in the gap (window close → participation decay)", cap,
                  height=660, cap_y=-0.28, margin_b=230)
    return K.write(fig, "04_markout_in_the_gap.html")


def by_decile_chart(t3: pd.DataFrame, dec_col: str, title: str, xaxis: str, fname: str) -> str:
    unc = t3[t3["priced"] & ~t3["exit_b_censored"].fillna(False)].copy()
    unc = unc[unc[dec_col].notna()]
    ga = (unc["exit_a_price_tick"] / unc["entry_price"] - 1) * 1e4
    gb = (unc["exit_b_price_tick"] / unc["entry_price"] - 1) * 1e4
    unc = unc.assign(ga=ga, gb=gb)
    g = unc.groupby(dec_col)
    x = sorted(unc[dec_col].unique())
    n = g.size().reindex(x).to_numpy()
    fig = go.Figure()
    for col, color, name in [("ga", K.BLUE, "A · window close"), ("gb", K.ORANGE,
                                                                   "B · participation decay")]:
        med = g[col].median().reindex(x).to_numpy()
        fig.add_trace(go.Scatter(x=x, y=med, mode="lines+markers", name=f"{name} — median",
                                 line=dict(color=color, width=2.5), marker=dict(size=8),
                                 text=[f"n={v}" for v in n], textposition="top center",
                                 hovertemplate=name + "<br>decile %{x}<br>%{y:,.0f} bp"
                                               "<extra></extra>"))
    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.update_xaxes(title_text=xaxis, tickmode="array", tickvals=x)
    fig.update_yaxes(title_text="gross markout, median (bp)")
    cap = K.caption(
        sample=f"uncensored like-for-like pair, n={len(unc):,}",
        filters="censored events excluded and reported separately; n annotated per decile.",
        extra="")
    K.base_layout(fig, title, cap, height=680, cap_y=-0.26, margin_b=220)
    return K.write(fig, fname)


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["cost"]["round_trip_bp"]
    d = pd.read_parquet(C.REPO / T2)
    t3 = pd.read_parquet(C.REPO / T3)
    out = [
        chart_01(d),
        chart_02(d),
        chart_03(t3, cost_bp),
        chart_04(t3),
        by_decile_chart(t3, "detection_price_decile",
                        "T4-05 · Exit A vs Exit B by detection-price decile",
                        "detection-price decile (0 = cheapest)", "05_by_detection_price_decile.html"),
        by_decile_chart(t3, "move_at_decile",
                        "T4-06 · Exit A vs Exit B by move_at decile — does the deeper-entry "
                        "penalty survive a participation exit?",
                        "move_at decile at entry (0 = least moved)", "06_by_move_at_decile.html"),
    ]
    C.write_json(f"{C.ART}/charts.json", {"task": "T4 charts", "config_hash": C.cfg_hash(),
                                          "charts": out})
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
