"""
Phase 3 chart 02 - cohort temporal distribution vs. the full file1 population.
Source: results/phase_3/artifacts/classification.parquet (287 cohort)
+ a lightweight (no big-table-scan) query for the file1 in-scope population's
per-month totals, reusing the same read-only CTE pattern as T1/T3.
"""
import json

import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"

with open(PHASE_1B_CONFIG) as f:
    cfg1b = json.load(f)
prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

con = duckdb.connect(DB_PATH, read_only=True)
file1_events = con.execute(f"""
    WITH canonical AS (
        SELECT me.ticker, COALESCE(me.date, me.event_date) AS event_date_canonical,
            CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
            ic.class AS instrument_class,
            (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
            ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day
        FROM momentum_events me
        LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
        LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
          ON me.ticker = ef.ticker AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    )
    SELECT event_date_canonical FROM canonical
    WHERE source_file = 'file1'
      AND instrument_class IN ('common', 'common_adr')
      AND NOT flag_bad_denominator
      AND NOT COALESCE(flag_trades_mom_outlier, FALSE)
      AND NOT flag_missing_event_day
""").fetchdf()
con.close()

file1_events["event_date_canonical"] = pd.to_datetime(file1_events["event_date_canonical"])
file1_events["month"] = file1_events["event_date_canonical"].dt.to_period("M").astype(str)
file1_monthly = file1_events.groupby("month").size()

cohort = pd.read_parquet("results/phase_3/artifacts/classification.parquet")
cohort["month"] = cohort["event_day"].dt.to_period("M").astype(str)
cohort_monthly = cohort.groupby("month").size()

months = sorted(file1_monthly.index)
file1_vals = file1_monthly.reindex(months, fill_value=0)
cohort_vals = cohort_monthly.reindex(months, fill_value=0)
share = (cohort_vals / file1_vals.replace(0, pd.NA) * 100).fillna(0)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45], vertical_spacing=0.08)

fig.add_trace(
    go.Bar(x=months, y=share.values, name="event_day_only share (%)", marker_color=RED,
           text=[str(v) for v in cohort_vals.values], textposition="outside",
           hovertemplate="%{x}<br>share=%{y:.1f}%%<br>cohort n=%{text}<extra></extra>"),
    row=1, col=1,
)

fig.add_trace(go.Bar(x=months, y=file1_vals.values, name="file1 population (all)", marker_color="#c9c7bd"), row=2, col=1)
fig.add_trace(go.Bar(x=months, y=cohort_vals.values, name="event_day_only cohort", marker_color=RED), row=2, col=1)

fig.update_xaxes(title="event month", tickangle=45, gridcolor=GRID, row=2, col=1, dtick=3)
fig.update_yaxes(title="% of month's file1 events, event_day_only", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="raw monthly count", gridcolor=GRID, row=2, col=1)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=760, barmode="overlay",
    title=dict(
        text=(f"Are the 287 clustered in time relative to the full file1 population? | "
              f"file1 total n={len(file1_events):,}, cohort n={len(cohort):,}"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=120, l=70, r=30),
    annotations=[
        dict(
            text=("Per-month cohort n on the top panel's bars. source: research/phase_3/build_chart_02.py "
                  "(file1 population via a lightweight canonical-logic query, no full-table scan), "
                  "results/phase_3/artifacts/classification.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.20, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_3/charts/02_cohort_temporal_distribution.html", include_plotlyjs="inline")
print(f"chart 02 written: file1_n={len(file1_events)}, cohort_n={len(cohort)}, months={len(months)}")
