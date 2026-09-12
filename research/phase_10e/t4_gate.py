#!/usr/bin/env python
"""
Phase 10e T4 — the Arm 1 gate.

THE VERDICT IS STATED SEPARATELY AND ALWAYS. Rows 10 and 12 are mutually exclusive, but they
do not partition the outcome space: "neither fired" collapses the named cell PAYING and the
named cell FAILING WHILE ANOTHER CELL CLEARS, which are opposite findings. So T4a classifies
the named cell into exactly one of

    both_below    both bounds below p_breakeven
    straddle      the bounds fall on opposite sides of p_breakeven   -> row 10
    both_above    both bounds above p_breakeven

and reports it alongside the grid-wide row-12 condition. A gate that returns the same summary
for its best and its second-worst outcome is the Phase 11 row-11 defect again.

THE GATE ROWS EVALUATED HERE
    10   the bounds straddle p_breakeven on the named cell            hard stop
    10a  R1 ambiguous share on the named cell > 0.25                  reporting trigger only
    11   R3 no-fill share on the named cell > 0.10                    hard stop
    12   optimistic p_clear below p_breakeven at EVERY cell           hard stop

No recommendation is made and no result is characterised (row 21). The agent describes the
picture; the read is Cooper's.

Usage: .venv/Scripts/python.exe research/phase_10e/t4_gate.py
"""
from __future__ import annotations

import json
import os

import duckdb
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = os.path.join(REPO, "config", "phase_10e.json")
SHARES = os.path.join(REPO, "results/phase_10e/artifacts/t3_shares.parquet")
ENTRIES = os.path.join(REPO, "results/phase_10e/artifacts/t1_candidate_entries.parquet")
OUT = "results/phase_10e/artifacts/t4_gate.json"


