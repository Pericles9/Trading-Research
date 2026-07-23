"""
Phase 6 T1 - eligibility waterfall.

Read-only. D1 universe (in_scope=TRUE AND source_file='file1') is read from
results/phase_5a/artifacts/sampling_frame.parquet rather than re-querying
momentum_events_canonical: that parquet IS the exact materialization of
that query (Phase 5a T2, research/phase_5a/t2_sampling_frame.py), and the
canonical view's trades_ingested/quotes_ingested columns force a DISTINCT
full-table scan of filtered_trades AND filtered_quotes on every query
(src/data/canonical.py) - reusing the frozen artifact avoids a redundant
multi-billion-row scan for a value that has not changed since Phase 5a
(dev v4 was pinned at phase-5a-approved with no canonical-view mutation
since). Freshness is checked by asserting the frame row count still
equals the expected D1 total before proceeding.

Eligibility (D2, phase_6 prompt): event-day trades present, i.e.
substr(trades_bitmap, 4, 1) = '1' (1-indexed; bitmap positions are
T-3..T+3 per config/phase_5.json's offsets=[-3..3], position 4 = offset 0).
clean_window is NOT applied as a filter - this is an intraday T=0
measurement and event-day-only events are fully eligible per D2.
"""
import json

import pandas as pd

PHASE_6_CONFIG = "config/phase_6.json"
SAMPLING_FRAME = "results/phase_5a/artifacts/sampling_frame.parquet"
OUT_SUMMARY = "results/phase_6/artifacts/t1_eligibility.json"
OUT_ELIGIBLE_PARQUET = "results/phase_6/artifacts/t1_eligible_events.parquet"


def main():
    with open(PHASE_6_CONFIG) as f:
        cfg = json.load(f)
    th = cfg["escalation_thresholds"]

    frame = pd.read_parquet(SAMPLING_FRAME)
    n_total = len(frame)
    freshness_ok = n_total == th["d1_total_expected"]
    print(f"D1 frame loaded: {n_total} rows (expected {th['d1_total_expected']}, freshness_ok={freshness_ok})")

    # position 4, 1-indexed -> Python index 3
    frame["t0_present"] = frame["trades_bitmap"].str[3] == "1"
    eligible = frame[frame["t0_present"]].copy()
    ineligible = frame[~frame["t0_present"]].copy()

    n_eligible = len(eligible)
    n_ineligible = len(ineligible)
    ineligible_pct = 100.0 * n_ineligible / n_total

    ineligible_patterns = (
        ineligible["trades_bitmap"].value_counts().rename_axis("trades_bitmap").reset_index(name="n")
        .sort_values("n", ascending=False)
    )

    eligible_cols = ["ticker", "event_date_canonical", "momentum_pct", "source_file",
                      "clean_window", "trades_bitmap", "quotes_bitmap"]
    eligible[eligible_cols].to_parquet(OUT_ELIGIBLE_PARQUET, index=False)

    row2_triggered = ineligible_pct > th["ineligible_share_max_pct"]

    summary = {
        "phase": "6", "task": "T1",
        "d1_total": n_total,
        "d1_freshness_check": {"expected": th["d1_total_expected"], "observed": n_total, "pass": freshness_ok},
        "eligible": {
            "n": n_eligible,
            "clean_window_true": int(eligible["clean_window"].sum()),
            "clean_window_false_event_day_only": int((~eligible["clean_window"]).sum()),
        },
        "ineligible": {
            "n": n_ineligible,
            "pct_of_d1": round(ineligible_pct, 4),
            "bitmap_patterns": ineligible_patterns.to_dict(orient="records"),
        },
        "escalation_row2_triggered": row2_triggered,
        "escalation_row2_threshold": {"max_pct": th["ineligible_share_max_pct"], "max_n": th["ineligible_share_max_n"]},
        "source": "research/phase_6/t1_eligibility.py:main",
        "artifact": OUT_ELIGIBLE_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not freshness_ok:
        print(f"\n*** WARNING: D1 frame row count {n_total} != expected {th['d1_total_expected']} - frame may be stale ***")
    if row2_triggered:
        print(f"\n*** ESCALATION row 2: ineligible share {ineligible_pct:.2f}% > {th['ineligible_share_max_pct']}% - HARD STOP ***")


if __name__ == "__main__":
    main()
