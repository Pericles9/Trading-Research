"""
E1-T5 charts: form-type mix, time-since-filing distribution, dilution-flag rate by
year x detection-price decile. Three separate files (one question each), not one
combined figure -- per research-charts skill SS1, each chart answers a single question.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/chart_t5_filing_landscape.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402


def chart_01_form_mix():
    df = pd.read_parquet(f"{CC.ART}/t5_form_mix.parquet").sort_values("n", ascending=False)
    summary = CC.load_json("t5_filing_landscape_summary")
    top = df.head(20)
    other_n = df["n"].iloc[20:].sum() if len(df) > 20 else 0
    x = top["flg_last_form"].tolist() + (["(other forms)"] if other_n else [])
    y = top["n"].tolist() + ([other_n] if other_n else [])

    fig = go.Figure(go.Bar(x=x, y=y, marker_color=CC.BLUE,
                            hovertemplate="%{x}<br>n=%{y:,}<extra></extra>"))
    fig.update_xaxes(title="nearest prior filing's form type", tickangle=-45)
    fig.update_yaxes(title="n events", type="log")
    cap = CC.caption(
        sample=f"n={summary['n_observed']:,} events with flg_quality=='observed' "
               f"(of {summary['n_total']:,} total; "
               f"{summary['n_no_filings_in_window']:,} no_filings_in_window, "
               f"{summary['n_unavailable']:,} unavailable, excluded here since "
               f"flg_last_form is undefined for both)",
        filters="top 20 form types by count, remainder pooled as '(other forms)'",
    )
    CC.base_layout(fig, "E1-T5: nearest prior filing, form-type mix", cap, height=560, cap_y=-0.42, margin_b=220)
    CC.write(fig, "t5_filing_landscape", "01_form_mix")


def chart_02_lag_distribution():
    df = pd.read_parquet(f"{CC.ART}/t5_lag_days.parquet")
    summary = CC.load_json("t5_filing_landscape_summary")
    vals = df["flg_lag_days"].dropna()
    vals_pos = vals[vals > 0]

    fig = go.Figure(go.Histogram(x=np.log10(vals_pos), nbinsx=60, marker_color=CC.ORANGE,
                                  hovertemplate="log10(days)=%{x:.2f}<br>count=%{y}<extra></extra>"))
    fig.update_xaxes(title="log10(days since nearest prior filing)")
    fig.update_yaxes(title="count")
    s = summary["flg_lag_days_summary"]
    cap = CC.caption(
        sample=f"n={s['n']:,} events with flg_quality=='observed'",
        filters="time from nearest prior filing's SEC-accepted timestamp to t0, in days; log10 x-axis",
        extra=f"p10={s['p10']:.2f}d · median={s['p50']:.2f}d · p90={s['p90']:.2f}d · max={s['max']:.1f}d "
              f"({(vals <= 0).sum()} non-positive values excluded from the log axis, shown separately if any).",
    )
    CC.base_layout(fig, "E1-T5: time since nearest prior filing", cap, height=560, cap_y=-0.36, margin_b=200)
    CC.write(fig, "t5_filing_landscape", "02_lag_distribution")


def chart_03_dilution_rate_heatmap():
    df = pd.read_parquet(f"{CC.ART}/t5_dilution_rate_by_year_decile.parquet")
    years = sorted(df["year"].unique())
    deciles = sorted(df["detection_price_decile"].unique())

    z = np.full((len(years), len(deciles)), np.nan)
    text = np.full((len(years), len(deciles)), "", dtype=object)
    for _, r in df.iterrows():
        i, j = years.index(r["year"]), deciles.index(r["detection_price_decile"])
        if r["display_suppressed"]:
            text[i, j] = f"n={int(r['n'])}<br>(suppressed, n<{int(r['n'])})"
        else:
            z[i, j] = r["dilution_rate"]
            text[i, j] = f"{r['dilution_rate']:.1%}<br>n={int(r['n'])}<br>unavail={int(r['n_unavailable_cell'])}"

    fig = go.Figure(go.Heatmap(
        z=z, x=[f"D{d}" for d in deciles], y=years, colorscale="Oranges",
        text=text, texttemplate="%{text}", textfont=dict(size=9),
        hovertemplate="year=%{y} decile=%{x}<br>%{text}<extra></extra>",
        colorbar=dict(title="dilution rate"),
    ))
    fig.update_xaxes(title="detection-price decile (D0=cheapest .. D9=most expensive)")
    fig.update_yaxes(title="event year")
    summary = CC.load_json("t5_filing_landscape_summary")
    cap = CC.caption(
        sample=f"n={summary['n_total'] - summary['n_unavailable']:,} events with flg_quality != 'unavailable' "
               f"({summary['n_unavailable']:,} unavailable events excluded from each cell's own denominator, "
               f"count shown per cell)",
        filters=f"dilution rate = share of flg_dilution_form_before_t0==True; cells with n < "
                f"{summary['min_cell_n_display_floor']} shown as suppressed, not hidden "
                f"({summary['n_cells_suppressed']} of {summary['n_cells_total']} cells)",
    )
    CC.base_layout(fig, "E1-T5: dilution-flag rate by year x detection-price decile", cap,
                    height=620, cap_y=-0.30, margin_b=220)
    CC.write(fig, "t5_filing_landscape", "03_dilution_rate_heatmap")


if __name__ == "__main__":
    chart_01_form_mix()
    chart_02_lag_distribution()
    chart_03_dilution_rate_heatmap()
