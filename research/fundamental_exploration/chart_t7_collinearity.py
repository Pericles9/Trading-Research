"""
E1-T7 chart: the full Spearman correlation heatmap among fundamental variables and
detection_price, with pairwise n shown in each cell's hover text (coverage varies
sharply -- pairwise n is never implied, always shown, per the Evidence Standard).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/chart_t7_collinearity.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402

LABELS = {
    "shs_shares_outstanding_corrected": "shs_shares_outstanding<br>(corrected)",
    "shs_lag_ns": "shs_lag_ns",
    "flg_lag_ns": "flg_lag_ns",
    "flg_n_filings_24h": "flg_n_filings_24h",
    "flg_n_filings_72h": "flg_n_filings_72h",
    "flg_dilution_form_before_t0_num": "flg_dilution_form_before_t0",
    "spl_n_splits_365d": "spl_n_splits_365d",
    "spl_reverse_split_365d_num": "spl_reverse_split_365d",
    "spl_last_split_ratio": "spl_last_split_ratio",
    "si_shares_short": "si_shares_short",
    "si_lag_ns": "si_lag_ns",
    "detection_price": "detection_price",
}


def main():
    corr = pd.read_parquet(f"{CC.ART}/t7_spearman_corr.parquet")
    n = pd.read_parquet(f"{CC.ART}/t7_spearman_n.parquet")
    summary = CC.load_json("t7_collinearity_summary")
    order = summary["variables"]
    corr = corr.loc[order, order]
    n = n.loc[order, order]
    labels = [LABELS[v] for v in order]

    text = [[f"rho={corr.loc[a,b]:.2f}<br>n={n.loc[a,b]:,}" for b in order] for a in order]

    fig = go.Figure(go.Heatmap(
        z=corr.values, x=labels, y=labels, zmin=-1, zmax=1, colorscale="RdBu", reversescale=True,
        text=text, hovertemplate="%{y} x %{x}<br>%{text}<extra></extra>",
        colorbar=dict(title="Spearman ρ"),
    ))
    fig.update_layout(height=760, width=860)
    fig.update_xaxes(tickangle=-40)

    cap = CC.caption(
        sample=f"n={summary['n_total']:,} in-scope events, pairwise-complete per cell (shown in hover, "
               f"ranges {min(summary['n_vs_detection_price'].values()):,}-{summary['n_total']:,})",
        filters="Spearman rank correlation; booleans coerced to 0/1; shs_shares_outstanding is the "
                "split-corrected figure (SS1)",
        extra=summary["gap_note"],
    )
    CC.base_layout(fig, "E1-T7: collinearity among fundamental variables and detection price", cap,
                    height=820, cap_y=-0.22, margin_b=200, margin_r=140, width=900)
    CC.write(fig, "t7_collinearity", "01_spearman_heatmap")


if __name__ == "__main__":
    main()
