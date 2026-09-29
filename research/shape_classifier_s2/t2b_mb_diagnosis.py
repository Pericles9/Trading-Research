"""
Shape classifier S2, T2b -- diagnosis of the minute-bar crossing mismatch found in the T2 check (measurement only;
written at the row 3 HARD STOP, fixes nothing).

T2 recomputes the minute-bar-close crossing (for Cooper's R1 tau_close_sensitive state) with b1's
common.first_crossing, but on the 04:00-20:00 SLICE of the prints; b1 called it on the FULL arrays with lo/hi.
is_spike reads each candidate's neighbours, so the slice's first print has no predecessor and can never be a spike,
while on the full arrays its pre-04:00 predecessor can make it one. For every event where T2's crossing is more than
128 ns (the stored value's rounding) from b1's stored tau_ns_mb, this re-runs both calls and records which one
reproduces b1.

Writes artifacts/t2b_mb_diagnosis.parquet, t2b_mb_diagnosis.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t2b_mb_diagnosis.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

C1 = S.C1
MB_CLOSE = "results/relative_momentum/r0/artifacts/t0a2_prior_close.parquet"


def main() -> int:
    cfg = json.load(open(S.REPO / "config/attention_excursion_b1.json"))["t2_tau"]
    dev, agree = cfg["spike_guard"]["deviation_threshold"], cfg["spike_guard"]["neighbour_agreement"]
    meta = pd.read_parquet(S.art("t2_event_meta.parquet"), columns=["event_id", "tau_mb_exact_ns"])
    b1 = pd.read_parquet(S.src("b1_tau"), columns=["event_id", "event_date_canonical", "tau_ns_mb", "tau_close_sensitive"])
    mb = pd.read_parquet(S.REPO / MB_CLOSE, columns=["event_id", "prior_close"])
    m = meta.merge(b1, on="event_id").merge(mb, on="event_id")
    m = m[m["tau_mb_exact_ns"].notna() & m["tau_ns_mb"].notna()].copy()
    m["t2_minus_b1_ns"] = m["tau_mb_exact_ns"].astype("int64") - S.as_int64(m["tau_ns_mb"]).astype("int64")
    bad = m[m["t2_minus_b1_ns"].abs() > S.TAU_ROUND_NS]
    rows = []
    for r in bad.itertuples():
        tr = C1.read_trades(r.event_id, with_conditions=False)
        ts, px = tr["ts"], tr["px"]
        lo = int(np.searchsorted(ts, C1.et_ns(r.event_date_canonical, "04:00:00"), "left"))
        hi = int(np.searchsorted(ts, C1.et_ns(r.event_date_canonical, "20:00:00"), "right"))
        lvl = cfg["crossing_multiple"] * r.prior_close
        i_full, sk_full = C1.first_crossing(px, lo, hi, lvl, dev, agree)
        i_sl, sk_sl = C1.first_crossing(px[lo:hi], 0, hi - lo, lvl, dev, agree)
        full_ns = int(ts[i_full]) if i_full is not None else None
        rows.append({"event_id": r.event_id, "t2_minus_b1_s": r.t2_minus_b1_ns / 1e9,
                     "full_call_minus_b1_ns": (full_ns - int(S.as_int64(pd.Series([r.tau_ns_mb]))[0])) if full_ns is not None else None,
                     "slice_call_index": i_sl, "slice_call_is_first_print_of_slice": i_sl == 0,
                     "full_call_spikes_skipped": sk_full, "slice_call_spikes_skipped": sk_sl,
                     "b1_tau_close_sensitive": bool(r.tau_close_sensitive)})
    d = pd.DataFrame(rows)
    d["config_hash"] = S.cfg_hash()
    d.to_parquet(S.art("t2b_mb_diagnosis.parquet"), index=False)
    out = {"config_hash": S.cfg_hash(), "events_compared": int(len(m)), "events_beyond_128ns": int(len(d)),
           "t2_earlier_than_b1": int((d["t2_minus_b1_s"] < 0).sum()),
           "slice_call_takes_first_print_of_slice": int(d["slice_call_is_first_print_of_slice"].sum()),
           "full_call_reproduces_b1_within_128ns": int((d["full_call_minus_b1_ns"].abs() <= S.TAU_ROUND_NS).sum()),
           "t2_minus_b1_s_quantiles": {str(q): float(d["t2_minus_b1_s"].quantile(q)) for q in (0.0, 0.5, 1.0)},
           "cause": "T2 called first_crossing on the 04:00-20:00 slice; the slice's first print has no predecessor so is never a spike, "
                    "while b1's full-array call judges it against its pre-04:00 predecessor and skips it",
           "scope": "Cooper R1 tcs_state input only; the crossing T2 used is a real print, used only once it has happened (no timing violation)",
           "not_fixed": "found at the row 3 HARD STOP; the fix (call first_crossing on the full arrays) waits for instruction"}
    S.write_json("t2b_mb_diagnosis.json", out)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
