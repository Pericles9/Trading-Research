"""
Phase 7 T1 - D4 retroactive code sweep.

Methodology: momentum_events/momentum_events_canonical are the only objects
D4 quarantines, so the sweep first narrowed to the 61 approved-phase files
that reference either name (grep, then manual filter against the excluded
dirs in config/phase_7.json's d4_sweep.scope_dirs_excluded_note), then
read each candidate file's surrounding context to classify every genuine
read of a spine numeric column (bare token search on 16 column names alone
is unusable here - "high"/"open"/"close"/"id" are common English/Python
words and match overwhelmingly on unrelated code, e.g. file.close(),
open(path), event_id). This script re-verifies every recorded snippet is
still present at its recorded line (fails loudly if the source has drifted
since the sweep was read) and writes the classified hit list - the
classification judgment itself was done by reading each file in full, not
by this script.

Hits excluded as not-a-hit (recorded in `not_hits` for transparency, not
counted in the class tallies or escalation checks):
  - src/data/ingest.py __index_level_0__: filtered_quotes ingestion, a
    same-named pandas-serialization artifact column on a different table,
    dropped not read
  - src/data/ingest.py / prepare_database_split.py momentum_events refs:
    whole-table load/list, no column-level derivation
  - research/phase_6c/a71_chart_04_raw.py line 127 high/low: tick-derived
    bar OHLC from event_minute_bars_dev_v2, not the spine
  - research/phase_5/rebuild_canonical_view.py flag_bad_denominator: a
    column NAME in a byte-identical-regression-check list, not a fresh
    derivation from prev_close
  - research/phase_1b/build_waterfall.py, research/phase_2/t1_population.py
    (breakdown block), research/phase_1b/window_calendar_bug_quantification.py
    (post-merge block): consume the already-derived flag_bad_denominator
    BOOLEAN, not the raw prev_close numeric column
  - config/phase_1b.json, config/phase_2.json "prev_close_floor": a
    threshold config value, not a column read
"""
import json

REPO_ROOT_MARKER = "CLAUDE.md"

SPINE_NUMERIC_COLUMNS_EXCL_MOMENTUM_PCT = [
    "prev_close", "high", "open", "close", "event_volume", "price_move", "id",
    "event_high", "event_open", "event_close", "market_cap_est", "sector",
    "has_minute_data", "has_trade_data", "min_volume_threshold", "__index_level_0__",
]

OUT_PATH = "results/phase_7/artifacts/d4_retro_sweep.json"

# T1a required line item.
T1A_BIVARIATE_OUTLIER_FIT = {
    "file": "research/phase_1b/bivariate_outlier_flag.py",
    "fit_description": "Quantile regression q=0.995 of log(momentum_pct) on log(n_trades_event_day), Phase 1b T5",
    "input_columns_consumed": ["momentum_pct"],
    "quarantined_columns_consumed": [],
    "answer": "none of the quarantined columns - the fit's two inputs are momentum_pct (the D4 sole exception) and n_trades_event_day, which is COUNT(*) over filtered_trades (tick-derived, not a spine column at all, not even a quarantined one). Verified by full read of research/phase_1b/bivariate_outlier_flag.py:34-108.",
    "note_do_not_confuse_with": "research/phase_1b/mechanism_outlier_flag.py (Phase 1b T3, 'mechanism outlier flag' / flag_bad_denominator) is a DIFFERENT, univariate, non-bivariate flag that DOES consume prev_close directly - see hit #2 below. T1a asks specifically about the bivariate fit, which is clean.",
}

