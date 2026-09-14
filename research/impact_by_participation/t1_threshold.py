"""T1 -- derive the pre-registered threshold from D25's closest-cell gap.

Reads results/phase_10e/artifacts/t2_excursion.parquet (already materialized, no new tick
pass). Sweeps round_trip_bp downward from 70.98, holding profit_k=3, stop_m=2 fixed (the
closest-cell 3:2 barrier ratio, latency 1 min, horizon 60 min -- results/phase_10e/REPORT.md
section 5 / t4_gate.json's grid), and reports where p_clear would need to land to close the
gap to p_breakeven = 0.6000.

WHAT THIS IS AND IS NOT, stated before any number is computed. t2_excursion.parquet stores
first-touch TIMES only at the six barrier levels research/phase_10e/t3_shares.py's grid
already used (profit_k in {1.5, 2, 3}, stop_m in {1, 2}), all at the fixed rt_bp = 70.98 those
levels were computed against -- not a continuous price path, and not touch times at arbitrary
OTHER absolute-bp levels. So a swept round_trip_bp cannot be reclassified with T3's exact
optimistic/pessimistic ORDERING logic (t_profit vs t_stop) without a new pass over price bars
at each new barrier level. What CAN be computed from what's already on disk is an upper bound:
whether the shrunk profit barrier was reached AT ALL by horizon 60 (mfe_h60), independent of
whether the shrunk stop barrier was reached first. That bound is reported here, exactly as a
bound, alongside the corresponding "stop reached at all" share and the reached-neither
(true expiry) share -- and the exact reclassification is named as the follow-on task it is,
not silently approximated as the real thing.

Usage: .venv/Scripts/python.exe -m research.impact_by_participation.t1_threshold
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
T2 = REPO / "results" / "phase_10e" / "artifacts" / "t2_excursion.parquet"
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
CHARTS = REPO / "results" / "impact_by_participation" / "charts"

CELL = {"latency_minutes": 1, "horizon_minutes": 60, "profit_k": 3, "stop_m": 2}
P_BREAKEVEN = (CELL["stop_m"] + 1) / (CELL["profit_k"] + CELL["stop_m"])   # 0.6000, exactly
P_RANDOMWALK = CELL["stop_m"] / (CELL["profit_k"] + CELL["stop_m"])        # 0.4000, exactly
BASELINE_RT_BP = 70.98
# log-spaced sweep, 70.98 bp down to 5 bp -- per the prompt's stated sensible range
SWEEP_BP = np.exp(np.linspace(np.log(BASELINE_RT_BP), np.log(5.0), 40))


def main() -> int:
    d = pd.read_parquet(T2, columns=["ticker", "event_date_canonical", "momentum_pct",
                                      "latency_minutes", "fill_price", "mfe_h60", "mae_h60"])
    d = d[d.latency_minutes == CELL["latency_minutes"]].copy()
    d = d[(d.fill_price > 0) & d.mfe_h60.notna() & d.mae_h60.notna()]
    n = len(d)
    mfe_ratio = d.mfe_h60.to_numpy() / d.fill_price.to_numpy() - 1.0   # >= 0
    mae_ratio = d.mae_h60.to_numpy() / d.fill_price.to_numpy() - 1.0   # <= 0

    rows = []
    for rt_bp in SWEEP_BP:
        rt = rt_bp / 10000.0
        profit_level = CELL["profit_k"] * rt
        stop_level = CELL["stop_m"] * rt
        reached_profit = mfe_ratio >= profit_level
        reached_stop = mae_ratio <= -stop_level
        rows.append({
            "round_trip_bp": float(rt_bp),
            "profit_barrier_bp": float(profit_level * 10000),
            "stop_barrier_bp": float(stop_level * 10000),
            "p_clear_upper_bound": float(reached_profit.mean()),
            "p_stop_reached_share": float(reached_stop.mean()),
            "p_reached_neither_true_expiry": float((~reached_profit & ~reached_stop).mean()),
            "p_reached_both_order_unknown": float((reached_profit & reached_stop).mean()),
            "n": int(n),
        })
    sweep = pd.DataFrame(rows)

    crossing = sweep[sweep.p_clear_upper_bound >= P_BREAKEVEN]
    threshold_row = crossing.iloc[-1].to_dict() if len(crossing) else None
    # iloc[-1]: sweep is ordered baseline->cheapest, so the LAST row still >= breakeven is the
    # most expensive (largest rt_bp) point at which the bound has already crossed -- report
    # both directions so this is not silently the wrong endpoint.
    first_cross = crossing.iloc[0].to_dict() if len(crossing) else None

    out = {
        "task": "T1", "phase": "impact_by_participation",
        "cell": CELL, "p_breakeven": P_BREAKEVEN, "p_randomwalk": P_RANDOMWALK,
        "baseline_round_trip_bp": BASELINE_RT_BP,
        "baseline_gap": None,  # filled below from the sweep's own baseline row
        "what_this_bound_is": (
            "p_clear_upper_bound = P(MFE ratio over horizon 60 >= profit_k * round_trip_bp), "
            "i.e. whether the shrunk profit barrier was reached AT ALL by horizon, ignoring "
            "whether the stop barrier was reached first. This is an UPPER BOUND on the true "
            "p_clear_optimistic T3 would compute with exact touch-time ordering -- true "
            "p_clear_optimistic <= this bound at every round_trip_bp, because reaching the "
            "level is necessary but not sufficient (the stop may still have been touched "
            "first). It is NOT the closest-cell's exact quantity and is not reported as such."
        ),
        "what_it_is_not": (
            "Not T3's optimistic/pessimistic p_clear. t2_excursion.parquet has no touch TIME "
            "at arbitrary barrier levels (only at the six preset profit_k/stop_m combinations "
            "already in the grid, all at round_trip_bp=70.98) -- reconstructing exact ordering "
            "at a swept level needs a new pass over event_minute_bars_v2, generalizing "
            "research/phase_10e/t2_excursion.py's own touch-time logic to an arbitrary level. "
            "Named as the follow-on this task does NOT do, not silently approximated."
        ),
        "sweep_n": int(n),
        "sweep": sweep.to_dict("records"),
        "threshold_bound_crosses_breakeven_at": threshold_row,
        "threshold_bound_first_crosses_at": first_cross,
        "interpretation_left_to_cooper": (
            "If the bound does not cross 0.6000 at any round_trip_bp down to 5 bp, that is a "
            "strong negative signal without needing exact ordering (an upper bound failing to "
            "clear means the exact quantity, which is <= the bound, also fails to clear). If "
            "the bound DOES cross, that is necessary-but-not-sufficient and inconclusive on "
            "its own -- T4/T5's comparison should be read against this bound with that caveat "
            "stated, and an exact reclassification is a candidate follow-on before treating a "
            "crossing as evidence the gap actually closes."
        ),
        "source": "research/impact_by_participation/t1_threshold.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t1_threshold",
    }
    baseline_row = sweep.iloc[0]
    out["baseline_gap"] = float(baseline_row.p_clear_upper_bound - P_BREAKEVEN)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "t1_threshold.json").write_text(json.dumps(out, indent=2, default=str))
    sweep.to_parquet(ARTIFACTS / "t1_threshold_sweep.parquet", index=False)

    print(f"T1: n={n:,} events/entries at latency={CELL['latency_minutes']}")
    print(f"T1: baseline (rt_bp={BASELINE_RT_BP}) p_clear_upper_bound = "
          f"{baseline_row.p_clear_upper_bound:.4f} vs p_breakeven {P_BREAKEVEN:.4f} "
          f"(gap {out['baseline_gap']:+.4f})")
    print(f"T1: T3's actual measured p_clear_optimistic at this cell was 0.3885 "
          f"(results/phase_10e/REPORT.md), gap -0.2115 -- compare against the bound above "
          f"as a consistency check (bound must be >= 0.3885).")
    if threshold_row:
        print(f"T1: bound crosses p_breakeven at round_trip_bp <= "
              f"{threshold_row['round_trip_bp']:.2f}")
    else:
        print("T1: bound does NOT cross p_breakeven anywhere in [5, 70.98] bp -- "
              "strong negative signal (exact p_clear is provably no better than this bound).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
