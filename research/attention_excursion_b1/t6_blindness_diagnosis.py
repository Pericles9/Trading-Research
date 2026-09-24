"""
Brief 1, T6 -- diagnosis of the blindness checks that failed. Reads; fixes nothing (HARD STOP).

For every rescale check over 1e-9: recompute the vector on the original and rescaled prints with the
same instrument, record which components moved, the peak index before and after, and whether the top
bucket prices are exactly tied on the original path (the condition under which a floating-point
rescale can reorder argmax). Writes artifacts/t6_blindness_failures.json.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t6_blindness_diagnosis.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import instruments as I  # noqa: E402

COMPS = ["u_peak", "rise_s", "fall_s", "dip_before_peak_s", "terminal_s", "sigma_b_bp", "sigma_path_bp", "rise_bp", "fall_bp"]


def main() -> int:
    bl = pd.read_parquet(C.art("t6_blindness_rescale.parquet"))
    bad = bl[bl["max_abs_diff"] > 1e-9]
    t2 = pd.read_parquet(C.art("t2_tau.parquet")).set_index("event_id")
    rows = []
    for r in bad.itertuples():
        tau = int(t2.loc[r.event_id, "tau_ns"])
        d = t2.loc[r.event_id, "event_date_canonical"]
        tp = float(t2.loc[r.event_id, "tau_price"])
        tr = C.read_trades(r.event_id, with_conditions=False)
        a = int(np.searchsorted(tr["ts"], tau, "right"))
        b = int(np.searchsorted(tr["ts"], C.et_ns(d, "20:00:00"), "right"))
        ts, px, sz = tr["ts"][a:b], tr["px"][a:b], tr["sz"][a:b]
        v0 = I.excursion_vector(tau, tp, ts, px, sz, int(r.N))
        v1 = I.excursion_vector(tau, tp * r.factor, ts, px * r.factor, sz, int(r.N))
        lp = np.log(np.r_[tp, v0["_bucket_price"]])
        top = lp.max()
        tied = np.flatnonzero(np.abs(lp - top) <= 1e-12)
        rows.append({"event_id": r.event_id, "N": int(r.N), "factor": float(r.factor), "max_abs_diff": float(r.max_abs_diff),
                     "i_peak_original": int(v0["i_peak"]), "i_peak_rescaled": int(v1["i_peak"]),
                     "positions_tied_at_the_top_original": tied.tolist(),
                     "components_moved": {c: [float(v0[c]), float(v1[c])] for c in COMPS if abs(v0[c] - v1[c]) > 1e-9}})
    other = bl[bl["max_abs_diff"] <= 1e-9]["max_abs_diff"]
    out = {"config_hash": C.cfg_hash(), "checks": int(len(bl)), "failed_checks": int(len(bad)),
           "failed_events": sorted(bad["event_id"].unique().tolist()), "failures": rows,
           "max_abs_diff_among_passing_checks": float(other.max()) if len(other) else None,
           "every_failure_has_a_tied_top": bool(all(len(x["positions_tied_at_the_top_original"]) > 1 for x in rows)),
           "every_failure_moves_u_peak_only": bool(all(set(x["components_moved"]) <= {"u_peak"} for x in rows))}
    C.write_json(f"{C.ART}/t6_blindness_failures.json", out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
