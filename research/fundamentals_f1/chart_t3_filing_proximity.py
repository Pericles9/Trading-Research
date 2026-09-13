"""
Build F1, F1-T3g: chart the time-since-nearest-filing distribution and the form-type mix
of the nearest prior filing. One file, two stacked panels sharing no axis (distinct
metrics) -- same one-deliverable-per-task convention as F1-T1d's chart.

Palette literals copied from research/phase_9/chart_common.py's validated CAT5 set
(documented there as CVD-safe, lightness-banded, contrast-checked), matching the pattern
chart_t1_identity_quality.py already established for this build -- not a fresh import,
per that file's own note on why (avoids cross-phase module coupling for a few constants).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/chart_t3_filing_proximity.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"

OUT_HTML = f"{C.CHARTS}/t3_filing_proximity.html"


def main():
    prox = pd.read_parquet(f"{C.ART}/event_filing_proximity.parquet")
    n_total = len(prox)
    observed = prox[prox["flg_quality"] == "observed"].copy()
    n_observed = len(observed)
    quality_counts = prox["flg_quality"].value_counts().to_dict()

    lag_days = observed["flg_lag_ns"].astype("float64") / 1e9 / 86400.0
    lag_days = lag_days[lag_days > 0]  # log axis needs strictly positive; escalation row 3 already guards <= 0

    form_counts = observed["flg_last_form"].value_counts()
    top_forms = form_counts.head(12)
    other_n = form_counts.iloc[12:].sum() if len(form_counts) > 12 else 0

    fig = make_subplots(rows=2, cols=1, row_heights=[0.5, 0.5], vertical_spacing=0.16,
                         subplot_titles=(
                             f"Time from nearest prior filing to t0 (n={len(lag_days):,} observed)",
                             f"Form type of nearest prior filing (n={n_observed:,} observed)"))

    log_lag = np.log10(lag_days.values)
    fig.add_trace(go.Histogram(x=log_lag, nbinsx=60, marker_color=BLUE, name="lag"), row=1, col=1)
    tickvals = list(range(int(np.floor(log_lag.min())), int(np.ceil(log_lag.max())) + 1))
    fig.update_xaxes(title="days since nearest prior filing (log10 scale)",
                      tickvals=tickvals, ticktext=[f"{10**t:g}" for t in tickvals],
                      gridcolor=GRID, row=1, col=1)
    fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=1)

    labels = list(top_forms.index) + (["(other, n forms grouped)"] if other_n else [])
    values = list(top_forms.values) + ([other_n] if other_n else [])
    palette = [BLUE, ORANGE, AQUA, YELLOW, GREEN] * 3
    fig.add_trace(go.Bar(x=labels, y=values, marker_color=palette[:len(labels)],
                          text=values, textposition="outside", name="form"), row=2, col=1)
    fig.update_xaxes(title="form type", tickangle=-35, row=2, col=1)
    fig.update_yaxes(title="n events", gridcolor=GRID, row=2, col=1)

    n_dilution = int(prox["flg_dilution_form_before_t0"].sum())
    caption = (
        f"sample: {n_total:,} in-scope events · flg_quality: "
        + ", ".join(f"{k}={v:,}" for k, v in quality_counts.items())
        + f" · flg_dilution_form_before_t0 = TRUE for {n_dilution:,} ({n_dilution/n_total:.1%}) "
        f"· config {C.cfg_hash()} · F1-T3g"
    )
    fig.update_layout(
        title="F1-T3: filing proximity to t0",
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK),
        showlegend=False, height=900, margin=dict(t=100, b=160),
        annotations=list(fig.layout.annotations) + [
            dict(text=caption, xref="paper", yref="paper", x=0, y=-0.20, showarrow=False,
                 font=dict(size=10, color=INK2), align="left")
        ],
    )
    os.makedirs(C.CHARTS, exist_ok=True)
    fig.write_html(OUT_HTML, include_plotlyjs=True)  # D14: no CDN, embed inline
    print(f"wrote {OUT_HTML}")
    print("flg_quality:", quality_counts)
    print("top forms:\n", top_forms)


if __name__ == "__main__":
    main()