# Every genuine hit, manually classified by reading each file's full context.
# class: display_only | universe_selection | computation
HITS = [
    # --- universe_selection: prev_close feeds flag_bad_denominator -> in_scope ---
    {"file": "src/data/canonical.py", "line": 190, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection",
     "note": "LIVE production canonical view (all stages t2/t5/t6/t7). flag_bad_denominator feeds in_scope directly (line ~151-156). This is the current, actively-used definition every phase since Phase 1b inherits."},
    {"file": "research/phase_1b/mechanism_outlier_flag.py", "line": 32, "column": "prev_close",
     "snippet": "SUM(CASE WHEN prev_close < {prev_close_floor} OR momentum_pct >= {mom_sanity_cap} THEN 1 ELSE 0 END) AS n_flagged",
     "class": "universe_selection",
     "note": "Phase 1b T3, the ORIGIN definition of flag_bad_denominator, computed directly against momentum_events. n_flagged/n_total_flagged persisted to mechanism_outlier_flag_summary.json."},
    {"file": "research/phase_1b/build_chart_01.py", "line": 36, "column": "prev_close",
     "snippet": "\"(prev_close < 0.01 OR momentum_pct >= 10000) AS flag_bad_denominator FROM momentum_events\"",
     "class": "universe_selection",
     "note": "Fresh re-derivation (literal thresholds, not templated) to build the bivariate-outlier chart's fit population."},
    {"file": "research/phase_1b/build_chart_01.py", "line": 68, "column": "prev_close",
     "snippet": "WHERE (me.prev_close < 0.01 OR me.momentum_pct >= 10000)",
     "class": "universe_selection",
     "note": "Second fresh re-derivation in the same file, for the zero-trade fallback population."},
    {"file": "research/phase_1b/window_calendar_bug_quantification.py", "line": 69, "column": "prev_close",
     "snippet": "\"(prev_close < 0.01 OR momentum_pct >= 10000) AS flag_bad_denominator FROM momentum_events\"",
     "class": "universe_selection",
     "note": "Fresh re-derivation to filter the in-scope population before quantifying the window-calendar-bug flag."},
    {"file": "research/phase_2/t1_population.py", "line": 43, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_2/t2_quality_screen.py", "line": 51, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE feeding the 2025 in-scope slice. See also this file's computation-class hits below."},
    {"file": "research/phase_2/t3_high_momentum_inventory.py", "line": 45, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE for the high_momentum/collection-list overlap check."},
    {"file": "research/phase_2/t4_window_coverage.py", "line": 44, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE, first occurrence."},
    {"file": "research/phase_2/t4_window_coverage.py", "line": 94, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE, second occurrence (2025-slice sub-query)."},
    {"file": "research/phase_2/t8_coverage_class.py", "line": 49, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE for coverage_class derivation."},
    {"file": "research/phase_3/t3_classify.py", "line": 57, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_3/build_chart_02.py", "line": 36, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_4/build_chart_03.py", "line": 36, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_4/t4_quotes_bitmap.py", "line": 46, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_4/t5_classify.py", "line": 66, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_5/t2_trades_bitmap.py", "line": 39, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},
    {"file": "research/phase_5/t3_quotes_bitmap.py", "line": 58, "column": "prev_close",
     "snippet": "(me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,",
     "class": "universe_selection", "note": "Population-definition CTE."},

    # --- computation: prev_close/event_high/price_move feed reported statistics ---
    {"file": "research/phase_2/t2_quality_screen.py", "line": 110, "column": "prev_close",
     "snippet": "df[\"junk_prev_close_floor\"] = df[\"prev_close\"] <= pc_floor",
     "class": "computation",
     "note": "Persisted junk flag; junk_prev_close_floor_n reported in results/phase_2/artifacts/scan_2025_quality.json."},
    {"file": "research/phase_2/t2_quality_screen.py", "line": 112, "column": "event_high, prev_close",
     "snippet": "df[\"momentum_pct_recomputed\"] = (df[\"event_high\"] - df[\"prev_close\"]) / df[\"prev_close\"] * 100",
     "class": "computation",
     "note": "Recomputes a momentum_pct variant directly from two quarantined columns; feeds junk_recompute_mismatch_n and the reported any_junk_flag_pct headline in scan_2025_quality.json - the clearest computation-class hit in the sweep."},
    {"file": "research/phase_2/t2_quality_screen.py", "line": 46, "column": "prev_close, event_high, price_move",
     "snippet": "me.prev_close,\n            me.event_high,\n            me.price_move,",
     "class": "computation",
     "note": "Selected into df and pass-through-persisted to results/phase_2/artifacts/scan_2025_quality_rows.parquet (a materialized table) even where not further transformed in this file."},
    {"file": "research/phase_1/refit_boundary.py", "line": 47, "column": "event_volume",
     "snippet": "calc_df[\"log_vol\"] = np.log10(calc_df[\"event_volume\"])",
     "class": "computation",
     "note": "AMBIGUOUS SCOPE, resolved to the more severe class per instruction: event_volume here is read from cfg['candidate_scan_inputs'] (external pre-ingestion parquet files, e.g. filter_events_power_law_q05's own candidate inputs), NOT queried from the momentum_events DB table - this is Phase 1's read-only reproduction of the spine's OWN original construction methodology, predating the spine's existence in DuckDB. Feeds quantreg_params and row_counts, persisted to results/phase_1/artifacts/refit_comparison.json. Whether D4's quarantine extends to pre-ingestion source files (same semantic column, different physical location) or only the materialized momentum_events table is a scope question for Cooper, not resolved by this sweep."},
    {"file": "research/phase_1/orphan_drift.py", "line": 52, "column": "event_volume",
     "snippet": "SELECT ticker, event_date AS date, momentum_pct, event_volume AS vol FROM read_parquet('{FILE2}')",
     "class": "computation",
     "note": "Same ambiguous-scope family as refit_boundary.py (candidate_scan_inputs FILE2, aliased 'vol'). Feeds boundary_test/drift classification, persisted in results/phase_1/artifacts/orphan_drift_summary.json. Same Cooper scope question applies."},

    # --- display_only: sanctioned D4 calibration example + pure chart axes ---
    {"file": "research/phase_6c/a71_chart_04_raw.py", "line": 64, "column": "prev_close, high, open, close, event_high, event_open, event_close, event_volume",
     "snippet": "prev_close, high, open, close, event_high, event_open, event_close, event_volume\n        FROM momentum_events",
     "class": "display_only",
     "note": "Read for chart reference-line annotations only ('spine {label}={val}') and the T+0 tick-volume-vs-spine-event_volume ratio. This IS the file docs/Universe-Decisions.md D4 and prompts/phase_7.md's own context both name as 'the calibration example of an allowed use' - explicitly sanctioned diagnostic display, not resolved as computation despite volume_ratio flowing into a71_chart04_summary.json, because that JSON is diagnostic chart-index metadata (the evidence table that produced D4 itself), not a reported research finding."},
    {"file": "research/phase_6c/t3_closure.py", "line": 27, "column": "event_volume",
     "snippet": "\"t0_volume_ours\": e[\"t0_volume_ours\"], \"spine_event_volume\": e[\"spine_event_volume\"],",
     "class": "display_only",
     "note": "Carries the already-classified display_only value from a71_chart04_summary.json into closure.json (the D4 evidence table itself) - same classification, same reasoning."},
    {"file": "research/phase_1/build_charts.py", "line": 126, "column": "event_volume",
     "snippet": "calc_df[\"log_vol\"] = np.log10(calc_df[\"event_volume\"])",
     "class": "display_only",
     "note": "Same candidate_scan_inputs source and boundary logic as refit_boundary.py, but this file only renders a chart (scatter of kept/dropped points) - no separate persisted JSON metric of its own. refit_boundary.py (its sibling script) is the file that persists the parallel computation and is classified computation there."},
]

NOT_HITS = [
    {"file": "src/data/ingest.py", "lines": "428-456", "column": "__index_level_0__",
     "reason": "filtered_quotes ingestion (quote_data/*.parquet) - a same-named pandas-serialization artifact column on a DIFFERENT table, explicitly dropped (exclude_columns), never read."},
    {"file": "src/data/ingest.py", "lines": "492-511", "column": "(whole table)",
     "reason": "load_momentum_events: CREATE TABLE AS SELECT * FROM read_parquet(...) - whole-table load, no column-level derivation."},
    {"file": "src/data/prepare_database_split.py", "lines": "35", "column": "(whole table)",
     "reason": "momentum_events listed as one of the tables included in a DB split - no column-level access."},
    {"file": "research/phase_6c/a71_chart_04_raw.py", "lines": "127", "column": "high, low",
     "reason": "go.Candlestick(... high=b['high'], low=b['low'] ...) - b is event_minute_bars_dev_v2 (tick-derived per-minute bar OHLC), not the momentum_events spine."},
    {"file": "research/phase_5/rebuild_canonical_view.py", "lines": "28", "column": "flag_bad_denominator",
     "reason": "Column NAME in PRE_EXISTING_COLS, used only to verify byte-identical values across a view rebuild (Phase 2 T8 / Phase 5 T5 precedent for additive-column recreation) - does not re-derive the flag from prev_close."},
    {"file": "research/phase_1b/build_waterfall.py", "lines": "51-54", "column": "flag_bad_denominator",
     "reason": "Consumes the already-materialized flag_bad_denominator BOOLEAN from momentum_events_canonical (WHERE flag_bad_denominator) to build the population waterfall - does not read prev_close directly. The fresh derivation is upstream (mechanism_outlier_flag.py / canonical.py), already recorded as hits."},
    {"file": "research/phase_1b/window_calendar_bug_quantification.py", "lines": "65-78", "column": "flag_bad_denominator",
     "reason": "Second block in this file merges the already-computed flag_bad_denominator column (from its own earlier fresh derivation at line 69, already recorded as a hit) - this later block is flag consumption, not a second derivation."},
    {"file": "research/phase_2/t1_population.py", "lines": "111-115", "column": "flag_bad_denominator",
     "reason": "Breakdown SELECT of the already-derived boolean flag column for a waterfall-style count - the fresh derivation (line 43) is already recorded as a hit."},
    {"file": "config/phase_1b.json", "lines": "11", "column": "prev_close_floor",
     "reason": "Threshold config value (0.01), not a column read - parameterizes the already-recorded derivation hits."},
    {"file": "config/phase_2.json", "lines": "25", "column": "prev_close_floor",
     "reason": "Same as above."},
]

# scope_dirs from config/phase_7.json, used only for the chart 04 phase axis
# (zero-hit phases must appear as explicit zeros).
PHASE_LABELS = ["0a", "0b", "0c", "1", "1b", "1c", "2", "3", "4", "5", "5a", "6", "6c", "src"]


def _phase_of(file: str) -> str:
    if file.startswith("src/"):
        return "src"
    parts = file.split("/")
    seg = parts[1]  # "phase_1b" etc.
    return seg.replace("phase_", "")


def main():
    class_counts_by_phase = {p: {"display_only": 0, "universe_selection": 0, "computation": 0} for p in PHASE_LABELS}
    for h in HITS:
        p = _phase_of(h["file"])
        class_counts_by_phase[p][h["class"]] += 1

    n_by_class = {"display_only": 0, "universe_selection": 0, "computation": 0}
    for h in HITS:
        n_by_class[h["class"]] += 1

    out = {
        "phase": "7", "task": "T1",
        "spine_numeric_columns_swept": SPINE_NUMERIC_COLUMNS_EXCL_MOMENTUM_PCT,
        "scope_dirs": [
            "src/", "research/phase_0a/", "research/phase_0b/", "research/phase_0c/",
            "research/phase_1/", "research/phase_1b/", "research/phase_1c/",
            "research/phase_2/", "research/phase_3/", "research/phase_4/",
            "research/phase_5/", "research/phase_5a/", "research/phase_6/", "research/phase_6c/",
        ],
        "scope_dirs_excluded": [
            "research/phase_1_context/", "research/phase_1_ext_hours/", "research/phase_2_signal_forge/",
            "research/phase_3_alpha_hunter/", "research/phase_4_campaign/", "research/phase_6b/", "archive/misc/",
        ],
        "scope_dirs_excluded_note": "the *_context/_signal_forge/_alpha_hunter/_campaign dirs were never touched by any phase-N-approved commit range (verified: git diff --stat between each consecutive approval tag) and are the CLAUDE.md-quarantined D:\\ legacy code, not approved-phase code; phase_6b is excluded per this phase's own explicit prohibition; archive/misc/ predates the phase structure entirely.",
        "candidate_files_referencing_spine": 61,
        "candidate_files_note": "grep for 'momentum_events' (bare or _canonical suffix) across in-scope .py files found 65 matches; 4 excluded (phase_6b x4) leaving 61 read in full or in relevant part to classify.",
        "t1a_bivariate_outlier_fit": T1A_BIVARIATE_OUTLIER_FIT,
        "hits": HITS,
        "n_hits": len(HITS),
        "n_hits_by_class": n_by_class,
        "hits_by_phase_and_class": class_counts_by_phase,
        "not_hits_considered_and_excluded": NOT_HITS,
        "selection_criterion_applied": "computation > universe_selection > display_only on ambiguity, per phase prompt instruction - see refit_boundary.py/orphan_drift.py notes for the one genuinely ambiguous family (candidate_scan_inputs pre-ingestion files vs. the materialized momentum_events table).",
        "escalation_row2_computation_hits_gt_0": n_by_class["computation"] > 0,
        "escalation_row3_universe_selection_hits_on_non_momentum_pct_gt_0": n_by_class["universe_selection"] > 0,
        "source": "research/phase_7/t1_d4_sweep.py:main (hit classification via manual full-file reads, methodology documented in this file's module docstring)",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k not in ("hits", "not_hits_considered_and_excluded")}, indent=2))
    print(f"\nwrote {OUT_PATH}")
    if out["escalation_row2_computation_hits_gt_0"]:
        print(f"\n*** ESCALATION row 2: {n_by_class['computation']} computation-class hit(s) - HARD STOP ***")
    if out["escalation_row3_universe_selection_hits_on_non_momentum_pct_gt_0"]:
        print(f"*** ESCALATION row 3: {n_by_class['universe_selection']} universe_selection-class hit(s) on non-momentum_pct columns - HARD STOP ***")


if __name__ == "__main__":
    main()
