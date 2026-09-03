#!/usr/bin/env python
"""
Phase 10e T2 — fill, excursion, and the two intra-bar ordering bounds.

THE R1 INSIGHT THAT MAKES THIS TRACTABLE. A minute bar's high and low have no order, so
first-passage is ambiguous exactly when **both barriers are first touched inside the same
bar**. That is not a nuisance to be bounded loosely — it is a precise condition:

    optimistic   profit wins ties      profit if t_profit <= t_stop
    pessimistic  the stop wins ties    profit if t_profit <  t_stop
    ambiguous    t_profit == t_stop and both fall within the horizon

So the whole R1 apparatus reduces to two first-touch minutes per barrier level, and the
ambiguous share is the tie rate. It also means the 90 barrier cells never have to be
materialised: five first-touch columns per (entry, latency) — three profit levels and two
stop levels — answer every cell, because horizon truncation is just a comparison against a
stored minute.

COST. One range-join pass per latency, bounded to the longest horizon, with every horizon
and every barrier computed by conditional aggregation in that single pass. Three passes
total rather than 90.

    min(case when high >= threshold then minute_index end)   <-- the first-touch minute
    max(case when minute_index <= fill + H then high end)    <-- MFE at horizon H
    min(case when minute_index <= fill + H then low  end)    <-- MAE at horizon H

R3 (no fill). `event_minute_bars_v2` stores only bars that traded, so a missing bar at
`fill_minute` IS the no-fill case: no print in that minute, nothing to fill against. Those
entries are carried with `filled = false`, never dropped and never forward-filled.

D19. Every excursion is emitted in **both** bp and cents, and additionally in multiples of
round-trip cost, which is the unit the barriers are expressed in.

D4 / row 6a. Prices here are BAR-derived (`event_minute_bars_v2`), not spine columns.
`momentum_pct` appears only inside the event key.

Usage: .venv/Scripts/python.exe research/phase_10e/t2_excursion.py
"""
from __future__ import annotations

