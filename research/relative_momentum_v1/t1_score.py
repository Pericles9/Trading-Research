"""
v1-T1: the attention score at the NEW entry instant.

The 10-minute trailing dollar volume was already read in T0, at the gap-gated entry trigger
(tau = ts[i], the trigger tick, not the fill tick), with the causality assertion in
common.window_dollar_volume. This task divides it by E2's B_e and reports the distribution.

Unchanged from v0 by instruction: one measure, relative volume, 10-minute window, E2's
3-session baseline reused as-is.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/t1_score.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import common as C  # noqa: E402

IN = f"{C.ART}/t0_candidates.parquet"
OUT_JSON = f"{C.ART}/t1_score.json"
OUT_PARQUET = f"{C.ART}/t1_scored.parquet"


def qd(x, ps=(0, .05, .25, .5, .75, .95, 1.0)):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return {f"p{int(p * 100)}": (round(float(np.quantile(x, p)), 4) if x.size else None)
            for p in ps}


def main() -> int:
    d = pd.read_parquet(C.REPO / IN)

    be = pd.read_parquet(C.REPO / C.BASELINE)
    d = d.merge(be[["event_id", "B_e", "n_baseline_sessions"]], on="event_id", how="left")

    bev = pd.to_numeric(d["B_e"], errors="coerce")
    dv = pd.to_numeric(d["dollar_volume"], errors="coerce")
    d["score"] = np.where(d["ok"].fillna(False) & (bev > 0) & dv.notna(), dv / bev, np.nan)
    d["score_available"] = d["score"].notna()
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    ok = d[d["ok"].fillna(False)]
    s = d.loc[d["score_available"], "score"]

    summary = {
        "task": "v1-T1 attention score at the gap-gated entry instant",
        "config_hash": C.cfg_hash(),
        "formula": "dollar volume in [tau - 600s, tau] / B_e, tau = the gap-gated entry trigger",
        "unchanged_from_v0": "one measure, relative volume, 10-min window, E2's 3-session B_e",
        "n_entries": int(len(ok)),
        "n_score_available": int(d["score_available"].sum()),
        "n_score_unavailable": int((ok.shape[0] - d["score_available"].sum())),
        "n_zero_volume_windows": int((dv == 0).sum()),
        "score_quantiles": qd(s.to_numpy()),
        "score_by_n_baseline_sessions": {
            str(int(k)): {"n": int(len(g)), **qd(g["score"], (.25, .5, .75))}
            for k, g in d[d["score_available"]].groupby("n_baseline_sessions")},
        "score_by_entry_kind": {
            str(k): {"n": int(len(g)), **qd(g["score"], (.25, .5, .75))}
            for k, g in d[d["score_available"]].groupby("entry_kind")},
        "score_by_session_bucket": {
            str(k): {"n": int(len(g)), **qd(g["score"], (.25, .5, .75))}
            for k, g in d[d["score_available"]].groupby("session_bucket")},
        "session_bucket_note": "B_e is RTH-scoped; a pre-market tau compares an extended-hours "
                               "window against a regular-session baseline. Carried as a facet.",
        "v0_score_median_for_reference": 13.41,
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
