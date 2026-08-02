"""
Phase 8 A10.1-T1 - backfill two carried labels into the anchor grid.

Scan-free; no price recomputation. Reads only existing phase-8 artifacts.

  has_premarket_print (A10.1a-ii): per event, TRUE iff the event has a T0 print
    at/before 09:00 ET (minute_index<=300) - i.e. the 09:00 clock anchor is
    DEFINED. Derived from t4_anchors.parquet (presence of the '0900' anchor
    rows). has_premarket_print=FALSE is exactly the 1,740 dropped from the 09:00
    column only. (The 09:00-undefined set is what pins the count; the label is
    named loosely but the 09:00 cutoff is deliberate.)

  flag_possible_row_cap (A10.1c, Cooper 2026-08-01: homed in the PHASE-8
    artifact like flag_has_dup_prints in 6b's event_index_v2, NOT canonical.py -
    escalation row 9 / 'nothing in src/ changes mid-phase' stand; the canonical.py
    addition is a remediation-phase open item). Definition: T=0 print count
    exactly in {50000,100000,200000}. Frozen, exact, no tolerance.

Escalation row 12: has_premarket_print=FALSE != 1740 OR flag_possible_row_cap
!= 8 -> hard stop (artifacts disagree with the reported run).
"""
from __future__ import annotations

import json

import pandas as pd

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
T4_PATH = "results/phase_8/artifacts/t4_anchors.parquet"
ROWCAP_COUNTS = "results/phase_8/artifacts/t2_row_cap_counts.parquet"
OUT_PARQUET = "results/phase_8/artifacts/a101_labels.parquet"
OUT_JSON = "results/phase_8/artifacts/a101_label_backfill.json"
ROUND_NUMBERS = [50_000, 100_000, 200_000]
KEY = ["ticker", "event_date_canonical", "mp"]


def main():
    d1 = pd.read_parquet(D1_PATH)
    d1["event_date_canonical"] = pd.to_datetime(d1["event_date_canonical"])
    d1["mp"] = d1["momentum_pct"].round(2)
    base = d1[KEY].drop_duplicates().reset_index(drop=True)
    assert len(base) == 15763, f"D1 base {len(base)} != 15763"

    # has_premarket_print: present in the '0900' anchor rows of t4_anchors.parquet
    grid = pd.read_parquet(T4_PATH)
    grid["event_date_canonical"] = pd.to_datetime(grid["event_date_canonical"])
    has0900 = grid[grid.anchor_name == "0900"][KEY].drop_duplicates()
    has0900["has_premarket_print"] = True
    lab = base.merge(has0900, on=KEY, how="left")
    lab["has_premarket_print"] = lab["has_premarket_print"].fillna(False).astype(bool)

    # flag_possible_row_cap: T0 print count exactly in the round-number set
    rc = pd.read_parquet(ROWCAP_COUNTS)
    rc["event_date_canonical"] = pd.to_datetime(rc["event_date_canonical"])
    rc["flag_possible_row_cap"] = rc["t0_print_count"].isin(ROUND_NUMBERS)
    lab = lab.merge(rc[KEY + ["t0_print_count", "flag_possible_row_cap"]], on=KEY, how="left")
    lab["flag_possible_row_cap"] = lab["flag_possible_row_cap"].fillna(False).astype(bool)

    n_no_pm = int((~lab["has_premarket_print"]).sum())
    n_rowcap = int(lab["flag_possible_row_cap"].sum())

    cap_events = lab[lab.flag_possible_row_cap].merge(rc[KEY + ["t0_print_count"]], on=KEY)
    cap_list = [{"ticker": r.ticker, "event_date": str(pd.Timestamp(r.event_date_canonical).date()),
                 "momentum_pct": float(r.mp), "t0_print_count": int(r.t0_print_count_x if hasattr(r, "t0_print_count_x") else r.t0_print_count)}
                for r in cap_events.itertuples()]
    cap_list.sort(key=lambda d: -d["t0_print_count"])

    lab.to_parquet(OUT_PARQUET, index=False)

    row12_fail = (n_no_pm != 1740) or (n_rowcap != 8)
    summary = {
        "phase": "8", "task": "A10.1-T1",
        "source": "research/phase_8/a101_backfill.py:main",
        "scan_free": True, "price_recomputation": False,
        "has_premarket_print": {
            "definition": "T0 print at/before 09:00 ET (minute_index<=300); FALSE = 09:00 anchor undefined",
            "true_n": int(lab["has_premarket_print"].sum()),
            "false_n": n_no_pm,
            "expected_false_n": 1740,
            "provenance": "t4_anchors.parquet '0900' anchor row presence",
        },
        "flag_possible_row_cap": {
            "definition": "T0 print count exactly in {50000,100000,200000}",
            "home": "phase-8 artifact (a101_labels.parquet), parallel to flag_has_dup_prints; canonical.py addition = remediation open item (Cooper 2026-08-01)",
            "true_n": n_rowcap,
            "expected_n": 8,
            "events": cap_list,
            "provenance": "t2_row_cap_counts.parquet",
        },
        "escalation_row_12_triggered": row12_fail,
        "artifact": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if row12_fail:
        print("\n*** ESCALATION ROW 12 TRIGGERED - HARD STOP ***")


if __name__ == "__main__":
    main()
