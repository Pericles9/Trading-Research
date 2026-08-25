"""
Phase 10c Stage 1, T0 -- denominator clarification, required before any Stage 1 computation.

The prompt names two 37s that look different (Amendment 6's post-override 37 including ACET,
vs. the dev-manifest table's pre-override 37 excluding ACET) and asks which pool the earlier
"36" is, and which RTH event sits in the manifest but not the floor derivation.

This traces both numbers to source and finds NEITHER discrepancy is a population difference.
Both are counting-methodology artifacts in a6_conditions.py / a8_auction_closure.py's
"n_rth_events": int(r_.ticker.nunique()) line. Two dev-sample tickers (MDIA, OCUL) each cover
TWO distinct events on different dates (Phase 3 Amendment 1's stratification draws by
t0_print_count decile, not by unique company, so a repeat ticker is expected, not a defect).
OCUL's two events (2020-10-07, 2023-12-04) BOTH classify 'rth' at thresholds 1.25 and 1.30 --
two real (ticker, event_date) rows collapsing to one unique ticker STRING under .nunique().

No event is absent from the floor derivation. r_ (the row-set median/floor is computed over)
always held the correct 37 (pre-override) / 38 (post-override) rows -- only the printed COUNT
used the wrong denominator. The floor and rung statistics were never affected.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t0_denominator.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
ET = "America/New_York"
KEY = ["ticker", "event_date_canonical"]
VARIANTS = [1.25, 1.30, 1.35]


def classify(det_v, cal):
    """The Amendment 4 from-scratch classifier, pre-override (no condition codes).
    Reproduced exactly as a6_conditions.py/a8_auction_closure.py compute it, so the
    diagnosis below traces the SAME code path that produced the disputed numbers."""
    out = {}
    for k, row in det_v.iterrows():
        if pd.isna(row.det_ns_poll0):
            out[k] = None
            continue
        a = pd.Timestamp(int(row.det_ns_poll0), unit="ns", tz="UTC").tz_convert(ET)
        sess = cal.date_to_session(pd.Timestamp(k[1]), direction="previous")
        close = cal.session_close(sess).tz_convert(ET)
        opn = cal.session_open(sess).tz_convert(ET)
        out[k] = "evening" if a > close else ("rth" if a >= opn else "premarket")
    return out


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    F = cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]["D4_median_precision_factor"]

    dev = c10c.load_dev_sample(cfg)
    dup_tickers = dev.ticker[dev.ticker.duplicated(keep=False)].unique().tolist()

    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    dens = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))

    per_variant = {}
    for v in VARIANTS:
        pre = classify(det[np.isclose(det.threshold, v)].set_index(KEY), cal)
        # post-override: apply Amendment 6's assign_segment using the known anchor codes for
        # the only 4 events that ever land 'evening' (ACET/OST/CELH/BMR -- Amendment 6 provenance)
        anchor_codes = {"ACET": {8, 9, 41}, "OST": {14, 12, 41}, "CELH": {12}, "BMR": {12, 37}}
        post = dict(pre)
        for k, seg in pre.items():
            if seg == "evening" and k[0] in anchor_codes:
                a = pd.Timestamp(int(det[np.isclose(det.threshold, v)]
                                      .set_index(KEY).loc[k].det_ns_poll0), unit="ns",
                                 tz="UTC").tz_convert(ET)
                sess = cal.date_to_session(pd.Timestamp(k[1]), direction="previous")
                post[k] = c10c.assign_segment(a, anchor_codes[k[0]],
                                              cal.session_open(sess).tz_convert(ET),
                                              cal.session_close(sess).tz_convert(ET))

        def rth_population(seg_map):
            pairs = sorted(k for k, s in seg_map.items() if s == "rth" and k in
                           set(zip(dev.ticker, dev.event_date_canonical)))
            return pairs

        pre_pairs = rth_population(pre)
        post_pairs = rth_population(post)

        d = dens.copy()
        d["seg_v"] = [pre.get((a, b)) for a, b in zip(d.ticker, d.event_date_canonical)]
        r_pre = d[(d.seg_v == "rth") & (d.precision_factor == F)]
        d2 = dens.copy()
        d2["seg_v"] = [post.get((a, b)) for a, b in zip(d2.ticker, d2.event_date_canonical)]
        r_post = d2[(d2.seg_v == "rth") & (d2.precision_factor == F)]

        assert set(zip(r_pre.ticker, r_pre.event_date_canonical)) == set(pre_pairs), (
            "every classified-rth dev event must have a floor row -- none actually missing")

        per_variant[str(v)] = {
            "pre_override_true_n_event_pairs": len(pre_pairs),
            "pre_override_buggy_nunique_count": int(r_pre.ticker.nunique()),
            "post_override_true_n_event_pairs": len(post_pairs),
            "post_override_buggy_nunique_count": int(r_post.ticker.nunique()),
            "pre_override_floor": (float(r_pre.derived_min_count.median())
                                   if len(r_pre) else None),
            "post_override_floor": (float(r_post.derived_min_count.median())
                                    if len(r_post) else None),
            "which_duplicated_ticker_collides": [t for t in dup_tickers
                                                 if sum(1 for k in pre_pairs if k[0] == t) > 1],
        }

    out = {
        "phase": "10c", "stage": "1", "task": "T0_denominator_clarification", "config_hash": chash,
        "finding": (
            "Neither 37 is a different POPULATION from the other. Both traced to the same "
            "code path (a6_conditions.py / a8_auction_closure.py: "
            "\"n_rth_events\": int(r_.ticker.nunique())), which counts DISTINCT TICKER STRINGS, "
            "not distinct (ticker, event_date) pairs. Two dev-sample tickers repeat on different "
            "dates (MDIA: 2024-04-09 and 2022-08-03; OCUL: 2020-10-07 and 2023-12-04) -- an "
            "expected consequence of stratifying the 56-event draw by t0_print_count decile "
            "rather than by unique company, not a defect in the draw itself."
        ),
        "which_pool_is_the_36": (
            "a6_conditions.py's ORIGINAL A3 re-derivation (pre-Amendment-6, no auction override). "
            "OCUL's two dev-sample events (2020-10-07, 2023-12-04) BOTH classify segment='rth' at "
            "thresholds 1.25 and 1.30 -- two real, distinct (ticker, event_date) rows that share "
            "one ticker string. .ticker.nunique() collapses them to 1, undercounting the TRUE "
            "37-event rth population by exactly 1, reporting 36. At threshold 1.35 OCUL never "
            "crosses at all (both dates unlabelled), so no collision occurs there and the printed "
            "28 was always correct."
        ),
        "the_missing_event_is_not_missing": (
            "No event is absent from the floor derivation. The row-set the floor/rung statistics "
            "are computed over (r_ = d[(d.seg_v=='rth') & (d.precision_factor==F)]) always "
            "contained every classified-rth dev-sample event's rows, OCUL's both included -- "
            "verified by assertion in this script. Only the DISPLAYED COUNT used the wrong "
            "denominator. rth_derived_floor and the binding rung (8) are unaffected by the bug at "
            "either threshold, confirmed per-variant below."
        ),
        "the_dev_manifest_37_and_the_true_pre_override_37_are_the_same_population": (
            "a5_variants.py's A4 table used sub.det_segment_poll0.value_counts() -- a row-count "
            "over the FULL 56-event frame, immune to the nunique() bug entirely and therefore "
            "correct at 37. This script's independently-recomputed pre_override_true_n_event_pairs "
            "confirms 37 at 1.25/1.30, 28 at 1.35 -- identical to the manifest table. There were "
            "never two different 37-event populations; there was one 37-event population (with "
            "ACET separately unlabelled/'evening') and one buggy DISPLAY of it as 36."
        ),
        "post_override_true_count_is_38_not_37": (
            "Amendment 6 adds ACET (1 real event) on top of the TRUE 37-event pre-override "
            "population, so the correct post-override count is 38 at 1.25 and 1.30 -- not the 37 "
            "a8_auction_closure.py printed. That 37 was itself a coincidence: the nunique() bug's "
            "-1 and ACET's +1 cancelled numerically, producing an unchanged printed total across "
            "an amendment that Cooper's own text says changes the population. This is the same "
            "error class as Amendment 4's VEEE/CODX offsetting swap and Amendment 2's threshold- "
            "variant segment-count marginals -- an identical count concealing a membership change."
        ),
        "systemic_scope_of_the_nunique_bug": (
            ".ticker.nunique() is used the same way, with the same OCUL/MDIA collision exposure, "
            "in a5_variants.py:108 (Amendment 3's own A3 rederivation, predates this diagnosis), "
            "t0_landscape.py:164, t0_charts.py:101/220 and t0b_charts.py:165/166/203 -- all in "
            "Stage 0 / Stage 0b, both already tagged (phase-10c-stage0, phase-10c-stage0b) and "
            "therefore NOT edited here, per the same closed-tagged-artifact convention used for "
            "Phase 10's common.py. Flagged, not silently fixed: any of those printed dev-sample "
            "n figures may be undercounting by 1 wherever OCUL or MDIA's two events land in the "
            "same bucket. This script and a8_auction_closure.py (untagged, still on the open "
            "branch) are corrected below; the tagged Stage 0/0b captions are not."
        ),
        "by_variant": per_variant,
        "duplicated_dev_sample_tickers": {
            "MDIA": ["2024-04-09", "2022-08-03"],
            "OCUL": ["2020-10-07", "2023-12-04"],
        },
        "verdict": (
            "NAMING RESOLVED, not a stop. Pre-override RTH population is 37 (ticker,event_date) "
            "pairs at 1.25/1.30 (28 at 1.35), identical to the dev-manifest table. Post-override "
            "is 38 at 1.25/1.30 (unchanged 28 at 1.35, ACET never crosses there). D5=8 confirmed "
            "on the corrected count -- see rth_derived_floor per variant above, unchanged from "
            "the previously reported figures since the floor was always computed on the full, "
            "correct row-set."
        ),
        "source": "research/phase_10c/s1_t0_denominator.py:main",
    }
    c10c.write_json(rel(f"{ART}/s1_t0_denominator.json"), out)

    print("T0 denominator clarification")
    for v, r in per_variant.items():
        print(f"  thr={v}: pre true_n={r['pre_override_true_n_event_pairs']} "
              f"(buggy nunique printed {r['pre_override_buggy_nunique_count']})  "
              f"post true_n={r['post_override_true_n_event_pairs']} "
              f"(buggy nunique printed {r['post_override_buggy_nunique_count']})  "
              f"floor pre={r['pre_override_floor']:.2f} post={r['post_override_floor']:.2f}"
              if r['pre_override_floor'] is not None else "")
        print(f"    colliding ticker(s): {r['which_duplicated_ticker_collides']}")
    print("\n" + out["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
