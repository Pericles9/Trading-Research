"""
Phase 2 T5 - overlap comparison between filtered_trades and high_momentum/.

high_momentum/ is absent from the E: data root (T3a) - there are zero
(event, session) pairs present in both sources by construction, so T5's
row-count comparison and its >10%-divergence escalation check are N/A
throughout. Still produces the contracted artifact (0 rows, documented
schema) and chart 03 (empty-state, annotated) rather than omitting them,
per the anti-pattern "chart contract omitted on an analysis-only phase."

Column-schema diff is reported from documentation only (results/cleanup/
deletion_report.md), since the source itself cannot be read to verify
independently - explicitly flagged as such, not presented as a live check.
"""
import json

import pandas as pd

OUT_PARQUET = "results/phase_2/artifacts/source_comparison.parquet"
OUT_SUMMARY = "results/phase_2/artifacts/source_comparison_summary.json"

# Documented (not independently verified - source absent) per
# results/phase_1c/artifacts/archive_schema_reference.json / config/phase_1c.json
# archive_schema (filtered/ trades side) and results/cleanup/deletion_report.md
# (high_momentum migration schema, as applied on write into filtered/).
FILTERED_TRADES_DB_COLUMNS = [
    "exchange", "id", "participant_timestamp", "price", "sequence_number",
    "sip_timestamp", "size", "tape", "trf_id", "trf_timestamp", "correction",
]
HIGH_MOMENTUM_DOCUMENTED_COLUMNS = ["sip_timestamp", "price", "size"]


def main():
    schema_diff = {
        "note": (
            "high_momentum/ is absent (T3a) - this schema diff is reported from "
            "results/cleanup/deletion_report.md's description of the migration write "
            "path, not from reading a live high_momentum file. Not independently verified."
        ),
        "filtered_trades_db_columns": FILTERED_TRADES_DB_COLUMNS,
        "high_momentum_documented_columns": HIGH_MOMENTUM_DOCUMENTED_COLUMNS,
        "columns_only_in_filtered_trades": sorted(set(FILTERED_TRADES_DB_COLUMNS) - set(HIGH_MOMENTUM_DOCUMENTED_COLUMNS)),
        "columns_only_in_high_momentum": sorted(set(HIGH_MOMENTUM_DOCUMENTED_COLUMNS) - set(FILTERED_TRADES_DB_COLUMNS)),
        "columns_in_both": sorted(set(FILTERED_TRADES_DB_COLUMNS) & set(HIGH_MOMENTUM_DOCUMENTED_COLUMNS)),
        "documented_transform": "sip_timestamp converted ms->ns (x1,000,000) on write into filtered/; corrupted rows (null sip_timestamp/price/size) dropped at copy time.",
    }

    empty = pd.DataFrame({
        "ticker": pd.Series(dtype="str"),
        "event_date_canonical": pd.Series(dtype="datetime64[ns]"),
        "session_date": pd.Series(dtype="datetime64[ns]"),
        "n_rows_filtered_trades": pd.Series(dtype="int64"),
        "n_rows_high_momentum": pd.Series(dtype="int64"),
        "divergence_pct": pd.Series(dtype="float64"),
    })
    empty.to_parquet(OUT_PARQUET, index=False)

    summary = {
        "phase": "2", "task": "T5",
        "n_compared_event_sessions": 0,
        "reason": "high_momentum/ absent from the E: data root (T3a) - zero (event, session) pairs can be present in both sources.",
        "escalation_check": {
            "condition": "row divergence > 10% on > 10% of compared event-sessions",
            "n_compared": 0,
            "triggered": False,
            "note": "Vacuously not triggered - no pairs to compare, not evidence of agreement.",
        },
        "column_schema_diff": schema_diff,
        "source": "research/phase_2/t5_source_comparison.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
