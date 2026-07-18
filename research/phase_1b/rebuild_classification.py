"""
Phase 1b T1-R3 - rebuild instrument_classification.parquet with vendor type
as the verdict. Heuristic (original T1 rule output) retained as a
validation column, not the source of truth.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
SNAPSHOT = "results/phase_1b/artifacts/ticker_reference_snapshot.parquet"
OLD_CLASSIFICATION = "results/phase_1b/artifacts/instrument_classification.parquet"
OUT_PARQUET = "results/phase_1b/artifacts/instrument_classification.parquet"
OUT_SUMMARY = "results/phase_1b/artifacts/instrument_classification_rebuild_summary.json"

VENDOR_TYPE_TO_CLASS = {
    "CS": ("common", True),
    "ADRC": ("common_adr", True),
    "PFD": ("preferred", False),
    "WARRANT": ("warrant", False),
    "UNIT": ("unit", False),
    "RIGHT": ("right", False),
    "ETF": ("fund_product", False),
    "ETN": ("fund_product", False),
    "ETV": ("fund_product", False),
    "FUND": ("fund_product", False),
}

HEURISTIC_AGREE_MAP = {
    "warrant": {"warrant"},
    "warrant_suspect": {"warrant"},
    "preferred": {"preferred"},
    "unit": {"unit"},
    "unit_suspect": {"unit"},
    "right": {"right"},
    "right_suspect": {"right"},
    "common": {"common", "common_adr"},
    "common_class_share": {"common", "common_adr"},
}
NON_SUSPECT_HEURISTIC_CLASSES = {
    "warrant", "preferred", "unit", "right", "common_class_share", "common",
}


def main():
    con = duckdb.connect(read_only=False)
    old = con.execute(f"SELECT ticker, class AS heuristic_class, rule_hit FROM read_parquet('{OLD_CLASSIFICATION}')").fetchdf()

    snap = con.execute(f"SELECT ticker, type, active, delisted_utc FROM read_parquet('{SNAPSHOT}')").fetchdf()
    snap["delisted_date"] = snap["delisted_utc"].astype(str).str.slice(0, 10)
    # dedupe near-duplicate vendor rows per ticker (same type, delisted_utc off by ~1 day
    # across snapshot refresh cycles - confirmed via manual inspection, 7 cases, all
    # same type both records). Keep the most recent (max) delisted_date per ticker.
    snap_dedup = (
        snap.groupby("ticker")
        .agg(vendor_type=("type", "first"), active=("active", "first"), delisted_date=("delisted_date", "max"))
        .reset_index()
    )

    df = old.merge(snap_dedup, on="ticker", how="left")
    df["lookup_method"] = "bulk_reference_snapshot"
    df.loc[df["vendor_type"].isna(), "lookup_method"] = "unresolved"

    other_types_seen = sorted(set(df["vendor_type"].dropna()) - set(VENDOR_TYPE_TO_CLASS))

    def map_class(vt):
        if pd.isna(vt):
            return "unresolved", False
        if vt in VENDOR_TYPE_TO_CLASS:
            return VENDOR_TYPE_TO_CLASS[vt]
        return "other", False

    mapped = df["vendor_type"].apply(map_class)
    df["class"] = mapped.apply(lambda x: x[0])
    df["in_scope_class"] = mapped.apply(lambda x: x[1])

    def agrees(row):
        target = HEURISTIC_AGREE_MAP.get(row["heuristic_class"])
        if target is None or pd.isna(row["vendor_type"]):
            return None
        return row["class"] in target
    df["heuristic_agrees"] = df.apply(agrees, axis=1)

    # T1-R3b: ticker-reuse check - event dates (momentum_events, canonical date)
    # vs vendor active/delisted window. Active tickers (no delisted_utc) treated
    # as covering all event dates (no evidence of a gap). Inactive tickers: every
    # event date must be <= delisted_date.
    con.execute(f"ATTACH '{DB_PATH}' AS mdb (READ_ONLY)")
    event_dates = con.execute(
        """
        SELECT ticker, MAX(COALESCE(date, event_date)) AS max_event_date, COUNT(*) AS n_events
        FROM mdb.momentum_events GROUP BY ticker
        """
    ).fetchdf()
    df = df.merge(event_dates, on="ticker", how="left")
    df["max_event_date"] = pd.to_datetime(df["max_event_date"])
    df["delisted_date_dt"] = pd.to_datetime(df["delisted_date"], errors="coerce")
    df["reuse_conflict"] = (df["active"] == False) & (df["max_event_date"] > df["delisted_date_dt"])
    df["reuse_conflict"] = df["reuse_conflict"].fillna(False)

    df["as_of_date"] = df["max_event_date"]  # per-ticker representative date used for the reuse check

    out_cols = [
        "ticker", "vendor_type", "class", "in_scope_class", "heuristic_class",
        "heuristic_agrees", "lookup_method", "as_of_date", "reuse_conflict",
    ]
    df[out_cols].to_parquet(OUT_PARQUET, index=False)

    # T1-R3a: confusion matrix
    confusion = pd.crosstab(df["heuristic_class"], df["class"])
    confusion_dict = {idx: row.to_dict() for idx, row in confusion.iterrows()}

    disagreements = df[(df["heuristic_agrees"] == False)]
    non_suspect_disagreements = disagreements[disagreements["heuristic_class"].isin(NON_SUSPECT_HEURISTIC_CLASSES)]
    n_matched = int(df["vendor_type"].notna().sum())
    non_suspect_disagree_pct = 100 * len(non_suspect_disagreements) / n_matched if n_matched else None

    reuse_conflicts = df[df["reuse_conflict"] == True]

    # source split (momentum_events vs folder-only) for the T1a-style counts table
    con_db = duckdb.connect(database=DB_PATH, read_only=True)
    me_tickers = set(con_db.execute("SELECT DISTINCT ticker FROM momentum_events").fetchdf()["ticker"])
    con_db.close()
    df["source"] = df["ticker"].apply(lambda t: "momentum_events" if t in me_tickers else "folder_only")
    counts_table = df.groupby(["class", "source"]).size().unstack(fill_value=0).reindex(
        columns=["momentum_events", "folder_only"], fill_value=0
    )

    summary = {
        "phase": "1b",
        "task": "T1-R3",
        "n_tickers": len(df),
        "n_matched_vendor": n_matched,
        "n_unresolved": int((df["class"] == "unresolved").sum()),
        "unresolved_pct": round(100 * (df["class"] == "unresolved").sum() / len(df), 4),
        "vendor_type_distribution": df["vendor_type"].value_counts(dropna=False).to_dict(),
        "other_vendor_types_not_in_mapping_table": other_types_seen,
        "class_counts_by_class_and_source": {
            cls: {"momentum_events": int(row["momentum_events"]), "folder_only": int(row["folder_only"])}
            for cls, row in counts_table.iterrows()
        },
        "t1_r3a_confusion_matrix_heuristic_rows_vendor_cols": confusion_dict,
        "t1_r3a_disagreements": {
            "n_total_disagreements": int(len(disagreements)),
            "n_non_suspect_disagreements": int(len(non_suspect_disagreements)),
            "non_suspect_disagree_pct_of_matched": round(non_suspect_disagree_pct, 4) if non_suspect_disagree_pct is not None else None,
            "escalation_threshold_pct": 5.0,
            "escalation_triggered": (non_suspect_disagree_pct or 0) > 5.0,
            "non_suspect_disagreement_tickers": sorted(non_suspect_disagreements["ticker"].tolist()) if len(non_suspect_disagreements) <= 50 else f"{len(non_suspect_disagreements)} rows, see artifact",
        },
        "t1_r3b_reuse_check": {
            "n_checked": int(df["max_event_date"].notna().sum()),
            "n_conflicts": int(len(reuse_conflicts)),
            "escalation_threshold": 25,
            "escalation_triggered": len(reuse_conflicts) > 25,
            "conflict_tickers": sorted(reuse_conflicts["ticker"].tolist()),
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
