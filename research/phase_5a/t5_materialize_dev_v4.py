"""
Phase 5a T5 - materialize filtered_trades_dev_v4 / filtered_quotes_dev_v4.

Writable connection - the one explicit, authorized write this phase
makes: new dev-tier tables only (filtered_trades_dev_v4 /
filtered_quotes_dev_v4), never momentum_events_canonical,
filtered_trades, or filtered_quotes themselves (read-only source of the
join), and never filtered_trades_dev_v3 / filtered_quotes_dev_v3 (left
untouched - v3 is superseded, not deleted, per prompts/phase_5a.md).

Join is through momentum_events_canonical's own key shape
(ticker, event_date, ROUND(momentum_pct,2)) against the 56-event
manifest (50 primary + 6 sidecar), never folder presence.

The representative-query timing check computes effective spread (not
quoted - CLAUDE.md standing methodology: "Always cross the spread"):
for each primary-cohort trade, an ASOF JOIN to the prevailing quote
(most recent quote at or before the trade's sip_timestamp), effective
spread = 2*|trade_price - quote_midpoint|, median by event.
"""
import json
import time

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PRIMARY_PARQUET = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
SIDECAR_PARQUET = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
PHASE_5A_CONFIG = "config/phase_5a.json"
OUT_SUMMARY = "results/phase_5a/artifacts/t5_materialize_summary.json"


