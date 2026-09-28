"""
v0-T1: attention score v0 = relative volume, causal, at each candidate's first rising edge.

    score = (dollar volume of all prints in [tau - 600s, tau]) / B_e

tau is the candidate's own first rising-edge entry_ts. The window ends at tau and opens
backward; common.window_dollar_volume asserts in code that no print after tau enters it.
Volume is read from each event's own filtered/ trades.parquet -- the same physical archive,
read directly rather than through filtered_trades, because a targeted range query against
that 4.9B-row table does not prune (measured: 9.5 s for one 10-minute window).

B_e is E2's 3-prior-session baseline, reused unchanged: mean dollar volume per 10-minute RTH
block over the available prior sessions. n_baseline_sessions is carried and facets every
panel -- a one-session baseline is a different measurement from a three-session one.

KNOWN SCALE MISMATCH, carried as a facet rather than corrected: B_e is RTH-scoped, so for a
candidate whose tau falls in premarket or after hours the ratio compares an extended-hours
window against a regular-session baseline. session_bucket is carried for exactly this reason.

D4: price and size come from the tick archive. No spine numeric column enters.

Usage: .venv/Scripts/python.exe research/relative_momentum_v0/t1_score.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v0 import common as C  # noqa: E402

IN = f"{C.ART}/t0_candidates.parquet"
OUT_JSON = f"{C.ART}/t1_score.json"
OUT_PARQUET = f"{C.ART}/t1_scored.parquet"


def main() -> int:
    cfg = C.load_cfg()
    W = cfg["facet2_qualification"]["score_v0"]["W_seconds"]

    cand = pd.read_parquet(C.REPO / IN)
    rows = []
    t0 = time.time()
    for i, r in enumerate(cand.itertuples(index=False), 1):
        if not r.folder_available:
            rows.append({"key": r.key, "ok": False, "reason": "no_folder"})
            continue
        res = C.window_dollar_volume(r.folder, int(r.entry_ts), W)
        rows.append({"key": r.key, **res})
        if i % 250 == 0:
            print(f"  {i}/{len(cand)}  {time.time() - t0:.0f}s", flush=True)
    vol = pd.DataFrame(rows)

    d = cand.merge(vol, on="key", how="left")
    assert len(d) == len(cand), "volume join changed the row count"

    be = pd.to_numeric(d["B_e"], errors="coerce")
    d["window_dollar_volume"] = pd.to_numeric(d["dollar_volume"], errors="coerce")
    d["score"] = np.where(d["baseline_available"] & (be > 0) & d["window_dollar_volume"].notna(),
                          d["window_dollar_volume"] / be, np.nan)
    d["score_available"] = d["score"].notna()

    # move_at at the candidate moment -- the diagnostic's variable, computed here so both
    # tasks read one artifact. Causal: entry_price is known at tau.
    pc = pd.to_numeric(d["prior_close"], errors="coerce")
    d["move_at"] = np.where(d["prior_close_available"] & (pc > 0),
                            (d["entry_price"] - pc) / pc, np.nan)

    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    s = d.loc[d["score_available"], "score"]
    zero_vol = int((d["window_dollar_volume"] == 0).sum())

    def qd(x, ps=(0, .05, .25, .5, .75, .95, 1.0)):
        return {f"p{int(p * 100)}": (float(np.quantile(x, p)) if len(x) else None) for p in ps}

    summary = {
        "task": "v0-T1 attention score v0 (relative volume)",
        "config_hash": C.cfg_hash(),
        "formula": cfg["facet2_qualification"]["score_v0"]["formula"],
        "W_seconds": W,
        "causality": "asserted in common.window_dollar_volume: no print with "
                     "sip_timestamp > tau enters any returned quantity.",
        "n_candidates": int(len(d)),
        "n_score_available": int(d["score_available"].sum()),
        "n_score_unavailable": int((~d["score_available"]).sum()),
        "n_zero_volume_windows": zero_vol,
        "zero_vs_unavailable_note": "a zero-print window is a measured zero (score = 0) and is "
                                    "NOT the same state as an unavailable score. Both are "
                                    "reported; neither is dropped.",
        "score_quantiles": qd(s.to_numpy()),
        "score_by_n_baseline_sessions": {
            str(int(k)): {"n": int(len(g)), **qd(g["score"].dropna().to_numpy(), (.25, .5, .75))}
            for k, g in d[d["score_available"]].groupby("n_baseline_sessions")
        },
        "score_by_session_bucket": {
            str(k): {"n": int(len(g)),
                     **qd(g["score"].dropna().to_numpy(), (.25, .5, .75))}
            for k, g in d[d["score_available"]].groupby("session_bucket")
        },
        "session_bucket_note": "B_e is RTH-scoped. A premarket or after-hours tau compares an "
                               "extended-hours window against a regular-session baseline. "
                               "Carried as a facet, not corrected.",
        "window_prints_quantiles": qd(pd.to_numeric(d["n_prints"], errors="coerce")
                                      .dropna().to_numpy(), (.05, .25, .5, .75, .95)),
        "move_at_quantiles": qd(d["move_at"].dropna().to_numpy()),
        "n_move_at_available": int(d["move_at"].notna().sum()),
        "elapsed_sec": round(time.time() - t0, 1),
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
