"""
10d Diagnostic 1, T3 -- the frame-scrubbable animation. Chart 06.

Per subset event at D5 = 8 min, four panels on one synced time axis:
  1  tape: price and prints
  2  local median interval through time -- the normalization denominator itself
  3  the histogram at frame t, with surviving peaks, ALL candidate troughs annotated with
     their void values, and the argmax winner marked
  4  the chart-01 absolute track, with a playhead at frame t

T3b: the histogram's x-range AND y-range are fixed across every frame of an event.
T3c: each frame is annotated with clock time, time from the D7 anchor WITH its poll
     interval, in-window print count, and ok share.
T3d: both layout readings on two pre-registered events -- one animation per kernel, and a
     single animation with the three kernels panelled together.

Slider + animation frames. No video, no new dependency.

Usage: .venv/Scripts/python.exe research/phase_10d_diag1/t3_animation.py
"""
from __future__ import annotations

import hashlib
import importlib.util as ilu
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
import chartlib as C  # noqa: E402
from common import ns_to_et, rel  # noqa: E402
_s2 = ilu.spec_from_file_location("t1f", os.path.join(HERE, "t1_frames.py"))
t1f = ilu.module_from_spec(_s2); _s2.loader.exec_module(t1f)
c10c, s1t1 = t1f.c10c, t1f.s1t1

ART = os.path.join(ROOT, "results", "phase_10d_diag1", "artifacts")
OUT = os.path.join(ROOT, "results", "phase_10d_diag1", "charts", "06_animation")
KP = 8.0


def conf():
    with open(os.path.join(ROOT, "config", "phase_10d_diag1.json"), encoding="utf-8") as f:
        return json.load(f)


def frame_payloads(ev, bins, centers, times, half, min_iv):
    """Per-frame histogram, peaks, full trough ladder, winner. Same path as T1."""
    ok_fin = ev["ok"] & np.isfinite(ev["norm"])
    mid_ok, norm_ok = ev["mid"][ok_fin], ev["norm"][ok_fin]
    locmed_ok = ev["loc_med"][ok_fin]
    o = np.argsort(mid_ok, kind="stable")
    mid_ok, norm_ok, locmed_ok = mid_ok[o], norm_ok[o], locmed_ok[o]
    mid_all = np.sort(ev["mid"])
    lo = np.searchsorted(mid_ok, times - half, "left")
    hi = np.searchsorted(mid_ok, times + half, "right")
    la = np.searchsorted(mid_all, times - half, "left")
    ha = np.searchsorted(mid_all, times + half, "right")
    out = []
    for t, a, b, aa, ba in zip(times, lo, hi, la, ha):
        n_in, n_all = int(b - a), int(ba - aa)
        rec = {"t": float(t), "n": n_in, "n_all": n_all,
               "ok_share": (n_in / n_all) if n_all else np.nan,
               "dens": np.zeros(centers.size), "pks": np.zeros(0, int),
               "ladder": [], "winner": None,
               "lm": (float(10.0 ** np.median(locmed_ok[a:b])) if n_in else np.nan)}
        if n_in >= min_iv:
            H = t1f.hist_ladder(norm_ok[a:b], bins, centers)
            if H:
                rec.update(dens=H["dens"], pks=H["pks"], ladder=H["ladder"],
                           winner=H["winner"])
        out.append(rec)
    return out


def build_event(cfg10c, r, F, d1_us, k_min, Cc):
    ev = t1f.event_arrays(cfg10c, r, F, d1_us, k_min)
    if ev is None:
        return None
    ok_fin = ev["ok"] & np.isfinite(ev["norm"])
    nv = ev["norm"][ok_fin]
    if nv.size < Cc["upstream"]["cell_level_ok_minimum"]:
        return None
    e_lo = np.floor(nv.min() * 10) / 10
    e_hi = np.ceil(nv.max() * 10) / 10 + 0.1
    bins = np.arange(e_lo, e_hi, 0.1)
    centers = (bins[:-1] + bins[1:]) / 2.0
    div = int(Cc["frames"]["step_divisor"])
    step_ns = k_min * 60.0 * 1e9 / div
    half = k_min * 60.0 * 1e9 / 2.0
    t_lo, t_hi = float(ev["bounds"]["start_ns"]), float(ev["bounds"]["end_ns"])
    times = t_lo + np.arange(int(np.floor((t_hi - t_lo) / step_ns)) + 1) * step_ns
    capA = int(Cc["charts"]["animation_max_frames"])
    dec = max(1, int(np.ceil(times.size / capA)))
    times = times[::dec]
    fr = frame_payloads(ev, bins, centers, times, half,
                        int(Cc["frames"]["min_intervals_per_frame"]))
    return {"ev": ev, "bins": bins, "centers": centers, "frames": fr,
            "decimation": dec, "n_frames": len(fr), "half": half}


