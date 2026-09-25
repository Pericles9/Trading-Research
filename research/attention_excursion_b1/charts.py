"""
Brief 1 -- every chart T7 lists, from artifacts. Dark theme (brief II.1, kept by A1.6), Plotly, one
chart per file, n on every bucket or series, no smoothing, nothing clipped.

  t1/01_revised_close_vs_minute_bar.html      t1/02_revised_close_vs_run1.html
  t2/01_row4_tau_exact_minus_proxy_prime.html t2/02_spike_guard_moves.html   t2/03_tau_close_gap.html
  t3/01_open_profile_0400.html                t3/02_open_profile_0930.html
  t4/strips_by_event.html (one chart, event selector)     t4/u_peak_N{50,100,200}.html
  t5/a2_curves_by_event.html (one chart, event selector)  t5/valid_rungs.html
  t5/valid_rungs_before_after.html (Amendment 3: 04:00 anchor vs segment anchor, by segment)
  t5b/competition_W{5,15,60}.html  t5b/matched_control_counts.html (Amendment 3 A3.5)
  t6/negative_excursion_bridge.html  t6/negative_excursion_free_walk.html  t6/negative_acceleration.html
  t6/positive_excursion.html
  t6/positive_acceleration.html  t6/null_parameter_sweep.html  t6/blindness.html

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/charts.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BG, FG, GRID = "#111418", "#e6e6e6", "#2a2f36"
PAL = ["#4ea1ff", "#ffb347", "#7ed957", "#ff6b6b", "#c792ea", "#9aa4b2"]
RUNG_COL = {50: PAL[0], 100: PAL[1], 200: PAL[2]}


def lay(fig, title, xt, yt, h=560):
    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=h,
                      font=dict(color=FG, size=13), title=dict(text=title, x=0.01),
                      legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=70, r=30, t=100, b=80))
    fig.update_xaxes(title=xt, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(title=yt, gridcolor=GRID, zeroline=False)
    return fig


def save(fig, task, name):
    fig.write_html(C.chart_path(task, name), include_plotlyjs=True)   # inlined: D14 offline (A2.8)


def ecdf(x):
    x = np.sort(np.asarray(x, dtype=float))
    return x, np.arange(1, x.size + 1) / x.size


def asinh_axis(fig, vals, labs):
    fig.update_xaxes(tickvals=[float(np.arcsinh(v)) for v in vals], ticktext=labs)


def j(name):
    return json.load(open(C.art(name), encoding="utf-8"))


def charts_t1_t2():
    t1 = pd.read_parquet(C.art("t1_prior_close.parquet"))
    t2 = pd.read_parquet(C.art("t2_tau.parquet"))
    for col, fname, lab in [("revised_vs_mb_bp", "01_revised_close_vs_minute_bar.html", "minute-bar close (old move_at build)"),
                            ("revised_vs_run1_bp", "02_revised_close_vs_run1.html", "run 1's largest-size rule")]:
        fig = go.Figure()
        for i, (src, g) in enumerate(t1.dropna(subset=[col]).groupby("prior_close_source")):
            x, y = ecdf(np.arcsinh(g[col]))
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i], width=2),
                                     name=f"{src} -- n={len(g):,}, equal {int((g[col] == 0).sum()):,}"))
        asinh_axis(fig, [-5000, -500, -100, -10, 0, 10, 100, 500, 5000], ["-5000", "-500", "-100", "-10", "0", "+10", "+100", "+500", "+5000"])
        lay(fig, f"T1 (A1.2) -- revised prior close vs {lab}, n = {int(t1[col].notna().sum()):,}<br><sup>by the revised rule's source; asinh axis, nothing clipped</sup>",
            "(revised - comparison) / comparison, bp", "cumulative share of events")
        save(fig, "t1", fname)

    s = j("t1_t2_summary.json")
    comp = t2[t2["row4_comparable"]]
    fig = go.Figure()
    fig.add_vrect(x0=np.arcsinh(-1), x1=np.arcsinh(61), fillcolor=PAL[2], opacity=0.12, line_width=0,
                  annotation_text="band [-1, 61] s", annotation_position="top left")
    for name, v, col, dash in [("row 4: tau_exact - tau_proxy' (same close)", comp["d_exact_minus_proxy_prime_s"], PAL[0], "solid"),
                               ("sensitivity: tau_exact - v1 stored proxy (own close)", t2["d_exact_minus_proxy_v1_s"].dropna(), PAL[3], "dot")]:
        v = v.dropna().to_numpy()
        o = int(((v < -1) | (v > 61)).sum())
        x, y = ecdf(np.arcsinh(v))
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, dash=dash, width=2),
                                 name=f"{name} -- n={v.size:,}, outside {o:,} ({o / v.size:.1%})"))
    asinh_axis(fig, [-36000, -3600, -60, -1, 0, 1, 61, 600, 3600, 36000], ["-10 h", "-1 h", "-60 s", "-1 s", "0", "+1 s", "+61 s", "+10 m", "+1 h", "+10 h"])
    r4 = s["escalation"]["row_4"]
    lay(fig, f"T2 -- revised row 4: {r4['n_outside']:,} of {r4['of_d1']:,} D1 events outside [-1, 61] s "
             f"({r4['observed_share_of_d1']:.2%}; HARD STOP above 2%)<br><sup>tau_proxy' = v1's minute proxy rebuilt from ticks on the "
             f"same prior close; the dotted curve is the as-run comparison kept as a sensitivity (A1.1)</sup>",
        "tau_exact - proxy (asinh axis)", "cumulative share of events")
    save(fig, "t2", "01_row4_tau_exact_minus_proxy_prime.html")

    mv = t2.loc[t2["guard_moved_tau"], "guard_move_s"].to_numpy()
    fig = go.Figure()
    if mv.size:
        edges = np.logspace(np.floor(np.log10(mv.min())), np.ceil(np.log10(mv.max())), 40)
        cnt, _ = np.histogram(mv, bins=edges)
        fig.add_trace(go.Bar(x=np.sqrt(edges[:-1] * edges[1:]), y=cnt, width=np.diff(edges) * 0.9, marker_color=PAL[1],
                             name=f"tau moved by the guard -- n={mv.size:,}"))
        fig.update_xaxes(type="log")
    lay(fig, f"T2 -- spike-guard moves (3% / 3%), n = {mv.size:,}<br><sup>{int(t2['guard15_differs'].sum()):,} events' tau differs "
             "under the overlay's 1.5% neighbour agreement (A1.4 sensitivity)</sup>", "tau (guarded) - tau (no guard), s, log", "events per bin")
    save(fig, "t2", "02_spike_guard_moves.html")

    g = t2["tau_gap_close_s"].dropna().to_numpy()
    tc = s["t2"]["tau_close_sensitive"]
    fig = go.Figure()
    fig.add_vrect(x0=np.arcsinh(-60), x1=np.arcsinh(60), fillcolor=PAL[2], opacity=0.12, line_width=0,
                  annotation_text="|gap| <= 60 s: not close-sensitive", annotation_position="top left")
    x, y = ecdf(np.arcsinh(g))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[4], width=2),
                             name=f"tau(revised close) - tau(minute-bar close) -- n={g.size:,}"))
    asinh_axis(fig, [-36000, -3600, -60, 0, 60, 3600, 36000], ["-10 h", "-1 h", "-60 s", "0", "+60 s", "+1 h", "+10 h"])
    lay(fig, f"T2 (A1.3) -- tau_close_sensitive: TRUE {tc['true']:,} · FALSE {tc['false']:,} · NULL {tc['null']:,} "
             f"(one side only: {tc['one_side_only']:,})<br><sup>a facet, never a filter</sup>", "tau_gap_close_s (asinh axis)", "cumulative share of events")
    save(fig, "t2", "03_tau_close_gap.html")


def charts_t3():
    prof = pd.read_parquet(C.art("t3_open_profile.parquet"))
    s = j("t3_open_boundary.json")
    for name, o, fn in [("04:00", 0, "01_open_profile_0400.html"), ("09:30", 330, "02_open_profile_0930.html")]:
        lo, hi = (-5, 120) if o == 0 else (315, 390)
        p = prof[(prof["clock_min"] >= lo) & (prof["clock_min"] < hi)]
        fig = go.Figure()
        x = p["clock_min"]
        fig.add_trace(go.Scatter(x=x, y=p["p75"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=p["p25"], mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor="rgba(78,161,255,0.25)", name="IQR across events"))
        fig.add_trace(go.Scatter(x=x, y=p["median"], mode="lines+markers", line=dict(color=PAL[0], width=2),
                                 marker=dict(size=4), name="median normalised n_trades", customdata=np.c_[p["n_events"], p["clock_et"]],
                                 hovertemplate="%{customdata[1]}: median %{y:.3f}, n=%{customdata[0]:,}<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=p["L_ref_10_20"], mode="lines", line=dict(color=PAL[1], dash="dot"),
                                 name="reference level: median over [m+10, m+20]"))
        fig.add_trace(go.Bar(x=x, y=p["n_events"], yaxis="y2", marker_color="rgba(154,164,178,0.25)", name="n events per minute"))
        pr = s["proposals"][name]
        for key, col, lab in [("proposed_boundary_first_minute", PAL[3], "proposed (first minute)"),
                              ("proposed_boundary_5_consecutive", PAL[2], "proposed (5 consecutive)")]:
            b = pr.get(key)
            if b:
                bx = int(b["minutes_after_open"]) + o
                fig.add_vline(x=bx, line=dict(color=col, dash="dash"),
                              annotation_text=f"{lab}: {b['clock_et']} (+{b['minutes_after_open']} min)", annotation_position="top")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="n events", rangemode="tozero"))
        lay(fig, f"T3 -- open profile at {name}: n_trades / event's own median minute, minutes ending at or before own tau<br>"
                 f"<sup>{s['events_used']:,} D1 events; proposal rule in config t3_open_boundary; no outcome enters. Cooper confirms or replaces.</sup>",
            "clock minute (ET)", "normalised trade rate", h=600)
        tk = p[p["clock_min"] % 5 == 0]
        fig.update_xaxes(tickvals=tk["clock_min"], ticktext=tk["clock_et"])
        save(fig, "t3", fn)


def charts_t4():
    """A2.8: Plotly inlined. The per-event strips are ONE chart with an event selector (config
    amendment_2.charts.per_event_views). The u_peak reference is the simulated discrete free walk (A2.2)."""
    ex = pd.read_parquet(C.art("t4_excursion.parquet"))
    bk = pd.read_parquet(C.art("t4_buckets.parquet"))
    refs = j("t6_references.json")["by_N"]
    evs = [e for e, _ in ex[ex["vector_available"] == True].groupby("event_id")]  # noqa: E712
    fig = go.Figure()
    vis_by_event = []
    for eid in evs:
        g = ex[(ex["event_id"] == eid) & (ex["vector_available"] == True)]  # noqa: E712
        start = len(fig.data)
        meta = g.iloc[0]
        for r in g.itertuples():
            b = bk[(bk["event_id"] == eid) & (bk["N"] == r.N)].sort_values("i")
            u = np.r_[0.0, b["u"].to_numpy()]
            lp = np.log(np.r_[r.tau_price, b["vwap"].to_numpy()] / r.tau_price) * 1e4
            fig.add_trace(go.Scatter(x=u, y=lp, mode="lines", line=dict(color=RUNG_COL[r.N], width=1.5), visible=False,
                                     name=f"N={r.N}: u_peak {r.u_peak:.3f}, rise {r.rise_s:.2f} / fall {r.fall_s:.2f} sigma_path"
                                          f"{' (peak tied)' if r.peak_tied else ''}"))
            fig.add_trace(go.Scatter(x=[r.u_peak], y=[lp[int(r.i_peak)]], mode="markers", visible=False, showlegend=False,
                                     marker=dict(color=RUNG_COL[r.N], size=10, symbol="triangle-up")))
            fig.add_trace(go.Scatter(x=[1.0], y=[lp[-1]], mode="markers", visible=False, showlegend=False,
                                     marker=dict(color=RUNG_COL[r.N], size=9, symbol="square")))
        fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers", marker=dict(color=FG, size=10), name="tau", visible=False))
        flags = [k for k in ["rise_censored", "no_rise", "peak_tied", "halt_in_path", "thin_path"] if bool(g[k].fillna(False).any())]
        title = (f"T4 -- {eid} ({meta['dev_group']}, {meta['tau_session_segment']}) -- bucketed path on the volume clock<br>"
                 f"<sup>{int(meta['n_path_prints_all']):,} prints after tau; flags: {', '.join(flags) or 'none'}; "
                 f"jump_share (N=100) {g[g['N'] == 100]['jump_share'].iloc[0]:.3f}; tau_close_sensitive={meta['tau_close_sensitive']}; "
                 f"A12 flag={meta['flag_cross_session_extreme']}; triangle = peak, square = end</sup>")
        vis_by_event.append((eid, start, len(fig.data), title))
    buttons = []
    for eid, a, b, title in vis_by_event:
        vis = [a <= i < b for i in range(len(fig.data))]
        buttons.append(dict(label=eid, method="update", args=[{"visible": vis}, {"title.text": title}]))
    for i in range(vis_by_event[0][1], vis_by_event[0][2]):
        fig.data[i].visible = True
    lay(fig, vis_by_event[0][3], "u = share of the path's volume traded (volume clock)", "ln(bucket VWAP / tau price), bp", h=620)
    fig.update_layout(updatemenus=[dict(buttons=buttons, direction="down", x=1.0, xanchor="right", y=1.12, yanchor="top",
                                        bgcolor="#1d2229", font=dict(color=FG))])
    save(fig, "t4", "strips_by_event.html")

    va = ex[(ex["vector_available"] == True) & (ex["dev_group"] == "dev_v3")]  # noqa: E712
    for N in (50, 100, 200):
        g = va[va["N"] == N]
        fig = go.Figure()
        edges = np.linspace(0, 1, 21)
        cnt, _ = np.histogram(g["u_peak"], bins=edges)
        fig.add_trace(go.Bar(x=(edges[:-1] + edges[1:]) / 2, y=cnt, width=0.045, marker_color=RUNG_COL[N],
                             name=f"dev sample u_peak -- n={len(g)}", text=cnt, textposition="outside"))
        rc = np.asarray(refs[str(N)]["free_walk"]["u_peak_counts"], dtype=float)
        uu = np.arange(N + 1) / N
        rbin, _ = np.histogram(uu, bins=edges, weights=rc)
        fig.add_trace(go.Scatter(x=(edges[:-1] + edges[1:]) / 2, y=len(g) * rbin / rc.sum(), mode="lines+markers",
                                 line=dict(color=FG, dash="dot"), name=f"simulated discrete free walk at N={N} (no drift), scaled to n"))
        lay(fig, f"T4 -- pooled u_peak, N = {N}, dev sample, unconditional (no attention split), n = {len(g)}<br>"
                 "<sup>reference: the simulated no-drift discrete free walk at this N under the realised-variance scale (Amendment 2 A2.2)</sup>",
            "u_peak (absolute 0.05 bins)", "events per bin")
        save(fig, "t4", f"u_peak_N{N}.html")


def charts_t5():
    rg = pd.read_parquet(C.art("t5_a2_rungs.parquet"))
    at = pd.read_parquet(C.art("t5_attention.parquet"))
    fig = go.Figure()
    spans = []
    segs = at.set_index("event_id")["tau_anchor_segment"].to_dict()
    for eid, g in rg.groupby("event_id"):
        a = len(fig.data)
        v = g[g["valid"]]
        fig.add_trace(go.Scatter(x=g["k"], y=np.where(g["valid"], g["accel"], np.nan), mode="lines+markers", line=dict(color=PAL[0]),
                                 visible=False, name=f"count version -- {len(v)} valid of {len(g)} rungs",
                                 customdata=np.c_[g["n_recent"], g["n_older"], g["W_s"], g["class"]],
                                 hovertemplate="k=%{x}: accel %{y:.3f}<br>n_recent %{customdata[0]}, n_older %{customdata[1]}, "
                                               "W %{customdata[2]:.1f}s, %{customdata[3]}<extra></extra>"))
        kv = g[g["valid"] & g["kernel_defined"]]
        fig.add_trace(go.Scatter(x=kv["k"], y=kv["accel_kernel"], mode="lines+markers", line=dict(color=PAL[1], dash="dash"),
                                 visible=False, name=f"one-sided kernel check -- {len(kv)} rungs defined"))
        inv = g[~g["valid"]]
        fig.add_trace(go.Scatter(x=inv["k"], y=np.zeros(len(inv)), mode="markers", visible=False,
                                 marker=dict(color=PAL[3], symbol="x", size=8), name=f"invalid rungs ({len(inv)}), drawn at 0",
                                 customdata=inv["class"], hovertemplate="k=%{x}: %{customdata}<extra></extra>"))
        spans.append((eid, a, len(fig.data)))
    sub = lambda e: (f"T5 -- A2 rung curve, {e} (tau in {segs.get(e)})<br><sup>every rung judged on its own (A2.4); W_k = H / 2^k, "  # noqa: E731
                     "H from the start of tau's clock segment (Amendment 3 A3.1); accel = ln(n_recent / n_older), collapsed at 10 ms</sup>")
    buttons = [dict(label=e, method="update", args=[{"visible": [a <= i < b for i in range(len(fig.data))]}, {"title.text": sub(e)}])
               for e, a, b in spans]
    for i in range(spans[0][1], spans[0][2]):
        fig.data[i].visible = True
    fig.add_hline(y=0, line=dict(color=GRID))
    lay(fig, sub(spans[0][0]), "rung k (coarse -> fine)", "accel_k", h=520)
    fig.update_layout(updatemenus=[dict(buttons=buttons, direction="down", x=1.0, xanchor="right", y=1.14, yanchor="top",
                                        bgcolor="#1d2229", font=dict(color=FG))])
    save(fig, "t5", "a2_curves_by_event.html")

    d_all = at[(at["dev_group"] == "dev_v3") & (at["attention_available"] == True)]  # noqa: E712
    d = d_all[d_all["a2_state"] == "value"]
    fig = go.Figure()
    for i, (sg, g) in enumerate(d.groupby("tau_anchor_segment")):
        vc = g["a2_valid_rungs"].astype(int).value_counts().sort_index()
        fig.add_trace(go.Bar(x=vc.index, y=vc.values, text=vc.values, textposition="outside", marker_color=PAL[i],
                             name=f"tau in {sg} -- n={len(g)}"))
    fig.update_layout(barmode="stack")
    lay(fig, f"T5 -- valid A2 rungs per dev event, segment-anchored (Amendment 3), n = {len(d)} with A2<br>"
             f"<sup>zero valid rungs: {int((d['a2_valid_rungs'] == 0).sum())}; contiguous valid runs: {int(d['a2_valid_contiguous'].sum())}; "
             f"tau in a cross minute, A2 unavailable (A3.2): {int((d_all['a2_state'] != 'value').sum())}</sup>", "valid rungs", "events")
    save(fig, "t5", "valid_rungs.html")

    ba = pd.read_parquet(C.art("t5_a3_before_after_events.parquet"))
    fig = go.Figure()
    order = [sg for sg in C.SEGMENTS if sg in set(ba["tau_anchor_segment"])]
    for arm, col, lab in [("a2_valid_rungs_before", PAL[5], "before: anchored at 04:00 (run 3)"),
                          ("a2_valid_rungs_after", PAL[0], "after: anchored at the segment start")]:
        g = ba.dropna(subset=[arm])
        cnt = {sg: int((g["tau_anchor_segment"] == sg).sum()) for sg in order}
        fig.add_trace(go.Box(x=[f"{sg} (n={cnt[sg]})" for sg in g["tau_anchor_segment"]], y=g[arm].astype(float), name=lab,
                             marker_color=col, boxpoints="all", jitter=0.4, pointpos=0,
                             customdata=g["event_id"], hovertemplate="%{customdata}: %{y}<extra></extra>"))
    fig.update_layout(boxmode="group")
    fig.update_xaxes(categoryorder="array", categoryarray=[f"{sg} (n={int((ba['tau_anchor_segment'] == sg).sum())})" for sg in order])
    lay(fig, f"T5 -- valid A2 rungs per dev event before and after the anchoring change, by clock segment of tau, n = {len(ba)}<br>"
             "<sup>every event drawn; cross-minute taus have no 'after' (A2 unavailable, A3.2); premarket ladders are the same in "
             "both runs by construction</sup>", "clock segment of tau", "valid rungs per event")
    save(fig, "t5", "valid_rungs_before_after.html")


def charts_t5b():
    cp = pd.read_parquet(C.art("t5b_competition.parquet"))
    ok = cp[cp["status"] == "ok"]
    sm = j("t5b_summary.json")
    und = sm["structurally_undefined_cells"]
    for W in sorted(ok["W_min"].unique()):
        fig = go.Figure()
        fig.add_vline(x=0, line=dict(color=GRID))
        for i, L in enumerate(["15", "60", "rest_of_session"]):
            c = cp[(cp["W_min"] == W) & (cp["liveness"] == L)]
            matched = c[(c["arm"] == "control") & (c["status"] != "no_match")][["j", "i"]].drop_duplicates()
            okc = ok[(ok["W_min"] == W) & (ok["liveness"] == L)]
            arms = [("crossing, pairs with a matched control", okc[okc["arm"] == "crossing"].merge(matched, on=["j", "i"]), "solid"),
                    ("matched control", okc[okc["arm"] == "control"], "dot")]
            for lab, g, dash in arms:
                v = g["log_ratio"].to_numpy()
                if v.size == 0:
                    continue
                x, y = ecdf(v)
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i], dash=dash, width=2),
                                         name=f"L={L}, {lab} -- n={v.size:,}, median {np.median(v):+.3f}"))
        missing = [L for L, ws in und.items() if int(W) in ws]
        mt = "; ".join(f"L={L}: {v['matching']['pairs_with_matched_control']:,} of {v['matching']['pairs']:,} pairs matched"
                       for L in ("15", "60", "rest_of_session") for k, v in sm["cells"].items() if k == f"L={L}|W={W}")
        lay(fig, f"T5b -- live name i's trade rate after vs before a new crossing, W = {W} min (dev-event dates only)<br>"
                 f"<sup>solid: at another name's crossing (pairs with a matched control); dotted: moments in i's own live span in the "
                 f"same octave since i's crossing and the same clock segment, no crossing within +/- W (A3.5). {mt}"
                 f"{'; structurally undefined here (W >= L): L=' + ', '.join(missing) if missing else ''}</sup>",
            "ln(n in [t, t+W) / n in [t-W, t))", "cumulative share", h=620)
        save(fig, "t5b", f"competition_W{W}.html")

    cells = list(sm["cells"].items())
    labs = [k.replace("|", " · ") for k, _ in cells]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labs, y=[v["matching"]["pairs_with_matched_control"] for _, v in cells], marker_color=PAL[2],
                         name="pairs with >= 1 matched control", text=[f"{v['matching']['pairs_with_matched_control']:,}" for _, v in cells],
                         textposition="outside"))
    reasons = sorted({r for _, v in cells for r in v["matching"]["no_match_reason"]})
    for i, r in enumerate(reasons):
        y = [v["matching"]["no_match_reason"].get(r, 0) for _, v in cells]
        fig.add_trace(go.Bar(x=labs, y=y, marker_color=[PAL[3], PAL[1], PAL[4]][i % 3], name=f"no_match: {r}",
                             text=[f"{x:,}" for x in y], textposition="outside"))
    fig.update_layout(barmode="group")
    lay(fig, "T5b -- matched-control counts per cell (Amendment 3 A3.5), dev-event dates only<br>"
             "<sup>a pair is (live name i, crossing j); no_match pairs are carried, never filled from outside the bin; "
             "counts are pairs</sup>", "liveness · W (min)", "pairs")
    save(fig, "t5b", "matched_control_counts.html")


def charts_t6():
    c6 = j("t6_controls.json")
    refs = j("t6_references.json")["by_N"]
    d = c6["detail"]
    v = c6["verdict"]
    for key, fname, ref_key, label in [("negative_excursion_bridge", "negative_excursion_bridge.html", "bridge", "bridge (demeaned shuffles)"),
                                       ("negative_excursion_free_walk", "negative_excursion_free_walk.html", "free_walk", "free walk (draws with replacement)")]:
        df = pd.read_parquet(C.art(f"t6_{key}.parquet"))
        fig = go.Figure()
        for N in (50, 100, 200):
            g = df[(df["N"] == N) & ~df["sigma_zero"]]
            c = np.bincount(g["i_peak"].astype(int), minlength=N + 1).astype(float)
            rc = np.asarray(refs[str(N)][ref_key]["u_peak_counts"], dtype=float)
            u = np.arange(N + 1) / N
            dd = d[key][str(N)]
            fig.add_trace(go.Scatter(x=u, y=np.cumsum(c) / c.sum(), mode="lines", line=dict(color=RUNG_COL[N], shape="hv"),
                                     name=f"N={N} control -- n={len(g):,}; KS {dd['ks_vs_simulated_reference']:.3f}; mean rise "
                                          f"{dd['mean_rise_s']:.3f} vs ref {dd['reference_mean_rise_s']:.3f}"))
            fig.add_trace(go.Scatter(x=u, y=np.cumsum(rc) / rc.sum(), mode="lines", line=dict(color=RUNG_COL[N], dash="dot", shape="hv"),
                                     name=f"N={N} simulated Gaussian {ref_key.replace('_', ' ')} (n={int(rc.sum()):,})"))
        lay(fig, f"T6 negative control, excursion -- {label} -- verdict {'PASS' if v[key] else 'FAIL'}<br>"
                 "<sup>pass: two-sample KS to the simulated reference <= 0.05 AND |mean rise_s - reference| <= 0.05, every rung "
                 "(Amendment 2 A2.2, references committed before the run)</sup>", "u_peak", "cumulative share", h=620)
        save(fig, "t6", fname)

    na = d["negative_acceleration"]
    ks = sorted(int(k) for k in na)
    fig = go.Figure()
    fig.add_hrect(y0=-0.1, y1=0.1, fillcolor=PAL[2], opacity=0.12, line_width=0, annotation_text="|median| < 0.1")
    fig.add_trace(go.Scatter(x=ks, y=[na[str(k)]["median_accel"] for k in ks], mode="lines+markers", line=dict(color=PAL[0]),
                             name="median accel_k", text=[f"n={na[str(k)]['n']:,}" for k in ks], hovertemplate="k=%{x}: %{y:.4f} (%{text})<extra></extra>"))
    fig.add_trace(go.Scatter(x=ks, y=[na[str(k)]["sd_z"] for k in ks], mode="lines+markers", line=dict(color=PAL[1]),
                             name="SD of z = accel / sqrt(1/n_r + 1/n_o) (band 0.80-1.25)", yaxis="y2"))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0.3, 1.5], title="SD(z)", showgrid=False))
    lay(fig, f"T6 negative control, acceleration (homogeneous Poisson, per-rung ladder) -- verdict {'PASS' if v['negative_acceleration'] else 'FAIL'}<br>"
             "<sup>tapes over each event's segment history [segment start, tau] (Amendment 3); per rung, pooled over events x draws; "
             "readable rungs need >= 100 values; n per rung on hover</sup>", "rung k", "median accel_k")
    save(fig, "t6", "negative_acceleration.html")

    pe = d["positive_excursion"]
    fig = go.Figure()
    for i, (key, rkey) in enumerate([("median_u_peak", "reference_median_u_peak"), ("median_rise_s", "reference_median_rise_s"),
                                     ("median_fall_s", "reference_median_fall_s")]):
        fig.add_trace(go.Bar(x=[f"N={N}" for N in (50, 100, 200)],
                             y=[(pe[str(N)][key] - pe[str(N)][rkey]) / (pe[str(N)][rkey] if key != "median_u_peak" else 1.0) for N in (50, 100, 200)],
                             name=f"{key}: recovered vs simulated reference ({'absolute, band +/-0.05' if key == 'median_u_peak' else 'relative, band +/-10%'})",
                             marker_color=PAL[i], text=[f"{pe[str(N)][key]:.3f} vs {pe[str(N)][rkey]:.3f} (n={pe[str(N)]['n']:,})" for N in (50, 100, 200)],
                             textposition="outside"))
    fig.add_hrect(y0=-0.10, y1=0.10, fillcolor=PAL[2], opacity=0.08, line_width=0)
    fig.add_hrect(y0=-0.05, y1=0.05, fillcolor=PAL[2], opacity=0.10, line_width=0)
    lay(fig, f"T6 positive control, excursion (injected peak u=0.3, rise 2.0, fall 1.5) -- verdict {'PASS' if v['positive_excursion'] else 'FAIL'}<br>"
             "<sup>recovered medians against the simulated expectation for the same injection at each N (A2.2); bias versus the injected "
             "values is in the report, as an instrument property</sup>", "rung", "recovered - reference")
    save(fig, "t6", "positive_excursion.html")

    pa = d["positive_acceleration"]
    fig = go.Figure()
    for i, m in enumerate(sorted({int(k.split(",")[0][2:]) for k in pa})):
        cells = sorted([(int(k.split(",")[1][2:]), vv) for k, vv in pa.items() if int(k.split(",")[0][2:]) == m])
        fig.add_trace(go.Scatter(x=[c[0] for c in cells], y=[c[1]["median_accel"] for c in cells], mode="lines+markers",
                                 line=dict(color=PAL[i]), name=f"step at midpoint of rung m={m}: recovered median",
                                 text=[f"n={c[1]['n']:,}, {c[1]['role']}" for c in cells], hovertemplate="k=%{x}: %{y:.3f} (%{text})<extra></extra>"))
        fig.add_trace(go.Scatter(x=[c[0] for c in cells], y=[c[1]["target"] for c in cells], mode="markers",
                                 marker=dict(color=PAL[i], symbol="x", size=9), name=f"m={m}: expected (ln2 at k=m, 0 after, ln(1+2^(k-m)) before)"))
    lay(fig, f"T6 positive control, acceleration (rate doubles at a known time, per-rung ladder) -- verdict {'PASS' if v['positive_acceleration'] else 'FAIL'}<br>"
             "<sup>tapes over each event's segment history (Amendment 3); band +/-0.2 around each expected value; rungs coarser "
             "than the step are reported, not in the verdict</sup>",
        "rung k", "median accel_k", h=620)
    save(fig, "t6", "positive_acceleration.html")

    sw = d["null_parameter_sweep"]["excursion"]
    fig = go.Figure()
    comps = list(sw)
    for N in (50, 100, 200):
        base = [sw[c]["medians"]["100"] for c in comps]
        fig.add_trace(go.Bar(x=comps, y=[sw[c]["medians"][str(N)] / b if b else np.nan for c, b in zip(comps, base)],
                             name=f"N={N} median / N=100 median", marker_color=RUNG_COL[N]))
    fig.add_hrect(y0=0.8, y1=1.2, fillcolor=PAL[2], opacity=0.1, line_width=0)
    lay(fig, "T6 null-parameter sweep -- component medians across the bucket ladder (dev sample, n=49 per rung)<br>"
             f"<sup>rung-dependent: {', '.join(c for c in comps if sw[c]['label'] == 'rung-dependent') or 'none'}</sup>",
        "component", "median relative to N=100")
    save(fig, "t6", "null_parameter_sweep.html")

    bl = pd.read_parquet(C.art("t6_blindness_rescale.parquet"))
    fig = go.Figure()
    for i, f in enumerate(sorted(bl["factor"].unique())):
        vv = bl[bl["factor"] == f]["max_abs_diff"].to_numpy()
        fig.add_trace(go.Box(y=np.maximum(vv, 1e-18), name=f"prices x{f} -- n={vv.size}", marker_color=PAL[i], boxpoints="all"))
    fig.add_hline(y=1e-9, line=dict(color=PAL[3], dash="dash"), annotation_text="1e-9 pass line")
    fig.update_yaxes(type="log")
    lay(fig, f"T6 blindness -- max abs change in sigma-unit and bp components under price rescaling, tie rule A2.3 -- verdict "
             f"{'PASS' if v['blindness'] else 'FAIL'}<br><sup>zeros drawn at 1e-18 on the log axis</sup>", "", "max abs difference")
    save(fig, "t6", "blindness.html")


def main() -> int:
    charts_t1_t2()
    charts_t3()
    charts_t4()
    charts_t5()
    charts_t5b()
    charts_t6()
    print("charts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
