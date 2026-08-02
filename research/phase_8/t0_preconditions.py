"""
Phase 8 T0 - preconditions pin.

Scan-free (event_minute_bars_v2 only). Records:
  - v2 row count (must match the config pin 45,925,350)
  - SHA256 of the v2 DDL (CREATE TABLE statement, verbatim from duckdb_tables().sql)
  - per-offset row counts, distinct D1 events, minute_index range
  - per-(offset,segment) row counts, distinct D1 events, minute_index range

D1 = the frozen 6b eligible list (results/phase_6b/artifacts/t1_eligible_events.parquet),
joined on (ticker, event_date_canonical, ROUND(momentum_pct,2)).

Escalation row 2: any missing offset or structurally incomplete extended-day coverage
is a hard stop. Per-event gaps on flanking sessions (an event with no prints that day)
are genuine absence, not table incompleteness, and are NOT an escalation - they are
carried later as no_baseline / anchor_undefined.
"""
from __future__ import annotations

import hashlib
import json

import duckdb
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
CONFIG_PATH = "config/phase_8.json"
OUT = "results/phase_8/artifacts/t0_preconditions.json"
EXPECTED_ROWS = 45_925_350
EXPECTED_OFFSETS = [-3, -2, -1, 0, 1, 2, 3]


def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")

    ddl = con.execute(
        "SELECT sql FROM duckdb_tables() WHERE table_name='event_minute_bars_v2'"
    ).fetchone()[0]
    ddl_sha256 = hashlib.sha256(ddl.encode("utf-8")).hexdigest()

    row_count = con.execute("SELECT COUNT(*) FROM event_minute_bars_v2").fetchone()[0]

    d1 = pd.read_parquet(D1_PATH)
    con.register("d1", d1)
    con.execute(
        "CREATE TEMP TABLE d1k AS "
        "SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp FROM d1"
    )
    join = (
        "JOIN d1k ON b.ticker=d1k.ticker "
        "AND b.event_date_canonical=d1k.event_date_canonical "
        "AND ROUND(b.momentum_pct,2)=d1k.mp"
    )

    per_offset = con.execute(f"""
        SELECT b.session_offset AS session_offset,
               COUNT(*) AS rows,
               COUNT(DISTINCT (b.ticker||b.event_date_canonical||b.momentum_pct)) AS distinct_events,
               MIN(b.minute_index) AS min_minute_index,
               MAX(b.minute_index) AS max_minute_index
        FROM event_minute_bars_v2 b {join}
        GROUP BY 1 ORDER BY 1
    """).fetchdf()

    per_seg = con.execute(f"""
        SELECT b.session_offset AS session_offset, b.segment AS segment,
               COUNT(*) AS rows,
               COUNT(DISTINCT (b.ticker||b.event_date_canonical||b.momentum_pct)) AS distinct_events,
               MIN(b.minute_index) AS min_minute_index,
               MAX(b.minute_index) AS max_minute_index
        FROM event_minute_bars_v2 b {join}
        GROUP BY 1,2 ORDER BY 1,2
    """).fetchdf()

    observed_offsets = sorted(int(x) for x in per_offset["session_offset"].tolist())
    all_offsets_present = observed_offsets == EXPECTED_OFFSETS
    all_segments_present = all(
        set(per_seg.loc[per_seg.session_offset == o, "segment"]) == {"premarket", "rth", "post"}
        for o in EXPECTED_OFFSETS
    )
    row_count_ok = int(row_count) == EXPECTED_ROWS

    out = {
        "phase": "8", "task": "T0",
        "source": "research/phase_8/t0_preconditions.py:main",
        "scan_free": True,
        "d1_source": D1_PATH,
        "d1_n": int(len(d1)),
        "v2_row_count": int(row_count),
        "v2_row_count_expected": EXPECTED_ROWS,
        "v2_row_count_pass": row_count_ok,
        "v2_ddl": ddl,
        "v2_ddl_sha256": ddl_sha256,
        "offsets_expected": EXPECTED_OFFSETS,
        "offsets_observed": observed_offsets,
        "all_offsets_present": all_offsets_present,
        "all_segments_present_every_offset": bool(all_segments_present),
        "escalation_row_2_triggered": not (all_offsets_present and all_segments_present),
        "per_offset": per_offset.to_dict(orient="records"),
        "per_offset_segment": per_seg.to_dict(orient="records"),
        "coverage_note": (
            "minute_index origin 04:00 ET (index 0). premarket 0-329 (04:00-09:30), "
            "rth 330-719 (09:30-16:00 on normal days), post 540-959 (post floor 540 = "
            "13:00 ET from early-close half-days; 720=16:00 on normal days). Per-event "
            "distinct counts below 15763 on flanking offsets and in premarket reflect "
            "genuine absence of trades that session, not table incompleteness - carried "
            "downstream as no_baseline / anchor_undefined, never as an escalation."
        ),
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)

    print(json.dumps({k: v for k, v in out.items() if k not in ("per_offset", "per_offset_segment", "v2_ddl")}, indent=2, default=str))
    print("\nper_offset:")
    print(per_offset.to_string(index=False))
    if out["escalation_row_2_triggered"]:
        print("\n*** ESCALATION ROW 2 TRIGGERED - HARD STOP ***")


if __name__ == "__main__":
    main()
