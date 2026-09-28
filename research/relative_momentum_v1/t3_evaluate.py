"""
v1-T3: the policy table, on the corrected population with the causal gate 1.

Same shape as v0: A, B1, B2, B, B-contested. Two things are added because v1 needs them:

  - gate1_warmup share per policy, and a POST-WARMUP row for every policy that gate 1 touches.
    250 of 903 candidates (27.7%) sit in gate 1's warmup and pass it by default. The brief said
    to revisit if warmup covered a meaningful share -- it does, so the post-warmup rows are the
    honest read and are labelled as such rather than blended in.
  - the next-tick fill slippage, which is a real unmodelled cost in the gate's own mechanics:
    the gap gate tests price[i] and fills price[i+1].

Cost is Phase 11's stack in both units (D19). The gate has no native fill or cost model --
verified in v0-T3: pnl is a pure price ratio and config/strategy.json has no fee block.

D5: long-only throughout.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/t3_evaluate.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import common as C  # noqa: E402

IN = f"{C.ART}/t2_gated.parquet"
OUT_JSON = f"{C.ART}/t3_evaluate.json"
OUT_PARQUET = f"{C.ART}/t3_evaluated.parquet"

QS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def block(d: pd.DataFrame, label: str, cost_bp: float, note: str = "") -> dict:
    if len(d) == 0:
        return {"policy": label, "n_trades": 0, "note": note}
    g = d["gross_pnl_pct"].to_numpy(dtype=float) * 100.0
    net_flat = g - cost_bp
    net_ps = d["net_bp_per_share"].to_numpy(dtype=float)
    return {
        "policy": label, "n_trades": int(len(d)),
        "share_gate1_warmup": round(float(d["gate1_warmup"].mean()), 4),
        "gross_bp": {f"p{int(q * 100)}": round(float(np.quantile(g, q)), 1) for q in QS},
        "gross_bp_median": round(float(np.median(g)), 1),
        "gross_bp_mean": round(float(g.mean()), 1),
        "net_bp_median_flat": round(float(np.median(net_flat)), 1),
        "net_bp_median_per_share": round(float(np.nanmedian(net_ps)), 1),
        "win_rate_gross": round(float((g > 0).mean()), 4),
        "win_rate_net_flat": round(float((net_flat > 0).mean()), 4),
        "win_rate_net_per_share": round(float(np.nanmean(net_ps > 0)), 4),
        "hold_sec_median": round(float(d["natural_hold_sec"].median()), 1),
        "queued_share": round(float((d["entry_kind"] == "queued").mean()), 4),
        "note": note,
    }


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["evaluation"]["cost"]["round_trip_bp"]
    cost_cents = cfg["evaluation"]["cost"]["round_trip_cents"]

    d = pd.read_parquet(C.REPO / IN)
    ent = d["entry_price"].to_numpy(dtype=float)
    d["cost_cents_bp"] = np.where(ent > 0, (cost_cents / 100.0) / ent * 1e4, np.nan)
    d["net_bp_per_share"] = d["gross_pnl_pct"].to_numpy(dtype=float) * 100.0 - d["cost_cents_bp"]
    # the gate's own fill convention, as a cost: trigger price -> next-tick fill
    d["fill_slippage_bp"] = np.where(
        d["trigger_price_observed"] > 0,
        (d["entry_price"] / d["trigger_price_observed"] - 1.0) * 1e4, np.nan)
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    post = d[~d["gate1_warmup"]]
    rows = [
        block(d, "A · every gap-gated first-window signal", cost_bp, "the baseline"),
        block(post, "A · post-warmup only", cost_bp,
              "same rule; the subset where gate 1 was actually active, for like-for-like"),
        block(d[d["gate1_level"]], "B1 · causal gate 1 only", cost_bp,
              "includes warmup passes, which are free passes"),
        block(post[post["gate1_level"]], "B1 · causal gate 1 only, POST-WARMUP",
              cost_bp, "the honest read of the level gate"),
        block(d[d["gate1_level_v0_style_insample"]],
              "B1-v0 · v0's in-sample gate 1, recomputed here", cost_bp,
              "so the causal fix can be told apart from the population fix"),
        block(d[d["gate2_is_max"]], "B2 · gate 2 only (cross-section)", cost_bp,
              "808 of 855 passes are uncontested"),
        block(d[d["policy_b"]], "B · both gates", cost_bp, "includes warmup"),
        block(post[post["policy_b"]], "B · both gates, POST-WARMUP", cost_bp,
              "the honest read of Policy B"),
        block(d[d["policy_b"] & ~d["gate2_trivial_singleton"]],
              "B-contested · both gates, contested moments only", cost_bp,
              "the only trades where the cross-sectional gate decided anything"),
    ]

    summary = {
        "task": "v1-T3 policy evaluation on the corrected population with causal gate 1",
        "config_hash": C.cfg_hash(),
        "population": {
            "n": int(len(d)),
            "gap_gate": "ON, reconstructed tick-exactly; threshold on move_at vs tick-derived "
                        "prior close",
            "move_at_entry_median": round(float(d["move_at_entry"].median()), 4),
            "date_range": [d["date"].min(), d["date"].max()],
            "hold_sec_median": round(float(d["natural_hold_sec"].median()), 1),
        },
        "gate1_warmup": {
            "n": int(d["gate1_warmup"].sum()),
            "share": round(float(d["gate1_warmup"].mean()), 4),
            "verdict": "MEANINGFUL -- the brief said revisit if warmup covers a meaningful share "
                       "of the sample. At 27.7% it does, so every gate-1 policy is reported both "
                       "with and without it and the post-warmup row is the one to read.",
        },
        "cost": {
            "flat_bp": cost_bp, "per_share_cents": cost_cents,
            "per_share_in_bp_quantiles": {
                f"p{int(q * 100)}": round(float(np.nanquantile(d["cost_cents_bp"], q)), 1)
                for q in (.05, .25, .5, .75, .95)},
            "source": cfg["evaluation"]["cost"]["source"],
            "native_model": "none -- verified in v0-T3",
        },
        "fill_slippage_bp": {
            "definition": "(next-tick fill / trigger price - 1), in bp. The gap gate tests "
                          "price[i] and fills price[i+1]; this is what that convention costs, "
                          "and it is ON TOP OF the spread cost above, not included in it.",
            "quantiles": {f"p{int(q * 100)}": round(float(np.nanquantile(
                d["fill_slippage_bp"], q)), 1) for q in (.05, .25, .5, .75, .95)},
            "mean": round(float(np.nanmean(d["fill_slippage_bp"])), 1),
            "share_negative": round(float(np.nanmean(d["fill_slippage_bp"] < 0)), 4),
        },
        "policy_table": rows,
        "d5": "long-only; no short or fade variant computed.",
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)

    print(json.dumps({k: v for k, v in summary.items() if k != "policy_table"},
                     indent=2, default=str))
    cols = ["policy", "n_trades", "share_gate1_warmup", "gross_bp_median", "gross_bp_mean",
            "net_bp_median_flat", "net_bp_median_per_share", "win_rate_gross",
            "win_rate_net_flat", "hold_sec_median"]
    print("\nPOLICY TABLE")
    print(pd.DataFrame(rows)[cols].to_string(index=False))
    print("\nGROSS DISTRIBUTION (bp)")
    print(pd.DataFrame([{"policy": r["policy"][:44], **r["gross_bp"]} for r in rows])
          .to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
