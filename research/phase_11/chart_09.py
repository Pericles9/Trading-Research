"""Chart 09 - is the measured effective spread cost, or is it staleness?

The diagnostic that tests whether the headline effective spread measures cost or
measures quote age. x = bbo_age_at_trade_p50 (log ms), y = effective spread.
Facet by participation quintile, RTH only. Binned medians with n per bin, no
LOESS and no fitted slope.

ENCODING DEVIATION per A3-1, same as chart 05: two stacked panels (upper bp,
lower cents) instead of the specified twin axes. Phase 9 chart 06 precedent.

Failure appearance from the contract: effective spread rising monotonically with
quote age across every quintile - the headline is substantially a staleness
artifact and T7's numerator does not mean what it says.
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
PQ = [1, 2, 3, 4, 5]
EDGES = np.array([0, 10, 50, 200, 1e3, 5e3, 3e4, 3e5, np.inf])  # ms


def main() -> None:
    d = pd.read_parquet(f"{A}/t8_impact_cells.parquet")
    d = d[(d.det_segment == "rth") & d.eff_frac.notna() & (d.eff_frac > 0)
          & d.bbo_age_at_trade_p50.notna()].copy()
    d["age_ms"] = d.bbo_age_at_trade_p50 / 1e6
    d["eff_bp"] = d.eff_frac * 10000
    d["eff_cents"] = d.eff_frac * d.tw_mid * 100
    d = d[d.age_ms > 0]

    titles = [f"pq {p} · {u}" for p in PQ for u in ("bp", "cents")]
    fig = make_subplots(rows=2, cols=len(PQ), shared_xaxes=True,
                        subplot_titles=[f"pq {p} · {u}" for u in ("bp", "cents") for p in PQ],
                        horizontal_spacing=0.035, vertical_spacing=0.10)

    rng = np.random.default_rng(42)
    for ui, (col, un) in enumerate([("eff_bp", "bp"), ("eff_cents", "cents")]):
        for ci, p in enumerate(PQ):
            s = d[d.pq_rth_open == p]
            if not len(s):
                continue
            v, sub_flag = K.subsample(np.arange(len(s)), 3000)
            idx = s.index[v.astype(int)]
            sm = s.loc[idx]
            fig.add_trace(go.Scatter(
                x=sm.age_ms, y=sm[col], mode="markers", showlegend=False,
                marker=dict(color=K.rgba(K.BLUE, .18), size=3),
                hovertemplate=f"age %{{x:,.0f}} ms<br>%{{y:,.2f}} {un}<extra></extra>",
            ), row=ui + 1, col=ci + 1)
            b = pd.cut(s.age_ms, EDGES)
            gm = s.groupby(b, observed=True)[col].median()
            gn = s.groupby(b, observed=True)[col].size()
            xs = [np.sqrt(max(i.left, 1) * min(i.right, 1e6)) for i in gm.index]
            fig.add_trace(go.Scatter(
                x=xs, y=gm.values, mode="lines+markers", showlegend=False,
                line=dict(color=K.ORANGE, width=2.4), marker=dict(size=7),
                text=[f"n={n:,}" for n in gn.values],
                hovertemplate="binned median %{y:,.2f} " + un + "<br>%{text}<extra></extra>",
            ), row=ui + 1, col=ci + 1)
            for x, y, n in zip(xs, gm.values, gn.values):
                fig.add_annotation(x=np.log10(x), y=np.log10(max(y, 1e-9)),
                                   xref=f"x{ui*len(PQ)+ci+1}", yref=f"y{ui*len(PQ)+ci+1}",
                                   text=f"{n:,}", showarrow=False,
                                   font=dict(size=6.5, color=K.INK2), yshift=9)
            fig.update_xaxes(type="log", title_text="prevailing BBO age at trade (ms, log)"
                             if ui == 1 else None, row=ui + 1, col=ci + 1)
            fig.update_yaxes(type="log", title_text=un if ci == 0 else None,
                             row=ui + 1, col=ci + 1)

    n_cells = len(d)
    cap = K.caption(
        sample=f"detection universe, RTH detection segment, {n_cells:,} event × minute "
               f"cells with a defined effective spread and BBO age.<br>        Scatter "
               f"sub-sampled to 3,000 points per facet for legibility; binned medians and "
               f"their n use ALL cells. n printed above every bin.",
        filters="D17 exclusion (locked carried); midpoint at δ = 0 on the sip basis "
                "(D16). Age bins are fixed log-spaced edges, not quantiles.<br>"
                "         No LOESS, no fitted slope - binned medians and the distribution "
                "only.",
        extra=CONFIG["standing_qualifier"]["text"] + "<br>       ENCODING DEVIATION "
              "(A3-1): stacked bp/cents panels instead of twin axes; Phase 9 chart 06 "
              "precedent.",
    )
    K.base_layout(fig, "09 · Effective spread against prevailing quote age — cost, or "
                       "staleness?",
                  cap, height=760, width=1320, cap_y=-0.22, margin_b=210)
    for a in fig.layout.annotations[:2 * len(PQ)]:
        a.font.size = 11
        a.font.color = K.INK
    K.write(fig, "09_spread_vs_staleness")


if __name__ == "__main__":
    main()
