"""
Phase 8 T2b - row-cap detector (ARBB, open since the Phase 6 risk register).

Scan-free (event_minute_bars_v2 only). Per-event T=0 total print count =
SUM(n_trades) over all T0 (session_offset=0) bars. Reports the distribution
and flags:
  - any value exactly 50,000 / 100,000 / 200,000
  - any exact count shared by >=3 distinct events (a silent-cap signature)
  - ARBB's own count, explicitly

No root-cause: that needs filtered/ parquet reads and is out of scope.
"""
from __future__ import annotations

import json

import duckdb
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
OUT_JSON = "results/phase_8/artifacts/t2_row_cap_scan.json"
OUT_PARQUET = "results/phase_8/artifacts/t2_row_cap_counts.parquet"
ROUND_NUMBERS = [50_000, 100_000, 200_000]


def main():
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    d1 = pd.read_parquet(D1_PATH)
    con.register("d1", d1)
    con.execute("CREATE TEMP TABLE d1k AS SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp FROM d1")

    counts = con.execute("""
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp,
               SUM(b.n_trades) AS t0_print_count
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical
                AND ROUND(b.momentum_pct,2)=d1k.mp
        WHERE b.session_offset = 0
        GROUP BY 1,2,3
    """).fetchdf()
    counts.to_parquet(OUT_PARQUET, index=False)
    n = len(counts)

    c = counts["t0_print_count"].astype("int64")
    dist = {
        "n": n,
        "min": int(c.min()), "max": int(c.max()),
        "median": float(c.median()),
        "q01": float(c.quantile(0.01)), "q25": float(c.quantile(0.25)),
        "q75": float(c.quantile(0.75)), "q99": float(c.quantile(0.99)),
    }

    # exact round-number hits
    round_hits = {str(v): int((c == v).sum()) for v in ROUND_NUMBERS}

    # any exact count shared by >=3 distinct events
    vc = c.value_counts()
    shared = vc[vc >= 3]
    shared_values = [{"count_value": int(v), "n_events": int(k)} for v, k in shared.items()]
    shared_values.sort(key=lambda d: (-d["n_events"], -d["count_value"]))

    # ARBB explicit
    arbb = counts[counts["ticker"] == "ARBB"]
    arbb_rows = [{"ticker": r.ticker, "event_date": str(r.event_date_canonical),
                  "momentum_pct": float(r.mp), "t0_print_count": int(r.t0_print_count)}
                 for r in arbb.itertuples()]

    summary = {
        "phase": "8", "task": "T2b",
        "source": "research/phase_8/t2b_row_cap.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "metric": "per-event T=0 total print count = SUM(n_trades) over all T0 segments",
        "distribution": dist,
        "round_number_exact_hits": round_hits,
        "shared_exact_count_ge3_events": {
            "n_distinct_values": len(shared_values),
            "values": shared_values[:50],
            "note": "an exact print-count shared by >=3 distinct events is a silent-cap signature. Low integer counts (e.g. very thin events with a handful of prints) can share values naturally; inspect the high-value entries.",
        },
        "arbb": arbb_rows if arbb_rows else "no ARBB event in D1",
        "no_root_cause_note": "root cause requires filtered/ parquet reads (out of scope). This is a detector only.",
        "counts_artifact": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "shared_exact_count_ge3_events"}, indent=2, default=str))
    print("\nshared >=3 (top 15):")
    for v in shared_values[:15]:
        print(" ", v)


if __name__ == "__main__":
    main()
