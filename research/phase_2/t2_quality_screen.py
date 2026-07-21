"""
Phase 2 T2 - 2025 quality screen.

Descriptive only - nothing deleted, no spine writes. "2025 slice" reuses
T1's exact definition: momentum_events_canonical.source_file='file2' AND
in_scope=TRUE (5,188 events; see results/phase_2/artifacts/t1_population.json).

Recompute formula, derived directly from the raw momentum_events columns
(confirmed exact-match on sample rows before use, not assumed):
  price_move = event_high - prev_close
  momentum_pct = price_move / prev_close * 100
file2 rows carry event_high/event_open/event_close (not high/open/close,
which are structurally NULL for every file2 row - a separate scan-process
schema, not a data-quality problem in itself).

Migration-signature facet (addendum in prompts/phase_2.md): the 2026-07-11
high_momentum->filtered/ migration wrote a subtractive 3-column trades
schema (sip_timestamp/price/size only). Rows in filtered_trades matching
that exact null pattern across all 8 of the dropped columns are flagged
descriptively as bearing the migration signature - not proof of origin,
just a schema fingerprint consistent with it. Zero-DuckDB-write phase:
read_only=True throughout.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PHASE_2_CONFIG = "config/phase_2.json"
T1_ARTIFACT = "results/phase_2/artifacts/t1_population.json"
PHASE_1B_CONFIG = "config/phase_1b.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
OUT_JSON = "results/phase_2/artifacts/scan_2025_quality.json"
OUT_ROWS_PARQUET = "results/phase_2/artifacts/scan_2025_quality_rows.parquet"


def canonical_2025_inscope_sql(prev_close_floor: float, mom_sanity_cap: float) -> str:
    return f"""
    WITH canonical AS (
        SELECT
            me.ticker,
            COALESCE(me.date, me.event_date) AS event_date_canonical,
            me.momentum_pct,
            me.prev_close,
            me.event_high,
            me.price_move,
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
            (ic_scope AND NOT flag_bad_denominator AND NOT COALESCE(flag_trades_mom_outlier, FALSE) AND NOT flag_missing_event_day) AS in_scope
        FROM (
            SELECT *, instrument_class IN ('common', 'common_adr') AS ic_scope FROM canonical
        )
    )
    SELECT * FROM scoped WHERE source_file = 'file2' AND in_scope
    """


def main():
    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

    with open(PHASE_2_CONFIG) as f:
        cfg2 = json.load(f)
    junk_bound = cfg2["quality_screen"]["junk_momentum_sanity_bound"]
    pc_floor = cfg2["quality_screen"]["prev_close_floor"]
    mismatch_tol = cfg2["quality_screen"]["recompute_mismatch_tolerance"]

    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute(canonical_2025_inscope_sql(prev_close_floor, mom_sanity_cap)).fetchdf()
    n = len(df)

    with open(T1_ARTIFACT) as f:
        t1 = json.load(f)
    assert n == t1["2025_slice"]["in_scope_n"], f"T2 population {n} != T1 2025 in-scope {t1['2025_slice']['in_scope_n']}"

    # --- momentum_pct distribution ---
    mom_stats = {
        "n": n,
        "mean": float(df["momentum_pct"].mean()),
        "median": float(df["momentum_pct"].median()),
        "std": float(df["momentum_pct"].std()),
        "min": float(df["momentum_pct"].min()),
        "max": float(df["momentum_pct"].max()),
        "p01": float(df["momentum_pct"].quantile(0.01)),
        "p05": float(df["momentum_pct"].quantile(0.05)),
        "p25": float(df["momentum_pct"].quantile(0.25)),
        "p75": float(df["momentum_pct"].quantile(0.75)),
        "p95": float(df["momentum_pct"].quantile(0.95)),
        "p99": float(df["momentum_pct"].quantile(0.99)),
    }

    # --- junk flags ---
    df["junk_momentum_gt_bound"] = df["momentum_pct"] > junk_bound
    df["junk_prev_close_floor"] = df["prev_close"] <= pc_floor

    df["momentum_pct_recomputed"] = (df["event_high"] - df["prev_close"]) / df["prev_close"] * 100
    df["recompute_mismatch_abs"] = (df["momentum_pct_recomputed"] - df["momentum_pct"]).abs()
    df["junk_recompute_mismatch"] = df["recompute_mismatch_abs"] > mismatch_tol
    n_recompute_undefined = int(df["event_high"].isna().sum())

    df["any_junk_flag"] = df["junk_momentum_gt_bound"] | df["junk_prev_close_floor"] | df["junk_recompute_mismatch"]

    junk_summary = {
        "junk_momentum_gt_bound_n": int(df["junk_momentum_gt_bound"].sum()),
        "junk_prev_close_floor_n": int(df["junk_prev_close_floor"].sum()),
        "junk_recompute_mismatch_n": int(df["junk_recompute_mismatch"].sum()),
        "recompute_undefined_n_null_event_high": n_recompute_undefined,
        "any_junk_flag_n": int(df["any_junk_flag"].sum()),
        "any_junk_flag_pct": round(100 * df["any_junk_flag"].sum() / n, 4) if n else 0.0,
        "sanity_bound": junk_bound,
        "prev_close_floor": pc_floor,
        "recompute_mismatch_tolerance": mismatch_tol,
    }

    # --- duplicate (ticker, event_day) pairs ---
    dup_counts = df.groupby(["ticker", "event_date_canonical"]).size()
    dup_pairs = dup_counts[dup_counts > 1]
    duplicates = {
        "n_duplicate_pairs": int(len(dup_pairs)),
        "n_rows_involved": int(dup_pairs.sum()) if len(dup_pairs) else 0,
        "examples": [
            {"ticker": t, "event_date_canonical": str(d), "n": int(c)}
            for (t, d), c in dup_pairs.head(20).items()
        ],
    }

    # --- event_day range and per-month counts ---
    df["event_date_canonical"] = pd.to_datetime(df["event_date_canonical"])
    df["month"] = df["event_date_canonical"].dt.strftime("%Y-%m")
    per_month = df.groupby("month").size().sort_index()
    date_range = {
        "min": str(df["event_date_canonical"].min().date()),
        "max": str(df["event_date_canonical"].max().date()),
        "per_month": per_month.to_dict(),
    }

    # --- migration-signature facet (filtered_trades, subtractive 3-col schema check) ---
    print("scanning filtered_trades for migration-signature null pattern on 2025 in-scope events (single pass)...")
    sig = con.execute("""
        WITH events_2025 AS (
            SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp
            FROM momentum_events WHERE event_date IS NOT NULL
        )
        SELECT
            ft.ticker, ft.event_date, ft.momentum_pct,
            COUNT(*) AS n_rows,
            COUNT(*) FILTER (
                WHERE exchange IS NULL AND id IS NULL AND participant_timestamp IS NULL
                  AND sequence_number IS NULL AND tape IS NULL AND trf_id IS NULL
                  AND trf_timestamp IS NULL AND correction IS NULL
            ) AS n_rows_migration_signature
        FROM filtered_trades ft
        JOIN events_2025 e
          ON ft.ticker = e.ticker AND ft.event_date = e.event_date_canonical AND ROUND(ft.momentum_pct, 2) = e.mom_2dp
        GROUP BY 1, 2, 3
    """).fetchdf()
    sig["frac_migration_signature"] = sig["n_rows_migration_signature"] / sig["n_rows"]
    sig_events_any = int((sig["n_rows_migration_signature"] > 0).sum())
    sig_events_all = int((sig["frac_migration_signature"] >= 0.999).sum())
    sig_events_none = int((sig["n_rows_migration_signature"] == 0).sum())
    migration_signature = {
        "note": "Descriptive schema-fingerprint check only, not proof of origin. 'all' = >=99.9% of an event's filtered_trades rows have all 8 dropped columns NULL simultaneously (exchange/id/participant_timestamp/sequence_number/tape/trf_id/trf_timestamp/correction).",
        "n_2025_trades_ingested_events_checked": int(len(sig)),
        "n_events_zero_migration_signature_rows": sig_events_none,
        "n_events_any_migration_signature_rows": sig_events_any,
        "n_events_fully_migration_signature": sig_events_all,
        "total_rows_scanned": int(sig["n_rows"].sum()),
        "total_rows_migration_signature": int(sig["n_rows_migration_signature"].sum()),
    }

    df.drop(columns=["month"]).to_parquet(OUT_ROWS_PARQUET, index=False)

    out = {
        "phase": "2", "task": "T2",
        "population": "momentum_events_canonical.source_file='file2' AND in_scope=TRUE (T1-defined 2025 slice)",
        "n": n,
        "momentum_pct_distribution": mom_stats,
        "junk_flags": junk_summary,
        "duplicates": duplicates,
        "event_day_range_and_per_month": date_range,
        "migration_signature_facet": migration_signature,
        "source": "research/phase_2/t2_quality_screen.py:main",
        "row_level_artifact": OUT_ROWS_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
