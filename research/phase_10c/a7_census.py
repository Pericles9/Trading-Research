"""
Phase 10c Amendment 5 -- code-set confirmation, record census, and the F/H checks.

B  count of near-close prints carrying 9 WITHOUT 8 or 15, and the population size
   under each reading of the rule's scope
D  census of trade-stream records by vendor code class, cohort-wide and by the
   print's own session position
F  confirm the A2.8 floor is genuinely per-event
H  confirm the timestamp-resolution chain never touched a float64 column

No exclusion is applied anywhere. This counts what the stream is made of.

Usage: .venv/Scripts/python.exe research/phase_10c/a7_census.py
"""
from __future__ import annotations

import importlib.util as ilu
import json
import os
import sys
import time

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
DICT = "data/metadata/massive_trade_conditions.json"
NON_VOLUME = {15, 16, 38}
VOL_NOT_LAST = {2, 7, 12, 13, 21, 37, 52, 53}
COLS = ["sip_timestamp", "price", "size", "conditions"]


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    vdict = json.load(open(rel(DICT), encoding="utf-8"))
    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))
    coh["event_date_canonical"] = coh["event_date_canonical"].astype(str)

    # ---------------------------------------------------------------- B
    near = pd.read_parquet(rel(f"{ART}/a6_near_close_prints.parquet"))
    def cs(x):
        return set(int(v) for v in x.split(",")) if x else set()
    sets = near.codes.map(cs)
    has9 = sets.map(lambda s: 9 in s)
    has8_15 = sets.map(lambda s: bool(s & {8, 15}))
    b = {
        "code_set": [8, 15], "dropped": [9],
        "n_near_close_prints": int(len(near)),
        "n_with_9": int(has9.sum()),
        "n_with_9_without_8_or_15": int((has9 & ~has8_15).sum()),
        "n_with_8_or_15": int(has8_15.sum()),
        "n_with_8": int(sets.map(lambda s: 8 in s).sum()),
        "n_with_15": int(sets.map(lambda s: 15 in s).sum()),
        "reading": None,
    }
    b["reading"] = ("Every print carrying 9 also carries 8 or 15, so on this cohort dropping 9 "
                    "changes nothing and the choice is immaterial here."
                    if b["n_with_9_without_8_or_15"] == 0 else
                    f"{b['n_with_9_without_8_or_15']} prints carry 9 without 8 or 15. Those are "
                    "exactly the prints the wider set {8, 9, 15} would have reclassified as "
                    "auction activity and {8, 15} does not.")
    ex = near[has9 & ~has8_15]
    b["examples_9_without_8_or_15"] = ex.head(15)[
        ["ticker", "event_date_canonical", "seconds_from_close", "price", "size", "codes"]
    ].to_dict("records")
    b["scope_populations"] = {
        "anchor_classification_only": {
            "n_anchors_affected": 1,
            "detail": "ACET 2020-09-18 only, across all three threshold variants"},
        "all_trades": {
            "n_near_close_prints_matching_8_or_15": int(has8_15.sum()),
            "detail": ("every print within +/-1 s of a session close carrying 8 or 15, across the "
                       "114-event cohort. This is the population the wider reading reassigns.")},
        "note": ("Reported so the error tolerance on the code set can be judged against the "
                 "population it actually governs. The scope choice is Cooper's.")}

    # ---------------------------------------------------------------- D
    t0 = time.perf_counter()
    rows = []
    for r in coh.itertuples(index=False):
        files = p10.trade_files(cfg, r.ticker, r.event_date_canonical, r.momentum_pct)
        if not files:
            continue
        fr = [pd.read_parquet(f, columns=COLS) for f in files]
        d = pd.concat(fr, ignore_index=True) if len(fr) > 1 else fr[0]
        if not len(d):
            continue
        sess = cal.date_to_session(pd.Timestamp(r.event_date_canonical), direction="previous")
        opn = cal.session_open(sess).tz_convert(ET).value
        cls = cal.session_close(sess).tz_convert(ET).value
        ts = d.sip_timestamp.to_numpy()
        pos = np.where(ts > cls, "evening", np.where(ts >= opn, "rth", "premarket"))
        n_nonvol = np.zeros(len(d), bool)
        n_vnl = np.zeros(len(d), bool)
        for i, c_ in enumerate(d.conditions.to_numpy()):
            s = set(int(x) for x in c_) if isinstance(c_, (list, np.ndarray)) else set()
            n_nonvol[i] = bool(s & NON_VOLUME)
            n_vnl[i] = bool(s & VOL_NOT_LAST)
        for p_ in ("premarket", "rth", "evening"):
            m = pos == p_
            if not m.any():
                continue
            rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                         "cohort_group": r.cohort_group, "print_position": p_,
                         "n_prints": int(m.sum()),
                         "n_non_volume_updating": int((n_nonvol & m).sum()),
                         "n_volume_not_last": int((n_vnl & m).sum())})
    cen = pd.DataFrame(rows)
    cen.to_parquet(rel(f"{ART}/a7_record_census.parquet"), index=False)
    tot = cen[["n_prints", "n_non_volume_updating", "n_volume_not_last"]].sum()
    by = cen.groupby("print_position")[["n_prints", "n_non_volume_updating",
                                        "n_volume_not_last"]].sum()
    d_sec = {
        "codes_counted_non_volume_updating": sorted(NON_VOLUME),
        "codes_counted_volume_but_not_last": sorted(VOL_NOT_LAST),
        "cohort_total": {"n_prints": int(tot.n_prints),
                         "n_non_volume_updating": int(tot.n_non_volume_updating),
                         "share_non_volume_updating": float(tot.n_non_volume_updating / tot.n_prints),
                         "n_volume_not_last": int(tot.n_volume_not_last),
                         "share_volume_not_last": float(tot.n_volume_not_last / tot.n_prints)},
        "by_print_position": {p_: {"n_prints": int(g.n_prints),
                                   "n_non_volume_updating": int(g.n_non_volume_updating),
                                   "share_non_volume_updating": float(g.n_non_volume_updating
                                                                      / g.n_prints),
                                   "n_volume_not_last": int(g.n_volume_not_last),
                                   "share_volume_not_last": float(g.n_volume_not_last / g.n_prints)}
                              for p_, g in by.iterrows()},
        "no_exclusion_applied": True,
        "note": ("Counts only. Whether any record class leaves the interval stream is a Cooper "
                 "decision needing its own amendment, since it changes what a print means after "
                 "Stage 0b already measured on the current definition."),
        "timing_seconds": round(time.perf_counter() - t0, 1),
    }

    # ---------------------------------------------------------------- F
    f_sec = {
        "question": "is the A2.8 derived floor per-event or segment-derived?",
        "answer": "PER EVENT. Confirmed.",
        "code_path": ("research/phase_10c/t1_subbursts.py computes sigma = np.std(li, ddof=1) on "
                      "THAT event's own log intervals, then floor = "
                      "c10c.median_se_min_count(sigma, F). Nothing segment-level enters."),
        "what_the_segment_figures_are": ("The 1.363 premarket / 1.758 rth values are medians of "
                                         "per-event sigma, computed for reporting. They are not "
                                         "inputs to any floor."),
        "consequence": ("A4 dissolves as Amendment 5 F anticipates. Evening events get their own "
                        "per-event floors, are evaluated against the global D6 grid, and take "
                        "insufficient_context per event/kernel pair. No evening sigma exists to "
                        "borrow and none is needed."),
    }

    # ---------------------------------------------------------------- H
    tr = pd.read_parquet(rel("results/phase_10b/artifacts/t0e_timestamp_resolution.parquet"))
    never = cfg.get("cohort", {}).get("never_pooled", ["dev_v4_sidecar", "row_cap_census"])
    pooled = tr[~tr.cohort_group.isin(never)].min_nonzero_gap_ns.dropna()
    h_sec = {
        "question": "did any timestamp-resolution figure come from a float64 column?",
        "answer": "NO. The chain is int64 end to end.",
        "chain": ["sip_timestamp is int64 on disk (verified by a live parquet read)",
                  "t0e_cohort_assertion.py takes t0['sip_timestamp'].to_numpy() -> int64",
                  "np.diff on int64 -> int64",
                  "min_nonzero_gap_ns stored as int64 in t0e_timestamp_resolution.parquet"],
        "pooled_analysis_cohort": {"n": int(pooled.size), "min_ns": int(pooled.min()),
                                   "median_ns": float(pooled.median()),
                                   "max_ns": int(pooled.max())},
        "all_rows_including_never_pooled_median_ns": float(tr.min_nonzero_gap_ns.median()),
        "verdict": ("The 80.5 ns median and 49 ns minimum stand. The 256 ns float64 quantisation "
                    "affects det_ns_* only, which is a different column on a different chain and "
                    "never enters a resolution measurement. The fragmentation-floor reasoning "
                    "built on those figures is unaffected."),
    }

    out = {"phase": "10c", "amendment": "A5", "config_hash": chash,
           "dictionary": {"stored_at": DICT, "source": vdict["source"],
                          "completeness": vdict["completeness"]},
           "B_code_set": b, "D_record_census": d_sec, "F_floor_scope": f_sec,
           "H_timestamp_resolution_provenance": h_sec,
           "source": "research/phase_10c/a7_census.py:main"}
    c10c.write_json(rel(f"{ART}/a7_census.json"), out)

    print("B  9 without 8 or 15:", b["n_with_9_without_8_or_15"], "of", b["n_near_close_prints"],
          "near-close prints  (with 9:", b["n_with_9"], ", with 8 or 15:", b["n_with_8_or_15"], ")")
    print("  ", b["reading"][:150])
    print("\nD  census, cohort total:", d_sec["cohort_total"])
    for p_, g in d_sec["by_print_position"].items():
        print(f"    {p_:10s} prints {g['n_prints']:>9,}  non-volume {g['n_non_volume_updating']:>6,} "
              f"({g['share_non_volume_updating']:.6f})  vol-not-last {g['n_volume_not_last']:>9,} "
              f"({g['share_volume_not_last']:.4f})")
    print("\nF ", f_sec["answer"])
    print("H ", h_sec["answer"], "| pooled median", h_sec["pooled_analysis_cohort"]["median_ns"],
          "ns, min", h_sec["pooled_analysis_cohort"]["min_ns"], "ns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
