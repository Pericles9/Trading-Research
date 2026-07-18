"""
Phase 1b T6 - finalize in_scope (view already rebuilt at stage=t6) and
build the event-side + folder-side accounting waterfalls.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection  # noqa: E402

OUT_SUMMARY = "results/phase_1b/artifacts/t6_waterfall_summary.json"


def main():
    con = get_connection(read_only=False)
    con.execute("CREATE OR REPLACE TEMP TABLE _canonical_t6 AS SELECT * FROM momentum_events_canonical")

    total = con.execute("SELECT COUNT(*) FROM _canonical_t6").fetchone()[0]

    # Event-side waterfall - sequential drops, order matters for the
    # narrative but each step's population is defined by cumulative NOT-yet-
    # dropped rows.
    steps = []
    remaining = "_canonical_t6"

    def count_where(table, where):
        return con.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]

    n0 = total
    steps.append({"step": "start", "n": n0})

    # Step 1: non-common (excluding fund_product) - warrant/preferred/unit/right/other/unresolved
    non_common_excl_fund = count_where(
        "_canonical_t6", "instrument_class NOT IN ('common','common_adr','fund_product')"
    )
    n1 = n0 - non_common_excl_fund
    steps.append({"step": "minus_non_common_instruments (excl. fund_product)", "n_dropped": non_common_excl_fund, "n_remaining": n1})

    # Step 2: fund_product
    con.execute(f"CREATE OR REPLACE TEMP TABLE _s1 AS SELECT * FROM _canonical_t6 WHERE instrument_class IN ('common','common_adr','fund_product')")
    n_fund = count_where("_s1", "instrument_class = 'fund_product'")
    n2 = n1 - n_fund
    steps.append({"step": "minus_fund_product", "n_dropped": n_fund, "n_remaining": n2})

    con.execute("CREATE OR REPLACE TEMP TABLE _s2 AS SELECT * FROM _s1 WHERE instrument_class IN ('common','common_adr')")

    # Step 3: bad denominator
    n_bad_denom = count_where("_s2", "flag_bad_denominator")
    n3 = n2 - n_bad_denom
    steps.append({"step": "minus_bad_denominator", "n_dropped": n_bad_denom, "n_remaining": n3})
    con.execute("CREATE OR REPLACE TEMP TABLE _s3 AS SELECT * FROM _s2 WHERE NOT flag_bad_denominator")

    # Step 4: bivariate outliers
    n_bivar = count_where("_s3", "flag_trades_mom_outlier")
    n4 = n3 - n_bivar
    steps.append({"step": "minus_bivariate_outliers", "n_dropped": n_bivar, "n_remaining": n4})
    con.execute("CREATE OR REPLACE TEMP TABLE _s4 AS SELECT * FROM _s3 WHERE NOT COALESCE(flag_trades_mom_outlier, FALSE)")

    # Step 5: zero-trade events (raw observation - flag_missing_event_day is
    # currently identical; kept as two narrative steps per Amendment 3)
    n_zero = count_where("_s4", "flag_missing_event_day")  # same set as flag_zero_event_day_trades
    n5 = n4 - n_zero
    steps.append({"step": "minus_zero_trade_events", "n_dropped": n_zero, "n_remaining": n5})
    con.execute("CREATE OR REPLACE TEMP TABLE _s5 AS SELECT * FROM _s4 WHERE NOT flag_missing_event_day")

    # Step 6: flag_missing_event_day (pending 1c repair) - additional drop
    # beyond step 5, expected 0 since it's currently the same set.
    n_missing_additional = count_where("_s5", "flag_missing_event_day")
    n6 = n5 - n_missing_additional
    steps.append({
        "step": "minus_flag_missing_event_day (pending 1c repair)",
        "n_dropped": n_missing_additional, "n_remaining": n6,
        "note": "Same underlying set as the prior step (flag_missing_event_day == flag_zero_event_day_trades currently) - 0 additional drop expected.",
    })

    n_in_scope_computed = n6
    n_in_scope_actual = count_where("_canonical_t6", "in_scope")
    waterfall_matches_in_scope = n_in_scope_computed == n_in_scope_actual

    # Terminal split into 3 coverage buckets (Amendment 2)
    con.execute("CREATE OR REPLACE TEMP TABLE _in_scope AS SELECT * FROM _canonical_t6 WHERE in_scope")
    n_both_sides = count_where("_in_scope", "trades_ingested AND quotes_ingested")
    n_trades_only = count_where("_in_scope", "trades_ingested AND NOT quotes_ingested")
    n_no_folder = count_where("_in_scope", "NOT trades_ingested")
    coverage_residual = n_in_scope_actual - (n_both_sides + n_trades_only + n_no_folder)

    # Annotation only (not a drop): flag_window_calendar_bug within in-scope
    n_window_bug_in_scope = count_where("_in_scope", "flag_window_calendar_bug")

    event_waterfall = {
        "steps": steps,
        "n_in_scope_computed_via_waterfall": n_in_scope_computed,
        "n_in_scope_actual_from_view": n_in_scope_actual,
        "waterfall_matches_view": waterfall_matches_in_scope,
        "terminal_coverage_split": {
            "both_sides_ingested": n_both_sides,
            "trades_only": n_trades_only,
            "no_folder": n_no_folder,
            "sum": n_both_sides + n_trades_only + n_no_folder,
            "residual": coverage_residual,
        },
        "flag_window_calendar_bug_annotation": {
            "n_in_scope_and_flagged": n_window_bug_in_scope,
            "note": "Annotation only - these events remain in scope for event-day work per Amendment 3.",
        },
    }

    # Folder-side accounting (0c/Phase-1 provenance). Uses Phase 1's
    # reclassified genuine-orphan count (1,341), not the raw 0c match_status
    # (7,252 "orphan") - 5,911 of those are false orphans (the same
    # date/event_date bug from Phase 1 T3/T4), already counted as matched-
    # to-spine events in momentum_events_canonical.
    folder_total = con.execute(
        "SELECT COUNT(*) FROM read_parquet('results/phase_1b/artifacts/folder_inventory_v2.parquet')"
    ).fetchone()[0]
    orphan_class = con.execute(
        """
        SELECT
            SUM(CASE WHEN oc.is_genuine_orphan THEN 1 ELSE 0 END) AS genuine_orphans,
            SUM(CASE WHEN oc.is_false_orphan_date_bug THEN 1 ELSE 0 END) AS false_orphans
        FROM read_parquet('results/phase_1b/artifacts/folder_inventory_v2.parquet') fi
        LEFT JOIN read_parquet('results/phase_1/artifacts/orphan_classification.parquet') oc
          ON fi.folder_name = oc.folder_name
        """
    ).fetchdf().iloc[0]
    genuine_orphans = int(orphan_class["genuine_orphans"])
    false_orphans = int(orphan_class["false_orphans"])
    matched_to_spine = folder_total - genuine_orphans  # includes false orphans, already matched via event_date
    folder_residual = folder_total - (matched_to_spine + genuine_orphans)

    folder_side = {
        "total_folders_24200_plus_409": folder_total,
        "matched_to_spine": matched_to_spine,
        "genuine_orphans": genuine_orphans,
        "of_which_false_orphans_date_bug_already_in_matched": false_orphans,
        "residual": folder_residual,
        "escalation_triggered": folder_residual != 0,
    }

    summary = {
        "phase": "1b", "task": "T6",
        "event_side_waterfall": event_waterfall,
        "folder_side_accounting": folder_side,
        "escalation": {
            "criterion": "waterfall residual != 0",
            "event_side_residual": n_in_scope_actual - n_in_scope_computed if not waterfall_matches_in_scope else 0,
            "folder_side_residual": folder_residual,
            "triggered": (not waterfall_matches_in_scope) or (folder_residual != 0) or (coverage_residual != 0),
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if summary["escalation"]["triggered"]:
        raise SystemExit("ESCALATION: waterfall residual != 0")


if __name__ == "__main__":
    main()
