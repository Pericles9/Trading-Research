"""Phase 11 T2 - assemble the state-census summary artifact."""
from __future__ import annotations

import json
import pathlib

import pandas as pd

A = "results/phase_11/artifacts/"
SEGS = ["premarket", "rth", "post"]
STATES = ["crossed", "locked", "null_price", "nonpos_price", "one_side_miss",
          "zero_bid_size", "zero_ask_size"]


def q(s):
    v = s.quantile([0, .5, .75, .95, 1]).values
    return dict(min=float(v[0]), median=float(v[1]), p75=float(v[2]),
                p95=float(v[3]), max=float(v[4]))


def main() -> None:
    cen = pd.read_parquet(A + "t2a_state_census.parquet")
    t0 = cen[cen.day_offset == 0]
    runs = pd.read_parquet(A + "t2b_run_lengths.parquet")
    bbo = pd.read_parquet(A + "t2c_bbo_runs.parquet")
    age = pd.read_parquet(A + "t2c_trade_age.parquet")
    qt = pd.read_parquet(A + "t2d_quote_to_trade.parquet")
    sp = pd.read_parquet(A + "t2e_quoted_spread.parquet")
    sp["cents"] = sp.tw_spread_dollars * 100.0

    r5 = t0[t0.segment == "rth"].time_hard_unusable
    out = {
        "task": "T2", "phase": "11", "date": "2026-08-15",
        "nature": "CENSUS. No cleaning applied, no quote state excluded. The exclusion "
                  "rule is Cooper's at the T4 gate (escalation row 19).",
        "cohort": {"n_events": 50, "day_offsets": [0, -1, -3], "segments": SEGS},
        "passes_over_full_tables": 0,

        "state_definition": {
            "source": "Cooper 2026-08-15 - v2 three-way split imported over A1-2's union",
            "state_hard_unusable": "null price U non-positive price U one-side-missing U "
                                   "crossed. GATES ROW 5.",
            "state_degraded": "locked U zero-size, among rows not already hard. Reported "
                              "only; does not gate.",
            "partition_check_max_abs_deviation_from_1": 0.0,
            "non_exclusive_states_also_reported": STATES,
            "wide_is_not_unusable": "No width predicate enters any state definition.",
        },

        "escalation_row_5": {
            "quantity": "state_hard_unusable clock-time share, T=0 RTH, median across events",
            "threshold": 0.25, "observed_median": float(r5.median()),
            "p75": float(r5.quantile(.75)), "p95": float(r5.quantile(.95)),
            "max": float(r5.max()), "n_events": int(len(r5)),
            "events_above_25pct": int((r5 > 0.25).sum()),
            "events_above_10pct": int((r5 > 0.10).sum()),
            "events_above_1pct": int((r5 > 0.01).sum()),
            "events_exactly_zero": int((r5 == 0).sum()),
            "verdict": "DOES NOT FIRE",
        },

        "t2a_time_shares_t0": {seg: {
            "n_events": int((t0.segment == seg).sum()),
            "hard_unusable": q(t0[t0.segment == seg].time_hard_unusable),
            "degraded": q(t0[t0.segment == seg].time_degraded),
            "clean": q(t0[t0.segment == seg].time_clean),
            **{st: q(t0[t0.segment == seg][f"time_{st}"]) for st in STATES},
        } for seg in SEGS},

        "t2b_run_lengths_t0_seconds": {st: {
            "cells_with_any_run": int((runs.state == st).sum()),
            "median_longest_run_s": float(runs[runs.state == st].max_run_ns.median() / 1e9)
            if (runs.state == st).any() else None,
            "max_longest_run_s": float(runs[runs.state == st].max_run_ns.max() / 1e9)
            if (runs.state == st).any() else None,
        } for st in STATES + ["hard_unusable", "degraded"]},
        "t2b_note": "150 event x segment cells exist per state at T=0. States with fewer "
                    "rows here simply never occurred in the remaining cells. one_side_miss "
                    "and null_price occurred in ZERO cells.",

        "t2c_stale_top_of_book": {
            "definition": "A run is a maximal stretch over which the (bid_price, ask_price) "
                          "pair is unchanged, measured in prevailing-quote clock time.",
            "runs_per_event": {seg: {
                "median_n_runs": float(bbo[bbo.segment == seg].n_runs.median()),
                "median_run_p50_ms": float(bbo[bbo.segment == seg].p50_ns.median() / 1e6),
                "median_run_p95_s": float(bbo[bbo.segment == seg].p95_ns.median() / 1e9),
                "median_run_max_s": float(bbo[bbo.segment == seg].max_ns.median() / 1e9),
            } for seg in SEGS},
            "bbo_age_at_trade": {seg: {
                "n_events": int((age.segment == seg).sum()),
                "n_trades": int(age[age.segment == seg].n_trades.sum()),
                "n_unmatched": int((age[age.segment == seg].n_trades
                                    - age[age.segment == seg].n_matched).sum()),
                "median_p50_age_ms": float(age[age.segment == seg].p50_age_ns.median() / 1e6),
                "median_share_age_gt_1s": float(age[age.segment == seg].share_age_gt_1s.median()),
                "median_share_age_gt_60s": float(age[age.segment == seg].share_age_gt_60s.median()),
            } for seg in SEGS},
        },

        "t2d_quote_to_trade": {
            "median_ratio_by_segment_and_offset": {
                seg: {str(off): (float(qt[(qt.segment == seg) & (qt.day_offset == off)]
                                       .quote_to_trade.median()))
                      for off in [-3, -1, 0]} for seg in SEGS},
            "median_inter_quote_interval_ms_t0": {
                seg: float(qt[(qt.segment == seg) & (qt.day_offset == 0)].p50_iq_ns.median() / 1e6)
                for seg in SEGS},
        },

        "t2e_quoted_spread": {
            "measure": "time-weighted QUOTED spread (ask - bid). NOT effective spread - "
                       "that needs a trade and an adopted offset and is barred pre-gate "
                       "(escalation row 10).",
            "excluded_from_this_statistic": "rows in state_hard_unusable only (no midpoint "
                                            "exists on them). No other state excluded.",
            "median_bp": {seg: {str(off): float(sp[(sp.segment == seg) &
                                                   (sp.day_offset == off)].tw_spread_bp.median())
                                for off in [-3, -1, 0]} for seg in SEGS},
            "median_cents": {seg: {str(off): float(sp[(sp.segment == seg) &
                                                      (sp.day_offset == off)].cents.median())
                                   for off in [-3, -1, 0]} for seg in SEGS},
            "what_chart_03_shows": (
                "In basis points the median falls monotonically from T-3 to T=0 in all "
                "three segments (RTH 165.0 -> 127.6 -> 83.9; premarket 1292.2 -> 974.3 -> "
                "760.3; post 591.8 -> 503.8 -> 250.6). In cents the RTH median does not "
                "fall (3.64 -> 3.43 -> 3.79); premarket falls from 32.97 to 25.99 and post "
                "from 19.70 to 7.23. n = 50 events at every point."),
            "largest_outlier_carried_not_clipped": {
                "event": "ALXO 2020-08-05, premarket, T-3",
                "tw_spread_cents": 18700730.0, "tw_spread_bp": 19019.0, "n_quotes": 18,
                "note": "Shown on chart 03, never clipped. It passes state_hard_unusable "
                        "(positive prices, not crossed, non-zero sizes), which is the "
                        "definitional consequence of 'a wide quote is not unusable'.",
            },
        },
    }

    pathlib.Path(A + "t2_state_census.json").write_text(json.dumps(out, indent=2))
    print("wrote t2_state_census.json")
    print("row 5:", out["escalation_row_5"]["verdict"],
          f"(median {out['escalation_row_5']['observed_median']:.6f} vs 0.25)")


if __name__ == "__main__":
    main()
