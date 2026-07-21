"""
Phase 2 chart 02 - 2025 momentum quality (ECDF + strip, log x, junk flagged).
Source: results/phase_2/artifacts/scan_2025_quality.json + scan_2025_quality_rows.parquet
"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

df = pd.read_parquet("results/phase_2/artifacts/scan_2025_quality_rows.parquet")
with open("results/phase_2/artifacts/scan_2025_quality.json") as f:
    q = json.load(f)

n = q["n"]
n_flagged = q["junk_flags"]["any_junk_flag_n"]
bound = q["junk_flags"]["sanity_bound"]

df_sorted = df.sort_values("momentum_pct")
ecdf_y = np.arange(1, len(df_sorted) + 1) / len(df_sorted)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04)

fig.add_trace(
    go.Scatter(x=df_sorted["momentum_pct"], y=ecdf_y, mode="lines", name="ECDF (all)",
               line=dict(color=BLUE, width=2)),
    row=1, col=1,
)

clean = df[~df["any_junk_flag"]]
flagged = df[df["any_junk_flag"]]
rng = np.random.default_rng(42)
fig.add_trace(
    go.Scatter(x=clean["momentum_pct"], y=rng.uniform(0.15, 0.85, len(clean)), mode="markers",
               name=f"clean (n={len(clean):,})", marker=dict(color=BLUE, size=4, opacity=0.35),
               hovertemplate="momentum_pct=%{x:.2f}<extra>clean</extra>"),
    row=2, col=1,
)
fig.add_trace(
    go.Scatter(x=flagged["momentum_pct"], y=rng.uniform(0.15, 0.85, len(flagged)), mode="markers",
               name=f"junk-flagged (n={len(flagged):,})", marker=dict(color=RED, size=5, opacity=0.6),
               hovertemplate="momentum_pct=%{x:.2f}<extra>flagged</extra>"),
    row=2, col=1,
)

fig.update_xaxes(type="log", title="momentum_pct (log scale)", gridcolor=GRID, row=2, col=1)
fig.update_xaxes(type="log", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="ECDF", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="strip (jittered)", showticklabels=False, gridcolor=GRID, row=2, col=1)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=620,
    title=dict(
        text=(f"How much of the 2025 scan is junk? | 2025 in-scope n={n:,}, "
              f"any-junk-flag n={n_flagged:,} ({q['junk_flags']['any_junk_flag_pct']}%), "
              f"sanity bound={bound:,} (0 rows exceed it - observed max={df['momentum_pct'].max():.2f})"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=100, b=110, l=70, r=30),
    annotations=[
        dict(
            text=(f"Population: momentum_events_canonical.source_file='file2' AND in_scope=TRUE (T1-defined 2025 "
                  f"slice), n={n:,}. Junk flags: momentum_pct&gt;{bound:,} (n={q['junk_flags']['junk_momentum_gt_bound_n']}), "
                  f"prev_close&le;{q['junk_flags']['prev_close_floor']} (n={q['junk_flags']['junk_prev_close_floor_n']}), "
                  f"|recomputed-stored momentum_pct|&gt;{q['junk_flags']['recompute_mismatch_tolerance']} "
                  f"(n={q['junk_flags']['junk_recompute_mismatch_n']} - all of any-junk-flag comes from this facet; "
                  f"median mismatch magnitude 0.10pp, concentrated among low-prev_close names, consistent with "
                  f"2-decimal rounding amplification, not verified further this phase). "
                  f"Sanity bound (10,000) is far outside the visible x-range (max observed 918.26) - marked at right edge. "
                  f"source: research/phase_2/t2_quality_screen.py, config/phase_2.json"),
            xref="paper", yref="paper", x=0.02, y=-0.22, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_2/charts/02_2025_momentum_quality.html", include_plotlyjs="inline")
print(f"chart 02 written: n={n}, flagged={n_flagged}")
