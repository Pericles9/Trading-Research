"""T4 -- compare T3's per-decile cost against the baseline and T1's bound. STOP HERE.

No full-tier query, no T5. Per the prompt's Approval Gate, this is where execution stops
for Cooper's explicit review before any full-tier promotion.
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
BASELINE_RT_BP = 70.98


def main() -> int:
    t3 = json.loads((ARTIFACTS / "t3_cost_by_decile.json").read_text())
    t1 = json.loads((ARTIFACTS / "t1_threshold.json").read_text())

    rows = []
    for r in sorted(t3["by_decile"], key=lambda x: x["decile"]):
        rt_equiv_p50 = 2.0 * r["eff_bp_p50"]  # one-sided -> round-trip-equivalent
        rows.append({
            "decile": r["decile"], "n": r["n"],
            "eff_bp_p50_one_sided": r["eff_bp_p50"],
            "round_trip_equivalent_bp_p50": rt_equiv_p50,
            "below_baseline_70_98bp": bool(rt_equiv_p50 < BASELINE_RT_BP),
            "pct_of_baseline": rt_equiv_p50 / BASELINE_RT_BP,
        })
    n_below = sum(1 for r in rows if r["below_baseline_70_98bp"])

    out = {
        "task": "T4", "phase": "impact_by_participation",
        "comparison_method": "round_trip_equivalent_bp_p50 = 2 * eff_bp_p50 (T3's one-sided "
            "median effective spread, doubled for a round-trip-comparable unit) vs. Phase 11's "
            "flat 70.98 bp round-trip headline (results/phase_11/artifacts/t7_cost_vs_capture.json).",
        "caveat_from_t1": t1["what_this_bound_is"],
        "caveat_stated_again_here": (
            "T1 found the reachability bound already clears p_breakeven at the FULL 70.98 bp "
            "cost (0.6501 vs 0.6000), and the ~0.26 shortfall against T3's actual "
            "p_clear_optimistic (0.3885) is dominated by ORDER (which barrier is touched "
            "first), not by barrier magnitude. So even where this comparison shows a decile's "
            "cost below baseline, that does NOT by itself establish the D24/D25 gap closes -- "
            "it establishes only that a narrower cost input is available; whether narrower "
            "barriers built from it would also improve the win-the-race probability is exactly "
            "what T1 flagged as needing the exact reclassification, not run here."
        ),
        "by_decile": rows,
        "n_deciles_below_baseline": n_below,
        "n_deciles_total": len(rows),
        "no_recommendation": "Per the Evidence Standard, no interpretation of what this means "
            "for D24/D25 follows. Comparison stated as data.",
        "STOP": ("T0-T4 complete. No full-tier query has been run. T5 (full-tier promotion and "
                 "the loop-closing p_clear recomputation) is BLOCKED pending Cooper's explicit "
                 "review of T0-T4, per this prompt's Approval Gate."),
        "source": "research/impact_by_participation/t4_compare.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t4_compare",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "t4_compare.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"T4: {n_below}/{len(rows)} deciles show round-trip-equivalent cost below "
          f"{BASELINE_RT_BP} bp baseline (dev tier, n=50 events, T=0 only)")
    for r in rows:
        flag = "BELOW" if r["below_baseline_70_98bp"] else "at/above"
        print(f"  decile {r['decile']:>2}  n={r['n']:>7,}  "
              f"rt_equiv={r['round_trip_equivalent_bp_p50']:6.2f} bp  "
              f"({r['pct_of_baseline']:.1%} of baseline)  {flag}")
    print("\nT4: STOP. T0-T4 complete, no full-tier query run. Awaiting Cooper's review "
          "before any full-tier promotion or T5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
