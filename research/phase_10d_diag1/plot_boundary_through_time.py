#!/usr/bin/env python
"""
Distributions and boundaries through time.

One picture per (event, kernel): the locally-normalized log-interval distribution
as a density field evolving across the session, with the argmax winner boundary
drawn on top of it and the whole candidate ladder drawn behind it.

Four stacked panels on one shared time axis:

    1  price                       (orientation)
    2  density, ABSOLUTE units     log10 seconds, reference lines 1 ms .. 10 s
    3  density, NORMALIZED units   decades of normalized log interval
    4  in-window interval count    (which frames are thin, so the field above is read honestly)

Panels 2 and 3 are the same field in two unit systems and they are not redundant:
log10(absolute) = log10(local_median) + normalized, so a boundary that is flat in
panel 3 can be moving in panel 2 and vice versa. That decomposition is exact, which
is why the absolute panel is a pure horizontal shift of the normalized one per frame
and needs no warping - just an offset before interpolation.

Diagnostic only. Nothing here selects, tunes, or applies a boundary rule. The window
is centered and therefore non-causal; every frame reads forward in time by half a
window. This is not a detector.

Usage
-----
    python plot_boundary_through_time.py \
        --frames results/phase_10d_diag1/artifacts/diag1_frames.parquet \
        --ladder results/phase_10d_diag1/artifacts/diag1_ladder.parquet \
        --tape   results/phase_10d_diag1/artifacts/diag1_tape.parquet \
        --out    results/phase_10d_diag1/charts/boundary_through_time \
        --kernel 8

    # every event on one scannable page, absolute panel only
    python plot_boundary_through_time.py --frames ... --ladder ... \
        --out ... --kernel 8 --contact

    # dark steps are selected, not an automatic flip
    python plot_boundary_through_time.py ... --theme dark

Input schema
------------
diag1_frames.parquet   one row per (event, kernel, frame, histogram bin)
    event_id         str
    kernel_min       float
    frame_idx        int
    frame_ts_ns      int64     frame centre, epoch ns
    local_median_s   float     the normalization denominator at that frame, seconds
    n_intervals      int       in-window interval count
    has_boundary     bool      did the ladder resolve at this frame
    bin_center_norm  float     decades of normalized log interval
    density          float     histogram density/count in that bin

diag1_ladder.parquet   one row per (event, kernel, frame, candidate trough)
    event_id, kernel_min, frame_idx, frame_ts_ns
    rank             int       0 = argmax winner, then descending void
    boundary_norm    float     decades
    boundary_abs_s   float     local_median_s * 10**boundary_norm
    void             float

diag1_tape.parquet     optional, one row per print
    event_id, ts_ns, price
"""

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Palette. Sequential = one hue, light -> dark (blue ramp). The overlay marks
# take a warm accent so they never read as another level of the density field.
# Dark steps are selected for the dark surface, not flipped.
# ---------------------------------------------------------------------------

BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
             "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
             "#184f95", "#104281", "#0d366b"]

THEMES = {
    "light": dict(
        surface="#fcfcfb", plane="#f9f9f7",
        ink="#0b0b0b", ink2="#52514e", muted="#898781",
        grid="#e1e0d9", axis="#c3c2b7",
        winner="#eb6834",      # categorical slot 2, orange
        ladder="#52514e",      # secondary ink - recessive, adds no hue
        seq=BLUE_RAMP,
    ),
    "dark": dict(
        surface="#1a1a19", plane="#0d0d0d",
        ink="#ffffff", ink2="#c3c2b7", muted="#898781",
        grid="#2c2c2a", axis="#383835",
        winner="#d95926",
        ladder="#c3c2b7",
        seq=BLUE_RAMP[::-1],   # dark surface: near-zero recedes to dark
    ),
}

# Human reference marks on the absolute axis. Recessive by design - these are
# chrome, not data. The question they answer at a glance: does anything in this
# field ever reach a timescale a person could act on.
REF_LINES_S = [(1e-6, "1 us"), (1e-3, "1 ms"), (1e-2, "10 ms"),
               (1e-1, "100 ms"), (1.0, "1 s"), (10.0, "10 s")]

