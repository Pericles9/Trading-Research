"""Chart 06 - does the round trip cost more than the trade captures? THE GATE.

x = round_trip_cost / realized_capture (log), ECDF, one line per latency;
facet by detection segment; vertical rule at 1.0; 1x / 1.5x / 2x cost as three
line styles.

Failure appearance from the contract: ECDFs sitting entirely right of 1.0 at
every latency - cost exceeds capture everywhere on the RTH cell.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import chart_common as K
from common import CONFIG

A = "results/phase_11/artifacts"
LAT = [0, 1, 5, 15, 30]
SEGS = ["premarket", "rth", "post"]
MULT = [("ratio_1.0x", "1×", "solid"), ("ratio_1.5x", "1.5×", "dash"),
        ("ratio_2.0x", "2×", "dot")]
COL = {0: K.AQUA, 1: K.GREEN, 5: K.BLUE, 15: K.ORANGE, 30: K.VIOLET}


def main() -> None:
    d = pd.read_parquet(f"{A}/t7_cost_vs_capture.parquet")
    d = d[d.hold == 30]

    fig = make_subplots(rows=1, cols=3,
                        subplot_titles=[f"{s} · hold 30 min" for s in SEGS],
                        horizontal_spacing=0.06)
    seen = set()
    for ci, seg in enumerate(SEGS):
        sub = d[d.det_segment == seg]
        for lat in LAT:
            s0 = sub[sub.latency == lat]
            for col, lab, dash in MULT:
                s = s0[col].replace([np.inf, -np.inf], np.nan).dropna()
                s = s[s > 0].sort_values()
                if len(s) < 2:
                    continue
                y = np.arange(1, len(s) + 1) / len(s)
                key = (lat, lab)
                fig.add_trace(go.Scatter(
                    x=s.values, y=y, mode="lines",
                    name=f"lat {lat}m · {lab}" + (" (impossible)" if lat == 0 else ""),
                    legendgroup=f"{lat}{lab}",
                    showlegend=(ci == 1 and key not in seen),
                    line=dict(color=K.rgba(COL[lat], .9), width=2 if dash == "solid" else 1.5,
                              dash=dash),
                    hovertemplate=(f"lat {lat}m {lab}<br>ratio %{{x:.4f}}"
                                   f"<br>ECDF %{{y:.4f}}<br>n={len(s):,}<extra></extra>"),
                ), row=1, col=ci + 1)
                if ci == 1:
                    seen.add(key)
        n1 = int(sub[sub.latency == 5]["ratio_1.0x"].notna().sum())
        fig.add_annotation(x=0.02, y=0.02,
                           xref=("x domain" if ci == 0 else f"x{ci+1} domain"),
                           yref=("y domain" if ci == 0 else f"y{ci+1} domain"),
                           xanchor="left", showarrow=False, font=dict(size=9, color=K.INK2),
                           bgcolor="rgba(255,255,255,.8)",
                           text=f"n at lat 5m, 1× = {n1:,}")
        # Shapes on a log axis take log10 coordinates; a raw 1.0 lands at 10^1.
        # Parity is ratio = 1.0 -> log10 = 0.
        ax = "x" if ci == 0 else f"x{ci+1}"
        ay = "y domain" if ci == 0 else f"y{ci+1} domain"
        fig.add_shape(type="line", x0=0, x1=0, y0=0, y1=1, yref=ay, xref=ax,
                      line=dict(color=K.RED, width=2, dash="dash"))
        # OPENING VIEW ONLY. A raw log axis spans to 1e-56 and renders the bulk as a
        # vertical line. Nothing is removed - double-click autoranges to the full
        # extent, and the count outside is disclosed in the caption.
        fig.update_xaxes(type="log", range=[-4, 2],
                         title_text="round-trip cost ÷ realized capture (log)",
                         row=1, col=ci + 1)
        fig.update_yaxes(range=[-0.02, 1.02], title_text="ECDF" if ci == 0 else None,
                         row=1, col=ci + 1)

    kill = CONFIG["cooper_thresholds"]["row_11_kill_threshold"]
    cap = K.caption(
        sample="detection universe with quotes_ingested, hold 30 min, fixed_horizon grid. "
               "Ratio computed PER EVENT then distributed - never a ratio of medians.<br>"
               "        Events with realized capture <= 0 are undefined on the ratio and "
               "are excluded from the ECDF but reported as a share in the T7 artifact.",
        filters="D17 exclusion (locked carried), midpoint at δ = 0 on the sip basis "
                f"(D16). Vertical rule at 1.0; kill threshold {kill} on the RTH cell at "
                "latency 5 (row 11).<br>         The 1.5× column carries equal prominence "
                "with 1× by A2-5; only 1× triggers row 11.",
        extra=CONFIG["standing_qualifier"]["text"] + "<br>       Opening view is [1e-4, 1e2]; 71 of 26,396 defined ratios sit outside it (premarket 11, RTH 60, post 0), reachable<br>       by double-click - none is removed.",
    )
    K.base_layout(fig, "06 · Round-trip cost against realized capture — the gate",
                  cap, height=760, width=1360, cap_y=-0.44, margin_b=300)
    fig.update_layout(legend=dict(orientation="h", x=0.0, y=-0.22, xanchor="left",
                                  yanchor="top", font=dict(size=9),
                                  bgcolor="rgba(255,255,255,0.9)",
                                  bordercolor=K.GRID, borderwidth=1))
    for a in fig.layout.annotations[:3]:
        a.font.size = 12.5
        a.font.color = K.INK
    K.write(fig, "06_cost_vs_capture")


if __name__ == "__main__":
    main()
