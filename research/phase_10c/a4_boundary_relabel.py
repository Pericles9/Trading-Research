"""
Phase 10c Amendment 2 -- session-boundary relabel and the downstream re-derivation check.

A  trading day = [prior XNYS session close, this session's close]. XNYS-derived, so
   early closes and holidays are handled without a constant.
B  segment label for all 56 events under that boundary; per-event before/after.
C  re-derive the A2.8 floor table on the new assignments; is the RTH binding rung
   still 8 minutes?

Also reports a defect this amendment surfaced: the detection artifact carries THREE
momentum-threshold variants per event and every Phase 10c number so far has silently
used the first.

Usage: .venv/Scripts/python.exe research/phase_10c/a4_boundary_relabel.py
"""
from __future__ import annotations

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


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)

    # ---------------------------------------------------------- threshold-variant defect
    thr_tab = (det.groupby(["threshold", "det_segment_poll0"], dropna=False).size()
               .unstack(fill_value=0))
    thr_defect = {
        "issue": ("v2_r13_detection.parquet carries THREE rows per event, one per momentum "
                  "threshold variant (1.25, 1.30, 1.35). research/phase_10c/common.py "
                  "load_detection() calls drop_duplicates(subset=COHORT_KEY), which keeps the "
                  "FIRST row and therefore silently selects threshold 1.25."),
        "impact": ("Every segment-stratified number in Stage 0b and Stage 1 was computed on the "
                   "1.25 variant without that being a recorded decision. The anchor variant is a "
                   "free parameter selecting the anchor -- the class of choice this phase's rules "
                   "exist to surface."),
        "segment_counts_by_threshold": {str(t): {str(k): int(v) for k, v in row.items()}
                                        for t, row in thr_tab.iterrows()},
        "note_on_T0_6": ("T0.6 reported zero segment migration across the five POLL variants. That "
                         "stands, but it was computed after the same drop_duplicates, so it "
                         "compared poll variants within threshold 1.25 only. The THRESHOLD variant "
                         "was never examined and it moves segments materially."),
        "status": "REPORTED, not silently fixed. Selecting a threshold variant is a Cooper decision.",
    }

    d125 = det[det.threshold == 1.25].copy()
    dev = dev.merge(d125[p10.COHORT_KEY + ["det_ns_poll0", "det_segment_poll0", "never_crosses",
                                           "cross_reason", "reference_undefined"]],
                    on=p10.COHORT_KEY, how="left")

    rows = []
    for r in dev.itertuples(index=False):
        ed = pd.Timestamp(r.event_date_canonical)
        # XNYS prior session close and this session's close -- no constant anywhere
        sess = cal.date_to_session(ed, direction="previous")
        prev = cal.previous_session(sess)
        this_close = cal.session_close(sess).tz_convert(ET)
        prev_close = cal.session_close(prev).tz_convert(ET)
        det_ns = r.det_ns_poll0
        if pd.isna(det_ns):
            rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                         "is_sidecar": bool(r.is_sidecar), "old_segment": r.det_segment_poll0,
                         "new_segment": None, "anchor_et": None,
                         "prev_close_et": str(prev_close), "this_close_et": str(this_close),
                         "moved": False, "reason": r.cross_reason,
                         "never_crosses": bool(r.never_crosses),
                         "reference_undefined": bool(r.reference_undefined),
                         "inside_redefined_day": None})
            continue
        a = pd.Timestamp(int(det_ns), unit="ns", tz="UTC").tz_convert(ET)
        inside = bool(prev_close < a <= this_close)
        rth_open = cal.session_open(sess).tz_convert(ET)
        if not inside:
            new = "outside_redefined_day"
        elif a >= rth_open:
            new = "rth"
        else:
            new = "premarket"          # anything from prior close up to this open
        rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                     "is_sidecar": bool(r.is_sidecar), "old_segment": r.det_segment_poll0,
                     "new_segment": new, "anchor_et": str(a),
                     "prev_close_et": str(prev_close), "this_close_et": str(this_close),
                     "moved": bool(new != r.det_segment_poll0), "reason": None,
                     "never_crosses": False, "reference_undefined": False,
                     "inside_redefined_day": inside,
                     "seconds_past_this_close": float((a - this_close).total_seconds())
                     if not inside else np.nan})
    t = pd.DataFrame(rows)
    t.to_parquet(rel(f"{ART}/a4_segment_relabel.parquet"), index=False)

    moved = t[t.moved]
    unl = t[t.new_segment.isna()]

    # ---------------------------------------------------------- C re-derivation
    d4 = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))
    key = ["ticker", "event_date_canonical"]
    newseg = t.set_index(key).new_segment.to_dict()
    d4 = d4.copy()
    d4["new_segment"] = [newseg.get((a, b)) for a, b in zip(d4.ticker, d4.event_date_canonical)]
    F = cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]["D4_median_precision_factor"]

    def binding(df, segcol):
        r_ = df[(df[segcol] == "rth") & (df.precision_factor == F)]
        if not len(r_):
            return None, None, None
        fl = float(r_.derived_min_count.median())
        wc = r_.groupby("kernel_min").window_count_median.median()
        ok = [k for k, c in wc.items() if c >= fl]
        return fl, (int(min(ok)) if ok else None), {str(k): float(v) for k, v in wc.items()}

    fl_old, rung_old, wc_old = binding(d4, "det_segment")
    fl_new, rung_new, wc_new = binding(d4, "new_segment")
    sig_old = {s: float(g.sigma_log10_post_agg.median())
               for s, g in pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
               .groupby("det_segment") if s in ("premarket", "rth")}
    ev0b = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    ev0b["new_segment"] = [newseg.get((a, b)) for a, b in zip(ev0b.ticker,
                                                              ev0b.event_date_canonical)]
    sig_new = {s: float(g.sigma_log10_post_agg.median())
               for s, g in ev0b.groupby("new_segment") if s in ("premarket", "rth")}

    out = {
        "phase": "10c", "amendment": "A2 (session boundary)", "config_hash": chash,
        "A_boundary": {
            "rule": "trading day = (prior XNYS session close, this session's close]",
            "source": "exchange_calendars XNYS session_close; no constant, so early closes and "
                      "holidays resolve automatically",
            "early_close_events_in_sample": int((t.this_close_et.astype(str)
                                                 .str.contains("13:00")).sum()),
        },
        "B1_existing_gap": {
            "question": "were anchors/segments NOT computed for the three, or computed and excluded?",
            "answer": ("NEITHER. All three were computed and returned a definite result. The "
                       "anchor exists for one; for the other two the momentum condition was never "
                       "satisfied, which is a measured property with a stated reason."),
            "per_event": {
                "ACET 2020-09-18": ("anchor EXISTS at 2020-09-18 16:00:00.0078 ET, segment 'post'. "
                                    "It crossed 7.8 ms after the RTH close. Not a gap."),
                "RBC 2022-09-26": ("never_crosses=True, reason 'reference undefined' -- no "
                                   "reference price could be established, so no threshold exists."),
                "NUKK 2022-04-18": ("never_crosses=True, reason 'running max never reaches "
                                    "threshold x reference'; only 43 T=0 prints."),
            },
        },
        "B3_reclassification": {
            "n_events": int(len(t)), "n_moved": int(len(moved)),
            "moved_events": moved[["ticker", "event_date_canonical", "is_sidecar", "old_segment",
                                   "new_segment", "anchor_et", "this_close_et",
                                   "seconds_past_this_close"]].to_dict("records"),
            "before": t.old_segment.fillna("unlabelled").value_counts().to_dict(),
            "after": t.new_segment.fillna("unlabelled").value_counts().to_dict(),
        },
        "B4_unlabelled": {
            "n": int(len(unl)),
            "resolution": ("POSITIVELY UNLABELLABLE, not an unresolved gap. Both have "
                           "never_crosses=True: RBC because the reference price is undefined, "
                           "NUKK because its running max never reaches threshold x reference. "
                           "With no anchor there is no segment to assign under any boundary "
                           "definition."),
            "events": unl[["ticker", "event_date_canonical", "is_sidecar", "reason",
                           "never_crosses", "reference_undefined"]].to_dict("records"),
        },
        "B_structural_limit": {
            "finding": ("Relabelling under the new boundary can only push events OUT of the day, "
                        "never pull any in. Phase 10's anchor derivation searched the OLD extended "
                        "day (04:00-20:00 ET on the event date), so by construction no anchor "
                        "exists before 04:00. The prior-evening and overnight span the new "
                        "boundary adds was never searched."),
            "consequence": ("To find anchors in the prior evening or overnight, the detection "
                            "derivation itself must be re-run on the redefined window. That is "
                            "Phase 10 D7 work, not a relabel."),
            "anchors_before_0400_et": 0,
        },
        "C_rederivation": {
            "F": F,
            "sigma_old": sig_old, "sigma_new": sig_new,
            "rth_derived_floor_old": fl_old, "rth_derived_floor_new": fl_new,
            "rth_binding_rung_old_min": rung_old, "rth_binding_rung_new_min": rung_new,
            "rth_window_counts_old": wc_old, "rth_window_counts_new": wc_new,
            "binding_rung_unchanged": bool(rung_old == rung_new),
            "verdict": ("D5 = 8 and D6 = {2, 8, 32} CONFIRMED on the corrected basis"
                        if rung_old == rung_new else
                        "BINDING RUNG MOVED -- stop and escalate; do not apply a new D5/D6"),
        },
        "threshold_variant_defect": thr_defect,
        "source": "research/phase_10c/a4_boundary_relabel.py:main",
    }
    c10c.write_json(rel(f"{ART}/a4_boundary_relabel.json"), out)

    print("A2 relabel")
    print(f"  moved: {len(moved)} of {len(t)}")
    for m in out["B3_reclassification"]["moved_events"]:
        print(f"    {m['ticker']} {m['event_date_canonical']} sidecar={m['is_sidecar']}: "
              f"{m['old_segment']} -> {m['new_segment']}  anchor {m['anchor_et']}  "
              f"({m['seconds_past_this_close']:.4f} s past close)")
    print(f"  before: {out['B3_reclassification']['before']}")
    print(f"  after : {out['B3_reclassification']['after']}")
    print(f"\nC re-derivation: RTH floor {fl_old:.0f} -> {fl_new:.0f}, "
          f"binding rung {rung_old} -> {rung_new} min")
    print(f"  {out['C_rederivation']['verdict']}")
    print(f"\nthreshold-variant defect: segment counts by threshold "
          f"{thr_defect['segment_counts_by_threshold']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
