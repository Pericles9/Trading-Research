"""
v0-T2: the two qualification gates, applied at each candidate's first rising edge.

Gate 1 -- level.  score >= the 75th percentile of the score's own distribution across all
                  candidate moments. The brief's declared v0 default, not fitted.
Gate 2 -- cross-section.  score is the highest among all candidates whose gate window is
                  concurrently live at that same moment. Liveness is the gate's own
                  window-close definition: [entry_ts, natural_exit_ts] of each candidate's
                  first window.

The concurrency distribution is reported alongside, because gate 2 cannot be read without it.
A candidate alone in its live set passes gate 2 trivially -- that class is counted separately
and never silently pooled with a candidate that won a real contest.

Gate 1's percentile is taken over this population, so it is in-sample by construction. Stated
here and in the report rather than hidden.

Usage: .venv/Scripts/python.exe research/relative_momentum_v0/t2_gates.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v0 import common as C  # noqa: E402

IN = f"{C.ART}/t1_scored.parquet"
OUT_JSON = f"{C.ART}/t2_gates.json"
OUT_PARQUET = f"{C.ART}/t2_gated.parquet"


def main() -> int:
    cfg = C.load_cfg()
    pct = cfg["facet2_qualification"]["gate_1_level"]["percentile"]

    d = pd.read_parquet(C.REPO / IN)
    s = d[d["score_available"]].copy()

    # ---- gate 1: level -----------------------------------------------------
    threshold = float(np.quantile(s["score"].to_numpy(), pct / 100.0))
    d["gate1_level"] = d["score_available"] & (d["score"] >= threshold)

    # ---- concurrency and gate 2: cross-section -----------------------------
    ent = s["entry_ts"].to_numpy(dtype=np.int64)
    ext = s["natural_exit_ts"].to_numpy(dtype=np.int64)
    sc = s["score"].to_numpy(dtype=float)

    n_live = np.zeros(len(s), dtype=int)
    is_max = np.zeros(len(s), dtype=bool)
    rank = np.zeros(len(s), dtype=int)
    runner_up_ratio = np.full(len(s), np.nan)

    for i in range(len(s)):
        tau = ent[i]
        live = (ent <= tau) & (ext >= tau)      # includes i itself
        n_live[i] = int(live.sum())
        vals = sc[live]
        is_max[i] = bool(sc[i] >= vals.max())
        rank[i] = int((vals > sc[i]).sum()) + 1
        if vals.size >= 2:
            srt = np.sort(vals)[::-1]
            runner_up_ratio[i] = srt[0] / srt[1] if srt[1] > 0 else np.inf

    s["n_live_at_tau"] = n_live
    s["gate2_is_max"] = is_max
    s["score_rank_in_live_set"] = rank
    s["live_leader_margin_ratio"] = runner_up_ratio
    s["gate2_trivial_singleton"] = is_max & (n_live == 1)

    d = d.merge(s[["key", "n_live_at_tau", "gate2_is_max", "score_rank_in_live_set",
                   "live_leader_margin_ratio", "gate2_trivial_singleton"]],
                on="key", how="left")
    d["gate2_is_max"] = d["gate2_is_max"].fillna(False).astype(bool)
    d["gate2_trivial_singleton"] = d["gate2_trivial_singleton"].fillna(False).astype(bool)
    d["policy_a"] = True                                  # every first-window signal
    d["policy_b"] = d["gate1_level"] & d["gate2_is_max"]  # both gates
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    nl = s["n_live_at_tau"].to_numpy()
    conc = {
        "n_candidate_moments": int(len(s)),
        "n_live_quantiles": {f"p{int(p * 100)}": float(np.quantile(nl, p))
                             for p in (0, .25, .5, .75, .9, .95, 1.0)},
        "distribution": {str(int(k)): int(v) for k, v in
                         pd.Series(nl).value_counts().sort_index().items()},
        "share_alone": float((nl == 1).mean()),
        "share_two_or_more": float((nl >= 2).mean()),
        "reading": "gate 2 only has something to decide where n_live >= 2. Below that it is "
                   "a formality and the candidate passes trivially.",
    }

    contested = s[s["n_live_at_tau"] >= 2]
    summary = {
        "task": "v0-T2 qualification gates",
        "config_hash": C.cfg_hash(),
        "gate_1": {
            "rule": cfg["facet2_qualification"]["gate_1_level"]["rule"],
            "percentile": pct,
            "threshold_score": threshold,
            "n_pass": int(d["gate1_level"].sum()),
            "share_pass": float(d["gate1_level"].sum() / d["score_available"].sum()),
            "in_sample_note": "the percentile is computed on this same population, so gate 1 "
                              "passes exactly 25% of scorable candidates by construction. It "
                              "is a declared v0 default, not a fitted threshold, but it is "
                              "not an out-of-sample level either.",
        },
        "gate_2": {
            "rule": cfg["facet2_qualification"]["gate_2_cross_section"]["rule"],
            "liveness": cfg["facet2_qualification"]["gate_2_cross_section"]["liveness"],
            "n_pass": int(d["gate2_is_max"].sum()),
            "n_pass_trivial_singleton": int(d["gate2_trivial_singleton"].sum()),
            "n_pass_contested": int((d["gate2_is_max"] & ~d["gate2_trivial_singleton"]).sum()),
            "share_pass": float(d["gate2_is_max"].sum() / d["score_available"].sum()),
        },
        "concurrency": conc,
        "contested_moments": {
            "n": int(len(contested)),
            "leader_margin_ratio_quantiles": {
                f"p{int(p * 100)}": float(np.nanquantile(
                    contested["live_leader_margin_ratio"].to_numpy(), p))
                for p in (.25, .5, .75, .95)} if len(contested) else {},
            "margin_note": "ratio of the live set's top score to its runner-up. A ratio near 1 "
                           "means 'highest' was a coin flip at that moment.",
        },
        "policies": {
            "A_n": int(d["policy_a"].sum()),
            "B_n": int(d["policy_b"].sum()),
            "B_share_of_A": float(d["policy_b"].sum() / d["policy_a"].sum()),
            "B_n_from_trivial_singletons": int(
                (d["policy_b"] & d["gate2_trivial_singleton"]).sum()),
            "B_n_from_contested": int(
                (d["policy_b"] & ~d["gate2_trivial_singleton"]).sum()),
        },
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
