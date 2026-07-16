"""Build the pinned 50-event dev sample per config/phase_0b.json.

Algorithm (must stay exactly as documented - this is what T5c's rebuild
check reproduces):
  1. Read momentum_events (ticker, date, momentum_pct) from the E: DuckDB.
  2. Eligibility: an event is eligible iff data/filtered/{ticker}_{date}_{momentum_pct:.2f}/
     exists AND contains both trades.parquet and quotes.parquet.
  3. Assign each eligible event to one of 10 momentum_pct deciles, computed
     over the eligible pool only, ordered by (momentum_pct, ticker, date)
     ascending, split into 10 approximately-equal contiguous groups (first
     `remainder` deciles get one extra row) - a fixed, non-random rule so
     decile boundaries never depend on library version/tie-break behavior.
  4. Within each decile, sort eligible events by (ticker, date) - the
     "deterministic ordering" config field - then draw 5 with
     random.Random(seed).sample(sorted_list, 5).
  5. Concatenate the 10 per-decile selections, sorted by (decile, ticker,
     date), as the final 50-row dev sample.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    return json.loads((REPO_ROOT / "config" / "phase_0b.json").read_text(encoding="utf-8"))


def eligible_events(con: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = con.execute(
        "SELECT ticker, date, momentum_pct FROM momentum_events ORDER BY ticker, date"
    ).fetchall()

    filtered_dir = REPO_ROOT / "data" / "filtered"
    eligible = []
    for ticker, date, momentum_pct in rows:
        folder_name = f"{ticker}_{date}_{momentum_pct:.2f}"
        folder = filtered_dir / folder_name
        if (folder / "trades.parquet").exists() and (folder / "quotes.parquet").exists():
            eligible.append({"ticker": ticker, "date": str(date), "momentum_pct": momentum_pct, "folder": folder_name})
    return eligible


def assign_deciles(eligible: list[dict], n_strata: int) -> list[list[dict]]:
    ordered = sorted(eligible, key=lambda e: (e["momentum_pct"], e["ticker"], e["date"]))
    n = len(ordered)
    base, remainder = divmod(n, n_strata)
    deciles: list[list[dict]] = []
    idx = 0
    for d in range(n_strata):
        size = base + (1 if d < remainder else 0)
        deciles.append(ordered[idx: idx + size])
        idx += size
    return deciles


def sample_dev_events(eligible: list[dict], cfg: dict) -> tuple[list[dict], list[dict]]:
    n_strata = cfg["dev_sample"]["n_strata"]
    per_stratum = cfg["dev_sample"]["per_stratum"]
    seed = cfg["dev_sample"]["seed"]

    deciles = assign_deciles(eligible, n_strata)
    eligible_counts = [len(d) for d in deciles]

    selected: list[dict] = []
    for decile_idx, decile_events in enumerate(deciles):
        sorted_group = sorted(decile_events, key=lambda e: (e["ticker"], e["date"]))
        rng = random.Random(seed)
        picked = rng.sample(sorted_group, per_stratum) if len(sorted_group) >= per_stratum else sorted_group
        for e in picked:
            selected.append({**e, "decile": decile_idx})

    selected.sort(key=lambda e: (e["decile"], e["ticker"], e["date"]))
    return selected, eligible_counts


def write_csv(selected: list[dict], out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["decile", "ticker", "date", "momentum_pct", "folder"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in selected:
            writer.writerow({k: row[k] for k in fieldnames})
    return hashlib.sha256(out_path.read_bytes()).hexdigest()


def main() -> None:
    cfg = load_config()
    con = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)
    try:
        eligible = eligible_events(con)
    finally:
        con.close()

    n_strata = cfg["dev_sample"]["n_strata"]
    per_stratum = cfg["dev_sample"]["per_stratum"]

    selected, eligible_counts = sample_dev_events(eligible, cfg)

    min_eligible = min(eligible_counts)
    escalation_triggered = min_eligible < per_stratum

    out_csv = REPO_ROOT / "config" / "dev_sample_events.csv"
    csv_hash = write_csv(selected, out_csv)

    summary = {
        "total_momentum_events_rows": None,
        "eligible_count": len(eligible),
        "n_strata": n_strata,
        "per_stratum": per_stratum,
        "eligible_per_decile": eligible_counts,
        "min_eligible_per_decile": min_eligible,
        "escalation_triggered": escalation_triggered,
        "selected_count": len(selected),
        "csv_sha256": csv_hash,
    }
    print(json.dumps(summary, indent=2))
    if escalation_triggered:
        print(f"HARD STOP: a decile has only {min_eligible} eligible events, < per_stratum={per_stratum}")
        sys.exit(1)


if __name__ == "__main__":
    main()
