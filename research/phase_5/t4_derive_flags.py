"""
Phase 5 T4 - derive spine_window_flags: merge T2/T3 bitmaps, carry Phase 3/4
labels, compute clean_window, and run all T4a-T4d reconciliation checks.

Read-only against the DB except for creating the new auxiliary
spine_window_flags table (explicitly named by the phase prompt, same
pattern as prior phases' *_dev tables - not a base-table or canonical-view
write). Labels are carried, not recomputed: trades_gap_label from Phase 3's
results/phase_3/artifacts/classification.parquet (287 file1 cohort),
quotes_gap_label from Phase 4's results/phase_4/artifacts/classification.parquet
(386 file1 cohort). Both label columns are NULL only where that side's
own full_window flag is True; every flagged event outside its respective
cohort (all file2 events, by construction, since both cohorts are
file1-scoped) gets 'not_classified'.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
TRADES_BITMAPS = "results/phase_5/artifacts/trades_bitmaps.parquet"
QUOTES_BITMAPS = "results/phase_5/artifacts/quotes_bitmaps_all.parquet"
PHASE_3_CLASSIFICATION = "results/phase_3/artifacts/classification.parquet"
PHASE_4_CLASSIFICATION = "results/phase_4/artifacts/classification.parquet"
PHASE_4_RECONCILIATION = "results/phase_4/artifacts/reconciliation.parquet"
PHASE_5_CONFIG = "config/phase_5.json"
OUT_PARQUET = "results/phase_5/artifacts/spine_window_flags.parquet"
OUT_SUMMARY = "results/phase_5/artifacts/reconciliation_summary.json"


def main():
    with open(PHASE_5_CONFIG) as f:
        cfg = json.load(f)
    th = cfg["escalation_thresholds"]

    trades = pd.read_parquet(TRADES_BITMAPS)
    quotes = pd.read_parquet(QUOTES_BITMAPS)
    print(f"trades_bitmaps: {len(trades)} rows; quotes_bitmaps_all: {len(quotes)} rows")

    key = ["ticker", "event_date_canonical", "momentum_pct", "source_file"]
    merged = trades.merge(
        quotes[key + ["quotes_bitmap", "quotes_missing_offsets", "quotes_n_missing", "quotes_full_window"]],
        on=key, how="outer", indicator=True,
    )
    unmatched = merged[merged["_merge"] != "both"]
    if len(unmatched):
        print(f"*** WARNING: {len(unmatched)} rows did not join both T2/T3 outputs ***")
        print(unmatched[key + ["_merge"]].head(20))
    merged = merged.drop(columns=["_merge"])
    print(f"merged spine_window_flags base: {len(merged)} rows")

    merged["clean_window"] = merged["trades_full_window"] & merged["quotes_full_window"]

    # --- carry Phase 3 trades labels (287 file1 cohort) ---
    p3 = pd.read_parquet(PHASE_3_CLASSIFICATION)[["ticker", "event_day", "momentum_pct", "label"]].rename(
        columns={"event_day": "event_date_canonical", "label": "_p3_label"}
    )
    p3["momentum_pct"] = p3["momentum_pct"].round(2)
    merged["momentum_pct"] = merged["momentum_pct"].round(2)
    merged = merged.merge(p3, on=["ticker", "event_date_canonical", "momentum_pct"], how="left")
    merged["trades_gap_label"] = merged.apply(
        lambda r: None if r["trades_full_window"] else (r["_p3_label"] if pd.notna(r["_p3_label"]) else "not_classified"),
        axis=1,
    )
    merged = merged.drop(columns=["_p3_label"])

    # --- carry Phase 4 quotes labels (386 file1 cohort) ---
    p4 = pd.read_parquet(PHASE_4_CLASSIFICATION)[["ticker", "event_day", "momentum_pct", "label"]].rename(
        columns={"event_day": "event_date_canonical", "label": "_p4_label"}
    )
    p4["momentum_pct"] = p4["momentum_pct"].round(2)
    merged = merged.merge(p4, on=["ticker", "event_date_canonical", "momentum_pct"], how="left")
    merged["quotes_gap_label"] = merged.apply(
        lambda r: None if r["quotes_full_window"] else (r["_p4_label"] if pd.notna(r["_p4_label"]) else "not_classified"),
        axis=1,
    )
    merged = merged.drop(columns=["_p4_label"])

    out_cols = [
        "ticker", "event_date_canonical", "momentum_pct", "source_file",
        "trades_full_window", "quotes_full_window", "clean_window",
        "trades_gap_label", "quotes_gap_label", "trades_bitmap", "quotes_bitmap",
    ]
    spine = merged[out_cols].copy()
    spine.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {len(spine)} rows to {OUT_PARQUET}")

    con = duckdb.connect(DB_PATH, read_only=False)
    con.execute(f"CREATE OR REPLACE TABLE spine_window_flags AS SELECT * FROM read_parquet('{OUT_PARQUET}')")
    tbl_count = con.execute("SELECT COUNT(*) FROM spine_window_flags").fetchone()[0]
    print(f"materialized DuckDB table spine_window_flags: {tbl_count} rows")

    # ================= T4a: file1 subset reconciliation =================
    file1 = spine[spine["source_file"] == "file1"]
    n_trades_flagged_f1 = int((~file1["trades_full_window"]).sum())
    n_quotes_flagged_f1 = int((~file1["quotes_full_window"]).sum())
    n_union_f1 = int(((~file1["trades_full_window"]) | (~file1["quotes_full_window"])).sum())
    n_both_f1 = int(((~file1["trades_full_window"]) & (~file1["quotes_full_window"])).sum())
    n_trades_only_f1 = int(((~file1["trades_full_window"]) & (file1["quotes_full_window"])).sum())
    n_quotes_only_f1 = int(((file1["trades_full_window"]) & (~file1["quotes_full_window"])).sum())

    t4a = {
        "trades_flagged_expected": th["trades_cohort_expected"], "trades_flagged_observed": n_trades_flagged_f1,
        "quotes_flagged_expected": th["quotes_cohort_expected"], "quotes_flagged_observed": n_quotes_flagged_f1,
        "union_expected": th["file1_union_expected"], "union_observed": n_union_f1,
        "overlap_expected": th["overlap_expected"],
        "overlap_observed": {"both": n_both_f1, "trades_only": n_trades_only_f1, "quotes_only": n_quotes_only_f1},
        "exact_match": (
            n_trades_flagged_f1 == th["trades_cohort_expected"]
            and n_quotes_flagged_f1 == th["quotes_cohort_expected"]
            and n_union_f1 == th["file1_union_expected"]
            and n_both_f1 == th["overlap_expected"]["both"]
            and n_trades_only_f1 == th["overlap_expected"]["trades_only"]
            and n_quotes_only_f1 == th["overlap_expected"]["quotes_only"]
        ),
    }

    # ================= T4b: 37 known file2 no-quotes-file events =================
    recon = pd.read_parquet(PHASE_4_RECONCILIATION)
    known37 = recon[
        (recon["in_scope"] == True) & (recon["source_file"] == "file2") & (recon["presence_class"] == "trades_only")
    ][["ticker", "event_date_canonical", "momentum_pct_y"]].rename(columns={"momentum_pct_y": "momentum_pct"})
    known37["momentum_pct"] = known37["momentum_pct"].round(2)
    n_known37 = len(known37)
    known37_joined = known37.merge(
        spine[["ticker", "event_date_canonical", "momentum_pct", "trades_full_window", "quotes_full_window"]],
        on=["ticker", "event_date_canonical", "momentum_pct"], how="left",
    )
    n_known37_matched = known37_joined["quotes_full_window"].notna().sum()
    n_known37_all_flagged_quotes = int((known37_joined["quotes_full_window"] == False).sum())
    t4b = {
        "n_known_no_quotes_file_events": n_known37,
        "threshold_min": th["file2_known_no_quotes_file_min"],
        "meets_min_threshold": n_known37 >= th["file2_known_no_quotes_file_min"],
        "n_matched_to_spine_window_flags": int(n_known37_matched),
        "n_all_flagged_on_quotes_side": n_known37_all_flagged_quotes,
        "all_37_flagged": n_known37_matched == n_known37 and n_known37_all_flagged_quotes == n_known37,
    }

    # ================= T4c: label integrity =================
    trades_bad = spine[(spine["trades_full_window"]) & (spine["trades_gap_label"].notna())]
    trades_bad2 = spine[(~spine["trades_full_window"]) & (spine["trades_gap_label"].isna())]
    quotes_bad = spine[(spine["quotes_full_window"]) & (spine["quotes_gap_label"].notna())]
    quotes_bad2 = spine[(~spine["quotes_full_window"]) & (spine["quotes_gap_label"].isna())]
    t4c = {
        "n_clean_trades_with_nonnull_label": int(len(trades_bad)),
        "n_flagged_trades_with_null_label": int(len(trades_bad2)),
        "n_clean_quotes_with_nonnull_label": int(len(quotes_bad)),
        "n_flagged_quotes_with_null_label": int(len(quotes_bad2)),
        "label_integrity_pass": len(trades_bad) == 0 and len(trades_bad2) == 0 and len(quotes_bad) == 0 and len(quotes_bad2) == 0,
    }

    # ================= T4d: file2 flagged counts + bitmap patterns =================
    file2 = spine[spine["source_file"] == "file2"]
    n_file2 = len(file2)
    n_file2_trades_flagged = int((~file2["trades_full_window"]).sum())
    n_file2_quotes_flagged = int((~file2["quotes_full_window"]).sum())
    file2_trades_flagged_pct = round(100 * n_file2_trades_flagged / n_file2, 2)
    file2_quotes_flagged_pct = round(100 * n_file2_quotes_flagged / n_file2, 2)
    file2_trades_bitmap_top = file2.loc[~file2["trades_full_window"], "trades_bitmap"].value_counts().head(15).to_dict()
    file2_quotes_bitmap_top = file2.loc[~file2["quotes_full_window"], "quotes_bitmap"].value_counts().head(15).to_dict()

    escalation_row4_max_pct = th["file2_flagged_share_max_pct"]
    escalation_row4_max_n = th["file2_flagged_share_max_n"]
    row4_triggered = (
        n_file2_trades_flagged > escalation_row4_max_n or n_file2_quotes_flagged > escalation_row4_max_n
        or file2_trades_flagged_pct > escalation_row4_max_pct or file2_quotes_flagged_pct > escalation_row4_max_pct
    )
    t4d = {
        "n_file2_inscope": n_file2,
        "n_file2_trades_flagged": n_file2_trades_flagged, "file2_trades_flagged_pct": file2_trades_flagged_pct,
        "n_file2_quotes_flagged": n_file2_quotes_flagged, "file2_quotes_flagged_pct": file2_quotes_flagged_pct,
        "trades_bitmap_pattern_top15": file2_trades_bitmap_top,
        "quotes_bitmap_pattern_top15": file2_quotes_bitmap_top,
        "escalation_row4_threshold_pct": escalation_row4_max_pct, "escalation_row4_threshold_n": escalation_row4_max_n,
        "escalation_row4_triggered": row4_triggered,
    }

    summary = {
        "phase": "5", "task": "T4",
        "n_spine_rows": len(spine),
        "t4a_file1_reconciliation": t4a,
        "t4b_known37_check": t4b,
        "t4c_label_integrity": t4c,
        "t4d_file2_first_measurement": t4d,
        "escalation_row3_triggered": not t4a["exact_match"] or not t4b["all_37_flagged"],
        "escalation_row4_triggered": row4_triggered,
        "escalation_row5_triggered": not t4c["label_integrity_pass"],
        "source": "research/phase_5/t4_derive_flags.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    con.close()
    print(json.dumps(summary, indent=2, default=str))

    if summary["escalation_row3_triggered"]:
        print("\n*** ESCALATION row 3: T4a/T4b reconciliation mismatch ***")
    if summary["escalation_row4_triggered"]:
        print("\n*** ESCALATION row 4: file2 flagged share exceeds threshold - HARD STOP per phase prompt ***")
    if summary["escalation_row5_triggered"]:
        print("\n*** ESCALATION row 5: label integrity failure ***")


if __name__ == "__main__":
    main()
