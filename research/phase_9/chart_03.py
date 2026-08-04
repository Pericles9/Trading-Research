"""
Chart 03 - how much of the excursion comes back, and how fast?

x = retrace_excursion (0 = still at the high, 1.0 = back to the T-1 RTH close,
>1.0 = below it), ECDF, one line per horizon t0..t3, reference lines at 0.5
and 1.0.

Failure appearance: ECDFs bunched far left and near-identical across horizons
-> nothing retraces and mean reversion is unsupported at any horizon.

HORIZON CEILING: T+3. event_minute_bars_v2 carries offsets -3..+3 only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_9 import chart_common as K
from research.phase_9 import common as C

HZ = ["t0_close", "t1_close", "t2_close", "t3_close"]


def main():
    R = pd.read_parquet(f"{C.ART}/t3_retracement.parquet")
    fig = go.Figure()

    meds = {}
    for i, h in enumerate(HZ):
        s = R.loc[R.horizon == h, "retrace_excursion"].dropna().sort_values()
        if not len(s):
            continue
        meds[h] = float(s.median())
        y = np.arange(1, len(s) + 1) / len(s)
        step = max(1, len(s) // 4000)          # thin the polyline, not the data
        fig.add_trace(go.Scatter(
            x=s.values[::step], y=y[::step], mode="lines",
            name=f"{h} (n={len(s):,}, median {meds[h]:.3f})",
            line=dict(color=K.CAT5[i], width=2.2),
            hovertemplate=f"{h}<br>retrace %{{x:.3f}}<br>ECDF %{{y:.3f}}<extra></extra>"))

    for xv, lab in ((0.5, "0.5 — half the excursion given back"),
                    (1.0, "1.0 — back to the T−1 RTH close")):
        fig.add_vline(x=xv, line=dict(color=K.INK2, width=1.5, dash="dash"))
        fig.add_annotation(x=xv, y=0.03, text=" " + lab, showarrow=False,
                           font=dict(size=9.5, color=K.INK2), xanchor="left",
                           bgcolor="rgba(255,255,255,0.85)")

    n0 = int(R.loc[R.horizon == "t0_close", "retrace_excursion"].notna().sum())
    title = ("03 · Excursion retracement ECDF by horizon<br>"
             "<sub>retrace = (H − p_h) / (H − A) · H = day_high_ext, A = tick_close_t−1_rth · "
             "T+3 is the hard horizon ceiling</sub>")
    cap = K.caption(
        f"detection universe n=15,369 (D1 15,763 minus the 394 det_undefined)",
        "H − A > 0 (0 undefined in this population); horizon session present in v2",
        "0 = still at the high · 1.0 = fully back to the T−1 RTH close · >1.0 = below it<br>"
        "x zoomed to [−1.5, 2.5]; tails remain in the figure and autorange on double-click<br>"
        "ECDF polyline thinned for rendering; every point is in the underlying data")
    fig.update_xaxes(title_text="retrace_excursion  (H − p_h) / (H − A)", range=[-1.5, 2.5])
    fig.update_yaxes(title_text="ECDF", range=[0, 1.02])
    K.base_layout(fig, title, cap, height=700, cap_y=-0.155, margin_b=230, margin_r=70)
    K.legend_inside(fig, x=0.012, y=0.985)
    K.write(fig, "03_retracement_ecdf")


if __name__ == "__main__":
    main()
