"""T5 (revised, per Cooper's go-ahead after T0-T4) -- the EXACT reclassification T1 flagged
as needed and did not run.

T1 found t2_excursion.parquet cannot support an exact ordering-sensitive p_clear at a swept
round_trip_bp, because it stores touch TIMES only at the six preset barrier levels, not a
continuous path. But research/phase_10e/t2_excursion.py:101-106 shows those touch times are
computed ENTIRELY from event_minute_bars_v2's high/low columns at MINUTE granularity --
`min(case when b.high >= fill_price*(1+k*rt) then minute_index end)`. That query can be
re-parametrised at an arbitrary swept `rt` directly against event_minute_bars_v2 (already
materialised, full universe -- the SAME cache research/phase_10e/t3_shares.py and t4_gate.py
already query at full-universe scale, not the raw 4.9B/3.8B-row tick tables). So the exact
quantity IS derivable without a new tick pass -- it just is not derivable from t2_excursion.parquet
alone, which is what T1 actually established.

Reuses research/phase_10e/t2_excursion.py's own SQL pattern (not reimplemented from scratch) and
research/phase_10e/t3_shares.py's outcome logic (optimistic/pessimistic tie-break), both imported
by re-deriving the same expressions against the same source views, at the closest cell only
(latency=1, horizon=60, profit_k=3, stop_m=2) -- not the full 90-cell grid, which is out of scope
here.

Usage: .venv/Scripts/python.exe -m research.impact_by_participation.t5_exact_reclassification
"""
from __future__ import annotations

import json
import os
import pathlib
import time

import duckdb
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
DB = REPO / "data" / "duckdb" / "main.duckdb"
CFG = REPO / "config" / "phase_10e.json"
ENTRIES = REPO / "results" / "phase_10e" / "artifacts" / "t1_candidate_entries.parquet"
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
CHARTS = REPO / "results" / "impact_by_participation" / "charts"

LATENCY = 1
HORIZON = 60
PROFIT_K = 3
STOP_M = 2
P_BREAKEVEN = (STOP_M + 1) / (PROFIT_K + STOP_M)   # 0.6000, exactly
BASELINE_RT_BP = 70.98
SWEEP_BP = np.exp(np.linspace(np.log(BASELINE_RT_BP), np.log(5.0), 40))