ABS_LO, ABS_HI, GRID_N = -9.0, 2.0, 240      # log10 seconds


def global_bounds(frames):
    """One y-range for every chart in the run, computed across all events.

    Cropping each event to its own data makes the events look alike and hides
    exactly what the run is for: whether one event's boundary sits at a
    different absolute scale from another's. Every per-event figure and every
    contact-sheet cell is drawn on this one range so positions are comparable
    by eye, cell to cell, page to page.
    """
    lm = frames["local_median_s"].to_numpy(float)
    ok = np.isfinite(lm) & (lm > 0)
    b = frames["bin_center_norm"].to_numpy(float)
    abs_v = b[ok] + np.log10(lm[ok])
    pad = 0.45
    return dict(
        abs_lo=float(np.nanmin(abs_v)) - pad, abs_hi=float(np.nanmax(abs_v)) + pad,
        nrm_lo=float(np.nanmin(b)) - pad, nrm_hi=float(np.nanmax(b)) + pad,
    )


def seq_colorscale(steps):
    n = len(steps) - 1
    return [[i / n, c] for i, c in enumerate(steps)]


# ---------------------------------------------------------------------------
# Field construction
# ---------------------------------------------------------------------------

def build_field(fr, y_grid, shift=None):
    """Interpolate each frame's density profile onto a common y grid.

    fr     : frames for one (event, kernel), long form
    y_grid : common vertical grid
    shift  : per-frame offset added to bin centres before interpolation.
             None for the normalized panel; log10(local_median_s) for absolute.

    Each column is max-normalized so a faint mode in a quiet stretch is as
    visible as a tall one in a busy stretch. Without this the picture shows
    activity, not shape - which is the failure mode of every density-through-time
    chart that gets read as "the distribution moved".
    """
    frames = np.sort(fr["frame_idx"].unique())
    Z = np.full((len(y_grid), len(frames)), np.nan)
    for j, fi in enumerate(frames):
        g = fr[fr["frame_idx"] == fi]
        if g.empty:
            continue
        x = g["bin_center_norm"].to_numpy(float)
        d = g["density"].to_numpy(float)
        order = np.argsort(x)
        x, d = x[order], d[order]
        if shift is not None:
            x = x + float(shift.get(fi, np.nan))
            if not np.isfinite(x).all():
                continue
        col = np.interp(y_grid, x, d, left=np.nan, right=np.nan)
        m = np.nanmax(col) if np.isfinite(col).any() else np.nan
        if m and np.isfinite(m) and m > 0:
            col = col / m
        Z[:, j] = col
    return frames, Z


def add_heatmap(fig, row, x, y, Z, t, cbar_y, cbar_title, ytitle, hover_unit,
                showscale=True):
    """One colorbar for the figure: both panels are the same field on the same
    0-1 scale, so a second bar is chrome that says nothing."""
    fig.add_trace(
        go.Heatmap(
            x=x, y=y, z=Z, showscale=showscale,
            colorscale=seq_colorscale(t["seq"]),
            zmin=0, zmax=1,
            hovertemplate=(f"%{{x}}<br>{hover_unit}: %{{y:.2f}}"
                           "<br>density %{z:.2f}<extra></extra>"),
            colorbar=dict(
                title=dict(text=cbar_title, font=dict(size=10, color=t["ink2"])),
                len=0.28, y=cbar_y, thickness=10, outlinewidth=0,
                tickfont=dict(size=9, color=t["muted"]),
            ),
        ),
        row=row, col=1,
    )
    fig.update_yaxes(title_text=ytitle, row=row, col=1)


