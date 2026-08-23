"""Phase 10c Stage 0 charts. Linked panels on a shared x-axis; no dual y-scale."""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART, CH = "results/phase_10c/artifacts", "results/phase_10c/charts"
PROM = 0.05


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    E = c10c.class_e(cfg)
    man = []

    # ------------------------------------------------------------ S0-1
    dc = pd.read_parquet(rel(f"{ART}/t0_1_density_curves.parquet"))
    ev = pd.read_parquet(rel(f"{ART}/t0_1_raw_landscape.parquet"))
    e1 = ev[ev.prominence_frac == PROM].copy()
    reps = e1.sort_values("n_prints_raw").iloc[np.linspace(0, len(e1) - 1, 10).astype(int)]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, subplot_titles=[
        "Per-event log-interval density, 10 representative events",
        "Across-event distribution of the three T0.1 summary quantities"])
    for _, r in reps.iterrows():
        s = dc[(dc.ticker == r.ticker) & (dc.event_date_canonical == r.event_date_canonical)]
        s = s.sort_values("log10s")
        fig.add_trace(go.Scatter(x=s.log10s, y=s.density, mode="lines",
                                 line=dict(width=1.4, color=C.ARM_B if r.is_sidecar else C.ARM_A),
                                 opacity=0.75, showlegend=False,
                                 name=f"{r.ticker} {r.event_date_canonical}",
                                 hovertemplate=f"{r.ticker} {r.event_date_canonical}<br>"
                                               "log10 %{x:.2f}<br>density %{y:.3f}<extra></extra>"),
                      row=1, col=1)
    for col, lab, colr in (("leftmost_mode_log10s", "leftmost mode", C.ARM_A),
                           ("first_trough_log10s", "first trough right of it", C.ARM_B),
                           ("largest_peak_log10s", "largest peak", C.INK2)):
        v = e1[col].dropna()
        fig.add_trace(go.Box(x=v, name=f"{lab} (n={len(v)})", marker_color=colr,
                             boxpoints="all", jitter=0.5, pointpos=0, marker=dict(size=4),
                             orientation="h", showlegend=False), row=1, col=2)
    for c_ in (1, 2):
        fig.update_xaxes(title_text="log10 inter-trade interval (s)", row=1, col=c_)
    fig.update_yaxes(title_text="density", row=1, col=1)
    lm = e1.leftmost_mode_log10s.dropna()
    C.finish(fig, "S0-1 — Raw interval landscape (T0.1)",
             "Per-event log-interval histograms, bin width 0.1 log units, no smoothing, exact "
             "timestamp ties collapsed per D12. Nothing is pooled across events: the right panel "
             "is the distribution ACROSS events of a per-event summary quantity.",
             C.caption(f"dev sample n={len(e1)} events (44 primary + sidecar shown in the second "
                       f"colour); {int(ev.n_intervals.sum()/len(ev.prominence_frac.unique())):,} intervals",
                       f"prominence = {PROM} of each event's own peak density; support fixed at "
                       "log10 -9 to +5 so events are comparable without pooling", chash,
                       f"<b>The leftmost mode sits at log10 {lm.median():+.2f}, i.e. "
                       f"{10**lm.median()*1e9:.0f} nanoseconds</b> (p10 {lm.quantile(.1):+.2f}, "
                       f"p90 {lm.quantile(.9):+.2f}). This is the v4 fragmentation mode, present "
                       "and unambiguous."),
             height=620, width=1500)
    man.append(C.write(fig, rel(CH), "s0_1_raw_landscape"))

    # ------------------------------------------------------------ S0-2
    fl = pd.read_parquet(rel(f"{ART}/t0_2_floor_sensitivity.parquet"))
    g = fl.groupby("floor_us")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
                        subplot_titles=["Fraction of raw prints absorbed by aggregation",
                                        "Leftmost surviving mode after aggregation"])
    q = g["frac_absorbed"].quantile
    fig.add_trace(go.Scatter(x=sorted(fl.floor_us.unique()), y=g["frac_absorbed"].median().values,
                             mode="lines+markers", line=dict(color=C.ARM_A, width=2.5),
                             marker=dict(size=9), name="median absorbed"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=list(sorted(fl.floor_us.unique())) + list(sorted(fl.floor_us.unique()))[::-1],
        y=list(q(.9).values) + list(q(.1).values)[::-1], fill="toself", fillcolor=C.ARM_A,
        opacity=0.18, line=dict(width=0), name="p10-p90", hoverinfo="skip"), row=1, col=1)
    mm = g[f"leftmost_mode_p{PROM}"].median()
    fig.add_trace(go.Scatter(x=mm.index, y=mm.values, mode="lines+markers",
                             line=dict(color=C.ARM_B, width=2.5), marker=dict(size=9),
                             name="median leftmost mode"), row=2, col=1)
    fig.add_trace(go.Scatter(x=mm.index, y=np.log10(np.asarray(mm.index, float) / 1e6),
                             mode="lines", line=dict(color="#C23531", width=2, dash="dash"),
                             name="the floor itself"), row=2, col=1)
    fig.update_xaxes(type="log", title_text="candidate D1 sweep floor (microseconds, log)",
                     row=2, col=1)
    fig.update_yaxes(title_text="fraction absorbed", row=1, col=1)
    fig.update_yaxes(title_text="log10 interval (s)", row=2, col=1)
    C.finish(fig, "S0-2 — Sweep-floor sensitivity (T0.2)",
             "Every candidate floor is reported; none is recommended. The red dashed line in the "
             "lower panel is the floor itself, plotted in the same units as the mode.",
             C.caption(f"dev sample n={fl.ticker.nunique()} tickers / {len(fl)//5} events, "
                       "5 candidate floors",
                       f"aggregation is anchor-based: a group opens at a print and closes when a "
                       f"print exceeds the floor from that opening print, so each aggregated event "
                       f"spans at most the floor; prominence {PROM}", chash,
                       "<b>The leftmost mode tracks the floor one-for-one across the whole "
                       "candidate range</b> — it lands in the first bin above the floor at every "
                       "value tested. Aggregation relocates the fast mode rather than removing it. "
                       "Median absorbed rises from 2.3% at 1 µs to 53.5% at 10 ms.<br>"
                       "The config guide asks whether the floor that clears the sub-microsecond "
                       "mode and the floor that starts destroying real structure are far apart. "
                       "<b>They are not separated anywhere in the tested range.</b>"),
             height=760, width=1440)
    man.append(C.write(fig, rel(CH), "s0_2_sweep_floor"))

    # ------------------------------------------------------------ S0-3
    fig = go.Figure()
    for f_ in sorted(fl.floor_us.unique()):
        v = fl[fl.floor_us == f_][f"largest_peak_p{PROM}"].dropna()
        fig.add_trace(go.Box(y=v, name=f"{f_} µs (n={len(v)})", boxpoints="all", jitter=0.4,
                             pointpos=0, marker=dict(size=4), line=dict(color=C.ARM_A)))
    fig.update_yaxes(title_text="log10 location of largest histogram peak (s)")
    fig.update_xaxes(title_text="candidate D1 sweep floor")
    C.finish(fig, "S0-3 — Candidate intraburst peak location (T0.3)",
             "Across-event distribution of the largest peak location in the aggregated histogram, "
             "one box per candidate floor. This is the quantity D2_max_cutoff_ms must sit above.",
             C.caption(f"dev sample, {len(fl)//5} events per floor",
                       f"prominence {PROM} of each event's own peak density; no smoothing", chash,
                       "The distribution carries a long right tail at every floor — p90 sits "
                       "between log10 +0.8 and +1.4, i.e. 6 to 25 seconds, because for many events "
                       "the histogram's dominant peak is the slow interburst mode rather than a "
                       "fast one. Setting D2 above the bulk of this distribution is what keeps "
                       "right-tail events from returning <code>no_intraburst_peak</code>."),
             height=680, width=1280)
    man.append(C.write(fig, rel(CH), "s0_3_peak_location"))

    # ------------------------------------------------------------ S0-4
    d4 = pd.read_parquet(rel(f"{ART}/t0_4_density_d4.parquet"))
    g4 = d4.groupby("precision_factor")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
                        subplot_titles=["Derived minimum print count in the window",
                                        "Resulting too_few_prints fraction"])
    fig.add_trace(go.Scatter(x=g4["derived_min_count"].median().index,
                             y=g4["derived_min_count"].median().values, mode="lines+markers",
                             line=dict(color=C.ARM_A, width=2.5), marker=dict(size=10),
                             name="median derived floor"), row=1, col=1)
    u = d4.drop_duplicates(subset=["ticker", "event_date_canonical"])
    fig.add_hline(y=float(u.window_count_median.median()), line=dict(color="#C23531", width=2,
                  dash="dash"), row=1, col=1,
                  annotation_text=f"median achievable count in a 4-min window "
                                  f"({u.window_count_median.median():.0f})",
                  annotation_position="top left")
    for st, col in ((0.5, C.ARM_B), (0.9, C.INK2)):
        fig.add_trace(go.Scatter(x=g4["too_few_prints_fraction"].quantile(st).index,
                                 y=g4["too_few_prints_fraction"].quantile(st).values,
                                 mode="lines+markers", line=dict(color=col, width=2.5),
                                 marker=dict(size=9),
                                 name=f"too_few_prints, p{int(st*100)}"), row=2, col=1)
    fig.update_xaxes(title_text="candidate D4_median_precision_factor", row=2, col=1)
    fig.update_yaxes(type="log", title_text="prints (log)", row=1, col=1)
    fig.update_yaxes(title_text="fraction of intervals", row=2, col=1)
    m12 = d4[d4.precision_factor == 1.2]
    C.finish(fig, "S0-4 — D4 precision-factor sensitivity at the 4-minute kernel (T0.4 / A1.3)",
             "Derived floor is n >= (sqrt(pi/2) * sigma_log10 / log10 F)^2, from the asymptotic "
             "standard error of a sample median. sigma_log10 is each event's own spread, so the "
             "floor is data-derived per event, not chosen.",
             C.caption(f"dev sample n={len(u)} events; sigma_log10 median "
                       f"{u.sigma_log10.median():.2f} decades",
                       "centered 4-minute clock-time window, clipped at extended-day bounds; "
                       "window counts taken on tie-collapsed prints", chash,
                       "<b>A1.3 asks whether the too_few_prints fraction is flat or steep across "
                       "this range. It is steep, so D4 is load-bearing rather than a preference.</b>"
                       f"<br>At the value currently set, F = 1.2, the derived floor is "
                       f"{m12.derived_min_count.median():,.0f} prints against a median achievable "
                       f"{u.window_count_median.median():.0f} in a 4-minute window; the median "
                       f"event's too_few_prints fraction is {m12.too_few_prints_fraction.median():.3f} "
                       f"and {int((m12.too_few_prints_fraction >= 1.0).sum())} of {len(m12)} events "
                       "have no usable interval at all."),
             height=800, width=1440)
    man.append(C.write(fig, rel(CH), "s0_4_d4_sensitivity"))

    # ------------------------------------------------------------ S0-5
    cl = pd.read_parquet(rel(f"{ART}/t0_5_clipped_fraction.parquet"))
    piv = cl.pivot_table(index="kernel_min", columns="cut_at_rth", values="clipped_fraction",
                         aggfunc="median")
    span, rth_o, rth_c = 960.0, 330.0, 720.0     # 04:00-20:00, 09:30, 16:00, minutes from 04:00
    ks = sorted(cl.kernel_min.unique())
    tgrid = np.arange(0, span, 2.0)
    Z = np.zeros((len(ks), len(tgrid)))
    for i, k in enumerate(ks):
        h = k / 2.0
        clip = (tgrid - h < 0) | (tgrid + h > span)
        clip |= ((tgrid - h < rth_o) & (tgrid > rth_o)) | ((tgrid + h > rth_o) & (tgrid < rth_o))
        clip |= ((tgrid - h < rth_c) & (tgrid > rth_c)) | ((tgrid + h > rth_c) & (tgrid < rth_c))
        Z[i] = clip.astype(float)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12, subplot_titles=[
        "Realized clipped fraction per event, median across events",
        "Where a centered window is clipped, by time of session (RTH boundaries treated as cuts)"])
    for col, lab, colr in (((False, "extended-day boundaries only", C.ARM_A)),
                           ((True, "plus RTH open and close", C.ARM_B))):
        fig.add_trace(go.Scatter(x=piv.index, y=piv[col], mode="lines+markers",
                                 line=dict(color=colr, width=2.5), marker=dict(size=9),
                                 name=lab), row=1, col=1)
    fig.add_trace(go.Heatmap(z=Z, x=tgrid, y=[str(k) for k in ks], colorscale=[[0, "#FBFBFB"],
                             [1, "#C23531"]], showscale=False,
                             hovertemplate="minutes from 04:00 %{x}<br>kernel %{y} min<br>"
                                           "clipped %{z}<extra></extra>"), row=2, col=1)
    fig.add_vline(x=rth_o, line=dict(color=C.INK2, width=1.6, dash="dot"), row=2, col=1)
    fig.add_vline(x=rth_c, line=dict(color=C.INK2, width=1.6, dash="dot"), row=2, col=1)
    fig.update_xaxes(type="log", title_text="kernel duration (minutes, log)", row=1, col=1)
    fig.update_xaxes(title_text="minutes from extended-day open (04:00 ET); dotted lines are "
                                "09:30 and 16:00", row=2, col=1)
    fig.update_yaxes(title_text="clipped fraction", row=1, col=1)
    fig.update_yaxes(title_text="kernel (min)", type="category", row=2, col=1)
    C.finish(fig, "S0-5 — Clipped-window fraction (T0.5)",
             "A centered clock-time window is clipped where it would reach past a session "
             "boundary. Both boundary definitions are reported because the prompt motivates "
             "clipping solely by the overnight gap, which points at the extended-day edges, while "
             "a window spanning the RTH open mixes two very different rate regimes.",
             C.caption(f"dev sample n={cl.ticker.nunique()} tickers, "
                       f"{len(cl.kernel_min.unique())} candidate kernels",
                       "upper panel is realized per-event fractions weighted by where prints "
                       "actually fall; lower panel is the analytic clip condition on a regular "
                       "session, which depends only on time of session and kernel duration", chash,
                       "<b>The two definitions give different answers for D11 and the choice "
                       "between them is the decision.</b> Under extended-day clipping the median "
                       f"fraction is {piv[False].loc[256]:.4f} even at 256 minutes and only "
                       f"{piv[False].loc[512]:.3f} at 512. Under RTH clipping it reaches "
                       f"{piv[True].loc[128]:.3f} at 128 minutes and {piv[True].loc[512]:.3f} at "
                       "512, since a 512-minute centered window cannot fit inside a 390-minute "
                       "regular session anywhere."),
             height=880, width=1440)
    man.append(C.write(fig, rel(CH), "s0_5_clipped_fraction"))

    c10c.write_json(rel(f"{ART}/t0_chart_manifest.json"),
                    {"config_hash": chash, "charts": man,
                     "source": "research/phase_10c/t0_charts.py:main"})
    print(f"{len(man)} charts written; kaleido "
          f"{sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
