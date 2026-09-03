#!/usr/bin/env python
"""
Phase 10e T4b — the horizon gradient. Free, and it decides whether Arm 2 is worth a pass.

THE ARGUMENT IT TESTS, AND THE ARGUMENT IT MAY REFUTE. Arm 1's finest horizon is 1 minute
while the strategy class operates in seconds, so the minute-scale gate tested a different
regime — that much is a real specification defect. But whether the *other* regime is more or
less favourable is a derivable question rather than an assertion:

    round-trip cost is FIXED at 70.98 bp and does not scale with the horizon;
    typical price movement scales roughly as sqrt(H).

so the cost drag relative to the 30-minute named cell is sqrt(30/H):

    H = 30 min  ->  1.0x        H = 60 s  ->  5.5x
    H =  5 min  ->  2.4x        H = 30 s  ->  7.7x
                                H = 10 s  -> 13.4x

A 10-second hold faces roughly THIRTEEN TIMES the cost drag of the 30-minute hold that just
failed. If that is right, the minute-scale null was GENEROUS to the second-scale case rather
than irrelevant to it.

THE TEST. Arm 1 already ran horizons of 1, 5, 15, 30 and 60 minutes. The gradient inside
that existing grid answers it directly, with no new computation and no data pass:

    p_clear RISING as the horizon shortens  -> the second-scale case is live
    p_clear FALLING as the horizon shortens -> the extrapolation runs against Arm 2

Held fixed: latency, detection segment, denominator, barrier pair. Only the horizon moves.
The gap to break-even is reported alongside, because p_breakeven does not depend on H — so
the gap moves exactly as p_clear does, and it is the quantity that matters.

Usage: .venv/Scripts/python.exe research/phase_10e/t4b_horizon_gradient.py
"""
from __future__ import annotations

import json
import os

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = os.path.join(REPO, "config", "phase_10e.json")
A = os.path.join(REPO, "results/phase_10e/artifacts")
OUT = "results/phase_10e/artifacts/t4b_horizon_gradient.json"
KTAG = {1.5: "k15", 2: "k2", 3: "k3"}


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    nc = cfg["named_cell"]
    L, seg = nc["latency_minutes"], nc["det_segment"]
    hors = cfg["arm1"]["horizons_minutes"]
    ks, ms = cfg["barrier_grid"]["profit_k"], cfg["barrier_grid"]["stop_m"]
    rt = cfg["cost"]["round_trip_bp"] / 10000.0

    c = duckdb.connect(); c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"create view t2 as select * from read_parquet('{os.path.join(A,'t2_excursion.parquet')}')")

    rows = []
    for k in ks:
        for mm in ms:
            tp, ts = f"tp_{KTAG[k]}", f"ts_m{mm}"
            sel = ", ".join(
                f"""sum(case when {tp} is not null and {tp} <= fill_minute + {H}
                         and ({ts} is null or {ts} > fill_minute + {H} or {tp} <= {ts})
                    then 1 else 0 end)*1.0/count(*) as opt_{H},
                    sum(case when ({tp} is null or {tp} > fill_minute + {H})
                         and ({ts} is null or {ts} > fill_minute + {H})
                    then 1 else 0 end)*1.0/count(*) as exp_{H}""" for H in hors)
            d = c.execute(f"""select count(*) as n, {sel} from t2
                              where latency_minutes = {L} and det_segment = '{seg}'""").fetchdf()
            be = (mm + 1) / (k + mm)
            for H in hors:
                rows.append({"profit_k": k, "stop_m": mm, "horizon_minutes": H,
                             "p_clear_optimistic": float(d[f"opt_{H}"].iloc[0]),
                             "expiry_share": float(d[f"exp_{H}"].iloc[0]),
                             "p_breakeven": be,
                             "gap_to_breakeven": float(d[f"opt_{H}"].iloc[0]) - be,
                             "n": int(d["n"].iloc[0])})
    g = pd.DataFrame(rows)

    # per barrier pair: does the gap improve or worsen as the horizon shortens?
    verdicts = []
    for (k, mm), s in g.groupby(["profit_k", "stop_m"]):
        s = s.sort_values("horizon_minutes")
        slope = np.polyfit(np.log(s.horizon_minutes), s.gap_to_breakeven, 1)[0]
        verdicts.append({
            "profit_k": k, "stop_m": mm,
            "gap_at_H1": float(s[s.horizon_minutes == 1].gap_to_breakeven.iloc[0]),
            "gap_at_H60": float(s[s.horizon_minutes == 60].gap_to_breakeven.iloc[0]),
            "gap_slope_per_log_horizon": float(slope),
            "improves_as_horizon_shortens": bool(slope < 0)})
    v = pd.DataFrame(verdicts)
    n_improve = int(v.improves_as_horizon_shortens.sum())

    cost_scale = {H: float(np.sqrt(30.0 / H)) for H in [30, 5, 1]}
    cost_scale.update({"60s": float(np.sqrt(30.0 / 1.0)), "30s": float(np.sqrt(30.0 / 0.5)),
                       "10s": float(np.sqrt(30.0 / (1.0 / 6.0)))})

    out = {
        "task": "Phase 10e T4b -- the horizon gradient, free, decides whether Arm 2 is worth a pass",
        "held_fixed": {"latency_minutes": L, "det_segment": seg,
                       "denominator": "print_weighted", "note": "only the horizon moves"},
        "derived_cost_scaling": {
            "premise": ("round-trip cost is FIXED at 70.98 bp; typical move scales as sqrt(H); "
                        "so relative cost drag = sqrt(30/H) against the 30-minute named cell"),
            "relative_drag_vs_30min": cost_scale,
            "reading": ("a 10-second hold faces ~13x the cost drag of the 30-minute hold that "
                        "failed -- shorter horizons are structurally HARDER against a fixed "
                        "cost, so the minute-scale null may be GENEROUS to the second-scale "
                        "case rather than irrelevant to it")},
        "gradient": g.to_dict("records"),
        "per_barrier_pair": verdicts,
        "n_pairs_improving_as_horizon_shortens": n_improve,
        "n_pairs": int(len(v)),
        "VERDICT": ("the gradient runs AGAINST short horizons in "
                    f"{len(v) - n_improve} of {len(v)} barrier pairs"
                    if n_improve < len(v) else
                    "the gradient FAVOURS short horizons in every barrier pair"),
        "source": "research/phase_10e/t4b_horizon_gradient.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t4b_horizon_gradient.py",
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"held fixed: latency {L}m, segment {seg}, print-weighted. Only H moves.\n")
    print("derived cost drag vs the 30-min named cell, from sqrt(30/H):")
    for kk, vv in cost_scale.items():
        print(f"   H={kk:>4}  {vv:5.1f}x")
    print()
    for (k, mm), s in g.groupby(["profit_k", "stop_m"]):
        s = s.sort_values("horizon_minutes")
        print(f"k={k} m={mm}  p_breakeven {s.p_breakeven.iloc[0]:.4f}")
        for r in s.itertuples(index=False):
            print(f"   H {r.horizon_minutes:>3}m   p_clear {r.p_clear_optimistic:.4f}   "
                  f"gap {r.gap_to_breakeven:+.4f}   expiry {r.expiry_share:.4f}")
    print(f"\nVERDICT: {out['VERDICT']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