def main() -> int:
    t0 = time.perf_counter()
    cfg = json.load(open(CFG, encoding="utf-8"))
    assert cfg["cost"]["round_trip_bp"] == BASELINE_RT_BP, "baseline cost drifted from config"

    c = duckdb.connect()
    c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"ATTACH '{DB}' AS m (READ_ONLY)")
    c.execute(f"create view ent as select * from read_parquet('{ENTRIES.as_posix()}')")
    c.execute("""create view bars as
        select ticker, event_date_canonical, momentum_pct, minute_index, high, low, first_price
        from m.event_minute_bars_v2 where session_offset = 0""")
    c.execute(f"""create or replace view fill as
        select e.ticker, e.event_date_canonical, e.momentum_pct,
               e.minute_index + {LATENCY} as fill_minute,
               f.first_price as fill_price
        from ent e
        left join bars f
          on e.ticker = f.ticker and e.event_date_canonical = f.event_date_canonical
         and e.momentum_pct = f.momentum_pct and f.minute_index = e.minute_index + {LATENCY}
        where f.first_price is not null""")
    c.execute(f"""create or replace table window_bars as
        select e.ticker, e.event_date_canonical, e.momentum_pct, e.fill_minute, e.fill_price,
               b.minute_index, b.high, b.low
        from fill e
        join bars b
          on e.ticker = b.ticker and e.event_date_canonical = b.event_date_canonical
         and e.momentum_pct = b.momentum_pct
         and b.minute_index >= e.fill_minute and b.minute_index <= e.fill_minute + {HORIZON}""")
    n_entries = c.execute("select count(*) from fill").fetchone()[0]
    n_events = c.execute(
        "select count(distinct (ticker, event_date_canonical)) from fill").fetchone()[0]
    print(f"entries with a fill at latency={LATENCY}: {n_entries:,} across {n_events:,} events "
          f"({time.perf_counter()-t0:.1f}s)")

    rows = []
    for rt_bp in SWEEP_BP:
        rt = rt_bp / 10000.0
        r = c.execute(f"""
            with touches as (
                select ticker, event_date_canonical, momentum_pct, fill_minute, fill_price,
                       min(case when high >= fill_price * (1 + {PROFIT_K} * {rt})
                           then minute_index end) as tp,
                       min(case when low  <= fill_price * (1 - {STOP_M} * {rt})
                           then minute_index end) as ts
                from window_bars group by all
            )
            select
                count(*) as n,
                sum(case when tp is not null and tp <= fill_minute + {HORIZON}
                         and (ts is null or ts > fill_minute + {HORIZON} or tp <= ts)
                    then 1 else 0 end) as n_prof_opt,
                sum(case when tp is not null and tp <= fill_minute + {HORIZON}
                         and (ts is null or ts > fill_minute + {HORIZON} or tp < ts)
                    then 1 else 0 end) as n_prof_pess,
                sum(case when tp is not null and tp <= fill_minute + {HORIZON}
                         and ts is not null and ts <= fill_minute + {HORIZON} and tp = ts
                    then 1 else 0 end) as n_ambig,
                sum(case when (tp is null or tp > fill_minute + {HORIZON})
                         and (ts is null or ts > fill_minute + {HORIZON})
                    then 1 else 0 end) as n_expiry
            from touches
        """).fetchone()
        n, n_prof_opt, n_prof_pess, n_ambig, n_expiry = r
        rows.append({
            "round_trip_bp": float(rt_bp),
            "profit_barrier_bp": float(PROFIT_K * rt_bp), "stop_barrier_bp": float(STOP_M * rt_bp),
            "n": int(n),
            "p_clear_optimistic": n_prof_opt / n, "p_clear_pessimistic": n_prof_pess / n,
            "ambiguous_share": n_ambig / n,
            "expiry_share": n_expiry / n,
        })
        print(f"  rt_bp={rt_bp:6.2f}  p_clear_opt={n_prof_opt/n:.4f}  "
              f"p_clear_pess={n_prof_pess/n:.4f}  ambig={n_ambig/n:.4f}  "
              f"expiry={n_expiry/n:.4f}", flush=True)

    baseline = rows[0]
    baseline_gap = baseline["p_clear_optimistic"] - P_BREAKEVEN
    crossing = [r for r in rows if r["p_clear_optimistic"] >= P_BREAKEVEN]
    threshold_row = crossing[-1] if crossing else None

    # Sanity checks against what's already on record.
    consistency = {
        "t3_shares_baseline_p_clear_optimistic": 0.3885,
        "this_script_baseline_p_clear_optimistic": baseline["p_clear_optimistic"],
        "match_within_tolerance": abs(baseline["p_clear_optimistic"] - 0.3885) < 0.01,
        "t1_upper_bound_at_baseline": 0.6501,
        "this_script_baseline_leq_t1_bound": baseline["p_clear_optimistic"] <= 0.6501,
        "note": ("this script's baseline should closely reproduce t3_shares.py's own "
                 "print_weighted, latency=1, horizon=60, k=3, m=2 cell (0.3885) since it "
                 "reuses the identical SQL pattern -- and must be <= T1's 0.6501 upper bound, "
                 "since the bound ignores order and this does not."),
    }

    out = {
        "task": "T5 (exact reclassification)", "phase": "impact_by_participation",
        "cell": {"latency_minutes": LATENCY, "horizon_minutes": HORIZON,
                 "profit_k": PROFIT_K, "stop_m": STOP_M},
        "p_breakeven": P_BREAKEVEN,
        "universe": "full (results/phase_10e/artifacts/t1_candidate_entries.parquet, all "
                    "candidate entries, not the dev cohort) -- event_minute_bars_v2 is an "
                    "already-materialised cache, not a new pass over filtered_trades/quotes",
        "n_entries": int(n_entries), "n_events": int(n_events),
        "baseline_round_trip_bp": BASELINE_RT_BP,
        "baseline_gap_exact": float(baseline_gap),
        "consistency_checks": consistency,
        "sweep": rows,
        "threshold_crosses_breakeven_at": threshold_row,
        "conclusion": (
            "EXACT gap closes" if threshold_row and threshold_row["round_trip_bp"] >= min(r["round_trip_bp"] for r in rows)
            else "does not close anywhere in the swept range"
        ) if threshold_row else "the exact p_clear_optimistic does NOT cross p_breakeven at any "
            f"round_trip_bp from {BASELINE_RT_BP} down to {SWEEP_BP[-1]:.1f} bp",
        "runtime_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/impact_by_participation/t5_exact_reclassification.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t5_exact_reclassification",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "t5_exact_reclassification.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"\nBASELINE (rt_bp={BASELINE_RT_BP}): p_clear_optimistic={baseline['p_clear_optimistic']:.4f} "
          f"vs p_breakeven={P_BREAKEVEN:.4f} (gap {baseline_gap:+.4f})")
    print(f"Consistency: matches T3's 0.3885? {consistency['match_within_tolerance']}   "
          f"<= T1's 0.6501 bound? {consistency['this_script_baseline_leq_t1_bound']}")
    if threshold_row:
        print(f"Exact p_clear_optimistic crosses p_breakeven at round_trip_bp <= "
              f"{threshold_row['round_trip_bp']:.2f}")
    else:
        print(f"Exact p_clear_optimistic does NOT cross p_breakeven anywhere from "
              f"{BASELINE_RT_BP} down to {SWEEP_BP[-1]:.1f} bp.")
    print(f"\n({out['runtime_seconds']}s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
