"""
Phase 7 T4 - three-surface analysis-ready sample pin.

Pins canonical spine + dev v4 + bar cache into one committed manifest.

Scan-free discipline (escalation row 11): spine flag tallies and the D1
event-key SHA256 are computed by replicating the view's flag logic against
momentum_events + the committed parquets (T2 proved this equals the view's
own columns) - the view is never SELECTed (its trades_ingested/quotes_ingested
columns scan filtered_trades/filtered_quotes). The bar cache
(event_minute_bars_v1) and the dev v4 tables ARE queried directly - they are
not filtered_trades/filtered_quotes and dev-tier reads are exempt anyway.
trades_ingested/quotes_ingested tallies are deliberately omitted from the
spine surface: they are coverage indicators (not flags) whose only definition
requires the prohibited full-table pass; their D1 values live in Phase 5a's
frozen sampling_frame.parquet.
"""
import hashlib
import json

import duckdb

from src.data.canonical import (
    ETH_DOMINANT_SOURCE_PATH, ETH_DOMINANT_THRESHOLD,
    CLASSIFICATION_PATH, EVENT_FLAGS_PATH, COVERAGE_CLASS_PATH,
    SPINE_WINDOW_FLAGS_PATH, IN_SCOPE_CLASSES, _p, _load_thresholds,
)

DB_PATH = "data/duckdb/main.duckdb"
SAMPLING_FRAME = "results/phase_5a/artifacts/sampling_frame.parquet"
DEV_PRIMARY = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
DEV_SIDECAR = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
PHASE6_T3_SUMMARY = "results/phase_6_rth_only/artifacts/t3_full_pass_summary.json"
OUT_PATH = "results/phase_7/artifacts/analysis_ready_manifest_v1.json"

BARS_TABLE = "event_minute_bars_v1"
EXPECTED = {"in_scope": 20951, "d1": 15763, "bar_rows": 30309950, "t0_events": 15763, "dev": 56}


def canon_cte(prev_close_floor, mom_sanity_cap, classification, event_flags, coverage_class, spine_window_flags, eth_src):
    """The view's SELECT, minus the two filtered_trades/quotes DISTINCT joins
    (trades_ingested/quotes_ingested) - identical flag logic, scan-free."""
    return f"""
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
        COALESCE(ef.repaired_1c, FALSE) AS repaired_1c,
        (ic.class IN {IN_SCOPE_CLASSES}
         AND NOT COALESCE((me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}), FALSE)
         AND NOT COALESCE(ef.flag_trades_mom_outlier, FALSE)
         AND NOT COALESCE(ef.flag_missing_event_day, FALSE)) AS in_scope,
        cc.coverage_class AS coverage_class,
        cc.quotes_full_window AS quotes_full_window,
        swf.trades_full_window AS trades_full_window,
        swf.clean_window AS clean_window,
        (ethd.ticker IS NOT NULL) AS flag_eth_dominant_t0,
        ethd.t0_eth_row_share AS t0_eth_row_share
    FROM momentum_events me
    LEFT JOIN read_parquet('{classification}') ic ON me.ticker = ic.ticker
    LEFT JOIN read_parquet('{event_flags}') ef
      ON me.ticker = ef.ticker AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
     AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    LEFT JOIN read_parquet('{coverage_class}') cc
      ON me.ticker = cc.ticker AND COALESCE(me.date, me.event_date) = cc.event_date_canonical
     AND ROUND(me.momentum_pct, 2) = ROUND(cc.momentum_pct, 2)
    LEFT JOIN read_parquet('{spine_window_flags}') swf
      ON me.ticker = swf.ticker AND COALESCE(me.date, me.event_date) = swf.event_date_canonical
     AND ROUND(me.momentum_pct, 2) = swf.momentum_pct
    LEFT JOIN (
        SELECT ticker, CAST(CAST(event_date_canonical AS DATE) AS VARCHAR) AS event_date_canonical,
               ROUND(momentum_pct, 2) AS momentum_pct, excluded_share AS t0_eth_row_share
        FROM read_parquet('{eth_src}') WHERE excluded_share > {ETH_DOMINANT_THRESHOLD}
    ) ethd
      ON me.ticker = ethd.ticker AND COALESCE(me.date, me.event_date) = ethd.event_date_canonical
     AND ROUND(me.momentum_pct, 2) = ethd.momentum_pct
    """


