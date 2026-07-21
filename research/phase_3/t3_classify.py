"""
Phase 3 T3 - classify the 287 pre-2025 event_day_only events.

Read-only. Cohort membership comes directly from
results/phase_2/artifacts/coverage_class.parquet (not re-derived from raw
coverage logic, per prompt instruction). flag_window_calendar_bug and
repaired_1c come from results/phase_1b/artifacts/event_flags.parquet -
the same source the canonical view itself joins, read directly to avoid
re-paying the live view's internal trades_ingested/quotes_ingested
DISTINCT-scan cost on every query (T1/T2 already queried the live view
directly per their explicit instructions; T3 has no such requirement).

One full-table-scan pass over filtered_trades, joined to ALL 20,951
in-scope events (not just the 287 cohort or just file1), because T3a
requires each cohort ticker's last-seen session date across ALL of that
ticker's own in-scope event windows - which may include file2 (2025)
events for tickers that also had a 2025 event. This single pass also
yields the file1-population global min/max session date needed for the
archive_edge rule.

Classification precedence (fixed, do not adjust in response to results):
  1. calendar_residue  - flag_window_calendar_bug OR repaired_1c
  2. archive_edge       - any of the 7 expected sessions outside the
                          observed file1 filtered_trades session-date range
  3. forward_missing    - all missing offsets >= +1
  4. backward_missing   - all missing offsets <= -1
  5. both_sides         - missing offsets on both sides of T=0
  6. unclassified        - none of the above (should be empty by construction)
"""
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
PHASE_3_CONFIG = "config/phase_3.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
COVERAGE_CLASS_PARQUET = "results/phase_2/artifacts/coverage_class.parquet"
OUT_PARQUET = "results/phase_3/artifacts/classification.parquet"
OUT_SUMMARY = "results/phase_3/artifacts/classification_summary.json"

OFFSETS = [-3, -2, -1, 0, 1, 2, 3]


def all_inscope_events(con, prev_close_floor, mom_sanity_cap):
    sql = f"""
    WITH canonical AS (
        SELECT
            me.ticker,
            COALESCE(me.date, me.event_date) AS event_date_canonical,
            me.momentum_pct,
            CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
            ic.class AS instrument_class,
            (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
            ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day,
            COALESCE(ef.flag_window_calendar_bug, FALSE) AS flag_window_calendar_bug,
            COALESCE(ef.repaired_1c, FALSE) AS repaired_1c
        FROM momentum_events me
        LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
        LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    ),
    scoped AS (
        SELECT *,
            (instrument_class IN ('common', 'common_adr')
             AND NOT flag_bad_denominator
             AND NOT COALESCE(flag_trades_mom_outlier, FALSE)
             AND NOT flag_missing_event_day) AS in_scope
        FROM canonical
    )
    SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp, source_file,
           flag_window_calendar_bug, repaired_1c
    FROM scoped WHERE in_scope
    """
    return con.execute(sql).fetchdf()


