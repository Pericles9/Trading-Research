"""T2 -- construct the execution participation-rate variable, dev-tier only.

T0 confirmed no such variable exists anywhere in this checkout. Definition, stated before
computation per the prompt's own requirement:

    participation_rate(print) = print.size / SUM(size) over all trades in the same
                                 (ticker, event_date, session_offset, minute_index) bar,
                                 INCLUSIVE of the print's own size in the denominator.

Inclusive, not ambient-excluding, because this is a retrospective measure of how large a
REAL historical print was relative to the volume actually printed in its minute -- not a
simulation of a hypothetical order's impact on a counterfactual book. "What volume would
have printed without this trade" is not answerable from a historical tape.

Minute bucketing reuses event_minute_bars_v2's own (session_offset, minute_index) grid
rather than re-deriving one -- that table already carries the reference the rest of
Phase 8/9/10e/11 aligns to.

Dev tier: filtered_trades_dev_v4, Phase 11's own frozen dev cohort (research/phase_11/common.py
primary_events, "50 primary events... frozen Phase 5a, never rebuilt"), not the generic
CLAUDE.md v3 dev sample -- used here for direct consistency with T3's reuse of Phase 11's own
Lee & Ready / effective-spread machinery at the same cell. Read via DuckDB SQL only; the
per-print result set (order of 1-2e6 rows for the dev cohort) is small enough to leave the
DB as-is rather than stream in chunks, unlike a full-tier pass.

Usage: .venv/Scripts/python.exe -m research.impact_by_participation.t2_participation
"""
from __future__ import annotations

import json
import pathlib

import duckdb
import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
DB = REPO / "data" / "duckdb" / "main.duckdb"
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
N_DECILES = 10


def main() -> int:
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB}' AS mom (READ_ONLY)")

    # dev_cohort='primary' only: filtered_trades_dev_v4 also carries 6 'flagged_sidecar'
    # events (56 total) that Phase 11's own prompt states are "never pooled" with the 50
    # primary events. Matched here for consistency with what T3 reuses.
    dev_events = con.execute(
        "SELECT DISTINCT ticker, event_date, momentum_pct FROM mom.filtered_trades_dev_v4 "
        "WHERE dev_cohort = 'primary'"
    ).df()
    n_dev_events = len(dev_events)

    # Assign each dev print to its (session_offset, minute_index) bar via the event's own
    # first_trade_ts/last_trade_ts window on event_minute_bars_v2, matched on ticker/event_date/
    # momentum_pct -- the same three-part key t8_impact.py and t4_gate.py both join on.
    d = con.execute("""
        WITH t AS (
            SELECT t.ticker, t.event_date, t.momentum_pct, t.sip_timestamp, t.size,
                   b.session_offset, b.minute_index
            FROM mom.filtered_trades_dev_v4 t
            JOIN mom.event_minute_bars_v2 b
              ON b.ticker = t.ticker AND b.event_date_canonical = t.event_date
             AND b.momentum_pct = t.momentum_pct
             AND t.sip_timestamp >= b.first_trade_ts AND t.sip_timestamp <= b.last_trade_ts
            WHERE t.dev_cohort = 'primary'
        ),
        bar_totals AS (
            SELECT ticker, event_date, momentum_pct, session_offset, minute_index,
                   SUM(size) AS bar_volume, COUNT(*) AS bar_n_trades
            FROM t GROUP BY 1, 2, 3, 4, 5
        )
        SELECT t.ticker, t.event_date, t.momentum_pct, t.session_offset, t.minute_index,
               t.sip_timestamp, t.size, bt.bar_volume, bt.bar_n_trades,
               t.size::DOUBLE / bt.bar_volume AS participation_rate
        FROM t JOIN bar_totals bt USING (ticker, event_date, momentum_pct, session_offset,
                                          minute_index)
        WHERE bt.bar_volume > 0
    """).df()

    n_matched = len(d)
    d["decile"] = pd.qcut(d["participation_rate"], N_DECILES, labels=False, duplicates="drop") + 1
    n_deciles_actual = int(d["decile"].nunique())

    bounds = (d.groupby("decile")["participation_rate"]
              .agg(["min", "max", "median", "count"]).reset_index()
              .rename(columns={"count": "n"}))

    out = {
        "task": "T2", "phase": "impact_by_participation",
        "definition": (
            "participation_rate(print) = print.size / SUM(size) over all trades in the same "
            "(ticker, event_date, momentum_pct, session_offset, minute_index) bar, INCLUSIVE "
            "of the print's own size."
        ),
        "minute_grid_source": "event_minute_bars_v2 (session_offset, minute_index), matched by "
                              "(ticker, event_date, momentum_pct) and sip_timestamp within "
                              "[first_trade_ts, last_trade_ts] of the bar.",
        "dev_table": "filtered_trades_dev_v4 (Phase 11's frozen dev cohort)",
        "n_dev_events": int(n_dev_events),
        "n_prints_total_dev": None,  # filled below
        "n_prints_matched_to_a_bar": int(n_matched),
        "n_deciles_requested": N_DECILES,
        "n_deciles_actual": n_deciles_actual,
        "decile_boundaries": bounds.to_dict("records"),
        "source": "research/impact_by_participation/t2_participation.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t2_participation",
    }
    n_prints_total = con.execute(
        "SELECT COUNT(*) FROM mom.filtered_trades_dev_v4 "
        "WHERE dev_cohort = 'primary'").fetchone()[0]
    out["n_prints_total_dev"] = int(n_prints_total)
    out["match_rate"] = float(n_matched / n_prints_total) if n_prints_total else None

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    d.to_parquet(ARTIFACTS / "t2_participation.parquet", index=False)
    (ARTIFACTS / "t2_participation.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"T2: {n_dev_events} dev events, {n_prints_total:,} prints total, "
          f"{n_matched:,} matched to a minute bar ({out['match_rate']:.2%})")
    print(f"T2: {n_deciles_actual} deciles actually populated (requested {N_DECILES})")
    print(bounds.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
