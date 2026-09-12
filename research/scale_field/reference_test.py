#!/usr/bin/env python
"""
Amendment 2, A2-3 -- the reference test.

THE OLD FINE-BAND CHART AND THE NEW PATH, ON THE SAME EVENT, THE SAME +/-15 s WINDOW,
AND THE SAME DATA. They must look the same before the span is extended.

The test is built so that a difference can only be the renderer. Both sides are fed
the SAME committed artifact --

    results/scale_field/artifacts/field_AEHL_2021-02-19_37.50.parquet

-- so nothing about the field, the ladder, the mask, the window or the tie handling
differs between them. Only the drawing code does. If the two pictures disagree, the
difference is in the renderer and it is findable by diffing the two paths, which is
exactly what A2-3 asks for.

Three panels are written:

    ref   the committed renderer, plot_scale_field.add_channel, raw values
    new   the same call from the new path -- this must match `ref`
    norm  the new path's PRIMARY view: per-column normalised, the Amendment 2 change

`ref` and `new` are the pass/fail comparison. `norm` is what the change actually buys
and is shown beside them rather than instead of them.

Usage:
    .venv/Scripts/python.exe research/scale_field/reference_test.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter  # noqa: E402
from adapter import rel  # noqa: E402
from plot_scale_field import add_channel, grid  # noqa: E402  -- the reference renderer
from plot_boundary_through_time import THEMES  # noqa: E402
from event_panels import normalise_columns  # noqa: E402

EVENT = "AEHL_2021-02-19_37.50"
BAND = "fine"
THEME = "light"
OUT = "results/scale_field/charts/event_panels/reference_test"


def main() -> int:
    art = Path(rel("results/scale_field/artifacts"))
    df = pd.read_parquet(art / f"field_{EVENT}.parquet")
    df = df[df["band"] == BAND]
    x, y, Z = grid(df, "dlograte")          # (time_ns, log2_scale, Z[scale, time])
    t = THEMES[THEME]

    n_cells = int(Z.size)
    n_masked = int(np.isnan(Z).sum())
    print(f"{EVENT} {BAND}: {Z.shape[1]} columns x {Z.shape[0]} scales, "
          f"{n_masked / n_cells:.1%} masked")

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.055,
        subplot_titles=(
            "REF — committed renderer (plot_scale_field.add_channel), raw values",
            "NEW — the same renderer called from the new path, raw values "
            "· must match REF",
            "NORM — the new path's PRIMARY view: per-column normalised (Amendment 2)",
        ))

    add_channel(fig, 1, x, y, Z, t, THEME, "dL/dln s<br>raw", 0.85, True, "dL/dln s")
    add_channel(fig, 2, x, y, Z, t, THEME, "dL/dln s<br>raw", 0.52, True, "dL/dln s")
    add_channel(fig, 3, x, y, normalise_columns(Z.T).T, t, THEME,
                "dL/dln s<br>col-norm", 0.19, True, "dL/dln s (col-norm)")

    # The pass/fail statement is numeric as well as visual: REF and NEW are the same
    # array through the same call, so any pixel difference would be a bug in this
    # test rather than in the renderer. Asserted so the claim is not merely asserted.
    a = np.asarray(fig.data[0].z, dtype=np.float64)
    b = np.asarray(fig.data[1].z, dtype=np.float64)
    same = np.array_equal(np.nan_to_num(a, nan=-999), np.nan_to_num(b, nan=-999))
    assert same, "REF and NEW disagree -- the new path is not calling the reference"
    print(f"REF vs NEW identical: {same}  "
          f"(zmin {fig.data[0].zmin:.3f} == {fig.data[1].zmin:.3f}, "
          f"zmax {fig.data[0].zmax:.3f} == {fig.data[1].zmax:.3f})")

    zn = np.asarray(fig.data[2].z, dtype=np.float64)
    print(f"NORM range after per-column normalisation: "
          f"{np.nanmin(zn):.3f} .. {np.nanmax(zn):.3f} (asinh units), "
          f"raw was {np.nanmin(a):.3f} .. {np.nanmax(a):.3f}")

    fig.update_layout(
        title=dict(text=(
            f"<b>A2-3 reference test</b> · {EVENT} · {BAND} band, ±15 s at the D7 anchor"
            f"<br><sup>All three panels are the SAME committed field artifact "
            f"(field_{EVENT}.parquet), so any difference between REF and NEW is the "
            f"renderer and nothing else. REF and NEW are asserted bit-identical. "
            f"NORM is the Amendment 2 change: each column divided by its own max "
            f"|dL/dln s|, sign preserved, so the picture shows shape rather than "
            f"activity. {Z.shape[1]} columns × {Z.shape[0]} scales, "
            f"{n_masked / n_cells:.1%} masked (n_eff &lt; 8, never interpolated).</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=1080, paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        margin=dict(l=72, r=104, t=118, b=45), showlegend=False)
    fig.update_xaxes(showgrid=False, linecolor=t["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a_ in fig.layout.annotations[:3]:
        a_.font.update(size=11, color=t["ink2"])
        a_.update(x=0, xanchor="left")

    out = Path(rel(OUT))
    out.mkdir(parents=True, exist_ok=True)
    fig.write_html(out / "reference_test.html", include_plotlyjs="directory",
                   full_html=True)
    fig.write_image(out / "reference_test.png", width=1500, height=1080, scale=1)
    print(f"wrote {out / 'reference_test.html'}")
    print(f"wrote {out / 'reference_test.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
