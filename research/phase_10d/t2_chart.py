"""
Phase 10d T2h -- chart 01, the control gate.

01  Does the reference cell reproduce 10c, and do all four axes move things the right way?
    Four panels, one per gated question:
      a  C1 identity     -- committed runs vs replayed objects, per replay cell (y=x line)
      b  C3 depth        -- separators admitted vs d, against the known construction
      c  C2 monotonicity -- violation counts across every monotone check (must be zero)
      d  C5 floor        -- objects deleted at each min_prints, showing 2 is inert

No real event is read: panel (a) reads the COMMITTED 10c sub-burst artifact, not ticks.

Usage: .venv/Scripts/python.exe research/phase_10d/t2_chart.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
import chartlib as C  # noqa: E402

CTRL = os.path.join(ROOT, "results", "phase_10d", "controls")
OUT = os.path.join(ROOT, "results", "phase_10d", "charts")


def load(name):
    with open(os.path.join(CTRL, name), encoding="utf-8") as f:
        return json.load(f)


def cfg_hash():
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        d = json.load(f)
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8]


def main() -> int:
    c1, c2, c3, c5 = load("c1_identity.json"), load("c2_monotonicity.json"), \
        load("c3_depth_direction.json"), load("c5_floor_noop.json")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "C1 — identity: committed 10c runs vs replayed objects",
            "C3 — depth direction: separators admitted as d rises",
            "C2 — monotonicity: violations across every gated check",
            "C5 — floor: objects deleted at each min_prints",
        ],
        vertical_spacing=0.155, horizontal_spacing=0.11)

    # ---- (a) C1
    x = [r["n_runs_committed"] for r in c1["replay_cells"]]
    y = [r["n_objects_replayed"] for r in c1["replay_cells"]]
    lab = [f"{r['ticker']} {r['event_date_canonical']} k={r['kernel_min']:g}m"
           for r in c1["replay_cells"]]
    lo, hi = min(x + y) * 0.7, max(x + y) * 1.4
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="y = x (exact)",
                             line=dict(color=C.GRID, width=2, dash="dash"),
                             hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers", name=f"replay cells (n={len(x)})",
        marker=dict(color=C.ARM_A, size=11, line=dict(color=C.INK, width=1)),
        text=lab, hovertemplate="%{text}<br>committed %{x}<br>replayed %{y}<extra></extra>"),
        row=1, col=1)
    fig.update_xaxes(type="log", title_text="sub-bursts in the committed 10c cell",
                     range=[np.log10(lo), np.log10(hi)], row=1, col=1)
    fig.update_yaxes(type="log", title_text="objects at every degenerate cell",
                     range=[np.log10(lo), np.log10(hi)], row=1, col=1)

    # ---- (b) C3
    ds = [r["d_decades"] for r in c3["rows"]]
    fig.add_trace(go.Bar(x=ds, y=[r["separators_admitted"] for r in c3["rows"]],
                         name="admitted", marker_color=C.ARM_B, width=0.16,
                         hovertemplate="d=%{x} dec<br>admitted %{y}<extra></extra>"),
                  row=1, col=2)
    fig.add_trace(go.Scatter(x=ds, y=[r["expected_admitted"] for r in c3["rows"]],
                             mode="markers", name="expected by construction",
                             marker=dict(color=C.INK, size=13, symbol="x-thin",
                                         line=dict(color=C.INK, width=2.5)),
                             hovertemplate="d=%{x} dec<br>expected %{y}<extra></extra>"),
                  row=1, col=2)
    fig.update_xaxes(title_text="d (decades added to threshold)", row=1, col=2)
    fig.update_yaxes(title_text=f"separators admitted (of {len(c3['separator_depths_above_threshold_decades'])})",
                     row=1, col=2)

    # ---- (c) C2
    ks = list(c2["violations"].keys())
    fig.add_trace(go.Bar(x=[c2["violations"][k] for k in ks], y=ks, orientation="h",
                         name=f"violations (checks n={c2['monotone_checks']:,})",
                         marker_color=C.SIDECAR,
                         hovertemplate="%{y}<br>violations %{x}<extra></extra>"),
                  row=2, col=1)
    fig.update_xaxes(title_text="violations (gate requires 0)", range=[0, 1], row=2, col=1)
    fig.update_yaxes(tickfont=dict(size=10), row=2, col=1)

    # ---- (d) C5
    mp = [2, 3, 5]
    dele = [c5["deleted_at_min_prints_2"], c5["deleted_at_min_prints_3"],
            c5["deleted_at_min_prints_5"]]
    tot = c5["objects_before_floor"]
    fig.add_trace(go.Bar(x=[str(m) for m in mp], y=dele, name=f"deleted (of {tot:,})",
                         marker_color=[C.ARM_A, C.ARM_B, C.ROWCAP], width=0.5,
                         text=[f"{v:,}<br>{v/tot:.1%}" for v in dele],
                         textposition="outside",
                         hovertemplate="min_prints=%{x}<br>deleted %{y:,}<extra></extra>"),
                  row=2, col=2)
    fig.update_xaxes(title_text="min_prints", row=2, col=2)
    fig.update_yaxes(title_text=f"objects deleted (of {tot:,} synthetic)",
                     range=[0, max(dele) * 1.28], row=2, col=2)

    cap = C.caption(
        sample=("C1: 8 committed 10c (event, kernel) cells spanning the run-count range,<br>"
                "replayed from results/phase_10c/artifacts/s1_t1_subbursts.parquet, plus 50 "
                "synthetic sequences.<br>C2/C4/C5: 200 synthetic sequences each. C3: one "
                "sequence with separators at known depths 0.1/0.3/0.6/0.9 decades."),
        filters=("No real event is read anywhere in T2 — the C1 replay reads emitted "
                 "objects from a committed artifact, not ticks."),
        chash=cfg_hash(),
        extra=("<b>Gate:</b> C1 identity PASS · C2 monotonicity PASS · C3 depth direction "
               "PASS · C4 separator equivalence PASS (12,000 comparisons, 0 differences) · "
               "C5 floor no-op PASS. All five are hard gates.<br>"
               "<b>C2 note:</b> gated on count, TOTAL and MAX duration. Median object "
               "duration is not monotone under merging and is reported un-gated — "
               "[1s,1s,100s,100s] has median 50.5s; merging the two 100s gives "
               "[1s,1s,200s], median 1s."))

    C.finish(fig, "Chart 01 — Control gate: assembly under merge tolerance, separator rule and floor",
             "Phase 10d T2 · every axis validated on constructed data before any real event is read",
             cap, height=940, width=1340)
    fig.update_layout(showlegend=True)
    os.makedirs(OUT, exist_ok=True)
    meta = C.write(fig, OUT, "01_control_assembly")
    with open(os.path.join(ROOT, "results", "phase_10d", "artifacts",
                           "t2_chart_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T2h", "charts": [meta]}, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
