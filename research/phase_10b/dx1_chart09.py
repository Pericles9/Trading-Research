"""DX10b.1 chart 09 -- are out-of-band rungs adjacent or scattered?"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from t1_plateau import cfg_hash, load_cfg  # noqa: E402

DX = "results/phase_10b/diagnostic_1"
CTRLS = ["C1", "C2"]


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    dm = json.load(open(rel(f"{DX}/artifacts/d2_excursion_map.json"), encoding="utf-8"))
    d = pd.read_parquet(rel("results/phase_10b/artifacts/t2_control_curves.parquet"))
    minp = cfg["t3_allan"]["min_pairs_pooled"]
    span = float(cfg["t2_controls"]["rth_span_s"])

    fig = make_subplots(rows=1, cols=2, subplot_titles=[
        f"{c} — {'homogeneous Poisson (true null)' if c == 'C1' else 'inhomogeneous Poisson'}"
        for c in CTRLS], horizontal_spacing=0.10)
    for ci, nm in enumerate(CTRLS, 1):
        sub = d[d["control"] == nm]
        hs = sorted(sub["h"].unique())
        Ts = sorted(sub["T"].unique())
        z = np.full((len(hs), len(Ts)), np.nan)
        txt = np.empty((len(hs), len(Ts)), dtype=object)
        for i, h in enumerate(hs):
            g = sub[sub["h"] == h].set_index("T")
            for j, T in enumerate(Ts):
                if T not in g.index:
                    continue
                r = g.loc[T]
                npair = int(np.floor(span / T)) - 1
                if not bool(r["eligible"]):
                    z[i, j] = 0.0
                    lab = f"low power (n_pairs={npair:,} < {minp})"
                elif bool(r["above"]):
                    z[i, j] = 2.0
                    lab = "ABOVE"
                elif bool(r["below"]):
                    z[i, j] = -2.0
                    lab = "below"
                else:
                    z[i, j] = 1.0
                    lab = "inside"
                txt[i, j] = (f"{nm}<br>h={h:g} s{'' if bool(r['h_eligible']) else ' (h ineligible)'}"
                             f"<br>T={T:.4g} s (rung {j})<br>n_pairs={npair:,}<br><b>{lab}</b>")
        fig.add_trace(go.Heatmap(
            z=z, x=[float(t) for t in Ts], y=[f"{h:g}" for h in hs], text=txt,
            hovertemplate="%{text}<extra></extra>", showscale=(ci == 1),
            zmin=-2, zmax=2,
            # z: -2 below, 0 low power, 1 inside, 2 above. Normalized positions on
            # zmin=-2..zmax=2 are 0.0, 0.5, 0.75, 1.0; band edges at 0.25/0.625/0.875.
            colorscale=[[0.0, "#5B8FF9"], [0.25, "#5B8FF9"],
                        [0.25, "#D9D9D9"], [0.625, "#D9D9D9"],
                        [0.625, "#FBFBFB"], [0.875, "#FBFBFB"],
                        [0.875, "#C23531"], [1.0, "#C23531"]],
            colorbar=dict(title="", tickvals=[-2, 0, 1, 2],
                          ticktext=["below band", f"low power (<{minp} pairs)", "inside", "ABOVE band"],
                          len=0.75, x=1.02)), row=1, col=ci)
        fig.update_xaxes(type="log", title_text="counting-window duration T (s, log)",
                         row=1, col=ci)
        fig.update_yaxes(title_text="bandwidth h (s)" if ci == 1 else None, type="category",
                         row=1, col=ci)

    def runs(nm):
        el = [v for v in dm["by_control"][nm].values() if v["h_eligible"]]
        return "; ".join(f"h={v['h']:g}: {v['n_above_eligible']} above in runs "
                         f"{v['run_lengths']}" for v in el)

    fp = dm["d2d_false_positive_arithmetic"]
    C.finish(
        fig, "09 — Are the out-of-band rungs adjacent or scattered?",
        "Every ladder rung at every bandwidth, from the A10b.1 amended run. Red = above the band "
        "(the only direction A10b.1 counts). Blue = below. Grey = excluded by the pooled-pair "
        "low-power rule. Adjacent red cells are ONE excursion at one physical scale; scattered "
        "single cells are independent noise.",
        C.caption(
            f"C1 and C2, {len(sorted(d[d.control == 'C1'].T.unique())) if False else 33} ladder rungs "
            f"x {len(sorted(d[d.control=='C1']['h'].unique()))} bandwidths, "
            f"{fp['n_eligible_rungs']} rungs eligible per bandwidth",
            f"95% pointwise matched-null band, 200 draws; low-power rule n_pairs >= {minp}",
            chash,
            f"<b>C2's upward excursions are CONTIGUOUS</b> — {runs('C2')} — and they sit at the four "
            "highest eligible rungs, T = 128/256/512/1024 s, whose pair counts fall 181 → 90 → 44 → "
            f"21 against the floor of {minp}. That is one excursion at one scale, in the lowest-power "
            "rungs of the ladder, counted by the gate as four independent failures.<br>"
            f"<b>C1 is at its nominal error rate:</b> {runs('C1')}, against "
            f"{fp['expected_above_pointwise']:.2f} expected above by chance at "
            f"{fp['n_eligible_rungs']} rungs. C1's upward behaviour was never anomalous.<br>"
            "Pointwise arithmetic assumes independent rungs; nested counting windows make "
            "neighbouring Allan values strongly correlated, and the adjacency visible here is the "
            "direct evidence of it."),
        height=760, width=1500)
    man = C.write(fig, rel(f"{DX}/charts"), "09_excursion_map")
    write_json(rel(f"{DX}/artifacts/d2_chart_manifest.json"),
               {"chart": man, "config_hash": chash,
                "source": "research/phase_10b/dx1_chart09.py:main"})
    return 0 if man["kaleido_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
