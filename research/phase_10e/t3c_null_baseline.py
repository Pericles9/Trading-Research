#!/usr/bin/env python
"""
Phase 10e T3c — the expiry-matched driftless baseline, and the RTH-fill robustness cut.

WHY THE BASELINE EXISTS. `p_randomwalk = m/(k+m)` is the touch probability for a driftless
walk run UNTIL a barrier is hit. This phase imposes an expiry, and expiry censors the FAR
barrier more than the near one — at k=3/m=2 the profit barrier sits 1.5x further out, so it
is reached later and censored more. The comparator is therefore biased AGAINST detecting
drift by a known amount in a known direction, and the "drift exists / does not" sentence
cannot rest on it.

WHAT IS SIMULATED. A driftless geometric random walk with

  * the SAME barrier distances (k and m multiples of the round trip),
  * the SAME expiry (the cell's horizon H),
  * the SAME minute-bar discretisation — the path is stepped at 10 s and reduced to a
    per-minute high and low, so first passage is judged on bars exactly as it is on real
    tape,
  * per-minute volatility drawn from the OBSERVED tape, via the Parkinson estimator
    sigma = ln(high/low) / (2*sqrt(ln 2)) on the phase's own entry bars.

Because the same bar reduction is applied, the simulation also yields an expiry-matched
AMBIGUITY baseline for free: ties (both barriers first touched in the same simulated bar)
arise from the same mechanism as R1's.

NO DATA PASS BEYOND READING THE VOLATILITY DISTRIBUTION, no gate is touched, and no
threshold moves. This corrects a comparator; it does not re-open a criterion.

SECOND OUTPUT — THE RTH-FILL RESTRICTED CUT. The named cell is labelled by DETECTION segment,
so RTH-detected entries can fill in the post session, where the tape is thinner. The headline
therefore averages two tapes. `p_clear` is recomputed restricted to entries whose FILL BAR
sits in RTH, as a robustness line.

Usage: .venv/Scripts/python.exe research/phase_10e/t3c_null_baseline.py
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
A = os.path.join(REPO, "results/phase_10e/artifacts")
OUT = "results/phase_10e/artifacts/t3c_null_baseline.json"
KTAG = {1.5: "k15", 2: "k2", 3: "k3"}

N_PATHS = 400_000
STEPS_PER_MIN = 6            # 10 s steps
SEED = 42


def simulate(sigmas, ks, ms, hors, rt, rng):
    """Driftless walk, minute-bar reduced. Returns p_profit_first per (k, m, H, bound)."""
    hmax = max(hors)
    n = sigmas.size
    dt = 1.0 / STEPS_PER_MIN
    # log-price increments; sigma is PER MINUTE, so per step scale by sqrt(dt)
    inc = rng.standard_normal((n, hmax * STEPS_PER_MIN)).astype(np.float32)
    inc *= (sigmas[:, None] * np.sqrt(dt)).astype(np.float32)
    path = np.cumsum(inc, axis=1)
    del inc
    # reduce to per-minute high/low, including the running path from the fill (log 0)
    path = path.reshape(n, hmax, STEPS_PER_MIN)
    bar_hi = path.max(axis=2)
    bar_lo = path.min(axis=2)
    del path
    # bar 0 also contains the fill itself at log-price 0
    bar_hi[:, 0] = np.maximum(bar_hi[:, 0], 0.0)
    bar_lo[:, 0] = np.minimum(bar_lo[:, 0], 0.0)
    run_hi = np.maximum.accumulate(bar_hi, axis=1)
    run_lo = np.minimum.accumulate(bar_lo, axis=1)
    del bar_hi, bar_lo

    BIG = hmax + 10
    out = {}
    tp = {k: np.argmax(run_hi >= np.log1p(k * rt), axis=1) for k in ks}
    tp_hit = {k: (run_hi[:, -1] >= np.log1p(k * rt)) for k in ks}
    ts = {m: np.argmax(run_lo <= np.log1p(-m * rt), axis=1) for m in ms}
    ts_hit = {m: (run_lo[:, -1] <= np.log1p(-m * rt)) for m in ms}
    for k in ks:
        for m in ms:
            a = np.where(tp_hit[k], tp[k], BIG)
            b = np.where(ts_hit[m], ts[m], BIG)
            for H in hors:
                ah = np.where(a <= H - 1, a, BIG)      # minute index 0..H-1 inside horizon
                bh = np.where(b <= H - 1, b, BIG)
                p_in, s_in = ah < BIG, bh < BIG
                opt = p_in & (~s_in | (ah <= bh))
                pess = p_in & (~s_in | (ah < bh))
                amb = p_in & s_in & (ah == bh)
                out[(k, m, H)] = {
                    "p_profit_first_optimistic": float(opt.mean()),
                    "p_profit_first_pessimistic": float(pess.mean()),
                    "expiry_share": float((~p_in & ~s_in).mean()),
                    "ambiguous_share": float(amb.mean()),
                }
    return out


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    nc = cfg["named_cell"]
    ks, ms = cfg["barrier_grid"]["profit_k"], cfg["barrier_grid"]["stop_m"]
    hors = cfg["arm1"]["horizons_minutes"]
    rt = cfg["cost"]["round_trip_bp"] / 10000.0
    L = nc["latency_minutes"]
    t0 = time.perf_counter()

    c = duckdb.connect(); c.execute("PRAGMA threads=4"); c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"ATTACH '{os.path.join(REPO,'data/duckdb/main.duckdb')}' AS m (READ_ONLY)")
    c.execute(f"create view ent as select * from "
              f"read_parquet('{os.path.join(A,'t1_candidate_entries.parquet')}')")
    c.execute(f"create view t2 as select * from "
              f"read_parquet('{os.path.join(A,'t2_excursion.parquet')}')")
    c.execute("""create view bars as select ticker, event_date_canonical, momentum_pct,
                 minute_index, segment, high, low from m.event_minute_bars_v2
                 where session_offset = 0""")

    # ---- observed per-minute Parkinson sigma, on the phase's own entry bars ----
    sig = c.execute(f"""
        select ln(high / low) / (2 * sqrt(ln(2))) as s
        from ent where det_segment = '{nc['det_segment']}' and high > 0 and low > 0
          and high > low
        using sample 400000 rows (reservoir, {SEED})""").fetchdf()["s"].to_numpy(np.float64)
    sig = sig[np.isfinite(sig) & (sig > 0)]
    print(f"observed per-minute Parkinson sigma, {nc['det_segment']} entries (n={sig.size:,}):")
    for q in (0.05, 0.25, 0.5, 0.75, 0.95):
        print(f"   q{int(q*100):02d} {np.quantile(sig, q):.6f}  "
              f"({np.quantile(sig, q)*10000:.1f} bp/min)")

    rng = np.random.default_rng(SEED)
    draw = rng.choice(sig, size=N_PATHS, replace=True).astype(np.float32)

    # ---- CALIBRATE BY MATCHING THE OBSERVED EXPIRY SHARE, PER CELL ------------
    # A first pass at the RAW Parkinson sigma produced a null that EXPIRED TWICE AS OFTEN
    # as the tape -- 23.7% against 11.3% on the named cell. That null is too quiet, which
    # depresses its p_profit_first and therefore OVERSTATES the drift it exists to measure.
    # The cause is known: Parkinson from a sparse minute bar is downward-biased, because
    # with few prints the observed high-low range understates the true one.
    #
    # So the null is matched on the thing that actually matters for this comparison -- the
    # CENSORING. Sweep a volatility scale, then per cell interpolate to the scale that
    # reproduces that cell's own observed expiry share. The censoring is then matched by
    # construction rather than assumed, and the sigma-calibration error is removed for
    # this purpose.
    scales = [0.6, 0.8, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0]
    print(f"\nsweeping {len(scales)} volatility scales x {N_PATHS:,} paths ...", flush=True)
    key_nc = (nc["profit_k"], nc["stop_m"], nc["horizon_minutes"])
    sweep = {}
    for sc in scales:
        sweep[sc] = simulate(draw * sc, ks, ms, hors, rt,
                             np.random.default_rng(SEED + int(sc * 100)))
        print(f"   scale {sc:>4}: named-cell null expiry "
              f"{sweep[sc][key_nc]['expiry_share']:.4f}", flush=True)

    g0 = pd.read_parquet(os.path.join(A, "t3_shares.parquet"))
    pw0 = g0[(g0.denominator == "print_weighted") & (g0.latency_minutes == L)]
    obs_exp = {(r.profit_k, r.stop_m, r.horizon_minutes): float(r.expiry_share)
               for _, r in pw0.iterrows()}

    null, matched_scale = {}, {}
    for key, target in obs_exp.items():
        xs = np.array([sweep[sc][key]["expiry_share"] for sc in scales])
        o = np.argsort(xs)
        sc_star = float(np.interp(target, xs[o], np.array(scales)[o]))
        matched_scale[key] = sc_star
        lo = max([s2 for s2 in scales if s2 <= sc_star], default=scales[0])
        hi = min([s2 for s2 in scales if s2 >= sc_star], default=scales[-1])
        w = 0.0 if hi == lo else (sc_star - lo) / (hi - lo)
        null[key] = {kk: (1 - w) * sweep[lo][key][kk] + w * sweep[hi][key][kk]
                     for kk in sweep[lo][key]}
    print(f"  matched ({time.perf_counter()-t0:.0f}s)")

    # ---- compare against the observed grid ----------------------------------
    g = pd.read_parquet(os.path.join(A, "t3_shares.parquet"))
    pw = g[(g.denominator == "print_weighted") & (g.latency_minutes == L)].copy()
    rows = []
    for _, r in pw.iterrows():
        nb = null[(r.profit_k, r.stop_m, r.horizon_minutes)]
        rows.append({
            "latency_minutes": int(r.latency_minutes),
            "horizon_minutes": int(r.horizon_minutes),
            "profit_k": float(r.profit_k), "stop_m": float(r.stop_m),
            "observed_p_clear_optimistic": float(r.p_clear_optimistic),
            "observed_p_clear_pessimistic": float(r.p_clear_pessimistic),
            "p_randomwalk_naive": float(r.p_randomwalk),
            "p_randomwalk_expiry_matched": nb["p_profit_first_optimistic"],
            "null_p_pessimistic": nb["p_profit_first_pessimistic"],
            "observed_expiry_share": float(r.expiry_share),
            "null_expiry_share": nb["expiry_share"],
            "observed_ambiguous_share": float(r.ambiguous_share),
            "null_ambiguous_share": nb["ambiguous_share"],
            "p_breakeven": float(r.p_breakeven),
            "drift_vs_naive": bool(r.p_clear_optimistic > r.p_randomwalk),
            "drift_vs_expiry_matched": bool(
                r.p_clear_optimistic > nb["p_profit_first_optimistic"]),
        })
    comp = pd.DataFrame(rows).sort_values(["horizon_minutes", "profit_k", "stop_m"])

    # ---- RTH-fill restricted robustness cut ---------------------------------
    k, mm, H = nc["profit_k"], nc["stop_m"], nc["horizon_minutes"]
    tp, ts = f"tp_{KTAG[k]}", f"ts_m{mm}"
    cut = c.execute(f"""
        select f.segment as fill_segment, count(*) as n,
               sum(case when p_in and (not s_in or {tp} <= {ts}) then 1 else 0 end)*1.0/count(*) as p_opt,
               sum(case when p_in and (not s_in or {tp} <  {ts}) then 1 else 0 end)*1.0/count(*) as p_pess,
               count(distinct (t.ticker||t.event_date_canonical||cast(t.momentum_pct as varchar))) as events
        from (select *, ({tp} is not null and {tp} <= fill_minute + {H}) as p_in,
                     ({ts} is not null and {ts} <= fill_minute + {H}) as s_in
              from t2 where latency_minutes = {L} and det_segment = '{nc['det_segment']}') t
        join bars f on t.ticker = f.ticker and t.event_date_canonical = f.event_date_canonical
                   and t.momentum_pct = f.momentum_pct and f.minute_index = t.fill_minute
        group by 1 order by 1""").fetchdf()

    named = null[(k, mm, H)]
    obs = pw[(pw.horizon_minutes == H) & (pw.profit_k == k) & (pw.stop_m == mm)].iloc[0]
    out = {
        "task": "Phase 10e T3c -- expiry-matched driftless baseline, and the RTH-fill cut",
        "why": ("p_randomwalk = m/(k+m) assumes run-to-barrier. With an expiry, the FAR "
                "barrier is censored more, so the comparator is biased against detecting "
                "drift by a known amount in a known direction."),
        "simulation": {
            "n_paths": N_PATHS, "steps_per_minute": STEPS_PER_MIN, "seed": SEED,
            "sigma_source": ("Parkinson ln(high/low)/(2*sqrt(ln2)) on this phase's own entry "
                             f"bars, {nc['det_segment']}, reservoir sample"),
            "sigma_quantiles_bp_per_min": {f"q{int(q*100):02d}":
                                           float(np.quantile(sig, q) * 10000)
                                           for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
            "matched_on": ["barrier distances", "expiry horizon",
                           "minute-bar discretisation",
                           "THE OBSERVED EXPIRY SHARE, per cell"],
            "calibration_correction": (
                "A first pass at the raw Parkinson sigma gave a null that expired 23.7% of "
                "the time against the tape's 11.3% -- too quiet, which depresses the null's "
                "p_profit_first and OVERSTATES drift. Parkinson from a sparse minute bar is "
                "downward-biased: with few prints the observed high-low range understates "
                "the true one. The null is therefore calibrated by SWEEPING a volatility "
                "scale and interpolating, per cell, to the scale that reproduces that "
                "cell's own observed expiry share. The censoring is matched by "
                "construction rather than assumed."),
            "matched_scale_per_cell": {str(k2): round(v, 3)
                                       for k2, v in matched_scale.items()},
            "note": ("the same bar reduction yields an expiry-matched AMBIGUITY baseline "
                     "for free")},
        "named_cell": {
            "observed_optimistic": float(obs.p_clear_optimistic),
            "observed_pessimistic": float(obs.p_clear_pessimistic),
            "p_randomwalk_naive": float(obs.p_randomwalk),
            "p_randomwalk_expiry_matched": named["p_profit_first_optimistic"],
            "p_breakeven": float(obs.p_breakeven),
            "observed_expiry_share": float(obs.expiry_share),
            "null_expiry_share": named["expiry_share"],
            "observed_ambiguous_share": float(obs.ambiguous_share),
            "null_ambiguous_share": named["ambiguous_share"],
            "drift_vs_naive": bool(obs.p_clear_optimistic > obs.p_randomwalk),
            "drift_vs_expiry_matched": bool(
                obs.p_clear_optimistic > named["p_profit_first_optimistic"])},
        "grid": comp.to_dict("records"),
        "n_cells_drift_vs_naive": int(comp.drift_vs_naive.sum()),
        "n_cells_drift_vs_expiry_matched": int(comp.drift_vs_expiry_matched.sum()),
        "n_cells": int(len(comp)),
        "rth_fill_restricted_cut": {
            "why": ("the named cell is labelled by DETECTION segment, so RTH-detected "
                    "entries can fill in post where the tape is thinner; the headline "
                    "averages two tapes"),
            "by_fill_segment": cut.to_dict("records"),
            "gate_unchanged": ("this is a robustness line. It does not move p_breakeven and "
                               "does not re-read row 12, which fired on all 90 cells.")},
        "runtime_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10e/t3c_null_baseline.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t3c_null_baseline.py",
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    n = out["named_cell"]
    print(f"\nNAMED CELL  k={k} m={mm} H={H} L={L}")
    print(f"  observed optimistic          {n['observed_optimistic']:.4f}")
    print(f"  p_randomwalk NAIVE           {n['p_randomwalk_naive']:.4f}")
    print(f"  p_randomwalk EXPIRY-MATCHED  {n['p_randomwalk_expiry_matched']:.4f}")
    print(f"  p_breakeven                  {n['p_breakeven']:.4f}")
    print(f"  expiry share obs {n['observed_expiry_share']:.4f} vs null "
          f"{n['null_expiry_share']:.4f}")
    print(f"  ambiguity    obs {n['observed_ambiguous_share']:.4f} vs null "
          f"{n['null_ambiguous_share']:.4f}")
    print(f"  DRIFT? vs naive {n['drift_vs_naive']}   "
          f"vs expiry-matched {n['drift_vs_expiry_matched']}")
    print(f"\ncells showing drift: {out['n_cells_drift_vs_naive']} vs naive, "
          f"{out['n_cells_drift_vs_expiry_matched']} vs expiry-matched, of {out['n_cells']}")
    print("\nRTH-FILL RESTRICTED CUT (named cell):")
    for r in cut.itertuples(index=False):
        print(f"   fill in {str(r.fill_segment):10s} p_opt {r.p_opt:.4f}  "
              f"p_pess {r.p_pess:.4f}  n {r.n:>9,}  events {r.events:>6,}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
