"""
Phase 10 v3 T1 -- the scale-separation gate.

Allan and Fano factors as functions of counting-window duration, per event, per
observable, per detection segment, over a dyadic ladder spanning 5.7 orders of
magnitude.

Both are computed DIRECTLY on the point process. No intensity estimation, no
smoothing bandwidth, no threshold. That independence is the point: the gate must
not inherit the machinery it gates (D8).

  Fano  F(T) = Var(N_i(T)) / E(N_i(T))                 Poisson -> 1 flat
  Allan A(T) = E[(N_{i+1}-N_i)^2] / (2 E[N])           Poisson -> 1 flat

Allan is primary because it tolerates a slowly-varying underlying rate -- which
is exactly the envelope being separated out. Fano is reported alongside and will
be inflated by the trend; that inflation is expected and is not evidence of
clustering.

Read on log-log: a straight power law with no knee means self-similar, no
characteristic scale, gate FAILS (row 6). A knee means the scale exists and its
location is the envelope/sub-burst boundary -- derived, not chosen.

Usage: .venv/Scripts/python.exe research/phase_10/v3_t1_gate.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, load_frozen_cohort, quantiles, read_event_trades, rel,
    session_window, write_json,
)

OUT_CURVES = "v3_t1_gate_curves.parquet"
OUT_KNEES = "v3_t1_gate_knees.parquet"
OUT_SUMMARY = "v3_t1_gate.json"


def load_cfg() -> dict:
    with open(rel("config/phase_10_v3.json"), encoding="utf-8") as f:
        return json.load(f)


def cfg_hash() -> str:
    import hashlib
    with open(rel("config/phase_10_v3.json"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def allan_fano(ts_ns: np.ndarray, weights: np.ndarray | None, start_ns: int,
               end_ns: int, T: float, min_windows: int) -> dict | None:
    """Counts in NON-OVERLAPPING windows of duration T tiling [start, end)."""
    span = (end_ns - start_ns) / 1e9
    n_win = int(np.floor(span / T))
    if n_win < min_windows:
        return None
    idx = ((ts_ns - start_ns) / 1e9 / T).astype(np.int64)
    keep = (idx >= 0) & (idx < n_win)
    idx = idx[keep]
    if weights is None:
        counts = np.bincount(idx, minlength=n_win).astype(np.float64)
    else:
        counts = np.bincount(idx, weights=np.asarray(weights, float)[keep],
                             minlength=n_win).astype(np.float64)
    mean = counts.mean()
    if mean <= 0:
        return None
    fano = float(counts.var(ddof=1) / mean)
    d = np.diff(counts)
    allan = float((d ** 2).mean() / (2.0 * mean))
    return {"T": float(T), "n_windows": int(n_win), "mean_count": float(mean),
            "fano": fano, "allan": allan}


def broken_stick(x: np.ndarray, y: np.ndarray) -> dict:
    """Two-segment CONTINUOUS piecewise-linear least squares vs a single line.

    Exhaustive search over interior breakpoints -- deterministic, no optimizer
    seed, no bandwidth. Returns both fits with BIC so a knee is TESTED rather
    than assumed.
    """
    n = x.size
    if n < 6:
        return {"ok": False, "reason": f"only {n} usable rungs"}

    A1 = np.vstack([np.ones(n), x]).T
    c1, res1, *_ = np.linalg.lstsq(A1, y, rcond=None)
    rss1 = float(((y - A1 @ c1) ** 2).sum())
    bic1 = n * np.log(max(rss1, 1e-300) / n) + 2 * np.log(n)

    best = None
    for i in range(2, n - 2):
        bp = x[i]
        # continuous hinge basis: 1, x, max(0, x - bp)
        A2 = np.vstack([np.ones(n), x, np.maximum(0.0, x - bp)]).T
        c2, *_ = np.linalg.lstsq(A2, y, rcond=None)
        rss2 = float(((y - A2 @ c2) ** 2).sum())
        if best is None or rss2 < best["rss"]:
            best = {"rss": rss2, "bp": float(bp), "coef": c2, "i": i}
    bic2 = n * np.log(max(best["rss"], 1e-300) / n) + 4 * np.log(n)

    s1 = float(best["coef"][1])
    s2 = float(best["coef"][1] + best["coef"][2])
    return {"ok": True, "n_rungs": int(n),
            "single_slope": float(c1[1]), "single_rss": rss1, "single_bic": float(bic1),
            "knee_log10T": best["bp"], "knee_seconds": float(10 ** best["bp"]),
            "slope_before": s1, "slope_after": s2, "slope_change": float(s2 - s1),
            "two_seg_rss": best["rss"], "two_seg_bic": float(bic2),
            "delta_bic": float(bic1 - bic2)}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_frozen_cohort({"paths": {"cohort_manifest": cfg["paths"]["cohort_manifest"]},
                                 "cohort": {"content_hash": cfg["cohort"]["content_hash"]}})
    lad = cfg["gate"]["ladder"]
    Ts = [lad["base_seconds"] * 2.0 ** e
          for e in range(lad["min_exponent"], lad["max_exponent"] + 1)]
    min_win = cfg["gate"]["min_windows_for_a_rung"]

    det = pd.read_parquet(rel(cfg["paths"]["detection"]))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], cfg["detection_anchor"]["threshold"])]
    seg = det[COHORT_KEY + ["det_segment_poll1"]].rename(
        columns={"det_segment_poll1": "segment"})

    rows, timings = [], []
    t0all = time.perf_counter()
    for i, r in enumerate(cohort.itertuples(index=False), 1):
        t_ev = time.perf_counter()
        w = session_window(r.event_date_canonical, 0)
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts = t0["sip_timestamp"].to_numpy()
        sz = t0["size"].to_numpy(dtype=float)
        for obs, wgt in (("print_rate", None), ("volume_rate", sz)):
            for T in Ts:
                res = allan_fano(ts, wgt, w["start_ns"], w["end_ns"], T, min_win)
                if res is None:
                    continue
                rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                             "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                             "observable": obs, **res})
        timings.append(time.perf_counter() - t_ev)
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t0all:.0f}s)", flush=True)

    cur = pd.DataFrame(rows).merge(seg, on=COHORT_KEY, how="left")
    cur["segment"] = cur["segment"].fillna("no_detection")
    cur.to_parquet(os.path.join(out_dir, OUT_CURVES), index=False)

    # ---------------- per-event knee
    kn = []
    for (tk, dt, mp, obs), g in cur[cur["cohort_group"].isin(POOLED)].groupby(
            ["ticker", "event_date_canonical", "momentum_pct", "observable"]):
        g = g.sort_values("T")
        m = g["allan"] > 0
        fit = broken_stick(np.log10(g.loc[m, "T"].to_numpy()),
                           np.log10(g.loc[m, "allan"].to_numpy()))
        kn.append({"ticker": tk, "event_date_canonical": dt, "momentum_pct": mp,
                   "observable": obs, "segment": g["segment"].iloc[0], **fit})
    knees = pd.DataFrame(kn)
    knees.to_parquet(os.path.join(out_dir, OUT_KNEES), index=False)

    # ---------------- segment-level fit on the median curve
    fc = cfg["failure_criteria"]
    seg_fits, rows6, rows7 = {}, [], []
    rng = np.random.default_rng(cfg["gate"]["knee_detection"]["bootstrap_seed"])
    reps = cfg["gate"]["knee_detection"]["bootstrap_reps"]

    # Gate rows are evaluated on the CONFIGURED segments only. `no_detection` is
    # not a segment -- it is the 2 never-crossing events carried per D7, which have
    # no detection anchor and therefore no segment. Row 7's observable is defined
    # "within a segment"; scoring it on a 2-event non-segment is a population
    # error, not a finding. Their curves are still computed and reported.
    valid_segments = set(cfg["segments"]["values"])
    for obs in cfg["observables"]["values"]:
        seg_fits[obs] = {}
        for sname, sub in cur[(cur["observable"] == obs)
                              & cur["cohort_group"].isin(POOLED)].groupby("segment"):
            is_segment = sname in valid_segments
            med = sub.groupby("T")["allan"].median()
            nper = sub.groupby("T")["allan"].size()
            m = med > 0
            fit = broken_stick(np.log10(med[m].index.to_numpy()),
                               np.log10(med[m].to_numpy()))
            ev = sub[COHORT_KEY].drop_duplicates()
            boots = []
            if fit.get("ok"):
                keys = list(map(tuple, ev.to_numpy()))
                sidx = sub.set_index(COHORT_KEY)
                for _ in range(reps):
                    pick = [keys[j] for j in rng.integers(0, len(keys), len(keys))]
                    try:
                        bs = sidx.loc[pick]
                    except KeyError:
                        continue
                    bm = bs.groupby("T")["allan"].median()
                    bm = bm[bm > 0]
                    bf = broken_stick(np.log10(bm.index.to_numpy()), np.log10(bm.to_numpy()))
                    if bf.get("ok"):
                        boots.append(bf["knee_log10T"])
            lo = float(np.percentile(boots, 2.5)) if boots else None
            hi = float(np.percentile(boots, 97.5)) if boots else None
            pe = knees[(knees["observable"] == obs) & (knees["segment"] == sname)
                       & knees["ok"].fillna(False)]
            iqr = (float(pe["knee_log10T"].quantile(0.75) - pe["knee_log10T"].quantile(0.25))
                   if len(pe) else None)
            seg_fits[obs][sname] = {
                "n_events": int(len(ev)), "n_rungs_used": int(m.sum()),
                "n_events_per_rung": {str(k): int(v) for k, v in nper.items()},
                "median_allan_by_T": {str(k): float(v) for k, v in med.items()},
                "fit": fit,
                "knee_interval_log10T": [lo, hi],
                "knee_interval_seconds": [None if lo is None else float(10 ** lo),
                                          None if hi is None else float(10 ** hi)],
                "n_bootstrap_ok": len(boots),
                "per_event_knee_log10T": quantiles(pe["knee_log10T"]) if len(pe) else None,
                "per_event_knee_iqr_decades": iqr,
            }
            seg_fits[obs][sname]["is_configured_segment"] = bool(is_segment)
            if fit.get("ok") and is_segment:
                d_bic, d_slope = fit["delta_bic"], abs(fit["slope_change"])
                p6 = (d_bic >= fc["row_6"]["threshold_min_delta_bic"]
                      and d_slope >= fc["row_6"]["threshold_min_slope_change"])
                rows6.append({"observable": obs, "segment": sname,
                              "delta_bic": d_bic, "slope_change": fit["slope_change"],
                              "single_slope": fit["single_slope"],
                              "slope_before": fit["slope_before"], "slope_after": fit["slope_after"],
                              "knee_seconds": fit["knee_seconds"], "pass": bool(p6)})
            if iqr is not None and is_segment:
                rows7.append({"observable": obs, "segment": sname, "iqr_decades": iqr,
                              "n_events": int(len(pe)),
                              "pass": bool(iqr <= fc["row_7"]["threshold_max_iqr_decades"])})

    # row 5 segment compatibility
    row5 = []
    for obs in cfg["observables"]["values"]:
        f = seg_fits.get(obs, {})
        if "premarket" in f and "rth" in f and f["premarket"]["fit"].get("ok") and f["rth"]["fit"].get("ok"):
            a, b = f["premarket"], f["rth"]
            sep = abs(a["fit"]["knee_log10T"] - b["fit"]["knee_log10T"])
            ia, ib = a["knee_interval_log10T"], b["knee_interval_log10T"]
            overlap = (None not in ia and None not in ib
                       and not (ia[1] < ib[0] or ib[1] < ia[0]))
            row5.append({"observable": obs, "separation_decades": sep,
                         "intervals_overlap": bool(overlap),
                         "pass": bool(sep <= fc["row_5"]["threshold_max_decades"] or overlap)})

    gate6 = all(r["pass"] for r in rows6) if rows6 else False
    gate7 = all(r["pass"] for r in rows7) if rows7 else False
    gate_pass = gate6 and gate7

    summary = {
        "phase": "10", "version": "v3", "task": "T1", "config_hash": chash,
        "what_this_is": cfg["gate"]["definitions"]["independence"],
        "primary_statistic": "allan_factor", "primary_why": cfg["gate"]["primary_why"],
        "ladder_seconds": Ts, "n_rungs": len(Ts),
        "n_events": int(cohort.shape[0]),
        "segment_counts": cur[cur["cohort_group"].isin(POOLED)][COHORT_KEY + ["segment"]]
                          .drop_duplicates().groupby("segment").size().to_dict(),
        "segment_fits": seg_fits,
        "gate_row_6": {"mode": fc["row_6"]["mode"], "thresholds": {
            "min_delta_bic": fc["row_6"]["threshold_min_delta_bic"],
            "min_slope_change": fc["row_6"]["threshold_min_slope_change"]},
            "rows": rows6, "pass": bool(gate6)},
        "gate_row_7": {"mode": fc["row_7"]["mode"],
                       "threshold_max_iqr_decades": fc["row_7"]["threshold_max_iqr_decades"],
                       "rows": rows7, "pass": bool(gate7)},
        "row_5_segment_compatibility": {"mode": fc["row_5"]["mode"], "rows": row5},
        "gate_pass": bool(gate_pass),
        "timing": {"total_seconds": round(time.perf_counter() - t0all, 1),
                   "max_seconds_per_event": round(float(np.max(timings)), 2) if timings else None,
                   "ceiling_per_event": cfg["runtime_ceilings"]["gate_seconds_per_event"]},
        "source": "research/phase_10/v3_t1_gate.py:main",
        "artifacts": [f"{cfg['paths']['out_artifacts']}{OUT_CURVES}",
                      f"{cfg['paths']['out_artifacts']}{OUT_KNEES}"],
    }
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    print("\n=== T1 SCALE-SEPARATION GATE ===")
    for r in rows6:
        print(f"  row6 {r['observable']:12s} {r['segment']:10s} "
              f"single-line slope {r['single_slope']:+.3f} | knee {r['knee_seconds']:>10.3f}s "
              f"slopes {r['slope_before']:+.3f}->{r['slope_after']:+.3f} "
              f"(change {r['slope_change']:+.3f}) dBIC {r['delta_bic']:8.2f} -> "
              f"{'PASS' if r['pass'] else 'FAIL'}")
    for r in rows7:
        print(f"  row7 {r['observable']:12s} {r['segment']:10s} per-event knee IQR "
              f"{r['iqr_decades']:.3f} decades (n={r['n_events']}) -> "
              f"{'PASS' if r['pass'] else 'FAIL'}")
    for r in row5:
        print(f"  row5 {r['observable']:12s} premarket-vs-rth separation "
              f"{r['separation_decades']:.3f} decades, intervals overlap "
              f"{r['intervals_overlap']} -> {'PASS' if r['pass'] else 'FAIL'}")
    print(f"\n  GATE: {'PASS' if gate_pass else 'FAIL'}")
    return 0 if gate_pass else 6


if __name__ == "__main__":
    raise SystemExit(main())