def hist_traces(fr, centers, colr):
    """The four dynamic histogram-panel traces for one frame."""
    lad = fr["ladder"]
    pk_x = centers[fr["pks"]] if len(fr["pks"]) else np.zeros(0)
    pk_y = fr["dens"][fr["pks"]] if len(fr["pks"]) else np.zeros(0)
    tx = np.array([c["loc"] for c in lad]) if lad else np.zeros(0)
    ty = np.array([fr["dens"][c["idx"]] for c in lad]) if lad else np.zeros(0)
    tv = [f"{c['void']:.3f}" for c in lad]
    w = fr["winner"]
    return [
        go.Bar(x=centers, y=fr["dens"], marker_color=colr, name="density",
               hovertemplate="%{x:.2f} dec<br>%{y:.4g}<extra></extra>"),
        go.Scatter(x=pk_x, y=pk_y, mode="markers", name="surviving peaks",
                   marker=dict(color=C.INK, size=8, symbol="triangle-down"),
                   hovertemplate="peak %{x:.2f}<extra></extra>"),
        go.Scatter(x=tx, y=ty, mode="markers+text", name="candidate troughs",
                   marker=dict(color=C.ROWCAP, size=9, symbol="circle-open",
                               line=dict(width=2)),
                   text=tv, textposition="bottom center", textfont=dict(size=8.5),
                   hovertemplate="trough %{x:.2f}<br>void %{text}<extra></extra>"),
        go.Scatter(x=([w["loc"]] if w else []), y=([fr["dens"][w["idx"]]] if w else []),
                   mode="markers", name="argmax winner",
                   marker=dict(color=C.ARM_B, size=15, symbol="star"),
                   hovertemplate="WINNER %{x:.2f}<extra></extra>"),
    ]


def slider_layout(n, labels):
    return dict(
        sliders=[dict(active=0, y=-0.045, x=0.06, len=0.9, pad=dict(t=32),
                      currentvalue=dict(prefix="frame: ", font=dict(size=12)),
                      steps=[dict(method="animate", label=labels[i],
                                  args=[[str(i)], dict(mode="immediate",
                                                       frame=dict(duration=0, redraw=True),
                                                       transition=dict(duration=0))])
                             for i in range(n)])],
        updatemenus=[dict(type="buttons", showactive=False, x=0.005, y=-0.045,
                          xanchor="left", yanchor="top", pad=dict(t=32),
                          buttons=[
                              dict(label="▶", method="animate",
                                   args=[None, dict(frame=dict(duration=140, redraw=True),
                                                    fromcurrent=True,
                                                    transition=dict(duration=0))]),
                              dict(label="❚❚", method="animate",
                                   args=[[None], dict(frame=dict(duration=0, redraw=False),
                                                      mode="immediate")])])])


