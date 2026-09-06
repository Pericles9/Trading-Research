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


def column_grid(arr_ns, lo_ns, hi_ns, k, max_points):
    """Print-indexed column edges: one column per `k` prints (Amendment 1, A1-1).

    THE REASON THIS IS THE RIGHT GRID RATHER THAN MERELY A BETTER ONE:

        column width      dt    = k / lambda(t)
        resolution floor  s_min = 2.2568 / lambda(t)
                    dt / s_min  = k / 2.2568        -- INDEPENDENT OF lambda

    so a print-indexed grid holds a constant ratio to the resolution floor everywhere
    on the tape, with no tuning and no per-event calibration. Dense stretches get
    narrow columns and dead stretches wide ones, automatically.

    THE SESSION IS NEVER TRUNCATED. The dead stretch before the first print and the
    one after the last are their own columns, so the panel always spans the full D3
    extended session even though no print falls in them.

    When `max_points` binds, k RISES for this event and the caller reports the
    achieved dt/s_min. A chart that says "columns are 7x s_min here" is honest; one
    that quietly drops the back half of the day is not.

    -> (edges_ns, centres_ns, dt_seconds, k_effective)
    """
    arr_ns = np.asarray(arr_ns, dtype=np.int64)
    n = arr_ns.size
    k_eff = float(k)
    if max_points and n / k_eff > max_points:
        k_eff = n / float(max_points)
    idx = np.unique(np.floor(np.arange(0.0, float(n), k_eff)).astype(np.int64))
    idx = idx[(idx >= 0) & (idx < n)]
    edges = np.unique(np.concatenate([[np.int64(lo_ns)], arr_ns[idx], [np.int64(hi_ns)]]))
    edges = edges[(edges >= lo_ns) & (edges <= hi_ns)]
    centres = edges[:-1] + (edges[1:] - edges[:-1]) // 2
    dt = (edges[1:] - edges[:-1]).astype(np.float64) / 1e9
    return edges, centres.astype(np.int64), dt, k_eff


