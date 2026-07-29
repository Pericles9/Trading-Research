"""
Phase 6b A6.3c (T5) - charts 01-07 (chart 08 dropped, A8.2). Standalone
Plotly HTML, one per file, n annotated, config-hash caption. dataviz palette.
Reads T4 artifacts only. Chart 04's primary anchor is tick_close_t_minus_1_rth.
"""
import hashlib
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_6.chart_common import pooled_curve_by_group, seeded_overlay_groups
from research.phase_6b import measurements_v2 as M2

A = "results/phase_6b/artifacts"
C = "results/phase_6b/charts"
CFG = "config/phase_6b.json"
ELIG = f"{A}/t1_eligible_events.parquet"

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GREEN, VIOLET, RED = "#008300", "#4a3aa7", "#e34948"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
DECILE_COLORS = [BLUE, ORANGE, AQUA, YELLOW, "#e87ba4", GREEN, VIOLET, RED, "#6da7ec", "#898781"]


def cfg_hash():
    with open(CFG, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def _rgba(hexc, a):
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def _write(fig, name):
    path = f"{C}/{name}.html"
    fig.write_html(path)
    try:
        fig.write_image(f"{C}/{name}.png", scale=1.35)
    except Exception as e:
        print(f"  png export failed ({name}): {e}")
    print(f"wrote {path}")


def _events_deciles():
    ev = pd.read_parquet(ELIG)
    ev["event_date_canonical"] = pd.to_datetime(ev["event_date_canonical"])
    ev["decile"] = pd.qcut(ev["momentum_pct"], 10, labels=False, duplicates="drop")
    return ev


def _rth_rule_time_shares():
    """Median RTH open/close as a fraction of the extended day, for vertical rules."""
    from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2
    with open(CFG) as f:
        cfg = json.load(f)
    ev = _events_deciles()
    spine = build_session_spine_v2(ev, cfg)
    sb = M2.session_bounds_from_spine(spine, offset=0)
    return float((sb["rth_open_min"] / sb["session_total_minutes"]).median()), \
           float((sb["rth_close_min"] / sb["session_total_minutes"]).median())


def _concentration_chart(value_col, name, fname, question):
    conc = pd.read_parquet(f"{A}/concentration_curves_v2.parquet")
    ev = _events_deciles()
    conc = conc.merge(ev[M2.EVENT_KEYS + ["decile"]], on=M2.EVENT_KEYS, how="left")
    t_grid = np.linspace(0, 1, 101)
    pooled = pooled_curve_by_group(conc, "decile", value_col, "time_share", t_grid)
    rth_open_ts, rth_close_ts = _rth_rule_time_shares()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=INK2, dash="dot", width=1),
                             name="diagonal", hoverinfo="skip"))
    for d in sorted(k for k in pooled if not np.isnan(k)):
        c = DECILE_COLORS[int(d) % 10]
        med = pooled[d]["median"]; n = pooled[d]["n"]
        fig.add_trace(go.Scatter(x=t_grid, y=med, mode="lines", line=dict(color=c, width=1.6),
                                 name=f"decile {int(d)} (n={n})", hovertemplate=f"decile {int(d)}<br>time=%{{x:.2f}}<br>share=%{{y:.3f}}<extra></extra>"))
    for xr, lab in [(rth_open_ts, "RTH open"), (rth_close_ts, "RTH close")]:
        fig.add_vline(x=xr, line=dict(color=INK, dash="dash", width=1), annotation_text=lab, annotation_font=dict(size=9))
    fig.update_layout(title=f"{name} concentration on the extended-day clock, pooled median by momentum decile",
                      plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=600, width=1080,
                      legend=dict(font=dict(size=9)))
    fig.update_xaxes(title="extended-day time share (04:00 ET → close)", range=[0, 1], gridcolor=GRID)
    fig.update_yaxes(title=f"cumulative {name} share", range=[0, 1], gridcolor=GRID)
    fig.add_annotation(text=f"n per decile in legend | RTH rules = population median | {question} | config {cfg_hash()}",
                       xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, fname)


def chart_01():
    _concentration_chart("volume_share", "volume", "01_volume_concentration_ext", "front-loaded volume?")


def chart_02():
    _concentration_chart("move_share", "move", "02_move_concentration_ext", "front-loaded price path?")


