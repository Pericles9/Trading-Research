#!/usr/bin/env python
"""
Per-event scale-field panel charts: the tape review, applied to the scale field.

WHY THIS EXISTS. D21 closed the D9 lineage when Cooper looked at marked bursts
against the tape and they were wrong. Nothing in the scale-space arc has ever been
through that review. This produces the artifact that makes it possible, and nothing
else: no statistic is reported, no threshold is established, no timescale is claimed.
Whether the marks land is Cooper's read.

FOUR PANES, ONE SHARED X-AXIS, FULL SESSION SPAN:

    1  trades          print price against time, raw scatter
    2  offline field   dL/dln s, RATE channel, CENTRED kernel, (t, log s) heatmap
                       with s_min(t) = 2.2568/lambda(t) overlaid
    3  online field    the same statistic under the ONE-SIDED/TRAILING kernel,
                       with s_min(t) = 4.5135/lambda(t) overlaid
    4  log ITT         log10(dt) per print against time, scatter

THE TWO s_min LINES ARE DIFFERENT AND ARE NOT SHARED. A one-sided kernel keeps half
the mass, so n_eff = sqrt(pi)*s*lambda and the causal floor is EXACTLY DOUBLE the
centred one. Drawing one line across both panes is a defect; the factor of two is
asserted in test_event_panels.py rather than trusted.

THE RATE CHANNEL, NOT THE INTERVAL CHANNEL. The feasibility work established that the
event-weighted interval channel mislocates burst position by a non-constant factor
(9x and 2.3x on synthetic) while the time-weighted rate channel recovers duration to
~15%. Chart the one that localises.

THE SIGN LIVES IN ONE PLACE. scale_field.burst_on() is imported and called; the
condition is never restated here. NEGATIVE selects bursts, POSITIVE selects voids.
That inversion is on the record, which is why this module references the helper
instead of re-deriving it.

MASKING IS THE RESULT, NOT A FAILURE. Cells under n_eff >= 8 come back NaN and are
drawn as absence -- never interpolated, never given a fallback. At fine scales over a
whole session most cells are masked. The masked fraction is reported per pane.

_reduce_extremum IS NOT ENABLED. It is in the module, off by default, as a recorded
negative result: it raises the background floor as much as the signal. Render columns
are point-sampled, and the column width is stated against the kernel width so
undersampling of short features is visible rather than hidden.

Usage:
    .venv/Scripts/python.exe research/scale_field/event_panels.py --cohort
    .venv/Scripts/python.exe research/scale_field/event_panels.py --render
    .venv/Scripts/python.exe research/scale_field/event_panels.py --render --event TKR_YYYY-MM-DD_MM.MM
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter  # noqa: E402
from adapter import rel  # noqa: E402
from scale_field import (burst_on, collapse_same_timestamp, field,  # noqa: E402
                         field_onesided, intervals, s_min_for_rate, seconds_since)
from t1_lead_time import knn_rate  # noqa: E402  -- imported, not copied

CONFIG_PATH = os.path.join(REPO_ROOT, "config", "scale_field_panels.json")
COHORT_KEY = ["ticker", "event_date_canonical", "momentum_pct"]
KERNELS = ("centred", "onesided")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_hash(path: str = CONFIG_PATH) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


# --------------------------------------------------------------------------- #
# T1 -- cohort
# --------------------------------------------------------------------------- #

def build_cohort(cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Joint [p70, p80] filter on tick print count and momentum_pct, then a seeded
    draw of ten.

    PERCENTILES COME FROM THE WHOLE D1 POOL, not from the readable subset. p70 means
    the universe's p70; recomputing it after a readability filter would quietly move
    the band. The readability filter (clean_window AND trades_ingested) is applied
    AFTER the joint filter so the population size at the joint filter is reported
    unwidened, which is the number the work order's hard stop is read against.
    """
    cc = cfg["cohort"]
    pool = pd.read_parquet(rel(cfg["paths"]["pool"]))
    pool["event_date_canonical"] = pool["event_date_canonical"].astype(str)
    pool["momentum_pct"] = pool["momentum_pct"].round(2)

    pc = pool["t0_print_count"].to_numpy(float)
    mm = pool["momentum_pct"].to_numpy(float)
    p_lo, p_hi = np.percentile(pc, cc["joint_filter"]["print_count_percentiles"])
    m_lo, m_hi = np.percentile(mm, cc["joint_filter"]["momentum_pct_percentiles"])

    in_print = (pc >= p_lo) & (pc <= p_hi)
    in_mom = (mm >= m_lo) & (mm <= m_hi)
    joint = pool[in_print & in_mom].copy()

    readable = joint[joint["clean_window"].fillna(False)
                     & joint["trades_ingested"].fillna(False)].copy()

    counts = {
        "pool_n": int(len(pool)),
        "print_count_p70": float(p_lo), "print_count_p80": float(p_hi),
        "momentum_pct_p70": float(m_lo), "momentum_pct_p80": float(m_hi),
        "n_marginal_print_count": int(in_print.sum()),
        "n_marginal_momentum": int(in_mom.sum()),
        "n_joint_filter": int(len(joint)),
        "n_joint_and_readable": int(len(readable)),
        "n_dropped_by_readability": int(len(joint) - len(readable)),
    }

    floor = int(cc["hard_stop_if_population_under"])
    if counts["n_joint_filter"] < floor:
        raise SystemExit(
            f"HARD STOP (work order s3): joint-filter population "
            f"{counts['n_joint_filter']} < {floor}. Post and stop -- widening is "
            f"Cooper's call and the widened definition goes in the caption.")

    # Deterministic order BEFORE the draw. Phase 10 T1 recorded why: an unsorted pool
    # makes a seeded draw non-reproducible and it silently returned a different cohort.
    readable = readable.sort_values(COHORT_KEY, kind="mergesort").reset_index(drop=True)
    rng = np.random.default_rng(int(cc["seed"]))
    n = min(int(cc["n_draw"]), len(readable))
    idx = np.sort(rng.choice(len(readable), size=n, replace=False))
    drawn = readable.iloc[idx].copy().reset_index(drop=True)
    drawn["event_id"] = [adapter.make_event_id(r.ticker, r.event_date_canonical,
                                               r.momentum_pct)
                         for r in drawn.itertuples(index=False)]
    return attach_flags(drawn, cfg), counts


