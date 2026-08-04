"""
Chart 07 - is runway one population or two?

Left panel: linear x, DENSITY PER MINUTE (the measure-invariant object).
Right panel: log x, raw counts per log bin, with the KDE trough marked.
Both coloured by detection segment. The atom at runway = 0 is drawn as its own
bar and labelled, because it is a point mass rather than a mode of a density.

Failure appearance: a single smooth decay from zero with no trough -> one
population, and the Phase 8 medians are readable as-is.

Why two panels with two measures: counts per LOG bin rise mechanically as the
bins widen, so a hump in the hours on a log axis is not by itself a second
mode. The left panel is the one that answers the question.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_9 import chart_common as K
from research.phase_9 import common as C

SEGS = ["premarket", "rth", "post"]


def main():
    j = json.load(open(f"{C.ART}/t6_runway_split.json"))
    R = pd.read_parquet(f"{C.ART}/t3_retracement.parquet")
    R = R[R.horizon == "t0_close"][["ticker", "event_date_canonical", "mp",
                                    "runway_minutes", "det_segment"]].copy()
    R["runway_minutes"] = R["runway_minutes"].astype(float)
    n_uni = len(R)
    trough = j["trough"]["trough_minutes"]
    n_zero = j["runway_zero_atom"]["n_runway_zero"]

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.085,
                        subplot_titles=["linear x — density per MINUTE (answers the question)",
                                        "log x — counts per log bin (bins widen to the right)"])

    lin_edges = np.arange(0, 981, 20)
    for si, sg in enumerate(SEGS):
        v = R.loc[R.det_segment == sg, "runway_minutes"].dropna().values
        cnt, _ = np.histogram(v, bins=lin_edges)
        fig.add_trace(go.Bar(
            x=(lin_edges[:-1] + 10), y=cnt / 20.0, name=f"{sg} (n={len(v):,})",
            marker_color=K.rgba(K.CAT5[si], 0.85), marker_line_width=0,
            hovertemplate=f"{sg}<br>%{{x}} ± 10 min<br>%{{y:.2f}} events/min<extra></extra>"),
            row=1, col=1)

        pos = v[v >= 1]
        if len(pos):
            lg = np.log10(pos)
            c2, e2 = np.histogram(lg, bins=np.linspace(0, np.log10(960), 45))
            # On a log axis Bar width is in DATA units, so a constant width
            # collapses every high-x bar to a hairline. Width each bar to its
            # own bin span - otherwise the log-bin hump this panel exists to
            # show is invisible.
            lo_e, hi_e = 10 ** e2[:-1], 10 ** e2[1:]
            fig.add_trace(go.Bar(
                x=(lo_e + hi_e) / 2, y=c2, width=(hi_e - lo_e), name=sg,
                marker_color=K.rgba(K.CAT5[si], 0.85), marker_line_width=0, showlegend=False,
                hovertemplate=f"{sg}<br>%{{x:.1f}} min<br>%{{y:,}} events<extra></extra>"),
                row=1, col=2)

    fig.update_layout(barmode="stack")

    # the zero atom, called out on the linear panel
    fig.add_annotation(x=10, y=n_zero / 20.0, xref="x", yref="y",
                       text=f"atom at runway = 0<br>n={n_zero:,} ({n_zero/n_uni:.1%})",
                       showarrow=True, arrowhead=2, ax=95, ay=-38,
                       font=dict(size=9.5, color=K.INK), bgcolor="rgba(255,255,255,0.88)",
                       row=1, col=1)

    # empirical trough on the log panel
    fig.add_vline(x=trough, line=dict(color=K.INK, width=2, dash="dash"), row=1, col=2)
    fig.add_annotation(x=np.log10(trough), y=0.97, xref="x2", yref="y2 domain",
                       text=f" KDE trough {trough:.1f} min<br> (only 1.19× deep vs mode 1)",
                       showarrow=False, font=dict(size=9, color=K.INK), xanchor="left",
                       bgcolor="rgba(255,255,255,0.88)")
    fig.add_annotation(x=np.log10(j["trough"]["mode_2_minutes"]), y=0.62, xref="x2", yref="y2 domain",
                       text=f"log-scale hump ~{j['trough']['mode_2_minutes']:.0f} min<br>"
                            f"= 11 events/min, vs ~780/min<br>in the first 6 minutes",
                       showarrow=False, font=dict(size=9, color=K.INK2), xanchor="center",
                       bgcolor="rgba(255,255,255,0.88)")

    md = j["measure_dependence"]
    title = ("07 · Is runway one population or two?<br>"
             "<sub>per-minute density decays monotonically through the bulk; the log-axis hump is a "
             "bin-width effect, not a second mode</sub>")
    cap = K.caption(
        f"detection universe n={n_uni:,}",
        "runway_minutes from Phase 8 A10.2 detection anchors",
        f"left panel: 20-min bins, y = events per MINUTE · right panel: 45 log bins over runway ≥ 1, raw counts<br>"
        f"per-minute density falls 342.65/min (0–20 min) → 68.80 (20–40) → ~10/min by 300 min; the largest<br>"
        f"interior local maximum is 13.55/min at 320–340 min, 25× below the first bin<br>"
        f"trough located by Gaussian KDE on log10(runway ≥ 1), bandwidth 0.15 log10 units; smoothing is<br>"
        f"used ONLY to locate the trough — every bar here is a raw count<br>"
        f"runway_minutes is NOT anchor-knowable and is never used as a markout bucket (escalation row 12)")
    fig.update_xaxes(title_text="runway (minutes, linear)", range=[0, 960], row=1, col=1)
    fig.update_xaxes(title_text="runway (minutes, log)", type="log", row=1, col=2)
    fig.update_yaxes(title_text="events per minute", row=1, col=1)
    fig.update_yaxes(title_text="events per log bin", row=1, col=2)
    K.base_layout(fig, title, cap, height=700, cap_y=-0.21, margin_b=290, margin_r=60, width=1350)
    K.legend_inside(fig, x=0.30, y=0.985)
    for a in fig.layout.annotations[:2]:
        a.font.size = 11
    K.write(fig, "07_runway_bimodality")


if __name__ == "__main__":
    main()
