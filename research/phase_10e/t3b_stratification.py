#!/usr/bin/env python
"""
Phase 10e T3b — stratification by path position and by the resolution floor.

TWO AXES, AND THE SECOND IS WHERE THE 10-SERIES ENTERS.

  minutes_since_anchor   does WHERE you are on the path matter?
  s_min_minute band      does the tape's RESOLVABILITY at a moment relate to what the path
                         pays from that moment? `s_min = 2.26/lambda` is the one surviving
                         criterion of the whole 10-series, and this is the only place in
                         Phase 10e where it is asked to earn its keep.

Both are computed on the named cell's barrier pair and latency so the stratification is a
slice of the gate cell rather than a different question. RTH only for the s_min axis, per
the chart contract.

Clustered CIs reuse T3's construction: resample EVENTS, common random numbers across bands.

Usage: .venv/Scripts/python.exe research/phase_10e/t3b_stratification.py
"""
from __future__ import annotations

import json
import os
import time

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = os.path.join(REPO, "config", "phase_10e.json")
T2 = os.path.join(REPO, "results/phase_10e/artifacts/t2_excursion.parquet")
OUT = "results/phase_10e/artifacts/t3b_stratification.parquet"
OUT_JSON = "results/phase_10e/artifacts/t3b_stratification.json"
KTAG = {1.5: "k15", 2: "k2", 3: "k3"}


