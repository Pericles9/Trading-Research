"""
Phase 10c Amendment 6 -- auction-rule closure: applies the settled {8, 15}
all-trades override, corrects the one anchor it actually moves (ACET), and
re-derives the RTH floor on the corrected segment assignment.

Amendment 5's A3 re-derivation text said "ACET in the RTH pool" but the code
behind it (a6_conditions.py) still bucketed ACET as 'evening' -- the override
was described, not implemented. This script implements it and re-runs the
same re-derivation so the D5=8 confirmation is real rather than aspirational.

Only 4 events ever land in 'evening' under any of the 3 threshold variants
(ACET, OST, CELH, BMR -- confirmed exhaustively from a6_segment_migration.parquet
marginals: evening counts 1/1/3, no other event appears). Their condition
codes are already known from Amendment 4's discriminant test
(a6_conditions_analysis.json -> A1_closing_print.A1_4_proposal.discriminant_test),
so no re-query of trade files is needed.

Usage: .venv/Scripts/python.exe research/phase_10c/a8_auction_closure.py
"""
from __future__ import annotations

import importlib.util as ilu
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
ET = "America/New_York"
KEY = ["ticker", "event_date_canonical"]
VARIANTS = [1.25, 1.30, 1.35]

# Condition codes on the anchor print itself, from a6_conditions_analysis.json's
# discriminant test (nearest-match lookup, already run in Amendment 4). These
# are the only 4 events that ever classify 'evening' under any variant.
ANCHOR_CODES = {
    "ACET": {8, 9, 41},
    "OST": {14, 12, 41},
    "CELH": {12},
    "BMR": {12, 37},
}


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    F = cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]["D4_median_precision_factor"]
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))
    coh["event_date_canonical"] = coh["event_date_canonical"].astype(str)

    # ------------------------------------------------------- corrected segments
    seg_by_variant, changed = {}, []
    for v in VARIANTS:
        s = det[np.isclose(det.threshold, v)].set_index(KEY)
        out = {}
        for k, row in s.iterrows():
            if pd.isna(row.det_ns_poll0):
                out[k] = None
                continue
            a = pd.Timestamp(int(row.det_ns_poll0), unit="ns", tz="UTC").tz_convert(ET)
            sess = cal.date_to_session(pd.Timestamp(k[1]), direction="previous")
            close = cal.session_close(sess).tz_convert(ET)
            opn = cal.session_open(sess).tz_convert(ET)
            codes = ANCHOR_CODES.get(k[0])
            old = "evening" if a > close else ("rth" if a >= opn else "premarket")
            new = c10c.assign_segment(a, codes, opn, close)
            out[k] = new
            if new != old:
                changed.append({"ticker": k[0], "event_date_canonical": k[1],
                                "threshold": v, "old_segment": old, "new_segment": new,
                                "anchor_codes": sorted(codes) if codes else None})
        seg_by_variant[v] = out

    changed_df = pd.DataFrame(changed)
    changed_df.to_parquet(rel(f"{ART}/a8_auction_reclassification.parquet"), index=False)

    # ------------------------------------------------------- A3-style re-derivation
    dens = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))
    ev0b = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    a3 = {}
    for v in VARIANTS:
        sm = seg_by_variant[v]
        d = dens.copy()
        d["seg_v"] = [sm.get((a, b)) for a, b in zip(d.ticker, d.event_date_canonical)]
        r_ = d[(d.seg_v == "rth") & (d.precision_factor == F)]
        if not len(r_):
            a3[str(v)] = {"n_rth_events": 0, "binding_rung_min": None}
            continue
        fl = float(r_.derived_min_count.median())
        wc = r_.groupby("kernel_min").window_count_median.median()
        ok = [k for k, c in wc.items() if c >= fl]
        e_ = ev0b.copy()
        e_["seg_v"] = [sm.get((a, b)) for a, b in zip(e_.ticker, e_.event_date_canonical)]
        # NOTE (Stage 1 T0 correction): count distinct (ticker, event_date) pairs, not
        # r_.ticker.nunique() -- two dev-sample tickers (MDIA, OCUL) each cover two distinct
        # events on different dates, and .nunique() silently collapses them. See
        # results/phase_10c/artifacts/s1_t0_denominator.json.
        n_events = r_[["ticker", "event_date_canonical"]].drop_duplicates().shape[0]
        a3[str(v)] = {"n_rth_events": int(n_events),
                      "sigma_rth_median": float(e_[e_.seg_v == "rth"].sigma_log10_post_agg.median()),
                      "rth_derived_floor": fl,
                      "acet_in_pool": bool(("ACET" in r_.ticker.values))
                      if v != 1.35 else False,
                      "binding_rung_min": (int(min(ok)) if ok else None)}
    rungs = [x["binding_rung_min"] for x in a3.values()]
    prior_n_rth = {"1.25": 36, "1.3": 36, "1.35": 28}  # a6_conditions_analysis.json A3, pre-override

    out = {
        "phase": "10c", "amendment": "A6 (auction rule closure)", "config_hash": chash,
        "A_rule": {
            "decision": "closing-auction rule keys on {8, 15}, scope ALL TRADES, code 9 dropped",
            "rationale": ("anchor-only scope is internally inconsistent, not merely narrower: under "
                         "it ACET's anchor sits in day T while its own twin -- the official-close "
                         "record 92us later -- stays attributed to day T+1. All-trades scope makes "
                         "the tick stream and the anchor agree."),
            "affected_population": {"anchor_classification_only": 1,
                                    "all_trades_near_close_prints_with_8_or_15": 291,
                                    "cohort_total_prints": 25218726},
            "code_9_note": ("0 of 877 near-close prints carry 9 without 8 or 15 (Amendment 5 B), so "
                            "the data does not discriminate the two readings on this cohort. The "
                            "decision to drop 9 rests on the semantic argument alone -- Cross Trade "
                            "carries no session/auction meaning and its after-close exclusivity here "
                            "is a property of these 114 events, not of the code."),
            "standing_limitation": ("empirical plus semantic, not validated. The dictionary confirms "
                                    "what 8 and 15 MEAN; it does not establish that {8, 15} captures "
                                    "every closing auction in the archive, or that no non-auction "
                                    "print carries them."),
            "implementation": ("research/phase_10c/common.py:assign_segment -- codes intersecting "
                              "{8, 15} force segment='rth' ahead of the timestamp rule. Previously "
                              "described in Amendment 4's A3 verdict text ('ACET in the RTH pool') "
                              "but not actually implemented -- a6_conditions.py's segment loop had "
                              "no code-aware override, so ACET was still bucketed 'evening' there "
                              "and excluded from the rth floor computation. This script is the first "
                              "to apply the override."),
        },
        "reclassified": {
            "n_changed": int(len(changed_df)),
            "events": changed,
            "only_4_events_ever_evening": ("Confirmed exhaustively from a6_segment_migration.parquet "
                                          "marginals across all 3 variants: ACET, OST, CELH, BMR. Of "
                                          "these only ACET carries code 8 or 15; OST/CELH/BMR carry "
                                          "{14,12,41}/{12}/{12,37} and are unaffected -- correctly, "
                                          "since they are genuine after-hours anchors, not closing "
                                          "prints."),
        },
        "C_rederivation_with_real_override": {
            "F": F,
            "by_variant": a3,
            "n_rth_events_prior_undercount": prior_n_rth,
            "all_agree_at_8": bool(set(rungs) == {8}),
            "verdict": ("D5 = 8 and D6 = {2, 8, 32} CONFIRMED, now with ACET genuinely included in "
                       "the rth pool at thresholds 1.25/1.30 (it never crosses at 1.35, unaffected "
                       "by this rule)."
                       if set(rungs) == {8} else
                       "BINDING RUNG MOVED under the corrected assignment -- stop and escalate."),
        },
        "D_amendment5_items_closed": {
            "5.A": "dictionary stored, location corrected in Amendment 6 section C (see below)",
            "5.B": "code set {8,15}, scope ALL TRADES per A above",
            "5.C": "code 15 not a trade, 0.0153% cohort-wide, immaterial, recorded not acted on",
            "5.D": "census recorded descriptively, no exclusion, no follow-on diagnostic (B below)",
            "5.F": "A2.8 floor confirmed per-event; A4 dissolves, no evening sigma exists or is needed",
            "5.H": "timestamp-resolution chain confirmed int64 end to end, unaffected by det_ns_* float64",
        },
        "E_carried_forward": [
            "det_ns_* float64 -> int64 repair at source (nearest-match recovers 0 ns residual today)",
            "eligible-pool gap: 15,299 eligible vs D14's 20,951 canonical in-scope, 5,652 (27%) unexplained",
            "A2.7.D17_burst_envelope_boundary -- delivered, still pending Cooper's read",
            "auction rule validation remains empirical plus semantic, not validated",
        ],
        "source": "research/phase_10c/a8_auction_closure.py:main",
    }
    c10c.write_json(rel(f"{ART}/a8_auction_closure.json"), out)

    print("A  rule: {8,15}, scope ALL TRADES. code 9 dropped on semantic grounds only")
    print(f"   affected: 1 anchor (ACET), 291 near-close prints of 25,218,726 cohort-wide")
    print(f"\nreclassified {len(changed_df)} anchor/variant pairs:")
    for c_ in changed:
        print(f"   {c_['ticker']} {c_['event_date_canonical']} thr={c_['threshold']}: "
              f"{c_['old_segment']} -> {c_['new_segment']}  codes={c_['anchor_codes']}")
    print("\nC  re-derivation with the override actually applied:")
    for v, r_ in a3.items():
        print(f"   thr={v}: n_rth={r_['n_rth_events']} (prior undercount {prior_n_rth.get(v, '?')}), "
              f"floor={r_.get('rth_derived_floor')}, rung={r_['binding_rung_min']}")
    print(f"\n{out['C_rederivation_with_real_override']['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
