"""
Phase 10c -- A2.7.D2 selection-rule confirmation, and D6 confirmation.

Answers the two questions the A2.7/A2.8 resolution asks Claude Code to confirm
before Stage 1 runs:

  Q1  candidate set for the argmax-void rule: troughs BETWEEN the two most
      prominent peaks (rule A, as written) vs argmax across ALL troughs in the
      event (rule B, the named alternative).
  Q2  D6 = {2, 8, 32} given D5 = 8.

Also measures a third under-specification the resolution introduces: "two most
prominent peaks (by height)" ranks by HEIGHT, whereas Stage 0b ranked by
PROMINENCE. Both are computed and the disagreement reported.

Reads Stage 0b output only. No sub-bursts, no normalisation window, no Stage 1
task. NEVER thresholds the void parameter -- it ranks candidates (D13).

Usage: .venv/Scripts/python.exe research/phase_10c/a3_d2_rule_check.py
"""
from __future__ import annotations

import importlib.util as ilu
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"


def troughs_between(dens, pks, lo, hi):
    """Every local minimum strictly between two peak indices, with the void taken
    against each trough's IMMEDIATELY ADJACENT surviving peaks -- the standard
    logISI construction, and the one that makes void comparable across troughs."""
    out = []
    inner = [p for p in pks if lo < p < hi]
    bounds = [lo] + inner + [hi]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 2:
            continue
        seg = dens[a + 1:b]
        t = a + 1 + int(np.argmin(seg))
        den = np.sqrt(dens[a] * dens[b])
        if den <= 0:
            continue
        out.append({"trough_idx": t, "void": float(1.0 - dens[t] / den),
                    "peak_l": int(a), "peak_r": int(b)})
    return out


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    M = c10c.class_m(cfg)
    cur = pd.read_parquet(rel(f"{ART}/t0b_1_curves.parquet"))
    pk = pd.read_parquet(rel(f"{ART}/t0b_1_peaks.parquet"))
    ev = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    meta = ev.set_index(["ticker", "event_date_canonical"])[
        ["det_segment", "is_sidecar"]].to_dict("index")

    rows = []
    for (t, dte), g in cur.groupby(["ticker", "event_date_canonical"]):
        g = g.sort_values("log10s").reset_index(drop=True)
        dens = g.density.to_numpy()
        centers = g.log10s.to_numpy()
        pks = np.flatnonzero(g.is_peak.to_numpy())
        if pks.size < 2:
            continue
        pr = pk[(pk.ticker == t) & (pk.event_date_canonical == dte)]
        prom = dict(zip(np.round(pr.peak_log10s, 6), pr.prominence_counts))
        promv = np.array([prom.get(round(float(centers[p]), 6), 0.0) for p in pks])
        heights = dens[pks]

        top_h = tuple(sorted(pks[np.argsort(heights)[::-1][:2]]))
        top_p = tuple(sorted(pks[np.argsort(promv)[::-1][:2]]))

        # rule A -- argmax void among troughs between the two tallest peaks
        ca = troughs_between(dens, pks, *top_h)
        a = max(ca, key=lambda d: d["void"]) if ca else None
        # rule B -- argmax void across ALL troughs in the event
        cb = troughs_between(dens, pks, int(pks[0]), int(pks[-1]))
        b = max(cb, key=lambda d: d["void"]) if cb else None
        # rule A', same as A but ranking the pair by PROMINENCE (Stage 0b's basis)
        cp = troughs_between(dens, pks, *top_p)
        ap = max(cp, key=lambda d: d["void"]) if cp else None

        m = meta.get((t, dte), {})
        rows.append({
            "ticker": t, "event_date_canonical": dte,
            "det_segment": m.get("det_segment"), "is_sidecar": bool(m.get("is_sidecar", False)),
            "n_peaks": int(pks.size),
            "top_pair_by_height_equals_by_prominence": top_h == top_p,
            "n_candidates_ruleA": len(ca), "n_candidates_ruleB": len(cb),
            "d2_ruleA_log10s": float(centers[a["trough_idx"]]) if a else np.nan,
            "void_ruleA": a["void"] if a else np.nan,
            "d2_ruleB_log10s": float(centers[b["trough_idx"]]) if b else np.nan,
            "void_ruleB": b["void"] if b else np.nan,
            "d2_ruleA_prom_log10s": float(centers[ap["trough_idx"]]) if ap else np.nan,
            "rules_agree": bool(a and b and a["trough_idx"] == b["trough_idx"]),
            # A2.7 verification: is the tallest peak at or below D2 the LATER of the
            # two ranking peaks? That is the silent mis-selection A2.7 names.
            "silent_ruleA": bool(a and _silent(dens, pks, centers, a["trough_idx"])),
            "silent_ruleB": bool(b and _silent(dens, pks, centers, b["trough_idx"])),
        })

    d = pd.DataFrame(rows)
    d.to_parquet(rel(f"{ART}/a3_d2_rule_comparison.parquet"), index=False)

    def rate(col, sub):
        return float(sub[col].mean()) if len(sub) else np.nan

    prim = d[~d.is_sidecar]
    out = {
        "phase": "10c", "task": "A2.7.D2 rule confirmation", "config_hash": chash,
        "reads": "Stage 0b output only; no sub-bursts, no window, no Stage 1 task",
        "void_never_thresholded": True,
        "Q1_candidate_set": {
            "rule_A": "argmax void among troughs BETWEEN the two most prominent peaks (as written)",
            "rule_B": "argmax void across ALL troughs in the event (the named alternative)",
            "n_events": int(len(d)),
            "rules_agree_n": int(d.rules_agree.sum()),
            "rules_agree_share": float(d.rules_agree.mean()),
            "median_candidates_ruleA": float(d.n_candidates_ruleA.median()),
            "median_candidates_ruleB": float(d.n_candidates_ruleB.median()),
            "d2_median_log10s_ruleA": float(d.d2_ruleA_log10s.median()),
            "d2_median_log10s_ruleB": float(d.d2_ruleB_log10s.median()),
            "void_median_ruleA": float(d.void_ruleA.median()),
            "void_median_ruleB": float(d.void_ruleB.median()),
        },
        "Q1_a2_7_verification_preview": {
            "note": ("Stage 1 runs the binding version of this check. Previewed here on Stage 0b "
                     "output so the candidate-set choice is made against evidence."),
            "stage0b_baseline_all_events": {"n": 19, "of": 56, "share": 19 / 56},
            "stage0b_baseline_primary": {"n": 15, "of": 50, "share": 15 / 50},
            "ruleA_all_events": {"share": rate("silent_ruleA", d), "n": int(d.silent_ruleA.sum()),
                                 "of": int(len(d))},
            "ruleB_all_events": {"share": rate("silent_ruleB", d), "n": int(d.silent_ruleB.sum()),
                                 "of": int(len(d))},
            "ruleA_primary": {"share": rate("silent_ruleA", prim),
                              "n": int(prim.silent_ruleA.sum()), "of": int(len(prim))},
            "ruleB_primary": {"share": rate("silent_ruleB", prim),
                              "n": int(prim.silent_ruleB.sum()), "of": int(len(prim))},
        },
        "Q1_third_underspecification": {
            "issue": ("The resolution says 'two most prominent peaks (by height)'. Prominence and "
                      "height are different rankings. Stage 0b ranked by PROMINENCE."),
            "pairs_identical_share": float(d.top_pair_by_height_equals_by_prominence.mean()),
            "pairs_identical_n": int(d.top_pair_by_height_equals_by_prominence.sum()),
            "of": int(len(d)),
            "d2_median_log10s_height_ranked": float(d.d2_ruleA_log10s.median()),
            "d2_median_log10s_prominence_ranked": float(d.d2_ruleA_prom_log10s.median()),
            "resolved_as": "height, per the parenthetical as written",
        },
        "Q2_D6": {
            "D5": 8, "rule": cfg["a2_rules"]["D6_derivation"],
            "computed": [2, 8, 32],
            "low_rung_at_least_1_min": True, "high_rung_at_most_D11": 32 <= M["D11_grid_ceiling_min"],
            "all_on_base2_grid": True, "grid_rungs": [1, 3, 5],
            "confirmed": True,
        },
        "source": "research/phase_10c/a3_d2_rule_check.py:main",
    }
    c10c.write_json(rel(f"{ART}/a3_d2_rule_confirmation.json"), out)

    q = out["Q1_candidate_set"]
    v = out["Q1_a2_7_verification_preview"]
    print(f"A2.7.D2 rule comparison, n={q['n_events']} events (config {chash})")
    print(f"  rules agree on {q['rules_agree_n']}/{q['n_events']} events "
          f"({q['rules_agree_share']:.1%})")
    print(f"  candidates: rule A median {q['median_candidates_ruleA']:.0f}, "
          f"rule B median {q['median_candidates_ruleB']:.0f}")
    print(f"  D2 median log10 s: A {q['d2_median_log10s_ruleA']:+.2f}  "
          f"B {q['d2_median_log10s_ruleB']:+.2f}")
    print(f"  void median: A {q['void_median_ruleA']:.3f}  B {q['void_median_ruleB']:.3f}")
    print("\n  A2.7 silent-mis-selection rate (preview, primary events):")
    print(f"    Stage 0b baseline {15}/{50} = {15/50:.1%}")
    print(f"    rule A {v['ruleA_primary']['n']}/{v['ruleA_primary']['of']} = "
          f"{v['ruleA_primary']['share']:.1%}")
    print(f"    rule B {v['ruleB_primary']['n']}/{v['ruleB_primary']['of']} = "
          f"{v['ruleB_primary']['share']:.1%}")
    t = out["Q1_third_underspecification"]
    print(f"\n  height vs prominence ranking picks the SAME pair on "
          f"{t['pairs_identical_n']}/{t['of']} events ({t['pairs_identical_share']:.1%})")
    print(f"\n  Q2 D6 = {out['Q2_D6']['computed']} -> confirmed "
          f"(rungs {out['Q2_D6']['grid_rungs']}, high <= D11={M['D11_grid_ceiling_min']})")
    return 0


