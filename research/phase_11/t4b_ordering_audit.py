"""T4b - reverse-chronological latent-error audit (Amendment 2 A2-1).

Read-only, code only. No data touched, no pass spent.

T1c-v established the source parquet is stored reverse chronological. Phase 11
itself is immune (every query sorts explicitly), but it reuses Phase 6b/8/9
artifacts FROZEN. If any code path that produced them treated file order as
chronological, Phase 11 inherits the error silently.

Classification per A2-1 T4b-ii:
  (a) cannot affect an artifact Phase 11 reuses frozen
  (b) could affect one
  (c) does affect one
Any (b) or (c) is escalation row 25 - hard stop.
"""
from __future__ import annotations

import json
import pathlib

FROZEN = {
    "a102_detection_anchors.parquet": "det_minute, det_segment, det_price_lat{0,1,5,15,30}, "
                                      "day_high_ext, era, runway (T6, T7)",
    "t3_participation.parquet": "pq_rth_open (T6c)",
    "t4_axis_grid.parquet": "realized capture at the matching fixed horizon (T7b-ii)",
    "t1_cross_session_flags.parquet": "flag_cross_session_extreme (T7e)",
    "a101_labels.parquet": "flag_possible_row_cap (T7e)",
    "event_index_v2.parquet": "flag_has_dup_prints (T7e)",
    "quotes_bitmaps_all.parquet": "quotes_ingested (D15)",
    "_actual_quotes_sessions_cache.parquet": "quotes session coverage (D15)",
    "event_minute_bars_v2": "upstream of a102, t3_participation, t4_axis_grid",
    "opportunity_decay_primary.parquet": "tick_close_t_minus_1_rth, day_high_ext, upstream of a102",
}

