"""
E1-T0: join event_fundamentals to the canonical spine and assert membership.

Per prompts/fundamental_exploration_e1.md E1-T0: exactly 20,951 rows, event_id unique,
and set equality against momentum_events_canonical WHERE in_scope = TRUE in both
directions. The set-equality check runs against UNIVERSE_MATERIALIZATION_PATH
(results/phase_5/artifacts/quotes_bitmaps_all.parquet), D15's own materialization of
that exact population -- not a live view scan. research/fundamentals_f1/
verify_event_fundamentals.py already established (2026-09-12) that a live SELECT
against momentum_events_canonical is pathologically slow regardless of which columns
are projected, because the view's staged construction joins filtered_trades/
filtered_quotes for coverage flags unconditionally. Reused, not re-derived
(reuse-before-build/D30) -- see config/fundamental_exploration.json's universe note.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t0_join_and_assert.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t0_join_and_assert.json"
OUT_PARQUET = f"{C.ART}/e1_joined.parquet"


def main() -> int:
    ef = C.load_event_fundamentals()
    detp = C.load_detection_price()

    checks = []

    n_rows = len(ef)
    n_unique = int(ef["event_id"].nunique())
    checks.append({
        "name": "row_count_and_uniqueness",
        "pass": bool(n_rows == C.TARGET_ROW_COUNT and n_unique == n_rows),
        "n_rows": n_rows, "expected": C.TARGET_ROW_COUNT, "n_unique_event_id": n_unique,
    })

    universe = pd.read_parquet(C.UNIVERSE_MATERIALIZATION_PATH).copy()
    if pd.api.types.is_datetime64_any_dtype(universe["event_date_canonical"]):
        universe["event_date_canonical"] = universe["event_date_canonical"].dt.strftime("%Y-%m-%d")
    universe_ids = set(universe.apply(C.event_id, axis=1))
    table_ids = set(ef["event_id"])
    only_in_universe = universe_ids - table_ids
    only_in_table = table_ids - universe_ids
    checks.append({
        "name": "event_id_set_equality_vs_in_scope_universe",
        "pass": not only_in_universe and not only_in_table,
        "n_universe": len(universe_ids), "n_table": len(table_ids),
        "n_only_in_universe": len(only_in_universe), "n_only_in_table": len(only_in_table),
        "sample_only_in_universe": list(only_in_universe)[:5],
        "sample_only_in_table": list(only_in_table)[:5],
        "note": "checked against results/phase_5/artifacts/quotes_bitmaps_all.parquet "
                "(D15's materialization of momentum_events_canonical WHERE in_scope=TRUE), "
                "not a live view scan -- see this script's module docstring.",
    })

    detp_ids = set(detp["event_id"])
    checks.append({
        "name": "detection_price_join_health",
        "pass": not (table_ids - detp_ids) and int(detp["detection_price"].isna().sum()) == 0,
        "n_detection_price_rows": len(detp_ids),
        "n_missing_from_detection_price": len(table_ids - detp_ids),
        "n_null_detection_price": int(detp["detection_price"].isna().sum()),
        "note": "join-health precondition for E1-T3/T4/T7, not one of E1-T0's brief-mandated "
                "assertions -- confirms the detection-price side is complete before building on it.",
    })

    joined = ef.merge(detp, on="event_id", how="left")
    assert len(joined) == n_rows, "join to detection_price changed row count"
    joined.to_parquet(OUT_PARQUET, index=False)

    n_fail = sum(1 for c in checks if not c["pass"])
    summary = {
        "task": "E1-T0 join and assert membership",
        "config_hash": C.cfg_hash(),
        "n_checks": len(checks), "n_fail": n_fail, "checks": checks,
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
