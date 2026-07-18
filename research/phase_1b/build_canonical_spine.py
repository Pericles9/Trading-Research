"""
Phase 1b T2 - build momentum_events_canonical (stage=t2) and run T2a/T2b/T2c
verification checks.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.canonical import create_view  # noqa: E402
from src.data.db import get_connection  # noqa: E402

OUT_SUMMARY = "results/phase_1b/artifacts/canonical_spine_t2_summary.json"


def main():
    con = get_connection(read_only=False)
    create_view(con, stage="t2")

    # Materialize once - the view's folder_ingested join scans filtered_trades
    # (4.9B rows); re-querying the view per check would repeat that scan.
    con.execute("CREATE OR REPLACE TEMP TABLE _canonical_t2 AS SELECT * FROM momentum_events_canonical")

    # T2a - row count
    row_count = con.execute("SELECT COUNT(*) FROM _canonical_t2").fetchone()[0]
    expected = 23268
    row_count_ok = row_count == expected

    # T2b - folder-join ambiguity check, join key (ticker, event_date_canonical, ROUND(momentum_pct,2))
    folder_inv = str(REPO_ROOT / "results" / "phase_0c" / "artifacts" / "folder_inventory.parquet").replace("\\", "/")
    multi_match = con.execute(
        f"""
        WITH ev AS (
            SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp
            FROM _canonical_t2
        ),
        fi AS (
            SELECT ticker, date AS event_date_canonical, ROUND(TRY_CAST(momentum_str AS DOUBLE), 2) AS mom_2dp,
                   folder_name
            FROM read_parquet('{folder_inv}')
            WHERE date_is_none = FALSE
        ),
        joined AS (
            SELECT ev.ticker, ev.event_date_canonical, ev.mom_2dp, fi.folder_name
            FROM ev
            JOIN fi USING (ticker, event_date_canonical, mom_2dp)
        )
        SELECT
            (SELECT COUNT(*) FROM (
                SELECT ticker, event_date_canonical, mom_2dp, COUNT(*) AS n_folders
                FROM joined GROUP BY 1,2,3 HAVING COUNT(*) > 1
            )) AS n_events_with_multiple_folder_matches,
            (SELECT COUNT(*) FROM (
                SELECT folder_name, COUNT(*) AS n_events
                FROM joined GROUP BY 1 HAVING COUNT(*) > 1
            )) AS n_folders_with_multiple_event_matches
        """
    ).fetchdf().iloc[0].to_dict()

    # T2c - event-side coverage: events with no matching folder at all, by instrument class
    no_folder = con.execute(
        """
        SELECT instrument_class, COUNT(*) AS n
        FROM _canonical_t2
        WHERE has_folder = FALSE
        GROUP BY instrument_class
        ORDER BY n DESC
        """
    ).fetchdf()

    n_no_folder_total = int(no_folder["n"].sum())

    summary = {
        "phase": "1b",
        "task": "T2",
        "t2a_row_count_check": {
            "observed": row_count,
            "expected": expected,
            "pass": row_count_ok,
        },
        "t2b_folder_join_ambiguity": {
            "n_events_with_multiple_folder_matches": int(multi_match["n_events_with_multiple_folder_matches"]),
            "n_folders_with_multiple_event_matches": int(multi_match["n_folders_with_multiple_event_matches"]),
            "escalation_threshold": 25,
            "escalation_triggered": int(multi_match["n_events_with_multiple_folder_matches"]) > 25,
        },
        "t2c_no_folder_coverage": {
            "n_total_no_folder": int(n_no_folder_total),
            "by_instrument_class": dict(zip(no_folder["instrument_class"], no_folder["n"].astype(int))),
            "note": "Headline number only - deep-dive stays in Phase 4 per the phase prompt.",
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

    if not row_count_ok:
        raise SystemExit(f"ESCALATION: canonical spine row count {row_count} != {expected}")


if __name__ == "__main__":
    main()
