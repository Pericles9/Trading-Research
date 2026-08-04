"""
Phase 10 T6a -- charts 01-06, per the prompt's chart contract.

01 burst count           02 burst duration        03 burst spacing
04 burst move share      05 arm agreement         06 burst-relative concentration

Every chart: distribution not just centre, n annotated, outliers shown never
clipped, log axes where multiplicative, no smoothing, captioned with sample /
filters / config hash, kaleido-verified PNG sibling.

Usage: python research/phase_10/t6a_charts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chartlib as C  # noqa: E402
from common import config_hash, load_config, rel, write_json  # noqa: E402

KEY = ["ticker", "event_date_canonical", "momentum_pct"]
POOLED = ["dev_v4_primary", "activity_extension"]
POPS = [("pooled_analysis_cohort", POOLED), ("row_cap_census", ["row_cap_census"]),
        ("dev_v4_sidecar", ["dev_v4_sidecar"])]
ARM_NAME = {"A": "Arm A — Kleinberg 2-state", "B": "Arm B — threshold + hysteresis"}


def pop_color(pop: str, arm: str) -> str:
    return C.POP_COLOR[pop] or C.ARM_COLOR[arm]


# ------------------------------------------------------------------ 01
def chart_01(ev, chash, out):
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                        subplot_titles=[ARM_NAME["A"], ARM_NAME["B"]],
                        horizontal_spacing=0.07)
    for ci, arm in enumerate(("A", "B"), 1):
        e = ev[ev["arm"] == arm]
        for pi, (pop, groups) in enumerate(POPS):
            sub = e[e["cohort_group"].isin(groups)]
            if not len(sub):
                continue
            col = pop_color(pop, arm)
            v = sub["n_bursts"].to_numpy(dtype=float)
            fig.add_trace(go.Box(
                x=np.maximum(v, 0.5), y=[pi] * len(v), orientation="h",
                name=f"{C.POP_LABEL[pop]} (n={len(v)})",
                marker=dict(color=col, size=6, opacity=0.75,
                            line=dict(color=C.SURFACE, width=1)),
                line=dict(color=col, width=2), fillcolor="rgba(0,0,0,0)",
                boxpoints="all", jitter=0.6, pointpos=0, width=0.55,
                legendgroup=pop, showlegend=(ci == 1),
                hovertemplate="%{x:,.0f} bursts<extra></extra>",
            ), row=1, col=ci)
            fig.add_annotation(
                x=np.log10(max(v.max(), 1)), y=pi + 0.36, xref=f"x{ci if ci>1 else ''}",
                yref=f"y{ci if ci>1 else ''}", xanchor="right", showarrow=False,
                text=f"n={len(v)}  median={np.median(v):,.0f}",
                font=dict(size=10.5, color=C.INK2),
            )
        fig.update_xaxes(type="log", title_text="bursts per event (log)", row=1, col=ci)
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(POPS))),
                     ticktext=["analysis<br>cohort", "row_cap<br>census", "dev_v4<br>sidecar"],
                     row=1, col=1)
    C.finish(
        fig, "01 — How many bursts does a session contain?",
        "Per-event burst count at each arm's reference parameter point. Log x. "
        "Every event plotted; carried populations are separate series and are never pooled.",
        C.caption("114 cohort events (100 pooled analysis + 8 row-cap census + 6 sidecar)",
                  "T=0 extended-day window only; reference parameter point per arm",
                  chash,
                  "<b>Reads:</b> all mass at 1 would be failure row 1; a single spike at one value "
                  "would be failure row 4."),
        height=760)
    return C.write(fig, out, "01_burst_count")


# ------------------------------------------------------------------ 02
def chart_02(bs, cfg, chash, out):
    floor = cfg["arm_b"]["min_dwell_seconds"]
    fig = go.Figure()
    for arm in ("A", "B"):
        b = bs[(bs["arm"] == arm) & (bs["cohort_group"].isin(POOLED))]
        n_ev = b.groupby(KEY).ngroups
        fig.add_trace(C.ecdf_trace(
            b["duration_seconds"].clip(lower=1e-4),
            f"{ARM_NAME[arm]} — {n_ev} events", C.ARM_COLOR[arm]))
    C.vline(fig, floor, f"Arm B minimum dwell = {floor:.0f}s")
    fig.update_xaxes(type="log", title_text="burst duration (seconds, log)")
    fig.update_yaxes(title_text="cumulative share of bursts", range=[0, 1.02])
    C.finish(
        fig, "02 — How long does a burst last?",
        "ECDF of burst duration, pooled analysis cohort. Log x. No binning and no smoothing, "
        "so every burst including the extremes is on the curve.",
        C.caption("pooled analysis cohort, n=100 events "
                  "(Arm A 22,438 bursts / Arm B 2,408 bursts)",
                  "T=0 only; reference parameter point per arm; row-cap census and sidecar excluded",
                  chash,
                  "<b>Reads:</b> mass piled against the dwell rule would be failure row 2. "
                  "Durations below 1e-4 s are drawn at 1e-4 so a log axis can show them; none are dropped."))
    return C.write(fig, out, "02_burst_duration")


# ------------------------------------------------------------------ 03
def chart_03(bs, ev, cfg, chash, out):
    merge = cfg["arm_b"]["merge_gap_seconds"]
    fig = go.Figure()
    caps = []
    for arm in ("A", "B"):
        b = bs[(bs["arm"] == arm) & (bs["cohort_group"].isin(POOLED))]
        sp = b["spacing_seconds"].dropna()
        e = ev[(ev["arm"] == arm) & (ev["cohort_group"].isin(POOLED))]
        n_single = int((e["n_bursts"] == 1).sum())
        n_zero = int((e["n_bursts"] == 0).sum())
        caps.append(f"{ARM_NAME[arm]}: {n_single} single-burst events, {n_zero} zero-burst "
                    f"events — these contribute no spacing value and are counted here, not dropped")
        fig.add_trace(C.ecdf_trace(sp.clip(lower=1e-4), ARM_NAME[arm], C.ARM_COLOR[arm]))
    C.vline(fig, merge, f"Arm B merge-gap tolerance = {merge:.0f}s")
    fig.update_xaxes(type="log", title_text="gap between consecutive bursts (seconds, log)")
    fig.update_yaxes(title_text="cumulative share of gaps", range=[0, 1.02])
    C.finish(
        fig, "03 — How far apart are consecutive bursts?",
        "ECDF of inter-burst spacing (end of one burst to start of the next), pooled analysis "
        "cohort. Log x.",
        C.caption("pooled analysis cohort, n=100 events", "T=0 only; reference parameter point per arm",
                  chash, "<br>".join(caps) +
                  "<br><b>Reads:</b> a spacing distribution indistinguishable from the merge-gap "
                  "tolerance would mean the parameter is generating the answer."))
    return C.write(fig, out, "03_burst_spacing")


# ------------------------------------------------------------------ 04
def chart_04(bs, chash, out):
    fig = make_subplots(
        rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.10,
        subplot_titles=["All bursts — ECDF of share of session move",
                        "Ordered by |move|: 1st, 2nd, 3rd largest burst"])
    n_undef = {}
    for arm in ("A", "B"):
        b = bs[(bs["arm"] == arm) & (bs["cohort_group"].isin(POOLED))]
        n_undef[arm] = int(b["move_share"].isna().sum())
        fig.add_trace(C.ecdf_trace(b["move_share"], ARM_NAME[arm], C.ARM_COLOR[arm]),
                      row=1, col=1)
        ranked = (b.assign(absr=b["burst_move"].abs())
                    .sort_values("absr", ascending=False).groupby(KEY).head(3).copy())
        ranked["rank"] = ranked.groupby(KEY).cumcount() + 1
        for rk in (1, 2, 3):
            v = ranked.loc[ranked["rank"] == rk, "move_share"].to_numpy(dtype=float)
            v = v[np.isfinite(v)]
            if not v.size:
                continue
            fig.add_trace(go.Box(
                y=v, x=[f"{rk}" if arm == "A" else f"{rk} "] * v.size,
                name=f"{ARM_NAME[arm]} rank {rk} (n={v.size})",
                marker=dict(color=C.ARM_COLOR[arm], size=5, opacity=0.6,
                            line=dict(color=C.SURFACE, width=1)),
                line=dict(color=C.ARM_COLOR[arm], width=2), fillcolor="rgba(0,0,0,0)",
                boxpoints="all", jitter=0.5, pointpos=0, width=0.4,
                legendgroup=f"{arm}rank", showlegend=False,
                offsetgroup=arm, alignmentgroup=str(rk),
                hovertemplate=f"Arm {arm} rank {rk}<br>share %{{y:.3f}}<extra></extra>",
            ), row=1, col=2)
    fig.add_hline(y=0, line=dict(color=C.GRID, width=1), row=1, col=2)
    fig.add_vline(x=0, line=dict(color=C.GRID, width=1), row=1, col=1)
    fig.update_xaxes(title_text="burst share of session move (signed)", row=1, col=1)
    fig.update_yaxes(title_text="cumulative share of bursts", range=[0, 1.02], row=1, col=1)
    fig.update_xaxes(title_text="burst rank within event (Arm A left / Arm B right)", row=1, col=2)
    fig.update_yaxes(title_text="share of session move (signed)", row=1, col=2)
    C.finish(
        fig, "04 — How much of the session move does a burst carry?",
        "Session move = last in-window T=0 print price minus first in-window T=0 print price, "
        "tick-derived. Shares are signed and unclipped: >1 or <0 is a real feature of a session "
        "that overshoots and retraces.",
        C.caption("pooled analysis cohort, n=100 events",
                  "T=0 only; reference parameter point per arm; row-cap census and sidecar excluded",
                  chash,
                  f"<b>Undefined denominator:</b> Arm A {n_undef['A']} bursts, Arm B {n_undef['B']} "
                  "bursts (session move exactly 0). Carried as undefined, never imputed."
                  "<br><b>Reads:</b> uniformly small shares would contradict the premise this "
                  "phase is built on."))
    return C.write(fig, out, "04_burst_move_share")


# ------------------------------------------------------------------ 05
def chart_05(pairs, chash, out):
    cross = pairs[pairs["comparison"] == "cross_arm"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.45, 0.55], horizontal_spacing=0.11,
                        subplot_titles=["Per-event interval Jaccard, Arm A vs Arm B",
                                        "Burst count: Arm A vs Arm B (identity line)"])
    fig.add_trace(C.ecdf_trace(cross["jaccard"], "Arm A vs Arm B", C.ARM_COLOR["B"]),
                  row=1, col=1)
    med = float(cross["jaccard"].median())
    fig.add_vline(x=med, line=dict(color=C.INK2, width=1.5, dash="dot"),
                  annotation_text=f"median {med:.3f}", annotation_position="top",
                  annotation_font=dict(size=10.5, color=C.INK2), row=1, col=1)
    a = cross["n_bursts_ref"].to_numpy(dtype=float)
    b = cross["n_bursts_cell"].to_numpy(dtype=float)
    lim = [0.5, max(a.max(), b.max()) * 1.4]
    fig.add_trace(go.Scatter(
        x=lim, y=lim, mode="lines", line=dict(color=C.GRID, width=1.5, dash="dash"),
        name="identity", showlegend=True, hoverinfo="skip"), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=np.maximum(a, 0.5), y=np.maximum(b, 0.5), mode="markers",
        name=f"events (n={len(cross)})",
        marker=dict(color=C.ARM_COLOR["A"], size=9, opacity=0.7,
                    line=dict(color=C.SURFACE, width=1.5)),
        customdata=cross[KEY + ["jaccard"]].to_numpy(),
        hovertemplate="%{customdata[0]} %{customdata[1]}<br>Arm A %{x:,.0f} bursts"
                      "<br>Arm B %{y:,.0f} bursts<br>Jaccard %{customdata[3]:.3f}<extra></extra>",
    ), row=1, col=2)
    fig.update_xaxes(title_text="interval Jaccard (seconds ∩ / seconds ∪)", range=[0, 1], row=1, col=1)
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1.02], row=1, col=1)
    fig.update_xaxes(type="log", title_text="Arm A burst count (log)", range=np.log10(lim), row=1, col=2)
    fig.update_yaxes(type="log", title_text="Arm B burst count (log)", range=np.log10(lim), row=1, col=2)
    C.finish(
        fig, "05 — Where do the two arms agree?",
        "Interval Jaccard on the union of each arm's burst intervals: seconds in the intersection "
        "over seconds in the union. Same measure as the T5a perturbation test.",
        C.caption(f"pooled analysis cohort, n={len(cross)} events",
                  "T=0 only; both arms at their reference parameter point", chash,
                  "<b>Reads:</b> an overlap distribution centred near zero would mean the two arms "
                  "are measuring different things and neither is established."))
    return C.write(fig, out, "05_arm_agreement")


# ------------------------------------------------------------------ 06
def chart_06(t4, bs, chash, out):
    fig = make_subplots(
        rows=1, cols=2, column_widths=[0.58, 0.42], horizontal_spacing=0.10,
        subplot_titles=["Cumulative share of burst move and volume, from burst start",
                        "Time from burst start to that burst's own high"])
    for arm in ("A", "B"):
        cur = pd.DataFrame(t4["arms"][arm]["concentration_curve_pooled"])
        cur = cur[cur["t_seconds"] > 0]
        col = C.ARM_COLOR[arm]
        rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
        band = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.13)"
        fig.add_trace(go.Scatter(
            x=list(cur["t_seconds"]) + list(cur["t_seconds"])[::-1],
            y=list(cur["move_share_p75"]) + list(cur["move_share_p25"])[::-1],
            fill="toself", fillcolor=band, line=dict(width=0), showlegend=False,
            hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=cur["t_seconds"], y=cur["move_share_p50"], mode="lines+markers",
            name=f"{ARM_NAME[arm]} — move (median, IQR band)",
            line=dict(color=col, width=2.5), marker=dict(size=7),
            customdata=cur[["n_bursts", "n_bursts_still_open"]].to_numpy(),
            hovertemplate="t=%{x:,.0f}s<br>median move share %{y:.3f}"
                          "<br>n bursts %{customdata[0]:,} (%{customdata[1]:,} still open)<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=cur["t_seconds"], y=cur["volume_share_p50"], mode="lines",
            name=f"{ARM_NAME[arm]} — volume (median)",
            line=dict(color=col, width=2, dash="dot"),
            customdata=cur[["n_bursts"]].to_numpy(),
            hovertemplate="t=%{x:,.0f}s<br>median volume share %{y:.3f}"
                          "<br>n bursts %{customdata[0]:,}<extra></extra>",
        ), row=1, col=1)
        b = bs[(bs["arm"] == arm) & (bs["cohort_group"].isin(POOLED))]
        fig.add_trace(C.ecdf_trace(b["seconds_to_burst_high"].clip(lower=1e-4),
                                   ARM_NAME[arm], col), row=1, col=2)

    tail = pd.DataFrame(t4["arms"]["A"]["concentration_curve_pooled"])
    tail = tail[tail["t_seconds"] > 0]
    fig.update_xaxes(type="log", title_text="seconds since burst start (log)", row=1, col=1)
    fig.update_yaxes(title_text="cumulative share of that burst's total", range=[-0.05, 1.05], row=1, col=1)
    fig.update_xaxes(type="log", title_text="seconds from burst start to burst high (log)", row=1, col=2)
    fig.update_yaxes(title_text="cumulative share of bursts", range=[0, 1.02], row=1, col=2)
    C.finish(
        fig, "06 — How fast is a burst spent, measured from burst start?",
        "Burst-relative, not session-anchored: t=0 is the moment each arm first calls the burst. "
        "Solid = move, dotted = volume, band = IQR across bursts. Bursts shorter than t contribute "
        "their terminal value.",
        C.caption("pooled analysis cohort, n=100 events (Arm A 22,438 bursts / Arm B 2,408 bursts)",
                  "T=0 only; reference parameter point per arm; row-cap census and sidecar excluded",
                  chash,
                  "n bursts and n still-open per grid point are on every hover. "
                  "<br><b>Reads:</b> curves hugging the diagonal would mean no concentration within "
                  "bursts, so burst-relative anchoring would buy nothing over session anchoring."))
    return C.write(fig, out, "06_burst_relative_concentration")


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out = rel(cfg["paths"]["out_charts"])

    bs = pd.read_parquet(os.path.join(art, "t4_burst_measurements.parquet"))
    ev = pd.read_parquet(os.path.join(art, "t4_event_measurements.parquet"))
    pairs = pd.read_parquet(os.path.join(art, "t5_overlap_pairs.parquet"))
    with open(os.path.join(art, "t4_burst_measurements.json"), encoding="utf-8") as f:
        t4 = json.load(f)

    print("charts 01-06:")
    manifest = [
        chart_01(ev, chash, out),
        chart_02(bs, cfg, chash, out),
        chart_03(bs, ev, cfg, chash, out),
        chart_04(bs, chash, out),
        chart_05(pairs, chash, out),
        chart_06(t4, bs, chash, out),
    ]
    n_ok = sum(m["kaleido_verified"] for m in manifest)
    write_json(os.path.join(art, "t6a_chart_manifest.json"), {
        "phase": "10", "task": "T6a", "config_hash": chash,
        "n_charts": len(manifest), "n_kaleido_verified": n_ok,
        "all_verified": n_ok == len(manifest),
        "palette": {
            "arm_a": C.ARM_A, "arm_b": C.ARM_B,
            "row_cap_census": C.ROWCAP, "dev_v4_sidecar": C.SIDECAR,
            "validation": "data-viz validator, light mode, --pairs all: lightness band PASS, "
                          "chroma floor PASS, CVD separation PASS (worst all-pairs ΔE 9.2 deutan), "
                          "normal-vision floor PASS (worst ΔE 16.3). Aqua carries a sub-3:1 "
                          "contrast WARN; relief is the mandatory per-series n label.",
        },
        "charts": manifest,
        "source": "research/phase_10/t6a_charts.py:main",
    })
    print(f"kaleido-verified {n_ok}/{len(manifest)}")
    return 0 if n_ok == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
