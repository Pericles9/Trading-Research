"""
Phase 13, T2: arm zero -- detection-price-decile partition, no fundamental data.

This runs before T3 and is not optional: it is the competing explanation for anything
T3 finds (cheap stocks file differently, dilute more, reverse-split more, and cost more
to trade, so a fundamental split can be a price split in different clothes).

Per Cooper's 2026-09-13 amendment: exploratory, no kill condition, no pass/fail
declaration anywhere in this script's output.

Usage: .venv/Scripts/python.exe research/phase_13/t2_arm_zero.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.phase_13 import common as C  # noqa: E402

HORIZONS = [5, 15, 30, 60]
OUT_PATH = f"{C.ART}/t2_arm_zero_summary.json"


def describe(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.median()), "p75": float(s.quantile(0.75)), "p90": float(s.quantile(0.90)),
        "mean": float(s.mean()),
    }


def main():
    p0 = pd.read_parquet(f"{C.ART}/p0_outcome.parquet")
    ctx = pd.read_parquet("results/fundamentals_f1/artifacts/t6_context.parquet",
                           columns=["event_id", "detection_price_decile"])
    df = p0.merge(ctx, on="event_id", how="left")

    by_decile = {}
    for h in HORIZONS:
        rows = []
        for decile, g in df.groupby("detection_price_decile", dropna=True):
            rows.append({
                "decile": int(decile),
                "mfe_cost_mult": describe(g[f"mfe_cost_mult_{h}"]),
                "mae_cost_mult": describe(g[f"mae_cost_mult_{h}"]),
            })
        by_decile[str(h)] = sorted(rows, key=lambda r: r["decile"])

    n_missing_decile = df["detection_price_decile"].isna().sum()
    summary = {
        "n_total": len(df),
        "n_missing_decile": int(n_missing_decile),
        "by_horizon_by_decile": by_decile,
        "note": "Exploratory, no kill condition, no pass/fail declaration -- per Cooper's 2026-09-13 "
                "amendment. Distributions only; Cooper reads them, this script does not interpret them.",
        "config_hash": C.cfg_hash(),
    }
    C.write_json(OUT_PATH, summary)
    print(json.dumps({"n_total": len(df), "n_missing_decile": int(n_missing_decile)}, indent=2))
    for h in HORIZONS:
        print(f"\n--- horizon {h}min: median mfe_cost_mult by decile ---")
        for row in by_decile[str(h)]:
            m = row["mfe_cost_mult"]
            print(f"  decile {row['decile']}: n={m.get('n', 0)}, median={m.get('median', float('nan')):.3f}")


if __name__ == "__main__":
    main()