HITS = [
    {"location": "research/phase_6b/build_minute_bars_v2.py:98-99",
     "pattern": "per-minute first_price / last_price aggregation",
     "code": "arg_min(price, sip_timestamp) AS first_price, "
             "arg_max(price, sip_timestamp) AS last_price",
     "reaches": "event_minute_bars_v2 -> a102_detection_anchors, t3_participation, "
                "t4_axis_grid, opportunity_decay_primary",
     "classification": "a",
     "why": "THE LOAD-BEARING CHECK. Both use an EXPLICIT ordering key (sip_timestamp) "
            "rather than row order. high/low are MAX/MIN(price) and first/last_trade_ts "
            "are MIN/MAX(sip_timestamp) - all order-independent aggregates. A "
            "reverse-chronological file yields byte-identical bars."},

    {"location": "research/phase_6b/measurements_v2.py:96",
     "pattern": "positional ops (.iloc[0], _first_crossing) on a grouped frame",
     "code": "g = grid.sort_values([\"event_id\", \"minute_index\"]).copy()",
     "reaches": "opportunity_decay_primary.parquet -> day_high_ext, "
                "tick_close_t_minus_1_rth",
     "classification": "a",
     "why": "An EXPLICIT sort precedes every positional operation in the function. The "
            "subsequent .iloc[0] calls read anchor / day_high_ext / has_anchor / denom, "
            "which are per-event CONSTANTS broadcast across the event's minute rows, so "
            "they are order-invariant regardless. _first_crossing operates on the sorted "
            "frame."},

    {"location": "research/phase_6b/measurements_v2.py:85",
     "pattern": "last trade at or before the T-1 RTH close",
     "code": "idx = tm1.groupby(EVENT_KEYS)[\"minute_index\"].idxmax()",
     "reaches": "tick_close_t_minus_1_rth -> a102 threshold and day_high_ext denominator",
     "classification": "a",
     "why": "idxmax on minute_index is an explicit argmax, not a positional pick."},

    {"location": "research/phase_8/a102_detection.py:86",
     "pattern": "first T0 minute reaching the 1.30x threshold",
     "code": "MIN(b.minute_index) FILTER (b.high >= t.threshold) AS det_minute",
     "reaches": "a102_detection_anchors.parquet - det_minute, the phase's entry anchor",
     "classification": "a",
     "why": "A filtered MIN aggregate over minute_index. No positional selection, no "
            "dependence on row order."},

    {"location": "research/phase_8/a102_detection.py:123",
     "pattern": "pivot_table(..., aggfunc='first')",
     "code": "wide = priced.pivot_table(index=KEY, columns='lat', values='price', "
             "aggfunc='first')",
     "reaches": "a102_detection_anchors.parquet - det_price_lat{0,1,5,15,30}",
     "classification": "a",
     "why": "`priced` is the output of an ASOF LEFT JOIN keyed on "
            "(ticker, event_date_canonical, mp, lat), which yields exactly ONE row per "
            "cell. aggfunc='first' over a single value is deterministic. Verified: the "
            "committed artifact has 15,763 rows for 15,763 events."},

    {"location": "research/phase_9/t4_axis_grid.py:84-97",
     "pattern": "entry / exit price selection",
     "code": "ASOF LEFT JOIN p9bars b ... AND t.target_minute >= b.minute_index",
     "reaches": "t4_axis_grid.parquet - realized capture, the T7b-ii denominator",
     "classification": "a",
     "why": "ASOF on an explicit minute_index key. No LIMIT, no head, no positional "
            "pick anywhere in the file."},

    {"location": "research/phase_8/t3_participation.py:132",
     "pattern": ".value_counts().iloc[0]",
     "code": "n_tied_at_mode = int(out.loc[mask, f'logrv_{name}'].round(9)"
             ".value_counts().iloc[0])",
     "reaches": "t3_participation.parquet - DIAGNOSTIC field only, not pq_rth_open",
     "classification": "a",
     "why": "value_counts() sorts by count descending, so .iloc[0] is the modal COUNT - "
            "order-independent. It records a tie diagnostic and does not enter "
            "pq_rth_open, which Phase 11 reuses."},

    {"location": "research/phase_4/t2_disk_census.py:107-123",
     "pattern": "session coverage derived from parquet row-group statistics",
     "code": "MIN(TRY_CAST(stats_min_value AS BIGINT)), MAX(TRY_CAST(stats_max_value "
             "AS BIGINT))",
     "reaches": "_actual_quotes_sessions_cache.parquet (D15 source)",
     "classification": "a",
     "why": "Derives the timestamp span from MIN/MAX over row-group STATISTICS. This is "
            "precisely the construction that is immune to storage order - it would give "
            "the same answer on a shuffled file."},

    {"location": "research/phase_4/t2_disk_census.py:82,93",
     "pattern": ".iloc[0] after a filter",
     "code": "row = df[df['file_name'] == f].iloc[0]; r.iloc[0]['num_rows']",
     "reaches": "_actual_quotes_sessions_cache.parquet (D15 source)",
     "classification": "a",
     "why": "Single-row selection after filtering on a unique file name, and a "
            "single-row query result. Not a positional pick over data rows."},

    {"location": "research/phase_5/t3_quotes_bitmap.py:92,158-165",
     "pattern": "coverage bitmap construction",
     "code": "SELECT DISTINCT ticker, event_date, ROUND(momentum_pct,2); "
             "missing_offsets = sorted(k for k, p in present.items() if not p)",
     "reaches": "quotes_bitmaps_all.parquet (D15 source)",
     "classification": "a",
     "why": "Set membership over DISTINCT keys plus a sorted set difference. No row "
            "order enters. The .value_counts().head(10) at line 226 is a summary "
            "printed to the JSON, not a bitmap input."},

    {"location": "src/data/ingest.py:264, 298, 339, 383, 483, 507, 535, 626, 655, 698",
     "pattern": "read_parquet into DuckDB",
     "code": "SELECT <columns> FROM read_parquet('<file>')",
     "reaches": "filtered_trades, filtered_quotes - upstream of everything",
     "classification": "a",
     "why": "Every source read is a FULL-TABLE read with no LIMIT, no head, and no "
            "positional selection. Row order is not preserved as meaning and no "
            "consumer relies on it; every downstream consumer aggregates or joins on "
            "an explicit key."},

    {"location": "src/data/ingest.py:448",
     "pattern": "LIMIT 1",
     "code": "SELECT * FROM parquet_schema('<file>') LIMIT 1",
     "reaches": "nothing - schema probe",
     "classification": "a",
     "why": "Reads the parquet SCHEMA, not data rows. Every row of parquet_schema() for "
            "a given file describes the same file."},

    {"location": "research/phase_6b/t2_dev_pipeline.py:106; "
                 "research/phase_1b/mechanism_outlier_flag.py:44; "
                 "research/phase_1c/volume_reconciliation.py:49; "
                 "research/phase_1b/window_calendar_bug_quantification.py:171",
     "pattern": "LIMIT 5 / LIMIT 10 / LIMIT 1",
     "code": "various",
     "reaches": "dev previews, printed diagnostics, and single-value spine lookups "
                "(momentum_pct / event_volume, which are per-event constants)",
     "classification": "a",
     "why": "None reaches an artifact Phase 11 reuses. The two LIMIT 1 lookups select a "
            "per-event constant column from momentum_events, where every matching row "
            "carries the same value."},

    {"location": "research/phase_8/t2a_eth_split.py:84",
     "pattern": ".iloc[0] on a filtered frame",
     "code": "return float(hit['minute_index'].iloc[0]) if len(hit) else None",
     "reaches": "t2_eth_split.json / t2_eth_split_curves.parquet",
     "classification": "a",
     "why": "Phase 11 reuses neither artifact. Out of scope by artifact, independent of "
            "whether the pick is ordered."},

    {"location": "research/phase_6b/t3_full_pass_v2.py:70,134",
     "pattern": ".iloc[0] on a groupby result",
     "code": "by_offset.loc[by_offset['session_offset'] == 0, 'n_events'].iloc[0]",
     "reaches": "t3_full_pass_v2_summary.json (reporting only)",
     "classification": "a",
     "why": "session_offset is unique in a groupby result, so the filter yields exactly "
            "one row. Reporting figure, not an artifact column."},
]

