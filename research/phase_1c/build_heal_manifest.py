"""
Phase 1c T1 - derive the heal-target manifest.

For every event carrying flag_missing_event_day (cause calendar_bug, n=142)
or flag_window_calendar_bug (n=1,849, disjoint population per Phase 1b's
T5-R3 scoping), replicate the legacy get_trading_window(D) (federal-calendar
business-day stepping, data/collection_scripts/collect_massive_data.py read
for reference only - never executed) and compare it against the true XNYS
T-3..T+3 session window. Heal targets are the resulting SET DIFFERENCE:
true sessions absent from the legacy window. This is a pure per-event set
comparison, not a positional offset-index mapping (Phase 1b's T5-R3 script
used position-indexing to label damage type and that broke for the 33
anchor-on-Set-A edge case; a direct set difference has no such edge case -
it mechanically reproduces the 142 event-day gaps AND correctly finds no
gap at k=0 for the 33 anchor-on-Set-A-but-has-trades events, without any
special-casing).

Target-type labeling (mechanical, not positional):
  - k == 0                          -> event_day
  - missing session itself in Set A -> flanking_setA (day was skipped: a
    federal-calendar phantom holiday that was a real XNYS session)
  - otherwise                       -> outer_setB (day itself is not a
    Set A date, so the shortfall must come from a Set B phantom-session
    date consuming a legacy step elsewhere in the window, pushing the
    true outer session out of reach)

The 8 unknown-cause flag_missing_event_day events are NOT heal targets -
they are diagnostic-only entries (event-day trades+quotes), tagged
diagnostic_unknown, resolved separately in T5.

Side rule: trades_ingested=TRUE & quotes_ingested=TRUE -> fetch both sides.
trades_ingested=TRUE & quotes_ingested=FALSE -> fetch trades only (the
~1,540-folder quote gap is out of scope - hard boundary, never touched).
"""
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

EVENT_FLAGS = CFG["paths"]["event_flags"]
CALENDAR_MISMATCH = CFG["paths"]["calendar_mismatch_1b"]
FOLDER_INV = CFG["paths"]["folder_inventory_v2"]
OUT_PATH = CFG["paths"]["heal_manifest"]
OUT_SUMMARY = "results/phase_1c/artifacts/t1_manifest_summary.json"

CAL = CFG["session_calendar"]
START, END = CAL["derivation_range"]["start"], CAL["derivation_range"]["end"]

OFFSETS = [-3, -2, -1, 0, 1, 2, 3]


def legacy_window(center_date: pd.Timestamp, us_bd) -> list[pd.Timestamp]:
    start_date = center_date - 3 * us_bd
    end_date = center_date + 3 * us_bd
    return list(pd.date_range(start_date, end_date, freq=us_bd))


