"""Chart 02 - does detection price alone predict net expectancy?

This is T3's competing explanation, not a finding in itself: cheap stocks file
differently, dilute more, reverse-split more, and cost more to trade, so a
fundamental split's gradient (if any) could just be a price split in different
clothes. No fundamental data enters this chart at all.

Failure appearance from the contract: no gradient across deciles -- price alone
explains nothing, so a fundamental split's gradient (if any) is not just price
in disguise.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from plotly.subplots import make_subplots

import chart_common as K

HORIZONS = [5, 15, 30, 60]


def main() -> None:
    t2 = K.load_json("t2_arm_zero_summary")
    by_h = t2["by_horizon_by_decile"]

    fig = make_subplots(rows=2, cols=2, subplot_titles=[f"{h} min" for h in HORIZONS],
                        vertical_spacing=0.14, horizontal_spacing=0.06)

    for i, h in enumerate(HORIZONS):
        r, c = divmod(i, 2)
        rows = by_h[str(h)]
        deciles = [f"D{row['decile']}" for row in rows]
        mfe_stats = [row["mfe_cost_mult"] for row in rows]
        mae_stats = [row["mae_cost_mult"] for row in rows]
        mfe_trace = K.box_from_stats(deciles, mfe_stats, "MFE cost-multiple", K.BLUE, "mfe")
        mae_trace = K.box_from_stats(deciles, mae_stats, "MAE cost-multiple", K.ORANGE, "mae")
        mfe_trace.showlegend = (i == 0)
        mae_trace.showlegend = (i == 0)
        mfe_trace.legendgroup = "mfe"
        mae_trace.legendgroup = "mae"
        fig.add_trace(mfe_trace, row=r + 1, col=c + 1)
        fig.add_trace(mae_trace, row=r + 1, col=c + 1)

    for i in range(4):
        r, c = divmod(i, 2)
        fig.update_yaxes(title_text="cost-multiple" if c == 0 else None, row=r + 1, col=c + 1)
        fig.update_xaxes(title_text="detection-price decile (0=cheapest)" if r == 1 else None,
                         row=r + 1, col=c + 1)

    n_total = sum(row["mfe_cost_mult"].get("n", 0) for row in by_h[str(HORIZONS[0])])
    cap = K.caption(
        sample=f"P0-covered events with a defined detection-price decile, n≈{n_total:,} per horizon.",
        filters="No fundamental column used. Boxes are precomputed p10/p25/median/p75/p90 "
                "(not raw points); mean not drawn on the box, shown on hover.",
        extra="Read directly: decile 0 (cheapest) shows the highest median MFE cost-multiple<br>"
              "        at every horizon (1.43x at 5min rising to 2.66x at 60min); the pattern<br>"
              "        across the middle deciles is not monotonic. This is the baseline T3's<br>"
              "        fundamental splits (charts 03-05) are read against.",
    )
    K.base_layout(fig, "02 · Arm zero — net expectancy by detection-price decile, no fundamental data",
                  cap, height=760, width=1080, cap_y=-0.16, margin_b=170)
    fig.update_layout(boxmode="group", margin_t=90)
    K.legend_inside(fig, x=0.012, y=1.10)
    K.write(fig, "02_arm_zero_price_decile")


if __name__ == "__main__":
    main()
