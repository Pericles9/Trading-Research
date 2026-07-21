"""
Phase 3 T2 - dev sample membership check.

Manifest resolution (config/phase_3.json dev_sample.manifest_path):
config/dev_sample_v2.json, per CLAUDE.md's standing, unambiguous pointer
("Dev sample = v2 ... v1 and the *_dev tables are retired - do not read
them"). config/dev_sample_events.csv exists but is the retired v1 list -
not read.

Queries the LIVE momentum_events_canonical view (read-only) once, joining
the 50 pinned dev events by (ticker, event_date_canonical, momentum_pct).
"""
import json

import duckdb

DB_PATH = "data/duckdb/main.duckdb"
PHASE_3_CONFIG = "config/phase_3.json"
OUT_PATH = "results/phase_3/artifacts/dev_sample_coverage.json"


def main():
    with open(PHASE_3_CONFIG) as f:
        cfg = json.load(f)
    manifest_path = cfg["dev_sample"]["manifest_path"]

    with open(manifest_path) as f:
        manifest = json.load(f)
    events = manifest["events"]
    n_dev = len(events)
    print(f"loaded {n_dev} dev sample v2 events from {manifest_path}")

    con = duckdb.connect(DB_PATH, read_only=True)
    con.execute("""
        CREATE TEMP TABLE dev_events (ticker VARCHAR, event_date DATE, momentum_pct DOUBLE, decile INTEGER)
    """)
    for e in events:
        con.execute(
            "INSERT INTO dev_events VALUES (?, ?, ?, ?)",
            [e["ticker"], e["date"], e["momentum_pct"], e["decile"]],
        )

    print("querying live momentum_events_canonical view (one pass, joined to 50 dev events)...")
    rows = con.execute("""
        SELECT de.ticker, de.event_date, de.momentum_pct, de.decile,
               mc.in_scope, mc.source_file, mc.coverage_class, mc.quotes_full_window, mc.repaired_1c,
               mc.flag_window_calendar_bug
        FROM dev_events de
        LEFT JOIN momentum_events_canonical mc
          ON de.ticker = mc.ticker
         AND de.event_date = mc.event_date_canonical
         AND ROUND(de.momentum_pct, 2) = ROUND(mc.momentum_pct, 2)
        ORDER BY de.decile, de.ticker
    """).fetchdf()
    con.close()

    n_matched = int(rows["in_scope"].notna().sum())
    n_unmatched = n_dev - n_matched
    n_not_full_window = int((rows["coverage_class"] != "full_window").sum())
    coverage_class_counts = rows["coverage_class"].value_counts(dropna=False).to_dict()
    quotes_full_window_counts = rows["quotes_full_window"].value_counts(dropna=False).to_dict()
    repaired_1c_counts = rows["repaired_1c"].value_counts(dropna=False).to_dict()

    pass_check = n_matched == n_dev and n_not_full_window == 0

    listing = rows.to_dict(orient="records")

    out = {
        "phase": "3", "task": "T2",
        "manifest_path": manifest_path,
        "manifest_note": "config/dev_sample_v2.json used per CLAUDE.md's standing pointer; config/dev_sample_events.csv (retired v1) not read.",
        "n_dev_events": n_dev,
        "n_matched_to_canonical": n_matched,
        "n_unmatched": n_unmatched,
        "coverage_class_counts": {str(k): int(v) for k, v in coverage_class_counts.items()},
        "quotes_full_window_counts": {str(k): int(v) for k, v in quotes_full_window_counts.items()},
        "repaired_1c_counts": {str(k): int(v) for k, v in repaired_1c_counts.items()},
        "n_not_full_window": n_not_full_window,
        "escalation_check": {
            "condition": "any dev event coverage_class != 'full_window'",
            "observed_n_affected": n_not_full_window,
            "triggered": n_not_full_window > 0,
        },
        "pass": pass_check,
        "full_listing": listing,
        "source": "research/phase_3/t2_dev_sample_check.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "full_listing"}, indent=2, default=str))
    print(f"\nPASS: {pass_check}")
    if n_not_full_window > 0:
        print("*** ESCALATION: dev event(s) with coverage_class != 'full_window' ***")
        print(rows[rows["coverage_class"] != "full_window"].to_string())


if __name__ == "__main__":
    main()
