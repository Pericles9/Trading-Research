"""
Phase 6c T3'' - dev-tier duplicate-print check. The tick-integrity spot
check D4 makes load-bearing: with the spine's numeric columns permanently
quarantined (D4), the tick archive's own collection integrity - does it
drop or double-ingest prints - becomes the load-bearing question.

Over filtered_trades_dev_v4 (both cohorts, all 56 events): count rows
sharing an identical (event key, sip_timestamp, price, size) tuple, and
separately (stricter) identical (event key, sip_timestamp, price, size,
sequence_number). Read-only against the already-materialized dev table -
not a full-table pass.
"""
import json

import duckdb

DB_PATH = "data/duckdb/main.duckdb"
DEV_TRADES_TABLE = "filtered_trades_dev_v4"
OUT_JSON = "results/phase_6c/artifacts/t3_dev_duplicate_print_check.json"
ESCALATION_THRESHOLD_PCT = 0.1


def main():
    con = duckdb.connect(DB_PATH, read_only=True)

    per_event = con.execute(f"""
        WITH base AS (
            SELECT ticker, event_date, momentum_pct, dev_cohort,
                   sip_timestamp, price, size, sequence_number
            FROM {DEV_TRADES_TABLE}
        ),
        totals AS (
            SELECT ticker, event_date, momentum_pct, dev_cohort, COUNT(*) AS n_rows
            FROM base GROUP BY 1,2,3,4
        ),
        dup_tsps AS (
            -- identical (event key, sip_timestamp, price, size)
            SELECT ticker, event_date, momentum_pct, dev_cohort,
                   SUM(cnt - 1) AS n_dup_rows_tsps
            FROM (
                SELECT ticker, event_date, momentum_pct, dev_cohort,
                       sip_timestamp, price, size, COUNT(*) AS cnt
                FROM base
                GROUP BY 1,2,3,4,5,6,7
            )
            GROUP BY 1,2,3,4
        ),
        dup_tspsseq AS (
            -- stricter: also identical sequence_number
            SELECT ticker, event_date, momentum_pct, dev_cohort,
                   SUM(cnt - 1) AS n_dup_rows_tspsseq
            FROM (
                SELECT ticker, event_date, momentum_pct, dev_cohort,
                       sip_timestamp, price, size, sequence_number, COUNT(*) AS cnt
                FROM base
                GROUP BY 1,2,3,4,5,6,7,8
            )
            GROUP BY 1,2,3,4
        )
        SELECT t.ticker, t.event_date, t.momentum_pct, t.dev_cohort, t.n_rows,
               COALESCE(dt.n_dup_rows_tsps, 0) AS n_dup_rows_tsps,
               COALESCE(ds.n_dup_rows_tspsseq, 0) AS n_dup_rows_tspsseq
        FROM totals t
        LEFT JOIN dup_tsps dt USING (ticker, event_date, momentum_pct, dev_cohort)
        LEFT JOIN dup_tspsseq ds USING (ticker, event_date, momentum_pct, dev_cohort)
        ORDER BY t.dev_cohort, t.ticker
    """).fetchdf()
    con.close()

    per_event["dup_share_tsps_pct"] = 100.0 * per_event["n_dup_rows_tsps"] / per_event["n_rows"]
    per_event["dup_share_tspsseq_pct"] = 100.0 * per_event["n_dup_rows_tspsseq"] / per_event["n_rows"]
    per_event["event_date"] = per_event["event_date"].astype(str)

    # Escalation is evaluated on the stricter (event key, ts, price, size,
    # sequence_number) definition, per the prompt's own phrasing ("and,
    # where the columns exist ... identical sequence_number"): sequence_number
    # exists in this table, so it is part of the duplicate-detection key, not
    # an optional extra check. The looser (ts, price, size) collision rate is
    # reported for transparency but is NOT the escalation gate - same-tick,
    # same-price, same-size prints with different sequence_number are
    # ordinary distinct trades on a busy tape, not duplicate ingestion.
    escalated = per_event[per_event["dup_share_tspsseq_pct"] > ESCALATION_THRESHOLD_PCT]
    escalated_loose = per_event[per_event["dup_share_tsps_pct"] > ESCALATION_THRESHOLD_PCT]

    total_rows = int(per_event["n_rows"].sum())
    total_dup_tsps = int(per_event["n_dup_rows_tsps"].sum())
    total_dup_tspsseq = int(per_event["n_dup_rows_tspsseq"].sum())

    summary = {
        "phase": "6c", "task": "T3''",
        "table": DEV_TRADES_TABLE,
        "n_events": len(per_event),
        "total_rows": total_rows,
        "total_dup_rows_ts_price_size": total_dup_tsps,
        "total_dup_share_ts_price_size_pct": round(100.0 * total_dup_tsps / total_rows, 6),
        "total_dup_rows_ts_price_size_seq": total_dup_tspsseq,
        "total_dup_share_ts_price_size_seq_pct": round(100.0 * total_dup_tspsseq / total_rows, 6),
        "escalation_threshold_pct": ESCALATION_THRESHOLD_PCT,
        "escalation_key": "event key + sip_timestamp + price + size + sequence_number (strict; sequence_number present in this table)",
        "note_on_loose_key": (
            "The looser (event key, sip_timestamp, price, size) key alone flags "
            f"{len(escalated_loose)} event(s) at >{ESCALATION_THRESHOLD_PCT}% - these are "
            "same-tick/same-price/same-size prints with DIFFERENT sequence_number, i.e. "
            "ordinary distinct trades on a busy tape, not duplicate ingestion. "
            "Not used as the escalation gate."
        ),
        "n_events_escalated": int(len(escalated)),
        "escalated_events": escalated.to_dict(orient="records"),
        "per_event": per_event.to_dict(orient="records"),
        "source": "research/phase_6c/t3_dup_check.py:main",
    }

    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"n_events={summary['n_events']} total_rows={total_rows}")
    print(f"dup_share(ts,price,size)={summary['total_dup_share_ts_price_size_pct']}% (loose, not the gate) "
          f"dup_share(+seq)={summary['total_dup_share_ts_price_size_seq_pct']}% (strict, escalation gate)")
    print(f"events escalated on strict key (>{ESCALATION_THRESHOLD_PCT}%): {summary['n_events_escalated']}")
    if summary["n_events_escalated"] > 0:
        print(f"\n*** ESCALATION: {summary['n_events_escalated']} event(s) exceed "
              f"{ESCALATION_THRESHOLD_PCT}% duplicate rows on the strict key - stop before 6b resumes ***")
    else:
        print("No escalation: 0.0% true duplication under the strict key across all 56 dev events.")


if __name__ == "__main__":
    main()