def add_overlays(fig, row, lad, ycol, t, show_legend):
    """Ladder behind, winner in front. Void is carried by marker size, so the
    ranking is never on colour alone."""
    losers = lad[lad["rank"] > 0]
    if not losers.empty:
        v = losers["void"].to_numpy(float)
        vmin, vmax = np.nanmin(v), np.nanmax(v)
        size = 4 + 6 * ((v - vmin) / (vmax - vmin) if vmax > vmin else np.zeros_like(v))
        fig.add_trace(
            go.Scattergl(
                x=losing_x(losers), y=losers[ycol], mode="markers",
                name="candidate troughs",
                marker=dict(color=t["ladder"], size=size, opacity=0.45,
                            line=dict(width=0)),
                customdata=np.stack([losers["rank"], losers["void"]], axis=-1),
                hovertemplate=("%{x}<br>rank %{customdata[0]:.0f}"
                               "<br>void %{customdata[1]:.3f}"
                               "<br>%{y:.2f}<extra></extra>"),
                showlegend=show_legend, legendgroup="ladder",
            ),
            row=row, col=1,
        )
    win = lad[lad["rank"] == 0].sort_values("frame_ts_ns")
    fig.add_trace(
        go.Scattergl(
            x=pd.to_datetime(win["frame_ts_ns"]), y=win[ycol],
            mode="lines", name="argmax boundary",
            line=dict(color=t["winner"], width=2),
            customdata=win["void"],
            hovertemplate="%{x}<br>boundary %{y:.2f}<br>void %{customdata:.3f}<extra></extra>",
            showlegend=show_legend, legendgroup="winner",
        ),
        row=row, col=1,
    )


def losing_x(losers):
    return pd.to_datetime(losers["frame_ts_ns"])


