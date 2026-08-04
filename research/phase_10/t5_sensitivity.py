"""
Phase 10 T5 -- sensitivity, cross-arm agreement, and the four pre-registered
failure criteria.

T5a  burst-set overlap under parameter perturbation, per arm
T5b  cross-arm agreement on the same events, same measure
T5c  the four pre-registered failure criteria, observed vs threshold, pass/fail
     and NOTHING FURTHER

Overlap measure (config.overlap_measure): interval Jaccard on the union of
burst intervals -- seconds in the intersection over seconds in the union. Chosen
because the downstream use of this phase is burst-relative ANCHORING, so what
matters is whether the same REGIONS of the session get labeled. Burst-count
agreement can be perfect while the intervals sit somewhere else entirely, and
can be poor while the same region is labeled with one extra split; it is
reported alongside but is not the failure-row-3 statistic.

Usage: python research/phase_10/t5_sensitivity.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import config_hash, load_config, quantiles, rel, write_json  # noqa: E402

KEY = ["ticker", "event_date_canonical", "momentum_pct"]
POOLED = ["dev_v4_primary", "activity_extension"]
OUT = "t5_sensitivity.json"
OUT_PAIRS = "t5_overlap_pairs.parquet"


# ------------------------------------------------------------------ intervals

def _union(iv: np.ndarray) -> np.ndarray:
    """Merge overlapping [start, end] rows into a disjoint union."""
    if iv.size == 0:
        return iv.reshape(0, 2)
    iv = iv[np.argsort(iv[:, 0])]
    out = [iv[0].copy()]
    for s, e in iv[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append(np.array([s, e]))
    return np.array(out)


def _total(iv: np.ndarray) -> float:
    return float((iv[:, 1] - iv[:, 0]).sum()) if iv.size else 0.0


def _intersect_total(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    i = j = 0
    tot = 0.0
    while i < len(a) and j < len(b):
        lo = max(a[i, 0], b[j, 0])
        hi = min(a[i, 1], b[j, 1])
        if hi > lo:
            tot += hi - lo
        if a[i, 1] < b[j, 1]:
            i += 1
        else:
            j += 1
    return float(tot)


def interval_jaccard(a_iv: np.ndarray, b_iv: np.ndarray) -> tuple[float, str]:
    """Seconds-in-intersection over seconds-in-union. Empty-vs-empty = 1.0,
    empty-vs-nonempty = 0.0; both cases counted separately."""
    a, b = _union(a_iv), _union(b_iv)
    ta, tb = _total(a), _total(b)
    if ta == 0.0 and tb == 0.0:
        return 1.0, "both_empty"
    if ta == 0.0 or tb == 0.0:
        return 0.0, "one_empty"
    inter = _intersect_total(a, b)
    union = ta + tb - inter
    return (inter / union if union > 0 else 0.0), "both_nonempty"


def intervals_by_event(df: pd.DataFrame) -> dict:
    out = {}
    for k, sub in df.groupby(KEY, sort=False):
        out[k] = np.stack([
            sub["start_ns"].to_numpy(dtype=np.float64) / 1e9,
            sub["end_ns"].to_numpy(dtype=np.float64) / 1e9,
        ], axis=1)
    return out


def compare(ref_iv: dict, cell_iv: dict, events: list) -> pd.DataFrame:
    rows = []
    for k in events:
        a = ref_iv.get(k, np.zeros((0, 2)))
        b = cell_iv.get(k, np.zeros((0, 2)))
        j, kind = interval_jaccard(a, b)
        rows.append({
            "ticker": k[0], "event_date_canonical": k[1], "momentum_pct": k[2],
            "jaccard": j, "kind": kind,
            "n_bursts_ref": int(len(a)), "n_bursts_cell": int(len(b)),
            "count_delta": int(len(b) - len(a)),
            "count_equal": bool(len(a) == len(b)),
        })
    return pd.DataFrame(rows)


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    fc = cfg["failure_criteria"]

    A = pd.read_parquet(os.path.join(out_dir, "t2_bursts_arm_a.parquet"))
    B = pd.read_parquet(os.path.join(out_dir, "t3_bursts_arm_b.parquet"))
    ea = pd.read_parquet(os.path.join(out_dir, "t2_arm_a_events.parquet"))
    eb = pd.read_parquet(os.path.join(out_dir, "t3_arm_b_events.parquet"))
    t4e = pd.read_parquet(os.path.join(out_dir, "t4_event_measurements.parquet"))
    t4b = pd.read_parquet(os.path.join(out_dir, "t4_burst_measurements.parquet"))
    for d in (A, B, ea, eb, t4e, t4b):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)

    pooled_events = [
        tuple(x) for x in
        ea.loc[ea["cohort_group"].isin(POOLED), KEY].itertuples(index=False, name=None)
    ]

    # ---------------------------------------------------------------- T5a
    pair_frames, sens = [], {}
    for arm, allb in (("A", A), ("B", B)):
        ref_iv = intervals_by_event(allb[allb["is_ref"]])
        cells = sorted(set(allb.loc[~allb["is_ref"], "param_set"]))
        per_cell, all_j = {}, []
        for cell in cells:
            cell_iv = intervals_by_event(allb[allb["param_set"] == cell])
            cmp = compare(ref_iv, cell_iv, pooled_events)
            cmp["arm"], cmp["param_set"], cmp["comparison"] = arm, cell, "vs_reference"
            pair_frames.append(cmp)
            all_j.append(cmp["jaccard"].to_numpy())
            per_cell[cell] = {
                "n_events": int(len(cmp)),
                "jaccard": quantiles(cmp["jaccard"]),
                "count_equal_share": float(cmp["count_equal"].mean()),
                "median_count_delta": float(cmp["count_delta"].median()),
                "n_one_empty": int((cmp["kind"] == "one_empty").sum()),
                "n_both_empty": int((cmp["kind"] == "both_empty").sum()),
            }
        pooled_j = np.concatenate(all_j) if all_j else np.zeros(0)
        sens[arm] = {
            "n_non_reference_cells": len(cells),
            "n_comparisons": int(pooled_j.size),
            "pooled_jaccard_vs_reference": quantiles(pooled_j),
            "per_cell": per_cell,
        }

    # ---------------------------------------------------------------- T5b
    a_ref_iv = intervals_by_event(A[A["is_ref"]])
    b_ref_iv = intervals_by_event(B[B["is_ref"]])
    cross = compare(a_ref_iv, b_ref_iv, pooled_events)
    cross["arm"], cross["param_set"], cross["comparison"] = "A_vs_B", "ref", "cross_arm"
    cross = cross.rename(columns={"n_bursts_ref": "n_bursts_arm_a", "n_bursts_cell": "n_bursts_arm_b"})
    pair_frames.append(cross.rename(columns={"n_bursts_arm_a": "n_bursts_ref",
                                             "n_bursts_arm_b": "n_bursts_cell"}))

    sub_a = t4e[t4e["arm"] == "A"].set_index(KEY)["burst_covered_seconds"]
    sub_b = t4e[t4e["arm"] == "B"].set_index(KEY)["burst_covered_seconds"]
    cross_idx = pd.MultiIndex.from_frame(cross[KEY])
    cross_out = {
        "n_events": int(len(cross)),
        "measure": "interval_jaccard (same measure as T5a)",
        "jaccard": quantiles(cross["jaccard"]),
        "count_equal_share": float(cross["count_equal"].mean()),
        "burst_count_arm_a": quantiles(cross["n_bursts_arm_a"]),
        "burst_count_arm_b": quantiles(cross["n_bursts_arm_b"]),
        "spearman_burst_count": float(
            pd.Series(cross["n_bursts_arm_a"]).corr(pd.Series(cross["n_bursts_arm_b"]), method="spearman")
        ),
        "n_events_arm_a_more_bursts": int((cross["n_bursts_arm_a"] > cross["n_bursts_arm_b"]).sum()),
        "n_events_arm_b_more_bursts": int((cross["n_bursts_arm_b"] > cross["n_bursts_arm_a"]).sum()),
        "n_events_equal_burst_count": int((cross["n_bursts_arm_a"] == cross["n_bursts_arm_b"]).sum()),
        "n_one_empty": int((cross["kind"] == "one_empty").sum()),
        "burst_covered_seconds_arm_a": quantiles(sub_a.reindex(cross_idx)),
        "burst_covered_seconds_arm_b": quantiles(sub_b.reindex(cross_idx)),
        "highest_agreement_events": cross.nlargest(5, "jaccard")[
            KEY + ["jaccard", "n_bursts_arm_a", "n_bursts_arm_b"]].to_dict("records"),
        "lowest_agreement_events": cross.nsmallest(5, "jaccard")[
            KEY + ["jaccard", "n_bursts_arm_a", "n_bursts_arm_b"]].to_dict("records"),
    }

    pd.concat(pair_frames, ignore_index=True).to_parquet(os.path.join(out_dir, OUT_PAIRS), index=False)

    # ---------------------------------------------------------------- T5c
    rows = []
    for arm in ("A", "B"):
        ev = t4e[(t4e["arm"] == arm) & (t4e["cohort_group"].isin(POOLED))]
        bs = t4b[(t4b["arm"] == arm) & (t4b["cohort_group"].isin(POOLED))]
        n_ev = len(ev)

        # row 1 -- degenerate to session flag
        span = ev["session_span_seconds"].replace(0, np.nan)
        share_span = ev["burst_covered_seconds"] / span
        degen = ev[(ev["n_bursts"] == 1) & (share_span >= fc["row_1"]["majority_span_share"])]
        obs1 = float(len(degen) / n_ev) if n_ev else np.nan
        rows.append({
            "row": 1, "arm": arm, "mode": fc["row_1"]["mode"],
            "observable": fc["row_1"]["observable"],
            "observed": obs1, "threshold": fc["row_1"]["threshold_share"],
            "direction": fc["row_1"]["direction"],
            "applies": True,
            "pass": bool(obs1 <= fc["row_1"]["threshold_share"]),
            "detail": {"n_events": n_ev, "n_degenerate": int(len(degen))},
        })

        # row 2 -- fragmentation at the floor
        obs2 = float(bs["duration_seconds"].median()) if len(bs) else np.nan
        thr2 = fc["row_2"]["threshold_multiple"] * fc["row_2"]["floor_reference_seconds"]
        applies2 = arm.lower() == "b" or ("arm_" + arm.lower()) in fc["row_2"]["applies_to"]
        rows.append({
            "row": 2, "arm": arm, "mode": fc["row_2"]["mode"],
            "observable": fc["row_2"]["observable"],
            "observed": obs2, "threshold": thr2, "direction": fc["row_2"]["direction"],
            "applies": bool(applies2),
            "pass": bool(obs2 > thr2) if applies2 else None,
            "detail": {
                "n_bursts": int(len(bs)),
                "floor_reference_seconds": fc["row_2"]["floor_reference_seconds"],
                "note": None if applies2 else
                        "Reported, not evaluated. The criterion is 'the rule re-emitting its own "
                        "parameter'; Arm A has no minimum-dwell parameter to re-emit (gamma plays "
                        "that role and is not a duration floor). config.failure_criteria.row_2 "
                        "pre-registers applies_to = [arm_b], reported_for = [arm_a, arm_b].",
            },
        })

        # row 3 -- parameter instability
        obs3 = sens[arm]["pooled_jaccard_vs_reference"]["q50"]
        thr3 = fc["row_3"]["threshold_median_jaccard"]
        rows.append({
            "row": 3, "arm": arm, "mode": fc["row_3"]["mode"],
            "observable": fc["row_3"]["observable"],
            "observed": obs3, "threshold": thr3, "direction": fc["row_3"]["direction"],
            "applies": True,
            "pass": bool(obs3 is not None and obs3 >= thr3),
            "detail": {"n_comparisons": sens[arm]["n_comparisons"],
                       "n_cells": sens[arm]["n_non_reference_cells"]},
        })

        # row 4 -- no structure
        vc = ev["n_bursts"].value_counts()
        modal_share = float(vc.iloc[0] / n_ev) if n_ev else np.nan
        iqr = float(ev["n_bursts"].quantile(0.75) - ev["n_bursts"].quantile(0.25)) if n_ev else np.nan
        fail4 = (modal_share > fc["row_4"]["threshold_modal_share"]) or (iqr < fc["row_4"]["threshold_min_iqr"])
        rows.append({
            "row": 4, "arm": arm, "mode": fc["row_4"]["mode"],
            "observable": fc["row_4"]["observable"],
            "observed": {"modal_share": modal_share, "iqr": iqr, "modal_value": int(vc.index[0]) if n_ev else None},
            "threshold": {"max_modal_share": fc["row_4"]["threshold_modal_share"],
                          "min_iqr": fc["row_4"]["threshold_min_iqr"]},
            "direction": fc["row_4"]["direction"],
            "applies": True,
            "pass": bool(not fail4),
            "detail": {"n_events": n_ev, "n_distinct_burst_counts": int(ev["n_bursts"].nunique())},
        })

    any_fail = any(r["pass"] is False for r in rows)

    summary = {
        "phase": "10", "task": "T5", "config_hash": chash,
        "overlap_measure": cfg["overlap_measure"],
        "population": "pooled analysis cohort (dev_v4_primary + activity_extension), n=%d. "
                      "row_cap_census and dev_v4_sidecar are excluded from every T5 statistic, "
                      "per the never-pooled rule." % len(pooled_events),
        "t5a_sensitivity": sens,
        "t5b_cross_arm": cross_out,
        "t5c_failure_criteria": {
            "row_0": {"mode": fc["row_0"]["mode"], "threshold": None, "observed": None,
                      "pass": None,
                      "note": "Cooper's judgment off chart 07. No numeric threshold. Overrides rows "
                              "1-4 in either direction. A pass on rows 1-4 does not constitute "
                              "acceptance."},
            "rows": rows,
            "any_failed": bool(any_fail),
        },
        "source": "research/phase_10/t5_sensitivity.py:main",
        "artifact": f"{cfg['paths']['out_artifacts']}{OUT_PAIRS}",
    }
    write_json(os.path.join(out_dir, OUT), summary)

    print(f"T5a pooled jaccard vs reference: "
          f"A med={sens['A']['pooled_jaccard_vs_reference']['q50']:.3f}  "
          f"B med={sens['B']['pooled_jaccard_vs_reference']['q50']:.3f}")
    print(f"T5b cross-arm jaccard: med={cross_out['jaccard']['q50']:.3f}  "
          f"spearman(count)={cross_out['spearman_burst_count']:.3f}")
    print("T5c pre-registered failure criteria:")
    for r in rows:
        v = r["observed"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        st = "n/a" if r["pass"] is None else ("PASS" if r["pass"] else "FAIL")
        print(f"  row {r['row']} arm {r['arm']}: observed={vs} threshold={r['threshold']} -> {st}")
    if any_fail:
        print("PRE-REGISTERED FAILURE CRITERION FIRED -- hard stop condition")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
