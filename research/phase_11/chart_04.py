"""Chart 04 - are the trades and quotes tables time-aligned, and on which clock?

x = alignment offset delta, plotted on the 27-rung sweep grid at even spacing
(a symlog axis in effect, with the true value on every tick). y = share of
trades priced at or inside the quoted spread prevailing at trade_time + delta.
One faint line per event plus the pooled median; two colours, one per timestamp
basis; vertical rule at delta = 0. Facets: session (T=0, T-3) x segment.

Failure appearances from the contract: flat across the sweep on both bases
(quotes carry no information - Stage B does not run); a peak far from zero (the
tables are offset); or the two bases peaking in opposite directions with
neither near zero (neither clock is a usable reference).

The agent selects a row of the T3b pre-registered reading rule. No offset is
adopted here - that is Cooper's at the T4 gate (escalation row 19).
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
OFFSETS = CONFIG["alignment_sweep"]["alignment_offsets_ns"]
BASES = [("sip_timestamp", K.BLUE), ("participant_timestamp", K.ORANGE)]
PANELS = [(0, "premarket"), (0, "rth"), (-3, "premarket"), (-3, "rth")]


def tick(ns: int) -> str:
    if ns == 0:
        return "0"
    s = "−" if ns < 0 else "+"
    a = abs(ns)
    if a >= 1_000_000_000:
        return f"{s}{a/1e9:g}s"
    if a >= 1_000_000:
        return f"{s}{a/1e6:g}ms"
    return f"{s}{a/1e3:g}µs"


def main() -> None:
    d = pd.read_parquet(f"{A}/t3_alignment_sweep.parquet")
    idx = {o: i for i, o in enumerate(OFFSETS)}
    d["xi"] = d.offset_ns.map(idx)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[f"T{o:+d} · {s}" if o else f"T=0 · {s}" for o, s in PANELS],
        horizontal_spacing=0.085, vertical_spacing=0.135)

    seen = set()
    facet_n: dict = {}
    for i, (off, seg) in enumerate(PANELS):
        r, c = divmod(i, 2)
        for basis, colr in BASES:
            sub = d[(d.day_offset == off) & (d.segment == seg) & (d.basis == basis)]
            if not len(sub):
                continue
            # one faint line per event
            for (tk, ed), g in sub.groupby(["ticker", "event_date"]):
                g = g.sort_values("xi")
                fig.add_trace(go.Scatter(
                    x=g.xi, y=g.share_at_or_inside, mode="lines",
                    line=dict(color=K.rgba(colr, 0.13), width=1),
                    showlegend=False, hoverinfo="skip"), row=r + 1, col=c + 1)
            med = sub.groupby("xi").share_at_or_inside.median().reset_index()
            n_ev = sub[["ticker", "event_date"]].drop_duplicates().shape[0]
            n_tr = int(sub[sub.offset_ns == 0].n_trades.sum())
            # n is per facet per basis, so it is annotated in the facet - a single
            # legend figure would be the premarket count wrongly applied to all four.
            facet_n.setdefault((off, seg), []).append(
                f"<span style='color:{colr}'>{basis}: {n_ev} events, "
                f"{n_tr:,} trades</span>")
            fig.add_trace(go.Scatter(
                x=med.xi, y=med.share_at_or_inside, mode="lines+markers",
                name=basis, legendgroup=basis, showlegend=basis not in seen,
                line=dict(color=colr, width=2.6), marker=dict(size=6),
                customdata=[tick(OFFSETS[int(x)]) for x in med.xi],
                hovertemplate=("%{customdata} · " + basis +
                               "<br>pooled median at-or-inside %{y:.4f}<extra></extra>"),
            ), row=r + 1, col=c + 1)
            seen.add(basis)
        fig.add_vline(x=idx[0], line=dict(color=K.INK2, width=1.4, dash="dash"),
                      row=r + 1, col=c + 1)

    show = [0, 3, 6, 9, 12, 13, 14, 17, 20, 23, 26]
    for i, (off, seg) in enumerate(PANELS):
        r, c = divmod(i, 2)
        fig.update_xaxes(tickmode="array", tickvals=show,
                         ticktext=[tick(OFFSETS[k]) for k in show],
                         tickangle=-45, row=r + 1, col=c + 1,
                         title_text="alignment offset δ (27-rung sweep grid, even spacing)"
                         if r == 1 else None)
        fig.update_yaxes(range=[0, 1.02], row=r + 1, col=c + 1,
                         title_text="share at or inside quoted spread" if c == 0 else None)
        ax = "x domain" if i == 0 else f"x{i+1} domain"
        ay = "y domain" if i == 0 else f"y{i+1} domain"
        fig.add_annotation(x=0.02, y=0.05, xref=ax, yref=ay, xanchor="left",
                           text="<br>".join(facet_n.get((off, seg), [])),
                           showarrow=False, font=dict(size=9), align="left",
                           bgcolor="rgba(255,255,255,0.82)")

    cap = K.caption(
        sample="dev v4 PRIMARY cohort, 50 events. Faint line = one event; bold line = "
               "pooled median across events.<br>        n events and n trades printed "
               "per basis INSIDE EACH FACET (trade counts at δ = 0).<br>"
               "        They differ by facet, so they are not in the legend.",
        filters="dev_cohort='primary', segments premarket/RTH. Trades whose prevailing "
                "quote is in<br>         state_hard_unusable are counted separately and "
                "excluded from the at-or-inside numerator,<br>         never dropped from "
                "the denominator. Post segment is in the artifact, not drawn.",
        extra="Both tables are put on the SAME clock for each curve (escalation row 19 "
              "keeps the<br>       choice with Cooper at the T4 gate). ASOF join on "
              "(ticker, event_date, session_date)<br>       with an explicit key - never "
              "storage order.",
    )
    K.base_layout(fig, "04 · Trade–quote alignment sweep — are the two tables on the same "
                       "clock?",
                  cap, height=900, width=1180, cap_y=-0.135, margin_b=215)
    fig.update_layout(margin_t=115,
                      legend=dict(orientation="h", y=1.075, x=0.0, xanchor="left",
                                  font=dict(size=10.5),
                                  bgcolor="rgba(255,255,255,0.86)",
                                  bordercolor=K.GRID, borderwidth=1))
    for a in fig.layout.annotations[:4]:
        a.font.size = 12.5
        a.font.color = K.INK
    K.write(fig, "04_alignment_sweep")


if __name__ == "__main__":
    main()
