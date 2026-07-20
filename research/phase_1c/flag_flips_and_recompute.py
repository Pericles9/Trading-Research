"""
Phase 1c T7 - flag flips and universe recompute.

Every heal-population event has exactly one gap (T1's derivation: 1,958
pairs across 1,958 gap-carrying events, 1:1). Per event:
  - flag_missing_event_day (the 142 calendar_bug + 8 collection_failure
    event-day events): cleared iff that event's event_day pair was
    successfully ingested (repair_ledger verification_status='ok' for
    every side the event required - trades always, quotes iff
    quotes_ingested was TRUE for that event pre-heal).
  - flag_window_calendar_bug (the 1,849 population): cleared iff EITHER
    (a) the event's single flanking/outer gap was successfully healed, or
    (b) the event needed no gap at all (the 33 anchor_on_set_a events -
    Phase 1c's direct set-difference re-derivation proved these already
    have complete T-3..T+3 data; Phase 1b's flag was a defensive
    placeholder for a case it could not offset-map, not evidence of real
    damage - see research/phase_1c/build_heal_manifest.py). Kept TRUE
    where the gap's fetch failed (part of T4's 12 failures) or fetched
    but failed T6 verification.
  - repaired_1c = TRUE only where an actual fetch+ingest happened and
    verified ok (the 33 anchor_on_set_a events get their flag cleared via
    reclassification, not repaired_1c - nothing was fetched for them).
  - scope_pending_repair: resolved (cleared) wherever flag_missing_event_day
    clears.

Writes the updated event_flags.parquet (same schema plus repaired_1c),
updates src/data/canonical.py to select repaired_1c and use the refreshed
flags (already automatic - the view reads event_flags.parquet directly),
and recomputes in_scope by re-running the view at stage="t6".
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data import canonical  # noqa: E402

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

EVENT_FLAGS = CFG["paths"]["event_flags"]
MANIFEST = CFG["paths"]["heal_manifest"]
LEDGER = CFG["paths"]["repair_ledger"]
DB_PATH = CFG["paths"]["momentum_events_db"]
OUT_SUMMARY = "results/phase_1c/artifacts/t7_recompute_summary.json"
OUT_WATERFALL = "results/phase_1c/artifacts/waterfall_v2.json"

ANCHOR_ON_SET_A_NOTE = "anchor_on_set_a_reclassified_no_damage_found"


def main():
    con = duckdb.connect(read_only=False)
    flags = con.execute(f"SELECT * FROM read_parquet('{EVENT_FLAGS}')").fetchdf()
    manifest = pd.read_parquet(MANIFEST)
    ledger = pd.read_parquet(LEDGER)

    flags["event_key"] = flags["ticker"] + "_" + flags["event_date_canonical"].astype(str)

    ok_ledger = ledger[ledger["verification_status"] == "ok"]
    ok_sides_by_event = ok_ledger.groupby("event_key")["side"].apply(set).to_dict()

    heal_pop_keys = set(manifest[manifest["target_type"] != "diagnostic_unknown"]["event_key"])
    diag_keys = set(manifest[manifest["target_type"] == "diagnostic_unknown"]["event_key"])

    # Events whose flag_window_calendar_bug=TRUE but carry no manifest row at
    # all (the 33 anchor_on_set_a) - reclassified via direct evidence, not repaired.
    manifest_event_keys = set(manifest["event_key"])
    flagged_window_bug = flags[flags["flag_window_calendar_bug"].fillna(False)]
    anchor_reclassified_keys = set(flagged_window_bug["event_key"]) - manifest_event_keys

    def event_required_sides(event_key):
        rows = manifest[manifest["event_key"] == event_key]
        sides = set()
        if rows["fetch_trades"].any():
            sides.add("trades")
        if rows["fetch_quotes"].any():
            sides.add("quotes")
        return sides

    n_missing_event_day_cleared = 0
    n_window_bug_cleared_repaired = 0
    n_window_bug_cleared_reclassified = 0
    n_still_flagged = 0
    repaired_1c_keys = set()

    new_flag_missing = []
    new_flag_window = []
    new_scope_pending = []
    new_repaired_1c = []

    for _, row in flags.iterrows():
        ek = row["event_key"]
        fmed, fwcb, spr = row["flag_missing_event_day"], row["flag_window_calendar_bug"], row["scope_pending_repair"]
        repaired = False

        if bool(fmed) and ek in (heal_pop_keys | diag_keys):
            required = event_required_sides(ek)
            achieved = ok_sides_by_event.get(ek, set())
            if required and required.issubset(achieved):
                fmed = False
                spr = False
                repaired = True
                n_missing_event_day_cleared += 1
            else:
                n_still_flagged += 1

        if bool(fwcb):
            if ek in anchor_reclassified_keys:
                fwcb = False
                n_window_bug_cleared_reclassified += 1
            elif ek in heal_pop_keys:
                required = event_required_sides(ek)
                achieved = ok_sides_by_event.get(ek, set())
                if required and required.issubset(achieved):
                    fwcb = False
                    repaired = True
                    n_window_bug_cleared_repaired += 1
                else:
                    n_still_flagged += 1

        if repaired:
            repaired_1c_keys.add(ek)

        new_flag_missing.append(fmed)
        new_flag_window.append(fwcb)
        new_scope_pending.append(spr)
        new_repaired_1c.append(ek in repaired_1c_keys)

    flags["flag_missing_event_day"] = new_flag_missing
    flags["flag_window_calendar_bug"] = new_flag_window
    flags["scope_pending_repair"] = new_scope_pending
    flags["repaired_1c"] = new_repaired_1c
    flags = flags.drop(columns=["event_key"])
    flags.to_parquet(EVENT_FLAGS, index=False)

    # Recompute in_scope via the canonical view (t6 stage - final formula).
    # repaired_1c is now a real view column (src/data/canonical.py, T7) fed
    # directly from the just-written event_flags.parquet - query it rather
    # than trust the Python-side set, as an independent cross-check.
    con_db = duckdb.connect(database=DB_PATH, read_only=False)
    canonical.create_view(con_db, stage="t6")
    prior_in_scope = 20802
    new_in_scope = con_db.execute("SELECT COUNT(*) FROM momentum_events_canonical WHERE in_scope").fetchone()[0]
    still_pending_missing_day = con_db.execute(
        "SELECT COUNT(*) FROM momentum_events_canonical WHERE flag_missing_event_day"
    ).fetchone()[0]
    still_window_bug = con_db.execute(
        "SELECT COUNT(*) FROM momentum_events_canonical WHERE flag_window_calendar_bug"
    ).fetchone()[0]
    n_repaired_1c_view = con_db.execute(
        "SELECT COUNT(*) FROM momentum_events_canonical WHERE repaired_1c"
    ).fetchone()[0]
    con_db.close()

    n_repaired_1c_python = len(repaired_1c_keys)
    cross_check_pass = n_repaired_1c_view == n_repaired_1c_python

    delta = new_in_scope - prior_in_scope
    # confirmed_zero exclusions: none this phase (T5 found 0/8 confirmed-zero)
    n_confirmed_zero_exclusions = 0
    arithmetic_reconciles = delta == (n_missing_event_day_cleared - n_confirmed_zero_exclusions)

    summary = {
        "phase": "1c", "task": "T7",
        "flag_missing_event_day_cleared": n_missing_event_day_cleared,
        "flag_missing_event_day_still_flagged": still_pending_missing_day,
        "flag_window_calendar_bug_cleared_via_repair": n_window_bug_cleared_repaired,
        "flag_window_calendar_bug_cleared_via_reclassification": n_window_bug_cleared_reclassified,
        "flag_window_calendar_bug_still_flagged": still_window_bug,
        "n_repaired_1c_python_side": n_repaired_1c_python,
        "n_repaired_1c_view_side": n_repaired_1c_view,
        "repaired_1c_cross_check_pass": cross_check_pass,
        "prior_in_scope": prior_in_scope,
        "new_in_scope": new_in_scope,
        "delta": delta,
        "n_confirmed_zero_exclusions": n_confirmed_zero_exclusions,
        "arithmetic": f"{prior_in_scope} + {n_missing_event_day_cleared} restored - {n_confirmed_zero_exclusions} confirmed-zero = {prior_in_scope + n_missing_event_day_cleared - n_confirmed_zero_exclusions}",
        "arithmetic_reconciles_against_ledger": arithmetic_reconciles,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not cross_check_pass or not arithmetic_reconciles:
        raise SystemExit("T7: universe arithmetic failed to reconcile - hard stop per phase prompt.")


if __name__ == "__main__":
    main()
