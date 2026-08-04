"""
Chart 02 - does the flagged set change the conclusion or only the tails?

Facet per variant (i untrimmed / ii flagged-only / iii flag-excluded /
iv trimmed); x = pq_rth_open quintile, y = t0_close -> t1_close markout,
violin + strip; median and mean-simple marked with distinct glyphs.

Failure appearance: medians shift materially between variants -> the flag is
not tail-only and the Phase 8 restatement is larger than a footnote.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_9 import chart_common as K
from research.phase_9 import common as C

QS = [1, 2, 3, 4, 5]
VARIANTS = [("i_untrimmed_all", "(i) untrimmed — PRIMARY"),
            ("ii_flagged_only", "(ii) flagged only"),
            ("iii_flagged_excluded", "(iii) flag-excluded"),
            ("iv_trimmed", "(iv) trimmed 0.55–1.80")]


def main():
    cfg = C.load_cfg()
    lo, hi = cfg["trim_ratio_bounds"]
    flags = pd.read_parquet(f"{C.ART}/t1_cross_session_flags.parquet")
    flags["event_date_canonical"] = pd.to_datetime(flags["event_date_canonical"])

    b = pd.read_parquet(C.CONTAM_PATH)
    b["event_date_canonical"] = pd.to_datetime(b["event_date_canonical"])
    b = b[(b.anchor_name == "t0_close") & (b.horizon_name == "t1_close") & b.markout.notna()].copy()
    f = flags[flags.session_pair == "t0_t1"][C.KEY + ["flag_cross_session_extreme"]]
    b = b.merge(f, on=C.KEY, how="left")
    b["flag_cross_session_extreme"] = b["flag_cross_session_extreme"].fillna(False).astype(bool)
    b["ratio"] = np.exp(b["markout"])

    subs = {"i_untrimmed_all": b,
            "ii_flagged_only": b[b.flag_cross_session_extreme],
            "iii_flagged_excluded": b[~b.flag_cross_session_extreme],
            "iv_trimmed": b[b.ratio.between(lo, hi)]}

    rng, outside = K.zoom_range(b["markout"].values)

    fig = make_subplots(rows=1, cols=4, shared_yaxes=True,
                        subplot_titles=[t for _, t in VARIANTS],
                        horizontal_spacing=0.018)

    for ci, (vk, _) in enumerate(VARIANTS, start=1):
        d = subs[vk]
        for qv in QS:
            s = d.loc[d.pq_rth_open == qv, "markout"].dropna()
            if not len(s):
                continue
            fig.add_trace(go.Violin(
                y=s.values, x=[f"Q{qv}"] * len(s), name=f"Q{qv}",
                line=dict(color=K.CAT5[qv - 1], width=1.4),
                fillcolor=K.rgba(K.CAT5[qv - 1], 0.22),
                points=False, showlegend=False, spanmode="hard",
                hoverinfo="skip"), row=1, col=ci)
            pts, sub = K.subsample(s.values, cap=600)
            fig.add_trace(go.Scatter(
                y=pts, x=np.full(len(pts), f"Q{qv}"), mode="markers",
                marker=dict(color=K.rgba(K.INK2, 0.20), size=3),
                showlegend=False,
                hovertemplate=f"Q{qv}<br>markout %{{y:.4f}}<extra></extra>"), row=1, col=ci)
            med = float(s.median())
            msimple = float(np.log1p(np.expm1(s).mean())) if len(s) else None
            fig.add_trace(go.Scatter(
                y=[med], x=[f"Q{qv}"], mode="markers",
                marker=dict(color=K.INK, size=11, symbol="line-ew-open",
                            line=dict(width=3, color=K.INK)),
                showlegend=(ci == 1 and qv == 1), name="median",
                hovertemplate=f"Q{qv} median %{{y:.5f}}<extra></extra>"), row=1, col=ci)
            if msimple is not None and np.isfinite(msimple):
                fig.add_trace(go.Scatter(
                    y=[msimple], x=[f"Q{qv}"], mode="markers",
                    marker=dict(color=K.RED, size=9, symbol="diamond",
                                line=dict(width=1, color="white")),
                    showlegend=(ci == 1 and qv == 1), name="mean simple (as log)",
                    hovertemplate=f"Q{qv} mean simple {np.expm1(msimple):+.3%}<extra></extra>"),
                    row=1, col=ci)
            # per-cell n, pinned just inside the bottom of each facet so it
            # cannot collide with the facet titles along the top
            fig.add_annotation(x=f"Q{qv}", y=0.012, yref=f"y{ci if ci>1 else ''} domain",
                               xref=f"x{ci if ci>1 else ''}",
                               text=f"n={len(s):,}", showarrow=False, textangle=-90,
                               font=dict(size=8, color=K.INK2), yanchor="bottom")

    fig.add_hline(y=0, line=dict(color=K.INK2, width=1, dash="dot"))
    title = ("02 · t0_close → t1_close by participation quintile, four corporate-action variants<br>"
             "<sub>median (black bar) barely moves; the mean simple return (red diamond) flips sign</sub>")
    cap = K.caption(
        "Phase 8 a102_contamination.parquet, anchor t0_close, horizon t1_close",
        "markout non-null; Phase 8 flagged union already excluded upstream",
        f"variants: (i) all n={len(subs['i_untrimmed_all']):,} · (ii) flagged n={len(subs['ii_flagged_only']):,} · "
        f"(iii) flag-excluded n={len(subs['iii_flagged_excluded']):,} · (iv) trimmed n={len(subs['iv_trimmed']):,}<br>"
        f"n printed inside each violin · strip sub-sampled to 600/cell<br>"
        f"y zoomed to the 0.5–99.5 pct band; {outside:,} points lie outside, remain in<br>"
        f"the figure, and autorange on double-click — nothing is clipped<br>"
        "(iii) and (iv) are near-duplicates by construction:<br>"
        "flag band [0.5556, 1.8] vs trim [0.55, 1.80]")
    fig.update_yaxes(title_text="markout  log(p_t1_close / p_t0_close)", range=rng, row=1, col=1)
    for ci in range(1, 5):
        fig.update_yaxes(range=rng, row=1, col=ci)
    # one shared x title, not four overlapping copies
    fig.add_annotation(x=0.5, y=-0.085, xref="paper", yref="paper",
                       text="pq_rth_open quintile", showarrow=False,
                       font=dict(size=12, color=K.INK))
    K.base_layout(fig, title, cap, height=800, cap_y=-0.20, margin_b=300, margin_r=60)
    K.legend_inside(fig, x=0.012, y=0.13, yanchor="bottom")
    for a in fig.layout.annotations[:4]:
        a.font.size = 11
    K.write(fig, "02_cross_session_sensitivity")


if __name__ == "__main__":
    main()
