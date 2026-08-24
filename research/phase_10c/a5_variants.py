"""
Phase 10c Amendment 3 -- threshold variants and the closing-print boundary.

A1  anchor-timing deltas per variant pair (the measurement segment counts cannot give)
A3  re-derive the A2.8 floor table under 1.30 and 1.35; is the RTH binding rung still 8?
A4  dev-sample composition under each variant
B   condition-code availability, and the post-close anchor distribution per variant

Usage: .venv/Scripts/python.exe research/phase_10c/a5_variants.py
"""
from __future__ import annotations

import glob
import importlib.util as ilu
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
VARIANTS = [1.25, 1.30, 1.35]
KEY = ["ticker", "event_date_canonical"]


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    F = cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]["D4_median_precision_factor"]
    dev = c10c.load_dev_sample(cfg)
    devkeys = set(zip(dev.ticker, dev.event_date_canonical))

    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)

    # ---------------------------------------------------------------- A1
    wide = {}
    for v in VARIANTS:
        s = det[np.isclose(det.threshold, v)].set_index(KEY)
        wide[v] = s["det_ns_poll0"]
    a1 = {}
    for i in range(len(VARIANTS)):
        for j in range(i + 1, len(VARIANTS)):
            a, b = VARIANTS[i], VARIANTS[j]
            df = pd.concat([wide[a].rename("a"), wide[b].rename("b")], axis=1).dropna()
            dt = (df["b"] - df["a"]) / 1e9          # seconds, later-threshold minus earlier
            a1[f"{a}_vs_{b}"] = {
                "n_both_anchored": int(len(dt)),
                "n_identical": int((dt == 0).sum()),
                "median_s": float(dt.median()), "iqr_s": [float(dt.quantile(.25)),
                                                          float(dt.quantile(.75))],
                "p90_abs_s": float(dt.abs().quantile(.9)),
                "max_abs_s": float(dt.abs().max()),
                "n_exceeding_60s": int((dt.abs() > 60).sum()),
                "share_exceeding_60s": float((dt.abs() > 60).mean()),
            }
            a1[f"{a}_vs_{b}"]["_deltas"] = [float(x) for x in dt.values]

    # ---------------------------------------------------------------- A4
    a4 = {"dev_sample_n": int(len(dev)),
          "draw_is_variant_independent": True,
          "why": ("dev_v4_primary and dev_v4_sidecar are a committed Phase 10 cohort manifest, "
                  "drawn in Phase 10 T1 by t0_print_count decile BEFORE detection was derived. "
                  "The draw cannot depend on a threshold variant. What varies by variant is how "
                  "many of the fixed 56 have an anchor at all."),
          "note_on_stratification": ("A1.6 struck the 'momentum_pct decile' wording; the actual "
                                     "stratification axis is t0_print_count decile."),
          "by_variant": {}}
    for v in VARIANTS:
        s = det[np.isclose(det.threshold, v)].set_index(KEY)
        sub = s[s.index.isin(devkeys)]
        a4["by_variant"][str(v)] = {
            "events_in_dev_sample": int(len(sub)),
            "with_anchor": int(sub.det_ns_poll0.notna().sum()),
            "without_anchor": int(sub.det_ns_poll0.isna().sum()),
            "segments": {str(k): int(x) for k, x in
                         sub.det_segment_poll0.fillna("unlabelled").value_counts().items()},
        }

    # ---------------------------------------------------------------- A3
    ev0b = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    dens = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))
    a3 = {"F": F, "by_variant": {}}
    for v in VARIANTS:
        s = det[np.isclose(det.threshold, v)].set_index(KEY)["det_segment_poll0"].to_dict()
        d = dens.copy()
        d["seg_v"] = [s.get((a, b)) for a, b in zip(d.ticker, d.event_date_canonical)]
        r_ = d[(d.seg_v == "rth") & (d.precision_factor == F)]
        e_ = ev0b.copy()
        e_["seg_v"] = [s.get((a, b)) for a, b in zip(e_.ticker, e_.event_date_canonical)]
        if not len(r_):
            a3["by_variant"][str(v)] = {"n_rth": 0, "binding_rung_min": None,
                                        "note": "no rth events under this variant in the dev sample"}
            continue
        fl = float(r_.derived_min_count.median())
        wc = r_.groupby("kernel_min").window_count_median.median()
        ok = [k for k, c in wc.items() if c >= fl]
        a3["by_variant"][str(v)] = {
            "n_rth_events": int(r_.ticker.nunique()),
            "sigma_rth_median": float(e_[e_.seg_v == "rth"].sigma_log10_post_agg.median()),
            "sigma_premarket_median": float(e_[e_.seg_v == "premarket"].sigma_log10_post_agg.median()),
            "rth_derived_floor": fl,
            "rth_window_counts": {str(k): float(x) for k, x in wc.items()},
            "binding_rung_min": (int(min(ok)) if ok else None),
        }
    rungs = [x.get("binding_rung_min") for x in a3["by_variant"].values()]
    a3["binding_rung_by_variant"] = {k: x.get("binding_rung_min") for k, x in
                                     a3["by_variant"].items()}
    a3["all_variants_agree"] = bool(len(set(rungs)) == 1 and rungs[0] is not None)
    a3["verdict"] = ("D5 = 8 and D6 = {2, 8, 32} hold globally across all three variants; the nine "
                     "cells stay directly comparable"
                     if a3["all_variants_agree"] and rungs[0] == 8 else
                     "BINDING RUNG DIFFERS BY VARIANT -- stop and escalate; do NOT assign "
                     "per-variant grids")

    # ---------------------------------------------------------------- B
    close_map = {}
    for d_ in sorted(set(det.event_date_canonical)):
        sess = cal.date_to_session(pd.Timestamp(d_), direction="previous")
        close_map[d_] = cal.session_close(sess).tz_convert(ET).value
    b_rows = []
    for v in VARIANTS:
        s = det[np.isclose(det.threshold, v)]
        for r in s.itertuples(index=False):
            if pd.isna(r.det_ns_poll0):
                continue
            off = (float(r.det_ns_poll0) - close_map[r.event_date_canonical]) / 1e9
            b_rows.append({"threshold": v, "ticker": r.ticker,
                           "event_date_canonical": r.event_date_canonical,
                           "seconds_after_close": off,
                           "in_dev": (r.ticker, r.event_date_canonical) in devkeys})
    bdf = pd.DataFrame(b_rows)
    within = bdf[(bdf.seconds_after_close > 0) & (bdf.seconds_after_close <= 1.0)]
    b = {"a_condition_codes": {
            "available": True,
            "column": "conditions",
            "location": ("present in every data/filtered/<event>/trades.parquet, but NOT in "
                         "research/phase_10/common.py:_TRADE_COLS, which reads only "
                         "sip_timestamp, price, size, sequence_number. Nothing in Phase 10c has "
                         "read it."),
            "acet_anchor_print": {"et": "2020-09-18 16:00:00.007793590-04:00", "price": 21.40,
                                  "size": 229769, "conditions": [8, 9, 41]},
            "acet_twin_print": {"et": "2020-09-18 16:00:00.007885823-04:00", "price": 21.40,
                                "size": 229769, "conditions": [15],
                                "reading": ("same price and same 229,769 shares 92 microseconds "
                                            "later -- the closing cross reported twice, the second "
                                            "carrying the closing-print code")},
            "implication": ("Mechanism 1 is available and needs no constant. Note the anchor print "
                            "itself carries [8, 9, 41] rather than [15], so a rule keying only on "
                            "15 would not catch it; the code set to key on is a decision that "
                            "should be made against the cohort-wide code distribution, not this "
                            "one event.")},
         "b_post_close_anchor_distribution": {
             "window": "0 < t - session_close <= 1 s",
             "by_variant": {str(v): {
                 "n_within_1s": int((within.threshold == v).sum()),
                 "n_anchored_total": int((bdf.threshold == v).sum()),
                 "events": within[within.threshold == v][
                     ["ticker", "event_date_canonical", "seconds_after_close", "in_dev"]
                 ].to_dict("records")} for v in VARIANTS},
             "any_beyond_1s": {str(v): int(((bdf.threshold == v) &
                                            (bdf.seconds_after_close > 1.0)).sum())
                               for v in VARIANTS},
         }}

    out = {"phase": "10c", "amendment": "A3", "config_hash": chash,
           "A1_anchor_timing_deltas": a1, "A3_floor_rederivation": a3,
           "A4_dev_sample_composition": a4, "B_closing_print": b,
           "D_population_question": {
               "question": "is 114 a full-population result (attrition) or a processed subset?",
               "answer": "PROCESSED SUBSET -- a scoping artifact, not attrition.",
               "evidence": {
                   "phase10_cohort_n_total": 114,
                   "stratification_eligible_pool": 15299,
                   "by_group": {"dev_v4_primary": 50, "activity_extension": 50,
                                "row_cap_census": 8, "dev_v4_sidecar": 6},
                   "draw": "5 per t0_print_count decile x 10 deciles for each of the two main arms"},
               "consequence": ("Detection was only ever derived on the 114-event cohort. Running "
                               "T1.5 on D14 = 20,951 requires deriving anchors for the remaining "
                               "20,837, which is Phase 10 D7 work. Nothing was lost; the coverage "
                               "gap is scope, not failure.")},
           "source": "research/phase_10c/a5_variants.py:main"}
    c10c.write_json(rel(f"{ART}/a5_variant_analysis.json"), out)
    bdf.to_parquet(rel(f"{ART}/a5_post_close_offsets.parquet"), index=False)

    print("A1 anchor-timing deltas (seconds, later minus earlier threshold)")
    for k, v in a1.items():
        print(f"  {k}: n={v['n_both_anchored']:3d} identical={v['n_identical']:3d} "
              f"median={v['median_s']:+.3f} IQR=[{v['iqr_s'][0]:+.3f},{v['iqr_s'][1]:+.3f}] "
              f"p90|d|={v['p90_abs_s']:.3f} max|d|={v['max_abs_s']:.1f} "
              f">60s: {v['n_exceeding_60s']} ({v['share_exceeding_60s']:.1%})")
    print("\nA3 RTH binding rung by variant:", a3["binding_rung_by_variant"])
    print("  ", a3["verdict"])
    print("\nA4 dev-sample composition")
    for k, v in a4["by_variant"].items():
        print(f"  thr {k}: {v['with_anchor']}/{v['events_in_dev_sample']} anchored  {v['segments']}")
    print("\nB post-close anchors within 1 s, by variant:",
          {k: v["n_within_1s"] for k, v in b["b_post_close_anchor_distribution"]["by_variant"].items()})
    print("  beyond 1 s:", b["b_post_close_anchor_distribution"]["any_beyond_1s"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
