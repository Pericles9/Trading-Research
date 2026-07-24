"""
Phase 6c T3' - closure artifact. Amendment 8 disposition: gate outcome (b),
superseded by D4 (tick-only analysis). No boolean - the mechanism-
confirmation question is closed by severance, not by a pass/fail verdict.
Assembles already-committed T1/T2 artifacts plus the A7.1 volume
cross-check table. No re-measurement.
"""
import json

T1_ARTIFACT = "results/phase_6c/artifacts/t1_stratified_criteria.json"
T2_ARTIFACT = "results/phase_6c/artifacts/t2_residual_classification.json"
CHART04_ARTIFACT = "results/phase_6c/artifacts/a71_chart04_summary.json"
OUT_JSON = "results/phase_6c/artifacts/closure.json"


def main():
    with open(T1_ARTIFACT) as f:
        t1 = json.load(f)
    with open(T2_ARTIFACT) as f:
        t2 = json.load(f)
    with open(CHART04_ARTIFACT) as f:
        chart04 = json.load(f)

    volume_cross_check = [
        {
            "ticker": e["ticker"], "cohort": e["cohort"], "t2_class": e["t2_class"],
            "t0_volume_ours": e["t0_volume_ours"], "spine_event_volume": e["spine_event_volume"],
            "volume_ratio": e["volume_ratio"],
        }
        for e in chart04["events"]
    ]

    final_classification = {
        "band_margin": ["NEPH", "ZENA", "PSIX"],
        "coverage_gap": ["ACET", "NUKK"],
        "unexplained": ["SCLX", "VEEE"],
    }

    closure = {
        "phase": "6c",
        "task": "T3'",
        "title": "Closure artifact - Amendment 8 disposition",
        "disposition": "b_superseded_by_D4",
        "amendment7_gate_outcome": "b",
        "amendment7_gate_reasoning": (
            "The pre-registered thinness mechanism (P1/P2/P3) is falsified for SCLX/VEEE by "
            "the volume cross-check's direction: their tick volume exceeds the spine's "
            "event_volume by 35.1x (SCLX) and 13.8x (VEEE); a coverage gap can only produce a "
            "volume deficit, not a surplus. No coverage_thin_symmetric category is created."
        ),
        "final_mechanism_statement": (
            "momentum_events' numeric columns carry inconsistent adjustment bases - per ticker, "
            "and per column within the same row. Evidence: NUKK price factor 7.98 with volume "
            "factor 8.001 (one coherent 1:8 reverse split); AMC (a band-passing control) price "
            "factor 5.24 with volume factor 10.06 (incoherent across columns); SCLX/VEEE volume "
            "factors 35.1x/13.8x against near-1 price ratios; NEPH/ZENA/PSIX/AMCX at 1.000-1.026 "
            "tick-vs-spine volume parity. The tick archive is the trustworthy layer; the spine's "
            "numeric columns cannot be certified even on events that pass price-ratio checks. "
            "Per-ticker factor characterization is not pursued - the dependency is severed "
            "instead (D4, docs/Universe-Decisions.md)."
        ),
        "final_classification": final_classification,
        "final_classification_unchanged_from_t2": True,
        "stratified_criteria": t1,
        "residual_classifications": t2["classifications"],
        "residual_classification_medians": t2["primary_cohort_medians"],
        "volume_cross_check": volume_cross_check,
        "d4_reference": "docs/Universe-Decisions.md#d4",
        "source": "research/phase_6c/t3_closure.py:main",
    }

    with open(OUT_JSON, "w") as f:
        json.dump(closure, f, indent=2, default=str)
    print(f"closure.json written: disposition={closure['disposition']}, "
          f"final_classification={final_classification}")


if __name__ == "__main__":
    main()