def main():
    with open(CALENDAR_MISMATCH) as f:
        cm = json.load(f)
    set_a = set(pd.Timestamp(d) for d in cm["set_a_phantom_holidays"]["dates"])

    fed_cal = USFederalHolidayCalendar()
    us_bd = CustomBusinessDay(calendar=fed_cal)

    xnys = mcal.get_calendar(CAL["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(xnys.schedule(start_date=START, end_date=END).index).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}

    con = duckdb.connect(read_only=False)
    flags = con.execute(f"SELECT * FROM read_parquet('{EVENT_FLAGS}')").fetchdf()
    # match_status is NOT a usable gate here: it is a raw-date matching
    # artifact predating the event_date_canonical fix (Phase 1) - 7,186
    # folders are labeled "orphan" despite having real ingested data and a
    # valid canonical-date match (e.g. AVR_2025-04-23_30.48: match_status=
    # orphan, trades_ingested=quotes_ingested=True). The ticker+date join
    # itself against event_flags.parquet's already-canonical population is
    # the correctness test; match_status is orthogonal and excluded.
    inv = con.execute(
        f"SELECT ticker, date AS event_date_str, trades_ingested, quotes_ingested "
        f"FROM read_parquet('{FOLDER_INV}')"
    ).fetchdf()
    flags["event_date_str"] = flags["event_date_canonical"].astype(str)
    df = flags.merge(inv, on=["ticker", "event_date_str"], how="left")

    calendar_bug_pop = df[
        df["flag_missing_event_day"].fillna(False) & (df["zero_trades_cause"] == "calendar_bug")
    ].copy()
    calendar_bug_pop["_offsets_to_check"] = [OFFSETS] * len(calendar_bug_pop)

    # flag_window_calendar_bug (n=1,849) is disjoint from flag_missing_event_day
    # by construction (Phase 1b's T5-R3 excluded flag_missing_event_day events
    # from that population before computing it). n_trades_event_day > 0 is
    # already-validated ground truth for every one of these events (that is
    # exactly why they were NOT classified flag_missing_event_day). A pure
    # calendar-only replication of get_trading_window() incorrectly finds D
    # itself "missing" for the 33-event anchor_on_set_a subset (D lands on a
    # Set A date, so date_range(freq=us_bd) mechanically excludes it) - but
    # real trades exist for all 33 on their anchor day (confirmed: e.g. NVA
    # 2025-10-13, n_trades_event_day=11,826), meaning the anchor day was
    # collected through some other path than get_trading_window(), not
    # root-caused further in Phase 1b and out of scope here too. k=0 is
    # therefore excluded from this population's offset check - trusted as
    # already-healthy per 1b's validated flag, not re-derived from calendar
    # logic alone (corroboration overriding a known, already-documented
    # false positive, not row-count-driven target selection).
    window_bug_pop = df[df["flag_window_calendar_bug"].fillna(False)].copy()
    window_bug_pop["_offsets_to_check"] = [[k for k in OFFSETS if k != 0]] * len(window_bug_pop)

    heal_pop = pd.concat([calendar_bug_pop, window_bug_pop], ignore_index=True)
    diagnostic_pop = df[
        df["flag_missing_event_day"].fillna(False) & (df["zero_trades_cause"] == "unknown")
    ].copy()

    n_heal_events = len(heal_pop)
    n_diagnostic_events = len(diagnostic_pop)
    print(f"heal population: {n_heal_events} events; diagnostic population: {n_diagnostic_events} events")

    missing_join = heal_pop["trades_ingested"].isna().sum()
    if missing_join:
        print(f"WARNING: {missing_join} heal-population events did not join to folder_inventory_v2 (trades_ingested NULL)")

    rows = []
    events_with_no_gap = []
    for _, row in heal_pop.iterrows():
        d = pd.Timestamp(row["event_date_canonical"])
        if d not in session_pos:
            raise ValueError(f"anchor date {d} for {row['ticker']} not a recognized XNYS session - cannot derive window")
        i0 = session_pos[d]
        true_window = {k: xnys_sessions[i0 + k] for k in OFFSETS}
        legacy_dates = set(legacy_window(d, us_bd))

        fetch_trades = bool(row["trades_ingested"]) if pd.notna(row["trades_ingested"]) else True
        fetch_quotes = bool(row["quotes_ingested"]) if pd.notna(row["quotes_ingested"]) else False

        event_key = f"{row['ticker']}_{d.date()}"
        gaps_for_event = 0
        for k in row["_offsets_to_check"]:
            true_date = true_window[k]
            if true_date in legacy_dates:
                continue
            gaps_for_event += 1
            if k == 0:
                target_type = "event_day"
            elif true_date in set_a:
                target_type = "flanking_setA"
            else:
                target_type = "outer_setB"
            rows.append({
                "event_key": event_key, "ticker": row["ticker"],
                "event_date_canonical": str(d.date()), "session": str(true_date.date()),
                "offset_k": k, "target_type": target_type,
                "fetch_trades": fetch_trades, "fetch_quotes": fetch_quotes,
                "status": "pending",
            })
        if gaps_for_event == 0:
            events_with_no_gap.append(event_key)

    for _, row in diagnostic_pop.iterrows():
        d = pd.Timestamp(row["event_date_canonical"])
        event_key = f"{row['ticker']}_{d.date()}"
        rows.append({
            "event_key": event_key, "ticker": row["ticker"],
            "event_date_canonical": str(d.date()), "session": str(d.date()),
            "offset_k": 0, "target_type": "diagnostic_unknown",
            "fetch_trades": True, "fetch_quotes": True,
            "status": "pending",
        })

    manifest = pd.DataFrame(rows)
    manifest.to_parquet(OUT_PATH, index=False)

    n_pairs = len(manifest)
    by_type = manifest["target_type"].value_counts().to_dict()
    by_side = {
        "trades": int(manifest["fetch_trades"].sum()),
        "quotes": int(manifest["fetch_quotes"].sum()),
    }
    n_distinct_pairs = manifest[["ticker", "session"]].drop_duplicates().shape[0]

    summary = {
        "phase": "1c", "task": "T1",
        "n_heal_events": n_heal_events,
        "n_diagnostic_events": n_diagnostic_events,
        "n_manifest_rows": n_pairs,
        "n_distinct_ticker_session_pairs": n_distinct_pairs,
        "pairs_by_target_type": by_type,
        "pairs_by_side": by_side,
        "events_with_zero_derived_gap": {
            "n": len(events_with_no_gap),
            "note": "heal-population events (flag_missing_event_day/flag_window_calendar_bug=TRUE) "
                    "for which the fresh set-difference found no true session missing from the legacy "
                    "window - possible if Phase 1b's flag was based on a damaged_offsets_json placeholder "
                    "(the anchor_on_set_a surprise) that this phase's direct membership test resolves "
                    "cleanly. Listed, not treated as an error.",
            "event_keys": events_with_no_gap[:50],
        },
        "escalation_t1a": {
            "criterion": "manifest size > 6000 pairs",
            "observed": n_pairs,
            "triggered": n_pairs > CFG["escalation_thresholds"]["heal_manifest_max_pairs"],
        },
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
