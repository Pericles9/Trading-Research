"""
Work-order Task 1: does the parameter-free field boolean LEAD a level detector, or
restate it?

    FIELD   sign of dL/dln s at the smallest ladder scale clearing 2 * s_min(t)
    LEVEL   lambda_hat(t, s) above its own TRAILING q90 at that same scale

The factor of 2 on s_min is the point: s_min moves with lambda, so a read taken AT the
boundary would be partly definitional -- the boundary dropping and the tape speeding up
are the same event. Reading one octave above it keeps the comparison on the field's
behaviour rather than on the floor's.

THE SIGN, SETTLED BY MEASUREMENT AND NOT BY ASSUMPTION. The work order specifies
`dL/dln s > 0`. On this estimator that selects VOIDS, not bursts:

    dL/dln s = E_w[z^2] - 1,  z = (t - t_i)/s

so at the centre of a cluster narrow compared with s every z ~ 0 and the quantity goes to
-1; in a void the nearest prints sit at |z| >> 1 and it goes positive. Measured on a
synthetic 120/s burst in a 3/s background: dL/dln s is negative at 14 of 14 scales inside
the burst (min -0.884) and positive at wide scales in the quiet stretch. Since LEVEL is a
HIGH-activity detector, comparing it against a void detector would be comparing two
anti-correlated things and the lead time would be meaningless.

So BOTH orientations are computed and reported:
    field_burst   dL/dln s < 0   -- concentration. PRIMARY, comparable to LEVEL.
    field_void    dL/dln s > 0   -- the work order's literal text, reported so the
                                    choice is visible rather than silently corrected.

WHAT IS REPORTED, per event and pooled by segment:
  1. signed lead of FIELD relative to LEVEL at matched onsets, in seconds AND in units
     of s (the scale sets what "early" can mean, so seconds alone are not comparable
     across events)
  2. Jaccard of the two ON-sets, plus both one-sided shares
  3. R^2 of ridge strength on log lambda_hat at the same (t, s)

READ, fixed before the run: overlap above ~0.9 with lead centred on zero means the field
restates the level detector and the machinery is not earning its keep. A positive median
lead of an appreciable fraction of s is the result that makes this a signal rather than a
description. BOTH OUTCOMES ARE REPORTABLE AND A NULL WILL NOT BE SOFTENED.

Usage: .venv/Scripts/python.exe research/scale_field/t1_lead_time.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import load_cohort, load_detection, load_event_prints_meta, rel  # noqa: E402
from scale_field import (collapse_same_timestamp, field, intervals,  # noqa: E402
                         s_min_for_rate, seconds_since)

OUT = "results/scale_field/artifacts/t1_lead_time.json"
OUT_EVENTS = "results/scale_field/artifacts/t1_lead_time_events.parquet"
OUT_ONSETS = "results/scale_field/artifacts/t1_lead_time_onsets.parquet"

WINDOW_S = 60.0            # anchor -> +60 s, the work order's window
LOOKBACK_S = 300.0         # causal history for the trailing q90
CONTEXT_S = 900.0          # tape read either side, so the edge mask never bites
GRID_DT = 0.02             # 20 ms, resolves the finest scale on the ladder
SCALE_LO, SCALE_HI, N_SCALES = 0.05, 7.5, 33   # 7.5 s = W/8, the window's own ceiling
KNN_K = 20
TRAIL_Q = 0.90
S_MIN_FACTOR = 2.0         # read one octave above the floor, not at it
N_SHIFT_DRAWS = 200        # circular-shift null for the onset matching
SHIFT_SEED = 42


def knn_rate(ts_ns, grid_ns, k=KNN_K):
    ts = np.asarray(ts_ns, dtype=np.int64)
    if ts.size < k + 1:
        return np.full(len(grid_ns), np.nan)
    i = np.searchsorted(ts, np.asarray(grid_ns, dtype=np.int64))
    lo = np.clip(i - k // 2, 0, ts.size - 1 - k)
    span = (ts[lo + k] - ts[lo]).astype(np.float64) / 1e9
    return np.where(span > 0, k / span, np.nan)


def trailing_q90(x, t, lookback):
    """Causal trailing quantile: at each t, the q90 of x over [t-lookback, t).
    Uses only the past. O(n log n) via a sorted-window walk is overkill here; the grids
    are ~20k points and a strided argpartition per point is fast enough, so this is the
    plain definition rather than an approximation of it."""
    n = len(t)
    out = np.full(n, np.nan)
    lo_idx = np.searchsorted(t, t - lookback, side="left")
    for i in range(n):
        a = lo_idx[i]
        if i - a < 30:
            continue
        seg = x[a:i]
        seg = seg[np.isfinite(seg)]
        if seg.size >= 30:
            out[i] = np.quantile(seg, TRAIL_Q)
    return out


def debounce(b, min_samples):
    """Drop ON runs shorter than the kernel that produced them.

    NOT a tuned parameter: a feature narrower than its own smoothing kernel has not been
    resolved by that kernel, so an ON run shorter than s* is an artifact of reading a
    smoothed field on a grid finer than the smoothing. The threshold is s*, which is
    arithmetic. Without it the field boolean chatters at ~2.8x the level detector's onset
    rate and the nearest-onset match degenerates into chance pairing."""
    b = np.asarray(b, bool)
    if b.size == 0 or min_samples <= 1:
        return b
    out = b.copy()
    i = 0
    n = b.size
    while i < n:
        if b[i]:
            j = i
            while j + 1 < n and b[j + 1]:
                j += 1
            if (j - i + 1) < min_samples:
                out[i:j + 1] = False
            i = j + 1
        else:
            i += 1
    return out


def shift_null(t_field, t_level, tol, t_lo, t_hi, n_draws=N_SHIFT_DRAWS, seed=SHIFT_SEED):
    """Circular-shift null for the onset match.

    THE QUESTION THIS ANSWERS. With FIELD onsets spaced ~3.8 s apart and a tolerance of
    ~7.8 s, EVERY level onset finds a field partner whether or not the two are related --
    and the first run duly matched 100% of them. So an observed median lead near zero is
    exactly what chance pairing produces, and the statistic means nothing until it is
    compared against chance. Shifting the field onsets circularly inside the window
    destroys any real timing relationship while preserving their COUNT and SPACING, which
    is what drives the matching artifact."""
    span = t_hi - t_lo
    if t_field.size == 0 or t_level.size == 0 or span <= 0:
        return {"n_draws": 0}
    rng = np.random.default_rng(seed)
    med, frac, matched = [], [], []
    for _ in range(n_draws):
        off = rng.uniform(0, span)
        tf = np.sort(t_lo + np.mod(t_field - t_lo + off, span))
        leads, _ = match_onsets(tf, t_level, tol)
        if leads.size:
            med.append(float(np.median(leads)))
            frac.append(float((leads > 0).mean()))
            matched.append(int(leads.size))
    if not med:
        return {"n_draws": 0}
    return {"n_draws": len(med),
            "lead_median_seconds": {"q05": float(np.quantile(med, .05)),
                                    "q50": float(np.quantile(med, .50)),
                                    "q95": float(np.quantile(med, .95))},
            "share_field_first": {"q05": float(np.quantile(frac, .05)),
                                  "q50": float(np.quantile(frac, .50)),
                                  "q95": float(np.quantile(frac, .95))},
            "matched_share_mean": float(np.mean(matched) / t_level.size)}


def rising_edges(b, t):
    """Times at which a boolean goes False->True. NaN-safe: an undefined cell breaks a
    run rather than continuing it."""
    b = np.where(np.isfinite(b.astype(float)), b, False).astype(bool)
    if b.size < 2:
        return np.zeros(0)
    idx = np.flatnonzero((~b[:-1]) & b[1:]) + 1
    return t[idx]


def match_onsets(t_field, t_level, tol):
    """Pair each LEVEL onset with the nearest FIELD onset within tol seconds.
    Signed lead = t_level - t_field, so POSITIVE means the field fired FIRST."""
    if t_field.size == 0 or t_level.size == 0:
        return np.zeros(0), np.zeros(0)
    j = np.searchsorted(t_field, t_level)
    leads, at = [], []
    for k, tl in enumerate(t_level):
        cands = []
        for jj in (j[k] - 1, j[k]):
            if 0 <= jj < t_field.size:
                cands.append(t_field[jj])
        if not cands:
            continue
        tf = min(cands, key=lambda v: abs(tl - v))
        if abs(tl - tf) <= tol:
            leads.append(tl - tf)
            at.append(tl)
    return np.asarray(leads), np.asarray(at)


def q(a, qs=(0.25, 0.5, 0.75)):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), **{f"q{int(x*100):02d}": float(np.quantile(a, x)) for x in qs},
            "mean": float(a.mean())}


def main() -> int:
    cfg = adapter.load_config()
    cohort = load_cohort(cfg)
    det = load_detection(cfg)
    anchors = {r.event_id: (r.anchor_ns, r.segment) for r in det.itertuples(index=False)
               if np.isfinite(r.anchor_ns)}
    pooled = cohort[cohort["pooled"]]
    scales = np.geomspace(SCALE_LO, SCALE_HI, N_SCALES)

    rows, onset_rows, t0 = [], [], time.perf_counter()
    for r in pooled.itertuples(index=False):
        if r.event_id not in anchors:
            continue
        anchor_ns, segment = anchors[r.event_id]
        anchor_ns = int(anchor_ns)
        ts, _ = load_event_prints_meta(r.event_id, None, cfg)
        lo_ns = anchor_ns - int((LOOKBACK_S + CONTEXT_S) * 1e9)
        hi_ns = anchor_ns + int((WINDOW_S + CONTEXT_S) * 1e9)
        sel = ts[(ts >= lo_ns) & (ts < hi_ns)]
        arr = collapse_same_timestamp(sel)
        if arr.size < 200:
            continue
        origin = int(arr[0])
        ts_s = seconds_since(arr, origin)
        ev_s, x = intervals(arr, origin=origin)

        # evaluate over lookback + window so the trailing q90 is causal and real
        g_lo = (anchor_ns - int(LOOKBACK_S * 1e9) - origin) / 1e9
        g_hi = (anchor_ns + int(WINDOW_S * 1e9) - origin) / 1e9
        tg = np.arange(g_lo, g_hi, GRID_DT)
        if tg.size < 500:
            continue
        f = field(ts_s, ev_s, x, tg, scales, neff_min=cfg["field"]["neff_min"],
                  sigma_lo=cfg["field"]["sigma_lo"],
                  edge_scales=cfg["field"]["edge_scales"])

        grid_ns = (origin + tg * 1e9).astype(np.int64)
        lam_knn = knn_rate(arr, grid_ns)
        s_target = S_MIN_FACTOR * s_min_for_rate(lam_knn)

        # per t: index of the smallest ladder scale >= s_target AND defined there
        jstar = np.full(tg.size, -1, dtype=np.int64)
        for i in range(tg.size):
            if not np.isfinite(s_target[i]):
                continue
            cand = np.flatnonzero((scales >= s_target[i])
                                  & np.isfinite(f["dlograte"][i]))
            if cand.size:
                jstar[i] = cand[0]
        ok = jstar >= 0
        if ok.sum() < 200:
            continue
        ii = np.arange(tg.size)
        dlr = np.where(ok, f["dlograte"][ii, np.clip(jstar, 0, None)], np.nan)
        lgr = np.where(ok, f["lograte"][ii, np.clip(jstar, 0, None)], np.nan)
        s_at = np.where(ok, scales[np.clip(jstar, 0, None)], np.nan)

        # booleans, restricted to the reported window [anchor, anchor+60]
        in_win = tg >= (anchor_ns - origin) / 1e9
        thr = trailing_q90(lgr, tg, LOOKBACK_S)
        b_burst = ok & in_win & np.isfinite(dlr) & (dlr < 0)
        b_void = ok & in_win & np.isfinite(dlr) & (dlr > 0)
        b_level = ok & in_win & np.isfinite(lgr) & np.isfinite(thr) & (lgr > thr)
        defined = ok & in_win & np.isfinite(dlr) & np.isfinite(thr)
        if defined.sum() < 200:
            continue

        tw = tg[in_win]
        rec = {"event_id": r.event_id, "ticker": r.ticker, "segment": segment,
               "n_grid_defined": int(defined.sum()),
               "median_s_star": float(np.nanmedian(s_at[in_win])),
               "median_lambda_knn": float(np.nanmedian(lam_knn[in_win])),
               "on_share_field_burst": float(b_burst[defined].mean()),
               "on_share_field_void": float(b_void[defined].mean()),
               "on_share_level": float(b_level[defined].mean())}

        for tag, bf in (("burst", b_burst), ("void", b_void)):
            inter = float((bf & b_level)[defined].sum())
            union = float((bf | b_level)[defined].sum())
            rec[f"jaccard_{tag}"] = inter / union if union > 0 else np.nan
            rec[f"only_field_{tag}"] = float((bf & ~b_level)[defined].sum()) / max(union, 1)
            rec[f"only_level_vs_{tag}"] = float((~bf & b_level)[defined].sum()) / max(union, 1)

            # debounce BOTH sides at the same non-tunable threshold, so neither is
            # advantaged: an ON run must last at least one kernel width s*.
            min_samp = max(1, int(round(rec["median_s_star"] / GRID_DT)))
            bfd = debounce(bf[in_win], min_samp)
            bld = debounce(b_level[in_win], min_samp)
            ef = rising_edges(bfd, tw)
            el = rising_edges(bld, tw)
            # tolerance tied to the FIELD's own onset spacing, not to s*: matching
            # cannot be allowed a window wider than the thing it is matching within.
            spacing = (np.median(np.diff(ef)) if ef.size > 2 else 5.0 * rec["median_s_star"])
            tol = float(min(5.0 * rec["median_s_star"], max(spacing / 2.0, GRID_DT)))
            rec[f"match_tol_s_{tag}"] = tol
            rec[f"onset_spacing_field_{tag}"] = float(spacing) if np.isfinite(spacing) else np.nan
            leads, at = match_onsets(ef, el, tol)
            rec[f"null_{tag}"] = shift_null(ef, el, tol, float(tw[0]), float(tw[-1]))
            rec[f"n_onsets_field_{tag}"] = int(ef.size)
            rec[f"matched_share_{tag}"] = float(leads.size / el.size) if el.size else np.nan
            rec[f"n_onsets_level"] = int(el.size)
            rec[f"n_matched_{tag}"] = int(leads.size)
            rec[f"lead_median_s_{tag}"] = float(np.median(leads)) if leads.size else np.nan
            rec[f"lead_iqr_s_{tag}"] = (float(np.quantile(leads, .75) - np.quantile(leads, .25))
                                        if leads.size >= 4 else np.nan)
            rec[f"lead_median_in_s_units_{tag}"] = (float(np.median(leads) / rec["median_s_star"])
                                                    if leads.size else np.nan)
            for L, A in zip(leads, at):
                onset_rows.append({"event_id": r.event_id, "segment": segment,
                                   "orientation": tag, "t_rel_anchor_s":
                                       float(A - (anchor_ns - origin) / 1e9),
                                   "lead_s": float(L),
                                   "lead_in_s_units": float(L / rec["median_s_star"]),
                                   "s_star": rec["median_s_star"]})

        # R^2 of ridge strength on log lambda at the same (t, s)
        yv = -dlr[defined]                      # concentration magnitude
        xv = lgr[defined]
        m = np.isfinite(xv) & np.isfinite(yv)
        if m.sum() > 50 and np.std(xv[m]) > 0:
            rec["r2_ridge_on_loglambda"] = float(np.corrcoef(xv[m], yv[m])[0, 1] ** 2)
            rec["corr_ridge_on_loglambda"] = float(np.corrcoef(xv[m], yv[m])[0, 1])
        rows.append(rec)
        if len(rows) % 20 == 0:
            print(f"  {len(rows)} events ({time.perf_counter()-t0:.0f}s)", flush=True)

    ev_df = pd.DataFrame(rows)
    on_df = pd.DataFrame(onset_rows)
    ev_df.drop(columns=[c for c in ev_df.columns if c.startswith("null_")]
               ).to_parquet(rel(OUT_EVENTS), index=False)
    if len(on_df):
        on_df.to_parquet(rel(OUT_ONSETS), index=False)
    print(f"\n{len(ev_df)} events, {len(on_df)} matched onsets, "
          f"{time.perf_counter()-t0:.0f}s")

    def pooled_stats(tag):
        d = {"jaccard": q(ev_df[f"jaccard_{tag}"]),
             "only_field": q(ev_df[f"only_field_{tag}"]),
             "only_level": q(ev_df[f"only_level_vs_{tag}"]),
             "lead_seconds_per_event_median": q(ev_df[f"lead_median_s_{tag}"]),
             "lead_in_s_units_per_event_median": q(ev_df[f"lead_median_in_s_units_{tag}"]),
             "n_events_with_matches": int(ev_df[f"n_matched_{tag}"].gt(0).sum()),
             "match_tol_seconds": q(ev_df[f"match_tol_s_{tag}"]),
             "onset_spacing_field_seconds": q(ev_df[f"onset_spacing_field_{tag}"]),
             "matched_share_of_level_onsets": q(ev_df[f"matched_share_{tag}"]),
             "circular_shift_null": {
                 "what": "field onsets shifted circularly inside the window, count and "
                         "spacing preserved, timing relationship destroyed; 200 draws per "
                         "event. If the observed lead sits inside this band the match is "
                         "chance pairing and the lead statistic is empty.",
                 "null_lead_median_seconds": q(pd.Series(
                     [r.get("lead_median_seconds", {}).get("q50", np.nan)
                      for r in ev_df[f"null_{tag}"] if isinstance(r, dict)])),
                 "null_share_field_first": q(pd.Series(
                     [r.get("share_field_first", {}).get("q50", np.nan)
                      for r in ev_df[f"null_{tag}"] if isinstance(r, dict)])),
                 "null_matched_share": q(pd.Series(
                     [r.get("matched_share_mean", np.nan)
                      for r in ev_df[f"null_{tag}"] if isinstance(r, dict)])),
             }}
        if len(on_df):
            sub = on_df[on_df["orientation"] == tag]
            d["lead_seconds_all_onsets"] = q(sub["lead_s"])
            d["lead_in_s_units_all_onsets"] = q(sub["lead_in_s_units"])
            d["share_of_onsets_field_first"] = (float((sub["lead_s"] > 0).mean())
                                                if len(sub) else None)
        return d

    out = {
        "task": "Task 1 -- lead time of the parameter-free field boolean against a level detector",
        "config_hash": adapter.config_hash(),
        "window": f"anchor -> +{WINDOW_S:g} s",
        "scale_rule": f"smallest ladder scale >= {S_MIN_FACTOR:g} * s_min(t); "
                      f"ladder {SCALE_LO}..{SCALE_HI} s ({N_SCALES} scales, {SCALE_HI} = W/8)",
        "level_detector": f"lambda_hat(t,s*) above its own trailing q{int(TRAIL_Q*100)} "
                          f"over a causal {LOOKBACK_S:g} s lookback",
        "sign_note": "The work order specifies dL/dln s > 0. On this estimator that selects "
                     "VOIDS: dL/dln s = E_w[z^2] - 1, which goes to -1 inside a cluster and "
                     "positive in a gap. Measured on a synthetic 120/s burst in a 3/s "
                     "background: negative at 14 of 14 scales inside the burst (min -0.884). "
                     "Since LEVEL is a high-activity detector, the comparable orientation is "
                     "dL/dln s < 0. BOTH are reported; 'burst' is primary.",
        "read_fixed_before_the_run": "Jaccard above ~0.9 with lead centred on zero means the "
                                     "field restates the level detector. A positive median "
                                     "lead of an appreciable fraction of s makes it a signal.",
        "n_events": int(len(ev_df)),
        "n_matched_onsets": int(len(on_df)),
        "median_s_star_seconds": float(ev_df["median_s_star"].median()) if len(ev_df) else None,
        "on_share": {k: q(ev_df[f"on_share_{k}"]) for k in
                     ("field_burst", "field_void", "level")} if len(ev_df) else {},
        "burst_orientation_PRIMARY": pooled_stats("burst") if len(ev_df) else {},
        "void_orientation_literal_work_order": pooled_stats("void") if len(ev_df) else {},
        "r2_ridge_on_loglambda": q(ev_df["r2_ridge_on_loglambda"]) if "r2_ridge_on_loglambda" in ev_df else {},
        "by_segment": {str(s): {"n": int(len(g)),
                                "jaccard_burst": q(g["jaccard_burst"]),
                                "lead_median_s_burst": q(g["lead_median_s_burst"]),
                                "lead_in_s_units_burst": q(g["lead_median_in_s_units_burst"])}
                       for s, g in ev_df.groupby("segment")} if len(ev_df) else {},
        "source": "research/scale_field/t1_lead_time.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scale_field/t1_lead_time.py",
    }
    with open(rel(OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    if len(ev_df):
        p = out["burst_orientation_PRIMARY"]
        print(f"\nmedian s* = {out['median_s_star_seconds']:.3f} s")
        print(f"ON share: field_burst {out['on_share']['field_burst']['q50']:.1%}  "
              f"level {out['on_share']['level']['q50']:.1%}")
        print(f"\nPRIMARY (dL/dln s < 0, burst-like):")
        print(f"  Jaccard vs LEVEL          median {p['jaccard']['q50']:.3f} "
              f"(IQR {p['jaccard']['q25']:.3f}-{p['jaccard']['q75']:.3f})")
        print(f"  ON in FIELD not LEVEL     median {p['only_field']['q50']:.3f}")
        print(f"  ON in LEVEL not FIELD     median {p['only_level']['q50']:.3f}")
        nl = p["circular_shift_null"]
        print(f"  match tolerance           median {p['match_tol_seconds']['q50']:.3f} s "
              f"(field onset spacing {p['onset_spacing_field_seconds']['q50']:.3f} s)")
        print(f"  matched share of LEVEL onsets: observed "
              f"{p['matched_share_of_level_onsets']['q50']:.1%}  "
              f"null {nl['null_matched_share']['q50']:.1%}")
        if p.get("lead_seconds_all_onsets", {}).get("n"):
            la = p["lead_seconds_all_onsets"]; lu = p["lead_in_s_units_all_onsets"]
            print(f"  signed lead, all {la['n']} onsets: median {la['q50']:+.3f} s "
                  f"(IQR {la['q25']:+.3f}..{la['q75']:+.3f})")
            print(f"                          in units of s: median {lu['q50']:+.3f}")
            print(f"  share of onsets where FIELD fired first: "
                  f"{p['share_of_onsets_field_first']:.1%}"
                  f"   NULL {nl['null_share_field_first']['q50']:.1%}")
            print(f"  null lead median (per event): {nl['null_lead_median_seconds']['q50']:+.3f} s")
        r2 = out["r2_ridge_on_loglambda"]
        if r2.get("n"):
            print(f"  R2 of ridge strength on log lambda: median {r2['q50']:.3f}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
