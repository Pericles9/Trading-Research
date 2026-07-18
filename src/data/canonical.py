"""momentum_events_canonical view definition.

Phase 1b, instructed promotion to src/ (Cooper decision D1/D2). This is a
VIEW over the raw `momentum_events` table - the raw table is never
modified. Downstream code must join to this view WHERE in_scope = TRUE
rather than aggregating filtered_trades/filtered_quotes directly; the
physical tables contain out-of-universe rows (non-common instruments,
genuine orphan-folder events, outlier-flagged events).

Coverage is per-side (Amendment 2, T4-R1): trades_ingested and
quotes_ingested are computed independently from filtered_trades and
filtered_quotes respectively. in_scope does not depend on either -
missing quote coverage is a recorded fact (~1,540 folders have a
trades.parquet but no quotes.parquet on disk), not an eligibility veto.
Any quote-derived statistic downstream must filter on
quotes_ingested = TRUE explicitly and report the n excluded.

Built in three stages, matching the order Phase 1b computes its inputs:
  - stage="t2": flag_bad_denominator computed directly (simple, static
    formula over raw columns); flag_trades_mom_outlier and in_scope are
    NULL placeholders.
  - stage="t5": adds flag_trades_mom_outlier and flag_zero_event_day_trades
    from event_flags.parquet (T5's output). in_scope still NULL.
  - stage="t6": in_scope gets its final formula (D5 + D4 combined).

Callers re-run create_view() with the later stage once the corresponding
artifact exists; DuckDB views are cheap to redefine (no data migration).

Path convention: all artifact paths are resolved absolute from
PROJECT_ROOT (src/data/paths.py) and embedded literally into the view's
SQL text, so the view resolves correctly regardless of the caller's
working directory.
"""
from __future__ import annotations

import json

import duckdb

from src.data.paths import PROJECT_ROOT

FOLDER_INVENTORY_PATH = PROJECT_ROOT / "results" / "phase_0c" / "artifacts" / "folder_inventory.parquet"
CLASSIFICATION_PATH = PROJECT_ROOT / "results" / "phase_1b" / "artifacts" / "instrument_classification.parquet"
EVENT_FLAGS_PATH = PROJECT_ROOT / "results" / "phase_1b" / "artifacts" / "event_flags.parquet"
CONFIG_PATH = PROJECT_ROOT / "config" / "phase_1b.json"

IN_SCOPE_CLASSES = ("common", "common_adr")


def _p(path) -> str:
    return str(path).replace("\\", "/")


def _load_thresholds() -> tuple[float, float]:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    flags = cfg["outlier_flags"]
    return flags["prev_close_floor"], flags["mom_sanity_cap"]


def create_view(
    con: duckdb.DuckDBPyConnection,
    stage: str = "t2",
    prev_close_floor: float | None = None,
    mom_sanity_cap: float | None = None,
) -> None:
    """Create or replace momentum_events_canonical for the given stage."""
    if prev_close_floor is None or mom_sanity_cap is None:
        cfg_floor, cfg_cap = _load_thresholds()
        prev_close_floor = prev_close_floor if prev_close_floor is not None else cfg_floor
        mom_sanity_cap = mom_sanity_cap if mom_sanity_cap is not None else cfg_cap

    folder_inv = _p(FOLDER_INVENTORY_PATH)
    classification = _p(CLASSIFICATION_PATH)
    event_flags = _p(EVENT_FLAGS_PATH)

    if stage == "t2":
        flag_trades_mom_outlier_expr = "CAST(NULL AS BOOLEAN)"
        flag_zero_trades_join = ""
        in_scope_expr = "CAST(NULL AS BOOLEAN)"
    elif stage in ("t5", "t6"):
        flag_trades_mom_outlier_expr = "ef.flag_trades_mom_outlier"
        flag_zero_trades_join = f"""
        LEFT JOIN read_parquet('{event_flags}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
        """
        if stage == "t5":
            in_scope_expr = "CAST(NULL AS BOOLEAN)"
        else:  # t6
            in_scope_expr = f"""(
                ic.class IN {IN_SCOPE_CLASSES}
                AND NOT COALESCE(flag_bad_denominator, FALSE)
                AND NOT COALESCE(ef.flag_trades_mom_outlier, FALSE)
                AND NOT COALESCE(ef.flag_zero_event_day_trades, FALSE)
            )"""
    else:
        raise ValueError(f"unknown stage: {stage!r}")

    sql = f"""
    CREATE OR REPLACE VIEW momentum_events_canonical AS
    SELECT
        me.ticker,
        COALESCE(me.date, me.event_date) AS event_date_canonical,
        me.momentum_pct,
        CASE
            WHEN me.date IS NOT NULL THEN 'file1'
            WHEN me.event_date IS NOT NULL THEN 'file2'
        END AS source_file,
        ic.class AS instrument_class,
        ic.vendor_type AS vendor_type,
        (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
        {flag_trades_mom_outlier_expr} AS flag_trades_mom_outlier,
        EXISTS (
            SELECT 1 FROM read_parquet('{folder_inv}') fi
            WHERE fi.ticker = me.ticker
              AND fi.date_is_none = FALSE
              AND fi.date = CAST(COALESCE(me.date, me.event_date) AS VARCHAR)
              AND ROUND(TRY_CAST(fi.momentum_str AS DOUBLE), 2) = ROUND(me.momentum_pct, 2)
        ) AS has_folder,
        (ft_distinct.ticker IS NOT NULL) AS trades_ingested,
        (fq_distinct.ticker IS NOT NULL) AS quotes_ingested,
        {in_scope_expr} AS in_scope
    FROM momentum_events me
    LEFT JOIN read_parquet('{classification}') ic ON me.ticker = ic.ticker
    LEFT JOIN (
        SELECT DISTINCT ticker, event_date, ROUND(momentum_pct, 2) AS mom_2dp
        FROM filtered_trades
    ) ft_distinct
      ON me.ticker = ft_distinct.ticker
     AND COALESCE(me.date, me.event_date) = ft_distinct.event_date
     AND ROUND(me.momentum_pct, 2) = ft_distinct.mom_2dp
    LEFT JOIN (
        SELECT DISTINCT ticker, event_date, ROUND(momentum_pct, 2) AS mom_2dp
        FROM filtered_quotes
    ) fq_distinct
      ON me.ticker = fq_distinct.ticker
     AND COALESCE(me.date, me.event_date) = fq_distinct.event_date
     AND ROUND(me.momentum_pct, 2) = fq_distinct.mom_2dp
    {flag_zero_trades_join}
    """
    con.execute(sql)
