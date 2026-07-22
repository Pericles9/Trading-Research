"""
Phase 4 chart 03 - cohort temporal distribution vs. the file1 population.
Source: results/phase_4/artifacts/classification.parquet (386 cohort)
+ results/phase_4/artifacts/reconciliation.parquet (presence_class: no-file vs partial-file)
+ a lightweight in-scope file1 population query (same CTE pattern as phase 3 chart 02).
"""
import json

import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RED = "#e34948"
ORANGE = "#eb6834"
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

cohort = pd.read_parquet("results/phase_4/artifacts/classification.parquet")
recon = pd.read_parquet("results/phase_4/artifacts/reconciliation.parquet")
cohort["mom_2dp"] = cohort["momentum_pct"].round(2)

recon_keyed = recon.set_index(["ticker", "date_parsed", "mom_2dp"])["presence_class"]
cohort = cohort.merge(
    recon[["ticker", "date_parsed", "mom_2dp", "presence_class"]],
    left_on=["ticker", "event_day", "mom_2dp"], right_on=["ticker", "date_parsed", "mom_2dp"], how="left",
)
cohort["shape"] = cohort["presence_class"].map({"trades_only": "no quotes file", "both": "quotes file, partial"}).fillna("unknown")
cohort["month"] = cohort["event_day"].dt.to_period("M").astype(str)

cohort_monthly = cohort.groupby("month").size()
months = sorted(file1_monthly.index)
file1_vals = file1_monthly.reindex(months, fill_value=0)
cohort_vals = cohort_monthly.reindex(months, fill_value=0)
share = (cohort_vals / file1_vals.replace(0, pd.NA) * 100).fillna(0)

shape_monthly = cohort.groupby(["month", "shape"]).size().unstack(fill_value=0).reindex(months, fill_value=0)
shape_color = {"no quotes file": RED, "quotes file, partial": ORANGE}

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.08)

fig.add_trace(
    go.Bar(x=months, y=share.values, name="cohort share (%)", marker_color="#7a7972",
           text=[str(v) for v in cohort_vals.values], textposition="outside",
           hovertemplate="%{x}<br>share=%{y:.1f}%%<br>cohort n=%{text}<extra></extra>", showlegend=False),
    row=1, col=1,
)

for shape in ["no quotes file", "quotes file, partial"]:
    if shape not in shape_monthly.columns:
        continue
    fig.add_trace(
        go.Bar(x=months, y=shape_monthly[shape].values, name=shape, marker_color=shape_color[shape]),
        row=2, col=1,
    )
fig.add_trace(go.Bar(x=months, y=file1_vals.values, name="file1 population (all)", marker_color="#c9c7bd", opacity=0.5), row=2, col=1)

fig.update_xaxes(title="event month", tickangle=45, gridcolor=GRID, type="category", dtick=3, row=1, col=1)
fig.update_xaxes(title="event month", tickangle=45, gridcolor=GRID, type="category", dtick=3, row=2, col=1)
fig.update_yaxes(title="% of month's file1 events, in 386 cohort", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="raw monthly count", gridcolor=GRID, row=2, col=1)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=780, barmode="overlay",
    title=dict(
        text=(f"Is the quotes-gap cohort concentrated in time? | "
              f"file1 total n={len(file1_events):,}, cohort n={len(cohort):,} "
              f"(no-file={int((cohort['shape']=='no quotes file').sum())}, partial-file={int((cohort['shape']=='quotes file, partial').sum())})"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=120, l=70, r=30),
    annotations=[
        dict(
            text=("Per-month cohort n on the top panel's bars. file1 population bar shown at 50%% opacity as a "
                  "backdrop. source: research/phase_4/build_chart_03.py (file1 population via lightweight "
                  "canonical-logic query, no full-table scan), classification.parquet, reconciliation.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.20, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_4/charts/03_cohort_temporal_distribution.html", include_plotlyjs="inline")
print(f"chart 03 written: file1_n={len(file1_events)}, cohort_n={len(cohort)}, months={len(months)}")