def main() -> int:
    Cc = conf()
    chash = hashlib.sha256(json.dumps(Cc, sort_keys=True).encode()).hexdigest()[:8]
    cfg10c = c10c.load_cfg()
    F = float(c10c.class_m(cfg10c)["D4_median_precision_factor"])
    d1_us = float(c10c.class_m(cfg10c)["D1_sweep_floor_us"])
    with open(os.path.join(ROOT, "config", "phase_10c.json"), encoding="utf-8") as f:
        poll = json.load(f)["data"]["detection_anchor_variant"]
    poll_s = int(poll.replace("poll", ""))
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)

    dev = c10c.load_dev_sample(cfg10c)
    subset = [(e["ticker"], e["event_date_canonical"]) for e in Cc["event_subset"]["events"]]
    dev = dev[dev.apply(lambda r: (r.ticker, r.event_date_canonical) in subset, axis=1)]
    layout_events = [(e["ticker"], e["event_date_canonical"])
                     for e in Cc["charts"]["animation_layout_events"]]
    os.makedirs(OUT, exist_ok=True)
    manifest, layout_rows = [], []
    t0 = time.perf_counter()

    for r in dev.itertuples(index=False):
        B = build_event(cfg10c, r, F, d1_us, KP, Cc)
        if B is None:
            manifest.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                             "kernel_min": KP, "built": False,
                             "why": "10c declines this cell (insufficient_context)"})
            continue
        ev, centers, frames = B["ev"], B["centers"], B["frames"]
        drow = det[(det.ticker == r.ticker)
                   & (det.event_date_canonical == r.event_date_canonical)
                   & (np.isclose(det.threshold, 1.25))]
        det_ns = (float(drow.iloc[0]["det_ns_poll0"])
                  if len(drow) and pd.notna(drow.iloc[0].get("det_ns_poll0")) else np.nan)

        ok_fin = ev["ok"] & np.isfinite(ev["norm"])
        mid_ok = ev["mid"][ok_fin]
        lm_track_x = ns_to_et(mid_ok.astype(np.int64))
        lm_track_y = 10.0 ** ev["loc_med"][ok_fin]
        win_x = ns_to_et(np.array([f["t"] for f in frames if f["winner"]], dtype=np.int64))
        win_y = [f["lm"] * 10.0 ** f["winner"]["loc"] for f in frames if f["winner"]]
        all_x, all_y, all_v = [], [], []
        for f in frames:
            for c in f["ladder"]:
                all_x.append(f["t"]); all_y.append(f["lm"] * 10.0 ** c["loc"])
                all_v.append(c["void"])
        all_x = ns_to_et(np.array(all_x, dtype=np.int64)) if all_x else []

        ymax = max(float(np.max(f["dens"])) for f in frames) * 1.12 or 1.0
        fig = make_subplots(
            rows=4, cols=1, vertical_spacing=0.075,
            row_heights=[0.21, 0.19, 0.35, 0.25],
            subplot_titles=[
                f"Tape — {r.ticker} {r.event_date_canonical}",
                "Local median interval (s) — the normalization denominator",
                f"Histogram at frame t — fixed axes across all {B['n_frames']} frames",
                "Absolute-units candidate track (chart 01) with a playhead"])

        f0 = frames[0]
        pxx = ns_to_et(ev["agg_ts"])
        fig.add_trace(go.Scattergl(x=pxx, y=ev["agg_px"], mode="lines", name="price",
                                   line=dict(color=C.INK, width=1)), row=1, col=1)     # 0
        fig.add_trace(go.Scatter(x=[pxx[0], pxx[0]], y=[float(np.nanmin(ev["agg_px"])),
                                                        float(np.nanmax(ev["agg_px"]))],
                                 mode="lines", name="playhead", showlegend=False,
                                 line=dict(color=C.ARM_B, width=2)), row=1, col=1)     # 1
        fig.add_trace(go.Scattergl(x=lm_track_x, y=lm_track_y, mode="markers",
                                   name="local median", showlegend=False,
                                   marker=dict(color=C.SIDECAR, size=1.8)), row=2, col=1)  # 2
        fig.add_trace(go.Scatter(x=[pxx[0], pxx[0]],
                                 y=[float(np.nanmin(lm_track_y)), float(np.nanmax(lm_track_y))],
                                 mode="lines", showlegend=False,
                                 line=dict(color=C.ARM_B, width=2)), row=2, col=1)     # 3
        for tr in hist_traces(f0, centers, C.ARM_A):                                    # 4..7
            fig.add_trace(tr, row=3, col=1)
        if len(all_x):
            fig.add_trace(go.Scattergl(x=all_x, y=all_y, mode="markers",
                                       name="candidates", showlegend=False,
                                       marker=dict(color=all_v, colorscale="Viridis",
                                                   size=2.6, opacity=0.55, cmin=0, cmax=1)),
                          row=4, col=1)                                                 # 8
        fig.add_trace(go.Scattergl(x=win_x, y=win_y, mode="markers", name="winner",
                                   showlegend=False,
                                   marker=dict(color=C.ARM_B, size=3.4)), row=4, col=1)  # 9
        ylo = max(min(all_y) if all_y else 1e-6, 1e-7)
        yhi = max(all_y) if all_y else 1.0
        fig.add_trace(go.Scatter(x=[pxx[0], pxx[0]], y=[ylo, yhi], mode="lines",
                                 showlegend=False,
                                 line=dict(color=C.ARM_B, width=2)), row=4, col=1)      # 10
        for v, lab in zip(Cc["reference_lines_s"], ["1 ms", "10 ms", "100 ms", "1 s", "10 s"]):
            fig.add_hline(y=v, line=dict(color=C.GRID, width=1, dash="dot"), row=4, col=1)

        dyn = [1, 3, 4, 5, 6, 7, 10]
        go_frames, labels = [], []
        for i, f in enumerate(frames):
            ph = ns_to_et(np.array([f["t"], f["t"]], dtype=np.int64))
            anch = ("n/a" if not np.isfinite(det_ns)
                    else f"{(f['t']-det_ns)/1e9:+,.0f} s")
            # Python 3.11 does not allow a multi-line expression inside an f-string;
            # build the clock label first.
            clock = (pd.Timestamp(int(f["t"]), unit="ns", tz="UTC")
                     .tz_convert("America/New_York").strftime("%H:%M:%S"))
            lad_txt = ("THIN — no ladder" if not f["ladder"]
                       else f"{len(f['ladder'])} candidate troughs")
            ann = dict(text=(f"<b>{clock} ET</b>   ·   D7 anchor ({poll}, poll interval "
                             f"{poll_s} s): {anch}   ·   in-window prints "
                             f"{f['n_all']+1:,}   ·   ok share {f['ok_share']:.1%}"
                             f"   ·   {lad_txt}"),
                       xref="paper", yref="paper", x=0.0, y=1.055, showarrow=False,
                       xanchor="left", font=dict(size=12, color=C.INK))
            labels.append(pd.Timestamp(int(f["t"]), unit="ns", tz="UTC")
                          .tz_convert("America/New_York").strftime("%H:%M"))
            data = [go.Scatter(x=ph, y=[float(np.nanmin(ev["agg_px"])),
                                        float(np.nanmax(ev["agg_px"]))], mode="lines",
                               line=dict(color=C.ARM_B, width=2)),
                    go.Scatter(x=ph, y=[float(np.nanmin(lm_track_y)),
                                        float(np.nanmax(lm_track_y))], mode="lines",
                               line=dict(color=C.ARM_B, width=2))]
            data += hist_traces(f, centers, C.ARM_A)
            data += [go.Scatter(x=ph, y=[ylo, yhi], mode="lines",
                                line=dict(color=C.ARM_B, width=2))]
            go_frames.append(go.Frame(data=data, traces=dyn, name=str(i),
                                      layout=go.Layout(annotations=[ann])))
        fig.frames = go_frames

        fig.update_yaxes(title_text="price", row=1, col=1)
        fig.update_yaxes(type="log", title_text="local median (s)", row=2, col=1)
        fig.update_xaxes(range=[float(centers.min()), float(centers.max())], row=3, col=1,
                         title_text="normalized log10 interval (decades)")
        fig.update_yaxes(range=[0, ymax], title_text="density", row=3, col=1)
        fig.update_yaxes(type="log", title_text="candidate (s), log", row=4, col=1)
        fig.update_layout(**slider_layout(len(frames), labels))

        cap = C.caption(
            sample=(f"{r.ticker} {r.event_date_canonical} · kernel {KP:g} min · "
                    f"{B['n_frames']} frames shown of "
                    f"{B['n_frames']*B['decimation']} computed (every "
                    f"{B['decimation']}{'st' if B['decimation']==1 else 'th'}), frame window "
                    f"= kernel width, step = kernel/8 = 1 min."),
            filters=("Frames with fewer than 30 in-window intervals are `thin`: the "
                     "histogram is drawn empty and no ladder is shown. No fallback boundary "
                     "is ever supplied."),
            chash=chash,
            extra=("<b>NON-CAUSAL.</b> The window is centered, so every frame reads forward "
                   "in time by half a kernel. Nothing here is a detector, a signal or an "
                   "operating point.<br><b>Axes are fixed across every frame</b> (T3b) — a "
                   "rescaling axis would make a stationary distribution look like it is "
                   "moving.<br>Panel 3's circles are EVERY candidate trough with its void; "
                   "the star is the argmax winner. Description only — no boundary rule is "
                   "adopted anywhere in this diagnostic."))
        C.finish(fig, f"Chart 06 — The distribution through time · {r.ticker} {r.event_date_canonical}",
                 "10d-diag1 T3a · scrubbable; drag the slider or press play",
                 cap, height=Cc["charts"]["height_animation"], width=Cc["charts"]["width"])
        name = f"{r.ticker}_{r.event_date_canonical}_k8"
        os.makedirs(OUT, exist_ok=True)
        html = os.path.join(OUT, f"{name}.html")
        fig.write_html(html, include_plotlyjs="cdn", full_html=True,
                       config={"displaylogo": False})
        manifest.append({"ticker": r.ticker,
                         "event_date_canonical": r.event_date_canonical,
                         "kernel_min": KP, "built": True, "chart": f"{name}.html",
                         "frames_shown": B["n_frames"], "decimation": B["decimation"],
                         "megabytes": round(os.path.getsize(html) / 1e6, 2)})
        print(f"  {name}.html  {B['n_frames']} frames  "
              f"{os.path.getsize(html)/1e6:.2f} MB  ({time.perf_counter()-t0:.0f}s)",
              flush=True)

        # ---------------- T3d: both layout readings, on the two pre-registered events
        if (r.ticker, r.event_date_canonical) in layout_events:
            per_k, grids = [], {}
            for k in Cc["upstream"]["kernels_min"]:
                Bk = build_event(cfg10c, r, F, d1_us, k, Cc)
                if Bk is None:
                    per_k.append({"kernel_min": k, "built": False})
                    continue
                grids[k] = (float(Bk["centers"].min()), float(Bk["centers"].max()),
                            int(Bk["centers"].size))
                fk = go.Figure(
                    data=hist_traces(Bk["frames"][0], Bk["centers"], C.ARM_A),
                    frames=[go.Frame(data=hist_traces(f, Bk["centers"], C.ARM_A),
                                     traces=[0, 1, 2, 3], name=str(i))
                            for i, f in enumerate(Bk["frames"])])
                ym = max(float(np.max(f["dens"])) for f in Bk["frames"]) * 1.12 or 1.0
                fk.update_xaxes(range=[float(Bk["centers"].min()), float(Bk["centers"].max())],
                                title_text="normalized log10 interval (decades)")
                fk.update_yaxes(range=[0, ym], title_text="density")
                fk.update_layout(**slider_layout(
                    len(Bk["frames"]),
                    [pd.Timestamp(int(f["t"]), unit="ns", tz="UTC")
                     .tz_convert("America/New_York").strftime("%H:%M") for f in Bk["frames"]]))
                C.finish(fk, f"Layout A (per kernel) — {r.ticker} {r.event_date_canonical}, "
                             f"kernel {k:g} min",
                         "10d-diag1 T3d · one animation per kernel",
                         C.caption(sample=f"{Bk['n_frames']} frames, kernel {k:g} min.",
                                   filters="thin frames drawn empty.", chash=chash,
                                   extra="Layout A reading: three separate files."),
                         height=620, width=Cc["charts"]["width"])
                pth = os.path.join(OUT, f"layoutA_{r.ticker}_{r.event_date_canonical}_k{k:g}.html")
                fk.write_html(pth, include_plotlyjs="cdn", full_html=True)
                per_k.append({"kernel_min": k, "built": True, "frames": Bk["n_frames"],
                              "megabytes": round(os.path.getsize(pth) / 1e6, 2),
                              "file": os.path.basename(pth)})

            built = [k for k in Cc["upstream"]["kernels_min"] if k in grids]
            fc = make_subplots(rows=1, cols=len(built),
                               subplot_titles=[f"kernel {k:g} min" for k in built],
                               horizontal_spacing=0.055)
            Bs = {k: build_event(cfg10c, r, F, d1_us, k, Cc) for k in built}
            nmin = min(Bs[k]["n_frames"] for k in built)
            base, fr_all = [], []
            for ci, k in enumerate(built, 1):
                for tr in hist_traces(Bs[k]["frames"][0], Bs[k]["centers"], C.ARM_A):
                    fc.add_trace(tr, row=1, col=ci)
                ym = max(float(np.max(f["dens"])) for f in Bs[k]["frames"]) * 1.12 or 1.0
                fc.update_xaxes(range=[float(Bs[k]["centers"].min()),
                                       float(Bs[k]["centers"].max())], row=1, col=ci)
                fc.update_yaxes(range=[0, ym], row=1, col=ci)
            for i in range(nmin):
                dat = []
                for k in built:
                    j = int(round(i * (Bs[k]["n_frames"] - 1) / max(nmin - 1, 1)))
                    dat += hist_traces(Bs[k]["frames"][j], Bs[k]["centers"], C.ARM_A)
                fr_all.append(go.Frame(data=dat, traces=list(range(len(dat))), name=str(i)))
            fc.frames = fr_all
            fc.update_layout(**slider_layout(
                nmin, [pd.Timestamp(int(f["t"]), unit="ns", tz="UTC")
                       .tz_convert("America/New_York").strftime("%H:%M")
                       for f in Bs[built[0]]["frames"][:nmin]]))
            grid_note = " · ".join(f"{k:g} min: [{g[0]:.2f}, {g[1]:.2f}] over {g[2]} bins"
                                   for k, g in grids.items())
            C.finish(fc, f"Layout B (combined) — {r.ticker} {r.event_date_canonical}",
                     "10d-diag1 T3d · the three kernels panelled together, one slider",
                     C.caption(
                         sample=f"{nmin} synchronised frames across {len(built)} kernels.",
                         filters="thin frames drawn empty.",
                         chash=chash,
                         extra=(f"<b>The three kernels do not share a bin grid</b> — each "
                                f"cell's grid is derived from its own full-session normalized "
                                f"range: {grid_note}.<br>Layout B therefore needs three "
                                f"x-axes and the panels cannot be compared bin-for-bin by "
                                f"eye. Layout A avoids that but costs three files and "
                                f"three sliders.")),
                     height=560, width=Cc["charts"]["width"])
            pthB = os.path.join(OUT, f"layoutB_{r.ticker}_{r.event_date_canonical}_combined.html")
            fc.write_html(pthB, include_plotlyjs="cdn", full_html=True)
            layout_rows.append({
                "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                "layoutA_files": per_k,
                "layoutA_total_megabytes": round(sum(p.get("megabytes", 0) for p in per_k), 2),
                "layoutA_n_files": sum(1 for p in per_k if p.get("built")),
                "layoutB_file": os.path.basename(pthB),
                "layoutB_megabytes": round(os.path.getsize(pthB) / 1e6, 2),
                "layoutB_n_files": 1,
                "layoutB_frames": nmin,
                "bin_grids_differ_across_kernels": len({g[2] for g in grids.values()}) > 1,
                "bin_grids": {str(k): list(g) for k, g in grids.items()}})
            print(f"    T3d layouts written for {r.ticker}", flush=True)

    with open(os.path.join(ART, "t3_animation_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T3", "config_hash": chash, "kernel_min": KP,
                   "animations": manifest, "T3d_layout_comparison": layout_rows,
                   "untracked_convention": ("charts/06_animation/ follows 10c's "
                                            "s1_06_animation_full/ convention: regenerable, "
                                            "not tracked, this manifest is the record")},
                  f, indent=2, default=str)
    built = [m for m in manifest if m.get("built")]
    print(f"\n{len(built)} animations built, "
          f"{sum(m['megabytes'] for m in built):.1f} MB total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
