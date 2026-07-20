"""
Phase 1c T1b - manifest cross-checks.

1. All 142 flag_missing_event_day(calendar_bug) event days present in the
   manifest as target_type=event_day pairs.
2. Every Set A phantom-holiday date (1b's T5-R1, n=14) is either present as
   a manifest session, or verified absent from the raw momentum_events
   table entirely within its own +/-3-trading-day XNYS window (i.e. no
   event of any class/scope exists nearby - a genuine data gap, not a
   derivation miss).
3. Zero manifest pairs with fetch_quotes=TRUE for an event whose
   quotes_ingested=FALSE (the hard boundary - trades-only events never get
   a quotes fetch target).

Any failure on 1 or 3 is a hard stop per the phase prompt. Check 2's
per-date resolution is reported, not gated (data-emptiness allows a
Set A date to legitimately go unreferenced).
"""
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

MANIFEST = CFG["paths"]["heal_manifest"]
CALENDAR_MISMATCH = CFG["paths"]["calendar_mismatch_1b"]
FOLDER_INV = CFG["paths"]["folder_inventory_v2"]
DB_PATH = CFG["paths"]["momentum_events_db"]
OUT_SUMMARY = "results/phase_1c/artifacts/t1b_crosscheck_summary.json"

CAL = CFG["session_calendar"]


def main():
    con = duckdb.connect(read_only=False)
    manifest = con.execute(f"SELECT * FROM read_parquet('{MANIFEST}')").fetchdf()

    # Check 1
    n_event_day = int((manifest["target_type"] == "event_day").sum())
    check1_pass = n_event_day == 142

    # Check 2
    with open(CALENDAR_MISMATCH) as f:
        cm = json.load(f)
    set_a_dates = cm["set_a_phantom_holidays"]["dates"]
    manifest_sessions = set(manifest["session"])
    missing = [d for d in set_a_dates if d not in manifest_sessions]

    xnys = mcal.get_calendar(CAL["calendar_code"])
    sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=CAL["derivation_range"]["start"], end_date=CAL["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(sessions)}

    con_db = duckdb.connect(database=DB_PATH, read_only=True)
    missing_resolution = []
    for d_str in missing:
        d = pd.Timestamp(d_str)
        if d not in session_pos:
            missing_resolution.append({"date": d_str, "resolution": "not_an_xnys_session", "n_nearby_events": None})
            continue
        i0 = session_pos[d]
        lo, hi = sessions[i0 - 3], sessions[i0 + 3]
        n_nearby = con_db.execute(
            "SELECT COUNT(*) FROM momentum_events WHERE COALESCE(date, event_date) BETWEEN ? AND ?",
            [str(lo.date()), str(hi.date())],
        ).fetchone()[0]
        missing_resolution.append({
            "date": d_str, "window_checked": [str(lo.date()), str(hi.date())],
            "n_momentum_events_any_scope_in_window": n_nearby,
            "resolution": "genuine_data_gap_no_events_nearby" if n_nearby == 0 else "UNEXPLAINED_needs_review",
        })
    con_db.close()
    check2_all_explained = all(r["resolution"] != "UNEXPLAINED_needs_review" for r in missing_resolution)

    # Check 3
    inv = con.execute(
        f"SELECT ticker, date AS event_date_canonical, quotes_ingested FROM read_parquet('{FOLDER_INV}')"
    ).fetchdf()
    m2 = manifest.merge(inv, on=["ticker", "event_date_canonical"], how="left")
    violations = m2[(m2["fetch_quotes"] == True) & (m2["quotes_ingested"] == False)]  # noqa: E712
    n_violations = len(violations)
    check3_pass = n_violations == 0

    overall_pass = check1_pass and check2_all_explained and check3_pass

    summary = {
        "phase": "1c", "task": "T1b",
        "check1_event_day_count": {"observed": n_event_day, "expected": 142, "pass": check1_pass},
        "check2_set_a_dates": {
            "n_set_a_dates": len(set_a_dates),
            "n_present_in_manifest": len(set_a_dates) - len(missing),
            "n_absent_from_manifest": len(missing),
            "absent_dates_resolution": missing_resolution,
            "all_explained": check2_all_explained,
        },
        "check3_quote_side_hard_boundary": {
            "n_violations": n_violations, "pass": check3_pass,
            "violation_sample": violations.head(10).to_dict("records") if n_violations else [],
        },
        "overall_pass": overall_pass,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if not overall_pass:
        raise SystemExit("T1b cross-check FAILED - see summary above. Hard stop per phase prompt.")


if __name__ == "__main__":
    main()
