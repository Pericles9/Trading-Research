"""
R0-T0c charts: the distributions behind the re-slice.

03 -- ECDF of the pre-cost markout, in bp, per slice. An ECDF is the right encoding for
      "does the median flip": the median is where a curve crosses y = 0.5, so the crossing
      relative to the x = 0 line IS the answer, read off the whole distribution rather than
      from a summary. No observation is dropped or clipped -- every row is in its curve and
      the curves run flat past the +/-3,000 bp view window, which exists for legibility only.
04 -- the same for the cost-adjusted markout (markout - rt_cost).

Five series, the CAT5 ceiling. S7 (the PF population itself) is in the artifact table and
in the report but not on the chart -- a sixth colour would break the validated palette, and
S7 sits between S3 and S5 on both panels.

Usage: .venv/Scripts/python.exe research/relative_momentum/chart_t0c.py
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

SLICED = f"{C.ART}/t0c_named_cell_sliced.parquet"


def series(cell: pd.DataFrame) -> list:
    d1 = cell[cell["momentum_pct"].notna()]
    return [
        ("S0 · named cell, as published", cell, K.INK2),
        ("S2 · mom < 50, before 2023-11-17", d1[~d1["mom_ge_50"] & ~d1["date_ge_boundary"]], K.BLUE),
        ("S3 · mom ≥ 50, before 2023-11-17", d1[d1["mom_ge_50"] & ~d1["date_ge_boundary"]], K.ORANGE),
        ("S4 · mom < 50, on/after 2023-11-17", d1[~d1["mom_ge_50"] & d1["date_ge_boundary"]], K.AQUA),
        ("S5 · mom ≥ 50, on/after — gate-admissible", d1[d1["mom_ge_50"] & d1["date_ge_boundary"]], K.VIOLET),
    ]


def ecdf_chart(cell: pd.DataFrame, col: str, title: str, cap_extra: str, fname: str) -> str:
    fig = go.Figure()
    for label, sub, color in series(cell):
        v = sub[col].to_numpy(dtype=float) * 1e4
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        v = np.sort(v)
        y = np.arange(1, v.size + 1) / v.size
        med = float(np.quantile(v, 0.5))
        fig.add_trace(go.Scatter(
            x=v, y=y, mode="lines", name=f"{label} (n={v.size:,}, median {med:+,.0f} bp)",
            line=dict(color=color, width=2),
            hovertemplate=label + "<br>%{x:,.0f} bp<br>F = %{y:.3f}<extra></extra>"))
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color=K.INK2)
    fig.update_xaxes(title_text=f"{col} (basis points, linear; view window ±3,000 bp)",
                     type="linear", range=[-3000, 3000])
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1])
    cap = K.caption(
        sample="Phase 11 T7 named cell (det_segment = rth, latency 5 min, hold 30 min), "
               "n = 10,544, re-sliced — no new data pass",
        filters="none — every row of the named cell is in S0, and S2–S5 partition its D1 rows "
                "exactly. The x range shows ±3,000 bp for legibility; no observation is "
                "dropped or clipped, the curves simply run flat beyond it.",
        extra=cap_extra)
    K.base_layout(fig, title, cap, height=700, cap_y=-0.22, margin_b=250)
    return K.write(fig, fname)


def main() -> int:
    cell = pd.read_parquet(os.path.join(C.REPO, SLICED))
    cell["net"] = cell["markout"] - cell["rt_cost"]
    out = [
        ecdf_chart(cell, "markout",
                   "T0c · pre-cost markout by slice — where each curve crosses the dotted "
                   "line is its median",
                   "The median flips positive only where the momentum floor is applied "
                   "(S3, S5). The date boundary alone (S4) does not flip it. momentum_pct "
                   "is a prior-close-to-day's-high measure and is not known at decision "
                   "time — see REPORT §T0c.",
                   "03_markout_ecdf_by_slice.html"),
        ecdf_chart(cell, "net",
                   "T0c · cost-adjusted markout by slice (markout − round-trip cost)",
                   "Round-trip cost is Phase 11's own per-row rt_cost, not a scalar. Its "
                   "median rises from 70.98 bp on the full cell to 106.30 bp on S5 and "
                   "112.57 bp on the PF population.",
                   "04_net_markout_ecdf_by_slice.html"),
    ]
    C.write_json(f"{C.ART}/t0c_charts.json", {
        "task": "R0-T0c charts", "config_hash": C.cfg_hash(),
        "charts": out, "source_artifacts": [SLICED],
    })
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
