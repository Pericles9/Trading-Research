"""
Phase 7 chart 04 - D4 sweep hits by phase x class. Per the Chart Contract:
question is "where do spine-numeric reads live, and are any of them
load-bearing" - looks-like-this-if-wrong is any non-zero computation
segment or any universe_selection segment outside momentum_pct usage.
Both are true here, which is the point: this chart is the evidence for
the escalation-row-2/3 hard stop, not a clean-bill-of-health chart.

Status-severity color mapping (dataviz skill status palette, fixed/never
themed): computation=critical, universe_selection=serious, display_only=good.
"""
import json

import plotly.graph_objects as go

IN_PATH = "results/phase_7/artifacts/d4_retro_sweep.json"
OUT_PATH = "results/phase_7/charts/04_d4_sweep_hits.html"

PHASE_ORDER = ["0a", "0b", "0c", "1", "1b", "1c", "2", "3", "4", "5", "5a", "6", "6c", "src"]
CLASS_ORDER = ["display_only", "universe_selection", "computation"]
COLORS = {"display_only": "#0ca30c", "universe_selection": "#ec835a", "computation": "#d03b3b"}
LABELS = {"display_only": "display_only", "universe_selection": "universe_selection", "computation": "computation"}


def main():
    with open(IN_PATH) as f:
        sweep = json.load(f)

    by_phase = sweep["hits_by_phase_and_class"]
    n_total = sweep["n_hits"]

    fig = go.Figure()
    for cls in CLASS_ORDER:
        y = [by_phase[p][cls] for p in PHASE_ORDER]
        text = [str(v) if v > 0 else "" for v in y]
        fig.add_trace(go.Bar(
            x=[f"phase_{p}" for p in PHASE_ORDER], y=y, name=LABELS[cls],
            marker=dict(color=COLORS[cls], line=dict(color="#fcfcfb", width=2)),
            text=text, textposition="inside", insidetextfont=dict(color="white", size=11),
            hovertemplate=f"%{{x}}<br>{cls}: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(text=f"D4 retroactive sweep: spine-numeric-column hits by phase x class (n={n_total} hits)"),
        xaxis=dict(title="phase", tickangle=-45),
        yaxis=dict(title="hit count", dtick=1, gridcolor="#e1e0d9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
        font=dict(color="#0b0b0b"),
        height=560, width=1100,
        annotations=[dict(
            text=(f"row 2 (computation>0): TRIGGERED, n={sweep['n_hits_by_class']['computation']} | "
                  f"row 3 (universe_selection on non-momentum_pct>0): TRIGGERED, n={sweep['n_hits_by_class']['universe_selection']}<br>"
                  f"zero-hit phases (explicit zero bars): {', '.join('phase_'+p for p in PHASE_ORDER if sum(by_phase[p].values())==0)}<br>"
                  f"source: {IN_PATH}"),
            xref="paper", yref="paper", x=0, y=-0.32, showarrow=False, font=dict(size=10, color="#52514e"), align="left",
        )],
        margin=dict(b=160),
    )

    fig.write_html(OUT_PATH)
    try:
        fig.write_image(OUT_PATH.replace(".html", ".png"), scale=1.5)
    except Exception as e:
        print(f"kaleido png export failed (non-fatal, html is canonical): {e}")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
