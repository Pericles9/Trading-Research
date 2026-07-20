"""
Phase 1c - investigative scan (not a phase task): for every remaining
(not-yet-ingested) quotes heal target, check whether the ORIGINAL archive
quotes.parquet already has non-zero rows for the target session date.
SDOT_2025-10-15_150.87's flanking heal for 2025-10-13 revealed the archive
can have partial pre-existing quotes coverage for a date where trades
coverage is confirmed zero - this scan measures how widespread that is
before any further ingestion proceeds. Read-only, no writes.
"""
import json

import duckdb
import pandas as pd

manifest = pd.read_parquet("results/phase_1c/artifacts/heal_manifest.parquet")
ledger = pd.read_parquet("results/phase_1c/artifacts/repair_ledger.parquet")
con = duckdb.connect(read_only=False)
inv = con.execute(
    "SELECT ticker, date AS event_date_canonical, folder_name FROM read_parquet('results/phase_1b/artifacts/folder_inventory_v2.parquet')"
).fetchdf()

done_keys = set(zip(ledger["event_key"], ledger["side"]))
targets = manifest[manifest["fetch_quotes"] & (manifest["target_type"] != "diagnostic_unknown")].copy()
targets = targets.merge(inv, on=["ticker", "event_date_canonical"], how="left")
todo = targets[~targets.apply(lambda r: (r["event_key"], "quotes") in done_keys, axis=1)]
todo = todo.dropna(subset=["folder_name"])

results = []
for i, (_, row) in enumerate(todo.iterrows()):
    path = f"data/filtered/{row['folder_name']}/quotes.parquet"
    try:
        n = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{path}') WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = DATE '{row['session']}'"
        ).fetchone()[0]
    except Exception as e:
        n = None
        print(f"  error on {path}: {e}")
    results.append({"event_key": row["event_key"], "ticker": row["ticker"], "session": row["session"],
                     "target_type": row["target_type"], "folder_name": row["folder_name"], "n_preexisting_quotes": n})
    if (i + 1) % 200 == 0:
        print(f"  {i + 1}/{len(todo)} scanned...")

df = pd.DataFrame(results)
df.to_parquet("results/phase_1c/artifacts/_preexisting_quotes_scan.parquet", index=False)
n_affected = int((df["n_preexisting_quotes"].fillna(0) > 0).sum())
print(f"\nscanned {len(df)} pending quotes targets; {n_affected} have non-zero pre-existing quotes rows")
if n_affected:
    print(df[df["n_preexisting_quotes"].fillna(0) > 0].to_string())

with open("results/phase_1c/artifacts/_preexisting_quotes_scan_summary.json", "w") as f:
    json.dump({"n_scanned": len(df), "n_affected": n_affected}, f, indent=2)
