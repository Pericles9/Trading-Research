"""
Phase 10c Stage 1, T6a/b/c -- animated local-normalized log-interval histogram, on a
handful of events, in BOTH candidate layouts (per-kernel separate, and combined),
for Cooper's choice (T6c -- explicitly not an agent decision).

Each frame is a REAL recomputation, not an interpolation: for a sampled frame time t,
the histogram shown is built from the log-intervals whose midpoint falls in
[t - kernel/2, t + kernel/2] (the same window definition T1 uses for the local
median), normalized by each interval's own local median from the full-event rolling
computation. Peaks are freshly detected per frame (Poisson floor, same as T1). The
event's single chosen threshold (computed once, on the full pooled histogram, per
T1's actual mechanism) is overlaid as a fixed reference line -- Stage 1 does not
choose a threshold per frame; this view shows how the local shape moves relative to
that fixed choice over the session.

4 sample events, one per notable case:
  ASPI 2023-08-01  rth, highest void (kernel=8) -- clean separation
  OCUL 2020-10-07  rth, lowest void (kernel=8)  -- messy, also a duplicated dev-sample ticker
  ZENA 2024-10-11  premarket, highest void
  CELH 2020-08-06  evening, the only evening example with n_subbursts > 0

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t6_animation.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import find_peaks, peak_prominences

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
import chartlib as C  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
OUT = "results/phase_10c/charts"
KERNELS = [2.0, 8.0, 32.0]
N_FRAMES = 24

SAMPLE_EVENTS = [
    ("ASPI", "2023-08-01", "rth, highest void"),
    ("OCUL", "2020-10-07", "rth, lowest void"),
    ("ZENA", "2024-10-11", "premarket, highest void"),
    ("CELH", "2020-08-06", "evening"),
]


def peaks_poisson(cnt):
    pk, _ = find_peaks(cnt)
    if pk.size == 0:
        return pk
    prom = peak_prominences(cnt, pk)[0]
    return pk[prom > np.sqrt(np.maximum(cnt[pk], 1))]


def envelope_boundary(centers, dens, pks):
    best = None
    for a, b in zip(pks[:-1], pks[1:]):
        if b - a < 2:
            continue
        seg = dens[a + 1:b]
        t = a + 1 + int(np.argmin(seg))
        den = np.sqrt(dens[a] * dens[b])
        if den <= 0:
            continue
        v = float(1.0 - dens[t] / den)
        if best is None or v > best["void"]:
            best = {"idx": int(t), "loc": float(centers[t]), "void": v}
    return best


def compute_event(cfg, ticker, date, momentum_pct, k_min, F):
    d = p10.read_event_trades(cfg, ticker, date, momentum_pct, offsets=(0,))
    s0 = d.get(0)
    raw_ts = s0["sip_timestamp"].to_numpy()
    uniq = np.unique(raw_ts)
    agg_ts, _ = c10c.sweep_aggregate(uniq, float(c10c.class_m(cfg)["D1_sweep_floor_us"]))
    dt_s = np.diff(agg_ts).astype(np.float64) / 1e9
    keep = dt_s > 0
    li = np.log10(dt_s[keep])
    mid = ((agg_ts[:-1].astype(np.float64) + agg_ts[1:].astype(np.float64)) / 2.0)[keep]
    b = c10c.session_bounds(date)
    edges = np.array([b["start_ns"], b["rth_open_ns"], b["rth_close_ns"], b["end_ns"]],
                     dtype=np.float64)
    seg_i = np.clip(np.searchsorted(edges, mid, "right") - 1, 0, len(edges) - 2)
    sigma = float(np.std(li, ddof=1))
    floor = c10c.median_se_min_count(sigma, F)

    ser = pd.Series(li, index=pd.to_datetime(mid.astype("int64"), unit="ns"))
    loc_med = np.full(li.size, np.nan)
    wcount = np.zeros(li.size)
    win = f"{int(k_min)}min"
    for _bi in np.unique(seg_i):
        m_ = seg_i == _bi
        sub = ser[m_]
        if sub.size == 0:
            continue
        _roll = sub.rolling(win, center=True, min_periods=1)
        loc_med[m_] = _roll.median().to_numpy()
        wcount[m_] = _roll.count().to_numpy()
    ok = wcount >= floor if np.isfinite(floor) else np.zeros(li.size, bool)
    norm = li - loc_med

    nv = norm[ok & np.isfinite(norm)]
    if nv.size < 50:
        return {"mid": mid, "norm": norm, "ok": ok, "bins": np.array([-1.0, 1.0]),
               "centers": np.array([0.0]), "global_threshold": None, "global_void": None,
               "session_bounds": b, "label": "insufficient_context"}
    e_lo, e_hi = np.floor(nv.min() * 10) / 10, np.ceil(nv.max() * 10) / 10 + 0.1
    bins = np.arange(e_lo, e_hi, 0.1)
    cnt, _ = np.histogram(nv, bins=bins)
    centers = (bins[:-1] + bins[1:]) / 2.0
    dens_full = cnt / (cnt.sum() * 0.1)
    pks_full = peaks_poisson(cnt)
    env = envelope_boundary(centers, dens_full, pks_full) if pks_full.size >= 2 else None

    return {"mid": mid, "norm": norm, "ok": ok, "bins": bins, "centers": centers,
           "global_threshold": env["loc"] if env else None,
           "global_void": env["void"] if env else None, "session_bounds": b,
           "label": "ok" if env else "no_threshold"}


def build_frames(ev, n_frames):
    mid, norm, ok = ev["mid"], ev["norm"], ev["ok"]
    b = ev["session_bounds"]
    t_lo, t_hi = b["start_ns"], b["end_ns"]
    frame_times = np.linspace(t_lo, t_hi, n_frames)
    win_ns = (t_hi - t_lo) / n_frames * 1.5
    frames = []
    for ft in frame_times:
        m = ok & np.isfinite(norm) & (np.abs(mid - ft) < win_ns)
        nv = norm[m]
        if nv.size < 10:
            frames.append({"t": ft, "centers": ev["centers"], "dens": np.zeros_like(ev["centers"]),
                          "n": int(nv.size)})
            continue
        cnt, _ = np.histogram(nv, bins=ev["bins"])
        dens = cnt / (cnt.sum() * 0.1) if cnt.sum() else np.zeros_like(cnt, dtype=float)
        frames.append({"t": ft, "centers": ev["centers"], "dens": dens, "n": int(nv.size)})
    return frames


def _frame_label(ns):
    return pd.Timestamp(int(ns), unit="ns", tz="UTC").tz_convert("America/New_York") \
        .strftime("%H:%M:%S")


def make_single_kernel_animation(ev, k_min, ticker, date, note, chash):
    frames_data = build_frames(ev, N_FRAMES)
    go_frames = []
    for i, fr in enumerate(frames_data):
        ann = dict(text=f"t={_frame_label(fr['t'])}  n={fr['n']}", xref="paper", yref="paper",
                  x=0.02, y=0.95, showarrow=False, font=dict(size=13, color=C.INK))
        go_frames.append(go.Frame(
            data=[go.Bar(x=fr["centers"], y=fr["dens"], marker_color=C.ARM_A)],
            name=str(i), layout=go.Layout(annotations=[ann])))
    fig = go.Figure(
        data=[go.Bar(x=frames_data[0]["centers"], y=frames_data[0]["dens"],
                     marker_color=C.ARM_A, name="local density")],
        frames=go_frames)
    if ev["global_threshold"] is not None:
        fig.add_vline(x=ev["global_threshold"], line=dict(color=C.INK2, width=2, dash="dash"),
                     annotation_text=f"chosen threshold (void={ev['global_void']:.3f})")
    fig.update_layout(
        updatemenus=[dict(type="buttons", showactive=False, y=1.12, x=0.0,
                          buttons=[dict(label="Play", method="animate",
                                       args=[None, {"frame": {"duration": 400, "redraw": True},
                                                    "fromcurrent": True}]),
                                  dict(label="Pause", method="animate",
                                       args=[[None], {"frame": {"duration": 0, "redraw": False},
                                                     "mode": "immediate"}])])],
        sliders=[dict(steps=[dict(method="animate", args=[[str(i)],
                                  {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                             label="") for i in range(len(frames_data))])])
    fig.update_xaxes(title_text="normalized log10 interval")
    fig.update_yaxes(title_text="local density", range=[0, max(fr["dens"].max()
                     for fr in frames_data) * 1.1 + 0.01])
    cap = C.caption(f"{ticker} {date} ({note})", f"kernel={k_min:g} min, {N_FRAMES} frames, "
                    "each a real recomputation over its own time window", chash)
    fig = C.finish(fig, f"T6 -- {ticker} {date}: evolving local histogram, kernel={k_min:g}min",
                  note, cap, height=620, width=1000)
    return fig


def make_combined_animation(evs_by_kernel, ticker, date, note, chash):
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"kernel={k:g} min" for k in KERNELS])
    frames_by_kernel = {k: build_frames(evs_by_kernel[k], N_FRAMES) for k in KERNELS}
    for ci, k in enumerate(KERNELS, 1):
        fr0 = frames_by_kernel[k][0]
        fig.add_trace(go.Bar(x=fr0["centers"], y=fr0["dens"], marker_color=C.ARM_A,
                             showlegend=False), row=1, col=ci)
        if evs_by_kernel[k]["global_threshold"] is not None:
            fig.add_vline(x=evs_by_kernel[k]["global_threshold"],
                         line=dict(color=C.INK2, width=2, dash="dash"), row=1, col=ci)
    frames = []
    for i in range(N_FRAMES):
        t_label = _frame_label(frames_by_kernel[KERNELS[0]][i]["t"])
        data = []
        for k in KERNELS:
            fr = frames_by_kernel[k][i]
            data.append(go.Bar(x=fr["centers"], y=fr["dens"], marker_color=C.ARM_A))
        frames.append(go.Frame(data=data, name=str(i), traces=[0, 1, 2],
                               layout=go.Layout(annotations=[dict(
                                   text=f"t={t_label}", xref="paper", yref="paper",
                                   x=0.02, y=1.08, showarrow=False,
                                   font=dict(size=13, color=C.INK))])))
    fig.frames = frames
    fig.update_layout(
        updatemenus=[dict(type="buttons", showactive=False, y=1.15, x=0.0,
                          buttons=[dict(label="Play", method="animate",
                                       args=[None, {"frame": {"duration": 400, "redraw": True},
                                                    "fromcurrent": True}]),
                                  dict(label="Pause", method="animate",
                                       args=[[None], {"frame": {"duration": 0, "redraw": False},
                                                     "mode": "immediate"}])])],
        sliders=[dict(steps=[dict(method="animate", args=[[str(i)],
                                  {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                             label="") for i in range(N_FRAMES)])])
    fig.update_yaxes(title_text="local density", row=1, col=1)
    cap = C.caption(f"{ticker} {date} ({note})", f"all 3 kernels, {N_FRAMES} frames, synced time axis",
                    chash)
    fig = C.finish(fig, f"T6 -- {ticker} {date}: evolving local histogram, all kernels",
                  "Combined comparative view -- candidate B for T6c", cap, height=620, width=1560)
    return fig


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    F = float(c10c.class_m(cfg)["D4_median_precision_factor"])
    man = []
    for ticker, date, note in SAMPLE_EVENTS:
        row = dev[(dev.ticker == ticker) & (dev.event_date_canonical == date)]
        mom = row.iloc[0].momentum_pct
        evs_by_kernel = {k: compute_event(cfg, ticker, date, mom, k, F) for k in KERNELS}

        for k in KERNELS:
            fig = make_single_kernel_animation(evs_by_kernel[k], k, ticker, date, note, chash)
            name = f"s1_06_t6_{ticker}_{date}_k{int(k)}"
            man.append(C.write(fig, OUT, name))

        fig_c = make_combined_animation(evs_by_kernel, ticker, date, note, chash)
        name_c = f"s1_06_t6_{ticker}_{date}_combined"
        man.append(C.write(fig_c, OUT, name_c))
        print(f"  done: {ticker} {date}")

    c10c.write_json(rel(f"{ART}/s1_t6_chart_manifest.json"), {
        "charts": man, "config_hash": chash,
        "layout_choice_needed": ("T6c: both layouts built on 4 sample events (one per kernel "
                                 "separately, AND a combined 3-panel comparative view). Cooper "
                                 "picks which layout T6d produces for the full 56-event dev "
                                 "sample -- not an agent decision."),
        "sample_events": SAMPLE_EVENTS,
    })
    print(f"\n{len(man)} charts; kaleido {sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
