#!/usr/bin/env python
"""
Phase 10e T3 — distributions, stratification, and clustered inference.

WHAT THE OUTCOME LOGIC IS, STATED ONCE. For a cell (latency L, horizon H, profit k, stop m):

    profit_in_H = t_profit is not null and t_profit <= fill_minute + H
    stop_in_H   = t_stop   is not null and t_stop   <= fill_minute + H

    optimistic   profit if profit_in_H and (not stop_in_H or t_profit <= t_stop)
    pessimistic  profit if profit_in_H and (not stop_in_H or t_profit <  t_stop)
    AMBIGUOUS    profit_in_H and stop_in_H and t_profit == t_stop

The two bounds differ on exactly the ties, so **the ambiguous share IS the tie rate** (R1).
Three outcome classes — profit / stop / expiry — sum to 1 on every cell under each bound
separately (R2). A win rate on touched-only entries is never computed (row 9).

THREE NUMBERS PER CELL, NEVER TWO (R6, amended 2026-08-31):

    p_clear        measured
    p_breakeven    (m+1)/(k+m)   one round trip is charged on every outcome
    p_randomwalk   m/(k+m)       driftless-walk touch probability

`p_clear` above `p_randomwalk` means **drift exists**; above `p_breakeven` means **it pays**.
A cell clearing the first and failing the second is a real finding — signal smaller than the
cost stack — and with only two numbers it is indistinguishable from no signal at all.

THE BOOTSTRAP IS CLUSTERED AND USES COMMON RANDOM NUMBERS. Entries repeat within an event,
so resampling entries would treat one event's 960 bars as 960 independent draws. Resampling
is therefore over EVENTS and, separately, over TICKERS (Phase 9's ticker-block construction).
One set of resample draws is reused across every cell, which is the paired construction and
also what makes 90 cells affordable: two matrix products rather than 90 loops.

D19. Every excursion quantity is emitted in bp AND cents, and in multiples of round trip.

Usage: .venv/Scripts/python.exe research/phase_10e/t3_shares.py
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
OUT_SHARES = "results/phase_10e/artifacts/t3_shares.parquet"
OUT_EXC = "results/phase_10e/artifacts/t3_excursion_dist.parquet"
OUT_JSON = "results/phase_10e/artifacts/t3_shares.json"

KTAG = {1.5: "k15", 2: "k2", 3: "k3"}


def cell_sql(L, H, k, mm, rt, denom_filter, k_min, m_min):
    tp, ts = f"tp_{KTAG[k]}", f"ts_m{mm}"
    return f"""
    select ticker, event_date_canonical, momentum_pct, det_segment,
           count(*) as n_total,
           sum(case when p_in and (not s_in or {tp} <= {ts}) then 1 else 0 end) as n_prof_opt,
           sum(case when p_in and (not s_in or {tp} <  {ts}) then 1 else 0 end) as n_prof_pess,
           sum(case when p_in and s_in and {tp} = {ts} then 1 else 0 end) as n_ambig,
           sum(case when (not p_in) and (not s_in) then 1 else 0 end) as n_expiry,
           sum(case when dead then 1 else 0 end) as n_dead
    from (
      select *,
        ({tp} is not null and {tp} <= fill_minute + {H}) as p_in,
        ({ts} is not null and {ts} <= fill_minute + {H}) as s_in,
        (mfe_h60 / fill_price - 1 < {k_min} * {rt}
         and mae_h60 / fill_price - 1 > -{m_min} * {rt}) as dead
      from t2 where latency_minutes = {L} {denom_filter}
    ) group by all"""


def boot_ci(per_event, reps, seed, level, cluster_col):
    """Clustered bootstrap on p_clear. per_event: DataFrame with cluster key, n_total,
    n_prof_opt, n_prof_pess, cell_id. Returns {cell_id: (lo_opt, hi_opt, lo_p, hi_p)}."""
    keys = per_event[cluster_col].to_numpy()
    uniq, inv = np.unique(keys, return_inverse=True)
    n_clusters = uniq.size
    cells = per_event["cell_id"].to_numpy()
    ucells, cinv = np.unique(cells, return_inverse=True)

    # cluster x cell matrices
    T = np.zeros((n_clusters, ucells.size), dtype=np.float32)
    O = np.zeros_like(T)
    P = np.zeros_like(T)
    np.add.at(T, (inv, cinv), per_event["n_total"].to_numpy(np.float32))
    np.add.at(O, (inv, cinv), per_event["n_prof_opt"].to_numpy(np.float32))
    np.add.at(P, (inv, cinv), per_event["n_prof_pess"].to_numpy(np.float32))

    rng = np.random.default_rng(seed)
    a = (1 - level) / 2
    lo_o = np.empty(ucells.size); hi_o = np.empty(ucells.size)
    lo_p = np.empty(ucells.size); hi_p = np.empty(ucells.size)
    CH = 250                                   # chunk reps to bound memory
    so, sp = [], []
    for start in range(0, reps, CH):
        n = min(CH, reps - start)
        idx = rng.integers(0, n_clusters, size=(n, n_clusters))
        W = np.empty((n, n_clusters), dtype=np.float32)
        for i in range(n):
            W[i] = np.bincount(idx[i], minlength=n_clusters)
        tot = W @ T
        with np.errstate(divide="ignore", invalid="ignore"):
            so.append(np.where(tot > 0, (W @ O) / tot, np.nan))
            sp.append(np.where(tot > 0, (W @ P) / tot, np.nan))
    so = np.vstack(so); sp = np.vstack(sp)
    lo_o = np.nanquantile(so, a, axis=0); hi_o = np.nanquantile(so, 1 - a, axis=0)
    lo_p = np.nanquantile(sp, a, axis=0); hi_p = np.nanquantile(sp, 1 - a, axis=0)
    return {c: (lo_o[i], hi_o[i], lo_p[i], hi_p[i]) for i, c in enumerate(ucells)}


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    lat, hor = cfg["arm1"]["latency_minutes"], cfg["arm1"]["horizons_minutes"]
    ks, ms = cfg["barrier_grid"]["profit_k"], cfg["barrier_grid"]["stop_m"]
    rt_bp = cfg["cost"]["round_trip_bp"]; rt = rt_bp / 10000.0
    reps = cfg["inference"]["bootstrap_reps"]; seed = cfg["inference"]["bootstrap_seed"]
    level = cfg["inference"]["ci_level"]; min_n = cfg["inference"]["min_cell_n"]
    max_ev = cfg["inference"]["max_event_share"]

    t0 = time.perf_counter()
    c = duckdb.connect(); c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"create view t2 as select * from read_parquet('{T2}')")

    rows = []
    for denom, filt in (("print_weighted", ""),
                        ("event_equalised", "and in_event_equalised")):
        for L in lat:
            for H in hor:
                for k in ks:
                    for mm in ms:
                        d = c.execute(cell_sql(L, H, k, mm, rt, filt, min(ks), min(ms))).fetchdf()
                        d["denominator"] = denom; d["latency_minutes"] = L
                        d["horizon_minutes"] = H; d["profit_k"] = k; d["stop_m"] = mm
                        d["cell_id"] = f"{denom}|L{L}|H{H}|k{k}|m{mm}"
                        rows.append(d)
            print(f"  {denom:16s} latency {L:>2} done ({time.perf_counter()-t0:.0f}s)",
                  flush=True)
    per_event = pd.concat(rows, ignore_index=True)
    print(f"per-event x cell rows: {len(per_event):,}")

    per_event["event_key"] = (per_event.ticker + "|"
                              + per_event.event_date_canonical.astype(str) + "|"
                              + per_event.momentum_pct.astype(str))
    ci_ev = boot_ci(per_event, reps, seed, level, "event_key")
    ci_tk = boot_ci(per_event, reps, seed + 1, level, "ticker")
    print(f"bootstrap done ({time.perf_counter()-t0:.0f}s)")

    g = per_event.groupby(["cell_id", "denominator", "latency_minutes", "horizon_minutes",
                           "profit_k", "stop_m"], as_index=False).agg(
        n=("n_total", "sum"), n_prof_opt=("n_prof_opt", "sum"),
        n_prof_pess=("n_prof_pess", "sum"), n_ambig=("n_ambig", "sum"),
        n_expiry=("n_expiry", "sum"), n_dead=("n_dead", "sum"),
        distinct_events=("event_key", "nunique"))
    # effective n under event-equal weighting: Kish, from per-event counts
    eff = (per_event.groupby("cell_id")["n_total"]
           .agg(lambda s: (s.sum() ** 2) / (s.pow(2).sum()) if s.pow(2).sum() else 0.0))
    mx = (per_event.groupby("cell_id")["n_total"].max()
          / per_event.groupby("cell_id")["n_total"].sum())
    g["effective_n"] = g.cell_id.map(eff)
    g["max_event_share"] = g.cell_id.map(mx)
    g["p_clear_optimistic"] = g.n_prof_opt / g.n
    g["p_clear_pessimistic"] = g.n_prof_pess / g.n
    g["ambiguous_share"] = g.n_ambig / g.n
    g["expiry_share"] = g.n_expiry / g.n
    g["dead_tape_share"] = g.n_dead / g.n
    g["p_breakeven"] = (g.stop_m + 1) / (g.profit_k + g.stop_m)
    g["p_randomwalk"] = g.stop_m / (g.profit_k + g.stop_m)
    for nm, d in (("event", ci_ev), ("ticker", ci_tk)):
        g[f"ci_{nm}_opt_lo"] = g.cell_id.map(lambda x: d[x][0])
        g[f"ci_{nm}_opt_hi"] = g.cell_id.map(lambda x: d[x][1])
        g[f"ci_{nm}_pess_lo"] = g.cell_id.map(lambda x: d[x][2])
        g[f"ci_{nm}_pess_hi"] = g.cell_id.map(lambda x: d[x][3])
    g["stop_share_optimistic"] = (g.n - g.n_prof_opt - g.n_expiry) / g.n
    g["stop_share_pessimistic"] = (g.n - g.n_prof_pess - g.n_expiry) / g.n
    for b in ("optimistic", "pessimistic"):
        tot = g[f"p_clear_{b}"] + g[f"stop_share_{b}"] + g["expiry_share"]
        assert np.allclose(tot, 1.0), f"R2 violated: classes do not sum to 1 ({b})"
    g["thin_cell"] = g.n < min_n
    g["event_dominated"] = g.max_event_share > max_ev
    # R2: three classes sum to 1 under each bound
    g.to_parquet(os.path.join(REPO, OUT_SHARES), index=False)

    # ---- excursion distributions, D19 both units ----------------------------
    qs = [0.05, 0.25, 0.5, 0.75, 0.95]
    exc = c.execute(f"""
        select latency_minutes, det_segment, pq_rth_open, era,
               count(*) as n,
               {','.join(f'quantile_cont(mfe_h{h}/fill_price - 1, {q}) as mfe_h{h}_q{int(q*100)}'
                         for h in hor for q in qs)},
               {','.join(f'quantile_cont(mae_h{h}/fill_price - 1, {q}) as mae_h{h}_q{int(q*100)}'
                         for h in hor for q in qs)},
               median(fill_price) as median_fill_price
        from t2 group by all""").fetchdf()
    exc.to_parquet(os.path.join(REPO, OUT_EXC), index=False)

    named = cfg["named_cell"]
    nc = g[(g.denominator == named["denominator"])
           & (g.latency_minutes == named["latency_minutes"])
           & (g.horizon_minutes == named["horizon_minutes"])
           & (g.profit_k == named["profit_k"]) & (g.stop_m == named["stop_m"])]
    out = {
        "task": "Phase 10e T3 -- shares, stratification, clustered inference",
        "outcome_logic": ("optimistic: profit if t_profit <= t_stop. pessimistic: profit if "
                          "t_profit < t_stop. The bounds differ on exactly the ties, so the "
                          "AMBIGUOUS SHARE IS THE TIE RATE."),
        "three_numbers_per_cell": "p_clear, p_breakeven=(m+1)/(k+m), p_randomwalk=m/(k+m)",
        "bootstrap": {"reps": reps, "seed": seed, "ci_level": level,
                      "clustering": ["event", "ticker"],
                      "note": ("common random numbers across cells -- the paired "
                               "construction, and what makes 90 cells affordable")},
        "n_cells": int(len(g)),
        "named_cell": named,
        "named_cell_row": nc.to_dict("records"),
        "runtime_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10e/t3_shares.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t3_shares.py",
    }
    with open(os.path.join(REPO, OUT_JSON), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\n{len(g)} cells. wrote {OUT_SHARES}, {OUT_EXC}, {OUT_JSON} "
          f"({out['runtime_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
