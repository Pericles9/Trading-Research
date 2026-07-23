"""
Phase 5 T5 - rebuild momentum_events_canonical with additive window-flag
columns (stage="t7" in src/data/canonical.py).

The only permitted mutation this phase: CREATE OR REPLACE VIEW via a
writable connection. No base-table writes, no data-root writes. Runs
the rebuild, exports post-mutation DDL, checks row-count/in_scope/
sample-diff safety, then re-runs the rebuild a second time to prove
idempotence (T5b) before restoring the connection to read-only use.
"""
import json

import duckdb
import pandas as pd

from src.data.canonical import create_view

DB_PATH = "data/duckdb/main.duckdb"
PHASE_5_CONFIG = "config/phase_5.json"
PRE_DDL = "results/phase_5/artifacts/view_ddl_pre.sql"
POST_DDL = "results/phase_5/artifacts/view_ddl_post.sql"
OUT_SUMMARY = "results/phase_5/artifacts/t5_mutation_safety.json"

# Pre-existing columns (unaffected by stage="t7") checked for byte-identical
# values on the sample diff.
PRE_EXISTING_COLS = [
    "ticker", "event_date_canonical", "momentum_pct", "source_file",
    "instrument_class", "vendor_type", "flag_bad_denominator",
    "flag_trades_mom_outlier", "flag_missing_event_day", "flag_window_calendar_bug",
    "repaired_1c", "has_folder", "trades_ingested", "quotes_ingested",
    "in_scope", "coverage_class", "quotes_full_window",
]
NEW_COLS = ["trades_full_window", "clean_window", "trades_gap_label", "quotes_gap_label", "trades_bitmap", "quotes_bitmap"]


def get_view_ddl(con):
    df = con.execute(
        "SELECT sql FROM duckdb_views() WHERE view_name='momentum_events_canonical' AND schema_name='main'"
    ).fetchdf()
    return df["sql"].iloc[0]


def snapshot(con, seed_ids):
    ids = ",".join(f"'{t}'" for t in seed_ids)
    return con.execute(f"""
        SELECT * FROM momentum_events_canonical
        WHERE ticker IN ({ids})
        ORDER BY ticker, event_date_canonical, momentum_pct
    """).fetchdf()


def main():
    with open(PHASE_5_CONFIG) as f:
        cfg = json.load(f)
    th = cfg["escalation_thresholds"]

    with open(PRE_DDL) as f:
        pre_ddl_recorded = f.read()

    con = duckdb.connect(DB_PATH, read_only=False)

    pre_row_count = con.execute("SELECT COUNT(*) FROM momentum_events_canonical").fetchone()[0]
    pre_in_scope = con.execute("SELECT COUNT(*) FILTER (WHERE in_scope) FROM momentum_events_canonical").fetchone()[0]

    # seeded 1,000-row sample: deterministic seed via a fixed ticker sample (seed 42, reused
    # from the project's standing dev-sample seed convention)
    tickers_df = con.execute("SELECT DISTINCT ticker FROM momentum_events_canonical ORDER BY ticker").fetchdf()
    seed_tickers = tickers_df["ticker"].sample(n=min(400, len(tickers_df)), random_state=42).tolist()
    pre_sample = snapshot(con, seed_tickers)
    print(f"pre-mutation sample: {len(pre_sample)} rows across {len(seed_tickers)} seeded tickers")

    # --- T5: rebuild (mutation #1) ---
    print("rebuilding momentum_events_canonical at stage=t7 (mutation #1)...")
    create_view(con, stage="t7")
    post_ddl = get_view_ddl(con)
    with open(POST_DDL, "w") as f:
        f.write(post_ddl + "\n")
    print(f"wrote post-mutation DDL to {POST_DDL} ({len(post_ddl)} chars)")

    post_row_count = con.execute("SELECT COUNT(*) FROM momentum_events_canonical").fetchone()[0]
    post_in_scope = con.execute("SELECT COUNT(*) FILTER (WHERE in_scope) FROM momentum_events_canonical").fetchone()[0]
    post_sample = snapshot(con, seed_tickers)

    row_count_unchanged = post_row_count == pre_row_count
    in_scope_unchanged = post_in_scope == pre_in_scope == th["canonical_in_scope_expected"]

    common_pre = pre_sample[PRE_EXISTING_COLS].reset_index(drop=True)
    common_post = post_sample[PRE_EXISTING_COLS].reset_index(drop=True)
    sample_shapes_match = common_pre.shape == common_post.shape
    sample_diff = pd.DataFrame()
    if sample_shapes_match:
        sample_diff = common_pre.compare(common_post)
    sample_byte_identical = sample_shapes_match and sample_diff.empty

    new_cols_present = all(c in post_sample.columns for c in NEW_COLS)

    print(f"row_count: pre={pre_row_count} post={post_row_count} unchanged={row_count_unchanged}")
    print(f"in_scope: pre={pre_in_scope} post={post_in_scope} unchanged={in_scope_unchanged}")
    print(f"sample byte-identical on pre-existing columns: {sample_byte_identical}")
    print(f"new columns present: {new_cols_present}")

    # --- T5b: idempotence - rebuild again (mutation #2), diff DDL and a fresh sample ---
    print("rebuilding a second time (mutation #2) for idempotence check...")
    create_view(con, stage="t7")
    post_ddl_2 = get_view_ddl(con)
    ddl_idempotent = post_ddl_2 == post_ddl

    post2_row_count = con.execute("SELECT COUNT(*) FROM momentum_events_canonical").fetchone()[0]
    post2_in_scope = con.execute("SELECT COUNT(*) FILTER (WHERE in_scope) FROM momentum_events_canonical").fetchone()[0]
    post2_sample = snapshot(con, seed_tickers)
    data_idempotent = post2_row_count == post_row_count and post2_in_scope == post_in_scope and post_sample.equals(post2_sample)

    idempotent = ddl_idempotent and data_idempotent
    print(f"idempotence: ddl_identical={ddl_idempotent} data_identical={data_idempotent}")

    con.close()

    summary = {
        "phase": "5", "task": "T5",
        "pre_ddl_char_len": len(pre_ddl_recorded), "post_ddl_char_len": len(post_ddl),
        "row_count": {"pre": int(pre_row_count), "post": int(post_row_count), "unchanged": row_count_unchanged},
        "in_scope": {"pre": int(pre_in_scope), "post": int(post_in_scope), "expected": th["canonical_in_scope_expected"], "unchanged": in_scope_unchanged},
        "sample_diff": {
            "seed": 42, "n_seed_tickers": len(seed_tickers), "n_sample_rows": len(pre_sample),
            "shapes_match": sample_shapes_match, "byte_identical": sample_byte_identical,
            "n_diffs": 0 if sample_diff.empty else len(sample_diff),
        },
        "new_columns_present": new_cols_present, "new_columns": NEW_COLS,
        "idempotence": {"ddl_identical": ddl_idempotent, "data_identical": data_idempotent, "pass": idempotent},
        "escalation_row1_triggered": not (row_count_unchanged and in_scope_unchanged),
        "escalation_row6_triggered": not idempotent,
        "source": "research/phase_5/rebuild_canonical_view.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if summary["escalation_row1_triggered"]:
        print("\n*** ESCALATION row 1: row count or in_scope changed - HARD STOP ***")
    if not sample_byte_identical:
        print("\n*** WARNING: sample diff found changes on pre-existing columns ***")
    if summary["escalation_row6_triggered"]:
        print("\n*** ESCALATION row 6: idempotence failure - HARD STOP ***")


if __name__ == "__main__":
    main()
