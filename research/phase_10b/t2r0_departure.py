"""
Phase 10b A10b.1 T2-R0 -- departure direction diagnostic.

READ-ONLY on the existing t2_control_curves.parquet. No simulation, nothing
rerun. Decomposes every out-of-band excursion into ABOVE the upper edge and
BELOW the lower edge, per control, per bandwidth, per rung.

T2-R0b fixes the interpretation in advance: a curve falling BELOW a matched-
Poisson band is not evidence of clustering, it is the opposite, and counting it
as a control failure is a specification defect.

T2-R0c is a HARD STOP if C1's out-of-band share is predominantly upward
(upward share alone >= 0.05 of eligible rungs) -- that would not be explained by
the amendment.

Usage: .venv/Scripts/python.exe research/phase_10b/t2r0_departure.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from t1_plateau import cfg_hash, load_cfg  # noqa: E402

OUT = "results/phase_10b/artifacts/t2r0_departure_direction.json"
CURVES = "results/phase_10b/artifacts/t2_control_curves.parquet"


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    up_max = 0.05
    d = pd.read_parquet(rel(CURVES))
    d = d[d["eligible"] & d["band_lo"].notna() & d["allan"].notna()].copy()
    d["above"] = d["allan"] > d["band_hi"]
    d["below"] = d["allan"] < d["band_lo"]
    d["within"] = ~(d["above"] | d["below"])

    by = []
    for (ctrl, h), g in d.groupby(["control", "h"]):
        g = g.sort_values("T")
        by.append({
            "control": ctrl, "h": float(h),
            "h_eligible": bool(g["h_eligible"].iloc[0]) if "h_eligible" in g else True,
            "n_eligible_rungs": int(len(g)),
            "share_above": float(g["above"].mean()),
            "share_below": float(g["below"].mean()),
            "share_inside": float(g["within"].mean()),
            "rungs_above_s": [float(x) for x in g.loc[g["above"], "T"]],
            "rungs_below_s": [float(x) for x in g.loc[g["below"], "T"]],
        })
    tab = pd.DataFrame(by)

    # T2-R0a: the two headline failures, decomposed
    def cell(ctrl, h):
        r = tab[(tab["control"] == ctrl) & (np.isclose(tab["h"], h))]
        return r.iloc[0].to_dict() if len(r) else None

    headline = {"C1_h64": cell("C1", 64.0), "C2_h16384": cell("C2", 16384.0)}

    # T2-R0c: hard-stop check on C1, over ELIGIBLE bandwidths only
    c1 = tab[(tab["control"] == "C1") & tab["h_eligible"]]
    c1_up_max = float(c1["share_above"].max()) if len(c1) else float("nan")
    c1_worst_h = float(c1.loc[c1["share_above"].idxmax(), "h"]) if len(c1) else None
    fired = bool(c1_up_max >= up_max)

    # rung profile: do the upward excursions cluster at one end of the ladder?
    prof = {}
    for ctrl in sorted(d["control"].unique()):
        g = d[(d["control"] == ctrl)]
        if "h_eligible" in g:
            g = g[g["h_eligible"]]
        pr = g.groupby("T")[["above", "below"]].mean().reset_index().sort_values("T")
        prof[ctrl] = {"T": [float(x) for x in pr["T"]],
                      "share_above": [float(x) for x in pr["above"]],
                      "share_below": [float(x) for x in pr["below"]]}

    out = {
        "phase": "10b", "task": "T2-R0", "amendment": "A10b.1", "config_hash": chash,
        "read_only": True, "source_artifact": CURVES,
        "note": ("Decomposition of the ORIGINAL T2 run's out-of-band excursions. No simulation "
                 "was performed and nothing was rerun, per T2-R0d."),
        "t2_r0b_interpretation": (
            "Fixed in advance: a curve falling BELOW a matched-Poisson band is not evidence of "
            "clustering, it is the opposite. Counting it as a control failure is a specification "
            "defect; under Change 3 it stops being counted."),
        "by_control_bandwidth": by,
        "t2_r0a_headline": headline,
        "t2_r0c_hard_stop_check": {
            "rule": "C1 upward share alone >= 0.05 of eligible rungs, at any eligible bandwidth",
            "threshold": up_max,
            "c1_max_share_above_over_eligible_h": c1_up_max,
            "c1_worst_bandwidth_s": c1_worst_h,
            "c1_share_above_by_h": {f"h={r['h']:g}": r["share_above"]
                                    for r in by if r["control"] == "C1" and r["h_eligible"]},
            "expected_by_chance": ("T2e band coverage 0.9348-0.9460 against a nominal 95% band, so "
                                   "~6% of rungs fall outside by chance and ~3% above"),
            "FIRED": fired,
        },
        "rung_profile": prof,
        "source": "research/phase_10b/t2r0_departure.py:main",
        "artifacts": [OUT],
    }
    write_json(rel(OUT), out)

    print("T2-R0 departure direction (eligible bandwidths, original T2 run)\n")
    print(f"{'ctrl':5s} {'h (s)':>9s} {'n':>4s} {'above':>7s} {'below':>7s} {'inside':>7s}  elig")
    for r in by:
        print(f"{r['control']:5s} {r['h']:9g} {r['n_eligible_rungs']:4d} "
              f"{r['share_above']:7.3f} {r['share_below']:7.3f} {r['share_inside']:7.3f}  "
              f"{'yes' if r['h_eligible'] else 'no'}")
    print("\nT2-R0a headline decomposition:")
    for k, r in headline.items():
        if r:
            print(f"  {k}: inside {r['share_inside']:.3f} = 1 - above {r['share_above']:.3f} "
                  f"- below {r['share_below']:.3f}   (n={r['n_eligible_rungs']} eligible rungs)")
    print(f"\nT2-R0c: C1 max upward share over eligible h = {c1_up_max:.4f} "
          f"(threshold {up_max}) at h={c1_worst_h:g} s")
    print("  ROW 4a FIRED -- HARD STOP" if fired else "  row 4a does not fire")
    return 2 if fired else 0


if __name__ == "__main__":
    raise SystemExit(main())
