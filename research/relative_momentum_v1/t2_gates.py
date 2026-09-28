"""
v1-T2 (Fix 1): gate 1 made causal, plus gate 2 unchanged.

GATE 1, the fix. v0 compared each score against the 75th percentile of the score's own
distribution over the whole backtest sample -- a level that cannot be known at decision time.
Here, at each candidate moment in chronological order:

    threshold(k) = 75th percentile of {score_j : tau_j < tau_k}, pooled across tickers

Strictly prior observations only. Fewer than 250 of them and gate 1 does not activate: the
candidate passes and is flagged gate1_warmup, so the different behaviour is visible in the
report rather than silent. Nothing in the rule depends on data from after the trade it gates.

GATE 2 is unchanged from v0: highest score among candidates whose window is live at that
moment, liveness being the gate's own window close. Uncontested passes are counted separately
and never pooled with a candidate that won a real contest.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/t2_gates.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import common as C  # noqa: E402

IN = f"{C.ART}/t1_scored.parquet"
OUT_JSON = f"{C.ART}/t2_gates.json"
OUT_PARQUET = f"{C.ART}/t2_gated.parquet"


def main() -> int:
    cfg = C.load_cfg()
    q = cfg["fix1_causal_gate1"]["percentile"] / 100.0
    min_n = cfg["fix1_causal_gate1"]["min_prior_observations"]

    d = pd.read_parquet(C.REPO / IN)
    s = d[d["score_available"]].sort_values("entry_ts").reset_index(drop=True).copy()

    # ---- Fix 1: expanding, strictly-prior percentile ----------------------
    thr, warm = C.expanding_quantile_threshold(s["score"].to_numpy(dtype=float), q, min_n)
    s["gate1_threshold_causal"] = thr
    s["gate1_warmup"] = warm
    s["gate1_level"] = np.where(warm, True, s["score"].to_numpy(dtype=float) >= thr)

    # the v0 threshold, recomputed on this population, for the like-for-like contrast
    thr_insample = float(np.quantile(s["score"].to_numpy(dtype=float), q))
    s["gate1_level_v0_style_insample"] = s["score"] >= thr_insample

    # ---- Gate 2, unchanged ------------------------------------------------
    ent = s["entry_ts"].to_numpy(dtype=np.int64)
    ext = s["natural_exit_ts"].to_numpy(dtype=np.int64)
    sc = s["score"].to_numpy(dtype=float)
    n_live = np.zeros(len(s), dtype=int)
    is_max = np.zeros(len(s), dtype=bool)
    margin = np.full(len(s), np.nan)
    for i in range(len(s)):
        tau = ent[i]
        live = (ent <= tau) & (ext >= tau)
        n_live[i] = int(live.sum())
        v = sc[live]
        is_max[i] = bool(sc[i] >= v.max())
        if v.size >= 2:
            srt = np.sort(v)[::-1]
            margin[i] = srt[0] / srt[1] if srt[1] > 0 else np.inf
    s["n_live_at_tau"] = n_live
    s["gate2_is_max"] = is_max
    s["live_leader_margin_ratio"] = margin
    s["gate2_trivial_singleton"] = is_max & (n_live == 1)

    s["policy_a"] = True
    s["policy_b"] = s["gate1_level"] & s["gate2_is_max"]
    s["policy_b_v0_style"] = s["gate1_level_v0_style_insample"] & s["gate2_is_max"]
    s.to_parquet(C.REPO / OUT_PARQUET, index=False)

    warm_n = int(s["gate1_warmup"].sum())
    live_hist = {str(int(k)): int(v) for k, v in
                 pd.Series(n_live).value_counts().sort_index().items()}
    post = s[~s["gate1_warmup"]]

    summary = {
        "task": "v1-T2 causal gate 1 (Fix 1) and gate 2",
        "config_hash": C.cfg_hash(),
        "gate_1_causal": {
            "rule": cfg["fix1_causal_gate1"]["rule"],
            "percentile": cfg["fix1_causal_gate1"]["percentile"],
            "min_prior_observations": min_n,
            "n_candidates": int(len(s)),
            "n_warmup": warm_n,
            "share_warmup": round(warm_n / len(s), 4),
            "warmup_ends_at": s.loc[s["gate1_warmup"], "date"].max() if warm_n else None,
            "warmup_note": "warmup candidates pass gate 1 by default and are flagged. The share "
                           "is reported per policy in T3 so the two regimes are never blended "
                           "silently.",
            "n_pass_total": int(s["gate1_level"].sum()),
            "n_pass_post_warmup": int(post["gate1_level"].sum()),
            "share_pass_post_warmup": round(float(post["gate1_level"].mean()), 4)
                                      if len(post) else None,
            "threshold_quantiles_post_warmup": {
                f"p{int(p * 100)}": round(float(np.nanquantile(
                    post["gate1_threshold_causal"], p)), 2) for p in (0, .25, .5, .75, 1.0)}
                if len(post) else {},
            "threshold_first": round(float(post["gate1_threshold_causal"].iloc[0]), 2)
                               if len(post) else None,
            "threshold_last": round(float(post["gate1_threshold_causal"].iloc[-1]), 2)
                              if len(post) else None,
            "threshold_drift_note": "the causal threshold moves as observations accumulate. Its "
                                    "range is reported because a rule whose level drifts is a "
                                    "different rule from a fixed one.",
        },
        "gate_1_v0_style_for_contrast": {
            "in_sample_threshold": round(thr_insample, 2),
            "n_pass": int(s["gate1_level_v0_style_insample"].sum()),
            "note": "v0's non-causal threshold, recomputed on THIS population. Reported so the "
                    "causal fix can be told apart from the population fix.",
        },
        "gate_2": {
            "n_pass": int(s["gate2_is_max"].sum()),
            "n_pass_trivial_singleton": int(s["gate2_trivial_singleton"].sum()),
            "n_pass_contested": int((s["gate2_is_max"] & ~s["gate2_trivial_singleton"]).sum()),
        },
        "concurrency": {
            "distribution": live_hist,
            "median": float(np.median(n_live)),
            "share_alone": round(float((n_live == 1).mean()), 4),
            "share_two_or_more": round(float((n_live >= 2).mean()), 4),
            "v0_share_alone_for_reference": 0.7948,
        },
        "policies": {
            "A_n": int(s["policy_a"].sum()),
            "B_n": int(s["policy_b"].sum()),
            "B_share_of_A": round(float(s["policy_b"].mean()), 4),
            "B_n_warmup": int((s["policy_b"] & s["gate1_warmup"]).sum()),
            "B_n_post_warmup": int((s["policy_b"] & ~s["gate1_warmup"]).sum()),
            "B_v0_style_n": int(s["policy_b_v0_style"].sum()),
        },
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