audit = {
    "task": "T4b", "phase": "11", "date": "2026-08-16",
    "authority": "prompts/phase_11_amendment_2.md A2-1",
    "nature": "Read-only, code only. No data touched, no pass spent, no query run.",
    "motivation": ("T1c-v measured the source parquet as REVERSE CHRONOLOGICAL - "
                   "sip_timestamp decreasing across 99.97% of consecutive file rows at "
                   "the median event, on all 50 dev-primary events. Phase 11 is immune "
                   "(every query sorts explicitly) but reuses Phase 6b/8/9 artifacts "
                   "frozen. This audit asks whether the CODE THAT PRODUCED THEM was."),
    "search_patterns": [
        "LIMIT / FETCH FIRST without a governing ORDER BY",
        ".head( / .first( / .iloc[0] / .iloc[-1] / .values[0] / .tail( on parquet or "
        "table reads",
        "read_parquet where row order is treated as chronological",
        "first_value / last_value without an explicit window ordering",
    ],
    "search_scope": "src/ and every research/phase_*/ committed .py. The "
                    "research/.obsidian/ vendored plugin bundle is excluded - it is not "
                    "pipeline code and matches only on unrelated JS 'limit' parameters.",
    "first_value_last_value_hits": 0,
    "first_value_note": "No first_value or last_value call exists anywhere in the "
                        "pipeline code. The per-minute first/last prices are built with "
                        "arg_min/arg_max on an explicit key instead.",
    "frozen_artifacts_in_scope": FROZEN,
    "hits": HITS,
    "summary": {
        "n_hits": len(HITS),
        "class_a": [h["location"] for h in HITS if h["classification"] == "a"],
        "class_b": [h["location"] for h in HITS if h["classification"] == "b"],
        "class_c": [h["location"] for h in HITS if h["classification"] == "c"],
    },
}
a, b, c = (len(audit["summary"][f"class_{k}"]) for k in "abc")
audit["summary"]["counts"] = {"a": a, "b": b, "c": c}
audit["summary"]["escalation_row_25"] = (
    "DOES NOT FIRE - zero class (b) and zero class (c) hits." if b + c == 0
    else f"FIRES - {b} class (b), {c} class (c).")
audit["summary"]["escalation_row_28"] = (
    "CLEARS - T4b has cleared, so Stage B tasks are authorised." if b + c == 0
    else "Stage B remains barred.")
audit["summary"]["headline"] = (
    "Every ordered quantity Phase 11 inherits is built with an EXPLICIT key - "
    "arg_min/arg_max on sip_timestamp for the minute bars, a filtered MIN over "
    "minute_index for det_minute, ASOF joins on minute_index for every price lookup, "
    "and MIN/MAX over row-group statistics for the D15 coverage sources. None of them "
    "would change if the source files were re-sorted."
    if b + c == 0 else "See class (b)/(c) entries.")

p = pathlib.Path("results/phase_11/artifacts/t4b_ordering_audit.json")
p.write_text(json.dumps(audit, indent=2))
print(f"wrote {p.name}: {len(HITS)} hits -> class a={a}, b={b}, c={c}")
print("row 25:", audit["summary"]["escalation_row_25"])
print("row 28:", audit["summary"]["escalation_row_28"])