def compute_event(event_id, cfg):
    """Both kernels, both s_min lines, masking applied, masked fraction recorded.

    scale_field.py is REUSED UNCHANGED -- Amendment 1 is a GRID and a RENDERING
    change; the estimator is untouched. The three scale groups exist only to set the
    base bin grid dt = min_scale / sigma_lo, and BOTH KERNELS USE THE SAME SPLIT, so
    panes 2 and 3 differ in the kernel and in nothing else.

    TWO GRIDS, and the difference between them is reported rather than blurred:
      * the EVALUATION grid, at k_eval prints per column (dt ~ 0.5 s_min), is what the
        field, the booleans and the debounce are computed on. At the render grid's
        dt = 2 s_min the debounce's 1 x s* minimum on-duration would be finer than the
        grid spacing and therefore inoperative.
      * the RENDER grid is that grid decimated by an integer stride, so render columns
        are print-indexed too and dt/s_min stays constant across the tape.
    """
    fcfg = cfg["field"]
    a1 = cfg["amendment_1"]
    cg, na = a1["column_grid"], a1["normalised_axis"]

    ts, meta = adapter.load_event_prints_meta(event_id, None)
    if meta["n_prints"] < 100:
        raise SystemExit(f"{event_id}: {meta['n_prints']} prints -- nothing to draw")

    arr = collapse_same_timestamp(ts)                  # reference tie variant
    origin = int(arr[0])
    ts_s = seconds_since(arr, origin)
    ev_s, x = intervals(arr, origin=origin)

    lo_ns, hi_ns = int(meta["window_start_ns"]), int(meta["window_end_ns"])
    edges, grid_ns, dt_eval, k_eval = column_grid(
        arr, lo_ns, hi_ns, cg["prints_per_column_eval"], cg["eval_max_points"])
    t_grid = (grid_ns - origin).astype(np.float64) / 1e9
    n_grid = grid_ns.size

    # render stride: aim for the amendment's k, then let max_columns raise it
    stride = max(1, int(round(cg["prints_per_column"] / k_eval)))
    if cg["max_columns"] and n_grid / stride > cg["max_columns"]:
        stride = int(np.ceil(n_grid / float(cg["max_columns"])))
    ci = np.arange(0, n_grid, stride)
    dtr = np.diff(grid_ns[ci]).astype(np.float64) / 1e9
    dt_render = np.append(dtr, dtr[-1]) if dtr.size else np.array([np.nan])

    scales = ladder(cfg)
    groups = cfg["scale_ladder"]["groups"]
    fk = dict(neff_min=fcfg["neff_min"], sigma_lo=fcfg["sigma_lo"],
              edge_scales=fcfg["edge_scales"])

    out = {"event_id": event_id, "meta": meta, "origin_ns": origin,
           "grid_ns": grid_ns, "t_grid": t_grid, "scales": scales,
           "edges_ns": edges, "dt_eval": dt_eval, "dt_render": dt_render,
           "ci": ci, "render_stride": int(stride),
           "k_eval": float(k_eval), "k_render": float(k_eval * stride),
           "n_eval_columns": int(n_grid), "n_render_columns": int(ci.size),
           "dt_over_s_min_eval": float(k_eval / 2.2567583341910247),
           "dt_over_s_min_render": float(k_eval * stride / 2.2567583341910247),
           "tape_ns": ts, "arrivals_ns": arr, "kernels": {}}

    u_grid = np.geomspace(na["u_min"], na["u_max"],
                          int(round(np.log2(na["u_max"] / na["u_min"])
                                    * na["per_octave"])) + 1)
    out["u_grid"] = u_grid
    logL = np.log2(scales)

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
                # TWO ON SHARES, AND THEY ARE DIFFERENT QUANTITIES NOW. On a
                # print-indexed grid every column holds the same number of PRINTS, not
                # the same amount of TIME, so a column mean is print-weighted. The
                # uniform grid this replaced gave a time-weighted share, so quoting one
                # against the other across the amendment would be comparing two
                # different statistics. Both are carried; the time-weighted one is the
                # comparable series.
                "on_share": float(on_db.mean()),
                "on_share_print_weighted": float(on_db.mean()),
                "on_share_time_weighted": float(
                    np.nansum(dt_eval[on_db]) / np.nansum(dt_eval))
                if dt_eval.size == on_db.size else float("nan"),
                "ladder_floor_binds_share": float(np.mean(
                    defined & (target < scales[0]))),
                "no_scale_clears_share": float(np.mean(
                    np.isfinite(target) & ~defined)),
                "s_star_median": float(np.nanmedian(np.where(defined, s_star, np.nan))),
            }

        # ---- the normalised view (A1-2): a COORDINATE CHANGE, not a normalisation of
        # the statistic. Nearest ladder scale in log space, so every cell drawn is a
        # value that was actually evaluated -- nothing is interpolated into existence.
        sm_r = s_min_t[ci]
        Zr = Z[ci, :]
        with np.errstate(invalid="ignore"):
            base = np.log2(np.where(np.isfinite(sm_r) & (sm_r > 0), sm_r, np.nan))
        tgt = np.log2(u_grid)[None, :] + base[:, None]
        safe = np.where(np.isfinite(tgt), tgt, logL[0])
        pos = np.clip(np.searchsorted(logL, safe), 1, logL.size - 1)
        take_lo = (safe - logL[pos - 1]) <= (logL[pos] - safe)
        idx = np.where(take_lo, pos - 1, pos)
        Znorm = np.take_along_axis(Zr, idx, axis=1)
        Znorm = np.where(np.isfinite(tgt) & (tgt >= logL[0]) & (tgt <= logL[-1]),
                         Znorm, np.nan)

        # ---- faithfulness (A1-3). PER COLUMN, not global: because the grid is
        # print-indexed, 2*dt/s_min is a CONSTANT, so this boundary is exactly the
        # horizontal rule the amendment asks for on the normalised pane, and the
        # curve 2*dt(t) on the absolute one. A global 2*max(dt) rule would hatch
        # almost the whole pane -- max(dt) falls in the deadest premarket stretch,
        # where one column can span minutes.
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = dt_render / np.where(sm_r > 0, sm_r, np.nan)
        u_faith = float(2.0 * np.nanmedian(ratio))
        s_faith_col = 2.0 * dt_render

        # MASKED and HATCHED are different things and conflating them would overstate
        # how much of the pane carries no data. Masked = n_eff < 8, the estimator
        # declining to answer. Hatched = the grid cannot honestly draw that scale.
        # The masked share is therefore measured BEFORE the aliasing cut.
        masked_norm = float(np.isnan(Znorm).mean())
        hatched_rows = float(np.mean(u_grid < u_faith))

        Znorm = np.where(u_grid[None, :] >= u_faith, Znorm, np.nan)
        Zabs = np.where(scales[None, :] >= s_faith_col[:, None], Zr, np.nan)

        out["kernels"][kernel] = {
            "Z": Z, "Znorm": Znorm, "Zabs": Zabs, "lam": lam, "s_min_t": s_min_t,
            "reads": reads,
            "masked_fraction": float(np.isnan(Z).mean()),
            "masked_fraction_norm": masked_norm,
            "hatched_row_share": hatched_rows,
            "u_faithful_at_specified_k": float(2.0 * 4.52 / 2.2567583341910247),
            "masked_fraction_abs": float(np.isnan(Zabs).mean()),
            "u_faithful": u_faith,
            "s_faithful_scalar": float(2.0 * np.nanmax(dt_render)),
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


def etnum(ns):
    """The same naive ET wall clock, as float64 epoch MILLISECONDS for a date axis.

    Why numeric rather than datetimes: plotly serialises a numeric array as base64
    binary and a datetime array as ISO strings. On a print-indexed grid the column
    count runs to tens of thousands, and at ~29 characters per timestamp the x arrays
    alone cost more than the field does. The axis is declared type='date', so the
    numbers are read as milliseconds and rendered as wall-clock labels -- identical
    display, a fraction of the payload. The ET conversion happens BEFORE the cast, so
    DST is handled by the same tz machinery as everywhere else.
    """
    return (et(ns).to_numpy().astype("datetime64[ms]").astype(np.float64))


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
    out.sort(key=lambda st: st[0])
    return out


def shading_trace(spans, y0, y1, colour, name, group, showlegend, visible=True):
    """All of an event's burst spans as ONE filled trace per pane rather than N shapes.

    Low opacity, and the online trace is drawn over the offline one WITHOUT hiding it:
    where they overlap the colour mixes, and that overlap is the most informative thing
    on the chart. A stack of opaque shapes would destroy exactly the comparison the
    chart is for.
    """
    if not spans:
        xs, ys = [np.nan], [np.nan]
    else:
        xs, ys = [], []
        for a, b in spans:
            xs += [a, a, b, b, np.nan]
            ys += [y0, y1, y1, y0, np.nan]
    return dict(x=np.asarray(xs, dtype=np.float64), y=np.asarray(ys, dtype=np.float64),
                fill="toself", mode="lines",
                line=dict(width=0), fillcolor=_rgba(colour, 0.16),
                name=name, legendgroup=group, showlegend=showlegend,
                hoverinfo="skip", visible=True if visible else "legendonly")


def _heat(x, y, Z, theme, cbar_y, hover_y, showscale=True, visible=True):
    """One field pane. asinh colour, unclipped, neutral exactly at zero, NaN as absence."""
    import plotly.graph_objects as go
    v = Z[np.isfinite(Z)]
    lo, hi = (float(v.min()), float(v.max())) if v.size else (-1.0, 1.0)
    A = np.arcsinh(Z).astype(np.float32)
    ticks = [tv for tv in CBAR_TICKS if lo <= tv <= hi]
    return go.Heatmap(
        x=x, y=y.astype(np.float32), z=A, xgap=0, ygap=0,
        zmin=float(np.arcsinh(lo)), zmax=float(np.arcsinh(hi)),
        colorscale=div_colorscale(float(np.arcsinh(lo)), float(np.arcsinh(hi)),
                                  theme, reverse=True),
        hovertemplate="%{x}<br>" + hover_y + "<br>dL/dln s (asinh) %{z:.3f}<extra></extra>",
        colorbar=dict(title=dict(text="dL/dln s<br>(asinh)", font=dict(size=9)),
                      len=0.28, y=cbar_y, thickness=9, outlinewidth=0,
                      tickmode="array",
                      tickvals=[float(np.arcsinh(tv)) for tv in ticks],
                      ticktext=[f"{tv:g}" for tv in ticks],
                      tickfont=dict(size=8)),
        showscale=showscale, visible=visible)


def build_figure(res, row, cfg, chash, theme):
    """Four panes, shared x, two toggled views of panes 2 and 3 (Amendment 1)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from plot_boundary_through_time import THEMES

    t = THEMES[theme]
    ev = res["event_id"]
    scales = res["scales"]
    u_grid = res["u_grid"]
    grid_ns = res["grid_ns"]
    ci = res["ci"]
    na = cfg["amendment_1"]["normalised_axis"]
    rcfg = cfg["render"]

    x_col = etnum(grid_ns[ci])
    y_u = np.log2(u_grid)
    y_s = np.log2(scales)

    # the absolute view is leaner: it answers "how long is this in seconds", which
    # does not need the finest columns. Its own achieved ratio is reported separately.
    cs = int(na["absolute_view_column_stride"])
    ss = int(na["absolute_view_scale_stride"])
    ai = np.arange(0, ci.size, cs)
    aj = np.arange(0, scales.size, ss)
    x_abs = x_col[ai]
    y_abs = y_s[aj]

    # ---- tape ---------------------------------------------------------------
    tape = adapter.load_event_tape(ev, None)
    n_tape = len(tape)
    cap = int(rcfg["tape_max_points"])
    stride = max(1, int(np.ceil(n_tape / cap)))
    tp = tape.iloc[::stride]
    arr = res["arrivals_ns"]
    itt = np.log10(np.diff(arr).astype(np.float64) * 1e-9)
    itt_ns = arr[1:]
    istride = max(1, int(np.ceil(len(itt) / cap)))

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.18, 0.31, 0.31, 0.20],
        subplot_titles=(
            "1 — trades: print price",
            "2 — OFFLINE field: dL/dln s, rate channel, CENTRED kernel",
            "3 — ONLINE field: dL/dln s, rate channel, ONE-SIDED (trailing) kernel",
            "4 — log₁₀ inter-trade interval per print",
        ),
    )

    fig.add_trace(go.Scattergl(
        x=etnum(tp["ts_ns"].to_numpy()),
        y=np.round(tp["price"].to_numpy(float), 4).astype(np.float32), mode="markers",
        marker=dict(size=2, color=t["ink2"], opacity=0.55),
        name="price", showlegend=False,
        hovertemplate="%{x}<br>%{y}<extra></extra>"), row=1, col=1)

    norm_idx, abs_idx = [], []
    for r, kernel in ((2, "centred"), (3, "onesided")):
        K = res["kernels"][kernel]
        cy = 0.585 if r == 2 else 0.265

        # --- PRIMARY: normalised s / s_min(t) --------------------------------
        # Rows below the aliasing line are NaN in every column by construction, so
        # they are not SENT -- the pane still spans the full u range and the hatched
        # band still covers them. Storing 6 always-empty rows per column cost ~1 MB an
        # event and showed nothing.
        keep = u_grid >= K["u_faithful"]
        fig.add_trace(_heat(x_col, y_u[keep], K["Znorm"][:, keep].T, theme, cy,
                            "s/s<sub>min</sub> = 2^%{y:.2f}", True, True), row=r, col=1)
        norm_idx.append(len(fig.data) - 1)

        # the aliased band: HATCHED, NOT COLOURED. Cells below it are already NaN in
        # the heatmap above -- nothing under this line is rendered as if measured.
        uf = np.log2(K["u_faithful"])
        fig.add_trace(go.Scatter(
            x=np.array([x_col[0], x_col[0], x_col[-1], x_col[-1]]),
            y=np.array([y_u[0], uf, uf, y_u[0]]),
            fill="toself", fillcolor="rgba(137,135,129,0.10)",
            fillpattern=dict(shape="/", size=6, solidity=0.12,
                             fgcolor=t["muted"], bgcolor="rgba(0,0,0,0)"),
            line=dict(width=0), mode="lines", hoverinfo="skip",
            name="aliased (s < 2·dt)", legendgroup="alias",
            showlegend=(r == 2)), row=r, col=1)
        norm_idx.append(len(fig.data) - 1)

        for uu, lab, dash in ((1.0, "s<sub>min</sub> (u = 1)", "solid"),
                              (2.0, "2×s<sub>min</sub>", "dot")):
            fig.add_trace(go.Scatter(
                x=np.array([x_col[0], x_col[-1]]),
                y=np.array([np.log2(uu)] * 2), mode="lines",
                line=dict(color=t["ink"], width=1.3, dash=dash),
                name=lab, legendgroup="floor", showlegend=(r == 2),
                hoverinfo="skip"), row=r, col=1)
            norm_idx.append(len(fig.data) - 1)

        # --- SECONDARY: absolute log2 s --------------------------------------
        fig.add_trace(_heat(x_abs, y_abs, K["Zabs"][np.ix_(ai, aj)].T, theme, cy,
                            "scale 2^%{y:.2f} s", True, False), row=r, col=1)
        abs_idx.append(len(fig.data) - 1)

        sm = K["s_min_t"][ci]
        ys = np.where(np.isfinite(sm) & (sm > 0), np.log2(np.maximum(sm, 1e-12)), np.nan)
        ys = np.where((ys >= y_s.min()) & (ys <= y_s.max()), np.round(ys, 3), np.nan)
        coef = 2.2568 if kernel == "centred" else 4.5135
        fig.add_trace(go.Scattergl(
            x=x_col, y=ys.astype(np.float32), mode="lines",
            line=dict(color=t["ink"], width=1.4), visible=False,
            name=f"s_min = {coef}/λ ({kernel})", legendgroup="floorabs",
            showlegend=(r == 2),
            hovertemplate="%{x}<br>s_min 2^%{y:.2f} s<extra></extra>"), row=r, col=1)
        abs_idx.append(len(fig.data) - 1)

        # 2*dt(t) as a curve on the absolute pane -- the same boundary, in the other
        # coordinate. Decimated: it is chrome, not data.
        d = max(1, ai.size // 600)
        sf = np.log2(2.0 * res["dt_render"][ai][::d])
        fig.add_trace(go.Scatter(
            x=x_abs[::d], y=np.clip(sf, y_s.min(), y_s.max()).astype(np.float32),
            mode="lines", line=dict(color=t["muted"], width=1.2, dash="dashdot"),
            visible=False, name="2·dt (aliasing floor)", legendgroup="alias2",
            showlegend=(r == 2), hoverinfo="skip"), row=r, col=1)
        abs_idx.append(len(fig.data) - 1)

    fig.add_trace(go.Scattergl(
        x=etnum(itt_ns[::istride]),
        y=np.round(itt[::istride], 3).astype(np.float32), mode="markers",
        marker=dict(size=2, color=t["muted"], opacity=0.45),
        name="log ITT", showlegend=False,
        hovertemplate="%{x}<br>log₁₀ Δt = %{y:.2f}<extra></extra>"), row=4, col=1)

    # ---- shading, all four panes, shared x -----------------------------------
    price = tp["price"].to_numpy(float)
    pane_y = {
        1: (float(np.nanmin(price)), float(np.nanmax(price))),
        2: (float(y_u.min()), float(y_u.max())),
        3: (float(y_u.min()), float(y_u.max())),
        4: (float(np.nanmin(itt)), float(np.nanmax(itt))),
    }
    shade_idx = {"primary": [], "overlay": []}
    for tag, vis in (("primary", True), ("overlay", False)):
        for kernel, label in (("centred", "offline"), ("onesided", "online")):
            rd = res["kernels"][kernel]["reads"][tag]
            spans = [(res["origin_ns"] + int(a * 1e9), res["origin_ns"] + int(b * 1e9))
                     for a, b in rd["spans"]]
            spans_x = [(float(etnum(np.array([a]))[0]), float(etnum(np.array([b]))[0]))
                       for a, b in spans]
            f = rd["read_factor"]
            name = (f"{label} bursts ({kernel}) · read {f:g}×s_min · {len(spans_x)} runs")
            group = f"{label}-{tag}"
            for r in (1, 2, 3, 4):
                tr = shading_trace(spans_x, pane_y[r][0], pane_y[r][1],
                                   BURST_COLOUR[kernel], name, group,
                                   showlegend=(r == 1), visible=vis)
                fig.add_trace(go.Scatter(**tr), row=r, col=1)
                shade_idx[tag].append(len(fig.data) - 1)

    # ---- the two views -------------------------------------------------------
    n = len(fig.data)

    def vis_for(view):
        v = []
        for i in range(n):
            if i in norm_idx:
                v.append(view == "norm")
            elif i in abs_idx:
                v.append(view == "abs")
            elif i in shade_idx["overlay"]:
                v.append("legendonly")
            else:
                v.append(True)
        return v

    # DOTTED KEYS, not a nested dict: plotly.js applies relayout on attribute paths,
    # and "title_text" inside a yaxis object is a plotly.py convenience that does not
    # survive the round trip -- the toggle would have silently kept the wrong axis
    # title. Caught by reading the emitted JSON rather than by trusting the call.
    yn_t, ya_t = "s / s<sub>min</sub>(t)  (log₂)", "log₂ kernel scale (s)"
    yn_r = [float(y_u.min()), float(y_u.max())]
    ya_r = [float(y_s.min()), float(y_s.max())]
    yn = {"yaxis2.title.text": yn_t, "yaxis3.title.text": yn_t,
          "yaxis2.range": yn_r, "yaxis3.range": yn_r}
    ya = {"yaxis2.title.text": ya_t, "yaxis3.title.text": ya_t,
          "yaxis2.range": ya_r, "yaxis3.range": ya_r}
    fig.update_layout(updatemenus=[dict(
        type="buttons", direction="right", x=0.0, y=1.045, xanchor="left",
        showactive=True, bgcolor=t["plane"], bordercolor=t["axis"], borderwidth=1,
        font=dict(size=10),
        buttons=[
            dict(label="normalised  s / s_min  (primary)", method="update",
                 args=[{"visible": vis_for("norm")}, yn]),
            dict(label="absolute  log₂ s", method="update",
                 args=[{"visible": vis_for("abs")}, ya]),
        ])])
    fig.update_yaxes(row=2, col=1, title_text=yn_t, range=yn_r)
    fig.update_yaxes(row=3, col=1, title_text=yn_t, range=yn_r)
    fig.update_yaxes(title_text="price", row=1, col=1)
    fig.update_yaxes(title_text="log₁₀ Δt (s)", row=4, col=1)

    # ---- caption -------------------------------------------------------------
    cc = res["cohort_counts"]
    flags = flag_list(row)
    kc, ko = res["kernels"]["centred"], res["kernels"]["onesided"]
    pc, po = kc["reads"]["primary"], ko["reads"]["primary"]
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
        f"tick-derived T=0 print count is substituted (§0a). Config hash {chash}. "
        f"<br><b>GRID (Amendment 1): columns are print-indexed, not uniform in time.</b> "
        f"dt = k/λ and s_min = 2.2568/λ, so dt/s_min = k/2.2568 everywhere on the tape. "
        f"Evaluation grid {res['n_eval_columns']:,} columns at k={res['k_eval']:.2f} "
        f"prints/col → <b>dt/s_min = {res['dt_over_s_min_eval']:.2f}</b>; render grid "
        f"{res['n_render_columns']:,} columns at k={res['k_render']:.2f} → "
        f"<b>dt/s_min = {res['dt_over_s_min_render']:.2f}</b> "
        f"(dt from {np.nanmin(res['dt_render']):.3g} s in the densest stretch to "
        f"{np.nanmax(res['dt_render']):.4g} s in the deadest — the whole point of the "
        f"print-indexed grid). The booleans are computed on the EVALUATION grid, so the "
        f"marking is resolved even where the picture is not. "
        f"<br><b>Y-AXIS is s/s_min(t) — a COORDINATE CHANGE, not a normalisation of the "
        f"statistic</b> (the values are raw; dividing by a standard error would drag the "
        f"argmax coarse, and nothing here does that). The mask boundary is therefore flat "
        f"at u=1 — <i>approximately</i>: the field's n_eff mask uses the kernel-weighted "
        f"count while s_min(t) uses the k=20 kNN rate, two estimators of the same λ, so "
        f"the edge wobbles around 1.0. <b>In this view the two floors LOOK identical when "
        f"they differ by exactly two</b> (2.2568/λ offline, 4.5135/λ online) — that is why "
        f"the absolute view is retained; toggle it at the top left. "
        f"<br><b>FAITHFULNESS:</b> hatched below u={kc['u_faithful']:.2f} offline / "
        f"{ko['u_faithful']:.2f} online (s &lt; 2·dt, per column — flat here <i>because</i> "
        f"the grid is print-indexed). Aliased cells are hatched, <b>never coloured</b>. At the "
        f"amendment's specified k = 4.52 this line would sit at u = "
        f"{kc['u_faithful_at_specified_k']:.1f}; it is higher here because max_columns "
        f"binds and k rises, which is reported rather than absorbed. "
        f"Global s_faithful = 2·max(dt) = {kc['s_faithful_scalar']:.4g} s, reported as the "
        f"worst case; the per-column line is the honest boundary. "
        f"<b>The primary read is at u=1, below the faithful line</b> — the marking reads a "
        f"scale the picture cannot draw, which is a consequence of dt=2·s_min at the render "
        f"grid and is stated rather than hidden. "
        f"<b>Masked and hatched are different and are counted apart.</b> MASKED (n_eff &lt; 8, "
        f"the estimator declining to answer, never interpolated): {kc['masked_fraction']:.1%} "
        f"of evaluated cells offline / {ko['masked_fraction']:.1%} online, and "
        f"{kc['masked_fraction_norm']:.1%} / {ko['masked_fraction_norm']:.1%} of rendered "
        f"cells before the aliasing cut. HATCHED (the grid cannot honestly draw it): "
        f"{kc['hatched_row_share']:.0%} / {ko['hatched_row_share']:.0%} of the u range. "
        f"<br><b>Read:</b> primary {pc['read_factor']:g}×s_min (median s* "
        f"{pc['s_star_median']:.2f} s offline / {po['s_star_median']:.2f} s online); ladder "
        f"floor binds {pc['ladder_floor_binds_share']:.1%} / "
        f"{po['ladder_floor_binds_share']:.1%}; no ladder scale clears the floor on "
        f"{pc['no_scale_clears_share']:.1%} / {po['no_scale_clears_share']:.1%} of the "
        f"session. 2×s_min read is a legend-toggled trace, hidden by default. "
        f"<b>Debounce</b> merge {cfg['burst_marking']['debounce']['merge_gap_factor']:g}×s*, "
        f"min on-duration {cfg['burst_marking']['debounce']['min_on_duration_factor']:g}×s*, "
        f"local to each run, not tuned per event: {pc['n_runs_raw']}→{len(pc['spans'])} runs "
        f"offline, {po['n_runs_raw']}→{len(po['spans'])} online. <b>ON share, two ways "
        f"because the grid is print-indexed:</b> by PRINT {pc['on_share']:.1%} / "
        f"{po['on_share']:.1%}, by TIME {pc['on_share_time_weighted']:.1%} / "
        f"{po['on_share_time_weighted']:.1%} — every column holds equal prints, not equal "
        f"time, so the column mean is print-weighted and only the time-weighted figure is "
        f"comparable with a uniform-grid render. "
        f"<br>{sub}Markers uniform 2 px — at {n_tape:,} prints the count does not permit "
        f"size-scaled markers. Colour asinh, unclipped, neutral exactly at zero; "
        f"<b>warm = negative = burst-like</b>. Rate channel, not the interval channel. "
        f"_reduce_extremum stays OFF. <b>No statistic is reported and no threshold applied</b> "
        f"— diagnostic render (D24/D25 closed tradeability; visible ≠ profitable)."
        "</sup>")

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=t["ink"]), x=0.005,
                   xanchor="left"),
        height=1440, hovermode="x unified",
        paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.012, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=70, r=88, t=300, b=44),
    )
    fig.update_xaxes(type="date")
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

def _v1_records(art):
    """The pre-amendment run, kept so the revised numbers can be read AGAINST it
    rather than instead of it. Absent is fine -- the comparison block is then omitted
    rather than faked."""
    f = art / "event_panels_render_v1_preamendment.json"
    if not f.exists():
        return {}
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    return {e["event_id"]: e for e in d.get("events", [])}


def write_index(rows, counts, cfg, chash, out, v1=None):
    v1 = v1 or {}
    a1 = cfg["amendment_1"]
    head = [("event", "s"), ("ticker", "s"), ("date", "s"), ("segment", "s"),
            ("prints", "n"), ("momentum %", "n"), ("mom decile", "n"),
            ("render cols", "n"), ("dt/s_min", "n"), ("dt min (s)", "n"),
            ("dt max (s)", "n"), ("masked 2", "n"), ("masked 3", "n"),
            ("hatched", "n"), ("runs off", "n"), ("runs on", "n"),
            ("ON% off (time)", "n"), ("ON% on (time)", "n"), ("flags", "s")]
    body = []
    for r in rows:
        body.append([
            f'<a href="{r["file"]}">{r["event_id"]}</a>', r["ticker"], r["date"],
            r["segment"], f'{r["prints"]:,}', f'{r["momentum_pct"]:.2f}',
            str(r["momentum_decile"]), f'{r["n_render_columns"]:,}',
            f'{r["dt_over_s_min_render"]:.2f}', f'{r["dt_min_seconds"]:.3g}',
            f'{r["dt_max_seconds"]:.4g}',
            f'{r["masked_offline"]*100:.1f}%', f'{r["masked_online"]*100:.1f}%',
            f'{r["hatched_row_share"]*100:.0f}%',
            str(r["runs_offline"]), str(r["runs_online"]),
            f'{r["on_offline_time_weighted"]*100:.1f}%',
            f'{r["on_online_time_weighted"]*100:.1f}%',
            ", ".join(r["flags"]) or "—",
        ])
    th = "".join(f'<th data-t="{t}" onclick="S({i})">{h}</th>'
                 for i, (h, t) in enumerate(head))
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in b) + "</tr>" for b in body)

    cmp_html = ""
    if v1:
        ch = ["event", "columns v1 → v2", "s per column v1 → v2 (median)",
              "runs offline v1 → v2", "runs online v1 → v2",
              "ON% offline v1 → v2", "ON% online v1 → v2"]
        cr = []
        for r in rows:
            o = v1.get(r["event_id"])
            if not o:
                continue
            v1cols = int(cfg["render"]["t_grid_points"])
            span = 57600.0
            cr.append(
                "<tr><td>" + r["event_id"] + "</td>"
                f"<td>{v1cols:,} → {r['n_render_columns']:,}</td>"
                f"<td>{span/v1cols:.2f} s (uniform) → {r['dt_min_seconds']:.3g}–"
                f"{r['dt_max_seconds']:.4g} s (print-indexed)</td>"
                f"<td>{o['runs_offline']} → {r['runs_offline']}</td>"
                f"<td>{o['runs_online']} → {r['runs_online']}</td>"
                f"<td>{o['on_offline']*100:.1f}% → "
                f"{r['on_offline_time_weighted']*100:.1f}%</td>"
                f"<td>{o['on_online']*100:.1f}% → "
                f"{r['on_online_time_weighted']*100:.1f}%</td></tr>")
        cmp_html = f"""
<h2>What changed under Amendment 1</h2>
<p>The estimator did not change. <b>The grid did</b>, and these are the same ten events
rendered before and after. Read the columns knowing what is and is not comparable:</p>
<ul>
<li><b>Comparable.</b> Run counts and the <b>time-weighted</b> ON share. The v1 grid was
uniform in time, so its column mean was already time-weighted; the v2 figure quoted here
is the time-weighted one for that reason, not the print-weighted column mean the new grid
produces by default.</li>
<li><b>Not comparable.</b> Masked fractions. v1 counted NaN cells over a time-uniform
rectangle; v2 counts them over a print-indexed one, so the two are weighted differently
and the drop from ~50% to ~28% is partly the axis change (problem 2) and partly the
weighting. It is not a like-for-like improvement and is not presented as one.</li>
<li><b>Run counts roughly tripled</b> (e.g. 751 → 2,251 offline on ARQQ). The tape did not
change: the v1 grid put 2.88 s between samples while the debounce minimum on-duration is
1 × s*, which on these events is often under a second — so v1 could not resolve the runs
it was debouncing. That is the grid defect the amendment names, measured.</li>
</ul>
<table><thead><tr>{''.join(f'<th>{h}</th>' for h in ch)}</tr></thead>
<tbody>{''.join(cr)}</tbody></table>
<p class=note>v1 record: <code>results/scale_field/artifacts/event_panels_render_v1_preamendment.json</code>.
Its charts were overwritten in place; the numbers are kept.</p>"""

    html = f"""<!doctype html><meta charset="utf-8">
<title>scale-field event panels</title>
<style>
 body{{font:13px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b0b0b;
   background:#f9f9f7;margin:0;padding:28px 32px;}}
 h1{{font-size:19px;margin:0 0 4px;}} h2{{font-size:15px;margin:26px 0 6px;}}
 p,li{{color:#52514e;max-width:105ch;margin:6px 0;}}
 table{{border-collapse:collapse;margin-top:12px;font-size:12px;background:#fcfcfb;}}
 th,td{{padding:5px 9px;border-bottom:1px solid #e1e0d9;text-align:left;
   white-space:nowrap;}}
 th{{cursor:pointer;user-select:none;background:#f4f2ec;position:sticky;top:0;}}
 th:hover{{color:#eb6834;}} a{{color:#256abf;}} tr:hover td{{background:#f4f2ec;}}
 code{{background:#f4f2ec;padding:1px 4px;}} .note{{font-size:12px;}}
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
draw is not. Tick-derived T=0 print count is substituted (§0a).</p>
<p><b>Grid (Amendment 1).</b> Columns are <b>print-indexed, not uniform in time</b>: one
column per k prints, so <code>dt/s_min = k/2.2568</code> everywhere on the tape and dense
stretches get narrow columns automatically. The <b>primary y-axis is s/s_min(t)</b> — a
coordinate change, not a normalisation of the statistic — with the absolute log₂ s view
toggled at the top left of each chart. <b>In the normalised view the offline and online
floors look identical when they differ by exactly two</b>; that is why the absolute view
is retained. Cells the grid cannot honestly draw are <b>hatched, never coloured</b>.</p>
<p><b>Read at 1×s_min</b> (primary), with 2×s_min as a legend-toggled trace. Config hash
<code>{chash}</code>.</p>
<p><b>Not a measurement.</b> No statistic is reported, no threshold established, no
timescale claimed. D24 and D25 closed tradeability on cost arithmetic; bursts being
visible and bursts being profitable are different claims.</p>
<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>
{cmp_html}
<script>
let dir={{}};
function S(i){{
 const tb=document.querySelectorAll('tbody')[0], rs=[...tb.rows];
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

    # The chart HTML is .gitignored under results/scale_field/charts/*/ -- the repo
    # commits MANIFESTS, not payloads, and these panels are 7-8 MB each. This is the
    # committed record of what was rendered and where it lives.
    with open(out / "chart_manifest.json", "w", encoding="utf-8") as f:
        json.dump({
            "config_hash": chash,
            "amendment": "1 -- dynamic render resolution matched to the tape",
            "n_charts": len(rows),
            "charts": [r["file"] for r in rows],
            "index": "index.html",
            "offline_rule": "D14 -- plotly.min.js written beside the charts, never a CDN",
            "html_is_gitignored": "results/scale_field/charts/*/*.html; the numbers behind "
                                  "every chart are in results/scale_field/artifacts/"
                                  "event_panels_render.json",
            "grid": {"rule": a1["column_grid"]["rule"],
                     "prints_per_column": a1["column_grid"]["prints_per_column"],
                     "achieved_dt_over_s_min": {r["event_id"]:
                                                r["dt_over_s_min_render"] for r in rows}},
            "v1_preamendment": "results/scale_field/artifacts/"
                               "event_panels_render_v1_preamendment.json",
            "source": "research/scale_field/event_panels.py:write_index",
        }, f, indent=2)


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
    p.add_argument("--index-only", action="store_true",
                   help="rebuild index.html from the committed render manifest without "
                        "recomputing any field.")
    p.add_argument("--skip-guard", action="store_true",
                   help="skip the A1-4 cost probe (it re-runs one event); the guard "
                        "still applies and this only exists for a re-render after the "
                        "projection has already been measured and reported.")
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

    if args.index_only:
        with open(art / "event_panels_render.json", encoding="utf-8") as f:
            prev = json.load(f)
        write_index(prev["events"], counts, cfg, prev["config_hash"], charts,
                    v1=_v1_records(art))
        print(f"rebuilt {charts / 'index.html'} from the committed manifest")
        return 0

    todo = drawn if args.event is None else drawn[drawn["event_id"] == args.event]
    if todo.empty:
        raise SystemExit(f"{args.event} is not in the drawn cohort")

    # ---- A1-4 cost guard ---------------------------------------------------
    # Evaluation cost is now driven by column count rather than a fixed grid, so it
    # is MEASURED on one median-density event and extrapolated on print count before
    # the cohort runs. Over the ceiling: POST AND STOP. Raising k is a decision, not
    # something to take silently, and the cohort and the scale band are never cut.
    guard = None
    if args.event is None and not args.skip_guard:
        pr = todo["t0_print_count"].to_numpy(float)
        probe = todo.iloc[int(np.argsort(pr)[len(pr) // 2])]
        t0 = time.perf_counter()
        _ = compute_event(probe["event_id"], cfg)
        probe_s = time.perf_counter() - t0
        projected = float(probe_s * pr.sum() / probe["t0_print_count"])
        ceiling = float(cfg["amendment_1"]["cost_guard"]["runtime_ceiling_seconds"])
        guard = {"probe_event": probe["event_id"],
                 "probe_prints": int(probe["t0_print_count"]),
                 "probe_seconds": round(probe_s, 1),
                 "cohort_prints": int(pr.sum()),
                 "projected_seconds": round(projected, 1),
                 "ceiling_seconds": ceiling,
                 "fired": bool(projected > ceiling)}
        print(f"cost guard: probe {probe['event_id']} {probe_s:.1f}s at "
              f"{int(probe['t0_print_count']):,} prints -> projected "
              f"{projected:.0f}s for the cohort against a {ceiling:.0f}s ceiling")
        if guard["fired"]:
            with open(art / "event_panels_cost_guard.json", "w", encoding="utf-8") as f:
                json.dump(guard, f, indent=2)
            raise SystemExit(
                f"POST AND STOP (Amendment 1 A1-4): projected {projected:.0f}s exceeds "
                f"the {ceiling:.0f}s ceiling. Raising k is a decision -- the cohort and "
                f"the scale band are not reduced silently.")

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
            "masked_offline_rendered": kc["masked_fraction_norm"],
            "masked_online_rendered": ko["masked_fraction_norm"],
            "n_eval_columns": res["n_eval_columns"],
            "n_render_columns": res["n_render_columns"],
            "k_eval": round(res["k_eval"], 3),
            "k_render": round(res["k_render"], 3),
            "dt_over_s_min_eval": round(res["dt_over_s_min_eval"], 3),
            "dt_over_s_min_render": round(res["dt_over_s_min_render"], 3),
            "dt_min_seconds": float(np.nanmin(res["dt_render"])),
            "dt_max_seconds": float(np.nanmax(res["dt_render"])),
            "u_faithful_offline": kc["u_faithful"],
            "u_faithful_online": ko["u_faithful"],
            "u_faithful_at_specified_k": kc["u_faithful_at_specified_k"],
            "hatched_row_share": kc["hatched_row_share"],
            "s_faithful_scalar_seconds": kc["s_faithful_scalar"],
            "runs_offline": len(pc["spans"]), "runs_online": len(po["spans"]),
            "on_offline": pc["on_share"], "on_online": po["on_share"],
            "on_offline_time_weighted": pc["on_share_time_weighted"],
            "on_online_time_weighted": po["on_share_time_weighted"],
            "s_star_median_offline": pc["s_star_median"],
            "s_star_median_online": po["s_star_median"],
            "ladder_floor_binds_offline": pc["ladder_floor_binds_share"],
            "ladder_floor_binds_online": po["ladder_floor_binds_share"],
            "flags": flag_list(row), "file": fname,
            "seconds": round(time.perf_counter() - t0, 1),
        }
        index_rows.append(rec)
        summary.append(rec)
        print(f"{ev:26s} cols {res['n_render_columns']:>6,} dt/s_min "
              f"{res['dt_over_s_min_render']:.2f} masked "
              f"{kc['masked_fraction_norm']:.1%}/{ko['masked_fraction_norm']:.1%} "
              f"runs {len(pc['spans'])}/{len(po['spans'])} "
              f"ON(time) {pc['on_share_time_weighted']:.1%}/"
              f"{po['on_share_time_weighted']:.1%} [{rec['seconds']}s]")

    if args.event is None:
        write_index(index_rows, counts, cfg, chash, charts, v1=_v1_records(art))
        with open(art / "event_panels_render.json", "w", encoding="utf-8") as f:
            json.dump({"config_hash": chash, "theme": args.theme,
                       "amendment": "1 -- dynamic render resolution matched to the tape",
                       "cost_guard": guard,
                       "grid": cfg["amendment_1"]["column_grid"],
                       "normalised_axis": cfg["amendment_1"]["normalised_axis"],
                       "faithfulness": cfg["amendment_1"]["faithfulness"],
                       "supersedes": "results/scale_field/artifacts/"
                                     "event_panels_render_v1_preamendment.json",
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
