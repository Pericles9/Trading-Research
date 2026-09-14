"""
E1-T1 (part 1/2): univariate distributions for the fundamental-side variables that
don't depend on the tape-metrics build (shs_, spl_, si_ groups; flg_ counts/quality;
detection_price; year). The tape-side variables (event volume, print counts,
inter-trade interval, session, ticker) are in t1_univariate_tape.py, which reads
tape_metrics.parquet once t1_prep_tape_metrics.py has produced it.

Every panel states its own n/unavailable/not-applicable breakdown in-panel (never only
in the caption), via chart_common.add_histogram_panel. "Not applicable" is used only
where a real, structural non-missing state exists distinct from data unavailability
(e.g. spl_last_split_ratio is NaN for the ~59% of events with zero splits in the
window -- a real "no split occurred", not "couldn't observe" -- kept separate from
spl_quality=='unavailable' per E1-T2's own finding about that column).

flg_last_form's own distribution and flg_lag_ns's distribution are NOT re-rendered
here -- both already have a dedicated chart in results/fundamental_exploration/charts/
t5_filing_landscape/ (01_form_mix.html, 02_lag_distribution.html). Per research-charts
skill SS0 ("does a chart already exist for this? ... do not write a parallel
renderer."), this script covers what T5 doesn't: flg_n_filings_24h/72h and flg_quality.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t1_univariate_fundamentals.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def quality_bar(fig, row, col, series, title):
    counts = series.value_counts()
    fig.add_trace(go.Bar(x=counts.index.tolist(), y=counts.values, marker_color=CC.AQUA,
                          hovertemplate="%{x}<br>n=%{y:,}<extra></extra>"), row=row, col=col)
    fig.add_annotation(text=f"<b>{title}</b>", xref="x domain", yref="y domain",
                        x=0.02, y=1.12, xanchor="left", yanchor="bottom",
                        showarrow=False, font=dict(size=11, color=CC.INK), row=row, col=col)
    fig.update_yaxes(title="count", row=row, col=col)


def load():
    df = pd.read_parquet(f"{C.ART}/e1_joined.parquet")
    df = C.add_corrected_shares_outstanding(df)
    df = C.add_identity_fields(df)
    return df


def chart_01_shares_outstanding(df, n_total):
    fig = make_subplots(rows=2, cols=2, vertical_spacing=0.20, horizontal_spacing=0.10,
                         subplot_titles=("", "", "", ""))
    n_unavail_shs = int((df["shs_shares_outstanding"].isna()).sum())
    CC.add_histogram_panel(fig, 1, 1, df["shs_shares_outstanding"], "shs_shares_outstanding (raw, as filed)",
                            log_x=True, n_total=n_total, n_unavailable=n_unavail_shs, color=CC.BLUE,
                            x_title="shares")
    CC.add_histogram_panel(fig, 1, 2, df["shs_shares_outstanding_corrected"], "shs_shares_outstanding (split-corrected)",
                            log_x=True, n_total=n_total, n_unavailable=n_unavail_shs, color=CC.ORANGE,
                            x_title="shares")
    lag_days = df["shs_lag_ns"] / 86_400e9
    CC.add_histogram_panel(fig, 2, 1, lag_days, "shs_lag_ns (staleness, days)",
                            log_x=True, n_total=n_total, n_unavailable=n_unavail_shs, color=CC.BLUE,
                            x_title="days")
    quality_bar(fig, 2, 2, df["shs_quality"], "shs_quality")
    fig.update_layout(height=760)
    cap = CC.caption(sample=f"n={n_total:,} in-scope events",
                      filters="shs_shares_outstanding: as filed, never split-adjusted unless labeled corrected; "
                              "never a float, never a market cap (SS1)")
    CC.base_layout(fig, "E1-T1: shares outstanding", cap, height=820, cap_y=-0.16, margin_b=170)
    CC.write(fig, "t1_univariate", "01_shares_outstanding")


def chart_02_split_history(df, n_total):
    fig = make_subplots(rows=2, cols=2, vertical_spacing=0.20, horizontal_spacing=0.10)
    n_unavail_spl = int((df["spl_quality"] == "unavailable").sum())
    CC.add_histogram_panel(fig, 1, 1, df["spl_n_splits_365d"], "spl_n_splits_365d",
                            log_x=False, n_total=n_total, n_unavailable=0, color=CC.GREEN,
                            x_title="count", nbins=10)
    rate = df["spl_reverse_split_365d"].astype(float)
    fig.add_trace(go.Bar(x=["False", "True"], y=[int((rate == 0).sum()), int((rate == 1).sum())],
                          marker_color=CC.GREEN, hovertemplate="%{x}<br>n=%{y:,}<extra></extra>"), row=1, col=2)
    fig.add_annotation(text="<b>spl_reverse_split_365d</b>", xref="x domain", yref="y domain",
                        x=0.02, y=1.12, xanchor="left", yanchor="bottom", showarrow=False,
                        font=dict(size=11, color=CC.INK), row=1, col=2)
    n_no_split = int((df["spl_n_splits_365d"] == 0).sum())
    CC.add_histogram_panel(fig, 2, 1, df["spl_last_split_ratio"], "spl_last_split_ratio (nearest split before t0, any lookback)",
                            log_x=True, n_total=n_total, n_unavailable=n_unavail_spl,
                            n_not_applicable=0, color=CC.GREEN, x_title="new/old shares ratio")
    quality_bar(fig, 2, 2, df["spl_quality"], "spl_quality (see E1-T2: conflates zero with unavailable)")
    cap = CC.caption(
        sample=f"n={n_total:,} in-scope events",
        filters="spl_n_splits_365d/spl_reverse_split_365d: strictly the 365 days before t0. "
                "spl_last_split_ratio: the single nearest split before t0, unbounded lookback -- a "
                "different, wider population than the 365d window at left.",
        extra=f"{n_no_split:,} events ({n_no_split/n_total:.1%}) have spl_n_splits_365d==0 -- a real "
              f"confirmed zero, distinct from spl_quality=='unavailable' (E1-T2 finding).",
    )
    CC.base_layout(fig, "E1-T1: split history", cap, height=820, cap_y=-0.20, margin_b=190)
    CC.write(fig, "t1_univariate", "02_split_history")


def chart_03_short_interest(df, n_total):
    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08)
    n_unavail_si = int((df["si_quality"] == "unavailable").sum())
    CC.add_histogram_panel(fig, 1, 1, df["si_shares_short"], "si_shares_short",
                            log_x=True, n_total=n_total, n_unavailable=n_unavail_si, color=CC.YELLOW,
                            x_title="shares")
    lag_days = df["si_lag_ns"] / 86_400e9
    CC.add_histogram_panel(fig, 1, 2, lag_days, "si_lag_ns (days)",
                            log_x=True, n_total=n_total, n_unavailable=n_unavail_si, color=CC.YELLOW,
                            x_title="days")
    quality_bar(fig, 1, 3, df["si_quality"], "si_quality")
    cap = CC.caption(sample=f"n={n_total:,} in-scope events",
                      filters="short interest is heavily lagged by construction (FINRA settlement-date "
                              "reporting) -- descriptive only, per SS1")
    CC.base_layout(fig, "E1-T1: short interest", cap, height=560, cap_y=-0.30, margin_b=190)
    CC.write(fig, "t1_univariate", "03_short_interest")


def chart_04_filing_counts_and_quality(df, n_total):
    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08)
    CC.add_histogram_panel(fig, 1, 1, df["flg_n_filings_24h"], "flg_n_filings_24h",
                            log_x=False, n_total=n_total, n_unavailable=0, color=CC.PINK,
                            x_title="count", nbins=15)
    CC.add_histogram_panel(fig, 1, 2, df["flg_n_filings_72h"], "flg_n_filings_72h",
                            log_x=False, n_total=n_total, n_unavailable=0, color=CC.PINK,
                            x_title="count", nbins=15)
    quality_bar(fig, 1, 3, df["flg_quality"], "flg_quality")
    cap = CC.caption(
        sample=f"n={n_total:,} in-scope events",
        filters="flg_last_form and flg_lag_ns distributions are charted in "
                "results/fundamental_exploration/charts/t5_filing_landscape/ (01, 02) -- not repeated here",
    )
    CC.base_layout(fig, "E1-T1: filing counts and quality", cap, height=560, cap_y=-0.28, margin_b=180)
    CC.write(fig, "t1_univariate", "04_filing_counts_and_quality")


def chart_05_detection_price_and_year(df, n_total):
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10)
    CC.add_histogram_panel(fig, 1, 1, df["detection_price"], "detection_price",
                            log_x=True, n_total=n_total, n_unavailable=0, color=CC.VIOLET,
                            x_title="USD")
    year_counts = df["year"].value_counts().sort_index()
    fig.add_trace(go.Bar(x=year_counts.index.tolist(), y=year_counts.values, marker_color=CC.VIOLET,
                          hovertemplate="%{x}<br>n=%{y:,}<extra></extra>"), row=1, col=2)
    fig.add_annotation(text="<b>year</b>", xref="x domain", yref="y domain", x=0.02, y=1.12,
                        xanchor="left", yanchor="bottom", showarrow=False,
                        font=dict(size=11, color=CC.INK), row=1, col=2)
    fig.update_yaxes(title="n events", row=1, col=2)
    cap = CC.caption(sample=f"n={n_total:,} in-scope events",
                      filters="detection_price: D4-compliant tick-derived price at t0 (F1-T6, reused per SS1)")
    CC.base_layout(fig, "E1-T1: detection price and event year", cap, height=560, cap_y=-0.24, margin_b=170)
    CC.write(fig, "t1_univariate", "05_detection_price_and_year")


def main():
    df = load()
    n_total = len(df)
    chart_01_shares_outstanding(df, n_total)
    chart_02_split_history(df, n_total)
    chart_03_short_interest(df, n_total)
    chart_04_filing_counts_and_quality(df, n_total)
    chart_05_detection_price_and_year(df, n_total)


if __name__ == "__main__":
    main()