def boot(per_event, reps, seed, level, key):
    keys = per_event[key].to_numpy()
    uniq, inv = np.unique(keys, return_inverse=True)
    band = per_event["band"].to_numpy()
    ub, binv = np.unique(band, return_inverse=True)
    T = np.zeros((uniq.size, ub.size), np.float32); O = np.zeros_like(T); P = np.zeros_like(T)
    np.add.at(T, (inv, binv), per_event.n_total.to_numpy(np.float32))
    np.add.at(O, (inv, binv), per_event.n_prof_opt.to_numpy(np.float32))
    np.add.at(P, (inv, binv), per_event.n_prof_pess.to_numpy(np.float32))
    rng = np.random.default_rng(seed); a = (1 - level) / 2
    so, sp = [], []
    for start in range(0, reps, 250):
        n = min(250, reps - start)
        idx = rng.integers(0, uniq.size, size=(n, uniq.size))
        W = np.empty((n, uniq.size), np.float32)
        for i in range(n):
            W[i] = np.bincount(idx[i], minlength=uniq.size)
        tot = W @ T
        with np.errstate(divide="ignore", invalid="ignore"):
            so.append(np.where(tot > 0, (W @ O) / tot, np.nan))
            sp.append(np.where(tot > 0, (W @ P) / tot, np.nan))
    so, sp = np.vstack(so), np.vstack(sp)
    return {b: (float(np.nanquantile(so[:, i], a)), float(np.nanquantile(so[:, i], 1 - a)),
                float(np.nanquantile(sp[:, i], a)), float(np.nanquantile(sp[:, i], 1 - a)))
            for i, b in enumerate(ub)}


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    nc = cfg["named_cell"]
    L, H = nc["latency_minutes"], nc["horizon_minutes"]
    k, mm = nc["profit_k"], nc["stop_m"]
    rt = cfg["cost"]["round_trip_bp"] / 10000.0
    reps = cfg["inference"]["bootstrap_reps"]; seed = cfg["inference"]["bootstrap_seed"]
    level = cfg["inference"]["ci_level"]; min_n = cfg["inference"]["min_cell_n"]
    tp, ts = f"tp_{KTAG[k]}", f"ts_m{mm}"

    t0 = time.perf_counter()
    c = duckdb.connect(); c.execute("PRAGMA threads=4"); c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"create view t2 as select * from read_parquet('{T2}')")

    axes = {
        "minutes_since_anchor": ("""case when minutes_since_anchor < 15 then 'a 0-14'
              when minutes_since_anchor < 30 then 'b 15-29'
              when minutes_since_anchor < 60 then 'c 30-59'
              when minutes_since_anchor < 120 then 'd 60-119'
              when minutes_since_anchor < 240 then 'e 120-239'
              else 'f 240+' end""", ""),
        "s_min_band": ("s_min_band", "and det_segment = 'rth'"),
    }
    frames = []
    for axis, (expr, extra) in axes.items():
        pe = c.execute(f"""
            select ticker, event_date_canonical, momentum_pct, {expr} as band,
                   count(*) as n_total,
                   sum(case when p_in and (not s_in or {tp} <= {ts}) then 1 else 0 end) as n_prof_opt,
                   sum(case when p_in and (not s_in or {tp} <  {ts}) then 1 else 0 end) as n_prof_pess,
                   avg(mfe_h{H} / fill_price - 1) as mean_mfe,
                   median(mfe_h{H} / fill_price - 1) as median_mfe,
                   median(mae_h{H} / fill_price - 1) as median_mae
            from (select *, ({tp} is not null and {tp} <= fill_minute + {H}) as p_in,
                         ({ts} is not null and {ts} <= fill_minute + {H}) as s_in
                  from t2 where latency_minutes = {L} {extra})
            group by all""").fetchdf()
        pe["event_key"] = (pe.ticker + "|" + pe.event_date_canonical.astype(str) + "|"
                           + pe.momentum_pct.astype(str))
        ci = boot(pe, reps, seed, level, "event_key")
        g = pe.groupby("band", as_index=False).agg(
            n=("n_total", "sum"), n_prof_opt=("n_prof_opt", "sum"),
            n_prof_pess=("n_prof_pess", "sum"),
            distinct_events=("event_key", "nunique"),
            median_mfe=("median_mfe", "median"), median_mae=("median_mae", "median"))
        g["axis"] = axis
        g["p_clear_optimistic"] = g.n_prof_opt / g.n
        g["p_clear_pessimistic"] = g.n_prof_pess / g.n
        g["p_breakeven"] = (mm + 1) / (k + mm)
        g["p_randomwalk"] = mm / (k + mm)
        g["ci_opt_lo"] = g.band.map(lambda b: ci[b][0])
        g["ci_opt_hi"] = g.band.map(lambda b: ci[b][1])
        g["ci_pess_lo"] = g.band.map(lambda b: ci[b][2])
        g["ci_pess_hi"] = g.band.map(lambda b: ci[b][3])
        g["thin_cell"] = g.n < min_n
        g["median_mfe_bp"] = g.median_mfe * 10000
        g["median_mae_bp"] = g.median_mae * 10000
        frames.append(g)
        print(f"  {axis}: {len(g)} bands ({time.perf_counter()-t0:.0f}s)")

    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(os.path.join(REPO, OUT), index=False)

    summ = {
        "task": "Phase 10e T3b -- stratification by path position and by s_min",
        "evaluated_on": {"latency_minutes": L, "horizon_minutes": H, "profit_k": k,
                         "stop_m": mm, "note": "the named cell's barrier pair and latency"},
        "s_min_axis_note": ("RTH only, per the chart contract. This is the only place in "
                            "Phase 10e where the 10-series' one surviving criterion is asked "
                            "to earn its keep against forward excursion."),
        "bands": out.to_dict("records"),
        "runtime_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10e/t3b_stratification.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t3b_stratification.py",
    }
    with open(os.path.join(REPO, OUT_JSON), "w", encoding="utf-8") as fh:
        json.dump(summ, fh, indent=2, default=str)

    for axis in axes:
        d = out[out.axis == axis]
        print(f"\n{axis}  (p_breakeven {d.p_breakeven.iloc[0]:.3f}, "
              f"p_randomwalk {d.p_randomwalk.iloc[0]:.3f})")
        for r in d.itertuples(index=False):
            print(f"   {str(r.band):16s} opt {r.p_clear_optimistic:.4f} "
                  f"[{r.ci_opt_lo:.4f},{r.ci_opt_hi:.4f}]  "
                  f"pess {r.p_clear_pessimistic:.4f}  n {r.n:>9,}  ev {r.distinct_events:>6,}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
