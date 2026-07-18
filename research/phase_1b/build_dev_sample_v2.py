"""
Phase 1b T7 - dev sample v2.

Eligibility: in_scope=TRUE AND trades_ingested=TRUE AND quotes_ingested=TRUE
AND flag_window_calendar_bug=FALSE (Amendment 3). Stratified 5 per
momentum_pct decile computed on that population, seed=42. Materializes
filtered_trades_dev_v2/filtered_quotes_dev_v2 FROM the main tables only.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection  # noqa: E402

CONFIG_PATH = "config/phase_1b.json"
OUT_MANIFEST = "config/dev_sample_v2.json"
OUT_SUMMARY = "results/phase_1b/artifacts/t7_dev_sample_v2_summary.json"


def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    seed = cfg["seed"]
    n_deciles = cfg["dev_sample"]["n_deciles"]
    per_decile = cfg["dev_sample"]["per_decile"]

    con = get_connection(read_only=False)

    eligible = con.execute(
        """
        SELECT ticker, event_date_canonical, momentum_pct
        FROM momentum_events_canonical
        WHERE in_scope
          AND trades_ingested
          AND quotes_ingested
          AND NOT flag_window_calendar_bug
        """
    ).fetchdf()
    n_eligible = len(eligible)
    print(f"eligible population: {n_eligible}")

    eligible["decile"] = pd.qcut(eligible["momentum_pct"], n_deciles, labels=False, duplicates="drop")
    n_actual_deciles = eligible["decile"].nunique()

    rng = np.random.default_rng(seed)
    sampled_parts = []
    for d in sorted(eligible["decile"].unique()):
        pool = eligible[eligible["decile"] == d]
        take = min(per_decile, len(pool))
        idx = rng.choice(pool.index, size=take, replace=False)
        sampled_parts.append(pool.loc[idx])
    sample = pd.concat(sampled_parts).sort_values(["decile", "ticker", "event_date_canonical"]).reset_index(drop=True)
    n_sample = len(sample)
    print(f"dev sample v2 size: {n_sample} across {n_actual_deciles} deciles")

    manifest = {
        "phase": "1b", "seed": seed, "n_deciles": n_deciles, "per_decile": per_decile,
        "eligibility": "in_scope=TRUE AND trades_ingested=TRUE AND quotes_ingested=TRUE AND flag_window_calendar_bug=FALSE",
        "n_eligible_population": n_eligible,
        "n_events": n_sample,
        "events": [
            {"ticker": r["ticker"], "date": str(r["event_date_canonical"]), "momentum_pct": r["momentum_pct"], "decile": int(r["decile"])}
            for _, r in sample.iterrows()
        ],
    }
    with open(OUT_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    # Materialize dev v2 tables FROM main tables only
    con.execute("DROP TABLE IF EXISTS filtered_trades_dev_v2")
    con.execute("DROP TABLE IF EXISTS filtered_quotes_dev_v2")

    con.register("dev_v2_manifest", sample[["ticker", "event_date_canonical", "momentum_pct"]])
    con.execute(
        """
        CREATE TABLE filtered_trades_dev_v2 AS
        SELECT ft.* FROM filtered_trades ft
        JOIN dev_v2_manifest m
          ON ft.ticker = m.ticker AND ft.event_date = m.event_date_canonical
         AND ROUND(ft.momentum_pct, 2) = ROUND(m.momentum_pct, 2)
        """
    )
    con.execute(
        """
        CREATE TABLE filtered_quotes_dev_v2 AS
        SELECT fq.* FROM filtered_quotes fq
        JOIN dev_v2_manifest m
          ON fq.ticker = m.ticker AND fq.event_date = m.event_date_canonical
         AND ROUND(fq.momentum_pct, 2) = ROUND(m.momentum_pct, 2)
        """
    )
    n_trades_dev = con.execute("SELECT COUNT(*) FROM filtered_trades_dev_v2").fetchone()[0]
    n_quotes_dev = con.execute("SELECT COUNT(*) FROM filtered_quotes_dev_v2").fetchone()[0]
    print(f"filtered_trades_dev_v2: {n_trades_dev:,} rows, filtered_quotes_dev_v2: {n_quotes_dev:,} rows")

    # T7a - subset verification: dev row count == main-table row count per event
    verification = con.execute(
        """
        SELECT m.ticker, m.event_date_canonical, m.momentum_pct,
               (SELECT COUNT(*) FROM filtered_trades ft WHERE ft.ticker=m.ticker AND ft.event_date=m.event_date_canonical AND ROUND(ft.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS main_trades,
               (SELECT COUNT(*) FROM filtered_trades_dev_v2 fd WHERE fd.ticker=m.ticker AND fd.event_date=m.event_date_canonical AND ROUND(fd.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS dev_trades,
               (SELECT COUNT(*) FROM filtered_quotes fq WHERE fq.ticker=m.ticker AND fq.event_date=m.event_date_canonical AND ROUND(fq.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS main_quotes,
               (SELECT COUNT(*) FROM filtered_quotes_dev_v2 qd WHERE qd.ticker=m.ticker AND qd.event_date=m.event_date_canonical AND ROUND(qd.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS dev_quotes
        FROM dev_v2_manifest m
        """
    ).fetchdf()
    verification["trades_match"] = verification["main_trades"] == verification["dev_trades"]
    verification["quotes_match"] = verification["main_quotes"] == verification["dev_quotes"]
    n_mismatch = int((~(verification["trades_match"] & verification["quotes_match"])).sum())

    # T7b - zero-row check
    zero_rows = verification[(verification["dev_trades"] == 0) | (verification["dev_quotes"] == 0)]
    n_zero = len(zero_rows)

    summary = {
        "phase": "1b", "task": "T7",
        "n_eligible_population": n_eligible,
        "n_deciles_available": int(n_actual_deciles),
        "n_sample": n_sample,
        "filtered_trades_dev_v2_rows": n_trades_dev,
        "filtered_quotes_dev_v2_rows": n_quotes_dev,
        "t7a_subset_verification": {
            "n_events_checked": len(verification),
            "n_mismatch": n_mismatch,
            "escalation_triggered": n_mismatch > 0,
            "mismatches": verification[~(verification["trades_match"] & verification["quotes_match"])].to_dict(orient="records") if n_mismatch else [],
        },
        "t7b_zero_row_check": {
            "n_zero_row_events": n_zero,
            "escalation_triggered": n_zero > 0,
            "events": zero_rows.to_dict(orient="records") if n_zero else [],
        },
        "per_event_row_counts": verification[["ticker", "event_date_canonical", "momentum_pct", "dev_trades", "dev_quotes"]].to_dict(orient="records"),
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "per_event_row_counts"}, indent=2, default=str))

    if n_mismatch > 0:
        raise SystemExit(f"ESCALATION: T7a subset verification failed for {n_mismatch} events")
    if n_zero > 0:
        raise SystemExit(f"ESCALATION: T7b zero-row check failed for {n_zero} events")


if __name__ == "__main__":
    main()