def main():
    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

    with open(PHASE_3_CONFIG) as f:
        cfg3 = json.load(f)
    cal_cfg = cfg3["session_calendar"]

    con = duckdb.connect(DB_PATH, read_only=True)
    events = all_inscope_events(con, prev_close_floor, mom_sanity_cap)
    print(f"all in-scope events (lightweight replica): {len(events)}")

    cc = pd.read_parquet(COVERAGE_CLASS_PARQUET)
    cc["event_date_canonical"] = pd.to_datetime(cc["event_date_canonical"])
    cc["mom_2dp"] = cc["momentum_pct"].round(2)
    cohort = cc[(cc["source_file"] == "file1") & (cc["coverage_class"] == "event_day_only")].copy()
    n_cohort = len(cohort)
    print(f"trades cohort (file1, event_day_only) from coverage_class.parquet: {n_cohort}")

    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=cal_cfg["derivation_range"]["start"], end_date=cal_cfg["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}

    print("scanning filtered_trades (single pass, joined to ALL 20,951 in-scope events)...")
    actual = con.execute("""
        SELECT ft.ticker, ft.event_date AS event_date_canonical, ft.momentum_pct AS mom_2dp,
               CAST(TO_TIMESTAMP(ft.sip_timestamp / 1e9) AS DATE) AS session_date
        FROM filtered_trades ft
        JOIN events_key e
          ON ft.ticker = e.ticker AND ft.event_date = e.event_date_canonical
         AND ROUND(ft.momentum_pct, 2) = e.mom_2dp
        GROUP BY 1, 2, 3, 4
    """).fetchdf()
    con.close()
    actual["mom_2dp"] = actual["mom_2dp"].round(2)
    print(f"actual (ticker,event,session) rows: {len(actual)}")

    # --- global file1 observed session-date range (archive_edge rule) ---
    events_file1_keys = set(zip(events.loc[events["source_file"] == "file1", "ticker"],
                                 events.loc[events["source_file"] == "file1", "event_date_canonical"],
                                 events.loc[events["source_file"] == "file1", "mom_2dp"]))
    actual_key = list(zip(actual["ticker"], actual["event_date_canonical"], actual["mom_2dp"]))
    actual["is_file1"] = [k in events_file1_keys for k in actual_key]
    file1_min = actual.loc[actual["is_file1"], "session_date"].min()
    file1_max = actual.loc[actual["is_file1"], "session_date"].max()
    print(f"file1 observed session-date range: {file1_min.date()} .. {file1_max.date()}")

    # --- per-ticker last-seen / first-seen session date across ALL that ticker's in-scope events (T3a, A1-T4) ---
    ticker_max_date = actual.groupby("ticker")["session_date"].max()
    ticker_min_date = actual.groupby("ticker")["session_date"].min()

    # --- per-cohort-event actual session-date set ---
    actual_by_event = actual.groupby(["ticker", "event_date_canonical", "mom_2dp"])["session_date"].apply(set).to_dict()

    records = []
    for _, row in cohort.iterrows():
        ticker, d, mom = row["ticker"], row["event_date_canonical"], row["mom_2dp"]
        key = (ticker, d, mom)
        if d not in session_pos:
            continue  # guard; should not happen for in-scope events
        i0 = session_pos[d]
        expected = {k: xnys_sessions[i0 + k] for k in OFFSETS if 0 <= i0 + k < len(xnys_sessions)}
        actual_set = actual_by_event.get(key, set())
        present = {k: (v in actual_set) for k, v in expected.items()}
        missing_offsets = sorted(k for k, p in present.items() if not p)
        bitmap = "".join("1" if present.get(k, False) else "0" for k in OFFSETS)

        flag_cal_bug = bool(events.loc[(events["ticker"] == ticker) & (events["event_date_canonical"] == d) & (events["mom_2dp"] == mom), "flag_window_calendar_bug"].iloc[0]) if len(events.loc[(events["ticker"] == ticker) & (events["event_date_canonical"] == d) & (events["mom_2dp"] == mom)]) else False
        repaired = bool(events.loc[(events["ticker"] == ticker) & (events["event_date_canonical"] == d) & (events["mom_2dp"] == mom), "repaired_1c"].iloc[0]) if len(events.loc[(events["ticker"] == ticker) & (events["event_date_canonical"] == d) & (events["mom_2dp"] == mom)]) else False

        archive_edge = any(v < file1_min or v > file1_max for v in expected.values())

        if flag_cal_bug or repaired:
            label = "calendar_residue"
        elif archive_edge:
            label = "archive_edge"
        elif missing_offsets and all(k >= 1 for k in missing_offsets):
            label = "forward_missing"
        elif missing_offsets and all(k <= -1 for k in missing_offsets):
            label = "backward_missing"
        elif missing_offsets:
            label = "both_sides"
        else:
            label = "unclassified"  # structurally: no missing offsets, but coverage_class said event_day_only

        records.append({
            "ticker": ticker, "event_day": d, "momentum_pct": mom,
            "bitmap": bitmap, "missing_offsets": missing_offsets, "label": label,
            "flag_window_calendar_bug": flag_cal_bug, "repaired_1c": repaired, "archive_edge": archive_edge,
            "expected_t_minus_3": expected.get(-3),
        })

    df = pd.DataFrame(records)

    # --- T3a: forward_missing weak within-archive delisting signature ---
    fwd = df[df["label"] == "forward_missing"].copy()
    fwd["ticker_last_seen"] = fwd["ticker"].map(ticker_max_date)
    fwd["is_last_seen_signature"] = fwd["event_day"] == fwd["ticker_last_seen"]
    n_fwd = len(fwd)
    n_signature = int(fwd["is_last_seen_signature"].sum())
    df["is_last_seen_signature"] = False
    if len(fwd):
        df.loc[df["label"] == "forward_missing", "is_last_seen_signature"] = fwd.set_index(fwd.index)["is_last_seen_signature"]

    # --- A1-T4: backward_missing weak within-archive listing signature ---
    bwd = df[df["label"] == "backward_missing"].copy()
    bwd["ticker_first_seen"] = bwd["ticker"].map(ticker_min_date)
    bwd["weak_listing_signature"] = bwd["ticker_first_seen"] > bwd["expected_t_minus_3"]
    n_bwd = len(bwd)
    n_listing_signature = int(bwd["weak_listing_signature"].sum())
    df["weak_listing_signature"] = False
    if len(bwd):
        df.loc[df["label"] == "backward_missing", "weak_listing_signature"] = bwd.set_index(bwd.index)["weak_listing_signature"]

    df.to_parquet(OUT_PARQUET, index=False)

    # --- T3b: cross-tabs ---
    label_counts = df["label"].value_counts().to_dict()
    # NOTE: groupby("label")["bitmap"].apply(lambda s: ...to_dict()).to_dict() silently
    # flattens into a MultiIndex Series ((label, bitmap) -> count) in this pandas version,
    # producing tuple dict keys that json.dump cannot serialize - looped explicitly instead.
    bitmap_by_label = {label: sub["bitmap"].value_counts().head(3).to_dict() for label, sub in df.groupby("label")}
    df["year"] = df["event_day"].dt.year
    label_by_year = df.groupby(["year", "label"]).size().unstack(fill_value=0).to_dict(orient="index")

    # --- T3c: cohort overlap (trades 287 vs quotes 386) ---
    quotes_cohort = cc[(cc["source_file"] == "file1") & (~cc["quotes_full_window"])].copy()
    trades_keys = set(zip(cohort["ticker"], cohort["event_date_canonical"], cohort["mom_2dp"]))
    quotes_cohort["event_date_canonical"] = pd.to_datetime(quotes_cohort["event_date_canonical"])
    quotes_cohort["mom_2dp"] = quotes_cohort["momentum_pct"].round(2)
    quotes_keys = set(zip(quotes_cohort["ticker"], quotes_cohort["event_date_canonical"], quotes_cohort["mom_2dp"]))
    n_both = len(trades_keys & quotes_keys)
    n_trades_only = len(trades_keys - quotes_keys)
    n_quotes_only = len(quotes_keys - trades_keys)

    n_unclassified = label_counts.get("unclassified", 0)
    unclassified_pct = n_unclassified / n_cohort if n_cohort else 0.0

    summary = {
        "phase": "3", "task": "T3",
        "n_cohort": n_cohort,
        "file1_observed_session_date_range": {"min": str(file1_min.date()), "max": str(file1_max.date())},
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "label_counts_pct_of_cohort": {str(k): round(100 * int(v) / n_cohort, 2) for k, v in label_counts.items()},
        "bitmap_top3_by_label": bitmap_by_label,
        "label_by_year": {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in label_by_year.items()},
        "t3a_forward_missing_signature": {
            "n_forward_missing": n_fwd,
            "n_is_last_seen_signature": n_signature,
            "note": "weak within-archive delisting signature - absence of a ticker's data after an event is not proof of delisting; it may simply mean no later event for that ticker. Within-archive signature only, not externally confirmed.",
        },
        "a1t4_backward_missing_signature": {
            "n_backward_missing": n_bwd,
            "n_weak_listing_signature": n_listing_signature,
            "note": "weak within-archive listing signature - absence of pre-event data is consistent with late listing but is not proof; within an event-conditional archive it is indistinguishable from flank-collection loss without external reference data, which is out of scope. PLBY_2021-02-16 is the illustrative exemplar (SPAC merger with MCAC consummated 2021-02-10; began trading as PLBY on Nasdaq 2021-02-11; event day 2021-02-16 -> T-3 predates the ticker's existence) - not a per-event external lookup performed on the cohort.",
        },
        "t3c_cohort_overlap": {
            "n_trades_cohort": n_cohort,
            "n_quotes_cohort": int(len(quotes_cohort)),
            "n_both": n_both,
            "n_trades_only": n_trades_only,
            "n_quotes_only": n_quotes_only,
        },
        "escalation_check": {
            "condition": "unclassified label count > 30% of 287",
            "threshold_pct": 30.0,
            "observed_n": n_unclassified,
            "observed_pct": round(100 * unclassified_pct, 2),
            "triggered": unclassified_pct > 0.30,
        },
        "source": "research/phase_3/t3_classify.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if n_unclassified > 0:
        print(f"\n*** {n_unclassified} unclassified events - see classification.parquet for bitmap details ***")


if __name__ == "__main__":
    main()
