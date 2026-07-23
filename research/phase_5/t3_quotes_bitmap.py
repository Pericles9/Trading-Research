"""
Phase 5 T3 - quotes-side per-event session bitmap, ALL 20,951 in-scope events.

Cache-reuse path (default): Phase 4 T4's cache
(results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet) already
holds the full-population (ticker, event_date_canonical, mom_2dp,
session_date) result of a single full-table pass over filtered_quotes,
joined to ALL 20,951 in-scope events (t4_quotes_bitmap.py's own docstring:
"joined to ALL 20,951 in-scope events (not just the 386 cohort)"). Reuse
requires (config/phase_5.json's full_table_pass_budget note):
  1. calendar pin identical - config/phase_4.json's session_calendar
     (post-T0b: pandas_market_calendars 5.4.0 / exchange_calendars 4.13.2,
     XNYS, 2019-12-01..2026-01-15) vs config/phase_5.json's (same fields).
  2. OFFSETS identical - [-3..3] both phases.
  3. in-scope population identical - every (ticker, event_date_canonical,
     mom_2dp) key present in the Phase 4 cache must belong to the CURRENT
     in-scope population (fresh all_inscope_events() query, cheap - no
     tick-table scan), and Phase 5 T1 already reconciled in_scope=20,951
     exact against the live view today.
If all three hold, no second full-table pass over filtered_quotes is run
(budget drops to 1, per config). Otherwise this script falls back to a
fresh full-table pass (--table filtered_quotes / --table
filtered_quotes_dev_v3 for dev-tier verification), mirroring T2 exactly.

Usage:
  python -m research.phase_5.t3_quotes_bitmap                  # cache-reuse path (default)
  python -m research.phase_5.t3_quotes_bitmap --no-reuse-cache --table filtered_quotes_dev_v3   # dev-tier fresh-scan verification
  python -m research.phase_5.t3_quotes_bitmap --no-reuse-cache --table filtered_quotes           # full fresh-scan fallback
"""
import argparse
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
PHASE_4_CONFIG = "config/phase_4.json"
PHASE_5_CONFIG = "config/phase_5.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
PHASE_4_CACHE = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"
OUT_PARQUET = "results/phase_5/artifacts/quotes_bitmaps_all.parquet"
OUT_SUMMARY = "results/phase_5/artifacts/quotes_bitmaps_all_summary.json"
OUT_VERIFICATION = "results/phase_5/artifacts/t3_cache_reuse_verification.json"


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
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day
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
    SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp, source_file
    FROM scoped WHERE in_scope
    """
    return con.execute(sql).fetchdf()


def verify_cache_reuse(events, cfg4, cfg5):
    cal4, cal5 = cfg4["session_calendar"], cfg5["session_calendar"]
    calendar_fields_match = (
        cal4["calendar_code"] == cal5["calendar_code"]
        and cal4["derivation_range"] == cal5["derivation_range"]
        and cal4.get("library_version_pinned_by_phase_1c", cal4.get("library_version_pinned")) == "5.4.0"
        and cal5.get("library_version_pinned") == "5.4.0"
    )
    offsets_match = list(range(-3, 4)) == cfg5["offsets"]

    cache = pd.read_parquet(PHASE_4_CACHE, columns=["ticker", "event_date_canonical", "mom_2dp"]).drop_duplicates()
    cache["event_date_canonical"] = pd.to_datetime(cache["event_date_canonical"])
    cache_keys = set(zip(cache["ticker"], cache["event_date_canonical"], cache["mom_2dp"]))

    current_keys = set(zip(events["ticker"], events["event_date_canonical"], events["mom_2dp"]))
    n_cache_keys = len(cache_keys)
    keys_not_in_current = cache_keys - current_keys
    population_match = len(keys_not_in_current) == 0

    result = {
        "calendar_fields_match": calendar_fields_match,
        "offsets_match": offsets_match,
        "n_distinct_events_in_cache": n_cache_keys,
        "n_current_inscope_events": len(current_keys),
        "n_cache_keys_not_in_current_scope": len(keys_not_in_current),
        "population_match": population_match,
        "reuse_authorized": calendar_fields_match and offsets_match and population_match,
    }
    return result, cache_keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="filtered_quotes")
    ap.add_argument("--no-reuse-cache", action="store_true")
    ap.add_argument("--out-parquet", default=OUT_PARQUET)
    ap.add_argument("--out-summary", default=OUT_SUMMARY)
    args = ap.parse_args()

    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]
    with open(PHASE_4_CONFIG) as f:
        cfg4 = json.load(f)
    with open(PHASE_5_CONFIG) as f:
        cfg5 = json.load(f)
    cal_cfg = cfg5["session_calendar"]
    offsets = cfg5["offsets"]

    con = duckdb.connect(DB_PATH, read_only=True)
    events = all_inscope_events(con, prev_close_floor, mom_sanity_cap)
    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    print(f"all in-scope events (lightweight replica): {len(events)}")

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=cal_cfg["derivation_range"]["start"], end_date=cal_cfg["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}
    print(f"XNYS calendar: {mcal.__version__}, {len(xnys_sessions)} sessions in derivation range")

    use_cache = not args.no_reuse_cache
    if use_cache:
        verification, _ = verify_cache_reuse(events, cfg4, cfg5)
        with open(OUT_VERIFICATION, "w") as f:
            json.dump(verification, f, indent=2, default=str)
        print(json.dumps(verification, indent=2))
        if not verification["reuse_authorized"]:
            print("*** cache reuse NOT authorized - falling back to a fresh full-table pass over filtered_quotes ***")
            use_cache = False

    events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()

    if use_cache:
        print(f"reusing Phase 4 cache: {PHASE_4_CACHE} (no filtered_quotes scan this phase)")
        actual = pd.read_parquet(PHASE_4_CACHE)
        actual["event_date_canonical"] = pd.to_datetime(actual["event_date_canonical"])
        table_scanned = None
    else:
        dev_mode = args.table != "filtered_quotes"
        if dev_mode:
            dev_keys = con.execute(f"""
                SELECT DISTINCT ticker, event_date AS event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp
                FROM {args.table}
            """).fetchdf()
            dev_keys["event_date_canonical"] = pd.to_datetime(dev_keys["event_date_canonical"])
            dev_key_set = set(zip(dev_keys["ticker"], dev_keys["event_date_canonical"], dev_keys["mom_2dp"]))
            events = events[[(r.ticker, r.event_date_canonical, r.mom_2dp) in dev_key_set for r in events.itertuples()]].copy()
            events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()
            print(f"dev-mode: restricted to {len(events)} events present in {args.table}")
        print(f"scanning {args.table} (single pass, joined to {len(events)} in-scope events)...")
        actual = con.execute(f"""
            SELECT t.ticker, t.event_date AS event_date_canonical, t.momentum_pct AS mom_2dp,
                   CAST(TO_TIMESTAMP(t.sip_timestamp / 1e9) AS DATE) AS session_date
            FROM {args.table} t
            JOIN events_key e
              ON t.ticker = e.ticker AND t.event_date = e.event_date_canonical
             AND ROUND(t.momentum_pct, 2) = e.mom_2dp
            GROUP BY 1, 2, 3, 4
        """).fetchdf()
        table_scanned = args.table
    con.close()
    actual["mom_2dp"] = actual["mom_2dp"].round(2)
    print(f"actual (ticker,event,session) rows: {len(actual)}")

    actual_by_event = actual.groupby(["ticker", "event_date_canonical", "mom_2dp"])["session_date"].apply(set).to_dict()

    records = []
    for row in events.itertuples():
        ticker, d, mom, source_file = row.ticker, row.event_date_canonical, row.mom_2dp, row.source_file
        key = (ticker, d, mom)
        if d not in session_pos:
            continue
        i0 = session_pos[d]
        expected = {k: xnys_sessions[i0 + k] for k in offsets if 0 <= i0 + k < len(xnys_sessions)}
        actual_set = actual_by_event.get(key, set())
        present = {k: (v in actual_set) for k, v in expected.items()}
        missing_offsets = sorted(k for k, p in present.items() if not p)
        bitmap = "".join("1" if present.get(k, False) else "0" for k in offsets)
        quotes_full_window = len(missing_offsets) == 0 and len(expected) == len(offsets)

        records.append({
            "ticker": ticker, "event_date_canonical": d, "momentum_pct": mom, "source_file": source_file,
            "quotes_bitmap": bitmap, "quotes_missing_offsets": missing_offsets,
            "quotes_n_missing": len(missing_offsets), "quotes_full_window": quotes_full_window,
            "expected_offsets_in_range": len(expected),
        })

    df = pd.DataFrame(records)
    df.to_parquet(args.out_parquet, index=False)

    n_events = len(df)
    n_full_window = int(df["quotes_full_window"].sum())
    n_flagged = n_events - n_full_window
    by_source = df.groupby("source_file")["quotes_full_window"].agg(["sum", "count"]).to_dict(orient="index")

    summary = {
        "phase": "5", "task": "T3", "table_scanned": table_scanned, "used_phase4_cache": use_cache,
        "n_events": n_events, "n_full_window": n_full_window, "n_flagged_not_full_window": n_flagged,
        "by_source_file": {
            k: {"full_window": int(v["sum"]), "not_full_window": int(v["count"] - v["sum"]), "total": int(v["count"])}
            for k, v in by_source.items()
        },
        "bitmap_top10": df["quotes_bitmap"].value_counts().head(10).to_dict(),
        "source": "research/phase_5/t3_quotes_bitmap.py:main",
        "artifact": args.out_parquet,
    }
    with open(args.out_summary, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
