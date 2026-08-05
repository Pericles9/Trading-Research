"""
Phase 10 v2 R1.4 -- cross-check the derived anchor against Phase 8's det_minute.

Same rule, same threshold, same tick archive, so they should agree to the
minute. This is a free validation of both.

Convention note, stated rather than reconciled away: Phase 8's `det_minute` is
the minute INDEX CONTAINING the crossing (a floor). D7's 60s poll is the first
minute boundary AT OR AFTER the crossing (a ceil). They therefore differ by
exactly 1 whenever the crossing is not itself on a boundary. Both comparisons
are reported:

  exact analogue  floor(crossing) vs det_minute          -- the real test
  as-specified    60s-poll minute  vs det_minute          -- R1.4a as written

R1.4b: disagreement beyond tolerance is a HARD STOP, not a reconciliation
exercise. Nothing here adjusts either side to fit the other.

Usage: .venv/Scripts/python.exe research/phase_10/v2_r14_phase8_check.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, config_hash_v2, load_config_v2, quantiles, rel, session_window, write_json,
)

OUT = "v2_r14_phase8_crosscheck.json"


def main() -> int:
    cfg = load_config_v2()
    chash = config_hash_v2()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cc = cfg["phase8_crosscheck"]
    thr = cc["compare_at"]["threshold"]
    poll = cc["compare_at"]["poll_interval_seconds"]
    tol = cc["tolerance_minutes"]

    det = pd.read_parquet(os.path.join(out_dir, "v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    d = det[np.isclose(det["threshold"], thr)].copy()

    p8 = pd.read_parquet(rel(cfg["paths"]["phase8_detection_anchors"])).rename(
        columns={"mp": "momentum_pct"})
    p8["event_date_canonical"] = p8["event_date_canonical"].astype(str)
    p8["momentum_pct"] = p8["momentum_pct"].round(2)
    m = d.merge(p8[COHORT_KEY + ["det_minute", "det_undefined", "tick_close_t_minus_1_rth",
                                 "det_segment"]],
                on=COHORT_KEY, how="left", suffixes=("", "_p8"))

    # crossing minute (floor) -- the exact analogue of det_minute
    starts = {r.event_date_canonical: session_window(r.event_date_canonical, 0)["start_ns"]
              for r in m.itertuples(index=False)}
    m["cross_minute_floor"] = [
        np.floor((r.cross_ns - starts[r.event_date_canonical]) / 60e9) if pd.notna(r.cross_ns) else np.nan
        for r in m.itertuples(index=False)
    ]
    m["poll60_minute"] = m[f"det_seconds_from_open_poll{poll}"] / 60.0

    comparable = m[(~m["never_crosses"]) & (~m["det_undefined"].fillna(True))].copy()
    comparable["diff_floor"] = comparable["cross_minute_floor"] - comparable["det_minute"]
    comparable["diff_poll60"] = comparable["poll60_minute"] - comparable["det_minute"]

    pooled = comparable[comparable["cohort_group"].isin(POOLED)]

    def agreement(col):
        v = comparable[col].dropna()
        return {
            "n": int(v.size),
            "n_exact": int((v == 0).sum()),
            "share_exact": float((v == 0).mean()) if v.size else None,
            "n_within_tolerance": int((v.abs() <= tol).sum()),
            "share_within_tolerance": float((v.abs() <= tol).mean()) if v.size else None,
            "n_beyond_tolerance": int((v.abs() > tol).sum()),
            "share_beyond_tolerance": float((v.abs() > tol).mean()) if v.size else None,
            "diff_minutes": quantiles(v),
        }

    ag_floor = agreement("diff_floor")
    ag_poll = agreement("diff_poll60")

    # reference-price cross-check: same definition, independently recomputed
    rp = comparable[["reference_price", "tick_close_t_minus_1_rth"]].dropna()
    rel_dev = ((rp["reference_price"] - rp["tick_close_t_minus_1_rth"]).abs()
               / rp["tick_close_t_minus_1_rth"].replace(0, np.nan))

    row8_thr = cfg["failure_criteria"]["row_8"]["threshold_max_share"]
    observed_row8 = ag_poll["share_beyond_tolerance"]

    worst = comparable.reindex(
        comparable["diff_floor"].abs().sort_values(ascending=False).index
    ).head(10)[COHORT_KEY + ["cohort_group", "cross_minute_floor", "poll60_minute",
                            "det_minute", "diff_floor", "det_segment_poll1", "det_segment"]]

    summary = {
        "phase": "10", "version": "v2", "task": "R1.4", "config_hash": chash,
        "compare_at": {"threshold": thr, "poll_interval_seconds": poll,
                       "tolerance_minutes": tol},
        "convention_note": (
            "Phase 8 det_minute is the minute CONTAINING the crossing (floor). The D7 60s poll is "
            "the first minute boundary AT OR AFTER the crossing (ceil). They differ by exactly 1 "
            "whenever the crossing is not on a boundary. The floor comparison is the exact "
            "analogue and is the real test; the 60s-poll comparison is reported as R1.4a specifies. "
            "Neither side was adjusted to fit the other (R1.4b)."),
        "population": {
            "n_cohort_rows_at_threshold": int(len(d)),
            "n_never_crosses_here": int(d["never_crosses"].sum()),
            "n_det_undefined_phase8": int(m["det_undefined"].fillna(True).sum()),
            "n_comparable": int(len(comparable)),
            "n_comparable_pooled": int(len(pooled)),
            "excluded_note": "events never-crossing here or det_undefined in Phase 8 are excluded "
                             "from the comparison and counted above",
        },
        "agreement_floor_exact_analogue": ag_floor,
        "agreement_poll60_as_specified": ag_poll,
        "reference_price_crosscheck": {
            "n": int(len(rp)),
            "n_exact": int((rel_dev == 0).sum()),
            "share_within_1e_6": float((rel_dev <= 1e-6).mean()) if len(rel_dev) else None,
            "max_relative_deviation": float(rel_dev.max()) if len(rel_dev) else None,
            "note": "D7 recomputes the same definition Phase 8 used (tick_close_t_minus_1_rth). "
                    "Agreement here validates the reference price independently of the crossing.",
        },
        "largest_disagreements_floor": worst.to_dict("records"),
        "failure_row_8": {
            "mode": cfg["failure_criteria"]["row_8"]["mode"],
            "observed_share_beyond_tolerance": observed_row8,
            "threshold": row8_thr,
            "pass": bool(observed_row8 is not None and observed_row8 <= row8_thr),
            "evaluated_on": "the 60s-poll comparison as R1.4a specifies",
            "floor_comparison_share_beyond_tolerance": ag_floor["share_beyond_tolerance"],
        },
        "source": "research/phase_10/v2_r14_phase8_check.py:main",
    }
    write_json(os.path.join(out_dir, OUT), summary)

    print(f"comparable: {len(comparable)} events "
          f"(never-crosses here {int(d['never_crosses'].sum())}, "
          f"det_undefined in P8 {int(m['det_undefined'].fillna(True).sum())})")
    print(f"floor vs det_minute : exact {ag_floor['n_exact']}/{ag_floor['n']} "
          f"({ag_floor['share_exact']:.3f}), within +/-{tol} min "
          f"{ag_floor['share_within_tolerance']:.3f}, beyond {ag_floor['share_beyond_tolerance']:.3f}")
    print(f"60s-poll vs det_min : exact {ag_poll['n_exact']}/{ag_poll['n']} "
          f"({ag_poll['share_exact']:.3f}), within +/-{tol} min "
          f"{ag_poll['share_within_tolerance']:.3f}, beyond {ag_poll['share_beyond_tolerance']:.3f}")
    print(f"reference price     : {summary['reference_price_crosscheck']['share_within_1e_6']:.4f} "
          f"within 1e-6 relative, max dev "
          f"{summary['reference_price_crosscheck']['max_relative_deviation']:.3e}")
    print(f"failure row 8: observed {observed_row8:.4f} vs threshold {row8_thr} -> "
          f"{'PASS' if summary['failure_row_8']['pass'] else 'FAIL'}")
    return 0 if summary["failure_row_8"]["pass"] else 8


if __name__ == "__main__":
    raise SystemExit(main())