def chart_03():
    mw = pd.read_parquet(f"{A}/min_window_stats_v2.parquet")
    cols = {"25pct": ("min_window_25pct_minutes", BLUE), "50pct": ("min_window_50pct_minutes", ORANGE), "75pct": ("min_window_75pct_minutes", AQUA)}
    fig = go.Figure()
    for label, (col, color) in cols.items():
        v = np.sort(mw[col].to_numpy()); cdf = np.arange(1, len(v) + 1) / len(v)
        fig.add_trace(go.Scatter(x=v, y=cdf, mode="lines", line=dict(color=color, width=2), name=f"{label} (median {np.median(v):.0f}m)"))
    fig.update_layout(title=f"Minimum-window CDFs: shortest span holding 25/50/75% of extended-day volume (n={len(mw)})",
                      plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=580, width=1080)
    fig.update_xaxes(title="minimum contiguous window (minutes, log)", type="log", gridcolor=GRID)
    fig.update_yaxes(title="CDF over events", range=[0, 1.02], gridcolor=GRID)
    fig.add_annotation(text=f"n={len(mw)} | config {cfg_hash()}", xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "03_min_window_cdf_ext")


def chart_04():
    pooled = pd.read_parquet(f"{A}/pooled_decay_primary.parquet").sort_values("minute_index")
    pooled_rth = pd.read_parquet(f"{A}/pooled_decay_rth_legacy.parquet").sort_values("minute_index")
    summ = json.load(open(f"{A}/t4_measurements_v2_summary.json"))
    cross = summ["headlines"]["a_primary_pooled_median_crossing_minute_since_0400et"]
    cross_rth = summ["headlines"]["rth_legacy_pooled_median_crossing_minute_since_open"]
    rth_open_ts, rth_close_ts = _rth_rule_time_shares()

    fig = go.Figure()
    # primary (tick anchor) with IQR band, x = minutes since 04:00 ET
    fig.add_trace(go.Scatter(x=list(pooled["minute_index"]) + list(pooled["minute_index"][::-1]),
                             y=list(pooled["q75"]) + list(pooled["q25"][::-1]), fill="toself",
                             fillcolor=_rgba(BLUE, 0.12), line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=pooled["minute_index"], y=pooled["median"], mode="lines", line=dict(color=BLUE, width=2),
                             name="primary (tick_close_T-1_RTH anchor), since 04:00 ET",
                             customdata=pooled["n"], hovertemplate="min %{x}<br>median %{y:.3f}<br>n=%{customdata}<extra></extra>"))
    # rth_legacy overlaid (its own clock is minutes-since-RTH-open; shift onto the 04:00 axis by the median rth-open offset for visual comparability)
    with open(CFG) as f:
        cfg = json.load(f)
    from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2
    sb = M2.session_bounds_from_spine(build_session_spine_v2(_events_deciles(), cfg), offset=0)
    rth_open_min_med = float(sb["rth_open_min"].median())
    fig.add_trace(go.Scatter(x=pooled_rth["minute_index"] + rth_open_min_med, y=pooled_rth["median"], mode="lines",
                             line=dict(color=ORANGE, width=2, dash="dash"),
                             name="rth_legacy (RTH-open anchor), shifted to 04:00 axis",
                             hovertemplate="rth min %{x}<br>median %{y:.3f}<extra></extra>"))
    fig.add_hline(y=0.5, line=dict(color=INK, dash="dot", width=1), annotation_text="50% realized")
    for c, col, lab, dy in [(cross, BLUE, f"primary {int(cross) if cross==cross else 'n/a'}", -30),
                            (cross_rth + rth_open_min_med if cross_rth == cross_rth else np.nan, ORANGE, f"rth_legacy {int(cross_rth) if cross_rth==cross_rth else 'n/a'} (since open)", 30)]:
        if c == c:  # not NaN
            fig.add_annotation(x=c, y=0.5, text=lab, showarrow=True, arrowhead=2, ax=0, ay=dy, font=dict(size=11, color=col), arrowcolor=col)
    # RTH open/close vertical rules (in minutes since 04:00)
    fig.add_vline(x=rth_open_min_med, line=dict(color=INK, dash="dash", width=1), annotation_text="RTH open", annotation_font=dict(size=9))
    fig.add_vline(x=float(sb["rth_close_min"].median()), line=dict(color=INK, dash="dash", width=1), annotation_text="RTH close", annotation_font=dict(size=9))
    fig.update_layout(title="Opportunity decay: pooled median realized-move fraction (primary tick anchor vs rth_legacy)",
                      plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=620, width=1150,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(title="minutes since 04:00 ET", range=[0, 720], gridcolor=GRID)
    fig.update_yaxes(title="pooled median realized fraction (IQR band, primary)", range=[-0.2, 1.3], gridcolor=GRID)
    fig.add_annotation(text=f"primary anchor = tick_close_T-1_RTH (D4, tick-only) | rth_legacy comparable to Phase 6's 52/57 | config {cfg_hash()}",
                       xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "04_opportunity_decay_ext")


def chart_05():
    pm = pd.read_parquet(f"{A}/opportunity_decay_primary_per_minute.parquet")
    ev = _events_deciles()
    groups = seeded_overlay_groups(ev, seed=42, n_random=30)
    with open(CFG) as f:
        cfg = json.load(f)
    from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2
    sb = M2.session_bounds_from_spine(build_session_spine_v2(ev, cfg), offset=0)
    rth_open_med = float(sb["rth_open_min"].median()); rth_close_med = float(sb["rth_close_min"].median())
    colors = {"top_decile": RED, "bottom_decile": BLUE, "seeded_random_30": INK2}
    fig = go.Figure()
    for gname, gdf in groups.items():
        sub = pm.merge(gdf[M2.EVENT_KEYS], on=M2.EVENT_KEYS, how="inner")
        for _, ev_sub in sub.groupby(M2.EVENT_KEYS):
            ev_sub = ev_sub.sort_values("minute_index")
            fig.add_trace(go.Scatter(x=ev_sub["minute_index"], y=ev_sub["realized_move_fraction"], mode="lines",
                                     line=dict(color=_rgba(colors[gname], 0.25), width=0.7), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=colors[gname], width=3), name=f"{gname} (n={len(gdf)})"))
    fig.add_hline(y=0.5, line=dict(color=INK, dash="dot", width=1))
    fig.add_vline(x=rth_open_med, line=dict(color=INK, dash="dash", width=1), annotation_text="RTH open", annotation_font=dict(size=9))
    fig.add_vline(x=rth_close_med, line=dict(color=INK, dash="dash", width=1), annotation_text="RTH close", annotation_font=dict(size=9))
    fig.update_layout(title="Per-event primary-decay traces: top/bottom decile + seeded random 30 (does the pooled curve hide a mixture?)",
                      plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=620, width=1150,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(title="minutes since 04:00 ET", range=[0, 720], gridcolor=GRID)
    fig.update_yaxes(title="realized fraction (signed)", range=[-1, 2], gridcolor=GRID)
    fig.add_annotation(text=f"group n in legend | config {cfg_hash()}", xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "05_per_event_overlay_ext")


def chart_06():
    seg = pd.read_parquet(f"{A}/segment_shares.parquet")
    fig = go.Figure()
    for s, color in [("premarket", ORANGE), ("rth", BLUE), ("post", VIOLET)]:
        fig.add_trace(go.Histogram(x=seg[f"{s}_share"], name=f"{s} (median {seg[f'{s}_share'].median():.3f})",
                                   marker_color=color, opacity=0.6, xbins=dict(start=0, end=1, size=0.02)))
    fig.update_layout(title=f"Per-event segment volume shares: premarket / RTH / post (n={len(seg)})", barmode="overlay",
                      plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=560, width=1080,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(title="share of T=0 extended-day volume", range=[0, 1], gridcolor=GRID)
    fig.update_yaxes(title="event count", gridcolor=GRID)
    fig.add_annotation(text=f"n={len(seg)} | if premarket is a spike at exactly 0, ETH rows are absent from collection - escalate | config {cfg_hash()}",
                       xref="paper", yref="paper", x=0, y=-0.14, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "06_segment_volume_shares")


def chart_07():
    ht = pd.read_parquet(f"{A}/high_time_of_day.parquet")
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=ht["high_hour_decimal"], marker_color=BLUE, xbins=dict(start=4, end=20, size=0.25), name="day_high_ext time"))
    for xr, lab in [(9.5, "09:30 RTH open"), (16.0, "16:00 RTH close")]:
        fig.add_vline(x=xr, line=dict(color=INK, dash="dash", width=1), annotation_text=lab, annotation_font=dict(size=9))
    fig.update_layout(title=f"ET clock time-of-day of the extended-day high (n={len(ht)})",
                      plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK), height=560, width=1080)
    fig.update_xaxes(title="ET hour of day_high_ext", range=[4, 20], dtick=1, gridcolor=GRID)
    fig.update_yaxes(title="event count", gridcolor=GRID)
    fig.add_annotation(text=f"n={len(ht)} | config {cfg_hash()}", xref="paper", yref="paper", x=0, y=-0.13, showarrow=False, font=dict(size=10, color=INK2))
    _write(fig, "07_high_time_of_day")


def main():
    import os
    os.makedirs(C, exist_ok=True)
    chart_01(); chart_02(); chart_03(); chart_04(); chart_05(); chart_06(); chart_07()
    print("charts 01-07 done (08 dropped, A8.2)")


if __name__ == "__main__":
    main()
