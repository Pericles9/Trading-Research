"""
Phase 1c T8 - volume reconciliation (informational - feeds Phase 6, gates
nothing except the median-ratio sanity threshold).

For the 149 healed event-day trades (142 calendar_bug event_day heals,
minus SNWV_2022-10-10's T4 failure, plus all 8 T5 collection_failure
event-days - matches T7's flag_missing_event_day_cleared exactly): fetched
event-day trade volume (SUM(size) from filtered_trades, scoped to the
event's own real trade date) vs the scan's own event_volume for that
(ticker, date) in momentum_events.
"""
import json

import duckdb
import pandas as pd

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

DB_PATH = CFG["paths"]["momentum_events_db"]
LEDGER = CFG["paths"]["repair_ledger"]
MANIFEST = CFG["paths"]["heal_manifest"]
THRESHOLDS = CFG["escalation_thresholds"]
OUT_PARQUET = "results/phase_1c/artifacts/volume_reconciliation.parquet"
OUT_SUMMARY = "results/phase_1c/artifacts/t8_volume_reconciliation_summary.json"


def main():
    manifest = pd.read_parquet(MANIFEST)
    ledger = pd.read_parquet(LEDGER)

    event_day_keys = set(manifest[manifest["target_type"].isin(["event_day", "diagnostic_unknown"])]["event_key"])
    healed_trades = ledger[
        (ledger["side"] == "trades") & (ledger["verification_status"] == "ok")
        & ledger["event_key"].isin(event_day_keys)
    ]
    print(f"n healed event-day trades pairs: {len(healed_trades)}")

    con = duckdb.connect(database=DB_PATH, read_only=False)
    rows = []
    for _, r in healed_trades.iterrows():
        ticker, event_date = r["ticker"], r["event_date_canonical"]
        fetched_volume = con.execute(
            "SELECT SUM(size) FROM filtered_trades WHERE ticker = ? AND event_date = ? "
            "AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?",
            [ticker, event_date, event_date],
        ).fetchone()[0]
        scan_row = con.execute(
            "SELECT event_volume FROM momentum_events WHERE ticker = ? AND COALESCE(date, event_date) = ? LIMIT 1",
            [ticker, event_date],
        ).fetchone()
        scan_volume = scan_row[0] if scan_row else None
        rows.append({
            "event_key": r["event_key"], "ticker": ticker, "event_date_canonical": event_date,
            "fetched_volume": fetched_volume, "scan_volume": scan_volume,
        })
    con.close()

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["fetched_volume", "scan_volume"])
    df = df[df["scan_volume"] > 0]
    df["ratio"] = df["fetched_volume"] / df["scan_volume"]
    df.to_parquet(OUT_PARQUET, index=False)

    median_ratio = float(df["ratio"].median())
    lo, hi = THRESHOLDS["volume_reconciliation_median_ratio_range"]
    triggered = not (lo <= median_ratio <= hi)

    summary = {
        "phase": "1c", "task": "T8",
        "n_events_reconciled": len(df),
        "n_excluded_missing_data": len(rows) - len(df),
        "ratio_stats": {
            "median": median_ratio, "mean": float(df["ratio"].mean()),
            "min": float(df["ratio"].min()), "max": float(df["ratio"].max()),
            "p25": float(df["ratio"].quantile(0.25)), "p75": float(df["ratio"].quantile(0.75)),
        },
        "escalation": {"threshold_range": [lo, hi], "median_ratio": median_ratio, "triggered": triggered},
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if triggered:
        raise SystemExit("T8: volume reconciliation median ratio outside [0.5, 2.0] - hard stop per phase prompt.")


if __name__ == "__main__":
    main()
