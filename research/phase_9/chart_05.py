"""
Chart 05 - is the Phase 8 time-of-day gradient real, or was it holding period?

Heatmap facet per hold; x = det_bin, y = latency, colour = median markout,
diverging about 0; cells with n < 100 hatched; n printed in every cell.

Failure appearance: the det_bin ordering is identical across hold facets ->
time-of-day is real and Phase 8 §19 stands as written.

Escalation row 11: no thin cell may be presented without hatching. Cells are
hatched off the `thin` flag in the artifact, whether or not any are thin.
Cells whose median sits on the zero atom (no print between entry and exit, so
the markout is exactly 0 by construction) are ringed - that median is fixed by
print density, not measured.
"""
from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_9 import chart_common as K
from research.phase_9 import common as C

DET_BINS = ["premarket", "0930-1000", "1000-1100", "1100-1300", "after_1300"]


def main():
    cfg = C.load_cfg()
    lats, holds = cfg["latencies"], cfg["hold_minutes"]
    j = json.load(open(f"{C.ART}/t4_axis_summary.json"))
    cells = [c for c in j["fixed_horizon_cells"] if c["era"] == "pooled" and c["det_bin"] != "ALL"]

    def get(lat, hold, db):
        return next((c for c in cells if c["latency"] == lat and c["hold"] == hold
                     and c["det_bin"] == db), None)

    vals = [c["median"] for c in cells if c["median"] is not None]
    amp = max(abs(min(vals)), abs(max(vals)))

    fig = make_subplots(rows=1, cols=len(holds), shared_yaxes=True,
                        subplot_titles=[f"hold {h} min" for h in holds],
                        horizontal_spacing=0.014)

    n_thin = n_atom = 0
    for ci, hold in enumerate(holds, start=1):
        z, txt, hov = [], [], []
        for lat in lats:
            zr, tr, hr = [], [], []
            for db in DET_BINS:
                c = get(lat, hold, db)
                if c is None or c["median"] is None:
                    zr.append(np.nan); tr.append(""); hr.append("no data")
                    continue
                zr.append(c["median"])
                mark = ""
                if c["thin"]:
                    mark += "▨"
                if c.get("median_on_zero_atom"):
                    mark += "◌"
                tr.append(f"{c['median']:+.3f}{mark}<br><span style='font-size:7px'>n={c['n']:,}</span>")
                hr.append(f"det+{lat} · hold {hold} · {db}<br>median {c['median']:+.5f}"
                          f"<br>trimmed mean simple {c['trimmed_mean_simple']:+.3%}"
                          f"<br>n={c['n']:,} · exact-zero {c['share_exact_zero']:.1%}"
                          + ("<br>THIN (n<100): no claim" if c["thin"] else "")
                          + ("<br>median sits on the zero atom" if c.get("median_on_zero_atom") else ""))
            z.append(zr); txt.append(tr); hov.append(hr)
        n_thin += sum(1 for lat in lats for db in DET_BINS
                      if (g := get(lat, hold, db)) and g["thin"])
        n_atom += sum(1 for lat in lats for db in DET_BINS
                      if (g := get(lat, hold, db)) and g.get("median_on_zero_atom"))
        fig.add_trace(go.Heatmap(
            z=z, x=DET_BINS, y=[f"det+{l}" for l in lats],
            colorscale=K.DIVERGING, zmid=0, zmin=-amp, zmax=amp,
            text=txt, texttemplate="%{text}", textfont=dict(size=9),
            customdata=hov, hovertemplate="%{customdata}<extra></extra>",
            showscale=(ci == len(holds)),
            colorbar=dict(title=dict(text="median<br>markout", side="right"),
                          thickness=12, len=0.62, x=1.012)), row=1, col=ci)

    title = ("05 · Axis separation: median markout by detection bin × latency, faceted by hold<br>"
             "<sub>entry = det + latency, exit = entry + hold · hold is CONSTANT within each facet, "
             "so latency and holding period are separated</sub>")
    cap = K.caption(
        "detection universe n=15,369, eras pooled",
        "entry and exit both on T0 and defined (target minute ≤ last T0 print)",
        f"▨ = thin cell, n < 100, no claim stated from it — {n_thin} of {len(lats)*len(DET_BINS)*len(holds)} cells<br>"
        f"◌ = median sits on the zero atom (no print between entry and exit, markout exactly 0 by "
        f"construction) — {n_atom} cells<br>"
        "colour diverging about 0, symmetric scale; n printed in every cell")
    for ci in range(1, len(holds) + 1):
        fig.update_xaxes(tickangle=-40, tickfont=dict(size=8.5), row=1, col=ci)
    fig.update_yaxes(title_text="entry latency", row=1, col=1)
    K.base_layout(fig, title, cap, height=600, cap_y=-0.36, margin_b=200, margin_r=115, width=1650)
    for a in fig.layout.annotations[:len(holds)]:
        a.font.size = 11
    K.write(fig, "05_axis_separation_grid")


if __name__ == "__main__":
    main()
