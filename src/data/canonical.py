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

flag_missing_event_day (Amendment 3, T5-R2) = zero trades on the event's
own calendar day, regardless of cause (calendar_bug or unknown) -
excluded from in_scope, pending Phase 1c repair. flag_window_calendar_bug
(Amendment 3, T5-R3) = the event's T-3..T+3 window has session-shape
damage from the same collector bug - these events stay IN scope for
event-day work; the flag governs use of flanking sessions, not
membership. Any analysis touching flanking sessions must filter on
flag_window_calendar_bug = FALSE and report the n excluded.

repaired_1c (Phase 1c, T7) = TRUE where a heal fetch was ingested and
verified for that event (see filtered/{event}/*_repair_1c.parquet sibling
files and results/phase_1c/artifacts/repair_ledger.parquet - the record of
what was healed and how; never re-derive by re-querying the vendor API).
Both flag columns above are cleared by Phase 1c where the event's gap was
successfully healed; a small residual of each flag remains TRUE where the
heal fetch failed (results/phase_1c/artifacts/t4_fetch_run_summary.json).

coverage_class (Phase 2, T8) = 'full_window' where all 7 of the event's
XNYS T-3..T+3 offsets are present in filtered_trades (post-1c heal),
else 'event_day_only'. quotes_full_window (Phase 2, T8) = same logic off
filtered_quotes, boolean. Both are additive, non-destructive flags - same
rule as flag_bad_denominator/in_scope: nothing is deleted, coverage_class
governs which population counts as the "full_window" primary analysis
set, not spine membership. Source: results/phase_2/t8_coverage_class.py,
results/phase_2/artifacts/coverage_class.parquet (one row per in-scope
event; NULL for any event not in_scope). Cooper's T8 gate decision: 2025
events are retained in the spine (in_scope unchanged) but excluded from
the full_window primary population - nearly all of them land in
event_day_only (results/phase_2/REPORT.md addendum).

Built in three stages, matching the order Phase 1b computes its inputs:
  - stage="t2": flag_bad_denominator computed directly (simple, static
    formula over raw columns); flag_trades_mom_outlier and in_scope are
    NULL placeholders.
  - stage="t5": adds flag_trades_mom_outlier, flag_missing_event_day, and
    flag_window_calendar_bug from event_flags.parquet (T5's output).
    in_scope still NULL.
  - stage="t6": in_scope gets its final formula (D5 + D4 + Amendment 3
    combined).

Callers re-run create_view() with the later stage once the corresponding
artifact exists; DuckDB views are cheap to redefine (no data migration).

Path convention: all artifact paths are resolved absolute from
PROJECT_ROOT (src/data/paths.py) and embedded literally into the view's
SQL text, so the view resolves correctly regardless of the caller's
working directory.

stage="t7" (Phase 5, T5): additive window-flag finalization. Left-joins
results/phase_5/artifacts/spine_window_flags.parquet (one row per
in_scope event, both source files - see research/phase_5/t4_derive_flags.py)
on (ticker, event_date_canonical, ROUND(momentum_pct,2)), adding
trades_full_window, clean_window, trades_gap_label, quotes_gap_label,
trades_bitmap, quotes_bitmap. Does NOT re-add quotes_full_window - that
column already exists on the view from stage="t6"'s coverage_class join
(Phase 2 T8) and was verified byte-identical to spine_window_flags'
independently-recomputed quotes_full_window across all 20,951 in-scope
events (0 mismatches, Phase 5 T5 decisions log) before this stage was
written, so adding a second column of the same name was skipped rather
than creating an ambiguous duplicate. trades_full_window is genuinely
new (stage="t6" only carries the trades side as the coverage_class
string, not a same-shaped boolean). Escalation row 4's file2-flagged-
share finding (Phase 5 Amendment 4) does not change this stage's SQL -
flag-and-carry applies uniformly to both source files.
"""
from __future__ import annotations

import json

import duckdb

from src.data.paths import PROJECT_ROOT

FOLDER_INVENTORY_PATH = PROJECT_ROOT / "results" / "phase_0c" / "artifacts" / "folder_inventory.parquet"
CLASSIFICATION_PATH = PROJECT_ROOT / "results" / "phase_1b" / "artifacts" / "instrument_classification.parquet"
EVENT_FLAGS_PATH = PROJECT_ROOT / "results" / "phase_1b" / "artifacts" / "event_flags.parquet"
CONFIG_PATH = PROJECT_ROOT / "config" / "phase_1b.json"
COVERAGE_CLASS_PATH = PROJECT_ROOT / "results" / "phase_2" / "artifacts" / "coverage_class.parquet"
SPINE_WINDOW_FLAGS_PATH = PROJECT_ROOT / "results" / "phase_5" / "artifacts" / "spine_window_flags.parquet"

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
    coverage_class = _p(COVERAGE_CLASS_PATH)
    spine_window_flags = _p(SPINE_WINDOW_FLAGS_PATH)

    if stage == "t2":
        flag_trades_mom_outlier_expr = "CAST(NULL AS BOOLEAN)"
        flag_missing_event_day_expr = "CAST(NULL AS BOOLEAN)"
        flag_window_calendar_bug_expr = "CAST(NULL AS BOOLEAN)"
        repaired_1c_expr = "CAST(NULL AS BOOLEAN)"
        flag_zero_trades_join = ""
        in_scope_expr = "CAST(NULL AS BOOLEAN)"
    elif stage in ("t5", "t6", "t7"):
        flag_trades_mom_outlier_expr = "ef.flag_trades_mom_outlier"
        flag_missing_event_day_expr = "COALESCE(ef.flag_missing_event_day, FALSE)"
        flag_window_calendar_bug_expr = "COALESCE(ef.flag_window_calendar_bug, FALSE)"
        repaired_1c_expr = "COALESCE(ef.repaired_1c, FALSE)"
        flag_zero_trades_join = f"""
        LEFT JOIN read_parquet('{event_flags}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
        """
        if stage == "t5":
            in_scope_expr = "CAST(NULL AS BOOLEAN)"
        else:  # t6, t7 - final in_scope formula unchanged by t7
            in_scope_expr = f"""(
                ic.class IN {IN_SCOPE_CLASSES}
                AND NOT COALESCE(flag_bad_denominator, FALSE)
                AND NOT COALESCE(ef.flag_trades_mom_outlier, FALSE)
                AND NOT COALESCE(ef.flag_missing_event_day, FALSE)
            )"""
    else:
        raise ValueError(f"unknown stage: {stage!r}")

    if stage == "t7":
        window_flags_join = f"""
    LEFT JOIN read_parquet('{spine_window_flags}') swf
      ON me.ticker = swf.ticker
     AND COALESCE(me.date, me.event_date) = swf.event_date_canonical
     AND ROUND(me.momentum_pct, 2) = swf.momentum_pct
        """
        window_flags_cols = """,
        swf.trades_full_window AS trades_full_window,
        swf.clean_window AS clean_window,
        swf.trades_gap_label AS trades_gap_label,
        swf.quotes_gap_label AS quotes_gap_label,
        swf.trades_bitmap AS trades_bitmap,
        swf.quotes_bitmap AS quotes_bitmap"""
    else:
        window_flags_join = ""
        window_flags_cols = ""

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
        {flag_missing_event_day_expr} AS flag_missing_event_day,
        {flag_window_calendar_bug_expr} AS flag_window_calendar_bug,
        {repaired_1c_expr} AS repaired_1c,
        EXISTS (
            SELECT 1 FROM read_parquet('{folder_inv}') fi
            WHERE fi.ticker = me.ticker
              AND fi.date_is_none = FALSE
              AND fi.date = CAST(COALESCE(me.date, me.event_date) AS VARCHAR)
              AND ROUND(TRY_CAST(fi.momentum_str AS DOUBLE), 2) = ROUND(me.momentum_pct, 2)
        ) AS has_folder,
        (ft_distinct.ticker IS NOT NULL) AS trades_ingested,
        (fq_distinct.ticker IS NOT NULL) AS quotes_ingested,
        {in_scope_expr} AS in_scope,
        cc.coverage_class AS coverage_class,
        cc.quotes_full_window AS quotes_full_window{window_flags_cols}
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
    LEFT JOIN read_parquet('{coverage_class}') cc
      ON me.ticker = cc.ticker
     AND COALESCE(me.date, me.event_date) = cc.event_date_canonical
     AND ROUND(me.momentum_pct, 2) = ROUND(cc.momentum_pct, 2)
    {flag_zero_trades_join}
    {window_flags_join}
    """
    con.execute(sql)
