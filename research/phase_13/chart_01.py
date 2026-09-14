"""Chart 01 - how much of the universe does P0 actually cover, and does it vary by
event year?

Minute-bar coverage (n_bars_h notna) is identical across all four horizons -- 15,763
of 20,951 events either have a bar anywhere in the [t0, t0+60] window or have none at
all (escalation row 5, LOG, fires: 75.2% < 80%). Read by year, this is not a
scattered gap: **2020-2024 are at exactly 100% minute-bar coverage; 2025 is at
exactly 0%** (5,188/5,188 events with zero bars). event_minute_bars_v2 has a hard
temporal cutoff before 2025, not a partial/random miss -- and that cutoff is exactly
what makes 15,763 equal Build F1's a102_detection_anchors.parquet row count (sum of
2020-2024's per-year counts, to the event). Round-trip-cost coverage
(event_quote_metrics_v1) follows the same pattern -- ~92-96% within 2020-2024, 0% in
2025 -- but is not a clean 100/0 split within the covered years, a second, smaller
gap layered on top of the year cutoff. Both are shown per year, not as one population
figure, because the failure mode this chart guards against is a coverage gap that is
concentrated and silently averaged away.

Failure appearance from the contract: flat 100% everywhere -- coverage gap silently
absorbed rather than measured.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import chart_common as K

HORIZONS = [5, 15, 30, 60]


def main() -> None:
    df = K.load_p0()
    years = sorted(df["event_year"].dropna().unique())

    by_year = []
    for y in years:
        g = df[df["event_year"] == y]
        row = {"year": y, "n_total": len(g), "n_cost": int(g["round_trip_cost_bp"].notna().sum())}
        for h in HORIZONS:
            row[f"n_bar_{h}"] = int(g[f"n_bars_{h}"].notna().sum())
        by_year.append(row)

    # Confirmed directly: bar coverage is identical across all 4 horizons, every year.
    flat = all(r[f"n_bar_{HORIZONS[0]}"] == r[f"n_bar_{h}"] for r in by_year for h in HORIZONS)

    fig = make_subplots(rows=1, cols=1)
    ys = [r["year"] for r in by_year]
    bar_share = [r[f"n_bar_{HORIZONS[0]}"] / r["n_total"] for r in by_year]
    cost_share = [r["n_cost"] / r["n_total"] for r in by_year]
    n_totals = [r["n_total"] for r in by_year]
    n_bars = [r[f"n_bar_{HORIZONS[0]}"] for r in by_year]
    n_costs = [r["n_cost"] for r in by_year]

    fig.add_trace(go.Bar(
        x=ys, y=bar_share, name="minute-bar coverage (event_minute_bars_v2)",
        marker_color=K.BLUE, offsetgroup="bar",
        customdata=list(zip(n_bars, n_totals)),
        hovertemplate="%{x}<br>minute-bar coverage %{y:.1%}<br>n=%{customdata[0]:,} / %{customdata[1]:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=ys, y=cost_share, name="round-trip-cost coverage (event_quote_metrics_v1)",
        marker_color=K.ORANGE, offsetgroup="cost",
        customdata=list(zip(n_costs, n_totals)),
        hovertemplate="%{x}<br>cost coverage %{y:.1%}<br>n=%{customdata[0]:,} / %{customdata[1]:,}<extra></extra>",
    ))
    fig.add_hline(y=0.80, line=dict(color=K.INK2, width=1, dash="dot"),
                  annotation_text="escalation row 5 LOG threshold (0.80) -- observation marker, not a pass/fail line",
                  annotation_font=dict(size=9, color=K.INK2), annotation_position="top left")

    total_bar_cov = sum(n_bars) / sum(n_totals)
    total_cost_cov = sum(n_costs) / sum(n_totals)
    bar_share_by_year = {r["year"]: r[f"n_bar_{HORIZONS[0]}"] / r["n_total"] for r in by_year}
    low_years = [y for y, s in bar_share_by_year.items() if s < 0.05]
    high_years = [y for y, s in bar_share_by_year.items() if s > 0.95]
    cap = K.caption(
        sample=f"Build F1 universe, n={sum(n_totals):,} events, {len(years)} event years.",
        filters="Coverage = share of events with a defined value; no cleaning or exclusion applied.",
        extra=(f"Population coverage: minute-bar {total_bar_cov:.1%} ({sum(n_bars):,}/{sum(n_totals):,}), "
               f"round-trip-cost {total_cost_cov:.1%} ({sum(n_costs):,}/{sum(n_totals):,}). This is a "
               f"temporal cutoff, not a scattered gap: {', '.join(high_years) or 'none'} sit at "
               f"~100% minute-bar coverage; {', '.join(low_years) or 'none'} sit at ~0%. "
               f"Minute-bar coverage confirmed identical across all 4 horizons (5/15/30/60 min): {flat}. "
               "Escalation row 5 (LOG) fired at T1: 75.2% population minute-bar coverage &lt; 80%."),
    )
    K.base_layout(fig, "01 · P0 coverage by event year — minute-bar and round-trip-cost sources",
                  cap, height=560, width=980, cap_y=-0.42, margin_b=150)
    fig.update_yaxes(title_text="coverage share", tickformat=".0%", range=[0, 1.05])
    fig.update_xaxes(title_text="event year")
    K.legend_inside(fig, x=0.012, y=1.14)
    fig.update_layout(barmode="group", margin_t=120)
    K.write(fig, "01_p0_coverage")


if __name__ == "__main__":
    main()
