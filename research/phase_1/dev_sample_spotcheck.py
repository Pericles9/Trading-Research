"""
Phase 1 T5b - per-event row counts for the 50 dev-sample events in
filtered_trades_dev / filtered_quotes_dev. Any zero triggers escalation
row 5 per the phase prompt.
"""
import json
import duckdb
import pandas as pd

DEV_CSV = "config/dev_sample_events.csv"
DB_PATH = "data/duckdb/main.duckdb"
OUT_PATH = "results/phase_1/artifacts/dev_sample_spotcheck.json"


def main():
    events = pd.read_csv(DEV_CSV)
    assert len(events) == 50, f"expected 50 dev-sample events, got {len(events)}"

    con = duckdb.connect(database=DB_PATH, read_only=True)
    con.register("dev_events_tmp", events)

    trades_counts = con.execute(
        """
        SELECT d.ticker, d.date, d.momentum_pct, COUNT(t.ticker) AS n_trades
        FROM dev_events_tmp d
        LEFT JOIN filtered_trades_dev t
          ON d.ticker = t.ticker AND d.date = t.event_date
        GROUP BY d.ticker, d.date, d.momentum_pct
        """
    ).fetchdf()

    quotes_counts = con.execute(
        """
        SELECT d.ticker, d.date, d.momentum_pct, COUNT(q.ticker) AS n_quotes
        FROM dev_events_tmp d
        LEFT JOIN filtered_quotes_dev q
          ON d.ticker = q.ticker AND d.date = q.event_date
        GROUP BY d.ticker, d.date, d.momentum_pct
        """
    ).fetchdf()
    con.close()

    merged = trades_counts.merge(quotes_counts, on=["ticker", "date", "momentum_pct"])
    merged = merged.sort_values(["ticker", "date"]).reset_index(drop=True)

    zero_trades = merged[merged["n_trades"] == 0]
    zero_quotes = merged[merged["n_quotes"] == 0]
    any_zero = merged[(merged["n_trades"] == 0) | (merged["n_quotes"] == 0)]

    result = {
        "phase": "1",
        "task": "T5b",
        "n_events": len(merged),
        "n_events_zero_trades": len(zero_trades),
        "n_events_zero_quotes": len(zero_quotes),
        "n_events_any_zero": len(any_zero),
        "escalation_triggered": len(any_zero) > 0,
        "per_event": merged.to_dict(orient="records"),
    }

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"n_events={len(merged)} zero_trades={len(zero_trades)} zero_quotes={len(zero_quotes)} any_zero={len(any_zero)}")
    if len(any_zero):
        print("ESCALATION - events with zero rows:")
        print(any_zero)


if __name__ == "__main__":
    main()
