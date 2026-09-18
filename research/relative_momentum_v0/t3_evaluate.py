"""
v0-T3: Policy A (EPG-only) against Policy B (EPG+Qual), same table, same trade.

The trade is the gate's own: rising-edge entry, window-close exit, the realized hold that
gives. Primary exit is natural_exit_* (the window-close exit); the exit actually realized in
the Phase F run is reported alongside, never instead of it.

pnl_pct as recorded is GROSS -- it equals (exit_price / entry_price - 1) * 100 to 2.8e-14 and
config/strategy.json carries no fee block. Cost is therefore applied here, from Phase 11:
70.98 bp and 2.512 cents, both units (D19). The cents leg matters because these are low-priced
names and a fixed per-share cost is not the same bar as a fixed bp cost.

Policy A is reported on two bases: all first-window signals, and the scorable subset, which is
the like-for-like base against Policy B. Both are shown so the comparison is not quietly made
against a different denominator.

D5: long-only throughout. No short or fade variant is computed.

Usage: .venv/Scripts/python.exe research/relative_momentum_v0/t3_evaluate.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v0 import common as C  # noqa: E402

IN = f"{C.ART}/t2_gated.parquet"
OUT_JSON = f"{C.ART}/t3_evaluate.json"
OUT_PARQUET = f"{C.ART}/t3_evaluated.parquet"

QS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def block(d: pd.DataFrame, label: str, col: str, cost_bp: float, note: str = "") -> dict:
    """Full distribution first; the median is one row of it, never the only row."""
    if len(d) == 0:
        return {"policy": label, "n_trades": 0, "note": note}
    g = d[col].to_numpy(dtype=float) * 100.0            # pnl_pct -> bp
    net_bp = g - cost_bp
    net_cents = d[f"{col}_net_cents_bp"].to_numpy(dtype=float)
    return {
        "policy": label, "n_trades": int(len(d)),
        "gross_bp": {f"p{int(q * 100)}": round(float(np.quantile(g, q)), 1) for q in QS},
        "gross_bp_mean": round(float(g.mean()), 1),
        "gross_bp_median": round(float(np.median(g)), 1),
        "net_bp_median_flat_cost": round(float(np.median(net_bp)), 1),
        "net_bp_median_per_share_cost": round(float(np.median(net_cents)), 1),
        "win_rate_gross": round(float((g > 0).mean()), 4),
        "win_rate_net_flat_cost": round(float((net_bp > 0).mean()), 4),
        "win_rate_net_per_share_cost": round(float((net_cents > 0).mean()), 4),
        "share_exactly_zero_gross": round(float((g == 0).mean()), 4),
        "hold_sec_median": round(float(d["natural_hold_sec"].median()), 1),
        "note": note,
    }


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["evaluation"]["cost"]["round_trip_bp"]
    cost_cents = cfg["evaluation"]["cost"]["round_trip_cents"]

    d = pd.read_parquet(C.REPO / IN)
    # Per-share cost expressed in bp of that trade's own entry price, so the cents leg is
    # comparable on the same axis. Low-priced names pay far more in bp terms.
    ent = d["entry_price"].to_numpy(dtype=float)
    cost_cents_bp = np.where(ent > 0, (cost_cents / 100.0) / ent * 1e4, np.nan)
    d["cost_cents_bp"] = cost_cents_bp
    for col in ("natural_exit_pnl_pct", "pnl_pct"):
        d[f"{col}_net_cents_bp"] = d[col].to_numpy(dtype=float) * 100.0 - cost_cents_bp
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    sc = d[d["score_available"]]
    rows_natural = [
        block(d, "A · EPG-only, all first-window signals", "natural_exit_pnl_pct", cost_bp,
              "includes the 28 candidates with no score; not the like-for-like base"),
        block(sc, "A · EPG-only, scorable subset (like-for-like base)",
              "natural_exit_pnl_pct", cost_bp, "the base Policy B is drawn from"),
        block(d[d["gate1_level"]], "B1 · gate 1 only (level)", "natural_exit_pnl_pct", cost_bp,
              "reported so the two gates can be told apart"),
        block(sc[sc["gate2_is_max"]], "B2 · gate 2 only (cross-section)",
              "natural_exit_pnl_pct", cost_bp,
              "794 of its 892 passes are trivial singletons"),
        block(d[d["policy_b"]], "B · EPG+Qual, both gates", "natural_exit_pnl_pct", cost_bp,
              "the brief's Policy B"),
        block(d[d["policy_b"] & ~d["gate2_trivial_singleton"]],
              "B-contested · both gates, contested moments only",
              "natural_exit_pnl_pct", cost_bp,
              "the only trades where the cross-sectional gate actually decided something"),
    ]
    rows_realized = [
        block(d, "A · EPG-only, all first-window signals", "pnl_pct", cost_bp,
              "realized exit as run in Phase F (EXIT_D / LULD / window close)"),
        block(sc, "A · EPG-only, scorable subset", "pnl_pct", cost_bp, ""),
        block(d[d["policy_b"]], "B · EPG+Qual, both gates", "pnl_pct", cost_bp, ""),
    ]

    summary = {
        "task": "v0-T3 policy evaluation",
        "config_hash": C.cfg_hash(),
        "trade_definition": {
            "entry": "gate first rising edge (entry_ts, entry_price)",
            "exit_primary": "window close (natural_exit_ts, natural_exit_price)",
            "exit_secondary": "realized exit as run in Phase F (exit_ts, exit_price)",
            "hold_median_sec": round(float(d["natural_hold_sec"].median()), 1),
        },
        "cost": {
            "flat_bp": cost_bp, "per_share_cents": cost_cents,
            "per_share_in_bp_quantiles": {
                f"p{int(q * 100)}": round(float(np.nanquantile(cost_cents_bp, q)), 1)
                for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
            "source": cfg["evaluation"]["cost"]["source"],
            "caveat": cfg["evaluation"]["cost"]["caveat"],
            "why_two_units": "D19. The per-share leg is the harsher bar on low-priced names, "
                             "and this population is full of them.",
        },
        "primary_window_close_exit": rows_natural,
        "secondary_realized_exit": rows_realized,
        "d5": "long-only; no short or fade variant computed.",
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("primary_window_close_exit", "secondary_realized_exit")},
                     indent=2, default=str))
    cols = ["policy", "n_trades", "gross_bp_median", "net_bp_median_flat_cost",
            "net_bp_median_per_share_cost", "win_rate_gross", "win_rate_net_flat_cost",
            "win_rate_net_per_share_cost", "hold_sec_median"]
    print("\nPRIMARY — window-close exit")
    print(pd.DataFrame(rows_natural)[cols].to_string(index=False))
    print("\nSECONDARY — realized exit")
    print(pd.DataFrame(rows_realized)[cols].to_string(index=False))
    print("\nGROSS DISTRIBUTION (bp), window-close exit")
    print(pd.DataFrame([{"policy": r["policy"], **r["gross_bp"]} for r in rows_natural])
          .to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
