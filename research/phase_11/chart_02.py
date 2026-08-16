"""Chart 02 - how much of the session is in an unusable quote state, and is it
clustered?

Facet per state; x = share of segment CLOCK TIME in that state, y = longest
single run of that state (log seconds); one point per event; colour = segment.

A 2% share concentrated in one 40-minute run and a 2% share scattered across
the session are different facts, which is why the run length is the y-axis.

Failure appearance from the contract: time shares near zero across all states
and all segments - the tape is cleaner than expected and the exclusion question
is moot.

No cleaning is applied. This is a census; the exclusion rule is Cooper's at the
T4 gate (escalation row 19).
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
STATES = ["hard_unusable", "degraded", "crossed", "locked", "nonpos_price",
          "one_side_miss", "zero_bid_size", "zero_ask_size", "null_price"]
TITLE = {"hard_unusable": "hard_unusable  (UNION — gates row 5)",
         "degraded": "degraded  (UNION — reported only)",
         "crossed": "crossed  (bid &gt; ask)", "locked": "locked  (bid = ask)",
         "nonpos_price": "non-positive price", "one_side_miss": "one side missing",
         "zero_bid_size": "zero bid size", "zero_ask_size": "zero ask size",
         "null_price": "null price"}


def main() -> None:
    cen = pd.read_parquet(f"{A}/t2a_state_census.parquet")
    cen = cen[cen.day_offset == 0]
    runs = pd.read_parquet(f"{A}/t2b_run_lengths.parquet")

    long = []
    for st in STATES:
        col = f"time_{st}"
        share = cen[["ticker", "event_date", "segment", col]].rename(columns={col: "share"})
        r = runs[runs.state == st][["ticker", "event_date", "segment", "max_run_ns"]]
        m = share.merge(r, on=["ticker", "event_date", "segment"], how="left")
        m["state"] = st
        long.append(m)
    long = pd.concat(long, ignore_index=True)
    long["max_run_s"] = long.max_run_ns / 1e9

    # Zero-time cells cannot be drawn on a log axis, so their count goes in the
    # facet title rather than in a floating annotation that collides with it.
    nz = {st: int((long[long.state == st].share.fillna(0) <= 0).sum()) for st in STATES}
    titles = [f"{TITLE[s]}<br><span style='font-size:9px;color:#52514e'>"
              f"150 cells · {nz[s]} at zero time (not plottable)</span>" for s in STATES]

    fig = make_subplots(rows=3, cols=3, subplot_titles=titles,
                        horizontal_spacing=0.075, vertical_spacing=0.135)

    seen = set()
    for i, st in enumerate(STATES):
        r, c = divmod(i, 3)
        sub = long[long.state == st]
        for seg in SEGS:
            s = sub[(sub.segment == seg) & (sub.share > 0) & sub.max_run_s.notna()]
            if not len(s):
                continue
            fig.add_trace(go.Scatter(
                x=s.share, y=s.max_run_s, mode="markers",
                name=seg, legendgroup=seg, showlegend=seg not in seen,
                marker=dict(color=K.rgba(SEG_COLOR[seg], 0.70), size=8,
                            line=dict(width=1.2, color="white")),
                customdata=np.stack([s.ticker, s.event_date.astype(str)], axis=-1),
                hovertemplate=("%{customdata[0]} %{customdata[1]} · " + seg +
                               "<br>time share %{x:.5f}<br>longest run %{y:,.1f} s"
                               "<extra></extra>"),
            ), row=r + 1, col=c + 1)
            seen.add(seg)
    # Row-5 threshold, on the facet it actually gates. Shapes on a log axis take
    # log10 coordinates, so the value is converted explicitly rather than passed raw.
    fig.add_shape(type="line", x0=np.log10(0.25), x1=np.log10(0.25), y0=0, y1=1,
                  yref="y domain", xref="x",
                  line=dict(color=K.RED, width=1.6, dash="dot"))
    fig.add_annotation(x=np.log10(0.25), y=1, xref="x", yref="y domain",
                       text=" row 5 → 0.25", showarrow=False, xanchor="left",
                       yanchor="top", font=dict(size=9, color=K.RED))

    # Share is bounded in [0,1] by construction; pin the range so one facet's
    # threshold marker cannot stretch the axis past what the measure can reach.
    for i in range(9):
        fig.update_xaxes(type="log", range=[-9.4, 0.12], row=i // 3 + 1, col=i % 3 + 1,
                         title_text="share of clock time" if i // 3 == 2 else None)
        fig.update_yaxes(type="log", row=i // 3 + 1, col=i % 3 + 1,
                         title_text="longest run (s)" if i % 3 == 0 else None)

    cap = K.caption(
        sample="dev v4 PRIMARY cohort, 50 events × 3 segments = 150 cells per facet, "
               "T=0 only.<br>        Both axes log, so cells with zero time in a state "
               "cannot be drawn; their count is printed per facet.",
        filters="dev_cohort='primary', day_offset=0. NO cleaning applied - this is a "
                "census.<br>         Clock time is prevailing-quote duration, clipped at "
                "each segment boundary, sorted explicitly by (sip_timestamp, "
                "sequence_number).",
        extra="hard_unusable and degraded are set UNIONS and are bounded in [0,1]; the "
              "seven<br>       individual states are NON-EXCLUSIVE and may sum above "
              "the union. Escalation row 5<br>       is defined on hard_unusable only "
              "(Cooper 2026-08-15).",
    )
    K.base_layout(fig, "02 · Nonsensical state census — how much of the session is unusable, "
                       "and is it clustered?",
                  cap, height=1120, width=1240, cap_y=-0.10, margin_b=195)
    fig.update_layout(margin_t=125,
                      legend=dict(orientation="h", y=1.085, x=0.0, xanchor="left",
                                  font=dict(size=11), bgcolor="rgba(255,255,255,0.86)",
                                  bordercolor=K.GRID, borderwidth=1))
    for a in fig.layout.annotations[:9]:
        a.font.size = 11.5
        a.font.color = K.INK
    K.write(fig, "02_nonsensical_state_census")


if __name__ == "__main__":
    main()