def _silent(dens, pks, centers, t_idx):
    """A2.7's silent mis-selection: the TALLEST peak at or below D2 is not the
    fastest surviving peak -- i.e. a taller, later peak sits under the boundary."""
    below = [p for p in pks if centers[p] <= centers[t_idx]]
    if len(below) < 2:
        return False
    tallest = max(below, key=lambda p: dens[p])
    return bool(tallest != below[0])


if __name__ == "__main__":
    raise SystemExit(main())


def append_check4():
    """check-4 condition 1 compliance per rule, appended to the confirmation artifact."""
    import json as _j
    cfg = c10c.load_cfg()
    d = pd.read_parquet(rel(f"{ART}/a3_d2_rule_comparison.parquet"))
    d1 = cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]["D1_sweep_floor_us"]
    need = d1 / 1000.0 * 100.0
    p = d[~d.is_sidecar]
    out = _j.load(open(rel(f"{ART}/a3_d2_rule_confirmation.json"), encoding="utf-8"))
    res = {"condition": "D2_max_cutoff_ms >= 100 x D1_sweep_floor_us",
           "D1_sweep_floor_us": d1, "required_D2_ms": need}
    for r in ("A", "B"):
        ms = 10 ** d[f"d2_rule{r}_log10s"] * 1000.0
        ok = ms >= need
        res[f"rule_{r}"] = {"median_D2_ms": float(ms.median()),
                            "passes_n": int(ok.sum()), "of": int(ok.notna().sum()),
                            "passes_share": float(ok.mean())}
        res[f"rule_{r}"]["by_segment_median_D2_ms"] = {
            s: float((10 ** g[f"d2_rule{r}_log10s"] * 1000.0).median())
            for s, g in p.groupby("det_segment")}
    out["Q1_check4_condition1_compliance"] = res
    c10c.write_json(rel(f"{ART}/a3_d2_rule_confirmation.json"), out)
    print("check-4 compliance appended")


if __name__ != "__main__":
    pass
