"""
E1-T3 chart: shares-outstanding x detection-price, two-way event counts. Two panels
(raw decile, split-corrected decile) sharing the same price-decile x-axis -- a
count table rendered as a heatmap, not a scatter of a constructed market-cap value
(SS1: no market cap is built here).

Caption note on a real gotcha found while building this: only 1,741 events actually
had their own shares-outstanding value rescaled (their filing predated the nearest
pre-t0 split), but 12,222 events show a *different decile label* between the raw and
corrected tables. That gap is not 12,222 individually-miscounted events -- deciles are
recomputed independently on each of the two distributions, so correcting even 1,741
values shifts where ALL ten bin edges fall, which relabels many events that did not
themselves change. Both counts are shown; conflating them would overstate the
correction's per-event reach.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/chart_t3_shares_x_price.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402


def _ordered(tab: pd.DataFrame) -> pd.DataFrame:
    row_order = sorted(tab.index, key=lambda s: (s == "no_shs_data", s))
    col_order = sorted(tab.columns, key=lambda s: (s == "no_price_data", s))
    return tab.reindex(index=row_order, columns=col_order, fill_value=0)


def main():
    raw = _ordered(pd.read_parquet(f"{CC.ART}/t3_two_way_raw.parquet"))
    corrected = _ordered(pd.read_parquet(f"{CC.ART}/t3_two_way_corrected.parquet"))
    summary = CC.load_json("t3_shares_x_price_summary")

    fig = make_subplots(rows=1, cols=2, subplot_titles=("raw (as filed)", "split-corrected"),
                         horizontal_spacing=0.08)
    for col_idx, tab in enumerate([raw, corrected], start=1):
        fig.add_trace(go.Heatmap(
            z=tab.values, x=list(tab.columns), y=list(tab.index), colorscale="Blues",
            text=tab.values, texttemplate="%{text}", textfont=dict(size=9),
            coloraxis="coloraxis",
            hovertemplate="shs decile=%{y} price decile=%{x}<br>n=%{z}<extra></extra>",
        ), row=1, col=col_idx)
        fig.update_xaxes(title="detection-price decile", row=1, col=col_idx)
    fig.update_yaxes(title="shares-outstanding decile (S0=fewest .. S9=most; "
                            "no_shs_data = shs_shares_outstanding unavailable)", row=1, col=1)
    fig.update_layout(coloraxis=dict(colorscale="Blues", colorbar=dict(title="n events")), height=620)

    cap = CC.caption(
        sample=f"n={summary['n_total']:,} in-scope events "
               f"({summary['n_no_shs_data']:,} with no shares-outstanding data, "
               f"kept as their own 'no_shs_data' row, never dropped)",
        filters="counts only -- no market cap is constructed (shares outstanding x price is never multiplied)",
        extra=(f"{summary['n_split_correction_applied']:,} events had their own raw value rescaled by "
               f"spl_last_split_ratio (their shares-outstanding filing predated the nearest pre-t0 split). "
               f"{summary['n_events_changing_decile_after_correction']:,} events show a different decile "
               f"label between the two panels -- mostly bin-edge movement from those rescaled values "
               f"shifting where all ten deciles fall, not individually mismeasured events. "
               f"{summary['n_shs_zero_artifact']} events carry shs_shares_outstanding==0.0 exactly (a data "
               f"artifact, not a real value) -- landed in raw's S0 here, excluded into corrected's "
               f"no_shs_data instead."),
    )
    CC.base_layout(fig, "E1-T3: shares outstanding x detection price, two-way event counts", cap,
                    height=680, cap_y=-0.30, margin_b=230, width=1180)
    CC.write(fig, "t3_shares_x_price", "01_two_way_counts")


if __name__ == "__main__":
    main()
