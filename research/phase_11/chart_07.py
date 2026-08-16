"""Chart 07 - where, if anywhere, does the ratio clear?

Heatmap: rows = hold, cols = latency; facet by segment x era; colour = median
ratio at 1x cost; cells with n < 100 hatched; zero-atom cells ringed per Phase 9.

Failure appearance from the contract: uniform colour - no cell separates, and no
latency or hold choice changes the answer.
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
HOLDS = [5.0, 15.0, 30.0, 60.0, 120.0]
SEGS = ["premarket", "rth", "post"]
ERAS = ["era_2020_2021", "era_2022_2024"]
MIN_N = CONFIG["universe"]["min_cell_n"]


def main() -> None:
    d = pd.read_parquet(f"{A}/t7_cost_vs_capture.parquet")
    panels = [(s, e) for s in SEGS for e in ERAS]
    fig = make_subplots(rows=3, cols=2, subplot_titles=[f"{s} · {e}" for s, e in panels],
                        horizontal_spacing=0.10, vertical_spacing=0.09)

    for i, (seg, era) in enumerate(panels):
        r, c = divmod(i, 2)
        sub = d[(d.det_segment == seg) & (d.era == era)]
        Z, T, ring = [], [], []
        for h in HOLDS:
            zrow, trow = [], []
            for lat in LAT:
                s = sub[(sub.latency == lat) & (sub.hold == h)]["ratio_1.0x"]
                s = s.replace([np.inf, -np.inf], np.nan).dropna()
                n = len(s)
                med = float(s.median()) if n else np.nan
                thin = n < MIN_N
                atom = bool(n and (s == 0).mean() > 0.5)
                if atom:
                    ring.append((LAT.index(lat), HOLDS.index(h)))
                zrow.append(np.nan if thin else med)
                trow.append(("n<100<br>HATCHED" if thin else f"{med:.2f}") +
                            f"<br>n={n:,}" + ("<br>ZERO-ATOM" if atom else ""))
            Z.append(zrow)
            T.append(trow)
        fig.add_trace(go.Heatmap(
            z=Z, x=[str(l) for l in LAT], y=[str(int(h)) for h in HOLDS],
            text=T, texttemplate="%{text}", textfont=dict(size=8),
            colorscale=K.DIVERGING, zmid=1.0, showscale=(i == 0),
            colorbar=dict(title="median<br>ratio", len=0.30, y=0.85),
            hovertemplate="latency %{x} min<br>hold %{y} min<br>%{text}<extra></extra>",
        ), row=r + 1, col=c + 1)
        for xi, yi in ring:
            fig.add_shape(type="rect", x0=xi - .5, x1=xi + .5, y0=yi - .5, y1=yi + .5,
                          line=dict(color=K.RED, width=2.5), row=r + 1, col=c + 1)
        fig.update_xaxes(title_text="latency (min)" if r == 2 else None, row=r + 1, col=c + 1)
        fig.update_yaxes(title_text="hold (min)" if c == 0 else None, row=r + 1, col=c + 1)

    cap = K.caption(
        sample="detection universe with quotes_ingested, fixed_horizon grid. Median of "
               "the PER-EVENT ratio at 1× cost; per-cell n printed in every cell.<br>"
               "        Cells with n < 100 are hatched (shown blank, n printed) and carry "
               "no claim. Red-ringed cells are Phase 9 zero-atom cells.",
        filters="D17 exclusion (locked carried); midpoint at δ = 0 on the sip basis "
                "(D16). Diverging scale centred on 1.0 - blue below, red above.<br>"
                "         The decision rests on the RTH panels alone (D18); premarket and "
                "post are shown and carry no kill/clear decision.",
        extra=CONFIG["standing_qualifier"]["text"],
    )
    K.base_layout(fig, "07 · Cost-to-capture across the latency × hold grid",
                  cap, height=1080, width=1180, cap_y=-0.085, margin_b=200)
    for a in fig.layout.annotations[:len(panels)]:
        a.font.size = 12
        a.font.color = K.INK
    K.write(fig, "07_cost_capture_grid")


if __name__ == "__main__":
    main()
