"""
Phase 10 v3 T2-T4 -- envelope, sub-burst identification, and the Arm A test.

  T2  envelope at the GATE-DERIVED scale (the T1 knee, per segment). Not a free
      parameter, not swept independently of the gate. Sensitivity is evaluated
      only INSIDE the knee's bootstrap interval.
  T3  sub-bursts = excursions of the fast rate above the event's OWN envelope.
      The rule operates on the RATIO rate/envelope, never on rate against a
      constant -- the defect D8 exists to prevent.
  T4  the Arm A test: is sub-burst count a restatement of print count?

Both curves come from the v2 adaptive centred k-block kNN estimator, reused.

Usage: .venv/Scripts/python.exe research/phase_10/v3_t2_t4_subbursts.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t5_sensitivity import interval_jaccard  # noqa: E402
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, knn_rate, load_frozen_cohort, quantiles, read_event_trades,
    rel, session_window, write_json,
)
from v3_t1_gate import cfg_hash, load_cfg  # noqa: E402

OUT_SUB = "v3_t3_subbursts.parquet"
OUT_EV = "v3_t3_event_metrics.parquet"
OUT_SUMMARY = "v3_t2_t4_summary.json"
OBS = ("print_rate", "volume_rate")


def hysteresis_runs(ratio: np.ndarray, on: float, off: float) -> list[tuple[int, int]]:
    """Schmitt trigger on rate/envelope. Returns inclusive index runs."""
    state = np.zeros(ratio.size, dtype=np.int8)
    cur = 0
    for i in range(ratio.size):
        if cur == 0:
            if ratio[i] >= on:
                cur = 1
        elif ratio[i] < off:
            cur = 0
        state[i] = cur
    if state.size == 0:
        return []
    pad = np.concatenate(([0], state, [0]))
    e = np.diff(pad)
    return list(zip(np.flatnonzero(e == 1).tolist(), (np.flatnonzero(e == -1) - 1).tolist()))


def subbursts_for(ts, px, sz, k_env, k_fast, knee_s, exc, floor_s) -> dict:
    """One (event, observable) decomposition. Returns intervals + diagnostics."""
    n = ts.size
    k_env = int(np.clip(k_env, 5, max(5, n - 1)))
    if n <= k_env or n <= k_fast:
        return {"ok": False, "reason": f"n={n} <= k_env={k_env} or k_fast={k_fast}"}
    fast = knn_rate(ts, sz, k_fast, floor_s)
    env = knn_rate(ts, sz, k_env, floor_s)
    return {"ok": True, "k_env": k_env, "fast": fast, "env": env}


def resolve(ts, ratio, knee_s, exc) -> list[dict]:
    """hysteresis -> merge -> drop-short, all at gate-derived scales."""
    raw = hysteresis_runs(ratio, exc["on_multiplier"], exc["off_multiplier"])
    merge_gap = exc["merge_gap_fraction_of_knee"] * knee_s
    min_dur = exc["min_duration_fraction_of_knee"] * knee_s
    merged: list[list[int]] = []
    for a, b in raw:
        if merged and (ts[a] - ts[merged[-1][1]]) / 1e9 < merge_gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = []
    for a, b in merged:
        dur = float(ts[b] - ts[a]) / 1e9
        if dur < min_dur:
            continue
        out.append({"start_idx": int(a), "end_idx": int(b),
                    "start_ns": int(ts[a]), "end_ns": int(ts[b]),
                    "duration_seconds": dur})
    return out


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    gate = json.load(open(os.path.join(art, "v3_t1_gate.json"), encoding="utf-8"))
    cohort = load_frozen_cohort({"paths": {"cohort_manifest": cfg["paths"]["cohort_manifest"]},
                                 "cohort": {"content_hash": cfg["cohort"]["content_hash"]}})
    exc = cfg["excursion"]
    k_fast = cfg["envelope"]["fast_k"]
    floor_s = 1e-09
    fallback_seg = "rth"

    det = pd.read_parquet(rel(cfg["paths"]["detection"]))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], cfg["detection_anchor"]["threshold"])]
    det = det.set_index(COHORT_KEY)

    v2m = pd.read_parquet(rel(cfg["paths"]["v2_event_metrics"]))
    v2m["event_date_canonical"] = v2m["event_date_canonical"].astype(str)
    v2m = v2m[(v2m["tie_variant"] == "as_is") & (v2m["k"] == k_fast)]
    peak = v2m.set_index(COHORT_KEY + ["observable"])["peak_ns"]

    def knee_for(obs, seg, which="fit"):
        f = gate["segment_fits"].get(obs, {}).get(
            seg if seg in gate["segment_fits"].get(obs, {}) else fallback_seg)
        if which == "fit":
            return f["fit"]["knee_seconds"]
        lo, hi = f["knee_interval_seconds"]
        return lo, hi

    sub_rows, ev_rows = [], []
    t0all = time.perf_counter()
    for i, r in enumerate(cohort.itertuples(index=False), 1):
        w = session_window(r.event_date_canonical, 0)
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts = t0["sip_timestamp"].to_numpy()
        px = t0["price"].to_numpy(dtype=float)
        sz = t0["size"].to_numpy(dtype=float)
        n = ts.size
        span = float(ts[-1] - ts[0]) / 1e9 if n > 1 else 0.0
        sess_span = w["span_minutes"] * 60.0
        sess_move = float(px[-1] - px[0])
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        drow = det.loc[key] if key in det.index else None
        if isinstance(drow, pd.DataFrame):
            drow = drow.iloc[0]
        seg = (drow["det_segment_poll1"] if drow is not None
               and pd.notna(drow["det_segment_poll1"]) else "no_detection")
        det_ns = (int(drow["det_ns_poll1"]) if drow is not None
                  and pd.notna(drow["det_ns_poll1"]) else None)

        for obs in OBS:
            knee = knee_for(obs, seg)
            lo, hi = knee_for(obs, seg, "interval")
            base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                    "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                    "observable": obs, "segment": seg, "knee_seconds": knee,
                    "n_prints_t0": n, "session_span_seconds": sess_span,
                    "print_span_seconds": span, "session_move": sess_move}

            k_env = round(n / max(sess_span, 1.0) * knee)
            res = subbursts_for(ts, px, sz, k_env, k_fast, knee, exc, floor_s)
            if not res["ok"]:
                ev_rows.append({**base, "ok": False, "reason": res["reason"], "n_subbursts": 0})
                continue
            fast_v = res["fast"][obs]
            env_v = res["env"][obs]
            ratio = fast_v / np.maximum(env_v, 1e-30)
            sbs = resolve(ts, ratio, knee, exc)

            # sensitivity INSIDE the knee interval only (T2b / failure row 3)
            jac = None
            if lo and hi and hi > lo:
                sets = []
                for kn_s in (lo, hi):
                    ke = int(np.clip(round(n / max(sess_span, 1.0) * kn_s), 5, max(5, n - 1)))
                    if n <= ke:
                        sets.append(None); continue
                    e2 = knn_rate(ts, sz, ke, floor_s)[obs]
                    r2 = fast_v / np.maximum(e2, 1e-30)
                    sets.append(resolve(ts, r2, kn_s, exc))
                if sets[0] is not None and sets[1] is not None:
                    A = np.array([[s["start_ns"] / 1e9, s["end_ns"] / 1e9] for s in sets[0]]
                                 ) if sets[0] else np.zeros((0, 2))
                    B = np.array([[s["start_ns"] / 1e9, s["end_ns"] / 1e9] for s in sets[1]]
                                 ) if sets[1] else np.zeros((0, 2))
                    jac = interval_jaccard(A, B)[0]

            pk_ns = peak.get((r.ticker, r.event_date_canonical, r.momentum_pct, obs))
            tot_prints_in = 0
            for j, s in enumerate(sbs):
                a, b = s["start_idx"], s["end_idx"]
                p = px[a:b + 1]
                move = float(p[-1] - p[0])
                tot_prints_in += (b - a + 1)
                sub_rows.append({
                    **base, "subburst_index": j, **s,
                    "n_prints": int(b - a + 1),
                    "share_session_prints": (b - a + 1) / n,
                    "volume": float(sz[a:b + 1].sum()),
                    "subburst_move": move,
                    "move_share": (move / sess_move) if sess_move != 0 else np.nan,
                    "high_price": float(p.max()),
                    "seconds_from_detection": (float(s["start_ns"] - det_ns) / 1e9
                                               if det_ns is not None else np.nan),
                    "seconds_from_peak": (float(s["start_ns"] - int(pk_ns)) / 1e9
                                          if pk_ns is not None and pd.notna(pk_ns) else np.nan),
                    "spacing_seconds": (float(s["start_ns"] - sbs[j - 1]["end_ns"]) / 1e9
                                        if j > 0 else np.nan),
                })
            covered = sum(s["duration_seconds"] for s in sbs)
            ev_rows.append({
                **base, "ok": True, "reason": None, "k_env": res["k_env"], "k_fast": k_fast,
                "n_subbursts": len(sbs),
                "subburst_covered_seconds": covered,
                "share_session_seconds_in_subbursts": covered / span if span > 0 else np.nan,
                "share_session_prints_in_subbursts": tot_prints_in / n,
                "peak_rate_abs": float(fast_v.max()),
                "envelope_median": float(np.median(env_v)),
                "ratio_median": float(np.median(ratio)),
                "ratio_max": float(ratio.max()),
                "knee_interval_low": lo, "knee_interval_high": hi,
                "knee_interval_jaccard": jac,
                "session_move_defined": bool(sess_move != 0),
                "largest_subburst_span_share": (max((s["duration_seconds"] for s in sbs), default=0)
                                                / span if span > 0 else np.nan),
            })
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t0all:.0f}s)", flush=True)

    sub = pd.DataFrame(sub_rows)
    ev = pd.DataFrame(ev_rows)
    sub.to_parquet(os.path.join(art, OUT_SUB), index=False)
    ev.to_parquet(os.path.join(art, OUT_EV), index=False)

    # ------------------------------------------------------------ T4 Arm A test
    fc = cfg["failure_criteria"]
    pooled = ev[ev["cohort_group"].isin(POOLED) & ev["ok"].fillna(False)]

    def arm_a(sub_df):
        out = {}
        for var, col in (("t0_print_count", "n_prints_t0"),
                         ("session_duration_seconds", "print_span_seconds"),
                         ("absolute_peak_rate", "peak_rate_abs")):
            x = sub_df[col].to_numpy(dtype=float)
            y = sub_df["n_subbursts"].to_numpy(dtype=float)
            m = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
            if m.sum() < 5:
                out[var] = {"n": int(m.sum()), "spearman": None, "loglog_slope": None}
                continue
            sp = sps.spearmanr(sub_df[col][np.isfinite(x)], sub_df["n_subbursts"][np.isfinite(x)])
            slope = float(np.polyfit(np.log10(x[m]), np.log10(y[m]), 1)[0])
            out[var] = {"n": int(m.sum()), "spearman": float(sp.statistic),
                        "spearman_pvalue": float(sp.pvalue), "loglog_slope": slope}
        return out

    t4 = {"pooled": {}, "by_segment": {}}
    for obs in OBS:
        s = pooled[pooled["observable"] == obs]
        t4["pooled"][obs] = {**arm_a(s), "n_events": int(len(s)),
                             "subbursts_per_1000_prints": quantiles(
                                 s["n_subbursts"] / (s["n_prints_t0"] / 1000.0)),
                             "subbursts_per_hour": quantiles(
                                 s["n_subbursts"] / (s["print_span_seconds"] / 3600.0))}
        t4["by_segment"][obs] = {
            str(g): {**arm_a(gg), "n_events": int(len(gg))}
            for g, gg in s.groupby("segment") if len(gg) >= 5}

    rows = []
    for obs in OBS:
        a = t4["pooled"][obs]["t0_print_count"]
        sp, sl = a["spearman"], a["loglog_slope"]
        rows.append({"row": 1, "observable": obs,
                     "spearman_vs_print_count": sp, "loglog_slope": sl,
                     "threshold_max_spearman": fc["row_1"]["threshold_max_spearman"],
                     "threshold_max_slope": fc["row_1"]["threshold_max_slope"],
                     "arm_a_reference": {"spearman": 0.96, "slope": 0.85},
                     "pass": bool(sp is not None and sl is not None
                                  and sp <= fc["row_1"]["threshold_max_spearman"]
                                  and sl <= fc["row_1"]["threshold_max_slope"])})

    summary = {
        "phase": "10", "version": "v3", "task": "T2-T4", "config_hash": chash,
        "envelope": {"scale_rule": cfg["envelope"]["scale_rule"],
                     "k_from_knee": cfg["envelope"]["k_from_knee"],
                     "fast_k": k_fast,
                     "knee_used_seconds": {obs: {s: knee_for(obs, s) for s in ("premarket", "rth")}
                                           for obs in OBS},
                     "k_env": {obs: quantiles(pooled.loc[pooled["observable"] == obs, "k_env"])
                               for obs in OBS}},
        "excursion_rule": cfg["excursion"]["rule"],
        "t2b_knee_interval_sensitivity": {
            obs: {"n": int(pooled.loc[pooled["observable"] == obs, "knee_interval_jaccard"].notna().sum()),
                  "jaccard": quantiles(pooled.loc[pooled["observable"] == obs, "knee_interval_jaccard"])}
            for obs in OBS},
        "t3_counts": {obs: {"n_events": int((pooled["observable"] == obs).sum()),
                            "n_subbursts": int(len(sub[sub["observable"] == obs])),
                            "count": quantiles(pooled.loc[pooled["observable"] == obs, "n_subbursts"]),
                            "by_segment": {str(g): quantiles(gg["n_subbursts"])
                                           for g, gg in pooled[pooled["observable"] == obs].groupby("segment")}}
                      for obs in OBS},
        "t4_arm_a_test": t4,
        "failure_row_1": {"mode": fc["row_1"]["mode"], "rows": rows,
                          "any_failed": any(not r["pass"] for r in rows)},
        "timing": {"total_seconds": round(time.perf_counter() - t0all, 1)},
        "source": "research/phase_10/v3_t2_t4_subbursts.py:main",
        "artifacts": [f"{cfg['paths']['out_artifacts']}{OUT_SUB}",
                      f"{cfg['paths']['out_artifacts']}{OUT_EV}"],
    }
    write_json(os.path.join(art, OUT_SUMMARY), summary)

    for obs in OBS:
        c = summary["t3_counts"][obs]
        print(f"{obs}: {c['n_events']} events, {c['n_subbursts']:,} sub-bursts, "
              f"count median {c['count']['q50']:.0f} (IQR {c['count']['q25']:.0f}-{c['count']['q75']:.0f})")
    print("\n=== T4 ARM A TEST (failure row 1) ===")
    for r in rows:
        print(f"  {r['observable']:12s} Spearman vs print count {r['spearman_vs_print_count']:+.4f} "
              f"(<= {r['threshold_max_spearman']}), log-log slope {r['loglog_slope']:+.4f} "
              f"(<= {r['threshold_max_slope']}) -> {'PASS' if r['pass'] else 'FAIL'}")
        for v in ("session_duration_seconds", "absolute_peak_rate"):
            a = t4["pooled"][r["observable"]][v]
            print(f"       vs {v:26s} Spearman {a['spearman']:+.4f}  slope {a['loglog_slope']:+.4f}")
    return 0 if not summary["failure_row_1"]["any_failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
