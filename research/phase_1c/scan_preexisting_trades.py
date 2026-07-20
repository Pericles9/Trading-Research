"""
Investigative scan (not a phase task) - same as scan_preexisting_quotes.py
but for the trades side, checking every remaining un-ingested trades heal
target for pre-existing archive coverage on its target session.
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
targets = manifest[manifest["fetch_trades"] & (manifest["target_type"] != "diagnostic_unknown")].copy()
targets = targets.merge(inv, on=["ticker", "event_date_canonical"], how="left")
todo = targets[~targets.apply(lambda r: (r["event_key"], "trades") in done_keys, axis=1)]
todo = todo.dropna(subset=["folder_name"])

results = []
for i, (_, row) in enumerate(todo.iterrows()):
    path = f"data/filtered/{row['folder_name']}/trades.parquet"
    try:
        n = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{path}') WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = DATE '{row['session']}'"
        ).fetchone()[0]
    except Exception as e:
        n = None
        print(f"  error on {path}: {e}")
    results.append({"event_key": row["event_key"], "ticker": row["ticker"], "session": row["session"],
                     "target_type": row["target_type"], "folder_name": row["folder_name"], "n_preexisting_trades": n})
    if (i + 1) % 200 == 0:
        print(f"  {i + 1}/{len(todo)} scanned...")

df = pd.DataFrame(results)
df.to_parquet("results/phase_1c/artifacts/_preexisting_trades_scan.parquet", index=False)
n_affected = int((df["n_preexisting_trades"].fillna(0) > 0).sum())
print(f"\nscanned {len(df)} pending trades targets; {n_affected} have non-zero pre-existing trades rows")
if n_affected:
    print(df[df["n_preexisting_trades"].fillna(0) > 0].to_string())

with open("results/phase_1c/artifacts/_preexisting_trades_scan_summary.json", "w") as f:
    json.dump({"n_scanned": len(df), "n_affected": n_affected}, f, indent=2)