def attach_flags(d: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Join the cross-phase flags that live in phase artifacts. NEVER re-derived --
    they are the standing exceptions to A9.3 and the rule is join, do not re-derive.

    Flagged events are LABELLED, NEVER EXCLUDED (work order s3)."""
    d = d.copy()
    p = cfg["paths"]

    f9 = pd.read_parquet(rel(p["phase9_flags"])).rename(columns={"mp": "momentum_pct"})
    f9["event_date_canonical"] = f9["event_date_canonical"].astype(str)
    f9["momentum_pct"] = f9["momentum_pct"].round(2)
    g = (f9.groupby(COHORT_KEY)
           .agg(n_session_pairs=("flag_cross_session_extreme", "size"),
                n_cross_session_extreme=("flag_cross_session_extreme", "sum"))
           .reset_index())
    g["flag_cross_session_extreme"] = g["n_cross_session_extreme"] > 0
    pairs = (f9[f9["flag_cross_session_extreme"]]
             .groupby(COHORT_KEY)["session_pair"]
             .apply(lambda s: ",".join(sorted(s.astype(str)))).reset_index()
             .rename(columns={"session_pair": "cross_session_extreme_pairs"}))
    d = d.merge(g, on=COHORT_KEY, how="left").merge(pairs, on=COHORT_KEY, how="left")
    d["flag_cross_session_extreme"] = d["flag_cross_session_extreme"].fillna(False).astype(bool)
    d["n_cross_session_extreme"] = d["n_cross_session_extreme"].fillna(0).astype(int)
    d["cross_session_extreme_pairs"] = d["cross_session_extreme_pairs"].fillna("")

    cap = pd.read_parquet(rel(p["row_cap_labels"])).rename(columns={"mp": "momentum_pct"})
    cap["event_date_canonical"] = cap["event_date_canonical"].astype(str)
    cap["momentum_pct"] = cap["momentum_pct"].round(2)
    d = d.merge(cap[COHORT_KEY + ["flag_possible_row_cap"]], on=COHORT_KEY, how="left")
    d["flag_possible_row_cap"] = d["flag_possible_row_cap"].fillna(False).astype(bool)

    ix_path = rel(p["event_index_v2"])
    if os.path.exists(ix_path):
        ev = pd.read_parquet(ix_path)
        ev["event_date_canonical"] = ev["event_date_canonical"].astype(str)
        ev["momentum_pct"] = ev["momentum_pct"].round(2)
        if "flag_has_dup_prints" in ev.columns:
            d = d.merge(ev[COHORT_KEY + ["flag_has_dup_prints"]], on=COHORT_KEY, how="left")
            d["flag_has_dup_prints"] = d["flag_has_dup_prints"].fillna(False).astype(bool)
    return d


FLAG_COLS = ["flag_cross_session_extreme", "flag_possible_row_cap",
             "flag_has_dup_prints", "flag_eth_dominant_t0", "repaired_1c",
             "flag_window_calendar_bug", "flag_missing_event_day"]


def flag_list(row) -> list[str]:
    return [c for c in FLAG_COLS if c in row.index and bool(row.get(c, False))]


# --------------------------------------------------------------------------- #
# booleans -- debounce
# --------------------------------------------------------------------------- #

def spans_from_boolean(b, t) -> list[tuple[float, float]]:
    """Contiguous ON runs as (t_first, t_last) in the units of `t`."""
    b = np.asarray(b, bool)
    if not b.any():
        return []
    d = np.diff(b.astype(np.int8))
    starts = np.flatnonzero(d == 1) + 1
    ends = np.flatnonzero(d == -1)
    if b[0]:
        starts = np.r_[0, starts]
    if b[-1]:
        ends = np.r_[ends, b.size - 1]
    return [(float(t[s]), float(t[e])) for s, e in zip(starts, ends)]


def debounce_runs(b, t, s_star, merge_factor: float, min_factor: float):
    """Merge gaps shorter than `merge_factor` x the local read scale, THEN drop ON runs
    shorter than `min_factor` x the local read scale.

    NOT A TUNED PARAMETER, and not a global one either. A feature narrower than the
    kernel that produced it has not been resolved by that kernel, so an ON run shorter
    than s* is an artifact of reading a smoothed field on a grid finer than the
    smoothing. The threshold is s*, which is arithmetic.

    LOCAL, because s* spans two orders of magnitude across an extended session: the
    scale used for a run is the median s* inside that run, and for a gap the median s*
    across the gap. One global sample count would over-debounce the bursts and
    under-debounce the dead stretches -- which is the same failure as tuning, arrived
    at by accident.

    ORDER IS PART OF THE DEFINITION: merge first. Two resolved half-runs separated by
    a sub-kernel gap are one feature; dropped first, they are nothing.

    A merge NEVER extends past the first or last ON sample -- the shading may not
    claim a burst where the boolean never fired.
    """
    b = np.asarray(b, bool).copy()
    t = np.asarray(t, float)
    s_star = np.asarray(s_star, float)
    if b.size == 0 or not b.any():
        return b

    if merge_factor > 0:
        on_idx = np.flatnonzero(b)
        lo, hi = on_idx[0], on_idx[-1]
        gaps = spans_from_boolean(~b, t)
        for g0, g1 in gaps:
            k = (t >= g0) & (t <= g1)
            if not k.any():
                continue
            i0, i1 = int(np.flatnonzero(k)[0]), int(np.flatnonzero(k)[-1])
            if i0 <= lo or i1 >= hi:          # leading / trailing OFF, not a gap
                continue
            sl = s_star[k]
            sl = sl[np.isfinite(sl)]
            if sl.size == 0:
                continue
            if (g1 - g0) < merge_factor * float(np.median(sl)):
                b[k] = True

    if min_factor > 0:
        for r0, r1 in spans_from_boolean(b, t):
            k = (t >= r0) & (t <= r1)
            sl = s_star[k]
            sl = sl[np.isfinite(sl)]
            if sl.size == 0:
                b[k] = False
                continue
            if (r1 - r0) < min_factor * float(np.median(sl)):
                b[k] = False
    return b


# --------------------------------------------------------------------------- #
# T3 -- the field, per event, both kernels
# --------------------------------------------------------------------------- #

def ladder(cfg: dict) -> np.ndarray:
    """One ladder, built from the cost groups. The joins are de-duplicated so the
    ladder is continuous and each scale appears exactly once."""
    out = []
    for g in cfg["scale_ladder"]["groups"]:
        out.append(np.geomspace(g["min_seconds"], g["max_seconds"], g["n_scales"]))
    s = np.unique(np.round(np.concatenate(out), 12))
    return s


def compute_event(event_id: str, cfg: dict) -> dict:
    """Both kernels, both s_min lines, masking applied, masked fraction recorded.

    scale_field.py is REUSED UNCHANGED. The three scale groups exist only to set the
    base bin grid dt = min_scale / sigma_lo -- the estimator, its constants and its
    masks are identical across them, and BOTH KERNELS USE THE SAME SPLIT, so panes 2
    and 3 differ in the kernel and in nothing else.
    """
    fcfg = cfg["field"]
    ts, meta = adapter.load_event_prints_meta(event_id, None)
    if meta["n_prints"] < 100:
        raise SystemExit(f"{event_id}: {meta['n_prints']} prints -- nothing to draw")

    arr = collapse_same_timestamp(ts)                  # reference tie variant
    origin = int(arr[0])
    ts_s = seconds_since(arr, origin)
    ev_s, x = intervals(arr, origin=origin)

    lo_ns, hi_ns = int(meta["window_start_ns"]), int(meta["window_end_ns"])
    n_grid = int(cfg["render"]["t_grid_points"])
    grid_ns = np.linspace(lo_ns, hi_ns, n_grid).astype(np.int64)
    t_grid = (grid_ns - origin).astype(np.float64) / 1e9

    scales = ladder(cfg)
    groups = cfg["scale_ladder"]["groups"]
    fk = dict(neff_min=fcfg["neff_min"], sigma_lo=fcfg["sigma_lo"],
              edge_scales=fcfg["edge_scales"])

    out = {"event_id": event_id, "meta": meta, "origin_ns": origin,
           "grid_ns": grid_ns, "t_grid": t_grid, "scales": scales,
           "tape_ns": ts, "arrivals_ns": arr, "kernels": {}}

    for kernel in KERNELS:
        t0 = time.perf_counter()
        cols = []
        for g in groups:
            sc = scales[(scales >= g["min_seconds"] - 1e-12)
                        & (scales <= g["max_seconds"] + 1e-12)]
            fn = field_onesided if kernel == "onesided" else field
            kw = dict(fk)
            if kernel == "centred":
                kw["reduce"] = fcfg["reduce"]
            f = fn(ts_s, ev_s, x, t_grid, sc, **kw)
            cols.append((sc, f["dlograte"]))
        # assemble one (t, scale) plane; the groups tile the ladder and overlap only
        # at the joins, where the finer group's evaluation is kept.
        Z = np.full((n_grid, scales.size), np.nan)
        for sc, dlr in cols:
            j = np.searchsorted(scales, sc)
            for c, jj in enumerate(j):
                col = Z[:, jj]
                Z[:, jj] = np.where(np.isnan(col), dlr[:, c], col)
        elapsed = time.perf_counter() - t0

        lam = knn_rate(ts, grid_ns, k=int(cfg["s_min"]["knn_k"]),
                       causal=(kernel == "onesided"))
        s_min_t = s_min_for_rate(lam, neff_min=fcfg["neff_min"], kernel=kernel)

        reads = {}
        for tag, factor in (("primary", cfg["section_0_resolutions"]["b_read_scale"]
                             ["read_factor_primary"]),
                            ("overlay", cfg["section_0_resolutions"]["b_read_scale"]
                             ["read_factor_overlay"])):
            on, s_star, j = burst_on({"dlograte": Z}, scales, s_min_t, factor=factor)
            db = cfg["burst_marking"]["debounce"]
            on_db = debounce_runs(on, t_grid, s_star,
                                  merge_factor=db["merge_gap_factor"],
                                  min_factor=db["min_on_duration_factor"])
            target = factor * s_min_t
            defined = j >= 0
            reads[tag] = {
                "read_factor": float(factor),
                "on_raw": on, "on": on_db, "s_star": s_star, "j": j,
                "spans": spans_from_boolean(on_db, t_grid),
                "n_runs_raw": len(spans_from_boolean(on, t_grid)),
                "on_share_raw": float(on.mean()),
                "on_share": float(on_db.mean()),
                # the one place the read is not where the work order asks it to be,
                # and it is a data fact rather than a choice
                "ladder_floor_binds_share": float(np.mean(
                    defined & (target < scales[0]))),
                "no_scale_clears_share": float(np.mean(
                    np.isfinite(target) & ~defined)),
                "s_star_median": float(np.nanmedian(np.where(defined, s_star, np.nan))),
            }

        out["kernels"][kernel] = {
            "Z": Z, "lam": lam, "s_min_t": s_min_t, "reads": reads,
            "masked_fraction": float(np.isnan(Z).mean()),
            "seconds_elapsed": round(elapsed, 2),
            "s_min_median": float(np.nanmedian(s_min_t[np.isfinite(s_min_t)])),
        }
    return out


# --------------------------------------------------------------------------- #
# T4 -- render
# --------------------------------------------------------------------------- #

def et(ns):
    """Epoch ns -> naive America/New_York wall clock, DISPLAY ONLY. Every axis in this
    repo is read in ET; plotting the raw epoch would put an rth event under a 16:00
    label that is really 11:00 -- the confusion the D3 clock exists to prevent."""
    return (pd.to_datetime(pd.Series(np.asarray(ns, dtype="int64")), unit="ns", utc=True)
            .dt.tz_convert("America/New_York").dt.tz_localize(None))


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


NEG = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#86b6ef", "#cde2fb"]
POS = ["#fbe3cd", "#f6c9a2", "#f2a874", "#eb6834", "#c9491d", "#8f300f"]
NEUTRAL = {"light": "#f4f2ec", "dark": "#26262a"}
CBAR_TICKS = [-1, -0.5, -0.25, 0, 0.25, 0.5, 1, 2, 4, 8, 16]
BURST_COLOUR = {"centred": "#c0392b", "onesided": "#1e8449"}   # red offline, green online


def div_colorscale(lo, hi, theme, reverse=False):
    """Diverging ramp whose neutral colour lands exactly on zero, wherever zero sits.
    Symmetric would waste half its range: dL/dln s is bounded below by -1 and has a
    long positive tail."""
    if not (lo < 0 < hi):
        span = POS if lo >= 0 else NEG[::-1]
        return [[i / (len(span) - 1), c] for i, c in enumerate(span)]
    frac = (0.0 - lo) / (hi - lo)
    neg, pos = (POS[::-1], NEG[::-1]) if reverse else (NEG, POS)
    stops = [[frac * (i / (len(neg) - 1)), c] for i, c in enumerate(neg)]
    stops.append([frac, NEUTRAL[theme]])
    stops += [[frac + (1 - frac) * ((i + 1) / len(pos)), c] for i, c in enumerate(pos)]
    stops[0][0], stops[-1][0] = 0.0, 1.0
    seen, out = set(), []
    for v, c in stops:
        v = min(max(float(v), 0.0), 1.0)
        while v in seen:
            v = min(v + 1e-6, 1.0)
        seen.add(v)
        out.append([v, c])
    out.sort(key=lambda s: s[0])
    return out


def shading_trace(spans, y0, y1, colour, name, group, showlegend, visible=True):
    """All of an event's burst spans as ONE filled trace per pane rather than N shapes.

    Low opacity, and the online trace is drawn over the offline one WITHOUT hiding it:
    where they overlap the colour mixes, and that overlap is the most informative thing
    on the chart. A stack of opaque shapes would destroy exactly the comparison the
    chart is for.
    """
    if not spans:
        xs, ys = [None], [None]
    else:
        xs, ys = [], []
        for a, b in spans:
            xs += [a, a, b, b, None]
            ys += [y0, y1, y1, y0, None]
    return dict(x=xs, y=ys, fill="toself", mode="lines",
                line=dict(width=0), fillcolor=_rgba(colour, 0.16),
                name=name, legendgroup=group, showlegend=showlegend,
                hoverinfo="skip", visible=True if visible else "legendonly")


def build_figure(res: dict, row: pd.Series, cfg: dict, chash: str, theme: str):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from plot_boundary_through_time import THEMES

    t = THEMES[theme]
    ev = res["event_id"]
    scales = res["scales"]
    grid_ns = res["grid_ns"]
    y = np.log2(scales)
    rcfg = cfg["render"]

    # ---- decimate the heatmap columns (point-sample; _reduce_extremum stays off) --
    n_cols = int(rcfg["heatmap_render_columns"])
    step = max(1, len(grid_ns) // n_cols)
    ci = np.arange(0, len(grid_ns), step)
    x_hm = et(grid_ns[ci])
    col_w = float((grid_ns[ci][1] - grid_ns[ci][0]) / 1e9)
    field_w = float((grid_ns[1] - grid_ns[0]) / 1e9)

    # ---- tape ---------------------------------------------------------------
    tape = adapter.load_event_tape(ev, None)
    n_tape = len(tape)
    cap = int(rcfg["tape_max_points"])
    stride = max(1, int(np.ceil(n_tape / cap)))
    tp = tape.iloc[::stride]
    # log ITT from the COLLAPSED arrivals -- the same series the field is built on, so
    # every interval is strictly positive and the log is defined without an imputed value
    arr = res["arrivals_ns"]
    itt = np.log10(np.diff(arr).astype(np.float64) * 1e-9)
    itt_ns = arr[1:]
    istride = max(1, int(np.ceil(len(itt) / cap)))

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.18, 0.31, 0.31, 0.20],
        subplot_titles=(
            "1 — trades: print price",
            "2 — OFFLINE field: dL/dln s, rate channel, CENTRED kernel "
            "· black line = s_min = 2.2568/λ",
            "3 — ONLINE field: dL/dln s, rate channel, ONE-SIDED (trailing) kernel "
            "· black line = s_min = 4.5135/λ (exactly double)",
            "4 — log₁₀ inter-trade interval per print",
        ),
    )

    fig.add_trace(go.Scattergl(
        x=et(tp["ts_ns"]), y=tp["price"], mode="markers",
        marker=dict(size=2, color=t["ink2"], opacity=0.55),
        name="price", showlegend=False,
        hovertemplate="%{x}<br>%{y}<extra></extra>"), row=1, col=1)

    for r, kernel in ((2, "centred"), (3, "onesided")):
        K = res["kernels"][kernel]
        Z = K["Z"][ci, :].T
        v = Z[np.isfinite(Z)]
        lo, hi = (float(v.min()), float(v.max())) if v.size else (-1.0, 1.0)
        A = np.arcsinh(Z)
        ticks = [tv for tv in CBAR_TICKS if lo <= tv <= hi]
        fig.add_trace(go.Heatmap(
            x=x_hm, y=y, z=np.round(A, 4), zmin=float(np.arcsinh(lo)),
            zmax=float(np.arcsinh(hi)),
            colorscale=div_colorscale(float(np.arcsinh(lo)), float(np.arcsinh(hi)),
                                      theme, reverse=True),
            hovertemplate="%{x}<br>scale 2^%{y:.2f} s<br>dL/dln s (asinh) "
                          "%{z:.3f}<extra></extra>",
            colorbar=dict(title=dict(text="dL/dln s<br>(asinh)",
                                     font=dict(size=9, color=t["ink2"])),
                          len=0.28, y=0.585 if r == 2 else 0.265, thickness=9,
                          outlinewidth=0, tickmode="array",
                          tickvals=[float(np.arcsinh(tv)) for tv in ticks],
                          ticktext=[f"{tv:g}" for tv in ticks],
                          tickfont=dict(size=8, color=t["muted"])),
            showscale=True), row=r, col=1)

        sm = K["s_min_t"]
        ys = np.where(np.isfinite(sm) & (sm > 0), np.log2(np.maximum(sm, 1e-12)), np.nan)
        ys = np.where((ys >= y.min()) & (ys <= y.max()), ys, np.nan)
        fig.add_trace(go.Scattergl(
            x=et(grid_ns), y=ys, mode="lines",
            line=dict(color=t["ink"], width=1.4), showlegend=False,
            name=f"s_min {kernel}",
            hovertemplate="%{x}<br>s_min 2^%{y:.2f} s<extra></extra>"), row=r, col=1)
        fig.update_yaxes(title_text="log₂ kernel scale (s)", row=r, col=1,
                         range=[float(y.min()), float(y.max())])

    fig.add_trace(go.Scattergl(
        x=et(itt_ns[::istride]), y=itt[::istride], mode="markers",
        marker=dict(size=2, color=t["muted"], opacity=0.45),
        name="log ITT", showlegend=False,
        hovertemplate="%{x}<br>log₁₀ Δt = %{y:.2f}<extra></extra>"), row=4, col=1)
    fig.update_yaxes(title_text="log₁₀ Δt (s)", row=4, col=1)
    fig.update_yaxes(title_text="price", row=1, col=1)

    # ---- shading, all four panes, shared x -----------------------------------
    price = tp["price"].to_numpy(float)
    pane_y = {
        1: (float(np.nanmin(price)), float(np.nanmax(price))),
        2: (float(y.min()), float(y.max())),
        3: (float(y.min()), float(y.max())),
        4: (float(np.nanmin(itt)), float(np.nanmax(itt))),
    }
    for tag, vis in (("primary", True), ("overlay", False)):
        for kernel, label in (("centred", "offline"), ("onesided", "online")):
            rd = res["kernels"][kernel]["reads"][tag]
            spans_ns = [(res["origin_ns"] + int(a * 1e9), res["origin_ns"] + int(b * 1e9))
                        for a, b in rd["spans"]]
            spans_dt = [(et([a]).iloc[0], et([b]).iloc[0]) for a, b in spans_ns]
            f = rd["read_factor"]
            name = (f"{label} bursts ({kernel}) · read {f:g}×s_min "
                    f"· {len(spans_dt)} runs")
            group = f"{label}-{tag}"
            for r in (1, 2, 3, 4):
                tr = shading_trace(spans_dt, pane_y[r][0], pane_y[r][1],
                                   BURST_COLOUR[kernel], name, group,
                                   showlegend=(r == 1), visible=vis)
                fig.add_trace(go.Scatter(**tr), row=r, col=1)

    # ---- caption -------------------------------------------------------------
    cc = res["cohort_counts"]
    flags = flag_list(row)
    kc, ko = res["kernels"]["centred"], res["kernels"]["onesided"]
    pc, po = kc["reads"]["primary"], ko["reads"]["primary"]
    smallest = float(scales[0])
    sub = (f"tape sub-sampled 1-in-{stride} for panes 1/4 "
           f"({len(tp):,} of {n_tape:,} prints drawn; stride only — the full value "
           f"range is kept, nothing is clipped). " if stride > 1 else
           f"all {n_tape:,} prints drawn, no sub-sampling. ")
    title = (
        f"<b>{ev}</b> · scale-space field, offline vs online · "
        f"{row['t0_print_count']:,} T=0 prints · momentum {row['momentum_pct']:.2f}% "
        f"(print decile {int(row['t0_print_decile'])})"
        + (f" · <b>FLAGS: {', '.join(flags)}</b>" if flags else " · no flags")
        + "<br><sup>"
        f"<b>Cohort:</b> joint [p70,p80] on <b>tick print count</b> and momentum_pct of "
        f"the D1 universe (n={cc['pool_n']:,}); print count {cc['print_count_p70']:,.0f}"
        f"–{cc['print_count_p80']:,.0f}, momentum {cc['momentum_pct_p70']:.2f}"
        f"–{cc['momentum_pct_p80']:.2f}%. Population at the joint filter "
        f"<b>{cc['n_joint_filter']}</b> ({cc['n_joint_and_readable']} readable); "
        f"10 drawn, seed {cfg['cohort']['seed']}. "
        f"<b>event_volume is NOT used</b> — it is a spine numeric and D4 bars it; "
        f"tick-derived T=0 print count is substituted (§0a). "
        f"Config hash {chash}. "
        f"<br><b>Masked (n_eff &lt; 8, never interpolated, never given a fallback):</b> "
        f"pane 2 {kc['masked_fraction']:.1%} of cells, pane 3 {ko['masked_fraction']:.1%}. "
        f"Blank IS the result at that scale. "
        f"<b>Ladder</b> {scales[0]:g}–{scales[-1]:g} s, {len(scales)} scales at 8/octave. "
        f"<b>Widths:</b> field grid {field_w:.2f} s/pt, heatmap render column "
        f"{col_w:.1f} s, against a smallest kernel of {smallest:g} s "
        f"({col_w/smallest:.0f}× the finest kernel — short features at the bottom of "
        f"the ladder are undersampled in the IMAGE; the shading is computed on the "
        f"{field_w:.2f} s grid, not the render columns). "
        f"<br><b>Read:</b> primary {pc['read_factor']:g}×s_min "
        f"(median s* {pc['s_star_median']:.2f} s offline / {po['s_star_median']:.2f} s "
        f"online); ladder floor binds {pc['ladder_floor_binds_share']:.1%} offline / "
        f"{po['ladder_floor_binds_share']:.1%} online; no ladder scale clears the floor "
        f"on {pc['no_scale_clears_share']:.1%} / {po['no_scale_clears_share']:.1%} of the "
        f"session. The {cfg['section_0_resolutions']['b_read_scale']['read_factor_overlay']:g}"
        f"×s_min read is a legend-toggled trace, hidden by default. "
        f"<b>Debounce</b> merge gap {cfg['burst_marking']['debounce']['merge_gap_factor']:g}"
        f"×s*, min on-duration "
        f"{cfg['burst_marking']['debounce']['min_on_duration_factor']:g}×s*, local to "
        f"each run, not tuned per event: "
        f"{pc['n_runs_raw']}→{len(pc['spans'])} runs offline, "
        f"{po['n_runs_raw']}→{len(po['spans'])} online "
        f"(ON {pc['on_share']:.1%} / {po['on_share']:.1%} of the session). "
        f"<br>{sub}"
        f"Markers are uniform 2 px — at {n_tape:,} prints the count does not permit "
        f"size-scaled markers. Colour is asinh, unclipped, neutral exactly at zero; "
        f"ticks in original units; <b>warm = negative = burst-like</b>. "
        f"Rate channel, not the interval channel. "
        f"<b>No statistic is reported and no threshold is applied</b> — this is a "
        f"diagnostic render (D24/D25 closed tradeability; visible ≠ profitable)."
        "</sup>")

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=t["ink"]), x=0.005,
                   xanchor="left"),
        height=1400, hovermode="x unified",
        paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.028, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=70, r=88, t=248, b=44),
    )
    fig.update_xaxes(title_text="America/New_York wall clock (D3 extended session)",
                     row=4, col=1)
    fig.update_xaxes(showgrid=False, linecolor=t["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:4]:
        a.font.update(size=10.5, color=t["ink2"])
        a.update(x=0, xanchor="left")
    return fig


# --------------------------------------------------------------------------- #
# index
# --------------------------------------------------------------------------- #

def write_index(rows: list[dict], counts: dict, cfg: dict, chash: str, out: Path):
    head = [("event", "s"), ("ticker", "s"), ("date", "s"), ("segment", "s"),
            ("prints", "n"), ("momentum %", "n"), ("mom decile", "n"),
            ("print decile", "n"), ("masked 2 (offline)", "n"),
            ("masked 3 (online)", "n"), ("runs offline", "n"), ("runs online", "n"),
            ("ON% offline", "n"), ("ON% online", "n"), ("flags", "s")]
    body = []
    for r in rows:
        body.append([
            f'<a href="{r["file"]}">{r["event_id"]}</a>', r["ticker"], r["date"],
            r["segment"], f'{r["prints"]:,}', f'{r["momentum_pct"]:.2f}',
            str(r["momentum_decile"]), str(r["print_decile"]),
            f'{r["masked_offline"]*100:.1f}%', f'{r["masked_online"]*100:.1f}%',
            str(r["runs_offline"]), str(r["runs_online"]),
            f'{r["on_offline"]*100:.1f}%', f'{r["on_online"]*100:.1f}%',
            ", ".join(r["flags"]) or "—",
        ])
    th = "".join(f'<th data-t="{t}" onclick="S({i})">{h}</th>'
                 for i, (h, t) in enumerate(head))
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in b) + "</tr>" for b in body)
    html = f"""<!doctype html><meta charset="utf-8">
<title>scale-field event panels</title>
<style>
 body{{font:13px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b0b0b;
   background:#f9f9f7;margin:0;padding:28px 32px;}}
 h1{{font-size:19px;margin:0 0 4px;}} p{{color:#52514e;max-width:105ch;margin:6px 0;}}
 table{{border-collapse:collapse;margin-top:16px;font-size:12px;background:#fcfcfb;}}
 th,td{{padding:5px 9px;border-bottom:1px solid #e1e0d9;text-align:left;
   white-space:nowrap;}}
 th{{cursor:pointer;user-select:none;background:#f4f2ec;position:sticky;top:0;}}
 th:hover{{color:#eb6834;}} a{{color:#256abf;}} tr:hover td{{background:#f4f2ec;}}
 code{{background:#f4f2ec;padding:1px 4px;}}
</style>
<h1>Scale-field event panels — offline vs online</h1>
<p><b>The tape review, applied to the scale field.</b> D21 closed the D9 lineage when
marked bursts were read against the tape and were wrong. Nothing in the scale-space arc
has been through that review; these are the charts that make it possible. Click a
column head to sort.</p>
<p><b>Cohort.</b> Joint [p70, p80] on <b>tick print count</b> and <code>momentum_pct</code>
of the D1 universe (n = {counts['pool_n']:,}). Print count
{counts['print_count_p70']:,.0f}–{counts['print_count_p80']:,.0f}, momentum
{counts['momentum_pct_p70']:.2f}–{counts['momentum_pct_p80']:.2f}%. Population at the
joint filter <b>{counts['n_joint_filter']}</b>, of which {counts['n_joint_and_readable']}
readable (<code>clean_window AND trades_ingested</code>); <b>{len(rows)} drawn</b>, seed
{cfg['cohort']['seed']}. Flagged events are labelled, never excluded.</p>
<p><b><code>event_volume</code> is not used.</b> It is a spine numeric and D4 bars it;
A13 permits reading spine numerics only to audit the selection function, which a cohort
draw is not. Tick-derived T=0 print count is substituted (§0a) — it is the quantity the
chart actually depends on and it carries no adjustment-basis inconsistency.</p>
<p><b>Read at 1×s_min</b> (primary), with 2×s_min as a legend-toggled trace on the same
panes. The two s_min lines differ by exactly two — a one-sided kernel keeps half the
mass — and are never shared between panes. Config hash <code>{chash}</code>.</p>
<p><b>Not a measurement.</b> No statistic is reported, no threshold established, no
timescale claimed. D24 and D25 closed tradeability on cost arithmetic; bursts being
visible and bursts being profitable are different claims.</p>
<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>
<script>
let dir={{}};
function S(i){{
 const tb=document.querySelector('tbody'), rs=[...tb.rows];
 const num=document.querySelectorAll('th')[i].dataset.t==='n';
 dir[i]=!dir[i];
 const v=r=>{{const s=r.cells[i].innerText.replace(/[,%]/g,'');
   return num?parseFloat(s)||0:s.toLowerCase();}};
 rs.sort((a,b)=>{{const x=v(a),y=v(b);return (x<y?-1:x>y?1:0)*(dir[i]?1:-1);}});
 rs.forEach(r=>tb.appendChild(r));
}}
</script>
"""
    (out / "index.html").write_text(html, encoding="utf-8")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def segment_shares(ts_ns, date: str) -> dict:
    b = adapter.segment_bounds_ns(date)
    n = max(len(ts_ns), 1)
    return {k: float(((ts_ns >= lo) & (ts_ns < hi)).sum()) / n for k, (lo, hi) in b.items()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cohort", action="store_true", help="T1: draw and commit the cohort")
    p.add_argument("--render", action="store_true", help="T3/T4: compute and render")
    p.add_argument("--event", default=None, help="render one event only")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--plotlyjs", default="directory", choices=["directory", "inline"])
    args = p.parse_args()

    cfg = load_config()
    chash = config_hash()
    art = Path(rel(cfg["paths"]["out_artifacts"]))
    charts = Path(rel(cfg["paths"]["out_charts"]))
    art.mkdir(parents=True, exist_ok=True)

    cohort_pq = art / "event_panels_cohort.parquet"
    counts_js = art / "event_panels_cohort.json"

    if args.cohort or not cohort_pq.exists():
        drawn, counts = build_cohort(cfg)
        drawn.to_parquet(cohort_pq, index=False)
        # .gitignore excludes *.parquet under this folder (the field artifacts are
        # large), and the work order requires the drawn event list to be COMMITTED.
        # The CSV is the committed copy: small, diffable, and it does not push a file
        # past a deliberate ignore rule.
        drawn[COHORT_KEY + ["event_id", "t0_print_count", "t0_print_decile",
                            "coverage_class"] + [c for c in FLAG_COLS if c in drawn]
              ].to_csv(art / "event_panels_cohort.csv", index=False)
        with open(counts_js, "w", encoding="utf-8") as f:
            json.dump({"config_hash": chash, "counts": counts,
                       "seed": cfg["cohort"]["seed"],
                       "n_drawn": int(len(drawn)),
                       "event_ids": drawn["event_id"].tolist(),
                       "hard_stop_floor": cfg["cohort"]["hard_stop_if_population_under"],
                       "hard_stop_fired": False,
                       "substitution": cfg["section_0_resolutions"]["a_cohort_column"],
                       "source": "research/scale_field/event_panels.py:build_cohort",
                       "reproduce": ".venv/Scripts/python.exe research/scale_field/"
                                    "event_panels.py --cohort"}, f, indent=2)
        print(f"joint-filter population {counts['n_joint_filter']} "
              f"({counts['n_joint_and_readable']} readable) -> drew {len(drawn)}")
        for _, r in drawn.iterrows():
            print(f"  {r['event_id']:28s} prints {r['t0_print_count']:>8,} "
                  f"mom {r['momentum_pct']:6.2f}  flags {flag_list(r) or '-'}")
        if not args.render:
            return 0

    drawn = pd.read_parquet(cohort_pq)
    with open(counts_js, encoding="utf-8") as f:
        counts = json.load(f)["counts"]

    if not args.render:
        return 0

    charts.mkdir(parents=True, exist_ok=True)
    todo = drawn if args.event is None else drawn[drawn["event_id"] == args.event]
    if todo.empty:
        raise SystemExit(f"{args.event} is not in the drawn cohort")

    index_rows, summary = [], []
    for _, row in todo.iterrows():
        ev = row["event_id"]
        t0 = time.perf_counter()
        res = compute_event(ev, cfg)
        res["cohort_counts"] = counts
        fig = build_figure(res, row, cfg, chash, args.theme)
        fname = f"{ev}.html"
        fig.write_html(charts / fname,
                       include_plotlyjs=(True if args.plotlyjs == "inline" else "directory"),
                       full_html=True)

        sh = segment_shares(res["tape_ns"], row["event_date_canonical"])
        kc, ko = res["kernels"]["centred"], res["kernels"]["onesided"]
        pc, po = kc["reads"]["primary"], ko["reads"]["primary"]
        rec = {
            "event_id": ev, "ticker": row["ticker"],
            "date": row["event_date_canonical"],
            "segment": max(sh, key=sh.get),
            "segment_shares": {k: round(v, 4) for k, v in sh.items()},
            "prints": int(row["t0_print_count"]),
            "momentum_pct": float(row["momentum_pct"]),
            "print_decile": int(row["t0_print_decile"]),
            "momentum_decile": int(np.clip(
                np.searchsorted(np.percentile(
                    pd.read_parquet(rel(cfg["paths"]["pool"]))["momentum_pct"],
                    np.arange(10, 100, 10)), row["momentum_pct"]), 0, 9)),
            "masked_offline": kc["masked_fraction"],
            "masked_online": ko["masked_fraction"],
            "runs_offline": len(pc["spans"]), "runs_online": len(po["spans"]),
            "on_offline": pc["on_share"], "on_online": po["on_share"],
            "s_star_median_offline": pc["s_star_median"],
            "s_star_median_online": po["s_star_median"],
            "ladder_floor_binds_offline": pc["ladder_floor_binds_share"],
            "ladder_floor_binds_online": po["ladder_floor_binds_share"],
            "flags": flag_list(row), "file": fname,
            "seconds": round(time.perf_counter() - t0, 1),
        }
        index_rows.append(rec)
        summary.append(rec)
        print(f"{ev:28s} masked {kc['masked_fraction']:.1%}/{ko['masked_fraction']:.1%} "
              f"runs {len(pc['spans'])}/{len(po['spans'])} "
              f"ON {pc['on_share']:.1%}/{po['on_share']:.1%} "
              f"[{rec['seconds']}s]")

    if args.event is None:
        write_index(index_rows, counts, cfg, chash, charts)
        with open(art / "event_panels_render.json", "w", encoding="utf-8") as f:
            json.dump({"config_hash": chash, "theme": args.theme,
                       "n_events": len(summary), "events": summary,
                       "ladder": {"min_seconds": float(ladder(cfg)[0]),
                                  "max_seconds": float(ladder(cfg)[-1]),
                                  "n_scales": int(ladder(cfg).size)},
                       "read_factors": cfg["section_0_resolutions"]["b_read_scale"],
                       "debounce": cfg["burst_marking"]["debounce"],
                       "masking": cfg["field"]["neff_rule"],
                       "not_a_measurement": cfg["what_this_is_not"],
                       "source": "research/scale_field/event_panels.py:main",
                       "reproduce": ".venv/Scripts/python.exe research/scale_field/"
                                    "event_panels.py --render"}, f, indent=2)
        print(f"\nwrote {charts / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
