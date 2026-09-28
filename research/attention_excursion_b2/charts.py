"""
Brief 2 -- every chart, from artifacts. Dark theme, Plotly inlined (D14), one chart per file; views of
the same quantity across facet levels or events sit in one chart behind a selector (Amendment 3 A3.6).
n on every bar and every curve, no smoothing, nothing clipped. ECDFs are drawn through at most 1,000
exact order statistics per curve, both extremes always included.

No chart puts an attention, catalyst or cross-sectional quantity against an excursion component (II.4,
section 6): T4's charts read t1_excursion, t0_population, t4_* and the reference only.

  t1/edge_classes.html           t1/path_prints.html
  t2/a2_valid_rungs.html         t2/level_measures.html      t2/turnover.html      t2/live_n.html
  t3/excess_W{5,15,60}.html      t3/baseline_cells.html      t3/r3_share_lost.html
  t4/u_peak.html                 t4/ecdf_{rise_s,fall_s,dip_before_peak_s,terminal_s}.html
  t4/rise_vs_cost.html           t4/cost_clearing.html       t4/gallery.html

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/charts.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402

BG, FG, GRID = "#111418", "#e6e6e6", "#2a2f36"
PAL = ["#4ea1ff", "#ffb347", "#7ed957", "#ff6b6b", "#c792ea", "#9aa4b2", "#f78fb3", "#63e6be", "#ffd43b", "#a5d8ff"]
RUNG_COL = {50: PAL[0], 100: PAL[1], 200: PAL[2]}
COMPS = ["rise_s", "fall_s", "dip_before_peak_s", "terminal_s"]
EDGES = ["rise_censored", "no_rise", "peak_tied", "halt_in_path", "thin_path"]


def lay(fig, title, xt, yt, h=600):
    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=h,
                      font=dict(color=FG, size=13), title=dict(text=title, x=0.01),
                      legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=70, r=30, t=110, b=80))
    fig.update_xaxes(title=xt, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(title=yt, gridcolor=GRID, zeroline=False)
    return fig


def save(fig, task, name):
    fig.write_html(B.chart_path(task, name), include_plotlyjs=True)


def ecdf(x, cap=1000):
    x = np.sort(np.asarray(x, dtype=float))
    x = x[np.isfinite(x)]
    n = x.size
    if n == 0:
        return x, x
    idx = np.unique(np.r_[0, np.round(np.linspace(0, n - 1, min(cap, n))).astype(int), n - 1])
    return x[idx], (idx + 1) / n


def selector(fig, views, y=1.13):
    """views: [(label, first_trace, end_trace, title)]; one visible at a time."""
    n = len(fig.data)
    buttons = [dict(label=lab, method="update", args=[{"visible": [a <= i < b for i in range(n)]}, {"title.text": t}])
               for lab, a, b, t in views]
    for i in range(n):
        fig.data[i].visible = views[0][1] <= i < views[0][2]
    fig.update_layout(title=dict(text=views[0][3]),
                      updatemenus=[dict(buttons=buttons, direction="down", x=1.0, xanchor="right", y=y, yanchor="top",
                                        bgcolor="#1d2229", font=dict(color=FG))])


def selector_idx(fig, views, y=1.13):
    """views: [(label, [trace indices], title)] -- lets several views share a trace (e.g. a reference)."""
    n = len(fig.data)
    buttons = [dict(label=lab, method="update", args=[{"visible": [i in set(ix) for i in range(n)]}, {"title.text": t}])
               for lab, ix, t in views]
    first = set(views[0][1])
    for i in range(n):
        fig.data[i].visible = i in first
    fig.update_layout(title=dict(text=views[0][2]),
                      updatemenus=[dict(buttons=buttons, direction="down", x=1.0, xanchor="right", y=y, yanchor="top",
                                        bgcolor="#1d2229", font=dict(color=FG))])


def asinh_axis(fig, vals, labs):
    fig.update_xaxes(tickvals=[float(np.arcsinh(v)) for v in vals], ticktext=labs)


# ====================================================================== T1
def charts_t1():
    ex = pd.read_parquet(B.art("t1_excursion.parquet"))
    s = B.read_json("t1_summary.json")
    ta = ex[ex["tau_ns"].notna()]
    fig = go.Figure()
    cats = ["vector_available"] + EDGES + ["peak_at_tau", "sigma_zero"]
    for N in (50, 100, 200):
        g = ta[ta["N"] == N]
        vals = [int(g[c].fillna(False).astype(bool).sum()) for c in cats]
        fig.add_trace(go.Bar(x=cats, y=vals, name=f"N={N} -- rows {len(g):,}", marker_color=RUNG_COL[N],
                             text=[f"{v:,}" for v in vals], textposition="outside"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(type="log")
    lay(fig, f"T1 -- excursion vector availability and edge classes, all of D1 with tau (n = {s['events_with_tau']:,} events)<br>"
             f"<sup>edge classes are flags, never drops; rows per rung; log count axis. Row 1 (vector on < 95%): "
             f"{'FIRED' if s['row_1']['fires'] else 'clear'}; row 6 thin {s['row_6']['observed_share']:.1%}; row 7 halt "
             f"{s['row_7']['observed_share']:.1%}</sup>", "", "events (log)")
    save(fig, "t1", "edge_classes.html")

    pe = ta.drop_duplicates("event_id")
    v = pe["n_path_prints_all"].dropna().to_numpy()
    fig = go.Figure()
    x, y = ecdf(np.maximum(v, 0.5))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[0], width=2), name=f"prints after tau to 20:00 -- n={v.size:,}"))
    fig.add_vline(x=250, line=dict(color=PAL[3], dash="dash"), annotation_text="thin_path: < 250 prints")
    fig.update_xaxes(type="log")
    lay(fig, f"T1 -- path length in prints, all of D1 with tau, n = {v.size:,}<br><sup>zero-print paths drawn at 0.5 on the log axis: "
             f"{int((v == 0).sum()):,}</sup>", "prints strictly after tau, up to 20:00 ET (log)", "cumulative share of events")
    save(fig, "t1", "path_prints.html")


# ====================================================================== T2
def charts_t2():
    at = pd.read_parquet(B.art("t2_attention.parquet"))
    rg = pd.read_parquet(B.art("t2_a2_rungs.parquet"))
    xs = pd.read_parquet(B.art("t2_cross_sectional.parquet"))
    a2 = at[at["a2_state"] == "value"]
    fig = go.Figure()
    for i, (sg, g) in enumerate(a2.groupby("tau_anchor_segment")):
        vc = g["a2_valid_rungs"].astype(int).value_counts().sort_index()
        fig.add_trace(go.Bar(x=vc.index, y=vc.values, name=f"tau in {sg} -- n={len(g):,}, ignition {int(g['a2_ignition'].sum()):,}",
                             marker_color=PAL[i], text=[f"{v:,}" for v in vc.values], textposition="outside"))
    fig.update_layout(barmode="group")
    na = int((at["a2_state"] == "unavailable_auction_minute").sum())
    lay(fig, f"T2 -- valid A2 rungs per event, segment-anchored, R1 extent, n = {len(a2):,} with A2<br>"
             f"<sup>tau in a cross minute (A2 unavailable): {na:,}; a2_ignition (rung 0 or 1 from_nothing): {int(a2['a2_ignition'].sum()):,}; "
             f"zero valid rungs: {int((a2['a2_valid_rungs'] == 0).sum()):,}</sup>", "valid rungs", "events")
    save(fig, "t2", "a2_valid_rungs.html")

    v = rg[rg["valid"]]
    fig = go.Figure()
    views = []
    for m, unit in (("trades_per_min", "collapsed trades per minute"), ("dollars_per_min", "dollars per minute"),
                    ("shares_per_min", "shares per minute")):
        a = len(fig.data)
        for i, (k, g) in enumerate(v.groupby("k")):
            x, y = ecdf(g[m].clip(lower=1e-9))
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i % len(PAL)], width=1.5), name=f"rung k={k} -- n={len(g):,}"))
        views.append((m, a, len(fig.data), f"T2 -- absolute level over each valid rung window [tau - W_k, tau]: {unit}, by rung<br>"
                                           f"<sup>{len(v):,} valid rungs on {v['event_id'].nunique():,} events; plain counts and sums over "
                                           f"time, no baseline; log axis</sup>"))
    selector(fig, views)
    fig.update_xaxes(type="log")
    lay(fig, views[0][3], "level (log)", "cumulative share of rungs", h=640)
    save(fig, "t2", "level_measures.html")

    tv = at[at["a1_state"] == "value"]["turnover"]
    st = at[at["attention_available"]]["a1_state"].value_counts().to_dict()
    fig = go.Figure()
    x, y = ecdf(tv)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[0], width=2), name=f"turnover (value state) -- n={tv.size:,}"))
    fig.update_xaxes(type="log")
    lay(fig, f"T2 -- A1 turnover, shares 04:00 -> tau / split-corrected shares outstanding<br><sup>states: "
             + ", ".join(f"{k} {v:,}" for k, v in st.items()) + "</sup>", "turnover (log)", "cumulative share of events")
    save(fig, "t2", "turnover.html")

    fig = go.Figure()
    lv = xs.drop_duplicates(["event_id", "liveness"])
    for i, L in enumerate(["15", "60", "rest_of_session"]):
        g = lv[lv["liveness"] == L]["live_n"]
        x, y = ecdf(g)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i], width=2, shape="hv"),
                                 name=f"L={L} -- n={g.size:,} crossings, alone {int((g == 1).sum()):,}"))
    fig.update_xaxes(type="log")
    lay(fig, "T2 -- live-set size at each crossing (the crosser included), all of D1", "live_n (log)", "cumulative share of crossings")
    save(fig, "t2", "live_n.html")


# ====================================================================== T3
def charts_t3():
    pr = pd.read_parquet(B.art("t3_pairs.parquet"))
    cells = pd.read_parquet(B.art("t3_baseline_cells.parquet"))
    s = B.read_json("t3_summary.json")
    ok = pr[(pr["status"] == "ok") & ~pr["baseline_thin"]]
    for W in sorted(pr["W_min"].unique()):
        fig = go.Figure()
        views = []
        facets = [("all", None, None)] + [(f"year {y}", "year", y) for y in sorted(ok["year"].unique())] + \
                 [(f"segment {sg}", "segment", sg) for sg in sorted(ok["segment"].astype(str).unique())]
        for lab, col, val in facets:
            a = len(fig.data)
            for i, L in enumerate(["15", "60", "rest_of_session"]):
                g = ok[(ok["W_min"] == W) & (ok["liveness"].astype(str) == L)]
                if col is not None:
                    g = g[g[col].astype(str) == str(val)]
                if len(g) == 0:
                    continue
                x, y = ecdf(g["excess"])
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i], width=2),
                                         name=f"L={L} -- n={len(g):,}, median {np.median(g['excess']):+.3f}"))
            cellk = [k for k in s["cells"] if k.endswith(f"|W={W}")]
            lost = "; ".join(f"{k.split('|')[0]}: lost to R3 {s['cells'][k]['share_lost_r3']:.1%}, in thin cells "
                             f"{(s['cells'][k]['pairs_in_thin_cells_share'] or 0):.1%}" for k in cellk)
            views.append((lab, a, len(fig.data), f"T3 -- competition excess, W = {W} min, {lab}: pair log-ratio minus its baseline cell's median<br>"
                                                 f"<sup>cells (year, segment, L, W, age octave); pairs in thin cells (< 20 moments) not drawn. {lost}</sup>"))
        fig.add_vline(x=0, line=dict(color=GRID))
        selector(fig, views)
        lay(fig, views[0][3], "excess = ln(n after / n before) - baseline cell median", "cumulative share of pairs", h=660)
        save(fig, "t3", f"excess_W{W}.html")

    fig = go.Figure()
    for i, L in enumerate(["15", "60", "rest_of_session"]):
        for j, W in enumerate(sorted(cells["W_min"].unique())):
            g = cells[(cells["liveness"] == L) & (cells["W_min"] == W)]
            if len(g) == 0:
                continue
            x, y = ecdf(np.maximum(g["n_finite"], 0.5))
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i], dash=["solid", "dash", "dot"][j], shape="hv"),
                                     name=f"L={L}, W={W} -- {len(g):,} cells, thin {int(g['baseline_thin'].sum()):,}"))
    fig.add_vline(x=20, line=dict(color=PAL[3], dash="dash"), annotation_text="20 moments")
    fig.update_xaxes(type="log")
    lay(fig, f"T3 -- baseline cell sizes (finite moments per cell); {s['baseline_cells']:,} cells, {s['baseline_thin_cells']:,} thin<br>"
             "<sup>zero-moment cells drawn at 0.5 on the log axis</sup>", "finite baseline moments in the cell (log)", "cumulative share of cells")
    save(fig, "t3", "baseline_cells.html")

    ks = list(s["cells"])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[k.replace("|", " · ") for k in ks], y=[s["cells"][k]["share_lost_r3"] for k in ks], marker_color=PAL[3],
                         name="pairs lost to R3", text=[f"{s['cells'][k]['share_lost_r3']:.1%} of {s['cells'][k]['pairs']:,}" for k in ks],
                         textposition="outside"))
    fig.add_trace(go.Bar(x=[k.replace("|", " · ") for k in ks],
                         y=[(s["cells"][k]["baseline"]["lost_r3"] or 0) / max(1, s["cells"][k]["baseline"]["moments_in_span"] or 1) for k in ks],
                         marker_color=PAL[5], name="baseline minutes lost to R3",
                         text=[f"{(s['cells'][k]['baseline']['lost_r3'] or 0):,} of {(s['cells'][k]['baseline']['moments_in_span'] or 0):,}" for k in ks],
                         textposition="outside"))
    fig.update_layout(barmode="group")
    lay(fig, "T3 -- share lost to the segment rule (R3), per (L, W)<br><sup>a window [t - W, t + W] must lie inside one clock segment "
             "with no cross minute</sup>", "liveness · W (min)", "share lost")
    save(fig, "t3", "r3_share_lost.html")


# ====================================================================== T4
def charts_t4():
    cfg = B.load_cfg()
    cost = cfg["cost_reference"]
    ub = pd.read_parquet(B.art("t4_u_peak_bins.parquet"))
    fa = pd.read_parquet(B.art("t4_facets.parquet"))
    ref = pd.read_parquet(B.art("t4a_reference_free_walk.parquet"))
    ex = pd.read_parquet(B.art("t1_excursion.parquet"))
    pop = pd.read_parquet(B.art("t0_population.parquet"))
    va = ex[ex["vector_available"] == True].drop(columns=["slice", "tau_anchor_segment", "price_tier", "year"], errors="ignore")  # noqa: E712
    va = va.merge(pop[["event_id", "slice", "year", "tau_anchor_segment", "price_tier"]], on="event_id", how="left")
    va["jump_share_band"] = B.jump_band(va["jump_share"].to_numpy(), cfg)
    levels = fa[["facet", "level"]].drop_duplicates().values.tolist()

    def subset(g, facet, lev):
        if facet == "all":
            return g
        if facet == "edge_class":
            if lev == "none_of_these":
                return g[~np.any(np.column_stack([g[e].fillna(False).astype(bool) for e in EDGES]), axis=1)]
            return g[g[lev].fillna(False).astype(bool)]
        return g[g[facet].astype("string").fillna("missing") == lev]

    fig = go.Figure()
    views = []
    for N in (50, 100, 200):
        for facet, lev in levels:
            b = ub[(ub["N"] == N) & (ub["facet"] == facet) & (ub["level"] == lev)]
            if b.empty:
                continue
            n = int(b["count"].sum())
            a = len(fig.data)
            mid = (b["bin_lo"] + b["bin_hi"]) / 2
            fig.add_trace(go.Bar(x=mid, y=b["count"], width=0.045, marker_color=RUNG_COL[N], name=f"events -- n={n:,}",
                                 text=b["count"], textposition="outside"))
            fig.add_trace(go.Scatter(x=mid, y=b["reference_share"] * n, mode="lines+markers", line=dict(color=FG, dash="dot"),
                                     name=f"simulated no-drift free walk at N={N}, scaled to n"))
            r = fa[(fa["N"] == N) & (fa["facet"] == facet) & (fa["level"] == lev)].iloc[0]
            views.append((f"N={N} · {facet}: {lev}", a, len(fig.data),
                          f"T4 step zero -- u_peak, N = {N}, {facet} = {lev}, n = {n:,}<br><sup>median {r['u_peak_median']:.3f} "
                          f"(reference {r['ref_u_peak_median']:.3f}); interior 0.1-0.9 {r['u_peak_share_interior_0.1_0.9']:.1%} "
                          f"(reference {r['ref_u_peak_share_interior_0.1_0.9']:.1%}); mass at both ends is what no drift looks like, "
                          f"an interior hump is a rise-then-fall</sup>"))
    selector(fig, views)
    lay(fig, views[0][3], "u_peak (absolute 0.05 bins)", "events per bin", h=640)
    save(fig, "t4", "u_peak.html")

    for c in COMPS:
        fig = go.Figure()
        views = []
        for N in (50, 100, 200):
            gN = va[va["N"] == N]
            rv = ref[ref["N"] == N][c]
            xr, yr = ecdf(rv)
            ri = len(fig.data)
            fig.add_trace(go.Scatter(x=xr, y=yr, mode="lines", line=dict(color=FG, dash="dot"),
                                     name=f"simulated no-drift free walk -- n={rv.size:,}, median {rv.median():.3f}"))
            for facet, lev in levels:
                g = subset(gN, facet, lev)[c].dropna()
                if g.empty:
                    continue
                a = len(fig.data)
                x, y = ecdf(g)
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=RUNG_COL[N], width=2),
                                         name=f"events -- n={g.size:,}, median {g.median():.3f}"))
                views.append((f"N={N} · {facet}: {lev}", [a, ri],
                              f"T4 step zero -- ECDF of {c}, N = {N}, {facet} = {lev}, n = {g.size:,}<br><sup>sigma_path units (realised "
                              f"variance of the bucket returns); reference: Brief 1's simulated discrete free walk at N = {N}</sup>"))
        selector_idx(fig, views)
        lay(fig, views[0][2], f"{c} (sigma_path units)", "cumulative share of events", h=640)
        save(fig, "t4", f"ecdf_{c}.html")

    fig = go.Figure()
    views = []
    tiers = cfg["brief2_diff"]["R4"]["price_tier"]["labels"]
    for unit, col, line in (("bp", "rise_bp", cost["rt_bp"]), ("cents", "rise_cents", cost["rt_cents"])):
        for N in (50, 100, 200):
            a = len(fig.data)
            gN = va[va["N"] == N]
            for i, t in enumerate(tiers):
                g = gN[gN["price_tier"] == t][col].dropna()
                x, y = ecdf(np.arcsinh(g))
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=PAL[i], width=2),
                                         name=f"{t} -- n={g.size:,}, above one round trip {(g > line).mean():.1%}"))
            fig.add_trace(go.Scatter(x=[np.arcsinh(line)] * 2, y=[0, 1], mode="lines", line=dict(color=PAL[3], dash="dash"),
                                     name=f"round-trip cost {line} {unit}"))
            views.append((f"{unit} · N={N}", a, len(fig.data),
                          f"T4 step zero -- the full rise ({col}) against one round trip ({line} {unit}), N = {N}, by price tier (R4)<br>"
                          "<sup>the unconditional version of the necessary-condition cost gate (Part I, I.5b); asinh axis, nothing clipped</sup>"))
    selector(fig, views)
    asinh_axis(fig, [0, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000], ["0", "1", "3", "10", "30", "100", "300", "1k", "3k", "10k", "30k"])
    lay(fig, views[0][3], "rise (asinh axis)", "cumulative share of events", h=640)
    save(fig, "t4", "rise_vs_cost.html")

    cr = pd.read_parquet(B.art("t4_cost.parquet"))
    fig = go.Figure()
    t = cr[cr["facet"] == "price_tier"]
    for N in (50, 100, 200):
        g = t[t["N"] == N].set_index("level").reindex(tiers)
        for unit, col, dash in (("bp", "share_rise_bp_gt_rt", ""), ("cents", "share_rise_cents_gt_rt", "/")):
            fig.add_trace(go.Bar(x=tiers, y=g[col], marker_color=RUNG_COL[N], marker_pattern_shape=dash,
                                 name=f"N={N}, rise > round trip in {unit}",
                                 text=[f"{v:.1%} (n={int(n):,})" for v, n in zip(g[col], g["n"])], textposition="outside"))
    fig.update_layout(barmode="group")
    lay(fig, f"T4 step zero -- share of events whose full rise exceeds one round trip ({cost['rt_bp']} bp flat; {cost['rt_cents']} cents "
             "per share), by price tier (R4)<br><sup>plain bars: bp; hatched: cents; per rung, never pooled</sup>", "price tier (tau price)",
        "share of events", h=640)
    save(fig, "t4", "cost_clearing.html")

    gal = pd.read_parquet(B.art("t4_gallery.parquet"))
    bk = pd.read_parquet(B.art("t4_gallery_buckets.parquet"))
    fig = go.Figure()
    views = []
    for e in gal["event_id"]:
        a = len(fig.data)
        meta = gal[gal["event_id"] == e].iloc[0]
        for N in (50, 100, 200):
            r = va[(va["event_id"] == e) & (va["N"] == N)].iloc[0]
            b = bk[(bk["event_id"] == e) & (bk["N"] == N)].sort_values("i")
            u = np.r_[0.0, b["u"].to_numpy()]
            lp = np.log(np.r_[r["tau_price"], b["vwap"].to_numpy()] / r["tau_price"]) * 1e4
            fig.add_trace(go.Scatter(x=u, y=lp, mode="lines", line=dict(color=RUNG_COL[N], width=1.5),
                                     name=f"N={N}: u_peak {r['u_peak']:.3f}, rise {r['rise_s']:.2f} / fall {r['fall_s']:.2f} sigma_path"))
            fig.add_trace(go.Scatter(x=[r["u_peak"]], y=[lp[int(r["i_peak"])]], mode="markers", showlegend=False,
                                     marker=dict(color=RUNG_COL[N], size=10, symbol="triangle-up")))
            fig.add_trace(go.Scatter(x=[1.0], y=[lp[-1]], mode="markers", showlegend=False,
                                     marker=dict(color=RUNG_COL[N], size=9, symbol="square")))
        fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers", marker=dict(color=FG, size=10), name="tau"))
        r100 = va[(va["event_id"] == e) & (va["N"] == 100)].iloc[0]
        flags = [k for k in EDGES if bool(r100[k])] if all(k in r100 for k in EDGES) else []
        views.append((e, a, len(fig.data),
                      f"T4 gallery -- {e} ({meta['year']}, {meta['tau_anchor_segment']}; stratum of {int(meta['stratum_size']):,})<br>"
                      f"<sup>{int(r100['n_path_prints_all']):,} prints after tau; flags: {', '.join(flags) or 'none'}; "
                      f"price tier {r100['price_tier']}; triangle = peak, square = end; 72 events drawn with seed "
                      f"{cfg['brief2']['t4_step_zero']['gallery']['seed']}</sup>"))
    selector(fig, views)
    lay(fig, views[0][3], "u = share of the path's volume traded (volume clock)", "ln(bucket VWAP / tau price), bp", h=640)
    save(fig, "t4", "gallery.html")


def main() -> int:
    which = sys.argv[1:] or ["t1", "t2", "t3", "t4"]
    for t in which:
        {"t1": charts_t1, "t2": charts_t2, "t3": charts_t3, "t4": charts_t4}[t]()
        print(f"{t} charts written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
