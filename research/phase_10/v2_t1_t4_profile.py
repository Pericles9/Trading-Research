"""
Phase 10 v2 T1-T4 -- intensity estimation, anchors, timescales, level conditioning.

One tick read per event drives all of:

  T1  adaptive centred-k-block kNN rate, BOTH observables (print rate and
      share-volume rate, co-equal), the full k grid, both tie variants
  T2  peak anchor (retrospective) and detection anchor (D7, joined from R1.3)
  T3  detection-to-peak (signed, never clipped), rise profile, decay timescales,
      terminal condition against the scalar flanking baseline
  T4  absolute peak rate carried as a per-event covariate

D6: shape uses no baseline -- every curve is normalized by its own peak. The
flanking sessions supply exactly one scalar per event, for the terminal
condition only.

D7: detection is a price-threshold crossing resolved to a poll boundary. Peak is
an arrival-intensity maximum. Both come from the same T=0 tick stream; they are
different quantities and the comparison is legitimate, but the two anchors are
NOT independently sourced.

Escalation row 10: negative detection-to-peak values are never clipped,
excluded, or absolute-valued. Their share is a headline number.

Usage: .venv/Scripts/python.exe research/phase_10/v2_t1_t4_profile.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, collapse_ties, config_hash_v2, first_sustained_crossing,
    knn_rate, load_config_v2, load_frozen_cohort, quantiles, read_event_trades,
    rel, session_window, write_json,
)

OUT_METRICS = "v2_t1_event_metrics.parquet"
OUT_PROFILES = "v2_t1_profiles.parquet"
OUT_SUMMARY = "v2_t1_t4_summary.json"
FLANK = (-3, -2, -1)
OBSERVABLES = {"print_rate": "print_rate", "volume_rate": "volume_rate"}


def scalar_baseline(cfg, ticker, date, mom, bitmap) -> dict:
    """D6 terminal condition: ONE scalar per event, whole-day flanking rate.

    Not time-of-day matched -- the flanking material is too thin to estimate an
    intraday shape (D6). Only sessions the canonical trades_bitmap marks
    collected contribute, to both numerator and denominator.
    """
    d = read_event_trades(cfg, ticker, date, mom, offsets=FLANK)
    n_prints = 0.0
    n_size = 0.0
    n_seconds = 0.0
    used = []
    for o in FLANK:
        w = session_window(date, o)
        if w is None:
            continue
        collected = (bitmap[o + 3] == "1") if isinstance(bitmap, str) and len(bitmap) == 7 \
            else (d.get(o) is not None and len(d.get(o)) > 0)
        if not collected:
            continue
        used.append(o)
        sub = d.get(o)
        if sub is not None and len(sub):
            n_prints += len(sub)
            n_size += float(sub["size"].sum())
        n_seconds += w["span_minutes"] * 60.0
    if not used or n_seconds <= 0:
        return {"baseline_print_per_sec": np.nan, "baseline_volume_per_sec": np.nan,
                "baseline_undefined": True, "baseline_sessions_used": 0,
                "baseline_flanking_prints": 0}
    if n_prints == 0:
        return {"baseline_print_per_sec": np.nan, "baseline_volume_per_sec": np.nan,
                "baseline_undefined": True, "baseline_sessions_used": len(used),
                "baseline_flanking_prints": 0}
    return {"baseline_print_per_sec": n_prints / n_seconds,
            "baseline_volume_per_sec": n_size / n_seconds,
            "baseline_undefined": False, "baseline_sessions_used": len(used),
            "baseline_flanking_prints": int(n_prints)}


def build_grid(cfg) -> np.ndarray:
    g = cfg["charts"]["profile_display_grid"]
    half = (g["n_points"] - 1) // 2
    pos = np.logspace(np.log10(g["log_seconds_min"]), np.log10(g["log_seconds_max"]), half)
    return np.concatenate((-pos[::-1], [0.0], pos))


def main() -> int:
    cfg = load_config_v2()
    chash = config_hash_v2()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_frozen_cohort(cfg)
    est = cfg["estimator"]
    ts_cfg = cfg["timescales"]
    k_grid, k_ref = est["k_grid"], est["k_reference"]
    floor_s = est["zero_span_floor_seconds"]
    fractions = ts_cfg["decay_fractions"]
    frac_labels = ts_cfg["decay_fraction_labels"]
    multiples = ts_cfg["terminal_condition"]["multiples"]
    polls = cfg["detection_anchor"]["poll_intervals_seconds"]
    thr_ref = cfg["detection_anchor"]["threshold_reference_point"]
    margin = cfg["failure_criteria"]["row_4"]["margin_seconds"]
    grid = build_grid(cfg)

    det = pd.read_parquet(os.path.join(out_dir, "v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], thr_ref)].set_index(
        [c for c in COHORT_KEY])

    rows, prof_rows = [], []
    t_start = time.perf_counter()
    per_event_seconds = []

    for i, r in enumerate(cohort.itertuples(index=False), 1):
        t_ev = time.perf_counter()
        w = session_window(r.event_date_canonical, 0)
        d0 = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d0.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts_raw = t0["sip_timestamp"].to_numpy()
        sz_raw = t0["size"].to_numpy(dtype=float)
        bl = scalar_baseline(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                             getattr(r, "trades_bitmap", None))

        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        drow = det.loc[key] if key in det.index else None
        if isinstance(drow, pd.DataFrame):
            drow = drow.iloc[0]

        base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                "n_prints_t0": int(ts_raw.size),
                "baseline_print_per_sec": bl["baseline_print_per_sec"],
                "baseline_volume_per_sec": bl["baseline_volume_per_sec"],
                "baseline_undefined": bl["baseline_undefined"],
                "baseline_sessions_used": bl["baseline_sessions_used"],
                "never_crosses": bool(drow["never_crosses"]) if drow is not None else True}

        collapsed_ts, collapsed_sz, n_collapsed = collapse_ties(ts_raw, sz_raw)
        variants = {"as_is": (ts_raw, sz_raw, k_grid),
                    "collapse_same_timestamp": (collapsed_ts, collapsed_sz, [k_ref])}

        for vname, (tsv, szv, ks) in variants.items():
            for k in ks:
                if k > tsv.size:
                    rows.append({**base, "tie_variant": vname, "k": k, "observable": None,
                                 "k_exceeds_n": True})
                    continue
                res = knn_rate(tsv, szv, k, floor_s)
                for obs in OBSERVABLES:
                    rate = res[obs]
                    pk = int(np.argmax(rate))
                    peak_rate = float(rate[pk])
                    peak_ns = int(tsv[pk])
                    norm = rate / peak_rate if peak_rate > 0 else np.zeros_like(rate)

                    rec = {**base, "tie_variant": vname, "k": k, "observable": obs,
                           "k_exceeds_n": False, "n_spans_floored": res["n_spans_floored"],
                           "n_collapsed": n_collapsed if vname != "as_is" else 0,
                           "peak_idx": pk, "peak_ns": peak_ns,
                           "peak_rate_abs": peak_rate,
                           "peak_seconds_from_open": float(peak_ns - w["start_ns"]) / 1e9,
                           "session_seconds": float(w["span_minutes"] * 60),
                           "peak_seconds_to_window_end": float(w["end_ns"] - peak_ns) / 1e9,
                           }
                    rec["peak_near_edge"] = bool(
                        rec["peak_seconds_from_open"] <= margin
                        or rec["peak_seconds_to_window_end"] <= margin)

                    # T3c decay timescales
                    for frac, lab in zip(fractions, frac_labels):
                        el, never = first_sustained_crossing(norm, tsv, pk, frac)
                        rec[f"decay_{lab}_s"] = el
                        rec[f"decay_{lab}_never"] = never

                    # T3d terminal condition
                    b = bl["baseline_print_per_sec"] if obs == "print_rate" else bl["baseline_volume_per_sec"]
                    for mult in multiples:
                        if bl["baseline_undefined"] or not np.isfinite(b) or b <= 0:
                            rec[f"terminal_{mult:g}x_s"] = None
                            rec[f"terminal_{mult:g}x_undefined"] = True
                        else:
                            el, never = first_sustained_crossing(rate, tsv, pk, mult * b)
                            rec[f"terminal_{mult:g}x_s"] = el
                            rec[f"terminal_{mult:g}x_undefined"] = bool(never)
                        rec[f"terminal_{mult:g}x_never"] = rec.get(f"terminal_{mult:g}x_undefined")

                    # T3a detection-to-peak, SIGNED, per poll interval. Never clipped.
                    for p in polls:
                        dv = drow[f"det_ns_poll{p}"] if drow is not None else None
                        if dv is None or (isinstance(dv, float) and not np.isfinite(dv)) or pd.isna(dv):
                            rec[f"det_to_peak_s_poll{p}"] = None
                        else:
                            rec[f"det_to_peak_s_poll{p}"] = float(peak_ns - int(dv)) / 1e9
                    rows.append(rec)

                    # profile curves: as_is variant only, both anchors
                    if vname == "as_is":
                        rel_peak = (tsv - peak_ns) / 1e9
                        vals = np.interp(grid, rel_peak, norm, left=np.nan, right=np.nan)
                        for gi, gv in enumerate(grid):
                            if np.isfinite(vals[gi]):
                                prof_rows.append({
                                    "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                                    "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                                    "observable": obs, "k": k, "anchor": "peak",
                                    "t_seconds": float(gv), "normalized_rate": float(vals[gi]),
                                    "abs_rate": float(vals[gi] * peak_rate)})
                        dv = drow[f"det_ns_poll{cfg['detection_anchor']['poll_interval_reference_point']}"] \
                            if drow is not None else None
                        if dv is not None and not pd.isna(dv):
                            rel_det = (tsv - int(dv)) / 1e9
                            vd = np.interp(grid, rel_det, norm, left=np.nan, right=np.nan)
                            for gi, gv in enumerate(grid):
                                if np.isfinite(vd[gi]):
                                    prof_rows.append({
                                        "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                                        "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                                        "observable": obs, "k": k, "anchor": "detection",
                                        "t_seconds": float(gv), "normalized_rate": float(vd[gi]),
                                        "abs_rate": float(vd[gi] * peak_rate)})

        per_event_seconds.append(time.perf_counter() - t_ev)
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t_start:.0f}s)", flush=True)

    m = pd.DataFrame(rows)
    p = pd.DataFrame(prof_rows)
    m.to_parquet(os.path.join(out_dir, OUT_METRICS), index=False)
    p.to_parquet(os.path.join(out_dir, OUT_PROFILES), index=False)

    # ------------------------------------------------------------ summaries
    m["k_exceeds_n"] = m["k_exceeds_n"].fillna(False).astype(bool)
    ref = m[(m["tie_variant"] == "as_is") & (m["k"] == k_ref)
            & m["cohort_group"].isin(POOLED) & (~m["k_exceeds_n"])]

    def obs_block(sub):
        out = {"n_events": int(len(sub)),
               "peak_rate_abs": quantiles(sub["peak_rate_abs"]),
               "peak_seconds_from_open": quantiles(sub["peak_seconds_from_open"]),
               "n_peak_near_edge": int(sub["peak_near_edge"].fillna(False).astype(bool).sum())}
        for lab in frac_labels:
            # object-dtype booleans: `~` on them yields -1, not negation. Coerce first.
            never = sub[f"decay_{lab}_never"].fillna(True).astype(bool)
            v = sub.loc[~never, f"decay_{lab}_s"]
            out[f"decay_{lab}_s"] = quantiles(v)
            out[f"decay_{lab}_never_reached"] = int(never.sum())
        for mult in multiples:
            und = sub[f"terminal_{mult:g}x_undefined"].fillna(True).astype(bool)
            v = sub.loc[~und, f"terminal_{mult:g}x_s"]
            out[f"terminal_{mult:g}x_s"] = quantiles(v)
            out[f"terminal_{mult:g}x_undefined"] = int(und.sum())
        for pp in polls:
            v = sub[f"det_to_peak_s_poll{pp}"].dropna()
            out[f"det_to_peak_s_poll{pp}"] = {
                **quantiles(v),
                "n_negative": int((v < 0).sum()),
                "share_negative": float((v < 0).mean()) if v.size else None,
                "label": "instantaneous — UPPER BOUND ON RUNWAY, physically impossible"
                         if pp == 0 else f"{pp}s poll",
            }
        return out

    summary = {
        "phase": "10", "version": "v2", "task": "T1-T4", "config_hash": chash,
        "method": {
            "estimator": est["variant"], "definition": est["definition"],
            "why": est["why_this_family"],
            "k_grid": k_grid, "k_reference": k_ref,
            "k_reference_note": est["k_reference_note"],
            "observables": list(OBSERVABLES),
            "observables_note": "co-equal, reported side by side throughout; neither is a check on "
                                "the other",
            "anchor_independence": cfg["reporting"]["anchor_independence_statement"],
            "normalization": ts_cfg["normalization"],
        },
        "pooled_reference": {obs: obs_block(ref[ref["observable"] == obs]) for obs in OBSERVABLES},
        "by_group_reference": {
            g: {obs: obs_block(sub[sub["observable"] == obs]) for obs in OBSERVABLES}
            for g, sub in m[(m["tie_variant"] == "as_is") & (m["k"] == k_ref) & (~m["k_exceeds_n"])]
            .groupby("cohort_group")
        },
        "by_detection_segment_reference": {},
        "across_k": {
            obs: {
                f"k{k}": {
                    "n_events": int(((m["tie_variant"] == "as_is") & (m["k"] == k)
                                     & (m["observable"] == obs) & m["cohort_group"].isin(POOLED)
                                     & (~m["k_exceeds_n"])).sum()),
                    "n_k_exceeds_n": int(((m["tie_variant"] == "as_is") & (m["k"] == k)
                                          & m["cohort_group"].isin(POOLED) & m["k_exceeds_n"]).sum()),
                    "decay_half_s": quantiles(
                        m.loc[(m["tie_variant"] == "as_is") & (m["k"] == k) & (m["observable"] == obs)
                              & m["cohort_group"].isin(POOLED) & (~m["k_exceeds_n"])
                              & (~m["decay_half_never"].fillna(True).astype(bool)), "decay_half_s"]),
                    "peak_seconds_from_open": quantiles(
                        m.loc[(m["tie_variant"] == "as_is") & (m["k"] == k) & (m["observable"] == obs)
                              & m["cohort_group"].isin(POOLED) & (~m["k_exceeds_n"]),
                              "peak_seconds_from_open"]),
                } for k in k_grid
            } for obs in OBSERVABLES
        },
        "baseline": {
            "n_undefined": int(m.drop_duplicates(COHORT_KEY)["baseline_undefined"].fillna(False).astype(bool).sum()),
            "rule": ts_cfg["terminal_condition"]["baseline"],
        },
        "timing": {
            "total_seconds": round(time.perf_counter() - t_start, 1),
            "max_seconds_per_event": round(float(np.max(per_event_seconds)), 2),
            "median_seconds_per_event": round(float(np.median(per_event_seconds)), 3),
            "ceiling_per_event": cfg["runtime_ceilings"]["estimator_seconds_per_event_all_k_all_observables"],
            "ceiling_aggregate": cfg["runtime_ceilings"]["estimator_seconds_aggregate"],
        },
        "source": "research/phase_10/v2_t1_t4_profile.py:main",
        "artifacts": [f"{cfg['paths']['out_artifacts']}{OUT_METRICS}",
                      f"{cfg['paths']['out_artifacts']}{OUT_PROFILES}"],
    }

    # detection-segment conditioning (R1.3d)
    segref = det.reset_index()[COHORT_KEY + [f"det_segment_poll{cfg['detection_anchor']['poll_interval_reference_point']}"]]
    segref.columns = COHORT_KEY + ["det_segment"]
    refseg = ref.merge(segref, on=COHORT_KEY, how="left")
    summary["by_detection_segment_reference"] = {
        str(seg): {obs: obs_block(sub[sub["observable"] == obs]) for obs in OBSERVABLES}
        for seg, sub in refseg.groupby("det_segment")
    }

    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    for obs in OBSERVABLES:
        b = summary["pooled_reference"][obs]
        print(f"{obs}: n={b['n_events']} peak@{b['peak_seconds_from_open']['q50']:,.0f}s "
              f"decay_half med {b['decay_half_s']['q50']:,.1f}s "
              f"(never {b['decay_half_never_reached']}), "
              f"det_to_peak poll1 med {b['det_to_peak_s_poll1']['q50']:,.1f}s "
              f"neg {b['det_to_peak_s_poll1']['share_negative']:.3f}")
    t = summary["timing"]
    print(f"runtime {t['total_seconds']}s total, max/event {t['max_seconds_per_event']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
