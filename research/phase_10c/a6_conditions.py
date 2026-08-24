"""
Phase 10c Amendment 4 -- closing-print evidence, evening segment, and re-derivation.

A1.1 conditions is read via a PHASE-10C-LOCAL reader rather than by mutating
     research/phase_10/common.py:_TRADE_COLS. Phase 10 is a closed, tagged phase;
     editing its module from 10c would change a closed phase's load path. Same
     effect, smaller blast radius, and recorded here rather than done silently.
A1.2 cohort-wide condition-code distribution for prints near session close
A1.3 the archive's own code definitions -- reported, not assumed
A2   evening segment; is 20:00-04:00 measured-empty or not?
A3   re-derive the floor with ACET in the RTH pool
D    per-event segment migration matrix across the three variants

Usage: .venv/Scripts/python.exe research/phase_10c/a6_conditions.py
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
COLS = ["sip_timestamp", "price", "size", "conditions"]


def read_with_conditions(cfg, ticker, date, mom):
    """Phase-10c-local reader. Same file discovery as Phase 10 (base + repair
    siblings, per CLAUDE.md) but requests the conditions column too."""
    files = p10.trade_files(cfg, ticker, date, mom)
    if not files:
        return None
    fr = [pd.read_parquet(f, columns=COLS) for f in files]
    return pd.concat(fr, ignore_index=True) if len(fr) > 1 else fr[0]


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    F = cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]["D4_median_precision_factor"]
    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))
    coh["event_date_canonical"] = coh["event_date_canonical"].astype(str)
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)

    # ---------------------------------------------------------------- A1.2
    rows, near_rows = [], []
    for r in coh.itertuples(index=False):
        d = read_with_conditions(cfg, r.ticker, r.event_date_canonical, r.momentum_pct)
        if d is None or not len(d):
            continue
        sess = cal.date_to_session(pd.Timestamp(r.event_date_canonical), direction="previous")
        close_ns = cal.session_close(sess).tz_convert(ET).value
        off = (d.sip_timestamp.to_numpy(dtype=np.float64) - close_ns) / 1e9
        near = np.abs(off) <= 1.0
        for o, c_, px, sz in zip(off[near], d.conditions.to_numpy()[near],
                                 d.price.to_numpy()[near], d["size"].to_numpy()[near]):
            codes = list(c_) if isinstance(c_, (list, np.ndarray)) else ([] if c_ is None else [c_])
            near_rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                              "seconds_from_close": float(o), "price": float(px),
                              "size": int(sz), "codes": ",".join(str(int(x)) for x in codes)})
        rows.append({"ticker": r.ticker, "n_near_close": int(near.sum())})
    near = pd.DataFrame(near_rows)
    near.to_parquet(rel(f"{ART}/a6_near_close_prints.parquet"), index=False)

    codes_flat = {}
    for cs in near.codes:
        for x in (cs.split(",") if cs else []):
            codes_flat[x] = codes_flat.get(x, 0) + 1
    after = near[near.seconds_from_close > 0]
    codes_after = {}
    for cs in after.codes:
        for x in (cs.split(",") if cs else []):
            codes_after[x] = codes_after.get(x, 0) + 1
    # signature of an auction print: unusually large size relative to the event
    big = near.sort_values("size", ascending=False).head(30)

    a1 = {
        "A1_1_reader": {
            "action": "conditions read via a Phase-10c-local reader, not by mutating _TRADE_COLS",
            "why": ("research/phase_10/common.py belongs to a closed, tagged phase. Editing its "
                    "module from Phase 10c would change a closed phase's load path for every "
                    "future re-run. The local reader achieves the same read with a smaller blast "
                    "radius. Recorded rather than done silently; say the word if the in-place "
                    "edit is wanted instead."),
            "file_discovery": "identical to Phase 10 -- base trades.parquet plus *_repair_1c siblings",
        },
        "A1_2_distribution": {
            "window": "|t - session_close| <= 1 s",
            "n_events_scanned": int(len(rows)),
            "n_prints_in_window": int(len(near)),
            "code_counts_whole_window": dict(sorted(codes_flat.items(),
                                                    key=lambda kv: -kv[1])),
            "code_counts_after_close_only": dict(sorted(codes_after.items(),
                                                        key=lambda kv: -kv[1])),
            "n_prints_after_close": int(len(after)),
            "largest_prints_near_close": big[["ticker", "event_date_canonical",
                                              "seconds_from_close", "price", "size", "codes"]]
            .to_dict("records"),
        },
        "A1_3_code_definitions": {
            "available_in_repo": False,
            "searched": ["data/filtered/METADATA.md", "data/Schema.md", "docs/**"],
            "what_metadata_says": "'conditions (object): Trade conditions.' -- no code-to-meaning map",
            "consequence": ("The archive ships no code dictionary and D14 makes this environment "
                            "offline, so the vendor's documentation cannot be fetched. Per the "
                            "amendment's own instruction I am NOT supplying a remembered mapping. "
                            "The rule therefore cannot be keyed on documented semantics today; it "
                            "can only be keyed on an empirically identified code set, or the "
                            "dictionary has to be brought into the repo first."),
        },
        "A1_4_proposal": {
            "status": "NOT PROPOSED",
            "reason": ("A1.4 asks for a code set justified by the distribution. Without the code "
                       "dictionary any set I named would be an empirical guess dressed as a rule, "
                       "and the amendment explicitly rules out remembered mappings. The blocking "
                       "item is the dictionary, not the measurement."),
        },
    }

    # ---------------------------------------------------------------- A2 gap
    gap = {"span": "20:00 -> 04:00 ET inside the redefined day", "by_variant": {}}
    for v in VARIANTS:
        s = det[np.isclose(det.threshold, v)]
        n_in = 0
        for r in s.itertuples(index=False):
            if pd.isna(r.det_ns_poll0):
                continue
            a = pd.Timestamp(int(r.det_ns_poll0), unit="ns", tz="UTC").tz_convert(ET)
            if (a.hour >= 20) or (a.hour < 4):
                n_in += 1
        gap["by_variant"][str(v)] = n_in
    gap["measured_empty"] = all(x == 0 for x in gap["by_variant"].values())
    gap["note"] = ("Measured, not assumed. Phase 10 derived anchors on the 04:00-20:00 window, so "
                   "this span could only be non-empty if an anchor sat exactly at a boundary.")

    # ---------------------------------------------------------------- A2 relabel + D
    seg_by_variant = {}
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
            if a > close:
                out[k] = "evening"          # A2: post-close belongs to the NEXT day's evening
            elif a >= opn:
                out[k] = "rth"
            else:
                out[k] = "premarket"
        seg_by_variant[v] = out

    mig = []
    for k in seg_by_variant[1.25]:
        mig.append({"ticker": k[0], "event_date_canonical": k[1],
                    "seg_125": seg_by_variant[1.25].get(k),
                    "seg_130": seg_by_variant[1.30].get(k),
                    "seg_135": seg_by_variant[1.35].get(k)})
    mg = pd.DataFrame(mig)
    mg["in_dev"] = [(a, b) in set(zip(coh.ticker, coh.event_date_canonical))
                    for a, b in zip(mg.ticker, mg.event_date_canonical)]
    mg.to_parquet(rel(f"{ART}/a6_segment_migration.parquet"), index=False)
    f = lambda s: s.fillna("unlabelled")  # noqa: E731
    dsec = {
        "marginals": {v: mg[c].fillna("unlabelled").value_counts().to_dict()
                      for v, c in (("1.25", "seg_125"), ("1.30", "seg_130"), ("1.35", "seg_135"))},
        "matrix_125_to_130": pd.crosstab(f(mg.seg_125), f(mg.seg_130)).to_dict(),
        "matrix_130_to_135": pd.crosstab(f(mg.seg_130), f(mg.seg_135)).to_dict(),
        "n_events_changing_segment_125_to_130": int((f(mg.seg_125) != f(mg.seg_130)).sum()),
        "n_events_changing_segment_130_to_135": int((f(mg.seg_130) != f(mg.seg_135)).sum()),
        "offsetting_check": ("Marginal rth was 37 under both 1.25 and 1.30. The matrix shows "
                             "whether that is the same 37 events or offsetting swaps."),
    }

    # ---------------------------------------------------------------- A3 re-derive
    dens = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))
    ev0b = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    a3 = {}
    for v in VARIANTS:
        sm = {k: s for k, s in seg_by_variant[v].items()}
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
        a3[str(v)] = {"n_rth_events": int(r_.ticker.nunique()),
                      "sigma_rth_median": float(e_[e_.seg_v == "rth"].sigma_log10_post_agg.median()),
                      "rth_derived_floor": fl,
                      "binding_rung_min": (int(min(ok)) if ok else None)}
    rungs = [x["binding_rung_min"] for x in a3.values()]
    a3_v = {"by_variant": a3, "all_agree_at_8": bool(set(rungs) == {8}),
            "verdict": ("D5 = 8 and D6 = {2, 8, 32} stand with ACET in the RTH pool"
                        if set(rungs) == {8} else
                        "BINDING RUNG MOVED -- stop and escalate, do not apply a new grid")}

    out = {"phase": "10c", "amendment": "A4", "config_hash": chash,
           "A1_closing_print": a1, "A2_evening_gap": gap,
           "A2_segments": {"evening": "prior session close -> 20:00 ET",
                           "premarket": "04:00 -> 09:30 ET",
                           "rth": "09:30 ET -> session close",
                           "retired": ["post", "outside_redefined_day"]},
           "A3_rederivation": a3_v, "D_migration": dsec,
           "source": "research/phase_10c/a6_conditions.py:main"}
    c10c.write_json(rel(f"{ART}/a6_conditions_analysis.json"), out)

    print("A1.2 near-close prints:", len(near), "across", len(rows), "events")
    print("   codes in |t-close|<=1s:", a1["A1_2_distribution"]["code_counts_whole_window"])
    print("   codes AFTER close only:", a1["A1_2_distribution"]["code_counts_after_close_only"])
    print("\nA1.3 code dictionary available in repo:",
          a1["A1_3_code_definitions"]["available_in_repo"])
    print("\nA2 20:00-04:00 anchors by variant:", gap["by_variant"],
          "-> measured empty:", gap["measured_empty"])
    print("\nA3 binding rung by variant:", {k: v["binding_rung_min"] for k, v in a3.items()},
          "rth n:", {k: v["n_rth_events"] for k, v in a3.items()})
    print("  ", a3_v["verdict"])
    print("\nD segment changes: 1.25->1.30:", dsec["n_events_changing_segment_125_to_130"],
          " 1.30->1.35:", dsec["n_events_changing_segment_130_to_135"])
    print("   marginals:", dsec["marginals"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
