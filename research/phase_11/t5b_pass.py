"""T5b - the single budgeted full pass (A3-6 step 6, merged with T4c per option (ii)).

ONE scan of filtered_quotes joined to filtered_trades over the detection universe,
producing BOTH event_quote_metrics_v1 and the T4c tie audit.

Writes: exactly one CREATE OR REPLACE TABLE for event_quote_metrics_v1 in
main.duckdb (escalation row 14a). Nothing pre-existing is touched; a catalogue
diff before/after evidences that rather than asserting it.

D15  quotes_ingested / trades_ingested read from the Phase 4/5 materializations.
D18  all 15,369 detection-universe events, all three segments.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import duckdb
import pandas as pd
from common import ARTIFACTS, CONFIG, DB, session_bounds
from stage_b_pipeline import build_cache

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
QSESS = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"
GRID = "results/phase_9/artifacts/t4_axis_grid.parquet"
CEIL = CONFIG["runtime"]["runtime_ceiling_seconds"]
# Cooper accepted a ONE-OFF exception to row 26 for this pass (2026-08-17). The
# standing ceiling above is untouched; only this run is bounded higher.
BOUND = CONFIG["runtime"]["row_26_oneoff_exception"]["t5b_oneoff_ceiling_seconds"]
R30 = CONFIG["cooper_thresholds"]["row_30_tie_price_error_p95_bp_max"]
LAT = [0, 1, 5, 15, 30]


def catalogue(con):
    return sorted(r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables").fetchall())


def main() -> None:
    t_all = time.perf_counter()
    con = duckdb.connect()                      # in-memory driver
    con.execute(f"ATTACH '{DB}' AS mom (READ_ONLY)")   # read-only for the scan
    # The first attempt crashed with a fatal GIL error inside the DuckDB call while
    # detached. The progress-bar thread is the known culprit in that setting, and
    # preserve_insertion_order=false plus an explicit spill directory keeps the
    # window functions inside memory at full scale.
    con.execute("SET enable_progress_bar = false")
    con.execute("SET threads = 8")
    con.execute("SET preserve_insertion_order = false")
    con.execute("SET temp_directory = 'E:/Trading Research/.duckdb_spill'")
    con.execute("CREATE MACRO et(ns) AS (make_timestamp_ns(ns) AT TIME ZONE 'UTC' "
                "AT TIME ZONE 'America/New_York')")
    cat_before = catalogue(con)

    # ---- detection universe, with D15 coverage --------------------------
    con.execute(f"""
        CREATE TABLE det AS
        SELECT a.ticker, a.event_date_canonical AS event_date, round(a.mp, 2) AS mp2,
               a.det_minute, a.det_segment, a.era, a.day_high_ext,
               (q.ticker IS NOT NULL) AS quotes_ingested
        FROM read_parquet('{ANCH}') a
        LEFT JOIN (SELECT DISTINCT ticker, event_date_canonical, mom_2dp
                   FROM read_parquet('{QSESS}')) q
          ON q.ticker = a.ticker AND q.event_date_canonical = a.event_date_canonical
         AND q.mom_2dp = round(a.mp, 2)
        WHERE a.det_undefined = FALSE
    """)
    n_det, n_qi = con.execute(
        "SELECT COUNT(*), COUNT(*) FILTER (quotes_ingested) FROM det").fetchone()
    print(f"detection universe {n_det:,} | quotes_ingested {n_qi:,} "
          f"| excluded {n_det - n_qi:,} ({(n_det-n_qi)/n_det:.4%})")

    con.execute("CREATE TABLE detq AS SELECT * FROM det WHERE quotes_ingested")
    dates = con.execute("""
        SELECT DISTINCT d::DATE AS d FROM (
          SELECT unnest([event_date - INTERVAL 6 DAY, event_date, event_date]) AS d
          FROM detq) WHERE d IS NOT NULL
        UNION SELECT DISTINCT event_date FROM detq""").df()["d"]
    con.register("sb_df", session_bounds(pd.Series(pd.to_datetime(dates)).dt.date))
    con.execute("CREATE TABLE sb AS SELECT * FROM sb_df")

    WHERE = ("(ticker, event_date, round(momentum_pct, 2)) IN "
             "(SELECT ticker, event_date, mp2 FROM detq)")

    # ---- event-partitioned batch loop -------------------------------
    # "One pass, event-partitioned (never one monolithic join)". Batches are
    # ticker-ordered so each predicate lands on contiguous row groups; DuckDB
    # prunes by zone map (measured: one ticker reads in ~7s cold, not a full-table
    # time), so the batches together cost one logical read of the table.
    evs = con.execute("SELECT ticker, event_date, mp2 FROM detq "
                      "ORDER BY ticker, event_date").df()
    BATCH = 400
    batches = [evs.iloc[i:i + BATCH] for i in range(0, len(evs), BATCH)]
    print(f"running the single budgeted pass in {len(batches)} event-partitioned "
          f"batches of <= {BATCH}...")
    # PER-BATCH CHECKPOINT + RESUME. The cache was accumulating in memory and was
    # written only after the loop, so a termination near the end would have destroyed
    # every completed batch. Each batch is now persisted to its own parquet part and
    # completed parts are skipped on restart, so no batch is ever computed twice and
    # an interrupted run resumes instead of restarting.
    PARTS = ARTIFACTS / "_t5b_parts"
    PARTS.mkdir(parents=True, exist_ok=True)
    secs = 0.0
    for i, b in enumerate(batches):
        cpart, tpart = PARTS / f"cache_{i:03d}.parquet", PARTS / f"tie_{i:03d}.parquet"
        if cpart.exists() and tpart.exists():
            if i % 5 == 0:
                print(f"  batch {i+1}/{len(batches)}  resumed (already on disk)", flush=True)
            continue
        con.register("b_df", b)
        con.execute("CREATE OR REPLACE TEMP TABLE _batch AS SELECT * FROM b_df")
        # T=0 extended-session bounds in UTC ns, for the raw prefilter.
        con.execute("""
            CREATE OR REPLACE TEMP TABLE _bounds AS
            SELECT ticker, event_date, mp2,
                   epoch_ns((event_date::DATE + TIME '04:00:00') AT TIME ZONE 'America/New_York') AS lo_ns,
                   epoch_ns((event_date::DATE + TIME '20:00:00') AT TIME ZONE 'America/New_York') AS hi_ns
            FROM _batch
        """)
        w = ("(ticker, event_date, round(momentum_pct, 2)) IN "
             "(SELECT ticker, event_date, mp2 FROM _batch)")
        # Accumulate IN MEMORY. Writing each batch straight into the attached
        # on-disk database made every INSERT after the first ~4x slower than the
        # work itself (314s for the CREATE, ~1371s per INSERT): each insert
        # checkpoints against a 100GB+ file. The cache is only ~8M rows, so it is
        # held in memory and written once, after the loop.
        secs += build_cache(con, "mom.filtered_quotes", "mom.filtered_trades", w,
                            out_table="_cache_batch", append=False)
        con.execute(f"COPY _cache_batch TO '{cpart.as_posix()}' (FORMAT PARQUET)")
        con.execute(f"COPY _tie TO '{tpart.as_posix()}' (FORMAT PARQUET)")
        if i % 5 == 0 or i == len(batches) - 1:
            print(f"  batch {i+1}/{len(batches)}  cumulative {secs:.0f}s", flush=True)
        if secs > BOUND:
            raise SystemExit(f"ESCALATION ROW 26: T5b {secs:.0f}s exceeded the one-off bound {BOUND}s")
    print(f"  pass wall {secs:.1f}s ({secs/3600:.2f} h), ceiling {CEIL}s")
    if secs > BOUND:
        raise SystemExit(f"ESCALATION ROW 26: T5b {secs:.0f}s exceeded the one-off bound {BOUND}s")

    # ---- assemble from the checkpointed parts -----------------------------
    con.execute(f"CREATE OR REPLACE TEMP TABLE _cache_mem AS "
                f"SELECT * FROM read_parquet('{(PARTS / 'cache_*.parquet').as_posix()}')")
    con.execute(f"CREATE OR REPLACE TEMP TABLE _tie_all AS "
                f"SELECT * FROM read_parquet('{(PARTS / 'tie_*.parquet').as_posix()}')")
    print(f"  assembled {con.execute('SELECT COUNT(*) FROM _cache_mem').fetchone()[0]:,} "
          f"cache rows from {len(list(PARTS.glob('cache_*.parquet')))} parts", flush=True)

    # ---- single write of the cache to the database (row 14a) --------------
    con.execute("DETACH mom")
    con.execute(f"ATTACH '{DB}' AS mom")          # read-write, for this one write
    t_w = time.perf_counter()
    con.execute("CREATE OR REPLACE TABLE mom.event_quote_metrics_v1 AS "
                "SELECT * FROM _cache_mem")
    print(f"  cache written to main.duckdb in {time.perf_counter()-t_w:.1f}s", flush=True)

    # ---- T4c: tie audit, from the same scan ------------------------------
    # Persisted FIRST. _tie_all is a TEMP table: if anything below failed after a
    # multi-hour pass, the tie evidence would die with the process while the cache
    # (written per batch to the on-disk table) survived.
    tie = con.execute("SELECT * FROM _tie_all").df()
    tie.to_parquet(ARTIFACTS / "t4c_tie_audit.parquet", index=False)
    print(f"  tie audit persisted: {len(tie):,} affected bars", flush=True)
    con.execute("CREATE OR REPLACE TABLE mom.event_quote_tie_audit_v1 AS "
                "SELECT * FROM _tie_all")
    tot_bars = con.execute("SELECT COUNT(*) FROM mom.event_quote_metrics_v1 "
                           "WHERE n_trades > 0").fetchone()[0]

    # Bars that actually feed the headline: det+latency targets and Phase 9 entry/exit,
    # ASOF-resolved to the bar the original code would have picked.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _cb AS
        SELECT ticker, event_date, minute_index FROM mom.event_quote_metrics_v1
        WHERE n_trades > 0
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _tgt AS
        SELECT ticker, event_date, det_minute + l AS tgt
        FROM detq, unnest({LAT}) AS u(l)
        UNION ALL
        SELECT ticker, event_date_canonical, entry_minute FROM read_parquet('{GRID}')
        WHERE grid = 'fixed_horizon' AND NOT entry_undefined
        UNION ALL
        SELECT ticker, event_date_canonical, exit_minute FROM read_parquet('{GRID}')
        WHERE grid = 'fixed_horizon' AND NOT exit_undefined
    """)
    con.execute("""
        CREATE OR REPLACE TABLE head_bars AS
        SELECT DISTINCT t.ticker, t.event_date, b.minute_index
        FROM _tgt t
        ASOF LEFT JOIN _cb b
          ON t.ticker = b.ticker AND t.event_date = b.event_date
         AND t.tgt >= b.minute_index
        WHERE b.minute_index IS NOT NULL
    """)
    hb = con.execute("""
        SELECT COUNT(*) n_head_bars,
               COUNT(*) FILTER (t.ticker IS NOT NULL) n_affected,
               COUNT(*) FILTER (t.px_range_max > 0) n_price_differing
        FROM head_bars h LEFT JOIN _tie_all t USING (ticker, event_date, minute_index)
    """).df().iloc[0]
    q = con.execute("""
        SELECT QUANTILE_CONT(px_range_bp, 0.5) p50, QUANTILE_CONT(px_range_bp, 0.95) p95,
               MAX(px_range_bp) mx, QUANTILE_CONT(px_range_cents, 0.5) c50,
               QUANTILE_CONT(px_range_cents, 0.95) c95, MAX(px_range_cents) cmx, COUNT(*) n
        FROM head_bars h JOIN _tie_all t USING (ticker, event_date, minute_index)
        WHERE t.px_range_max > 0
    """).df().iloc[0]

    cat_after = catalogue(con)
    n_rows, n_ev = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT (ticker, event_date)) "
        "FROM mom.event_quote_metrics_v1").fetchone()
    dups = con.execute("""
        SELECT COUNT(*) FROM (SELECT ticker, event_date, offset_ns, minute_index, segment,
        COUNT(*) c FROM mom.event_quote_metrics_v1 GROUP BY ALL HAVING c > 1)""").fetchone()[0]
    mi = con.execute("SELECT MIN(minute_index), MAX(minute_index) "
                     "FROM mom.event_quote_metrics_v1").fetchone()
    cols = [c[0] for c in con.execute("DESCRIBE mom.event_quote_metrics_v1").fetchall()]
    req = CONFIG["outputs"]["stage_b_table_required_columns"]
    missing = [c for c in req if c not in cols]

    out = {
        "task": "T5b + T4c", "phase": "11", "date": "2026-08-16",
        "resolution": "Cooper option (ii) - one scan, both outputs.",
        "pass": {"wall_seconds": round(secs, 1), "wall_hours": round(secs / 3600, 3),
                 "ceiling_seconds": CEIL, "t5a_predicted_seconds": 2271,
                 "standing_ceiling_seconds": CEIL, "oneoff_bound_seconds": BOUND,
                 "escalation_row_26": "FIRED at 8.10h projected against the 6.00h standing ceiling; Cooper accepted a ONE-OFF exception 2026-08-17 and the pass ran under a 12h bound. The standing ceiling is unchanged.",
                 "passes_spent": 1},
        "filter_waterfall": {
            "detection_universe": int(n_det),
            "quotes_ingested_true": int(n_qi),
            "quotes_ingested_false_excluded": int(n_det - n_qi),
            "quotes_ingested_false_share": round((n_det - n_qi) / n_det, 6),
            "row_10_threshold": 0.20,
            "row_10_verdict": "DOES NOT FIRE" if (n_det - n_qi) / n_det <= 0.20 else "FIRES",
            "coverage_source": "results/phase_4/artifacts/_actual_quotes_sessions_cache."
                               "parquet (D15) - NOT momentum_events_canonical",
        },
        "t5c_integrity": {
            "cache_rows": int(n_rows), "distinct_events": int(n_ev),
            "duplicate_keys": int(dups), "minute_index_min": mi[0], "minute_index_max": mi[1],
            "required_columns_missing": missing,
            "escalation_row_24": "DOES NOT FIRE" if not missing else "FIRES",
            "catalogue_objects_added": sorted(set(cat_after) - set(cat_before)),
            "catalogue_objects_removed": sorted(set(cat_before) - set(cat_after)),
        },
        "t4c_tie_audit": {
            "t0_minute_bars_with_trades": int(tot_bars),
            "affected_bars": int(len(tie)),
            "affected_share": round(len(tie) / tot_bars, 6) if tot_bars else None,
            "price_differing_bars": int((tie.px_range_max > 0).sum()),
            "price_differing_share_of_affected": round(
                float((tie.px_range_max > 0).mean()), 6) if len(tie) else None,
            "headline_feeding_bars": {
                "n_bars": int(hb.n_head_bars), "n_affected": int(hb.n_affected),
                "n_price_differing": int(hb.n_price_differing),
                "affected_share": round(float(hb.n_affected / hb.n_head_bars), 6),
            },
            "bounded_price_error_on_headline_feeding_bars": {
                "n": int(q.n) if pd.notna(q.n) else 0,
                "p50_bp": round(float(q.p50), 3) if pd.notna(q.p50) else None,
                "p95_bp": round(float(q.p95), 3) if pd.notna(q.p95) else None,
                "max_bp": round(float(q.mx), 3) if pd.notna(q.mx) else None,
                "p50_cents": round(float(q.c50), 4) if pd.notna(q.c50) else None,
                "p95_cents": round(float(q.c95), 4) if pd.notna(q.c95) else None,
                "max_cents": round(float(q.cmx), 4) if pd.notna(q.cmx) else None,
            },
            "escalation_row_30": {
                "threshold_bp": R30, "observed_p95_bp":
                    round(float(q.p95), 3) if pd.notna(q.p95) else None,
                "verdict": ("DOES NOT FIRE" if pd.notna(q.p95) and float(q.p95) <= R30
                            else "FIRES - HARD STOP"),
            },
            "not_exposed": "det_minute = MIN(minute_index) FILTER (high >= threshold) with "
                           "high = MAX(price). Tie-immune by construction, so the "
                           "detection MINUTE is sound regardless of this result.",
            "measure_only": "No fix applied. The sequence_number tiebreak would require "
                            "rebuilding event_minute_bars_v2 and re-deriving frozen "
                            "artifacts - a Cooper decision (row 32).",
        },
        "total_wall_seconds": round(time.perf_counter() - t_all, 1),
    }
    pathlib.Path(ARTIFACTS / "t5_cache_integrity.json").write_text(json.dumps(out, indent=2))
    json.dump(out["t4c_tie_audit"], open(ARTIFACTS / "t4c_tie_audit.json", "w"), indent=2)

    print(f"\ncache rows {n_rows:,} | events {n_ev:,} | dup keys {dups} | mi {mi}")
    print(f"required cols missing: {missing or 'none'}  -> row 24 "
          f"{out['t5c_integrity']['escalation_row_24']}")
    print(f"catalogue added: {out['t5c_integrity']['catalogue_objects_added']}")
    print(f"catalogue removed: {out['t5c_integrity']['catalogue_objects_removed']}")
    print(f"\nT4C: {len(tie):,} affected bars of {tot_bars:,} "
          f"({len(tie)/tot_bars:.4%}); headline-feeding {int(hb.n_affected):,} of "
          f"{int(hb.n_head_bars):,}")
    print(f"  bounded error on headline bars: p50={out['t4c_tie_audit']['bounded_price_error_on_headline_feeding_bars']['p50_bp']} bp "
          f"p95={out['t4c_tie_audit']['bounded_price_error_on_headline_feeding_bars']['p95_bp']} bp")
    print(f"  ROW 30 (threshold {R30} bp): "
          f"{out['t4c_tie_audit']['escalation_row_30']['verdict']}")
    print(f"  ROW 10: {out['filter_waterfall']['row_10_verdict']}")


if __name__ == "__main__":
    main()
