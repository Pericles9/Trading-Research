"""Chart 01 - is filtered_quotes consolidated best-quote data, and are the
dropped source columns usable?

Panel A  per event: share of T=0 rows with bid_exchange != ask_exchange (x)
         against distinct venues seen (y), premarket / RTH / post.
Panel B  indicators null share per event, by era.
Panel C  conditions code-combination frequency, codes as opaque integers.
Panel D  storage-order census (T1c-v) - share of consecutive FILE-order rows
         where each field decreases.

Failure appearances from the contract:
  A - all events at share ~0 with one venue each -> per-venue data, and every
      midpoint in this phase would need a best-quote reconstruction first.
  B - null everywhere -> the indicator route is closed.
  C - one combination on ~100% of rows -> the field carries no discriminating
      information.
  D - none. No hypothesis rests on it; it is a record of archive state.
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

A = "results/phase_11/artifacts"
SEGS = ["premarket", "rth", "post"]
SEG_COLOR = {"premarket": K.ORANGE, "rth": K.BLUE, "post": K.AQUA}
ERA_COLOR = {"era_2020_2021": K.VIOLET, "era_2022_2024": K.GREEN}


def main() -> None:
    ident = pd.read_parquet(f"{A}/t1a_exchange_identity.parquet")
    ident = ident[ident.segment.isin(SEGS)]
    ind = pd.read_parquet(f"{A}/t1c_indicators.parquet")
    ind["share_null"] = ind.n_null / ind.n_rows
    combos = pd.read_parquet(f"{A}/t1c_conditions_combos.parquet")
    stor = pd.read_parquet(f"{A}/t1c_storage_order.parquet")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "A · venues vs. two-sided share (T=0)",
            "B · <i>indicators</i> null share, by era",
            "C · <i>conditions</i> combinations (opaque)",
            "D · storage order (T1c-v)",
        ),
        horizontal_spacing=0.16, vertical_spacing=0.13,
    )

    # -- Panel A -----------------------------------------------------------
    for seg in SEGS:
        s = ident[ident.segment == seg]
        fig.add_trace(go.Scatter(
            x=s.share_two_sided, y=s.n_bid_exch, mode="markers",
            name=f"{seg} (n={len(s)} events)", legendgroup=seg,
            marker=dict(color=K.rgba(SEG_COLOR[seg], 0.72), size=9,
                        line=dict(width=1.4, color="white")),
            customdata=np.stack([s.ticker, s.n_ask_exch, s.n_rows], axis=-1),
            hovertemplate=("%{customdata[0]} · " + seg +
                           "<br>two-sided %{x:.3f}<br>bid venues %{y}"
                           "<br>ask venues %{customdata[1]}"
                           "<br>rows %{customdata[2]:,}<extra></extra>"),
        ), row=1, col=1)
    # The failure appearance lives in the bottom-left corner; mark it.
    fig.add_shape(type="rect", x0=-0.02, x1=0.01, y0=0.4, y1=1.6,
                  fillcolor=K.rgba(K.RED, 0.10), line=dict(color=K.RED, width=1,
                  dash="dot"), row=1, col=1)
    fig.add_annotation(x=0.055, y=1.5, text="per-venue failure zone<br>(1 venue, ~0 two-sided)",
                       showarrow=False, font=dict(size=9, color=K.RED),
                       xanchor="left", row=1, col=1)

    # -- Panel B -----------------------------------------------------------
    for era, sub in ind.groupby("era"):
        sub = sub.sort_values("share_null")
        fig.add_trace(go.Scatter(
            x=sub.share_null, y=np.arange(len(sub)), mode="markers",
            name=f"{era} (n={len(sub)} events)", legendgroup=era,
            marker=dict(color=K.rgba(ERA_COLOR[era], 0.78), size=8,
                        line=dict(width=1.2, color="white")),
            customdata=np.stack([sub.ticker, sub.n_rows], axis=-1),
            hovertemplate=("%{customdata[0]} · " + era +
                           "<br>null share %{x:.4f}<br>rows %{customdata[1]:,}"
                           "<extra></extra>"),
        ), row=1, col=2)
    fig.add_vline(x=1.0, line=dict(color=K.RED, width=1.5, dash="dot"), row=1, col=2)
    fig.add_annotation(x=0.985, y=len(ind) * 0.5, text="all-null → route closed",
                       showarrow=False, textangle=-90, xanchor="right",
                       font=dict(size=9, color=K.RED), row=1, col=2)

    # -- Panel C -----------------------------------------------------------
    c = combos.sort_values("n_rows", ascending=True)
    tot = c.n_rows.sum()
    fig.add_trace(go.Bar(
        x=c.n_rows, y=c.combo.astype(str), orientation="h", showlegend=False,
        marker=dict(color=K.rgba(K.BLUE, 0.80),
                    line=dict(width=1.6, color=K.SURFACE)),
        text=[f" {n:,} · {e}ev" for n, e in zip(c.n_rows, c.n_events)],
        textposition="outside", textfont=dict(size=9, color=K.INK2), cliponaxis=False,
        hovertemplate="combo [%{y}]<br>rows %{x:,}<extra></extra>",
    ), row=2, col=1)

    # -- Panel D -----------------------------------------------------------
    fields = [("share_sip_decreases", "sip_timestamp", K.BLUE),
              ("share_par_decreases", "participant_timestamp", K.ORANGE),
              ("share_seq_decreases", "sequence_number", K.AQUA)]
    for i, (col, lab, colr) in enumerate(fields):
        fig.add_trace(go.Scatter(
            x=stor[col], y=np.full(len(stor), i) + np.random.default_rng(42)
            .uniform(-0.16, 0.16, len(stor)),
            mode="markers", showlegend=False,
            marker=dict(color=K.rgba(colr, 0.62), size=7,
                        line=dict(width=1.1, color="white")),
            customdata=stor.ticker,
            hovertemplate="%{customdata} · " + lab + "<br>decreasing %{x:.5f}<extra></extra>",
        ), row=2, col=2)
    fig.add_vline(x=0.5, line=dict(color=K.INK2, width=1, dash="dash"), row=2, col=2)
    fig.add_annotation(x=0.5, y=2.62, text="  50% = no order", showarrow=False,
                       xanchor="left", font=dict(size=9, color=K.INK2), row=2, col=2)

    # -- axes --------------------------------------------------------------
    fig.update_xaxes(title_text="share of rows with bid_exchange ≠ ask_exchange",
                     range=[-0.03, 1.03], row=1, col=1)
    fig.update_yaxes(title_text="distinct bid venues", row=1, col=1)
    fig.update_xaxes(title_text="share of rows with indicators NULL",
                     range=[-0.02, 1.02], row=1, col=2)
    fig.update_yaxes(title_text="event (sorted within era)", showticklabels=False,
                     row=1, col=2)
    # Headroom so the outside bar labels do not run into panel D.
    fig.update_xaxes(title_text="rows (log)", type="log",
                     range=[np.log10(c.n_rows.min() / 4), np.log10(c.n_rows.max() * 60)],
                     row=2, col=1)
    fig.update_yaxes(title_text="conditions combination", type="category", row=2, col=1)
    fig.update_xaxes(title_text="share of consecutive file-order pairs that decrease",
                     range=[-0.03, 1.06], row=2, col=2)
    fig.update_yaxes(title_text="", tickmode="array", tickvals=[0, 1, 2],
                     ticktext=[f[1] for f in fields], row=2, col=2)

    n_ev = len(ident[["ticker", "event_date"]].drop_duplicates())
    n_src = int(ind.n_rows.sum())
    cap = K.caption(
        sample=f"dev v4 PRIMARY cohort, {n_ev} events. Panel A: T=0 only, "
               f"{int(ident.n_rows.sum()):,} quote rows.<br>"
               f"        Panels B/C/D: source quotes.parquet, all sessions "
               f"T-3..T+3, {n_src:,} rows.",
        filters="dev_cohort='primary'. No quote state excluded - T1 is a census.<br>"
                "         Segments from pinned exchange_calendars 4.13.2 XNYS "
                "(half days honoured).",
        extra="Panel D is the sole escalation-row-19 exemption (row 19a): measuring<br>"
              "       storage order necessarily depends on storage order, and its "
              "output feeds nothing.<br>       Every other query in this phase "
              "sorts explicitly.",
    )
    K.base_layout(fig, "01 · Quote table identity — is this consolidated best-quote data?",
                  cap, height=1040, width=1180, cap_y=-0.125, margin_b=210, margin_r=90)
    fig.update_layout(legend=dict(orientation="h", y=1.075, x=0.0, xanchor="left",
                                 font=dict(size=10.5), bgcolor="rgba(255,255,255,0.86)",
                                 bordercolor=K.GRID, borderwidth=1))
    for a in fig.layout.annotations[:4]:
        a.font.size = 12.5
        a.font.color = K.INK
        a.y = a.y + 0.012
    K.write(fig, "01_quote_table_identity")


if __name__ == "__main__":
    main()
