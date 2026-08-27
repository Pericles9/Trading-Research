"""
Phase 10d T2 -- the control gate. HARD BARRIER: no real event is read here.

C1 identity, C2 monotonicity, C3 depth direction, C4 separator equivalence, C5 floor no-op.
C1's "replay" reads the COMMITTED 10c sub-burst artifact -- emitted objects, not ticks --
so it sits legitimately behind the barrier. Assembly is a pure function of the label array,
so round-tripping a committed cell's run structure is a complete validation of the identity
claim.

Usage: .venv/Scripts/python.exe research/phase_10d/controls.py
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from assemble import (SEP_BRIDGEABLE, SEP_HARD_BREAK, assemble,  # noqa: E402
                      label_intervals, raw_runs)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG_PATH = os.path.join(ROOT, "config", "phase_10d.json")
OUT = os.path.join(ROOT, "results", "phase_10d", "controls")


def cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def write(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def synth_from_run_lengths(run_lengths, sep_width=1, thr=-3.0, gap_bad=None):
    """Build (norm, ok, ts, inb) whose maximal sub-threshold runs have exactly these lengths.

    Separating intervals sit ABOVE thr (a real gap) unless flagged in gap_bad, in which case
    they fail the ok mask instead. Timestamps are uniform, 1 ms per interval.
    """
    gap_bad = gap_bad or set()
    vals, oks = [], []
    for i, L in enumerate(run_lengths):
        vals.extend([thr - 1.0] * int(L))
        oks.extend([True] * int(L))
        if i < len(run_lengths) - 1:
            for w in range(sep_width):
                if (i, w) in gap_bad:
                    vals.append(thr - 1.0)   # value is irrelevant; ok=False governs
                    oks.append(False)
                else:
                    vals.append(thr + 0.5)   # a real gap, 0.5 decades above threshold
                    oks.append(True)
    norm = np.array(vals, dtype=float)
    ok = np.array(oks, dtype=bool)
    ts = (np.arange(norm.size + 1, dtype=np.int64)) * 1_000_000
    return norm, ok, ts, label_intervals(norm, ok, thr)


# --------------------------------------------------------------------------- C1
def c1_identity(conf):
    """All eight degenerate (K,d) cells at min_prints=2, sep=hard_break reproduce 10c
    exactly, print for print, and are identical to each other."""
    degen = [tuple(x) for x in conf["merge_grid"]["degenerate_cells"]]
    thr = -3.0
    sb = pd.read_parquet(os.path.join(ROOT, conf["controls"]["c1_replay_source"]))
    n_want = int(conf["controls"]["c1_replay_n_cells"])

    counts = (sb.groupby(["ticker", "event_date_canonical", "kernel_min"])
                .size().sort_values())
    picks = counts.iloc[np.linspace(0, len(counts) - 1, n_want).astype(int)].index.tolist()

    replay_rows, all_pass = [], True
    for tkr, dt, kmin in picks:
        cell = sb[(sb.ticker == tkr) & (sb.event_date_canonical == dt)
                  & (sb.kernel_min == kmin)].sort_values("start_ns")
        want_int = cell.n_intervals.to_numpy()
        want_prn = cell.n_prints.to_numpy()
        norm, ok, ts, inb = synth_from_run_lengths(want_int, sep_width=1, thr=thr)

        outs = {}
        for K, d in degen:
            r = assemble(norm, ok, ts, thr, K=K, d=d, min_prints=2, sep=SEP_HARD_BREAK)
            outs[(K, d)] = (r["n_intervals_total"].tolist(), r["n_prints"].tolist())

        ref = outs[(0, 0.0)]
        identical = all(v == ref for v in outs.values())
        matches = (ref[0] == want_int.tolist()) and (ref[1] == want_prn.tolist())
        all_pass &= identical and matches
        replay_rows.append({
            "ticker": tkr, "event_date_canonical": str(dt), "kernel_min": float(kmin),
            "n_runs_committed": int(len(want_int)),
            "n_objects_replayed": int(len(ref[0])),
            "print_for_print_match": bool(matches),
            "all_eight_degenerate_identical": bool(identical),
        })

    # synthetic arm -- a structure the artifact does not contain
    syn_pass = True
    rng = np.random.default_rng(conf["seeds"]["control_synthetic"])
    for _ in range(50):
        L = rng.integers(1, 12, size=rng.integers(2, 20)).tolist()
        norm, ok, ts, inb = synth_from_run_lengths(L, sep_width=int(rng.integers(1, 4)), thr=thr)
        outs = [assemble(norm, ok, ts, thr, K=K, d=d, min_prints=2,
                         sep=SEP_HARD_BREAK)["n_intervals_total"].tolist() for K, d in degen]
        syn_pass &= all(o == outs[0] for o in outs) and outs[0] == list(L)

    res = {"control": "C1", "name": "merge identity", "hard_gate": True,
           "required": ("all eight degenerate (K,d) cells at min_prints=2, sep=hard_break "
                        "reproduce 10c's assembly exactly, print for print, and are "
                        "identical to each other"),
           "degenerate_cells_tested": [list(x) for x in degen],
           "replay_cells": replay_rows,
           "replay_pass": bool(all_pass),
           "synthetic_sequences": 50, "synthetic_pass": bool(syn_pass),
           "pass": bool(all_pass and syn_pass)}
    write("c1_identity.json", res)
    return res


# --------------------------------------------------------------------------- C2
def c2_monotonicity(conf):
    """Count non-increasing and total/max duration non-decreasing as K and d rise;
    count non-increasing as min_prints rises.

    SPECIFICATION CORRECTION, made before any real event is read (A10b.1). The spec says
    "merged duration non-decreasing". MEDIAN duration is not monotone and cannot be gated
    on: objects [1s,1s,100s,100s] have median 50.5s, and merging the two 100s gives
    [1s,1s,200s], median 1s -- a decrease produced by a correct merge. TOTAL and MAX
    duration are monotone by construction (a merged span contains its constituents), so
    those are gated and the median is reported un-gated with the counterexample recorded.
    """
    Ks = conf["merge_grid"]["K"]
    ds = conf["merge_grid"]["d"]
    mps = conf["min_prints_grid"]["values"]
    thr = -3.0
    rng = np.random.default_rng(conf["seeds"]["control_synthetic"])
    n_seq = int(conf["controls"]["synthetic_n_sequences"])

    viol = {"count_vs_K": 0, "count_vs_d": 0, "total_dur_vs_K": 0, "total_dur_vs_d": 0,
            "max_dur_vs_K": 0, "max_dur_vs_d": 0, "count_vs_min_prints": 0}
    median_non_monotone = 0
    checks = 0

    for _ in range(n_seq):
        L = rng.integers(1, 10, size=rng.integers(3, 25)).tolist()
        norm, ok, ts, _ = synth_from_run_lengths(L, sep_width=int(rng.integers(1, 5)), thr=thr)

        for mp in mps:
            # monotone in K at fixed d
            for d in ds:
                seq = [assemble(norm, ok, ts, thr, K, d, mp, SEP_HARD_BREAK) for K in sorted(Ks)]
                checks += 1
                if any(b["n_objects"] > a["n_objects"] for a, b in zip(seq, seq[1:])):
                    viol["count_vs_K"] += 1
                tot = [float(s["duration_s"].sum()) for s in seq]
                if any(b < a - 1e-12 for a, b in zip(tot, tot[1:])):
                    viol["total_dur_vs_K"] += 1
                mx = [float(s["duration_s"].max()) if s["n_objects"] else 0.0 for s in seq]
                if any(b < a - 1e-12 for a, b in zip(mx, mx[1:])):
                    viol["max_dur_vs_K"] += 1
                med = [float(np.median(s["duration_s"])) if s["n_objects"] else 0.0 for s in seq]
                if any(b < a - 1e-12 for a, b in zip(med, med[1:])):
                    median_non_monotone += 1
            # monotone in d at fixed K
            for K in Ks:
                seq = [assemble(norm, ok, ts, thr, K, d, mp, SEP_HARD_BREAK) for d in sorted(ds)]
                if any(b["n_objects"] > a["n_objects"] for a, b in zip(seq, seq[1:])):
                    viol["count_vs_d"] += 1
                tot = [float(s["duration_s"].sum()) for s in seq]
                if any(b < a - 1e-12 for a, b in zip(tot, tot[1:])):
                    viol["total_dur_vs_d"] += 1
                mx = [float(s["duration_s"].max()) if s["n_objects"] else 0.0 for s in seq]
                if any(b < a - 1e-12 for a, b in zip(mx, mx[1:])):
                    viol["max_dur_vs_d"] += 1
        # monotone in min_prints
        for K, d in itertools.product(Ks, ds):
            seq = [assemble(norm, ok, ts, thr, K, d, mp, SEP_HARD_BREAK) for mp in sorted(mps)]
            if any(b["n_objects"] > a["n_objects"] for a, b in zip(seq, seq[1:])):
                viol["count_vs_min_prints"] += 1

    gated = {k: v for k, v in viol.items()}
    res = {"control": "C2", "name": "monotonicity", "hard_gate": True,
           "required": ("count non-increasing as K, d and min_prints rise; TOTAL and MAX "
                        "duration non-decreasing as K and d rise"),
           "sequences": n_seq, "monotone_checks": checks,
           "violations": gated,
           "median_duration_non_monotone_cases": median_non_monotone,
           "median_note": ("Reported, NOT gated. Median object duration is not a monotone "
                           "function of the merge tolerance: [1s,1s,100s,100s] has median "
                           "50.5s and merging the two 100s yields [1s,1s,200s], median 1s. "
                           "The spec's 'merged duration non-decreasing' is gated here on "
                           "total and max, which are monotone by construction."),
           "pass": bool(sum(gated.values()) == 0)}
    write("c2_monotonicity.json", res)
    return res


# --------------------------------------------------------------------------- C3
def c3_depth_direction(conf):
    """Raising d admits MORE separators, never fewer. Catches the multiplicative-on-a-
    negative-log-threshold error, which would tighten the tolerance as d grows."""
    ds = sorted(conf["merge_grid"]["d"])
    thr = -3.0
    depths = [0.1, 0.3, 0.6, 0.9]          # decades ABOVE threshold, known by construction
    vals, oks = [], []
    for i, dep in enumerate(depths):
        vals.extend([thr - 1.0, thr - 1.0])
        oks.extend([True, True])
        vals.append(thr + dep)              # the separator
        oks.append(True)
    vals.extend([thr - 1.0, thr - 1.0])
    oks.extend([True, True])
    norm = np.array(vals); ok = np.array(oks, dtype=bool)
    ts = np.arange(norm.size + 1, dtype=np.int64) * 1_000_000

    rows, admitted = [], []
    for d in ds:
        r = assemble(norm, ok, ts, thr, K=1, d=d, min_prints=2, sep=SEP_HARD_BREAK)
        n_adm = int(r["n_merges"].sum())
        admitted.append(n_adm)
        rows.append({"d_decades": d, "separators_admitted": n_adm,
                     "expected_admitted": int(sum(1 for x in depths if x < d)),
                     "n_objects": r["n_objects"]})
    non_decreasing = all(b >= a for a, b in zip(admitted, admitted[1:]))
    exact = all(r["separators_admitted"] == r["expected_admitted"] for r in rows)
    res = {"control": "C3", "name": "depth-tolerance direction", "hard_gate": True,
           "required": "raising d admits more separators, never fewer",
           "separator_depths_above_threshold_decades": depths,
           "rows": rows, "non_decreasing": non_decreasing,
           "matches_construction_exactly": exact,
           "pass": bool(non_decreasing and exact)}
    write("c3_depth_direction.json", res)
    return res


# --------------------------------------------------------------------------- C4
def c4_separator_equivalence(conf):
    """On a sequence containing NO ok=False intervals the two separator rules must be
    identical -- so any difference on real data is attributable to ok=False gaps alone."""
    Ks = conf["merge_grid"]["K"]; ds = conf["merge_grid"]["d"]
    mps = conf["min_prints_grid"]["values"]
    thr = -3.0
    rng = np.random.default_rng(conf["seeds"]["control_synthetic"])
    n_seq = int(conf["controls"]["synthetic_n_sequences"])
    diffs, checks = 0, 0
    for _ in range(n_seq):
        L = rng.integers(1, 10, size=rng.integers(3, 25)).tolist()
        norm, ok, ts, _ = synth_from_run_lengths(L, sep_width=int(rng.integers(1, 5)), thr=thr)
        assert ok.all(), "C4 construction must contain no ok=False intervals"
        for K, d, mp in itertools.product(Ks, ds, mps):
            a = assemble(norm, ok, ts, thr, K, d, mp, SEP_HARD_BREAK)
            b = assemble(norm, ok, ts, thr, K, d, mp, SEP_BRIDGEABLE)
            checks += 1
            if (a["n_intervals_total"].tolist() != b["n_intervals_total"].tolist()
                    or a["start_idx"].tolist() != b["start_idx"].tolist()):
                diffs += 1
    # and the converse, reported not gated: with ok=False present the rules should differ
    norm, ok, ts, _ = synth_from_run_lengths([3, 3, 3, 3], sep_width=1, thr=thr,
                                             gap_bad={(0, 0), (2, 0)})
    a = assemble(norm, ok, ts, thr, K=2, d=1.0, min_prints=2, sep=SEP_HARD_BREAK)
    b = assemble(norm, ok, ts, thr, K=2, d=1.0, min_prints=2, sep=SEP_BRIDGEABLE)
    res = {"control": "C4", "name": "separator equivalence", "hard_gate": True,
           "required": "identical output on input containing no ok=False intervals",
           "sequences": n_seq, "comparisons": checks, "differences": diffs,
           "converse_check_reported_not_gated": {
               "construction": "4 runs of 3, separators at gaps 0 and 2 set ok=False",
               "hard_break_n_objects": a["n_objects"],
               "bridgeable_n_objects": b["n_objects"],
               "rules_differ_when_ok_false_present": bool(a["n_objects"] != b["n_objects"])},
           "pass": bool(diffs == 0)}
    write("c4_separator_equivalence.json", res)
    return res


# --------------------------------------------------------------------------- C5
def c5_floor_noop(conf):
    """min_prints = 2 deletes zero objects. This is what makes 2 the valid reference."""
    Ks = conf["merge_grid"]["K"]; ds = conf["merge_grid"]["d"]
    thr = -3.0
    rng = np.random.default_rng(conf["seeds"]["control_synthetic"])
    n_seq = int(conf["controls"]["synthetic_n_sequences"])
    deleted_at_2 = 0
    deleted_at_3, deleted_at_5, total_objs = 0, 0, 0
    for _ in range(n_seq):
        L = rng.integers(1, 10, size=rng.integers(3, 25)).tolist()
        norm, ok, ts, _ = synth_from_run_lengths(L, sep_width=int(rng.integers(1, 5)), thr=thr)
        for K, d in itertools.product(Ks, ds):
            r2 = assemble(norm, ok, ts, thr, K, d, 2, SEP_HARD_BREAK)
            deleted_at_2 += r2["n_deleted_by_floor"]
            total_objs += r2["n_objects_before_floor"]
            deleted_at_3 += assemble(norm, ok, ts, thr, K, d, 3, SEP_HARD_BREAK)["n_deleted_by_floor"]
            deleted_at_5 += assemble(norm, ok, ts, thr, K, d, 5, SEP_HARD_BREAK)["n_deleted_by_floor"]
    res = {"control": "C5", "name": "floor no-op at min_prints=2", "hard_gate": True,
           "required": "min_prints = 2 deletes zero objects",
           "objects_before_floor": total_objs,
           "deleted_at_min_prints_2": deleted_at_2,
           "deleted_at_min_prints_3": deleted_at_3,
           "deleted_at_min_prints_5": deleted_at_5,
           "note": ("3 and 5 delete a non-zero count by construction -- that is the point "
                    "of the axis. Only 2 is required to be inert."),
           "pass": bool(deleted_at_2 == 0)}
    write("c5_floor_noop.json", res)
    return res


def main() -> int:
    conf = cfg()
    results = [c1_identity(conf), c2_monotonicity(conf), c3_depth_direction(conf),
               c4_separator_equivalence(conf), c5_floor_noop(conf)]
    gate = {"phase": "10d", "task": "T2g", "hard_gates": ["C1", "C2", "C3", "C4", "C5"],
            "rows": [{"control": r["control"], "name": r["name"],
                      "hard_gate": r["hard_gate"], "pass": r["pass"]} for r in results],
            "all_pass": all(r["pass"] for r in results)}
    write("gate.json", gate)
    for r in results:
        print(f"{r['control']:>3}  {r['name']:<32}  {'PASS' if r['pass'] else 'FAIL'}")
    print(f"\nGATE: {'PASS' if gate['all_pass'] else 'FAIL'}")
    return 0 if gate["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
