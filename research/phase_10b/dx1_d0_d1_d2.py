"""
Phase 10b DX10b.1 -- D0 (state), D1 (satisfiability audit), D2 (excursion map).

Measures the gate. Changes no method, adopts no criterion, reads no real event.

Usage: .venv/Scripts/python.exe research/phase_10b/dx1_d0_d1_d2.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from pipeline import grid_dx, heldout_intensity  # noqa: E402
from t1_plateau import cfg_hash, load_cfg  # noqa: E402
from t2r5_controls import block_floor_event, build_controls  # noqa: E402

DX = "results/phase_10b/diagnostic_1"
DXA = f"{DX}/artifacts"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, cwd=rel(".")).stdout.strip()


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    dcfg = json.load(open(rel("config/phase_10b_diagnostic_1.json"), encoding="utf-8"))
    c2c, c3c, c4c = cfg["t2_controls"], cfg["t3_allan"], cfg["t4_rescaling"]
    span = float(c2c["rth_span_s"])
    res_ns = float(c2c["C1"]["quantization_ns"])
    lad_lo, lad_hi = c3c["ladder_exponents"]
    ladder = np.array([2.0 ** e for e in range(lad_lo, lad_hi + 1)])
    sw_lo, sw_hi = c4c["bandwidth_exponents"]
    hs_t4 = [2.0 ** e for e in range(sw_lo, sw_hi + 1)]
    br, mpb = c4c["block_ratio"], c4c["min_prints_per_block"]
    fl_max, floor_frac = c4c["floored_time_max"], c4c["lambda_floor_frac"]

    os.makedirs(rel(DXA), exist_ok=True)
    os.makedirs(rel(f"{DX}/charts"), exist_ok=True)

    # ---------------------------------------------------------------- D0
    stored = json.load(open(rel("results/phase_10b/artifacts/t2_controls.json"), encoding="utf-8"))
    coh = pd.read_parquet(rel(cfg["cohort"]["manifest"]))
    n_target = float(np.median(coh["t0_print_count"]))
    regen = build_controls(cfg, span, n_target, np.random.default_rng(c2c["seed"]), res_ns)
    repro = {nm: {"stored_n_prints": stored["results"][nm]["n_prints"],
                  "regenerated_n_prints": int(regen[nm].size),
                  "match": bool(stored["results"][nm]["n_prints"] == regen[nm].size)}
             for nm in stored["results"]}
    all_match = all(v["match"] for v in repro.values())

    d0 = {
        "task": "D0", "branch": sh("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "tip": sh("git", "log", "--oneline", "-1"),
        "working_tree_porcelain": sh("git", "status", "--porcelain").splitlines(),
        "working_tree_clean": sh("git", "status", "--porcelain") == "",
        "escalation_row_1_note": (
            "ROW 1 (working tree dirty) IS TRIPPED BY THREE PRE-EXISTING ENTRIES ONLY: a .gitignore "
            "modification, untracked .claude/skills/, and untracked prompts/phase_9. These are the "
            "exact three entries Cooper waived on 2026-08-06 with 'leave and proceed. make sure "
            "nothing gets lost'. None is an output of any phase 10b task and none is written by this "
            "diagnostic. Flagged rather than treated as a fresh stop; the waiver is recorded here so "
            "the decision is visible."),
        "artifacts_present": {f: os.path.getsize(rel(f"results/phase_10b/artifacts/{f}"))
                              for f in sorted(os.listdir(rel("results/phase_10b/artifacts")))},
        "d0b_per_draw_realizations": {
            "persisted": False,
            "what_was_persisted": ("t2_controls.json holds per-control SUMMARIES and per-(control, h, "
                                   "rung) band/curve rows in t2_control_curves.parquet. Individual "
                                   "null-draw curves and repeated control realizations were not "
                                   "written to disk."),
            "deterministically_reproducible": all_match,
            "reproduction": ("build_controls(cfg, span, median t0_print_count, "
                             f"numpy default_rng({c2c['seed']}), {res_ns} ns) in "
                             "research/phase_10b/t2r5_controls.py"),
            "verification_against_stored_summaries": repro,
            "row_2_fires": not all_match},
    }

    # ---------------------------------------------------------------- D1
    def rung_reach(target, lo_e, hi_e, name):
        lt = float(np.log2(target))
        inside = lo_e <= lt <= hi_e
        dist = 0.0 if inside else min(abs(lt - lo_e), abs(lt - hi_e))
        return {"target_s": target, "target_log2": lt, "range_log2": [lo_e, hi_e],
                "range_s": [2.0 ** lo_e, 2.0 ** hi_e], "inside_range": bool(inside),
                "rungs_outside": dist, "statistic": name}

    # eligible T-rungs after the pooled-pair rule
    npair = np.floor(span / ladder).astype(np.int64) - 1
    elig_T = npair >= c3c["min_pairs_pooled"]
    T_hi_e = int(np.log2(ladder[elig_T].max()))
    T_lo_e = int(np.log2(ladder[elig_T].min()))

    # eligible bandwidths under the three block rules, at the controls' own rate
    t_c1 = regen["C1"]
    bfe, _ = block_floor_event(t_c1, 0.0, span, mpb)
    rules = {}
    for rname, blkf in (("original_fixed_60s", lambda h: 60.0),
                        ("a10b1_max_h_over_4_and_floor", lambda h: max(h / br, bfe)),
                        ("no_block_length_rule_h_over_4", lambda h: h / br)):
        el = []
        for h in hs_t4:
            blk = blkf(h)
            dx, glim = grid_dx(h, blk, span, c4c["max_grid_points"])
            _, _, floored = heldout_intensity(t_c1, 0.0, span, h, blk, dx, floor_frac)
            binds = (rname == "a10b1_max_h_over_4_and_floor") and (h / br < bfe)
            el.append({"h": float(h), "block_s": float(blk), "floored_time_fraction": float(floored),
                       "block_floor_binds": bool(binds), "grid_limited": bool(glim),
                       "eligible": bool(floored <= fl_max and not binds and not glim)})
        rules[rname] = {"by_h": el,
                        "n_eligible": int(sum(r["eligible"] for r in el)),
                        "eligible_share": float(np.mean([r["eligible"] for r in el])),
                        "eligible_h": [r["h"] for r in el if r["eligible"]]}
    # the alternative A10b.1 explicitly rejected
    rej = [{"h": float(h), "eligible": bool(h >= 60.0)} for h in hs_t4]
    rules["rejected_alternative_h_lt_60_ineligible"] = {
        "by_h": rej, "n_eligible": int(sum(r["eligible"] for r in rej)),
        "eligible_share": float(np.mean([r["eligible"] for r in rej])),
        "eligible_h": [r["h"] for r in rej if r["eligible"]]}

    a = rules["a10b1_max_h_over_4_and_floor"]["eligible_share"]
    b = rules["rejected_alternative_h_lt_60_ineligible"]["eligible_share"]
    crit = [
        dict(rung_reach(1e-5, sw_lo, sw_hi, "C3 T4 crossing (bandwidth sweep)"),
             criterion="C3 T4 crossing recovers 10 us", source="original prompt + A10b.1"),
        dict(rung_reach(60.0, sw_lo, sw_hi, "C4 T4 crossing (bandwidth sweep)"),
             criterion="C4 T4 crossing recovers 60 s", source="original prompt + A10b.1"),
        dict(rung_reach(1e-5, T_lo_e, T_hi_e, "C3 knee (T ladder, eligible rungs)"),
             criterion="C3 knee recovers 10 us", source="A10b.1"),
        dict(rung_reach(60.0, T_lo_e, T_hi_e, "C4 knee (T ladder, eligible rungs)"),
             criterion="C4 knee recovers 60 s", source="A10b.1"),
        dict(rung_reach(1e-3, T_lo_e, T_hi_e, "C3' knee (T ladder, eligible rungs)"),
             criterion="C3' knee recovers 1 ms", source="A10b.1"),
        dict(rung_reach(1e-1, T_lo_e, T_hi_e, "C4' knee (T ladder, eligible rungs)"),
             criterion="C4' knee recovers 100 ms", source="A10b.1"),
    ]
    for c in crit:
        c["reachable_by_range"] = c["inside_range"]
    # bandwidth-eligibility overlay: a T4 target must also be an ELIGIBLE bandwidth
    eh = rules["a10b1_max_h_over_4_and_floor"]["eligible_h"]
    for c in crit:
        if "T4 crossing" in c["statistic"]:
            near = min(eh, key=lambda h: abs(np.log2(h) - c["target_log2"])) if eh else None
            c["nearest_eligible_bandwidth_s"] = near
            c["rungs_from_nearest_eligible"] = (abs(np.log2(near) - c["target_log2"])
                                                if near else None)
            c["reachable_within_1_rung_after_eligibility"] = bool(
                near is not None and abs(np.log2(near) - c["target_log2"]) <= 1.0 + 1e-9)

    d1 = {
        "task": "D1", "config_hash": chash,
        "d1a_criteria": crit,
        "d1b_confirmed": {
            "C3_t4_target_rungs_below_sweep_floor": crit[0]["rungs_outside"],
            "C3_t4_never_satisfiable": not crit[0]["inside_range"],
            "C4_t4_target_inside_sweep": crit[1]["inside_range"],
            "C4_t4_reachable_after_a10b1_eligibility":
                crit[1].get("reachable_within_1_rung_after_eligibility"),
        },
        "d1c_interaction_matrix": {
            "min_pairs_pooled": {"value": c3c["min_pairs_pooled"],
                                 "removes_T_rungs_above_s": float(span / (c3c["min_pairs_pooled"] + 1)),
                                 "can_void": "any knee or crossing target above that T"},
            "floored_time_max": {"value": fl_max,
                                 "can_void": "any T4 crossing target at a bandwidth whose out-of-sample "
                                             "lambda-hat sits at the floor"},
            "block_floor_binding": {"block_floor_event_s": bfe,
                                    "binds_below_h_s": bfe * br,
                                    "can_void": "any T4 crossing target below h = block_ratio * "
                                                "block_floor_event -- which is what removed C4's 60 s"},
        },
        "d1d_eligible_bandwidths_by_block_rule": rules,
        "d1d_plain_statement": (
            f"A10b.1's block rule leaves {a:.3f} of the 21-rung bandwidth sweep eligible. The "
            f"alternative it explicitly rejected -- declaring h < 60 s ineligible -- leaves {b:.3f}. "
            f"A10b.1's rule is therefore {'WORSE' if a < b else 'no worse'} than the alternative it "
            "rejected, by the measure used to reject it. The rejection rationale was that the "
            "alternative 'would exclude v3's premarket knee of 16 s from the search range by "
            f"construction'; A10b.1's own rule also excludes h = 16 s, since the block floor binds "
            f"below h = {bfe * br:.1f} s."),
        "block_floor_event_s_for_C1": bfe,
    }

    # ---------------------------------------------------------------- D2
    d = pd.read_parquet(rel("results/phase_10b/artifacts/t2_control_curves.parquet"))
    npair_map = {float(t): int(n) for t, n in zip(ladder, npair)}
    exc = {}
    for nm in ("C1", "C2"):
        per_h = {}
        for h, g in d[(d["control"] == nm)].groupby("h"):
            g = g.sort_values("T").reset_index(drop=True)
            he = bool(g["h_eligible"].iloc[0])
            ok = g["eligible"].to_numpy()
            above, below = g["above"].to_numpy(), g["below"].to_numpy()
            out = above | below
            idx_out = np.flatnonzero(out & ok)
            runs, cur = [], []
            for i in idx_out:
                if cur and i == cur[-1] + 1:
                    cur.append(i)
                else:
                    if cur:
                        runs.append(cur)
                    cur = [i]
            if cur:
                runs.append(cur)
            n_ok = int(ok.sum())
            # D2c: share with and without the low-power (min_pairs) exclusion
            share_excl = float(1 - (above & ok).sum() / n_ok) if n_ok else np.nan
            n_all = int(len(g))
            share_incl = float(1 - above.sum() / n_all) if n_all else np.nan
            per_h[f"h={h:g}"] = {
                "h": float(h), "h_eligible": he, "n_rungs_eligible": n_ok, "n_rungs_all": n_all,
                "excursions": [{"rung_index": int(i), "T_s": float(g["T"][i]),
                                "n_pairs": npair_map.get(float(g["T"][i])),
                                "direction": "above" if above[i] else "below"} for i in idx_out],
                "longest_consecutive_run": int(max((len(r) for r in runs), default=0)),
                "n_distinct_runs": len(runs),
                "run_lengths": [len(r) for r in runs],
                "share_inside_upper_only_minpairs_applied": share_excl,
                "share_inside_upper_only_all_33_rungs": share_incl,
                "n_above_eligible": int((above & ok).sum()),
                "n_below_eligible": int((below & ok).sum())}
        exc[nm] = per_h
    n_elig_rungs = int(elig_T.sum())
    d2 = {
        "task": "D2", "read_only": True,
        "source": "results/phase_10b/artifacts/t2_control_curves.parquet (A10b.1 amended run)",
        "by_control": exc,
        "d2c_note": ("The min_pairs_pooled exclusion is ALREADY applied to the inside-band share in "
                     "the implementation -- rungs with fewer than "
                     f"{c3c['min_pairs_pooled']} window pairs never enter it. Both readings are "
                     "reported so the effect of that choice is visible: 'minpairs_applied' is what "
                     "the gate used, 'all_33_rungs' is what it would have been without the rule. "
                     "n_pairs is given for every excursion so low-power rungs are identifiable."),
        "d2d_false_positive_arithmetic": {
            "band_level": 0.95, "n_eligible_rungs": n_elig_rungs,
            "expected_outside_pointwise": 0.05 * n_elig_rungs,
            "expected_above_pointwise": 0.025 * n_elig_rungs,
            "caveat": ("Pointwise arithmetic assumes independent rungs. Allan values at neighbouring "
                       "rungs come from nested windows and are strongly correlated, so this "
                       "expectation is a lower bound on the variability of the count and adjacency "
                       "in the excursion runs above is the direct evidence of that correlation.")},
    }

    out = {"phase": "10b", "diagnostic": "DX10b.1", "config_hash": chash,
           "diagnostic_config": dcfg, "no_real_event_read": True,
           "D0": d0, "D1": d1, "D2": d2,
           "source": "research/phase_10b/dx1_d0_d1_d2.py:main"}
    write_json(rel(f"{DXA}/d1_satisfiability_audit.json"), {"D0": d0, "D1": d1})
    write_json(rel(f"{DXA}/d2_excursion_map.json"), d2)
    write_json(rel(f"{DXA}/d0_state.json"), d0)

    print("D0b regeneration:", "ALL MATCH" if all_match else "MISMATCH -- ROW 2 FIRES")
    for k, v in repro.items():
        print(f"   {k}: stored {v['stored_n_prints']:,} regen {v['regenerated_n_prints']:,} "
              f"{'ok' if v['match'] else 'MISMATCH'}")
    print(f"\nD1 eligible-bandwidth share of the {len(hs_t4)}-rung sweep:")
    for k, v in rules.items():
        print(f"   {k:42s} {v['n_eligible']:2d}/{len(hs_t4)} = {v['eligible_share']:.3f}")
    print(f"\n   block_floor_event = {bfe:.2f} s -> binds below h = {bfe*br:.1f} s")
    print(f"   {d1['d1d_plain_statement']}")
    print("\nD1a reachability:")
    for c in crit:
        extra = ""
        if "T4 crossing" in c["statistic"]:
            extra = (f" | nearest eligible h {c['nearest_eligible_bandwidth_s']} "
                     f"({c['rungs_from_nearest_eligible']:.2f} rungs) -> "
                     f"{'REACHABLE' if c['reachable_within_1_rung_after_eligibility'] else 'NOT REACHABLE'}")
        verdict = "in range" if c["inside_range"] else f"OUT by {c['rungs_outside']:.2f} rungs"
        print(f"   {c['criterion']:34s} target {c['target_s']:<9.6g} range "
              f"[{c['range_s'][0]:.4g}, {c['range_s'][1]:.4g}] {verdict}{extra}")
    print("\nD2 excursion runs:")
    for nm in ("C1", "C2"):
        for hk, v in exc[nm].items():
            if v["h_eligible"]:
                print(f"   {nm} {hk:10s} above={v['n_above_eligible']} below={v['n_below_eligible']} "
                      f"runs={v['run_lengths']} longest={v['longest_consecutive_run']} "
                      f"| inside(upper,minpairs)={v['share_inside_upper_only_minpairs_applied']:.4f}")
    print(f"\nD2d expected by chance at {n_elig_rungs} eligible rungs: "
          f"{0.05*n_elig_rungs:.2f} outside, {0.025*n_elig_rungs:.2f} above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
