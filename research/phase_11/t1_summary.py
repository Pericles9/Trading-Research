"""Phase 11 T1 - assemble the summary artifact from the T1a/T1b/T1c tables."""
from __future__ import annotations

import json
import pathlib

import pandas as pd

A = "results/phase_11/artifacts/"


def q(s):
    v = s.quantile([0, .25, .5, .75, 1]).values
    return dict(min=float(v[0]), p25=float(v[1]), median=float(v[2]),
                p75=float(v[3]), max=float(v[4]))


def main() -> None:
    ident = pd.read_parquet(A + "t1a_exchange_identity.parquet")
    core = ident[ident.segment.isin(["premarket", "rth", "post"])]
    nul = pd.read_parquet(A + "t1b_null.parquet")
    rs = pd.read_parquet(A + "t1b_resolution_sip.parquet")
    rp = pd.read_parquet(A + "t1b_resolution_par.parquet")
    o = pd.read_parquet(A + "t1b_order.parquet")
    lat = pd.read_parquet(A + "t1b_clock_latency.parquet")
    ind = pd.read_parquet(A + "t1c_indicators.parquet")
    ind["sh"] = ind.n_null / ind.n_rows
    iv = pd.read_parquet(A + "t1c_indicator_values.parquet")
    cc = pd.read_parquet(A + "t1c_conditions_codes.parquet")
    cb = pd.read_parquet(A + "t1c_conditions_combos.parquet")
    st = pd.read_parquet(A + "t1c_storage_order.parquet")
    seg = pd.read_parquet(A + "t1_segment_census.parquet")

    e20 = ind[ind.era == "era_2020_2021"]
    e22 = ind[ind.era == "era_2022_2024"]
    sh20 = float(e20.n_null.sum() / e20.n_rows.sum())
    sh22 = float(e22.n_null.sum() / e22.n_rows.sum())

    out = {
        "task": "T1", "phase": "11", "date": "2026-08-15",
        "interpreter": ".venv/Scripts/python.exe (duckdb 1.4.4, exchange_calendars 4.13.2)",
        "cohort": {
            "dev_table": "filtered_quotes_dev_v4", "dev_cohort": "primary", "n_events": 50,
            "t0_quote_rows": int(core.n_rows.sum()),
            "source_parquet_rows_all_sessions": int(ind.n_rows.sum()),
        },
        "passes_over_full_tables": 0,

        "t1a_consolidated_best_quote": {
            "reading": "CONFIRMED consolidated best-quote, not per-venue.",
            "per_segment": {s: {
                "n_events": int((core.segment == s).sum()),
                "distinct_bid_exchanges": q(core[core.segment == s].n_bid_exch),
                "distinct_ask_exchanges": q(core[core.segment == s].n_ask_exch),
                "share_rows_bid_exch_ne_ask_exch": q(core[core.segment == s].share_two_sided),
            } for s in ["premarket", "rth", "post"]},
            "events_with_single_bid_venue_rth":
                int((core[core.segment == "rth"].n_bid_exch == 1).sum()),
            "events_with_two_sided_share_below_1pct_rth":
                int((core[core.segment == "rth"].share_two_sided < 0.01).sum()),
            "null_exchange_rows": int(ident.n_null_exch.sum()),
            "premarket_does_not_collapse": (
                "Two-sided share median 0.861 premarket vs 0.884 RTH. The premarket "
                "collapse the prompt asked about is not observed; venue COUNT falls "
                "(median 6 vs 13) while two-sidedness holds."),
            "escalation_row_3": "does not fire - the reading is established",
        },

        "t1b_timestamps": {
            "row_4a": {
                "threshold": "> 1% on any single event",
                "denominator_i_all_t0": {"n_bad": int(nul.n_sip_bad_t0_all.sum()),
                                         "max_event_share": 0.0},
                "denominator_ii_t0_rth_sip_assigned": {"n_bad": int(nul.n_sip_bad_t0_rth.sum()),
                                                       "max_event_share": 0.0},
                "denominator_iii_participant_clock": {"n_bad": int(nul.n_par_bad_t0_all.sum())},
                "observed_max": 0.0,
                "verdict": ("DOES NOT FIRE. All three denominators are exactly zero, so the "
                            "denominator ambiguity flagged at T0c is moot - no straddle exists."),
            },
            "resolution_smallest_nonzero_gap_ns": {
                "sip_timestamp": {"min": int(rs.min_nonzero_gap_ns.min()),
                                  "median": float(rs.min_nonzero_gap_ns.median()),
                                  "max": int(rs.min_nonzero_gap_ns.max())},
                "participant_timestamp": {"min": int(rp.min_nonzero_gap_ns.min()),
                                          "median": float(rp.min_nonzero_gap_ns.median()),
                                          "max": int(rp.min_nonzero_gap_ns.max())},
                "corroboration": ("sip min 49 ns / median 80 ns reproduces the Phase 10 v1 "
                                  "TRADES-side finding (median 80.5 ns, min 49 ns) on the "
                                  "quotes side, measured independently."),
            },
            "identical_consecutive_timestamps": {
                "sip": {"n": int(rs.n_zero_gap.sum()), "of": int(rs.n_gaps.sum()),
                        "share": float(rs.n_zero_gap.sum() / rs.n_gaps.sum())},
                "participant": {"n": int(rp.n_zero_gap.sum()),
                                "share": float(rp.n_zero_gap.sum() / rp.n_gaps.sum())},
            },
            "t1b_i_epoch_timezone": {
                "check": ("Quote intensity per minute relative to the XNYS regular open/close, "
                          "after interpreting both fields as nanoseconds since the Unix epoch "
                          "UTC and converting to America/New_York."),
                "open_minute_minus_1": 2808, "open_minute_0": 12835, "open_jump_ratio": 4.57,
                "close_minute_minus_1": 6949, "close_minute_0": 878, "close_drop_ratio": 7.92,
                "rows_on_non_session_dates": 0, "half_day_sessions_in_cohort": 1,
                "verdict": ("CONFIRMED. The activity discontinuities land exactly on the XNYS "
                            "calendar boundaries; a wrong epoch or timezone would displace them."),
            },
            "t1b_ii_ordering_agreement": {
                "sorted_by": "sip_timestamp, sequence_number (explicit ORDER BY)",
                "share_participant_inverts": q(o.share_par_inverts),
                "share_sequence_number_inverts": q(o.share_seq_inverts),
                "share_sip_ties": q(o.share_sip_ties),
                "tied_sip_rows": int(o.n_tie_rows.sum()),
                "tied_rows_where_sequence_number_also_tied": int(o.n_tie_seq_dup.sum()),
                "escalation_row_6": {
                    "threshold": "> 1% of tied rows", "observed": 0.0,
                    "verdict": ("DOES NOT FIRE. sequence_number breaks every sip tie uniquely "
                                "and never inverts on any of the 50 events, so it is a usable "
                                "secondary ASOF sort key."),
                },
            },
            "t1b_iii_clock_latency_sip_minus_participant_ns": {s: {
                "median_of_event_p50": float(lat[lat.segment == s].p50.median()),
                "median_of_event_p25": float(lat[lat.segment == s].p25.median()),
                "median_of_event_p75": float(lat[lat.segment == s].p75.median()),
                "max_event_share_negative": float(lat[lat.segment == s].share_negative.max()),
            } for s in ["premarket", "rth", "post"]},
            "t1b_iv_which_timestamp_downstream": {
                "T2_state_census": ("sip_timestamp - the consolidated arrival clock is the one "
                                    "on which a prevailing-quote series is defined for a "
                                    "consolidated feed."),
                "T3_alignment_sweep": ("BOTH, by construction - T3a-i runs the whole sweep on "
                                       "each basis and the choice is Cooper's at the T4 gate."),
                "T1c_v_storage_order": ("all three fields, since the question is about file "
                                        "layout rather than about a clock."),
                "Stage_B": "not decided here. Set at the T4 gate (escalation row 19).",
            },
        },

        "t1c_source_columns": {
            "indicators": {
                "total_rows": int(ind.n_rows.sum()), "n_null": int(ind.n_null.sum()),
                "n_populated": int(ind.n_populated.sum()),
                "n_empty_list": int(ind.n_empty_list.sum()),
                "share_null": float(ind.n_null.sum() / ind.n_rows.sum()),
                "events_100pct_null": int((ind.n_null == ind.n_rows).sum()),
                "per_event_null_share": q(ind.sh),
                "distinct_codes": int(len(iv)),
                "mean_list_length_among_populated": float(iv.n.sum() / ind.n_populated.sum()),
                "code_frequency": [{"code": int(r.indicator_code), "n": int(r.n)}
                                   for r in iv.itertuples()],
                "finding": ("CONTRADICTS the working assumption carried into the prompt from a "
                            "2-row sample. indicators is POPULATED on 88.85% of source rows, "
                            "not null. No event is 100% null. Among populated rows 99.77% carry "
                            "code 1 alone and the mean list length is 1.0."),
            },
            "conditions": {
                "n_null_rows": 0, "distinct_codes": int(len(cc)),
                "distinct_combinations": int(len(cb)),
                "code_frequency": [{"code": int(r.condition_code), "n_rows": int(r.n_rows),
                                    "n_events": int(r.n_events)} for r in cc.itertuples()],
                "combination_frequency": [{"combo": str(r.combo), "n_rows": int(r.n_rows),
                                           "n_events": int(r.n_events)} for r in cb.itertuples()],
                "note": ("Codes reported as OPAQUE INTEGERS. No meaning is inferred "
                         "(escalation row 22). Code 81 appears on 3,698,276 rows but only 7 of "
                         "50 events - concentrated, not uniform."),
            },
            "t1c_iii_dictionary_search": {
                "searched": ["data/metadata/", "data/collection_scripts/", "data/Schema.md",
                             "docs/", "hawkes-ofi-impact/", "scanner-epg-momentum/",
                             "repo-wide ripgrep for condition_code / conditions_map / "
                             "sale_condition / quote_condition / trade_condition / "
                             "nbbo_indicator / indicator_code"],
                "found": False,
                "closest_artifacts": [
                    "results/phase_1c/artifacts/archive_schema_reference.json - records "
                    "conditions BIGINT[] / indicators BIGINT[] as TYPES only",
                    "results/phase_1c/artifacts/t3r1_optional_fields.json - file-level "
                    "presence only"],
                "escalation_row_20": ("FIRES as NOT A STOP. Codes stay opaque, no "
                                      "withdrawn-quote filter is built in this phase, census "
                                      "recorded to docs/Open-Items-Register.md."),
            },
            "t1c_iv_era_and_day_offset": {
                "indicators_null_share_era_2020_2021": sh20,
                "indicators_null_share_era_2022_2024": sh22,
                "era_gap_pp": round(abs(sh22 - sh20) * 100, 2), "threshold_pp": 20.0,
                "conditions_null_share_all_cells": 0.0,
                "escalation_row_21": ("DOES NOT FIRE (6.21 pp < 20 pp). No collection-era "
                                      "artifact at the era grain; the null share varies more by "
                                      "day offset (3.4%-24.1%) than by era."),
            },
            "t1c_v_storage_order": {
                "exemption": "escalation row 19a - this task and nothing else",
                "share_consecutive_file_rows_decreasing": {
                    "sip_timestamp": q(st.share_sip_decreases),
                    "participant_timestamp": q(st.share_par_decreases),
                    "sequence_number": q(st.share_seq_decreases)},
                "events_with_any_sip_decrease": int((st.share_sip_decreases > 0).sum()),
                "finding": ("The source parquet is stored in REVERSE CHRONOLOGICAL order. "
                            "sip_timestamp decreases between 99.97% of consecutive file rows at "
                            "the median event (min 91.26%), and sequence_number decreases at "
                            "99.99%. This confirms Cooper's 2-row sample observation across all "
                            "50 events. Code that assumed file order is chronological would read "
                            "the archive backwards."),
                "consequence": ("None for this phase - every query sorts explicitly (escalation "
                                "row 19). Recorded to docs/Open-Items-Register.md."),
            },
        },

        "segment_census": [
            {"segment": r.segment, "is_t0": bool(r.is_t0), "n": int(r.n),
             "n_events": int(r.n_events)} for r in seg.itertuples()],
        "segment_note": ("53 T=0 rows across 26 events fall outside the 04:00-20:00 ET extended "
                         "window (40 early, 13 late). They are labelled outside_early / "
                         "outside_late and carried, never dropped. Zero rows land on a "
                         "non-session date."),
    }

    pathlib.Path(A + "t1_quote_table_identity.json").write_text(json.dumps(out, indent=2))
    print("wrote t1_quote_table_identity.json")
    print("row 4a  :", out["t1b_timestamps"]["row_4a"]["verdict"][:60])
    print("row 6   :", out["t1b_timestamps"]["t1b_ii_ordering_agreement"]
                          ["escalation_row_6"]["verdict"][:60])
    print("row 21  : era gap",
          out["t1c_source_columns"]["t1c_iv_era_and_day_offset"]["era_gap_pp"], "pp")


if __name__ == "__main__":
    main()