def main():
    with open(PHASE_5A_CONFIG) as f:
        cfg = json.load(f)
    max_seconds = cfg["escalation_thresholds"]["representative_query_max_seconds"]

    primary = pd.read_parquet(PRIMARY_PARQUET)[["ticker", "event_date_canonical", "momentum_pct", "dev_cohort"]]
    sidecar = pd.read_parquet(SIDECAR_PARQUET)[["ticker", "event_date_canonical", "momentum_pct", "dev_cohort"]]
    manifest = pd.concat([primary, sidecar], ignore_index=True)
    n_manifest = len(manifest)
    print(f"manifest: {n_manifest} events ({len(primary)} primary + {len(sidecar)} sidecar)")

    con = duckdb.connect(DB_PATH, read_only=False)
    con.register("dev_v4_manifest", manifest)

    con.execute("DROP TABLE IF EXISTS filtered_trades_dev_v4")
    con.execute("DROP TABLE IF EXISTS filtered_quotes_dev_v4")

    con.execute("""
        CREATE TABLE filtered_trades_dev_v4 AS
        SELECT ft.*, m.dev_cohort
        FROM filtered_trades ft
        JOIN dev_v4_manifest m
          ON ft.ticker = m.ticker AND ft.event_date = m.event_date_canonical
         AND ROUND(ft.momentum_pct, 2) = ROUND(m.momentum_pct, 2)
    """)
    con.execute("""
        CREATE TABLE filtered_quotes_dev_v4 AS
        SELECT fq.*, m.dev_cohort
        FROM filtered_quotes fq
        JOIN dev_v4_manifest m
          ON fq.ticker = m.ticker AND fq.event_date = m.event_date_canonical
         AND ROUND(fq.momentum_pct, 2) = ROUND(m.momentum_pct, 2)
    """)

    trades_counts = con.execute("""
        SELECT dev_cohort, COUNT(*) AS n_rows, COUNT(DISTINCT (ticker, event_date, momentum_pct)) AS n_events
        FROM filtered_trades_dev_v4 GROUP BY dev_cohort
    """).fetchdf()
    quotes_counts = con.execute("""
        SELECT dev_cohort, COUNT(*) AS n_rows, COUNT(DISTINCT (ticker, event_date, momentum_pct)) AS n_events
        FROM filtered_quotes_dev_v4 GROUP BY dev_cohort
    """).fetchdf()
    print("trades:\n", trades_counts)
    print("quotes:\n", quotes_counts)

    # T5a - per-event presence check. Primary events must have BOTH sides present;
    # sidecar events may legitimately lack quotes (e.g. the no-quotes-file pattern 1111111|0000000).
    presence = con.execute("""
        SELECT m.ticker, m.event_date_canonical, m.momentum_pct, m.dev_cohort,
               COALESCE(t.n_trades, 0) AS n_trades, COALESCE(q.n_quotes, 0) AS n_quotes
        FROM dev_v4_manifest m
        LEFT JOIN (
            SELECT ticker, event_date, ROUND(momentum_pct,2) AS mom_2dp, COUNT(*) AS n_trades
            FROM filtered_trades_dev_v4 GROUP BY 1,2,3
        ) t ON m.ticker=t.ticker AND m.event_date_canonical=t.event_date AND ROUND(m.momentum_pct,2)=t.mom_2dp
        LEFT JOIN (
            SELECT ticker, event_date, ROUND(momentum_pct,2) AS mom_2dp, COUNT(*) AS n_quotes
            FROM filtered_quotes_dev_v4 GROUP BY 1,2,3
        ) q ON m.ticker=q.ticker AND m.event_date_canonical=q.event_date AND ROUND(m.momentum_pct,2)=q.mom_2dp
    """).fetchdf()

    primary_missing = presence[(presence["dev_cohort"] == "primary") & ((presence["n_trades"] == 0) | (presence["n_quotes"] == 0))]
    row5_triggered = len(primary_missing) > 0
    sidecar_presence = presence[presence["dev_cohort"] == "flagged_sidecar"][["ticker", "event_date_canonical", "n_trades", "n_quotes"]]

    # representative query timing: effective spread (ASOF join to prevailing quote), median by event, primary cohort
    t0 = time.perf_counter()
    spread = con.execute("""
        WITH matched AS (
            SELECT t.ticker, t.event_date, t.momentum_pct, t.sip_timestamp, t.price,
                   2 * abs(t.price - (q.bid_price + q.ask_price) / 2.0) AS effective_spread
            FROM filtered_trades_dev_v4 t
            ASOF JOIN filtered_quotes_dev_v4 q
              ON t.ticker = q.ticker AND t.event_date = q.event_date
             AND ROUND(t.momentum_pct,2) = ROUND(q.momentum_pct,2)
             AND t.sip_timestamp >= q.sip_timestamp
            WHERE t.dev_cohort = 'primary'
        )
        SELECT ticker, event_date, momentum_pct, MEDIAN(effective_spread) AS median_effective_spread, COUNT(*) AS n_trades
        FROM matched GROUP BY 1,2,3
    """).fetchdf()
    elapsed = time.perf_counter() - t0
    print(f"representative query (effective spread median by event, primary cohort): {elapsed:.3f}s, {len(spread)} events")
    con.close()

    row6_triggered = elapsed > max_seconds

    summary = {
        "phase": "5a", "task": "T5",
        "manifest": {"n_total": n_manifest, "n_primary": len(primary), "n_sidecar": len(sidecar)},
        "trades_dev_v4": trades_counts.set_index("dev_cohort").to_dict(orient="index"),
        "quotes_dev_v4": quotes_counts.set_index("dev_cohort").to_dict(orient="index"),
        "t5a_primary_presence_check": {
            "n_primary_missing_either_side": len(primary_missing),
            "missing_events": primary_missing[["ticker", "event_date_canonical", "n_trades", "n_quotes"]].to_dict(orient="records"),
            "pass": not row5_triggered,
        },
        "t5a_sidecar_presence": sidecar_presence.to_dict(orient="records"),
        "representative_query": {
            "description": "effective spread (ASOF join to prevailing quote) median by event, primary cohort",
            "elapsed_seconds": round(elapsed, 3), "max_seconds": max_seconds,
            "n_events_covered": len(spread), "pass": not row6_triggered,
        },
        "escalation_row5_triggered": row5_triggered,
        "escalation_row6_triggered": row6_triggered,
        "escalation_row7_triggered": False,
        "source": "research/phase_5a/t5_materialize_dev_v4.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if row5_triggered:
        print(f"\n*** ESCALATION row 5: {len(primary_missing)} primary event(s) missing trades or quotes rows - HARD STOP ***")
    if row6_triggered:
        print(f"\n*** ESCALATION row 6: representative query took {elapsed:.1f}s > {max_seconds}s - HARD STOP ***")


if __name__ == "__main__":
    main()
