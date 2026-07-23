"""
Phase 6 T5 - Chart 01: volume concentration. x=session-time share,
y=cum volume share; pooled median + IQR band; faceted by momentum_pct
decile. Per Chart Contract: failure mode is curves hugging the diagonal
(no concentration) or a single step at t=0 (opening-print artifact -
cross-check chart 05... here, chart 04's with/without-minute-0 overlay).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_6.chart_common import EVENT_KEYS, pooled_curve_by_group, config_hash

CONCENTRATION = "results/phase_6/artifacts/concentration_curves.parquet"
EVENT_INDEX = "results/phase_6/artifacts/event_index.parquet"
OUT_HTML = "results/phase_6/charts/01_volume_concentration.html"


def build(value_col="volume_share", title="Volume concentration", out_html=OUT_HTML):
    concentration = pd.read_parquet(CONCENTRATION)
    events = pd.read_parquet(EVENT_INDEX)[EVENT_KEYS + ["decile"]]
    n_total = events["decile"].notna().sum()

    long_df = concentration.merge(events, on=EVENT_KEYS, how="inner")
    t_grid = np.linspace(0, 1, 101)
    pooled = pooled_curve_by_group(long_df, "decile", value_col, "time_share", t_grid)

    deciles = sorted(pooled.keys())
    n_cols = 5
    n_rows = int(np.ceil(len(deciles) / n_cols))
    titles = [f"Decile {int(d)} (n={pooled[d]['n']})" for d in deciles]
    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=titles,
                         shared_xaxes=True, shared_yaxes=True)

    for i, d in enumerate(deciles):
        r, c = divmod(i, n_cols)
        p = pooled[d]
        fig.add_trace(go.Scatter(x=t_grid, y=p["q75"], mode="lines", line=dict(width=0),
                                  showlegend=False, hoverinfo="skip"), row=r + 1, col=c + 1)
        fig.add_trace(go.Scatter(x=t_grid, y=p["q25"], mode="lines", line=dict(width=0),
                                  fill="tonexty", fillcolor="rgba(31,119,180,0.25)",
                                  name="IQR" if i == 0 else None, showlegend=(i == 0), hoverinfo="skip"),
                      row=r + 1, col=c + 1)
        fig.add_trace(go.Scatter(x=t_grid, y=p["median"], mode="lines", line=dict(color="rgb(31,119,180)", width=2),
                                  name="median" if i == 0 else None, showlegend=(i == 0)),
                      row=r + 1, col=c + 1)
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="gray", dash="dot", width=1),
                                  name="diagonal (no concentration)" if i == 0 else None, showlegend=(i == 0)),
                      row=r + 1, col=c + 1)

    fig.update_xaxes(title_text="session-time share", range=[0, 1])
    fig.update_yaxes(title_text=value_col.replace("_", " "), range=[0, 1])
    fig.update_layout(
        title=f"{title} - pooled median + IQR by momentum_pct decile (n_total={n_total})",
        height=200 * n_rows + 190, width=1400,
        margin=dict(b=110),
        annotations=list(fig.layout.annotations) + [dict(
            text=f"n={n_total} events | filters: D1 eligible (T1), T=0 bars only | config hash: {config_hash()}",
            xref="paper", yref="paper", x=0, y=-0.16, showarrow=False, font=dict(size=10, color="gray"))],
    )
    fig.write_html(out_html)
    print(f"wrote {out_html} (n_total={n_total}, deciles={len(deciles)})")
    return fig


if __name__ == "__main__":
    build()
