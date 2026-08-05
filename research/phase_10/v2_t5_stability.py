"""
Phase 10 v2 T5 -- stability and the pre-registered failure criteria.

  T5a  timescale spread across the resolution grid, per event and pooled
  T5b  timescale agreement between the two observables, per event
  T5c  tie-variant agreement
  T5d  every pre-registered failure row, observed vs threshold, pass/fail

Standing lesson from v1, applied: a stability pass is not evidence of
correctness. Both v1 arms passed every numeric row while being wrong. Rows 1-9
exist to DISQUALIFY, never to endorse.

Usage: .venv/Scripts/python.exe research/phase_10/v2_t5_stability.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, config_hash_v2, load_config_v2, quantiles, rel, write_json,
)

OUT = "v2_t5_stability.json"


def main() -> int:
    cfg = load_config_v2()
    chash = config_hash_v2()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    fc = cfg["failure_criteria"]
    est = cfg["estimator"]
    k_grid, k_ref = est["k_grid"], est["k_reference"]
    polls = cfg["detection_anchor"]["poll_intervals_seconds"]

    m = pd.read_parquet(os.path.join(out_dir, "v2_t1_event_metrics.parquet"))
    m["event_date_canonical"] = m["event_date_canonical"].astype(str)
    m["k_exceeds_n"] = m["k_exceeds_n"].fillna(False).astype(bool)
    m["decay_half_never"] = m["decay_half_never"].fillna(True).astype(bool)
    ok = m[(~m["k_exceeds_n"]) & m["cohort_group"].isin(POOLED)]
    asis = ok[ok["tie_variant"] == "as_is"]

    def decay(obs, k, tie="as_is"):
        s = ok[(ok["observable"] == obs) & (ok["k"] == k) & (ok["tie_variant"] == tie)
               & (~ok["decay_half_never"])]
        return s.set_index(COHORT_KEY)["decay_half_s"]

    # ------------------------------------------------------------ T5a
    t5a = {}
    for obs in ("print_rate", "volume_rate"):
        per_k = {f"k{k}": quantiles(decay(obs, k)) for k in k_grid}
        wide = asis[(asis["observable"] == obs) & (~asis["decay_half_never"])].pivot_table(
            index=COHORT_KEY, columns="k", values="decay_half_s")
        wide = wide.dropna()
        spread = (wide.max(axis=1) / wide.min(axis=1)) if len(wide) else pd.Series(dtype=float)
        pk = asis[asis["observable"] == obs].pivot_table(
            index=COHORT_KEY, columns="k", values="peak_seconds_from_open").dropna()
        peak_move = (pk.max(axis=1) - pk.min(axis=1)) if len(pk) else pd.Series(dtype=float)
        t5a[obs] = {
            "pooled_median_decay_half_per_k": per_k,
            "per_event_across_k_ratio": quantiles(spread),
            "n_events_all_k_defined": int(len(wide)),
            "per_event_peak_location_range_seconds": quantiles(peak_move),
        }

    # ------------------------------------------------------------ T5b
    a = decay("print_rate", k_ref)
    b = decay("volume_rate", k_ref)
    joint = pd.concat([a.rename("print"), b.rename("volume")], axis=1).dropna()
    sp = sps.spearmanr(joint["print"], joint["volume"]) if len(joint) > 2 else None
    pa = asis[(asis["observable"] == "print_rate") & (asis["k"] == k_ref)].set_index(COHORT_KEY)["peak_seconds_from_open"]
    pb = asis[(asis["observable"] == "volume_rate") & (asis["k"] == k_ref)].set_index(COHORT_KEY)["peak_seconds_from_open"]
    pjoint = pd.concat([pa.rename("p"), pb.rename("v")], axis=1).dropna()
    t5b = {
        "n_events": int(len(joint)),
        "spearman_decay_half": float(sp.statistic) if sp is not None else None,
        "spearman_pvalue": float(sp.pvalue) if sp is not None else None,
        "decay_half_ratio_volume_over_print": quantiles(joint["volume"] / joint["print"]),
        "peak_location_difference_seconds": quantiles((pjoint["v"] - pjoint["p"]).abs()),
        "n_events_peak_within_60s": int(((pjoint["v"] - pjoint["p"]).abs() <= 60).sum()),
    }

    # ------------------------------------------------------------ T5c
    t5c = {}
    for obs in ("print_rate", "volume_rate"):
        aa = decay(obs, k_ref, "as_is")
        cc = decay(obs, k_ref, "collapse_same_timestamp")
        j = pd.concat([aa.rename("as_is"), cc.rename("collapse")], axis=1).dropna()
        lr = np.log(j["collapse"] / j["as_is"]).abs() if len(j) else pd.Series(dtype=float)
        pa_ = asis[(asis["observable"] == obs) & (asis["k"] == k_ref)].set_index(COHORT_KEY)["peak_seconds_from_open"]
        pc_ = ok[(ok["observable"] == obs) & (ok["k"] == k_ref)
                 & (ok["tie_variant"] == "collapse_same_timestamp")].set_index(COHORT_KEY)["peak_seconds_from_open"]
        pj = pd.concat([pa_.rename("a"), pc_.rename("c"), aa.rename("d")], axis=1).dropna()
        moved = ((pj["c"] - pj["a"]).abs() > pj["d"]) if len(pj) else pd.Series(dtype=bool)
        t5c[obs] = {
            "n_events": int(len(j)),
            "median_abs_log_ratio_decay": float(lr.median()) if len(lr) else None,
            "tolerance_max_median_abs_log_ratio": cfg["tie_handling"]["divergence_tolerance"]["max_median_abs_log_ratio_decay"],
            "share_peak_moved_beyond_decay": float(moved.mean()) if len(moved) else None,
            "tolerance_max_share_peak_moved": cfg["tie_handling"]["divergence_tolerance"]["max_share_peak_moved_beyond_decay"],
            "n_events_peak_identical": int((pj["c"] == pj["a"]).sum()) if len(pj) else 0,
        }
    tie_ok = all(
        (v["median_abs_log_ratio_decay"] is not None
         and v["median_abs_log_ratio_decay"] <= v["tolerance_max_median_abs_log_ratio"]
         and (v["share_peak_moved_beyond_decay"] or 0) <= v["tolerance_max_share_peak_moved"])
        for v in t5c.values())

    # ------------------------------------------------------------ T4 level conditioning
    lvl = {}
    for obs in ("print_rate", "volume_rate"):
        s = asis[(asis["observable"] == obs) & (asis["k"] == k_ref) & (~asis["decay_half_never"])].copy()
        if not len(s):
            continue
        s["quartile"] = pd.qcut(s["peak_rate_abs"].rank(method="first"), 4, labels=False)
        sp2 = sps.spearmanr(s["peak_rate_abs"], s["decay_half_s"])
        by_q = {int(q): {"n": int(len(g)), "peak_rate_abs": quantiles(g["peak_rate_abs"]),
                         "decay_half_s": quantiles(g["decay_half_s"])}
                for q, g in s.groupby("quartile")}
        top = by_q.get(3, {}).get("decay_half_s", {}).get("q50")
        bot = by_q.get(0, {}).get("decay_half_s", {}).get("q50")
        lvl[obs] = {
            "n_events": int(len(s)),
            "by_absolute_peak_rate_quartile": by_q,
            "spearman_decay_vs_peak_rate": float(sp2.statistic),
            "spearman_pvalue": float(sp2.pvalue),
            "top_over_bottom_quartile_ratio": (top / bot) if (top and bot) else None,
        }

    # ------------------------------------------------------------ failure rows
    det_j = json.load(open(os.path.join(out_dir, "v2_r13_detection.json"), encoding="utf-8"))
    p8_j = json.load(open(os.path.join(out_dir, "v2_r14_phase8_crosscheck.json"), encoding="utf-8"))
    prof = json.load(open(os.path.join(out_dir, "v2_t1_t4_summary.json"), encoding="utf-8"))
    rows = []

    kmin, kmax = min(k_grid), max(k_grid)
    for obs in ("print_rate", "volume_rate"):
        wide_hi = t5a[obs]["pooled_median_decay_half_per_k"][f"k{kmax}"]["q50"]
        wide_lo = t5a[obs]["pooled_median_decay_half_per_k"][f"k{kmin}"]["q50"]
        ratio = (wide_hi / wide_lo) if (wide_hi and wide_lo) else None
        thr = fc["row_1"]["threshold_max_ratio"]
        rows.append({"row": 1, "observable": obs, "mode": fc["row_1"]["mode"],
                     "observed": ratio, "threshold": f"<= {thr} and >= {1/thr:.3f}",
                     "pass": bool(ratio is not None and (1 / thr) <= ratio <= thr),
                     "detail": {"k_min": kmin, "k_max": kmax,
                                "median_decay_at_k_min": wide_lo, "median_decay_at_k_max": wide_hi}})

    thr2 = fc["row_2"]["threshold_min_spearman"]
    rows.append({"row": 2, "observable": "print_rate vs volume_rate", "mode": fc["row_2"]["mode"],
                 "observed": t5b["spearman_decay_half"], "threshold": f">= {thr2}",
                 "pass": bool(t5b["spearman_decay_half"] is not None and t5b["spearman_decay_half"] >= thr2),
                 "detail": {"n": t5b["n_events"]}})

    thr3 = fc["row_3"]["threshold_max_ratio"]
    for obs in lvl:
        rr = lvl[obs]["top_over_bottom_quartile_ratio"]
        rows.append({"row": 3, "observable": obs, "mode": fc["row_3"]["mode"],
                     "observed": rr, "threshold": f"<= {thr3} and >= {1/thr3:.3f}",
                     "pass": bool(rr is not None and (1 / thr3) <= rr <= thr3),
                     "detail": {"spearman": lvl[obs]["spearman_decay_vs_peak_rate"]}})

    thr4 = fc["row_4"]["threshold_max_share"]
    for obs in ("print_rate", "volume_rate"):
        s = asis[(asis["observable"] == obs) & (asis["k"] == k_ref)]
        share = float(s["peak_near_edge"].fillna(False).astype(bool).mean()) if len(s) else None
        rows.append({"row": 4, "observable": obs, "mode": fc["row_4"]["mode"],
                     "observed": share, "threshold": f"<= {thr4}",
                     "pass": bool(share is not None and share <= thr4),
                     "detail": {"n": int(len(s)), "margin_seconds": fc["row_4"]["margin_seconds"]}})

    thr5 = fc["row_5"]["threshold_max_share"]
    for obs in ("print_rate", "volume_rate"):
        s = asis[(asis["observable"] == obs) & (asis["k"] == k_ref)]
        share = float(s["decay_half_never"].mean()) if len(s) else None
        rows.append({"row": 5, "observable": obs, "mode": fc["row_5"]["mode"],
                     "observed": share, "threshold": f"<= {thr5}",
                     "pass": bool(share is not None and share <= thr5),
                     "detail": {"n": int(len(s))}})

    thr6 = fc["row_6"]["threshold_max_ratio"]
    for obs in ("print_rate", "volume_rate"):
        pk = asis[asis["observable"] == obs].pivot_table(
            index=COHORT_KEY, columns="k", values="peak_seconds_from_open").dropna()
        d = decay(obs, k_ref)
        j = pd.concat([(pk.max(axis=1) - pk.min(axis=1)).rename("move"), d.rename("decay")], axis=1).dropna()
        rr = float((j["move"] / j["decay"]).median()) if len(j) else None
        rows.append({"row": 6, "observable": obs, "mode": fc["row_6"]["mode"],
                     "observed": rr, "threshold": f"<= {thr6}",
                     "pass": bool(rr is not None and rr <= thr6),
                     "detail": {"n": int(len(j))}})

    r7 = det_j["failure_row_7"]
    rows.append({"row": 7, "observable": "never-crosses", "mode": r7["mode"],
                 "observed": r7["observed_share"], "threshold": f"<= {r7['threshold']}",
                 "pass": r7["pass"], "detail": {}})
    r8 = p8_j["failure_row_8"]
    rows.append({"row": 8, "observable": "phase-8 agreement", "mode": r8["mode"],
                 "observed": r8["observed_share_beyond_tolerance"],
                 "threshold": f"<= {r8['threshold']}", "pass": r8["pass"],
                 "detail": {"floor_comparison_beyond": r8["floor_comparison_share_beyond_tolerance"]}})

    thr9 = fc["row_9"]["threshold_max_ratio"]
    for obs in ("print_rate", "volume_rate"):
        pr = prof["pooled_reference"][obs]
        m0 = pr["det_to_peak_s_poll0"]["q50"]
        m60 = pr["det_to_peak_s_poll60"]["q50"]
        rr = (m0 / m60) if (m0 and m60) else None
        rows.append({"row": 9, "observable": obs, "mode": fc["row_9"]["mode"],
                     "observed": rr, "threshold": f"<= {thr9}",
                     "pass": bool(rr is not None and rr <= thr9),
                     "detail": {"median_det_to_peak_instantaneous": m0,
                                "median_det_to_peak_60s_poll": m60,
                                "note": "instantaneous is the physically impossible upper bound on runway"}})

    any_fail = any(r["pass"] is False for r in rows)

    summary = {
        "phase": "10", "version": "v2", "task": "T5", "config_hash": chash,
        "population": f"pooled analysis cohort, n=100; reference k={k_ref}, as_is tie variant, "
                      f"threshold 1.30. row_cap_census and dev_v4_sidecar never pooled.",
        "t5a_resolution": t5a,
        "t5b_observable_agreement": t5b,
        "t5c_tie_variant_agreement": {**t5c, "within_tolerance": tie_ok,
                                      "escalation_row_8_triggered": (not tie_ok)},
        "t4_level_conditioning": lvl,
        "t5d_failure_criteria": {
            "row_0": {"mode": fc["row_0"]["mode"], "observed": None, "pass": None,
                      "note": fc["row_0"]["note"]},
            "rows": rows, "any_failed": bool(any_fail),
        },
        "standing_lesson": fc["standing_lesson"],
        "source": "research/phase_10/v2_t5_stability.py:main",
    }
    write_json(os.path.join(out_dir, OUT), summary)

    print(f"T5a decay-half median by k (print): "
          f"{[round(t5a['print_rate']['pooled_median_decay_half_per_k'][f'k{k}']['q50'] or 0, 1) for k in k_grid]}")
    print(f"T5b observable spearman: {t5b['spearman_decay_half']:.3f} (n={t5b['n_events']})")
    print(f"T5c tie variants within tolerance: {tie_ok}")
    print("T5d failure criteria:")
    for r in rows:
        o = r["observed"]
        os_ = f"{o:.4f}" if isinstance(o, float) else str(o)
        print(f"  row {r['row']} {r['observable'][:22]:24s} observed={os_:>10s} "
              f"thr {r['threshold']:>18s} -> {'PASS' if r['pass'] else 'FAIL'}")
    if any_fail:
        print("PRE-REGISTERED FAILURE CRITERION FIRED")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
