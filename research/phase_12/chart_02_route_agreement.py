#!/usr/bin/env python
"""Chart 02 -- do the three identification routes agree? T2c / the Stage A gate.

Question: do the three identification routes agree? Route 2 contributes zero candidates by
construction (no dictionary) -- shown as its own zero-height bar, not omitted, so the reader sees
why rather than wondering where it went.

Usage: .venv/Scripts/python.exe research/phase_12/chart_02_route_agreement.py
"""
from __future__ import annotations

import json
import os

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IN_JSON = os.path.join(REPO, "results", "phase_12", "artifacts", "t2_agreement_matrix.json")
OUT = os.path.join(REPO, "results", "phase_12", "charts", "02_route_agreement.html")


def main() -> int:
    d = json.load(open(IN_JSON, encoding="utf-8"))
    ev = d["agreement_by_event"]

    labels = ["Route 1 only\n(gaps, no route-3 touch)", "Route 3 only\n(band touch, no route-1 gap)",
               "Both routes\n(same event)", "Route 2\n(zero, no dictionary)"]
    values = [ev["n_route1_only"], ev["n_route3_only"], ev["n_both"], 0]
    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#7f7f7f"]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=values, marker_color=colors,
                          text=[str(v) for v in values], textposition="outside"))
    fig.add_hline(y=d["cooper_threshold_row_10_min"], line_dash="dash", line_color="black",
                  annotation_text=f"row 10 floor: {d['cooper_threshold_row_10_min']} corroborated events needed")

    single_route_share = d["single_route_only_share_gap_level"]
    fig.update_layout(
        title="T2c/T3 -- route agreement, dev tier (event-level view; see caption for gap-level)",
        yaxis_title="n events",
        annotations=[dict(
            text=(f"Event level: {ev['n_route1_only']} route-1-only, {ev['n_route3_only']} "
                  f"route-3-only, {ev['n_both']} both (out of {ev['n_route1_events']} route-1 "
                  f"candidate-events, {d['route_3_touched_events_n']} route-3-touched events, "
                  f"{d['route_3_total_events_n']} total dev events).<br>"
                  f"Gap level (finer grain): {d['agreement_by_gap']['n_route1_gaps']} route-1 "
                  f"candidate gaps, single-route-only share = {single_route_share:.3f} -- "
                  f"ABOVE Cooper's row-11 ceiling (0.6). Only {ev['n_both']} corroborated events "
                  f"-- BELOW Cooper's row-10 floor (50). {d['route_2_note']}<br>"
                  f"Corroboration approximated at the event level (grain mismatch: route 1 is "
                  "gap-level, route 3 is minute-bar-level) -- see t2_agreement_matrix.json "
                  "grain_note. Source: results/phase_12/artifacts/t2_agreement_matrix.json"),
            xref="paper", yref="paper", x=0, y=-0.35, showarrow=False,
            align="left", font=dict(size=10),
        )],
        margin=dict(b=170),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="directory")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
