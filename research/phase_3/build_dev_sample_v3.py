"""
Phase 3 Amendment 1, A1-T3 - dev sample v3.

Copy of research/phase_1b/build_dev_sample_v2.py (the located, unambiguous
v2 builder) with exactly one change to the eligibility WHERE clause:
adds `AND coverage_class='full_window' AND quotes_full_window=TRUE`.
Seed (42), n_deciles (10), per_decile (5) - all inherited unchanged from
config/phase_1b.json, same as v2. Deciles are computed over the
v3-eligible (post-filter) population, exactly as v2 computed them over
its own eligible population - same pd.qcut + numpy Generator(seed) logic,
byte-for-byte.

Materializes filtered_trades_dev_v3 / filtered_quotes_dev_v3 FROM the
main tables only (filtered_trades/filtered_quotes), mirroring v2's own
table-naming convention (_v2 suffix -> _v3 suffix). This is the one
explicit, authorized write this amendment makes - new dev-tier tables
only, never momentum_events_canonical, filtered_trades, or filtered_quotes
themselves (read-only source of the join).

config/dev_sample_v2.json and its builder are not modified.
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
OUT_MANIFEST = "config/dev_sample_v3.json"
OUT_SUMMARY = "results/phase_3/artifacts/dev_sample_v3_build_summary.json"


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
          AND coverage_class = 'full_window'
          AND quotes_full_window
        """
    ).fetchdf()
    n_eligible = len(eligible)
    print(f"v3 eligible population: {n_eligible}")

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
    print(f"dev sample v3 size: {n_sample} across {n_actual_deciles} deciles")

    manifest = {
        "phase": "3", "amendment": "1", "seed": seed, "n_deciles": n_deciles, "per_decile": per_decile,
        "eligibility": "in_scope=TRUE AND trades_ingested=TRUE AND quotes_ingested=TRUE AND flag_window_calendar_bug=FALSE AND coverage_class='full_window' AND quotes_full_window=TRUE",
        "n_eligible_population": n_eligible,
        "n_events": n_sample,
        "events": [
            {"ticker": r["ticker"], "date": str(r["event_date_canonical"]), "momentum_pct": r["momentum_pct"], "decile": int(r["decile"])}
            for _, r in sample.iterrows()
        ],
    }
    with open(OUT_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    con.execute("DROP TABLE IF EXISTS filtered_trades_dev_v3")
    con.execute("DROP TABLE IF EXISTS filtered_quotes_dev_v3")

    con.register("dev_v3_manifest", sample[["ticker", "event_date_canonical", "momentum_pct"]])
    con.execute(
        """
        CREATE TABLE filtered_trades_dev_v3 AS
        SELECT ft.* FROM filtered_trades ft
        JOIN dev_v3_manifest m
          ON ft.ticker = m.ticker AND ft.event_date = m.event_date_canonical
         AND ROUND(ft.momentum_pct, 2) = ROUND(m.momentum_pct, 2)
        """
    )
    con.execute(
        """
        CREATE TABLE filtered_quotes_dev_v3 AS
        SELECT fq.* FROM filtered_quotes fq
        JOIN dev_v3_manifest m
          ON fq.ticker = m.ticker AND fq.event_date = m.event_date_canonical
         AND ROUND(fq.momentum_pct, 2) = ROUND(m.momentum_pct, 2)
        """
    )
    n_trades_dev = con.execute("SELECT COUNT(*) FROM filtered_trades_dev_v3").fetchone()[0]
    n_quotes_dev = con.execute("SELECT COUNT(*) FROM filtered_quotes_dev_v3").fetchone()[0]
    print(f"filtered_trades_dev_v3: {n_trades_dev:,} rows, filtered_quotes_dev_v3: {n_quotes_dev:,} rows")

    # A1-T3b - verify every v3 event satisfies the full rule
    rule_check = con.execute(
        """
        SELECT m.ticker, m.event_date_canonical, m.momentum_pct,
               mc.coverage_class, mc.quotes_full_window
        FROM dev_v3_manifest m
        JOIN momentum_events_canonical mc
          ON m.ticker = mc.ticker AND m.event_date_canonical = mc.event_date_canonical
         AND ROUND(m.momentum_pct, 2) = ROUND(mc.momentum_pct, 2)
        """
    ).fetchdf()
    rule_check["rule_pass"] = (rule_check["coverage_class"] == "full_window") & (rule_check["quotes_full_window"])
    n_rule_fail = int((~rule_check["rule_pass"]).sum())

    # subset verification, same pattern as v2's T7a
    verification = con.execute(
        """
        SELECT m.ticker, m.event_date_canonical, m.momentum_pct,
               (SELECT COUNT(*) FROM filtered_trades ft WHERE ft.ticker=m.ticker AND ft.event_date=m.event_date_canonical AND ROUND(ft.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS main_trades,
               (SELECT COUNT(*) FROM filtered_trades_dev_v3 fd WHERE fd.ticker=m.ticker AND fd.event_date=m.event_date_canonical AND ROUND(fd.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS dev_trades,
               (SELECT COUNT(*) FROM filtered_quotes fq WHERE fq.ticker=m.ticker AND fq.event_date=m.event_date_canonical AND ROUND(fq.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS main_quotes,
               (SELECT COUNT(*) FROM filtered_quotes_dev_v3 qd WHERE qd.ticker=m.ticker AND qd.event_date=m.event_date_canonical AND ROUND(qd.momentum_pct,2)=ROUND(m.momentum_pct,2)) AS dev_quotes
        FROM dev_v3_manifest m
        """
    ).fetchdf()
    verification["trades_match"] = verification["main_trades"] == verification["dev_trades"]
    verification["quotes_match"] = verification["main_quotes"] == verification["dev_quotes"]
    n_mismatch = int((~(verification["trades_match"] & verification["quotes_match"])).sum())
    con.close()

    summary = {
        "phase": "3", "amendment": "1", "task": "A1-T3",
        "n_eligible_population": n_eligible,
        "n_deciles_available": int(n_actual_deciles),
        "n_sample": n_sample,
        "filtered_trades_dev_v3_rows": n_trades_dev,
        "filtered_quotes_dev_v3_rows": n_quotes_dev,
        "a1t3b_rule_verification": {
            "n_events_checked": len(rule_check),
            "n_rule_fail": n_rule_fail,
            "escalation_triggered": n_rule_fail > 0,
            "failures": rule_check[~rule_check["rule_pass"]].to_dict(orient="records") if n_rule_fail else [],
        },
        "subset_verification": {
            "n_events_checked": len(verification),
            "n_mismatch": n_mismatch,
            "escalation_triggered": n_mismatch > 0,
        },
        "source": "research/phase_3/build_dev_sample_v3.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if n_rule_fail > 0:
        raise SystemExit(f"ESCALATION: {n_rule_fail} v3 events fail the full_window/quotes_full_window rule")
    if n_mismatch > 0:
        raise SystemExit(f"ESCALATION: subset verification failed for {n_mismatch} events")


if __name__ == "__main__":
    main()