def shade_thin(fig, rows, x, n, t, floor=30):
    """Wash the frames whose window holds too little data to trust the shape.

    Kept visible rather than blanked: a thin frame still shows something, and
    masking it would hide how much of the session is thin. The wash is the
    caveat, drawn on the picture instead of left in a footnote."""
    thin = (n.to_numpy() < floor)
    if not thin.any():
        return 0
    runs, i = [], 0
    while i < len(thin):
        if thin[i]:
            j = i
            while j + 1 < len(thin) and thin[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    col = "rgba(137,135,129,0.30)"
    for a, b in runs:
        x0 = x.iloc[a]
        x1 = x.iloc[min(b + 1, len(x) - 1)]
        for r in rows:
            fig.add_vrect(x0=x0, x1=x1, row=r, col=1, line_width=0,
                          fillcolor=col, layer="above")
    return int(thin.sum())


# ---------------------------------------------------------------------------
# Per-event figure
# ---------------------------------------------------------------------------

def event_figure(ev, kern, fr, lad, tape, t, gb):
    fr = fr.sort_values(["frame_idx", "bin_center_norm"])
    meta = (fr.groupby("frame_idx")
              .agg(ts=("frame_ts_ns", "first"),
                   lm=("local_median_s", "first"),
                   n=("n_intervals", "first"))
              .sort_index())
    x = pd.to_datetime(meta["ts"])

    y_abs = np.linspace(gb["abs_lo"], gb["abs_hi"], GRID_N)
    shift = {i: math.log10(v) for i, v in meta["lm"].items() if v and v > 0}
    _, Z_abs = build_field(fr, y_abs, shift=shift)

    y_nrm = np.linspace(gb["nrm_lo"], gb["nrm_hi"], GRID_N)
    _, Z_nrm = build_field(fr, y_nrm, shift=None)

    have_tape = tape is not None and not tape.empty
    rows = 4
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.035,
        row_heights=[0.13, 0.35, 0.35, 0.10],
        subplot_titles=(
            "price",
            "distribution and boundaries — absolute interval",
            "distribution and boundaries — normalized",
            "in-window intervals per frame",
        ),
    )

    if have_tape:
        fig.add_trace(
            go.Scattergl(x=pd.to_datetime(tape["ts_ns"]), y=tape["price"],
                         mode="lines", line=dict(color=t["ink2"], width=1),
                         name="price", showlegend=False,
                         hovertemplate="%{x}<br>%{y}<extra></extra>"),
            row=1, col=1)
    fig.update_yaxes(title_text="price", row=1, col=1)

    add_heatmap(fig, 2, x, y_abs, Z_abs, t, 0.55,
                "density<br>(per-frame<br>max = 1)", "log₁₀ seconds", "log₁₀ s",
                showscale=True)
    # crop the absolute axis to where the field actually lives; the full
    # -9..2 grid exists so every event shares a mapping, not so every event
    # shows nine empty decades
    fig.update_yaxes(range=[gb["abs_lo"], gb["abs_hi"]], row=2, col=1)
    fig.update_yaxes(range=[gb["nrm_lo"], gb["nrm_hi"]], row=3, col=1)
    add_overlays(fig, 2, lad.assign(_y=np.log10(lad["boundary_abs_s"].clip(lower=1e-12)))
                 .rename(columns={"_y": "y_abs"}), "y_abs", t, show_legend=True)

    lo_v, hi_v = gb["abs_lo"], gb["abs_hi"]
    for sec, label in REF_LINES_S:
        yv = math.log10(sec)
        if not (lo_v - 0.4 <= yv <= hi_v + 0.4):
            continue
        fig.add_hline(y=yv, row=2, col=1,
                      line=dict(color=t["grid"], width=1, dash="dot"))
        fig.add_annotation(row=2, col=1, x=x.iloc[-1], y=yv, text=label,
                           showarrow=False, xanchor="left", yanchor="middle",
                           xshift=4, font=dict(size=9, color=t["muted"]))

    add_heatmap(fig, 3, x, y_nrm, Z_nrm, t, 0.28,
                "", "decades (normalized)", "decades", showscale=False)
    add_overlays(fig, 3, lad, "boundary_norm", t, show_legend=False)
    n_thin = shade_thin(fig, (2, 3), x, meta["n"], t)

    fig.add_trace(
        go.Scattergl(x=x, y=meta["n"], mode="lines",
                     line=dict(color=t["muted"], width=1),
                     name="in-window intervals", showlegend=False,
                     hovertemplate="%{x}<br>%{y} intervals<extra></extra>"),
        row=4, col=1)
    fig.update_yaxes(title_text="n", row=4, col=1)

    thin = n_thin
    fig.update_layout(
        title=dict(
            text=(f"<b>{ev}</b> · {kern:g}-min kernel · "
                  f"{len(meta)} frames, {thin} thin (&lt;30 intervals, washed grey)<br>"
                  "<sup>Diagnostic. No cutoff applied, no rule adopted. "
                  "Centered window — non-causal, not a detector.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=1000, hovermode="x unified",
        paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.03, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=70, r=90, t=95, b=45),
    )
    fig.update_xaxes(showgrid=False, linecolor=t["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:4]:
        a.font.update(size=11, color=t["ink2"])
        a.update(x=0, xanchor="left")
    return fig


# ---------------------------------------------------------------------------
# Contact sheet - every event's absolute panel on one scannable page
# ---------------------------------------------------------------------------

def contact_figure(kern, frames, ladder, t, gb, ncols=3):
    evs = sorted(frames["event_id"].unique())
    nrows = math.ceil(len(evs) / ncols)
    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=evs,
                        vertical_spacing=0.045, horizontal_spacing=0.035)
    y_abs = np.linspace(gb["abs_lo"], gb["abs_hi"], 160)

    for k, ev in enumerate(evs):
        r, c = k // ncols + 1, k % ncols + 1
        fr = frames[frames["event_id"] == ev].sort_values(["frame_idx", "bin_center_norm"])
        if fr.empty:
            continue
        meta = (fr.groupby("frame_idx")
                  .agg(ts=("frame_ts_ns", "first"), lm=("local_median_s", "first"))
                  .sort_index())
        shift = {i: math.log10(v) for i, v in meta["lm"].items() if v and v > 0}
        _, Z = build_field(fr, y_abs, shift=shift)
        x = pd.to_datetime(meta["ts"])
        fig.add_trace(go.Heatmap(x=x, y=y_abs, z=Z, zmin=0, zmax=1,
                                 colorscale=seq_colorscale(t["seq"]),
                                 showscale=(k == 0),
                                 colorbar=dict(len=0.25, y=0.88, thickness=9,
                                               outlinewidth=0,
                                               tickfont=dict(size=8, color=t["muted"])),
                                 hovertemplate="%{x}<br>log₁₀ s %{y:.2f}<extra></extra>"),
                      row=r, col=c)
        win = (ladder[(ladder["event_id"] == ev) & (ladder["rank"] == 0)]
               .sort_values("frame_ts_ns"))
        if not win.empty:
            fig.add_trace(
                go.Scattergl(x=pd.to_datetime(win["frame_ts_ns"]),
                             y=np.log10(win["boundary_abs_s"].clip(lower=1e-12)),
                             mode="lines", line=dict(color=t["winner"], width=1.5),
                             showlegend=False, hoverinfo="skip"),
                row=r, col=c)
        for sec, _ in [(1e-3, ""), (1e-1, ""), (1.0, "")]:
            fig.add_hline(y=math.log10(sec), row=r, col=c,
                          line=dict(color=t["grid"], width=1, dash="dot"))

    fig.update_layout(
        title=dict(text=(f"<b>Boundary through time — all events, {kern:g}-min kernel</b>"
                         "<br><sup>Absolute interval. Orange = argmax boundary. "
                         "Dotted rules at 1 ms / 100 ms / 1 s. "
                         "Density max-normalized per frame.</sup>"),
                   font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=max(420, 300 * nrows), paper_bgcolor=t["plane"],
        plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=10, color=t["ink2"]),
        margin=dict(l=55, r=70, t=100, b=40), showlegend=False)
    fig.update_xaxes(showgrid=False, linecolor=t["axis"], tickfont=dict(size=8))
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"],
                     title_text="log₁₀ s", title_font=dict(size=9),
                     tickfont=dict(size=8))
    fig.update_yaxes(range=[gb["abs_lo"], gb["abs_hi"]])
    for a in fig.layout.annotations:
        a.font.update(size=10, color=t["ink2"])
    return fig


# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", required=True)
    p.add_argument("--ladder", required=True)
    p.add_argument("--tape", default=None)
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--kernel", type=float, default=8.0)
    p.add_argument("--events", default=None, help="comma-separated subset")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--contact", action="store_true",
                   help="also write the all-events contact sheet")
    p.add_argument("--plotlyjs", default="directory",
                   choices=["directory", "inline"],
                   help="'directory' writes one shared plotly.min.js beside the "
                        "charts; 'inline' embeds it in every file. Never CDN — "
                        "D14, the environment is offline and a CDN reference "
                        "renders a blank page.")
    args = p.parse_args()
    jsmode = True if args.plotlyjs == "inline" else "directory"

    t = THEMES[args.theme]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    frames = pd.read_parquet(args.frames)
    ladder = pd.read_parquet(args.ladder)
    frames = frames[np.isclose(frames["kernel_min"], args.kernel)]
    ladder = ladder[np.isclose(ladder["kernel_min"], args.kernel)]
    tape = pd.read_parquet(args.tape) if args.tape else None

    gb = global_bounds(frames)
    print(f"global y-range  absolute {gb['abs_lo']:.2f}..{gb['abs_hi']:.2f} log10 s"
          f"   normalized {gb['nrm_lo']:.2f}..{gb['nrm_hi']:.2f} decades"
          "   (computed over ALL events at this kernel)")

    evs = sorted(frames["event_id"].unique())
    if args.events:
        want = {e.strip() for e in args.events.split(",")}
        evs = [e for e in evs if e in want]

    for ev in evs:
        fr = frames[frames["event_id"] == ev]
        lad = ladder[ladder["event_id"] == ev]
        tp = tape[tape["event_id"] == ev] if tape is not None else None
        if fr.empty or lad.empty:
            print(f"skip {ev}: no frames or no ladder")
            continue
        fig = event_figure(ev, args.kernel, fr, lad, tp, t, gb)
        path = out / f"{ev}_k{args.kernel:g}_{args.theme}.html"
        fig.write_html(path, include_plotlyjs=jsmode, full_html=True)
        print(f"wrote {path}")

    if args.contact:
        fig = contact_figure(args.kernel, frames, ladder, t, gb)
        path = out / f"_contact_k{args.kernel:g}_{args.theme}.html"
        fig.write_html(path, include_plotlyjs=jsmode, full_html=True)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
