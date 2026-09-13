"""Chart 06 - how do all three splits compare to arm zero, side by side?

Population-level (not cross-cut by year/decile -- charts 03-05 carry that
granularity) so this chart is the one-look summary, not a replacement for the
small multiples. Per Cooper's 2026-09-13 amendment and escalation rows 2/3: no
reference line, no pass/fail shading, no ranking of the categories, both sides
of every split drawn in the same two neutral colors used throughout this phase.

Failure appearance from the contract: any visual cue (color, ordering,
annotation) that implies one split "won" -- this chart exists to let Cooper
compare, not to declare a comparison's winner.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import plotly.graph_objects as go

import chart_common as K
import t3_partitions as T3

HORIZONS = [5, 15, 30, 60]
METRICS = [("mfe_cost_mult", "MFE cost-multiple"), ("mae_cost_mult", "MAE cost-multiple")]


def population_stats(df, col, horizon, metric_key):
    out = {}
    for val, g in df.groupby(col, observed=True, dropna=True):
        out[bool(val)] = T3.describe(g[f"{metric_key}_{horizon}"])
    return out


def main() -> None:
    df, _meta = T3.build_df()
    t2 = K.load_json("t2_arm_zero_summary")

    categories = (
        [f"arm-zero D{d}" for d in range(10)]
        + ["T3a below", "T3a above", "T3b below", "T3b above", "T3c below", "T3c above"]
    )
    color_for = {}
    for d in range(10):
        color_for[f"arm-zero D{d}"] = K.AQUA
    for s in ["T3a", "T3b", "T3c"]:
        color_for[f"{s} below"] = K.ORANGE
        color_for[f"{s} above"] = K.BLUE

    fig = go.Figure()
    trace_membership: dict[tuple[int, str], list[int]] = {(h, m[0]): [] for h in HORIZONS for m in METRICS}
    y_ranges: dict[tuple[int, str], list[float]] = {}
    trace_idx = 0

    for h in HORIZONS:
        for metric_key, metric_label in METRICS:
            arm_zero_rows = t2["by_horizon_by_decile"][str(h)]
            arm_zero_by_decile = {r["decile"]: r[metric_key] for r in arm_zero_rows}
            t3a = population_stats(df, T3.SPLITS["t3a_flg_dilution_form_before_t0"], h, metric_key)
            t3b = population_stats(df, T3.SPLITS["t3b_high_turnover_above_median"], h, metric_key)
            t3c = population_stats(df, T3.SPLITS["t3c_spl_reverse_split_365d"], h, metric_key)

            stats_by_cat = {}
            for d in range(10):
                stats_by_cat[f"arm-zero D{d}"] = arm_zero_by_decile.get(d)
            stats_by_cat["T3a below"] = t3a.get(False)
            stats_by_cat["T3a above"] = t3a.get(True)
            stats_by_cat["T3b below"] = t3b.get(False)
            stats_by_cat["T3b above"] = t3b.get(True)
            stats_by_cat["T3c below"] = t3c.get(False)
            stats_by_cat["T3c above"] = t3c.get(True)

            visible = (h == 15 and metric_key == "mfe_cost_mult")
            all_vals = []
            for cat in categories:
                s = stats_by_cat.get(cat)
                if s and s.get("n", 0) > 0:
                    all_vals.extend([s["p10"], s["p90"]])
                trace = K.box_from_stats([cat], [s] if s else [None], cat, color_for[cat], offsetgroup=cat)
                trace.visible = visible
                trace.showlegend = False
                fig.add_trace(trace)
                trace_membership[(h, metric_key)].append(trace_idx)
                trace_idx += 1
            if all_vals:
                lo, hi = min(all_vals), max(all_vals)
                pad = 0.08 * (hi - lo) if hi > lo else 1.0
                y_ranges[(h, metric_key)] = [lo - pad, hi + pad]

    def visibility_mask(h, metric_key):
        target = set(trace_membership[(h, metric_key)])
        return [i in target for i in range(trace_idx)]

    horizon_buttons = [
        dict(label=f"{h} min", method="update",
             args=[{"visible": visibility_mask(h, "mfe_cost_mult")},
                   {"yaxis.range": y_ranges.get((h, "mfe_cost_mult"), [0, 1])}])
        for h in HORIZONS
    ]
    metric_buttons = [
        dict(label=label, method="update",
             args=[{"visible": visibility_mask(15, key)},
                   {"yaxis.range": y_ranges.get((15, key), [0, 1])}])
        for key, label in METRICS
    ]

    fig.update_layout(
        updatemenus=[
            dict(type="buttons", direction="right", x=0.0, y=1.16, xanchor="left",
                 buttons=horizon_buttons, showactive=True),
            dict(type="buttons", direction="right", x=0.45, y=1.16, xanchor="left",
                 buttons=metric_buttons, showactive=True),
        ],
    )
    fig.add_annotation(text="horizon:", x=-0.02, y=1.16, xref="paper", yref="paper",
                       showarrow=False, xanchor="right", font=dict(size=10))
    fig.add_annotation(text="metric:", x=0.43, y=1.16, xref="paper", yref="paper",
                       showarrow=False, xanchor="right", font=dict(size=10))
    fig.update_yaxes(title_text="cost-multiple", range=y_ranges.get((15, "mfe_cost_mult"), [0, 1]))
    fig.update_xaxes(title_text="arm zero (by price decile) and each split's two sides", tickangle=-45)

    cap = K.caption(
        sample="Full P0-covered population, aggregated (not cross-cut by year/decile -- "
               "see charts 03-05 for that granularity).",
        filters="Arm zero = detection-price decile alone, no fundamental data. T3a/T3b/T3c = "
                "each split's two sides, population-aggregate.",
        extra="Deliberately no reference line, no pass/fail shading, no ranking. Both sides of<br>"
              "        every split share the same two colors (orange=below, blue=above)<br>"
              "        throughout this phase; arm-zero deciles are a third neutral color, not<br>"
              "        ordered by outcome. Read this chart to compare, not to find a winner<br>"
              "        (Cooper's 2026-09-13 amendment; escalation rows 2/3).",
    )
    K.base_layout(fig, "06 · All splits vs. arm zero — one-look comparison, no ranking",
                  cap, height=740, width=1180, cap_y=-0.48, margin_b=260)
    fig.update_layout(margin_t=130, showlegend=False)
    K.write(fig, "06_all_splits_summary")


if __name__ == "__main__":
    main()
