"""Chart 05 - what does it cost to cross at detection?

ENCODING DEVIATION, recorded per Amendment 3 A3-1: the prompt specified "twin
axes bp and cents". A dual y-scale is the one encoding this project's
visualization standard forbids outright, and Phase 9 resolved the identical
conflict on its chart 06 with a linked panel sharing the x-axis. Charts 05 and
09 follow that precedent - two stacked panels per facet, upper basis points,
lower cents, identical faceting and identical n. The reason it matters here:
D19 exists BECAUSE bp and cents move in opposite directions, and on twin axes a
reader can see one line, read a slope, and believe they have seen both units.

Rows = latency x unit, cols = era. x = participation quintile. Violin + strip.
Cells with n < 100 are hatched and carry no claim. Latency 0 is marked as the
impossible upper bound.
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
ERAS = ["era_2020_2021", "era_2022_2024"]
UNITS = [("eff_bp", "bp"), ("eff_cents", "cents")]


def main() -> None:
    d = pd.read_parquet(f"{A}/t6_effective_spread.parquet")
    d = d[(d.det_segment == "rth") & d.eff_bp.notna() & (d.eff_bp > 0)]

    titles, specs = [], []
    for lat in LAT:
        for _, un in UNITS:
            for era in ERAS:
                titles.append(f"latency {lat} min{' — UPPER BOUND, impossible' if lat == 0 else ''} · {un} · {era}")
    fig = make_subplots(rows=len(LAT) * 2, cols=2, subplot_titles=titles,
                        shared_xaxes=True, vertical_spacing=0.018,
                        horizontal_spacing=0.09)

    rng = np.random.default_rng(42)
    for li, lat in enumerate(LAT):
        for ui, (col, un) in enumerate(UNITS):
            r = li * 2 + ui + 1
            for ci, era in enumerate(ERAS):
                sub = d[(d.latency == lat) & (d.era == era)]
                for pq in [1, 2, 3, 4, 5]:
                    s = sub[sub.pq_rth_open == pq][col].dropna()
                    s = s[s > 0]
                    if not len(s):
                        continue
                    thin = len(s) < CONFIG["universe"]["min_cell_n"]
                    fig.add_trace(go.Violin(
                        x=np.full(len(s), pq), y=s, showlegend=False,
                        line=dict(color=K.INK2 if thin else K.BLUE, width=1.4),
                        fillcolor=K.rgba(K.RED if thin else K.BLUE, 0.13 if thin else 0.22),
                        points=False, width=0.8, spanmode="hard", hoverinfo="skip",
                    ), row=r, col=ci + 1)
                    v, _ = K.subsample(s.values, 400)
                    fig.add_trace(go.Scatter(
                        x=pq + rng.uniform(-.14, .14, len(v)), y=v, mode="markers",
                        showlegend=False,
                        marker=dict(color=K.rgba(K.BLUE, .45), size=3.5),
                        hovertemplate=f"pq {pq}<br>%{{y:,.2f}} {un}<extra></extra>",
                    ), row=r, col=ci + 1)
                    fig.add_annotation(x=pq, y=np.log10(max(s.median(), 1e-9)),
                                       xref=f"x{(r-1)*2+ci+1}", yref=f"y{(r-1)*2+ci+1}",
                                       text=f"n={len(s):,}" + ("<br><b>HATCHED</b>" if thin else ""),
                                       showarrow=False, font=dict(size=7, color=K.INK),
                                       bgcolor="rgba(255,255,255,.75)")
                fig.update_yaxes(type="log", title_text=un if ci == 0 else None,
                                 row=r, col=ci + 1)
                fig.update_xaxes(tickmode="array", tickvals=[1, 2, 3, 4, 5],
                                 title_text="participation quintile (pq_rth_open)"
                                 if r == len(LAT) * 2 else None, row=r, col=ci + 1)

    n_ev = d[["ticker", "event_date"]].drop_duplicates().shape[0]
    cap = K.caption(
        sample=f"detection universe, RTH detection segment, {n_ev:,} events with "
               f"quotes_ingested. Coverage source: Phase 4/5 materialisations (D15).<br>"
               f"        Premarket and post are measured and in the artifact; the "
               f"decision rests on the RTH cell alone (D18).",
        filters="D17 exclusion: crossed / null / non-positive / one-side-missing / "
                "zero-size removed; LOCKED CARRIED.<br>         Midpoint = "
                "contemporaneous consolidated best quote at δ = 0, sip_timestamp basis "
                "(D16). Cells n<100 hatched, no claim.",
        extra=CONFIG["standing_qualifier"]["text"] + "<br>       ENCODING DEVIATION "
              "(A3-1): stacked bp/cents panels instead of the specified twin axes - a "
              "dual y-scale is<br>       barred by the project standard; Phase 9 chart 06 "
              "precedent. Latency 0 is a physical impossibility, marked as the upper bound.",
    )
    K.base_layout(fig, "05 · Effective spread at the detection anchor — basis points and "
                       "cents, never one alone",
                  cap, height=340 * len(LAT), width=1180, cap_y=-0.055, margin_b=230)
    for a in fig.layout.annotations[:len(titles)]:
        a.font.size = 10
        a.font.color = K.INK
    K.write(fig, "05_effective_spread_at_detection")


if __name__ == "__main__":
    main()
