"""
v2-T3: settle v0's gate-1 mechanism. One query, no new data pass.

Two competing explanations for why v0's percentile gate degraded the median trade are on the
record, and they imply opposite things about what to build next:

  (a) it selected DEEP INTO THE MOVE -- Spearman(score, move_at) was 0.69 in v0, so the gate was
      largely a proxy for "already moved a lot", and buying late is what hurt.
  (b) it selected THIN TAPE -- relative volume is notional divided by a baseline, so a name whose
      baseline is tiny scores high on very little absolute activity. If v0's passes are
      systematically thinner and cheaper than its fails, the gate was never an attention gate; it
      was an illiquidity filter pointed the wrong way.

These are separable on data already computed. v0's own artifact carries gate1_level together with
the absolute quantities measured at v0's tau.

Run independently of v2's T1b calibration stop: this task touches neither the floor nor the policy
table, and the question is a standing one.

Usage: .venv/Scripts/python.exe research/relative_momentum_v2/t3_v0_mechanism.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v2 import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t3_v0_mechanism.json"
OUT_PARQUET = f"{C.ART}/t3_v0_mechanism.parquet"

QUANTITIES = [
    ("dollar_volume", "notional in the 10-min window, USD"),
    ("n_prints", "print count in the 10-min window"),
    ("entry_price", "entry price, USD"),
    ("move_at", "move already achieved at decision time"),
    ("score", "relative volume (the gate's own variable)"),
    ("B_e", "the baseline the score divides by, USD per 10-min RTH block"),
]


def block(g: pd.DataFrame, col: str) -> dict:
    v = g[col].to_numpy(dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size),
            **{f"p{int(p * 100)}": round(float(np.quantile(v, p)), 4)
               for p in (.05, .25, .5, .75, .95)},
            "mean": round(float(v.mean()), 4)}


def main() -> int:
    d = pd.read_parquet(C.REPO / C.V0_DIAGNOSTIC)
    d = d[d["score_available"]].copy()
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    p = d[d["gate1_level"]]
    f = d[~d["gate1_level"]]

    rows = []
    for col, desc in QUANTITIES:
        bp, bf = block(p, col), block(f, col)
        med_p, med_f = bp.get("p50"), bf.get("p50")
        ratio = (med_p / med_f) if (med_p is not None and med_f not in (None, 0)) else None
        u = stats.mannwhitneyu(p[col].dropna(), f[col].dropna(), alternative="two-sided")
        rows.append({
            "quantity": col, "description": desc,
            "pass_n": bp["n"], "fail_n": bf["n"],
            "pass_median": med_p, "fail_median": med_f,
            "pass_over_fail_median_ratio": round(ratio, 4) if ratio is not None else None,
            "pass_p25": bp.get("p25"), "fail_p25": bf.get("p25"),
            "mannwhitney_p": float(u.pvalue),
        })
    tbl = pd.DataFrame(rows)

    # Which explanation does the direction support?
    notional = tbl.loc[tbl["quantity"] == "dollar_volume"].iloc[0]
    prints = tbl.loc[tbl["quantity"] == "n_prints"].iloc[0]
    price = tbl.loc[tbl["quantity"] == "entry_price"].iloc[0]
    baseline = tbl.loc[tbl["quantity"] == "B_e"].iloc[0]
    move = tbl.loc[tbl["quantity"] == "move_at"].iloc[0]

    thinner = bool(notional["pass_over_fail_median_ratio"] < 1.0
                   and prints["pass_over_fail_median_ratio"] < 1.0)
    cheaper = bool(price["pass_over_fail_median_ratio"] < 1.0)
    deeper = bool(move["pass_over_fail_median_ratio"] > 1.0)
    smaller_baseline = bool(baseline["pass_over_fail_median_ratio"] < 1.0)

    verdict = {
        "passes_are_thinner_in_absolute_activity": thinner,
        "passes_are_cheaper": cheaper,
        "passes_are_deeper_into_the_move": deeper,
        "passes_have_a_smaller_baseline": smaller_baseline,
        "explanation_b_illiquidity_filter": thinner and cheaper,
        "explanation_a_deep_into_the_move": deeper,
        "note": "these are not exclusive -- both mechanisms can be present, and the baseline row is "
                "the one that separates them. relative volume = notional / B_e, so a pass can be "
                "bought either by a LARGE numerator (real attention) or a SMALL denominator (a thin "
                "baseline). If passes have a smaller B_e without more notional, the gate was "
                "selecting on the denominator.",
    }

    summary = {
        "task": "v2-T3 settle v0's gate-1 mechanism",
        "config_hash": C.cfg_hash(),
        "source": C.V0_DIAGNOSTIC,
        "new_data_pass": False,
        "population": {"n": int(len(d)), "gate1_pass": int(len(p)), "gate1_fail": int(len(f)),
                       "note": "v0's own candidates and its own in-sample 75th-percentile gate; "
                               "quantities measured at v0's tau (un-gap-gated first window)."},
        "comparison": rows,
        "verdict": verdict,
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)

    cols = ["quantity", "pass_n", "fail_n", "pass_median", "fail_median",
            "pass_over_fail_median_ratio", "mannwhitney_p"]
    print("=== v0 gate-1 PASS vs FAIL, on data already computed ===")
    print(tbl[cols].to_string(index=False))
    print("\n=== VERDICT ===")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
