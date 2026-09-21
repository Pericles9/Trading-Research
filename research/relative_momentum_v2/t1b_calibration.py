"""
v2-T1b: the calibration gate. A STOP POINT, not a formality (Correction 1 sections 5 and 6).

Three gates, each able to stop v2 on its own:

  5b  Every reference rung's actual percentile position on the full 903. A floor rung above p10 is
      still a selection gate, which is the mechanism that damaged v0 and v1. Report and STOP.

  5c  Are the pathological cases in the sample at all? The floor exists to catch the dead-tape
      winner: a name with no ABSOLUTE attention that holds all the RELATIVE attention because
      nothing else is trading. Two parts:
        (i)  do candidates with degenerate absolute activity exist, and in which session segment
        (ii) THE JOINT TEST -- do those candidates score HIGH on the ratio, and do they win
             rank contests when no floor is applied? If low-activity candidates never win under
             rank-only, the floor has nothing to catch and v2's architecture is answering a
             question this population does not pose.
      If the cases are absent, the floor cannot be calibrated against its own purpose and v2 STOPS.

  6   Power. Project survivor, NO_TRADE and F+R-contested counts at all 13 configurations BEFORE
      T2 runs. STOP if the contested cell is too small to read. v0's was 42 of 244; scaled down
      this could reach single digits and distinguish nothing. Finding that out after the run is a
      wasted pass.

Liveness note: natural_exit_ts is also float64 in v1's artifact, so it carries the same ~128 ns
rounding. Liveness comparisons are at second scale, so a 128 ns error cannot change a live/not-live
determination except on a measure-zero coincidence. Not snapped; recorded.

Usage: .venv/Scripts/python.exe research/relative_momentum_v2/t1b_calibration.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v2 import common as C  # noqa: E402

IN = f"{C.ART}/t1_measured.parquet"
V1_SCORED = "results/relative_momentum/v1/artifacts/t1_scored.parquet"
OUT_JSON = f"{C.ART}/t1b_calibration.json"
OUT_PARQUET = f"{C.ART}/t1b_projection.parquet"

P10 = 0.10


def pct_position(series: pd.Series, value: float) -> float:
    v = series.to_numpy(dtype=float)
    v = v[np.isfinite(v)]
    return float((v < value).mean())


def live_sets(tau: np.ndarray, end: np.ndarray, eligible: np.ndarray, score: np.ndarray):
    """For each eligible candidate, how many eligible candidates are live at its tau, and whether
    it holds the top score among them. Liveness = [tau_j, exit_j] contains tau_i."""
    n_live = np.zeros(tau.size, dtype=int)
    is_max = np.zeros(tau.size, dtype=bool)
    idx = np.flatnonzero(eligible)
    for i in idx:
        live = eligible & (tau <= tau[i]) & (end >= tau[i])
        n_live[i] = int(live.sum())
        v = score[live]
        v = v[np.isfinite(v)]
        is_max[i] = (not v.size) or bool(score[i] >= v.max())
    return n_live, is_max


def main() -> int:
    cfg = C.load_cfg()
    d = pd.read_parquet(C.REPO / IN)
    d = d[d["measured"]].reset_index(drop=True)

    sc = pd.read_parquet(C.REPO / V1_SCORED)[["key", "score", "B_e", "n_baseline_sessions"]]
    d = d.merge(sc, on="key", how="left")
    d["score_available"] = d["score"].notna()

    # ---------------------------------------------------------------- 5b
    ref = C.derive_thresholds(cfg)
    rung_rows = []
    checks = [
        ("MIN_PRINTS", "print_count", ref["MIN_PRINTS"], "floor", "below"),
        ("MIN_NOTIONAL_USD", "notional_usd", ref["MIN_NOTIONAL_USD"], "floor", "below"),
        ("MIN_VENUES", "venue_count", ref["MIN_VENUES"], "floor", "below"),
        ("MIN_QUOTES", "quote_count", ref["MIN_QUOTES"], "floor", "below"),
        ("MAX_SPREAD_BP", "spread_bp", ref["MAX_SPREAD_BP"], "floor", "above"),
        ("MIN_DEPTH_USD", "depth_usd", ref["MIN_DEPTH_USD"], "floor", "below"),
        ("MIN_PRICE_USD", "last_price", ref["MIN_PRICE_USD"], "separate_filter", "below"),
    ]
    for name, col, thr, cls, direction in checks:
        s = d[col]
        if direction == "below":
            rej = float((s.to_numpy(dtype=float) < thr).mean())
        else:
            rej = float((s.to_numpy(dtype=float) > thr).mean())
        rung_rows.append({
            "constant": name, "quantity": col, "reference_threshold": round(float(thr), 4),
            "class": cls, "direction": f"reject if {direction}",
            "percentile_position": round(pct_position(s, thr), 4),
            "rejection_share": round(rej, 4),
            "gate_5b_pass": bool(cls != "floor" or rej <= P10),
        })
    floor_rows = [r for r in rung_rows if r["class"] == "floor"]
    gate_5b = all(r["gate_5b_pass"] for r in floor_rows)

    # ---------------------------------------------------------------- 5c
    seg = "session_bucket"
    below_ref = {}
    for name, col, thr, cls, direction in checks:
        if cls != "floor":
            continue
        hit = (d[col].to_numpy(dtype=float) < thr) if direction == "below" \
            else (d[col].to_numpy(dtype=float) > thr)
        below_ref[name] = {"n": int(hit.sum()),
                           "by_segment": d.loc[hit, seg].value_counts().to_dict()}

    # (i) degenerate absolute activity exists?
    q10_prints = float(d["print_count"].quantile(0.10))
    d["low_activity"] = d["print_count"] <= q10_prints

    # (ii) THE JOINT TEST -- rank-only (no floor) winners, and where they sit on absolute activity
    tau = d["tau_ns"].to_numpy(dtype=np.int64)
    end = d["natural_exit_ts"].to_numpy(dtype=np.float64).astype(np.int64)
    score = d["score"].to_numpy(dtype=float)
    eligible_all = d["score_available"].to_numpy()
    n_live_R, is_max_R = live_sets(tau, end, eligible_all, score)
    d["n_live_no_floor"] = n_live_R
    d["rank_winner_no_floor"] = is_max_R & eligible_all
    d["contested_no_floor"] = d["rank_winner_no_floor"] & (d["n_live_no_floor"] >= 2)

    d["score_decile"] = pd.qcut(d["score"], 10, labels=False, duplicates="drop")
    joint = {
        "print_count_p10": round(q10_prints, 2),
        "n_low_activity": int(d["low_activity"].sum()),
        "low_activity_by_segment": d.loc[d["low_activity"], seg].value_counts().to_dict(),
        "score_decile_of_low_activity": {
            str(int(k)): int(v) for k, v in
            d.loc[d["low_activity"], "score_decile"].value_counts().sort_index().items()},
        "n_rank_winners_no_floor": int(d["rank_winner_no_floor"].sum()),
        "n_contested_winners_no_floor": int(d["contested_no_floor"].sum()),
        "n_low_activity_rank_winners": int((d["low_activity"] & d["rank_winner_no_floor"]).sum()),
        "n_low_activity_contested_winners": int(
            (d["low_activity"] & d["contested_no_floor"]).sum()),
        "share_of_contested_winners_that_are_low_activity": (
            round(float((d["low_activity"] & d["contested_no_floor"]).sum()
                        / max(int(d["contested_no_floor"].sum()), 1)), 4)),
        "median_score_low_activity": (round(float(d.loc[d["low_activity"], "score"].median()), 3)
                                      if d["low_activity"].any() else None),
        "median_score_rest": round(float(d.loc[~d["low_activity"], "score"].median()), 3),
        "reading": "the pathology is a candidate with low ABSOLUTE activity holding a HIGH ratio. "
                   "If low-activity candidates sit in the upper score deciles and win contests "
                   "under rank-only, the floor has a target. If they never win, v2's architecture "
                   "is answering a question this population does not pose.",
    }
    gate_5c = bool(d["low_activity"].any() and int(d["rank_winner_no_floor"].sum()) > 0)

    # ---------------------------------------------------------------- 6
    contested_floor_n = cfg["calibration_gate_t1b"]["contested_floor_n"]
    proj_rows = []
    for conf in C.ladder_configurations(cfg):
        thr = C.derive_thresholds(cfg, conf["overrides"])
        passes = np.zeros(len(d), dtype=bool)
        fail_counter: dict[str, int] = {}
        for i, row in enumerate(d.itertuples(index=False)):
            m = {k: getattr(row, k) for k in C.FLOOR_INPUTS}
            ok, fails = C.absolute_floor(m, thr)
            passes[i] = ok
            for f in fails:
                fail_counter[f] = fail_counter.get(f, 0) + 1
        price_ok = np.array([C.price_filter(v, thr) for v in d["last_price"].to_numpy(float)])

        for price_on in (False, True):
            elig = passes & eligible_all & (price_ok if price_on else True)
            nl, mx = live_sets(tau, end, elig, score)
            winners = elig & mx
            contested = winners & (nl >= 2)
            proj_rows.append({
                "config": conf["label"], "swept": conf["swept"], "price_filter_on": price_on,
                "n_floor_survivors": int((passes & (price_ok if price_on else True)).sum()),
                "survivor_share": round(float((passes & (price_ok if price_on else True)).mean()), 4),
                "n_FR": int(winners.sum()),
                "n_FR_contested": int(contested.sum()),
                "n_NO_TRADE_moments": int((eligible_all & ~elig).sum()),
                "contested_readable": bool(int(contested.sum()) >= contested_floor_n),
                **{f"fail_{k}": v for k, v in fail_counter.items()},
            })
    proj = pd.DataFrame(proj_rows)
    # only the fail_* counters are sparse across configs; leave 'swept' as the string/None it is
    fail_cols = [c for c in proj.columns if c.startswith("fail_")]
    proj[fail_cols] = proj[fail_cols].fillna(0).astype(int)
    proj["swept"] = proj["swept"].astype("string")
    proj.to_parquet(C.REPO / OUT_PARQUET, index=False)
    d.to_parquet(C.REPO / f"{C.ART}/t1b_enriched.parquet", index=False)

    ref_rows = proj[proj["config"] == "reference"]
    gate_6 = bool(ref_rows["contested_readable"].all())

    verdict = {
        "gate_5b_rungs_in_left_tail": gate_5b,
        "gate_5c_pathology_present": gate_5c,
        "gate_6_contested_cell_readable": gate_6,
        "all_pass": bool(gate_5b and gate_5c and gate_6),
        "contested_floor_n": contested_floor_n,
    }

    summary = {
        "task": "v2-T1b calibration gate (HARD STOP)",
        "config_hash": C.cfg_hash(),
        "n": int(len(d)),
        "gate_5b_rung_positions": rung_rows,
        "gate_5b_note": "a floor rung rejecting more than p10 of an already-activity-filtered "
                        "population is a second selection gate, not a floor.",
        "candidates_below_each_reference_rung": below_ref,
        "gate_5c_joint_test": joint,
        "distributions_by_segment": {
            str(s_): {"n": int(len(g)), **{q: {f"p{int(p*100)}": round(float(g[q].quantile(p)), 4)
                                              for p in (.01, .05, .25, .5, .95)}
                                          for q in ["print_count", "notional_usd", "venue_count",
                                                    "quote_count", "spread_bp", "spread_cents",
                                                    "depth_usd", "last_price"]}}
            for s_, g in d.groupby(seg)},
        "gate_6_projection_reference": ref_rows.to_dict("records"),
        "verdict": verdict,
        "outputs": [OUT_PARQUET, f"{C.ART}/t1b_enriched.parquet"],
    }
    C.write_json(OUT_JSON, summary)

    print("=== GATE 5b — reference rung positions on the full 903 ===")
    print(pd.DataFrame(rung_rows).to_string(index=False))
    print("\n=== GATE 5c — is the pathology in the sample? ===")
    print(json.dumps(joint, indent=2, default=str))
    print("\n=== GATE 6 — power projection, all 13 configurations ===")
    cols = ["config", "price_filter_on", "n_floor_survivors", "survivor_share", "n_FR",
            "n_FR_contested", "n_NO_TRADE_moments", "contested_readable"]
    print(proj[cols].to_string(index=False))
    print("\n=== VERDICT ===")
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
