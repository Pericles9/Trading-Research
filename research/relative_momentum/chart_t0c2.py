"""
R0-T0c2 charts.

05 -- the response curve. Forward markout and cost-adjusted markout against equal-population
      deciles of move_at_entry, the causal measure. Median with the interquartile band drawn
      around it, n on every bucket, and the round-trip cost on the same axis so the gap
      between gross and net is visible rather than asserted. This is the primary object: no
      threshold is set anywhere on it.
06 -- ECDF of forward markout by causal slice, built to be read directly against chart 03,
      which is the same encoding on the lookahead variable. The pair is the finding.

Usage: .venv/Scripts/python.exe research/relative_momentum/chart_t0c2.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import chart_common as K  # noqa: E402
from research.relative_momentum import common as C  # noqa: E402

CELL = f"{C.ART}/t0c2_named_cell_move_at.parquet"
LEVEL = 0.50
GATE_DATE = "2023-11-17"


def chart_05(m: pd.DataFrame) -> str:
    m = m[m["move_at_entry"].notna()].copy()
    m["net"] = m["markout"] - m["rt_cost"]
    m["dec"] = pd.qcut(m["move_at_entry"], 10, labels=False, duplicates="drop")

    g = m.groupby("dec")
    x = g["move_at_entry"].median().to_numpy() * 100
    n = g.size().to_numpy()
    fig = go.Figure()
    for col, color, name in [("markout", K.BLUE, "forward markout (gross)"),
                             ("net", K.ORANGE, "cost-adjusted markout (net)")]:
        p25 = g[col].quantile(.25).to_numpy() * 1e4
        p50 = g[col].quantile(.50).to_numpy() * 1e4
        p75 = g[col].quantile(.75).to_numpy() * 1e4
        fig.add_trace(go.Scatter(x=np.concatenate([x, x[::-1]]),
                                 y=np.concatenate([p75, p25[::-1]]),
                                 fill="toself", fillcolor=K.rgba(color, .13),
                                 line=dict(width=0), hoverinfo="skip",
                                 name=f"{name} — IQR", showlegend=True))
        fig.add_trace(go.Scatter(
            x=x, y=p50, mode="lines+markers+text", name=f"{name} — median",
            line=dict(color=color, width=2.5), marker=dict(size=7, color=color),
            text=[f"n={v:,}" for v in n], textposition="bottom center",
            textfont=dict(size=9, color=K.INK2),
            hovertemplate=name + "<br>move at entry %{x:.1f}%<br>median %{y:,.0f} bp"
                          "<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=x, y=g["rt_cost"].quantile(.50).to_numpy() * 1e4, mode="lines",
        name="median round-trip cost", line=dict(color=K.INK2, width=1.5, dash="dot"),
        hovertemplate="round-trip cost %{y:,.0f} bp<extra></extra>"))
    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.update_xaxes(title_text="move_at_entry — move already achieved at decision time "
                                "(%, decile median)")
    fig.update_yaxes(title_text="basis points")
    cap = K.caption(
        sample="Phase 11 T7 named cell (rth, latency 5 min, hold 30 min), n = 10,544, all of "
               "which have move_at_entry defined",
        filters="none — equal-population deciles, every row in exactly one bucket, nothing "
                "trimmed or clipped. Bands are the interquartile range, not a confidence "
                "interval.",
        extra="move_at_entry = (entry_price − tick-derived prior close) / prior close, "
              "evaluated at the named cell's own entry instant, so nothing after the decision "
              "enters it. NO THRESHOLD IS SET ON THIS CURVE.")
    K.base_layout(fig, "T0c2 · forward markout against the move already achieved at decision "
                       "time", cap, height=700, cap_y=-0.24, margin_b=240)
    return K.write(fig, "05_response_curve_move_at_entry.html")


def chart_06(cell: pd.DataFrame) -> str:
    m = cell[cell["move_at_entry"].notna()].copy()
    hi = m["move_at_entry"] >= LEVEL
    late = m["event_date"] >= GATE_DATE
    ser = [
        ("S0 · named cell, as published", cell, K.INK2),
        ("C2 · move < 50%, before 2023-11-17", m[~hi & ~late], K.BLUE),
        ("C3 · move ≥ 50%, before 2023-11-17", m[hi & ~late], K.ORANGE),
        ("C4 · move < 50%, on/after 2023-11-17", m[~hi & late], K.AQUA),
        ("C5 · move ≥ 50%, on/after — causal analogue of S5", m[hi & late], K.VIOLET),
    ]
    fig = go.Figure()
    for label, sub, color in ser:
        v = sub["markout"].to_numpy(dtype=float) * 1e4
        v = np.sort(v[np.isfinite(v)])
        if v.size == 0:
            continue
        fig.add_trace(go.Scatter(
            x=v, y=np.arange(1, v.size + 1) / v.size, mode="lines",
            name=f"{label} (n={v.size:,}, median {np.quantile(v, .5):+,.0f} bp)",
            line=dict(color=color, width=2),
            hovertemplate=label + "<br>%{x:,.0f} bp<br>F = %{y:.3f}<extra></extra>"))
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color=K.INK2)
    fig.update_xaxes(title_text="forward markout (basis points; view window ±3,000 bp)",
                     range=[-3000, 3000])
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1])
    cap = K.caption(
        sample="Phase 11 T7 named cell, n = 10,544, sliced on move_at_entry",
        filters="none — C2–C5 partition the cell exactly and nothing is dropped or clipped; "
                "the curves run flat past the view window. C3 and C5 are small (n = 214, 123) "
                "and are read as such.",
        extra="READ THIS AGAINST CHART 03, which is the same encoding on momentum_pct. There "
              "the median crossed to the right of zero on the gate-admissible slice; here, on "
              "the decision-time measure, it does not.")
    K.base_layout(fig, "T0c2 · the same slices on the causal measure — compare with chart 03",
                  cap, height=700, cap_y=-0.24, margin_b=240)
    return K.write(fig, "06_markout_ecdf_causal_slices.html")


def main() -> int:
    cell = pd.read_parquet(os.path.join(C.REPO, CELL))
    out = [chart_05(cell), chart_06(cell)]
    C.write_json(f"{C.ART}/t0c2_charts.json", {
        "task": "R0-T0c2 charts", "config_hash": C.cfg_hash(),
        "charts": out, "source_artifacts": [CELL]})
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
