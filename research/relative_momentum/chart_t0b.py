"""
R0-T0b charts: the two pictures behind the stopping gate.

01 -- the population funnel by year. D1, the gate's admissible universe, the events the
      gate was actually run on, and the events it fired on. Counts, per year, labelled.
02 -- the momentum_pct distribution of D1 against the gate's own 50% floor, which is the
      single rule that removes 10,046 of D1's 15,763 events. Distribution, not a summary:
      the floor's position inside the distribution is the whole point.

D4 note for chart 02: momentum_pct is used here as a labelled DIAGNOSTIC of a selection
boundary, which is what brief section I.2 permits and what D4's sole exception covers
(momentum_pct is the universe-selection/stratification variable). It enters no computed
quantity in this run.

Usage: .venv/Scripts/python.exe research/relative_momentum/chart_t0b.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import chart_common as K  # noqa: E402
from research.relative_momentum import common as C  # noqa: E402

MEMBERSHIP = f"{C.ART}/t0b_membership.parquet"
T0B_JSON = f"{C.ART}/t0b_overlap_join.json"


def chart_01(m: pd.DataFrame) -> str:
    g = m.groupby("year").agg(
        n_d1=("event_id", "size"),
        n_admitted=("gate_admitted", "sum"),
        n_run=("gate_run", "sum"),
        n_fired=("gate_fired", "sum"),
    ).reset_index()

    series = [
        ("D1 (in_scope, file1)", "n_d1", K.BLUE),
        ("gate lister would admit (mom ≥ 50, dated, trades present)", "n_admitted", K.ORANGE),
        ("gate was actually run on", "n_run", K.AQUA),
        ("gate fired a rising edge on", "n_fired", K.VIOLET),
    ]
    fig = go.Figure()
    for label, col, color in series:
        fig.add_bar(
            x=g["year"], y=g[col], name=label, marker_color=color,
            text=[f"{v:,}" for v in g[col]], textposition="outside",
            textfont=dict(size=10),
            hovertemplate="%{x}<br>" + label + ": %{y:,}<extra></extra>",
        )
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_yaxes(title_text="events (count)")
    fig.update_xaxes(title_text="event year")
    cap = K.caption(
        sample=f"D1 n={len(m):,} (momentum_events_canonical, in_scope = TRUE, source_file = 'file1')",
        filters="none — every D1 event is on this chart; the bars are nested subsets, not exclusions",
        extra="gate side re-implemented read-only from scanner-epg-momentum/backtest/data/loaders/"
              "trades.py::list_events and read from every per_event_summary.json under "
              "scanner-epg-momentum/backtest/results. 2020–2022 carry zero gate runs: the backtest "
              "has never been executed on any event before 2023-11-17.",
    )
    K.base_layout(fig, "T0b · D1 against the participation gate's event set, by year", cap,
                  height=680, cap_y=-0.24, margin_b=230)
    return K.write(fig, "01_population_funnel_by_year.html")


def chart_02(m: pd.DataFrame) -> str:
    mom = m["momentum_pct"].to_numpy(dtype=float)
    floor = 50.0

    # Log-spaced bins: momentum_pct is multiplicative and spans orders of magnitude
    # (CLAUDE.md: log axes where data is multiplicative — here it usually is).
    lo = max(np.nanmin(mom), 1e-3)
    hi = np.nanmax(mom)
    edges = np.geomspace(lo, hi, 61)
    cnt, _ = np.histogram(mom, bins=edges)
    centers = np.sqrt(edges[:-1] * edges[1:])
    below = cnt.copy()
    above = cnt.copy()
    below[centers >= floor] = 0
    above[centers < floor] = 0

    n_below = int((mom < floor).sum())
    n_above = int((mom >= floor).sum())

    fig = go.Figure()
    fig.add_bar(x=centers, y=below, name=f"below the gate's floor (n={n_below:,})",
                marker_color=K.rgba(K.RED, 0.85), width=np.diff(edges),
                hovertemplate="momentum_pct ≈ %{x:.1f}%<br>n = %{y:,}<extra></extra>")
    fig.add_bar(x=centers, y=above, name=f"at or above the floor (n={n_above:,})",
                marker_color=K.rgba(K.BLUE, 0.85), width=np.diff(edges),
                hovertemplate="momentum_pct ≈ %{x:.1f}%<br>n = %{y:,}<extra></extra>")
    fig.add_vline(x=floor, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_annotation(x=np.log10(floor), y=1.0, yref="paper", yanchor="bottom",
                       text="gate's min_mom_pct = 50.0", showarrow=False,
                       font=dict(size=11, color=K.INK))
    fig.update_layout(barmode="overlay", bargap=0)
    fig.update_xaxes(type="log", title_text="momentum_pct (spine, log axis) — diagnostic only, D4")
    fig.update_yaxes(title_text="events per bin (count)")
    cap = K.caption(
        sample=f"D1 n={len(m):,}; 60 log-spaced bins over [{lo:.2f}%, {hi:,.0f}%]",
        filters="none — no event is clipped or excluded; the full range including the upper tail is shown",
        extra="momentum_pct is shown as a labelled diagnostic of a selection boundary (brief I.2, D4's "
              f"sole exception) and enters no computed quantity. {n_below:,} of {len(m):,} D1 events "
              f"({n_below / len(m):.1%}) fall below the gate's own floor and are outside its universe "
              "for that reason alone.",
    )
    K.base_layout(fig, "T0b · where the gate's 50% floor cuts D1", cap,
                  height=660, cap_y=-0.26, margin_b=230)
    return K.write(fig, "02_gate_floor_against_d1_momentum.html")


def main() -> int:
    m = pd.read_parquet(os.path.join(C.REPO, MEMBERSHIP))
    out = [chart_01(m), chart_02(m)]
    C.write_json(f"{C.ART}/t0b_charts.json", {
        "task": "R0-T0b charts",
        "config_hash": C.cfg_hash(),
        "charts": out,
        "source_artifacts": [MEMBERSHIP, T0B_JSON],
    })
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
