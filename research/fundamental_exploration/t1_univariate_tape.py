"""
E1-T1 (part 2/2): univariate distributions for the tape-side variables that depend on
t1_prep_tape_metrics.py's bulk DuckDB join (event volume, print counts, median
inter-trade interval, t0's session bucket) plus ticker frequency.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t1_univariate_tape.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def bar_panel(fig, row, col, counts, title):
    fig.add_trace(go.Bar(x=[str(x) for x in counts.index], y=counts.values, marker_color=CC.AQUA,
                          hovertemplate="%{x}<br>n=%{y:,}<extra></extra>"), row=row, col=col)
    fig.add_annotation(text=f"<b>{title}</b>", xref="x domain", yref="y domain", x=0.02, y=1.12,
                        xanchor="left", yanchor="bottom", showarrow=False,
                        font=dict(size=11, color=CC.INK), row=row, col=col)
    fig.update_yaxes(title="count", row=row, col=col)


def load():
    ef = pd.read_parquet(f"{C.ART}/e1_joined.parquet", columns=["event_id", "ticker"])
    tape = pd.read_parquet(f"{C.ART}/tape_metrics.parquet")
    return ef.merge(tape, on="event_id", how="left")


def chart_06_volume(df, n_total):
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10)
    CC.add_histogram_panel(fig, 1, 1, df["volume_shares"], "event volume (shares, regular session)",
                            log_x=True, n_total=n_total,
                            n_not_applicable=int((df["volume_shares"] == 0).sum()), color=CC.BLUE,
                            x_title="shares")
    CC.add_histogram_panel(fig, 1, 2, df["volume_notional"], "event volume (notional USD, regular session)",
                            log_x=True, n_total=n_total,
                            n_not_applicable=int((df["volume_notional"] == 0).sum()), color=CC.BLUE,
                            x_title="USD")
    cap = CC.caption(sample=f"n={n_total:,} in-scope events",
                      filters="declared window: regular session (09:30-16:00 America/New_York, XNYS) of "
                              "event_date_canonical -- config.tape_side.event_volume_window")
    CC.base_layout(fig, "E1-T1: event volume", cap, height=560, cap_y=-0.28, margin_b=180)
    CC.write(fig, "t1_univariate", "06_event_volume")


def chart_07_prints_and_intertrade(df, n_total):
    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08)
    CC.add_histogram_panel(fig, 1, 1, df["print_count_at_t0"], "print_count_at_t0 (same minute as t0)",
                            log_x=True, n_total=n_total,
                            n_not_applicable=int((df["print_count_at_t0"] == 0).sum()), color=CC.PINK,
                            x_title="prints")
    CC.add_histogram_panel(fig, 1, 2, df["print_count_session"], "print_count_session (regular session)",
                            log_x=True, n_total=n_total,
                            n_not_applicable=int((df["print_count_session"] == 0).sum()), color=CC.PINK,
                            x_title="prints")
    intertrade_s = df["median_intertrade_ns"] / 1e9
    CC.add_histogram_panel(fig, 1, 3, intertrade_s, "median inter-trade interval (regular session)",
                            log_x=True, n_total=n_total,
                            n_unavailable=int(df["median_intertrade_ns"].isna().sum()), color=CC.PINK,
                            x_title="seconds")
    cap = CC.caption(sample=f"n={n_total:,} in-scope events",
                      filters="print_count_at_t0: trades in t0_ns's own 60s bucket, any session. "
                              "print_count_session / median inter-trade interval: regular session only.")
    CC.base_layout(fig, "E1-T1: print counts and inter-trade interval", cap, height=560, cap_y=-0.28, margin_b=180)
    CC.write(fig, "t1_univariate", "07_prints_and_intertrade")


def chart_08_session_and_ticker(df, n_total):
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10)
    session_counts = df["t0_session"].value_counts()
    bar_panel(fig, 1, 1, session_counts, "t0_session")

    per_ticker = df["ticker"].value_counts()
    fig.add_trace(go.Histogram(x=per_ticker.values, nbinsx=30, marker_color=CC.AQUA,
                                hovertemplate="events per ticker=%{x}<br>n tickers=%{y}<extra></extra>"),
                  row=1, col=2)
    fig.add_annotation(text="<b>events per ticker</b>", xref="x domain", yref="y domain", x=0.02, y=1.12,
                        xanchor="left", yanchor="bottom", showarrow=False,
                        font=dict(size=11, color=CC.INK), row=1, col=2)
    fig.update_xaxes(title="events for that ticker", row=1, col=2)
    fig.update_yaxes(title="n tickers", row=1, col=2)

    cap = CC.caption(
        sample=f"n={n_total:,} in-scope events, {df['ticker'].nunique():,} distinct tickers",
        filters="t0_session classified from t0_ns against the same regular-session bounds as event volume",
        extra=f"max events for one ticker: {int(per_ticker.max())} ({per_ticker.idxmax()})",
    )
    CC.base_layout(fig, "E1-T1: t0 session and ticker frequency", cap, height=560, cap_y=-0.26, margin_b=180)
    CC.write(fig, "t1_univariate", "08_session_and_ticker")


def main():
    df = load()
    n_total = len(df)
    chart_06_volume(df, n_total)
    chart_07_prints_and_intertrade(df, n_total)
    chart_08_session_and_ticker(df, n_total)


if __name__ == "__main__":
    main()
