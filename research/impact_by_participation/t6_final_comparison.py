"""T6 (final) -- compare T5's exact threshold against T3's measured achievable cost.

The decisive comparison this whole line of work was built to make: does ANY participation
decile's measured cost reach the round_trip_bp T5 established is actually required?
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"


def main() -> int:
    t3 = json.loads((ARTIFACTS / "t3_cost_by_decile.json").read_text())
    t5 = json.loads((ARTIFACTS / "t5_exact_reclassification.json").read_text())
    required_bp = t5["threshold_interpolated_round_trip_bp"]

    rows = []
    for r in sorted(t3["by_decile"], key=lambda x: x["decile"]):
        rt_equiv = 2.0 * r["eff_bp_p50"]
        rows.append({
            "decile": r["decile"], "n": r["n"],
            "measured_round_trip_equivalent_bp": rt_equiv,
            "required_round_trip_bp": required_bp,
            "multiple_of_required": rt_equiv / required_bp,
            "clears_required_threshold": bool(rt_equiv <= required_bp),
        })
    n_clearing = sum(1 for r in rows if r["clears_required_threshold"])
    min_measured = min(r["measured_round_trip_equivalent_bp"] for r in rows)
    min_multiple = min_measured / required_bp

    out = {
        "task": "T6 (final comparison)", "phase": "impact_by_participation",
        "required_round_trip_bp_to_close_closest_cell_gap": required_bp,
        "baseline_round_trip_bp": 70.98,
        "required_as_pct_of_baseline": required_bp / 70.98,
        "by_decile": rows,
        "n_deciles_clearing_required_threshold": n_clearing,
        "n_deciles_total": len(rows),
        "cheapest_decile_measured_bp": min_measured,
        "cheapest_decile_multiple_of_required": min_multiple,
        "finding": (
            f"0 of {len(rows)} participation deciles reach the required ~{required_bp:.1f} bp "
            f"round-trip cost. Even the cheapest measured decile ({min_measured:.1f} bp "
            f"round-trip-equivalent) is {min_multiple:.1f}x the threshold that would close the "
            "closest cell's gap. The required cost is a large reduction from baseline "
            f"({required_bp/70.98:.1%} of 70.98 bp) -- far beyond what participation-rate "
            "variation alone was measured to achieve on this dev cohort."
        ),
        "no_recommendation": "Per the Evidence Standard, no interpretation of what this means "
            "for D24/D25/candidate (b) follows. Stated as data.",
        "source": "research/impact_by_participation/t6_final_comparison.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t6_final_comparison",
    }
    (ARTIFACTS / "t6_final_comparison.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"Required round_trip_bp to close the gap: {required_bp:.2f} "
          f"({required_bp/70.98:.1%} of the 70.98 bp baseline)")
    print(f"{n_clearing}/{len(rows)} deciles clear it")
    for r in rows:
        print(f"  decile {r['decile']:>2}  measured={r['measured_round_trip_equivalent_bp']:6.2f} bp  "
              f"({r['multiple_of_required']:.1f}x required)  "
              f"{'CLEARS' if r['clears_required_threshold'] else 'does not clear'}")
    print(f"\nCheapest decile is {min_multiple:.1f}x the required threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