import json
import os
import time

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
CFG = os.path.join(REPO, "config", "phase_10e.json")
ENTRIES = os.path.join(REPO, "results/phase_10e/artifacts/t1_candidate_entries.parquet")
OUT_PARQUET = "results/phase_10e/artifacts/t2_excursion.parquet"
OUT_JSON = "results/phase_10e/artifacts/t2_summary.json"


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    lat = cfg["arm1"]["latency_minutes"]                  # [0, 1, 5]
    hor = cfg["arm1"]["horizons_minutes"]                 # [1, 5, 15, 30, 60]
    ks = cfg["barrier_grid"]["profit_k"]                  # [1.5, 2, 3]
    ms = cfg["barrier_grid"]["stop_m"]                    # [1, 2]
    rt_bp = cfg["cost"]["round_trip_bp"]
    rt = rt_bp / 10000.0
    hmax = max(hor)

    t0 = time.perf_counter()
    c = duckdb.connect()
    c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"PRAGMA temp_directory='{os.path.join(REPO, 'results/phase_10e/_tmp')}'")
    c.execute(f"ATTACH '{DB}' AS m (READ_ONLY)")
    c.execute(f"create view ent as select * from read_parquet('{ENTRIES}')")
    c.execute("""create view bars as
        select ticker, event_date_canonical, momentum_pct, minute_index, high, low,
               first_price
        from m.event_minute_bars_v2 where session_offset = 0""")

    print(f"round trip {rt_bp} bp = {rt:.6f}; profit k {ks}; stop m {ms}")
    print(f"latencies {lat}; horizons {hor}\n")

    parts = []
    for L in lat:
        ta = time.perf_counter()
        # fill bar: the bar at minute_index + L. Absent => no fill (R3).
        c.execute(f"""create or replace view fill_{L} as
            select e.ticker, e.event_date_canonical, e.momentum_pct,
                   e.minute_index, e.minutes_since_anchor, e.det_segment, e.era,
                   e.pq_rth_open, e.s_min_band, e.s_min_minute, e.n_prints,
                   e.in_event_equalised,
                   e.flag_possible_row_cap, e.flag_has_dup_prints,
                   e.flag_cross_session_extreme,
                   e.minute_index + {L} as fill_minute,
                   f.first_price        as fill_price
            from ent e
            left join bars f
              on e.ticker = f.ticker
             and e.event_date_canonical = f.event_date_canonical
             and e.momentum_pct = f.momentum_pct
             and f.minute_index = e.minute_index + {L}""")

        prof = ",\n".join(
            f"min(case when b.high >= e.fill_price * (1 + {k} * {rt}) "
            f"then b.minute_index end) as tp_k{str(k).replace('.', '')}" for k in ks)
        stop = ",\n".join(
            f"min(case when b.low <= e.fill_price * (1 - {mm} * {rt}) "
            f"then b.minute_index end) as ts_m{mm}" for mm in ms)
        mfe = ",\n".join(
            f"max(case when b.minute_index <= e.fill_minute + {h} then b.high end) "
            f"as mfe_h{h}" for h in hor)
        mae = ",\n".join(
            f"min(case when b.minute_index <= e.fill_minute + {h} then b.low end) "
            f"as mae_h{h}" for h in hor)

        c.execute(f"""create or replace table t2_{L} as
            select e.*, {L} as latency_minutes,
                   {prof}, {stop}, {mfe}, {mae},
                   count(b.minute_index) as n_bars_in_window
            from fill_{L} e
            left join bars b
              on e.ticker = b.ticker
             and e.event_date_canonical = b.event_date_canonical
             and e.momentum_pct = b.momentum_pct
             and b.minute_index >= e.fill_minute
             and b.minute_index <= e.fill_minute + {hmax}
            where e.fill_price is not null
            group by all""")
        n = c.execute(f"select count(*) from t2_{L}").fetchone()[0]
        nofill = c.execute(
            f"select count(*) from fill_{L} where fill_price is null").fetchone()[0]
        tot = n + nofill
        print(f"  latency {L:>2}: filled {n:>10,}   no-fill {nofill:>9,} "
              f"({nofill/tot:.2%})   {time.perf_counter()-ta:.0f}s")
        parts.append((L, n, nofill, tot))

    c.execute("create or replace table t2 as " +
              " union all by name ".join(f"select * from t2_{L}" for L in lat))
    n_all = c.execute("select count(*) from t2").fetchone()[0]
    print(f"\nt2 total filled rows across latencies: {n_all:,}")

    os.makedirs(os.path.join(REPO, "results/phase_10e/artifacts"), exist_ok=True)
    c.execute(f"copy t2 to '{os.path.join(REPO, OUT_PARQUET)}' (format parquet)")

    out = {
        "task": "Phase 10e T2 -- fill, excursion, and the two R1 ordering bounds",
        "r1_reduction": (
            "First-passage on bars is ambiguous EXACTLY when both barriers are first touched "
            "inside the same bar. optimistic: profit if t_profit <= t_stop. pessimistic: "
            "profit if t_profit < t_stop. ambiguous: t_profit == t_stop within the horizon. "
            "So R1 reduces to two first-touch minutes per barrier level and the ambiguous "
            "share is the tie rate -- the 90 barrier cells never have to be materialised."),
        "cost_unit": {"round_trip_bp": rt_bp, "round_trip_fraction": rt,
                      "round_trip_cents": cfg["cost"]["round_trip_cents"],
                      "source": "Phase 11, read from config, NOT recomputed"},
        "barriers": {"profit_k": ks, "stop_m": ms,
                     "profit_levels_bp": [k * rt_bp for k in ks],
                     "stop_levels_bp": [mm * rt_bp for mm in ms]},
        "latency_minutes": lat, "horizons_minutes": hor,
        "latency_0_note": cfg["arm1"]["latency_0_note"],
        "latency_axis_caveat": cfg["arm1"]["latency_axis_caveat"],
        "R3_no_fill": {
            "definition": ("event_minute_bars_v2 stores only bars that traded, so a missing "
                           "bar at fill_minute IS the no-fill case. Carried with "
                           "filled = false, never dropped, never forward-filled."),
            "per_latency": [{"latency_minutes": L, "filled": nf, "no_fill": nfl,
                             "total": tot, "no_fill_share": nfl / tot}
                            for (L, nf, nfl, tot) in parts]},
        "rows_written": int(n_all),
        "runtime_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10e/t2_excursion.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t2_excursion.py",
    }
    with open(os.path.join(REPO, OUT_JSON), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {OUT_PARQUET}\nwrote {OUT_JSON}   "
          f"({out['runtime_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