def no_fill_by_segment(cfg):
    """R3 on the named cell, plus the decomposition row 11 requires posting."""
    L = cfg["named_cell"]["latency_minutes"]
    c = duckdb.connect(); c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"ATTACH '{os.path.join(REPO,'data/duckdb/main.duckdb')}' AS m (READ_ONLY)")
    c.execute(f"create view ent as select * from read_parquet('{ENTRIES}')")
    c.execute("""create view bars as select ticker, event_date_canonical, momentum_pct,
                 minute_index, first_price from m.event_minute_bars_v2
                 where session_offset = 0""")
    q = lambda grp, where: c.execute(f"""
        select {grp} as k, count(*) as n_all,
               sum(case when f.first_price is null then 1 else 0 end) as n_nofill
        from ent e left join bars f
          on e.ticker = f.ticker and e.event_date_canonical = f.event_date_canonical
         and e.momentum_pct = f.momentum_pct and f.minute_index = e.minute_index + {L}
        {where} group by 1 order by 1""").fetchdf()
    by_det = q("e.det_segment", "")
    by_bar = q("e.bar_segment", "")
    by_age = q("""case when e.minutes_since_anchor < 30 then '0-29'
                       when e.minutes_since_anchor < 60 then '30-59'
                       when e.minutes_since_anchor < 120 then '60-119'
                       when e.minutes_since_anchor < 240 then '120-239'
                       else '240+' end""", "where e.det_segment = 'rth'")
    for d in (by_det, by_bar, by_age):
        d["share"] = d.n_nofill / d.n_all
    named = by_det[by_det.k == cfg["named_cell"]["det_segment"]]
    return {
        "named_cell_segment": cfg["named_cell"]["det_segment"],
        "named_cell_latency": L,
        "named_cell_no_fill_share": float(named["share"].iloc[0]),
        "named_cell_n": int(named["n_all"].iloc[0]),
        "named_cell_n_nofill": int(named["n_nofill"].iloc[0]),
        "by_det_segment": by_det.to_dict("records"),
        "by_entry_bar_segment": by_bar.to_dict("records"),
        "by_minutes_since_anchor_rth_anchored": by_age.to_dict("records"),
    }


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    nc = cfg["named_cell"]
    g = pd.read_parquet(SHARES)

    sel = g[(g.denominator == nc["denominator"])
            & (g.latency_minutes == nc["latency_minutes"])
            & (g.horizon_minutes == nc["horizon_minutes"])
            & (g.profit_k == nc["profit_k"]) & (g.stop_m == nc["stop_m"])]
    assert len(sel) == 1, f"named cell did not resolve uniquely: {len(sel)} rows"
    r = sel.iloc[0]
    be = float(r.p_breakeven)
    opt, pess = float(r.p_clear_optimistic), float(r.p_clear_pessimistic)
    verdict = ("both_above" if pess > be else
               "both_below" if opt < be else "straddle")

    # row 12: optimistic below break-even at EVERY cell in the grid
    pw = g[g.denominator == "print_weighted"]
    n_clear_opt = int((pw.p_clear_optimistic >= pw.p_breakeven).sum())
    row12 = bool(n_clear_opt == 0)

    nf = no_fill_by_segment(cfg)
    row11 = bool(nf["named_cell_no_fill_share"] > cfg["cooper_thresholds"]
                 ["row_11_no_fill_share_max"])
    row10 = bool(verdict == "straddle")
    row10a = bool(float(r.ambiguous_share) > cfg["cooper_thresholds"]
                  ["row_10a_r1_ambiguous_share_max"])

    out = {
        "task": "Phase 10e T4 -- the Arm 1 gate",
        "THE_VERDICT": {
            "_rule": ("stated separately and always, because two of the four outcomes fire "
                      "no row at all"),
            "named_cell": {k: nc[k] for k in
                           ("denominator", "det_segment", "latency_minutes",
                            "horizon_minutes", "profit_k", "stop_m")},
            "state": verdict,
            "p_clear_optimistic": opt,
            "p_clear_pessimistic": pess,
            "p_breakeven": be,
            "p_randomwalk": float(r.p_randomwalk),
            "drift_exists_optimistic": bool(opt > float(r.p_randomwalk)),
            "drift_exists_pessimistic": bool(pess > float(r.p_randomwalk)),
            "it_pays_optimistic": bool(opt > be),
            "it_pays_pessimistic": bool(pess > be),
            "n": int(r.n), "distinct_events": int(r.distinct_events),
            "effective_n": float(r.effective_n),
            "ci_event_opt": [float(r.ci_event_opt_lo), float(r.ci_event_opt_hi)],
            "ci_event_pess": [float(r.ci_event_pess_lo), float(r.ci_event_pess_hi)],
            "ci_ticker_opt": [float(r.ci_ticker_opt_lo), float(r.ci_ticker_opt_hi)],
            "ci_ticker_pess": [float(r.ci_ticker_pess_lo), float(r.ci_ticker_pess_hi)],
        },
        "three_class_shares_named_cell": {
            "optimistic": {"profit": opt, "stop": float(r.stop_share_optimistic),
                           "expiry": float(r.expiry_share)},
            "pessimistic": {"profit": pess, "stop": float(r.stop_share_pessimistic),
                            "expiry": float(r.expiry_share)},
            "note": "three classes sum to 1 under each bound separately (R2), asserted in T3",
        },
        "R1_ambiguous_share_named_cell": float(r.ambiguous_share),
        "R4_dead_tape_share_named_cell": float(r.dead_tape_share),
        "R3_no_fill": nf,
        "GATE_ROWS": {
            "row_10_straddle": {"fires": row10, "condition":
                                "bounds straddle p_breakeven on the named cell",
                                "observed": verdict},
            "row_10a_ambiguity_reporting_trigger": {
                "fires": row10a, "threshold":
                cfg["cooper_thresholds"]["row_10a_r1_ambiguous_share_max"],
                "observed": float(r.ambiguous_share),
                "note": "REPORTING TRIGGER, NOT A STOP"},
            "row_11_no_fill": {"fires": row11, "threshold":
                               cfg["cooper_thresholds"]["row_11_no_fill_share_max"],
                               "observed": nf["named_cell_no_fill_share"]},
            "row_12_arm1_gate": {
                "fires": row12,
                "condition": "optimistic p_clear below p_breakeven at EVERY cell",
                "n_cells_where_optimistic_clears": n_clear_opt,
                "n_cells_print_weighted": int(len(pw))},
        },
        "grid_summary_print_weighted": (
            g[g.denominator == "print_weighted"]
            [["latency_minutes", "horizon_minutes", "profit_k", "stop_m", "n",
              "distinct_events", "effective_n", "p_clear_optimistic",
              "p_clear_pessimistic", "p_breakeven", "p_randomwalk", "ambiguous_share",
              "expiry_share", "dead_tape_share", "thin_cell", "event_dominated"]]
            .sort_values(["latency_minutes", "horizon_minutes", "profit_k", "stop_m"])
            .to_dict("records")),
        "source": "research/phase_10e/t4_gate.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t4_gate.py",
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    v = out["THE_VERDICT"]
    print("=" * 72)
    print(f"T4 VERDICT on the named cell: {v['state'].upper()}")
    print("=" * 72)
    print(f"  p_clear optimistic  {v['p_clear_optimistic']:.4f}   "
          f"CI(event) [{v['ci_event_opt'][0]:.4f}, {v['ci_event_opt'][1]:.4f}]")
    print(f"  p_clear pessimistic {v['p_clear_pessimistic']:.4f}   "
          f"CI(event) [{v['ci_event_pess'][0]:.4f}, {v['ci_event_pess'][1]:.4f}]")
    print(f"  p_breakeven         {v['p_breakeven']:.4f}")
    print(f"  p_randomwalk        {v['p_randomwalk']:.4f}")
    print(f"  drift exists?  opt {v['drift_exists_optimistic']}  "
          f"pess {v['drift_exists_pessimistic']}")
    print(f"  it pays?       opt {v['it_pays_optimistic']}  pess {v['it_pays_pessimistic']}")
    print(f"  n {v['n']:,}   distinct events {v['distinct_events']:,}   "
          f"effective n {v['effective_n']:,.0f}")
    print("\nGATE ROWS")
    for k, d in out["GATE_ROWS"].items():
        print(f"  {'FIRES' if d['fires'] else 'pass ':6s} {k}   observed "
              f"{d.get('observed', d.get('n_cells_where_optimistic_clears'))}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