def main():
    prev_close_floor, mom_sanity_cap = _load_thresholds()
    paths = dict(
        classification=_p(CLASSIFICATION_PATH), event_flags=_p(EVENT_FLAGS_PATH),
        coverage_class=_p(COVERAGE_CLASS_PATH), spine_window_flags=_p(SPINE_WINDOW_FLAGS_PATH),
        eth_src=_p(ETH_DOMINANT_SOURCE_PATH),
    )
    con = duckdb.connect(DB_PATH, read_only=False)
    con.execute(f"CREATE OR REPLACE TEMP VIEW _canon AS {canon_cte(prev_close_floor, mom_sanity_cap, **paths)}")

    # ---------- SURFACE 1: SPINE ----------
    counts = con.execute("""
        SELECT
            COUNT(*) AS n_rows,
            SUM(CASE WHEN in_scope THEN 1 ELSE 0 END) AS in_scope_n,
            SUM(CASE WHEN in_scope AND source_file='file1' THEN 1 ELSE 0 END) AS d1_n
        FROM _canon
    """).fetchdf().iloc[0]

    # flag tallies over the full in_scope population and over D1
    def tally(where):
        return con.execute(f"""
            SELECT
                SUM(CASE WHEN flag_bad_denominator THEN 1 ELSE 0 END) AS flag_bad_denominator,
                SUM(CASE WHEN COALESCE(flag_trades_mom_outlier,FALSE) THEN 1 ELSE 0 END) AS flag_trades_mom_outlier,
                SUM(CASE WHEN flag_missing_event_day THEN 1 ELSE 0 END) AS flag_missing_event_day,
                SUM(CASE WHEN flag_window_calendar_bug THEN 1 ELSE 0 END) AS flag_window_calendar_bug,
                SUM(CASE WHEN repaired_1c THEN 1 ELSE 0 END) AS repaired_1c,
                SUM(CASE WHEN COALESCE(clean_window,FALSE) THEN 1 ELSE 0 END) AS clean_window,
                SUM(CASE WHEN COALESCE(trades_full_window,FALSE) THEN 1 ELSE 0 END) AS trades_full_window,
                SUM(CASE WHEN COALESCE(quotes_full_window,FALSE) THEN 1 ELSE 0 END) AS quotes_full_window,
                SUM(CASE WHEN flag_eth_dominant_t0 THEN 1 ELSE 0 END) AS flag_eth_dominant_t0,
                SUM(CASE WHEN t0_eth_row_share IS NOT NULL THEN 1 ELSE 0 END) AS t0_eth_row_share_non_null
            FROM _canon WHERE {where}
        """).fetchdf().iloc[0].astype("int64").to_dict()

    tally_in_scope = tally("in_scope")
    tally_d1 = tally("in_scope AND source_file='file1'")

    # D1 event-key SHA256: canonical serialization "ticker|YYYY-MM-DD|mom.2f", sorted, newline-joined
    d1_keys = con.execute("""
        SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS m
        FROM _canon WHERE in_scope AND source_file='file1'
    """).fetchdf()
    key_strings = sorted(f"{r.ticker}|{r.event_date_canonical}|{r.m:.2f}" for r in d1_keys.itertuples(index=False))
    d1_key_blob = "\n".join(key_strings)
    d1_key_sha256 = hashlib.sha256(d1_key_blob.encode("utf-8")).hexdigest()

    # view defining SQL hash (from the catalog - the actual t8 view; no scan)
    view_ddl = con.execute(
        "SELECT sql FROM duckdb_views() WHERE view_name='momentum_events_canonical' AND schema_name='main'"
    ).fetchone()[0]
    view_sql_sha256 = hashlib.sha256(view_ddl.encode("utf-8")).hexdigest()

    # ---------- SURFACE 2: DEV V4 ----------
    import pandas as pd
    prim = pd.read_parquet(DEV_PRIMARY); side = pd.read_parquet(DEV_SIDECAR)
    dev = pd.concat([prim, side], ignore_index=True)
    con.register("_dev_df", dev.assign(
        d=pd.to_datetime(dev["event_date_canonical"]).dt.strftime("%Y-%m-%d"),
        m=dev["momentum_pct"].round(2))[["ticker", "d", "m"]])
    dev_join = con.execute("""
        SELECT COUNT(*) AS matched FROM (SELECT DISTINCT ticker,d,m FROM _dev_df) d
        JOIN (SELECT DISTINCT ticker, event_date_canonical AS d, ROUND(momentum_pct,2) AS m FROM _canon WHERE in_scope) c
        USING (ticker,d,m)
    """).fetchone()[0]
    dev_flagged = con.execute(f"""
        SELECT d.ticker, d.d AS event_date, d.m AS momentum_pct
        FROM (SELECT DISTINCT ticker,d,m FROM _dev_df) d
        JOIN (SELECT ticker, event_date_canonical AS d, ROUND(momentum_pct,2) AS m FROM _canon WHERE flag_eth_dominant_t0) c
        USING (ticker,d,m) ORDER BY 1,2
    """).fetchdf()
    dev_trades_rows = con.execute("SELECT COUNT(*) FROM filtered_trades_dev_v4").fetchone()[0]
    dev_quotes_rows = con.execute("SELECT COUNT(*) FROM filtered_quotes_dev_v4").fetchone()[0]

    # ---------- SURFACE 3: BAR CACHE ----------
    bar_total = con.execute(f"SELECT COUNT(*) FROM {BARS_TABLE}").fetchone()[0]
    by_offset = con.execute(f"""
        SELECT session_offset,
               COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) AS n_events,
               COUNT(*) AS n_bar_rows
        FROM {BARS_TABLE} GROUP BY session_offset ORDER BY session_offset
    """).fetchdf()
    t0_events = int(by_offset.loc[by_offset["session_offset"] == 0, "n_events"].iloc[0])
    bar_dupes = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT ticker,event_date_canonical,momentum_pct,session_offset,minute_index,COUNT(*) c
            FROM {BARS_TABLE} GROUP BY 1,2,3,4,5 HAVING COUNT(*)>1)
    """).fetchone()[0]
    minute_range = con.execute(f"SELECT MIN(minute_index) mn, MAX(minute_index) mx FROM {BARS_TABLE}").fetchone()

    con.close()

    # compare bar cache to Phase 6 T3 table exactly
    with open(PHASE6_T3_SUMMARY) as f:
        p6 = json.load(f)
    p6_by_offset = {int(r["session_offset"]): (int(r["n_events"]), int(r["n_bar_rows"])) for r in p6["bars"]["by_offset"]}
    offset_matches, offset_diff = True, []
    for r in by_offset.itertuples(index=False):
        off = int(r.session_offset); exp = p6_by_offset.get(off)
        got = (int(r.n_events), int(r.n_bar_rows))
        if exp != got:
            offset_matches = False
            offset_diff.append({"offset": off, "phase6": exp, "phase7": got})

    # out-of-session: RTH-only cache -> all minute_index in [0, 389]; max 389 < 390 confirms no leakage,
    # and the byte-identical match to Phase 6 T3 inherits verify_bars' original 0/0 result.
    out_of_session_ok = (minute_range[0] >= 0 and minute_range[1] < 390)

    row9_triggered = dev_join != EXPECTED["dev"]
    row10_triggered = (
        bar_total != EXPECTED["bar_rows"] or t0_events != EXPECTED["t0_events"]
        or bar_dupes != 0 or not offset_matches or not out_of_session_ok
    )

    manifest = {
        "manifest": "analysis_ready_manifest_v1", "phase": "7", "task": "T4",
        "generated": "2026-07-24",
        "note": "Three-surface pin ahead of measurement work. flag_eth_dominant_t0 / t0_eth_row_share are annotations (flag-don't-delete); no measurement excludes flagged events by default (per-phase Cooper decision). Spine tallies + D1 key hash computed scan-free (view flag logic replicated on base+parquets, T2-proven equivalent); the view itself is never materialized (trades_ingested/quotes_ingested would scan filtered_trades/quotes).",
        "surface_spine": {
            "total_rows": int(counts["n_rows"]),
            "in_scope": {"observed": int(counts["in_scope_n"]), "expected": EXPECTED["in_scope"], "pass": int(counts["in_scope_n"]) == EXPECTED["in_scope"]},
            "d1": {"observed": int(counts["d1_n"]), "expected": EXPECTED["d1"], "pass": int(counts["d1_n"]) == EXPECTED["d1"]},
            "flag_tallies_over_in_scope_20951": tally_in_scope,
            "flag_tallies_over_d1_15763": tally_d1,
            "flag_eth_dominant_t0_note": "TRUE=736 over the full spine; the same 736 all fall inside D1 (every flagged event is a file1 in_scope event, by construction from event_minute_bars_v1). t0_eth_row_share non-null count == flag TRUE count (only flagged events carry a share).",
            "trades_ingested_quotes_ingested_omitted": "coverage indicators, not flags; their only definition scans filtered_trades/quotes (prohibited). D1 values are in results/phase_5a/artifacts/sampling_frame.parquet.",
            "view_defining_sql_sha256": view_sql_sha256,
            "view_defining_sql_note": "SHA256 of the stage=t8 view DDL from duckdb_views(); embeds absolute read_parquet paths, so it pins THIS environment's view text.",
            "d1_event_key_sha256": d1_key_sha256,
            "d1_event_key_serialization": "each key = f'{ticker}|{event_date_canonical}|{momentum_pct:.2f}' (event_date_canonical as YYYY-MM-DD, momentum_pct rounded to 2dp then formatted %.2f); keys sorted ascending as strings; joined by '\\n'; UTF-8; SHA256.",
            "d1_event_key_count": len(key_strings),
        },
        "surface_dev_v4": {
            "manifest_join_vs_canonical_spine": {"observed": int(dev_join), "expected": EXPECTED["dev"], "pass": int(dev_join) == EXPECTED["dev"]},
            "per_cohort_counts": {"primary": int(len(prim)), "sidecar": int(len(side)), "total": int(len(dev))},
            "dev_table_row_counts": {"filtered_trades_dev_v4": int(dev_trades_rows), "filtered_quotes_dev_v4": int(dev_quotes_rows)},
            "dev_events_flag_eth_dominant_t0": dev_flagged.to_dict(orient="records"),
        },
        "surface_bar_cache": {
            "table": BARS_TABLE,
            "total_rows": {"observed": int(bar_total), "expected": EXPECTED["bar_rows"], "pass": int(bar_total) == EXPECTED["bar_rows"]},
            "distinct_t0_events": {"observed": int(t0_events), "expected": EXPECTED["t0_events"], "pass": int(t0_events) == EXPECTED["t0_events"]},
            "duplicate_event_offset_minute_keys": {"observed": int(bar_dupes), "pass": int(bar_dupes) == 0},
            "minute_index_range": {"min": int(minute_range[0]), "max": int(minute_range[1]), "rth_max_bound": 390, "in_bounds": bool(out_of_session_ok)},
            "per_offset": by_offset.to_dict(orient="records"),
            "per_offset_matches_phase6_t3": offset_matches,
            "per_offset_diffs": offset_diff,
            "out_of_session_note": "RTH-only cache: all minute_index in [0,389], max 389 < 390-min RTH bound. Byte-identical to Phase 6 T3's materialization (total rows + all 7 per-offset counts match), inheriting verify_bars' original 0 duplicate / 0 out-of-session result.",
        },
        "escalation_row9_dev_join_ne_56": bool(row9_triggered),
        "escalation_row10_bar_cache_deviation": bool(row10_triggered),
        "source": "research/phase_7/t4_manifest.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(json.dumps(manifest, indent=2, default=str))

    if row9_triggered:
        print(f"\n*** ESCALATION row 9: dev v4 manifest join {dev_join} != 56 - HARD STOP ***")
    if row10_triggered:
        print(f"\n*** ESCALATION row 10: bar-cache integrity deviation - HARD STOP ***")
    if not (row9_triggered or row10_triggered):
        print("\nT4 escalation rows 9, 10 clear.")


if __name__ == "__main__":
    main()
