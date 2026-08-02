"""
Phase 8 T4 - anchor construction (clock + rung) and horizon prices.

Scan-free (event_minute_bars_v2 only). Produces the long per
(event, anchor, horizon) price table t4_anchors.parquet used by T5, plus
rung-attrition stats and chart 07.

Price convention (all anchors and horizons): last trade at or before the
target minute = last_price of the bar with the greatest minute_index <=
target on the target session. Implemented with a DuckDB ASOF LEFT JOIN.

Clock anchors (fixed minute_index on T0; t0_close = last T0 print):
  0900=300 rth_open=330 open+5=335 open+15=345 open+30=360 open+60=390
  open+120=450 t0_close=last_t0_minute
Rung anchors (event-relative): first T0 minute where cumulative T0 extended
volume >= mult * b_session (b_session from T3). mult in {1,2,5,10}.

Horizons per anchor: anchor+30, anchor+60 (on T0), t0_close, t1_close,
t3_close (last extended print on T0/T+1/T+3).

Flags (carried, never imputed):
  anchor_undefined  = no T0 print at/before the clock anchor minute, OR the
                      rung is never reached.
  horizon_undefined = anchor+30/+60 target beyond the last T0 print, or the
                      T+1/T+3 session absent in v2.
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
T3_PATH = "results/phase_8/artifacts/t3_participation.parquet"
CONFIG = "config/phase_8.json"
OUT_PARQUET = "results/phase_8/artifacts/t4_anchors.parquet"
OUT_JSON = "results/phase_8/artifacts/t4_anchors_summary.json"

RUNG_MULTS = [1, 2, 5, 10]
HORIZONS = ["anchor+30", "anchor+60", "t0_close", "t1_close", "t3_close"]


def crossing_bin(mi: float) -> str:
    if mi is None or (isinstance(mi, float) and np.isnan(mi)):
        return None
    # minute_index origin 04:00 ET; ET minute = 240 + mi
    if mi < 330:
        return "premarket (04:00-09:30)"
    if mi < 390:
        return "open-10:30"
    if mi < 480:
        return "10:30-12:00"
    if mi < 600:
        return "12:00-14:00"
    if mi < 720:
        return "14:00-16:00"
    return "post (16:00-20:00)"


def et_time(mi: float) -> str:
    if mi is None or (isinstance(mi, float) and np.isnan(mi)):
        return None
    total = 240 + int(mi)
    return f"{total // 60:02d}:{total % 60:02d}"


def main():
    with open(CONFIG) as f:
        cfg = json.load(f)
    clock = {a["name"]: a["minute_index"] for a in cfg["clock_anchors"]["anchors"]}

    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    d1 = pd.read_parquet(D1_PATH)
    d1["event_date_canonical"] = pd.to_datetime(d1["event_date_canonical"])
    con.register("d1", d1)
    con.execute("CREATE TEMP TABLE d1k AS SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp FROM d1")

    t3 = pd.read_parquet(T3_PATH)
    t3["event_date_canonical"] = pd.to_datetime(t3["event_date_canonical"])
    bs = t3[["ticker", "event_date_canonical", "mp", "b_session", "participation_class"]].copy()
    con.register("bs", bs)

    # D1 bars for the needed offsets, materialized once (scan-free reuse)
    con.execute("""
        CREATE TEMP TABLE p8bars AS
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp,
               b.session_offset, b.minute_index, b.last_price, b.volume
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical
                AND ROUND(b.momentum_pct,2)=d1k.mp
        WHERE b.session_offset IN (0,1,3)
    """)

    # per-event T0 stats + session presence
    stats = con.execute("""
        SELECT ticker, event_date_canonical, mp,
               MIN(minute_index) FILTER (session_offset=0) AS first_t0_mi,
               MAX(minute_index) FILTER (session_offset=0) AS last_t0_mi,
               COUNT(*) FILTER (session_offset=1) > 0 AS has_t1,
               COUNT(*) FILTER (session_offset=3) > 0 AS has_t3
        FROM p8bars GROUP BY 1,2,3
    """).fetchdf()
    stats["event_date_canonical"] = pd.to_datetime(stats["event_date_canonical"])

    # rung crossing minutes: first T0 minute where cum vol >= mult*b_session
    rung = con.execute(f"""
        WITH cum AS (
            SELECT p.ticker, p.event_date_canonical, p.mp, p.minute_index,
                   SUM(p.volume) OVER (PARTITION BY p.ticker,p.event_date_canonical,p.mp
                                       ORDER BY p.minute_index) AS cv
            FROM p8bars p WHERE p.session_offset=0
        )
        SELECT c.ticker, c.event_date_canonical, c.mp,
               {", ".join([f"MIN(c.minute_index) FILTER (c.cv >= {m}*bs.b_session) AS rung_{m}_mi" for m in RUNG_MULTS])}
        FROM cum c JOIN bs ON c.ticker=bs.ticker AND c.event_date_canonical=bs.event_date_canonical AND c.mp=bs.mp
        WHERE bs.b_session IS NOT NULL
        GROUP BY 1,2,3
    """).fetchdf()
    rung["event_date_canonical"] = pd.to_datetime(rung["event_date_canonical"])

    key = ["ticker", "event_date_canonical", "mp"]
    ev = stats.merge(rung, on=key, how="left").merge(
        bs[key + ["b_session", "participation_class"]], on=key, how="left")

    # ---- build anchor-minute frame (event x anchor) ----
    rows = []
    for r in ev.itertuples(index=False):
        rd = r._asdict()
        first_t0, last_t0 = rd["first_t0_mi"], rd["last_t0_mi"]
        for name, m in clock.items():
            if name == "t0_close":
                amin = last_t0
                undef = pd.isna(last_t0)
            else:
                amin = m
                undef = pd.isna(first_t0) or (first_t0 > m)
            rows.append({**{k: rd[k] for k in key}, "anchor_name": name, "anchor_kind": "clock",
                         "anchor_minute": (np.nan if undef else amin), "anchor_undefined": bool(undef),
                         "last_t0_mi": last_t0, "has_t1": rd["has_t1"], "has_t3": rd["has_t3"]})
        for m in RUNG_MULTS:
            cm = rd.get(f"rung_{m}_mi")
            undef = pd.isna(cm)
            rows.append({**{k: rd[k] for k in key}, "anchor_name": f"rung_{m}x", "anchor_kind": "rung",
                         "anchor_minute": (np.nan if undef else cm), "anchor_undefined": bool(undef),
                         "last_t0_mi": last_t0, "has_t1": rd["has_t1"], "has_t3": rd["has_t3"]})
    A = pd.DataFrame(rows)
    A["crossing_minute"] = np.where(A["anchor_kind"] == "rung", A["anchor_minute"], np.nan)
    A["crossing_bin"] = A["crossing_minute"].map(crossing_bin)
    A["crossing_et"] = A["crossing_minute"].map(et_time)

    # ---- build targets (event x anchor x {anchor + horizons}) ----
    trows = []
    for r in A.itertuples(index=False):
        d = r._asdict()
        if d["anchor_undefined"]:
            continue
        am = d["anchor_minute"]
        base = {k: d[k] for k in key}
        base["anchor_name"] = d["anchor_name"]
        # anchor itself
        trows.append({**base, "role": "anchor", "session_offset": 0, "target_minute": am, "pre_undef": False})
        # anchor+30 / +60 (undefined beyond last T0 print)
        for h, dd in [("anchor+30", 30), ("anchor+60", 60)]:
            tm = am + dd
            trows.append({**base, "role": h, "session_offset": 0, "target_minute": tm,
                          "pre_undef": bool(tm > d["last_t0_mi"])})
        # t0_close
        trows.append({**base, "role": "t0_close", "session_offset": 0, "target_minute": d["last_t0_mi"], "pre_undef": False})
        # t1_close / t3_close
        trows.append({**base, "role": "t1_close", "session_offset": 1, "target_minute": 959, "pre_undef": not bool(d["has_t1"])})
        trows.append({**base, "role": "t3_close", "session_offset": 3, "target_minute": 959, "pre_undef": not bool(d["has_t3"])})
    T = pd.DataFrame(trows)
    con.register("targets", T)

    # ---- ASOF join: last_price at/before target on the target session ----
    priced = con.execute("""
        SELECT t.ticker, t.event_date_canonical, t.mp, t.anchor_name, t.role,
               t.session_offset, t.target_minute, t.pre_undef, b.last_price AS price
        FROM targets t
        ASOF LEFT JOIN p8bars b
          ON t.ticker=b.ticker AND t.event_date_canonical=b.event_date_canonical
         AND t.mp=b.mp AND t.session_offset=b.session_offset
         AND t.target_minute >= b.minute_index
    """).fetchdf()
    priced["event_date_canonical"] = pd.to_datetime(priced["event_date_canonical"])

    # pivot to per (event, anchor): anchor_price + horizon prices + undef flags
    anc = priced[priced.role == "anchor"][key + ["anchor_name", "price"]].rename(columns={"price": "anchor_price"})
    long = anc.copy()
    hz = priced[priced.role != "anchor"].copy()
    hz["horizon_undefined"] = hz["pre_undef"] | hz["price"].isna()
    hz = hz.rename(columns={"role": "horizon_name", "price": "horizon_price"})
    grid = hz[key + ["anchor_name", "horizon_name", "horizon_price", "horizon_undefined"]].merge(
        long, on=key + ["anchor_name"], how="left")

    # attach anchor labels (kind, minute, crossing) from A; anchor_undefined anchors have no grid rows
    grid = grid.merge(A[key + ["anchor_name", "anchor_kind", "anchor_minute",
                               "crossing_minute", "crossing_bin", "crossing_et"]],
                      on=key + ["anchor_name"], how="left")
    grid["anchor_undefined"] = grid["anchor_price"].isna()
    grid.to_parquet(OUT_PARQUET, index=False)

    # ---- rung attrition (T4c) ----
    n_d1 = len(ev)
    attr = {}
    for m in RUNG_MULTS:
        col = f"rung_{m}_mi"
        reached = ev[col].notna()
        cm = ev.loc[reached, col]
        attr[f"rung_{m}x"] = {
            "n_reaching": int(reached.sum()),
            "frac_of_d1": float(reached.mean()),
            "median_crossing_minute_index": (float(cm.median()) if len(cm) else None),
            "median_crossing_et": (et_time(cm.median()) if len(cm) else None),
        }

    # anchor_undefined rates per clock anchor (escalation row 7). Threshold from
    # config: A10.1b raised it 10% -> 15% for clock anchors (Cooper 2026-08-01).
    row7_threshold = cfg.get("amendment_a10_1", {}).get("escalation_row_7_threshold_clock_anchor", 0.10)
    anc_undef = {}
    for name in clock:
        sub = A[A.anchor_name == name]
        anc_undef[name] = {"anchor_undefined_n": int(sub["anchor_undefined"].sum()),
                           "anchor_undefined_frac": float(sub["anchor_undefined"].mean())}
    row7_fail = {n: v for n, v in anc_undef.items() if v["anchor_undefined_frac"] > row7_threshold}

    summary = {
        "phase": "8", "task": "T4",
        "source": "research/phase_8/t4_anchors.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "n_d1": n_d1,
        "rung_attrition": attr,
        "clock_anchor_undefined": anc_undef,
        "escalation_row_7_threshold": row7_threshold,
        "escalation_row_7_threshold_note": "A10.1b raised 10% -> 15% for clock anchors (Cooper 2026-08-01); 0900 at 11.04% now passes",
        "escalation_row_7_fail_anchors": row7_fail,
        "escalation_row_7_triggered": len(row7_fail) > 0,
        "artifact": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if summary["escalation_row_7_triggered"]:
        print("\n*** ESCALATION ROW 7 TRIGGERED (clock anchor_undefined > 10%) - HARD STOP ***")


if __name__ == "__main__":
    main()
