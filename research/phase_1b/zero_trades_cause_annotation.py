"""
Phase 1b T5-R2 - annotate the 150 zero-event-day-trades events with cause
(calendar_bug vs unknown), set flag_missing_event_day + scope_pending_repair,
and check filtered_quotes coverage for the 8 unknown singletons.
"""
import json

import duckdb
import pandas as pd

EVENT_FLAGS = "results/phase_1b/artifacts/event_flags.parquet"
CALENDAR_MISMATCH = "results/phase_1b/artifacts/t5r1_calendar_mismatch.json"
DB_PATH = "data/duckdb/main.duckdb"
OUT_SUMMARY = "results/phase_1b/artifacts/t5r2_zero_trades_cause.json"


def main():
    with open(CALENDAR_MISMATCH) as f:
        set_a = set(json.load(f)["set_a_phantom_holidays"]["dates"])

    con = duckdb.connect(read_only=False)
    flags = con.execute(f"SELECT * FROM read_parquet('{EVENT_FLAGS}')").fetchdf()

    zero_mask = flags["flag_zero_event_day_trades"] == True  # noqa: E712
    flags["event_date_str"] = flags["event_date_canonical"].astype(str)
    flags["zero_trades_cause"] = None
    flags.loc[zero_mask, "zero_trades_cause"] = flags.loc[zero_mask, "event_date_str"].apply(
        lambda d: "calendar_bug" if d in set_a else "unknown"
    )
    flags["flag_missing_event_day"] = zero_mask
    flags["scope_pending_repair"] = zero_mask

    n_calendar_bug = int((flags["zero_trades_cause"] == "calendar_bug").sum())
    n_unknown = int((flags["zero_trades_cause"] == "unknown").sum())

    unknown_events = flags[flags["zero_trades_cause"] == "unknown"][["ticker", "event_date_canonical", "momentum_pct"]].copy()

    # T5-R2a: filtered_quotes coverage for the 8 unknown singletons, same
    # true-calendar-day match used for n_trades_event_day (not the folder tag).
    con_db = duckdb.connect(database=DB_PATH, read_only=True)
    rows = []
    for _, r in unknown_events.iterrows():
        n_quotes = con_db.execute(
            """
            SELECT COUNT(*) FROM filtered_quotes
            WHERE ticker = ? AND event_date = ?
              AND CAST(TO_TIMESTAMP(sip_timestamp / 1e9) AS DATE) = ?
            """,
            [r["ticker"], str(r["event_date_canonical"]), str(r["event_date_canonical"])],
        ).fetchone()[0]
        rows.append({
            "ticker": r["ticker"], "event_date": str(r["event_date_canonical"]),
            "momentum_pct": r["momentum_pct"], "n_quotes_event_day": n_quotes,
            "possible_full_day_halt": n_quotes > 0,
        })
    con_db.close()

    out_cols = ["ticker", "event_date_canonical", "momentum_pct", "n_trades_event_day",
                "flag_trades_mom_outlier", "flag_zero_event_day_trades",
                "zero_trades_cause", "flag_missing_event_day", "scope_pending_repair"]
    flags[out_cols].to_parquet(EVENT_FLAGS, index=False)

    summary = {
        "phase": "1b",
        "task": "T5-R2",
        "n_calendar_bug": n_calendar_bug,
        "n_unknown": n_unknown,
        "expected": {"calendar_bug": 142, "unknown": 8},
        "matches_expected": (n_calendar_bug, n_unknown) == (142, 8),
        "t5r2a_unknown_singletons_quotes_check": rows,
        "n_possible_full_day_halt": sum(r["possible_full_day_halt"] for r in rows),
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
