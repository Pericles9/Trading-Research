#!/usr/bin/env python
"""
Post-10e — Phase 8 and Phase 9 re-read against the cost stack that did not exist when they ran.

WHY THIS IS NEARLY FREE AND WHY IT MATTERS. Phase 8 measured a markout grid from detection
anchors knowable in real time, and Phase 9 measured retracement at T0..T+3 with clustered
CIs. **Both were measured before Phase 11 produced a round-trip cost of 70.98 bp / 2.512
cents.** Re-reading their committed artifacts against that number is a re-cut, not a
measurement: no tick pass, no new computation, no gate touched.

IT ALSO REPLACES AN EXTRAPOLATION WITH A MEASUREMENT. Arm 1's horizon axis stopped at 60
minutes, and the read after it projected the gap-to-break-even forward on the flattest
observed slope. **Phase 8's grid already carries `t0_close`, `t1_close` and `t3_close`** — so
the horizon axis can be measured past 60 minutes rather than extrapolated, which is a
strictly stronger way to answer the same question.

WHAT IS COMPARED. A long trade held from the detection anchor to a horizon earns its markout
and pays one round trip. So it clears when

    markout > round_trip  (70.98 bp = 0.007098)

reported as a SHARE, defined on every event, per the standing rule that no gate quantity may
have a denominator that can vanish.

A12 APPLIES AND IS CARRIED. `t1_close` and `t3_close` span session boundaries, so per D4
Amendment A12 every statistic is reported with and without `flag_cross_session_extreme`,
untrimmed primary, flagged events as their own row and never dropped.

D19: bp and cents together. D4: markout is tick-derived from Phase 8; `mp` is a key only.

Usage: .venv/Scripts/python.exe research/phase_10e/t5_costed_markouts.py
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = os.path.join(REPO, "config", "phase_10e.json")
OUT = "results/phase_10e/artifacts/t5_costed_markouts.json"

ORDER = ["det+5", "det+15", "det+30", "det+60", "t0_close", "t1_close", "t3_close"]
APPROX_MIN = {"det+5": 5, "det+15": 15, "det+30": 30, "det+60": 60,
              "t0_close": 195, "t1_close": 585, "t3_close": 1365}


def boot_share(df, value_col, thresh, reps, seed, level):
    """Event-clustered bootstrap on share(value > thresh). One event = one cluster."""
    ev = df["event_key"].to_numpy()
    uniq, inv = np.unique(ev, return_inverse=True)
    hit = (df[value_col].to_numpy() > thresh).astype(np.float32)
    n_h = np.bincount(inv, weights=hit, minlength=uniq.size)
    n_t = np.bincount(inv, minlength=uniq.size).astype(np.float32)
    rng = np.random.default_rng(seed)
    a = (1 - level) / 2
    out = []
    for _ in range(0, reps, 500):
        k = min(500, reps - len(out))
        idx = rng.integers(0, uniq.size, size=(k, uniq.size))
        W = np.empty((k, uniq.size), np.float32)
        for i in range(k):
            W[i] = np.bincount(idx[i], minlength=uniq.size)
        tot = W @ n_t
        out.append(np.where(tot > 0, (W @ n_h) / tot, np.nan))
    s = np.concatenate(out)
    return float(np.nanquantile(s, a)), float(np.nanquantile(s, 1 - a))


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    rt_bp = cfg["cost"]["round_trip_bp"]; rt = rt_bp / 10000.0
    rt_c = cfg["cost"]["round_trip_cents"]
    reps = cfg["inference"]["bootstrap_reps"]; seed = cfg["inference"]["bootstrap_seed"]
    level = cfg["inference"]["ci_level"]

    g = pd.read_parquet(os.path.join(
        REPO, "results/phase_8/artifacts/a102_detection_markout_grid.parquet"))
    g["event_key"] = (g.ticker + "|" + g.event_date_canonical.astype(str) + "|"
                      + g.mp.astype(str))
    fl = pd.read_parquet(os.path.join(
        REPO, "results/phase_9/artifacts/t1_cross_session_flags.parquet"))
    fl = fl[fl.session_pair == "tm1_t0"][["ticker", "event_date_canonical", "mp",
                                          "flag_cross_session_extreme"]]
    g = g.merge(fl, on=["ticker", "event_date_canonical", "mp"], how="left")
    g["flag_cross_session_extreme"] = g.flag_cross_session_extreme.fillna(False)
    g = g[g.markout.notna()]

    rows = []
    for (lat, hor), s in g.groupby(["latency", "horizon"]):
        for label, sub in (("untrimmed", s),
                           ("a12_flag_removed", s[~s.flag_cross_session_extreme])):
            if not len(sub):
                continue
            share = float((sub.markout > rt).mean())
            lo, hi = (boot_share(sub, "markout", rt, reps, seed, level)
                      if label == "untrimmed" else (np.nan, np.nan))
            rows.append({
                "latency_minutes": int(lat), "horizon": hor,
                "approx_horizon_minutes": APPROX_MIN.get(hor),
                "set": label,
                "n": int(len(sub)), "events": int(sub.event_key.nunique()),
                "share_clearing_round_trip": share,
                "ci_lo": lo, "ci_hi": hi,
                "median_markout_bp": float(sub.markout.median() * 10000),
                "median_gap_to_cost_bp": float(sub.markout.median() * 10000 - rt_bp),
                "mean_markout_bp": float(sub.markout.mean() * 10000),
                "q25_bp": float(sub.markout.quantile(.25) * 10000),
                "q75_bp": float(sub.markout.quantile(.75) * 10000),
            })
    d = pd.DataFrame(rows)
    d["horizon"] = pd.Categorical(d.horizon, ORDER, ordered=True)
    d = d.sort_values(["set", "latency_minutes", "horizon"])

    unt = d[d.set == "untrimmed"]
    best = unt.loc[unt.share_clearing_round_trip.idxmax()]
    n_clear = int((unt.share_clearing_round_trip > 0.5).sum())

    # Phase 9 retracement at the day horizons, attached as path-risk context
    r = pd.read_parquet(os.path.join(REPO, "results/phase_9/artifacts/t3_retracement.parquet"))
    r = r[r.retrace_excursion.notna()]
    ret = (r.groupby(["horizon", "det_segment"], as_index=False)
             .agg(n=("retrace_excursion", "size"),
                  median_retrace=("retrace_excursion", "median"),
                  q75_retrace=("retrace_excursion", lambda x: x.quantile(.75)),
                  q95_retrace=("retrace_excursion", lambda x: x.quantile(.95)),
                  share_flagged=("flag_cs_any", "mean")))

    out = {
        "task": ("Phase 8 markout grid and Phase 9 retracement, re-read against the Phase 11 "
                 "cost stack that did not exist when either was measured"),
        "why_nearly_free": ("a re-cut of committed artifacts -- no tick pass, no new "
                            "measurement, no gate touched"),
        "cost_line": {"round_trip_bp": rt_bp, "round_trip_cents": rt_c,
                      "source": "Phase 11, read from config, not recomputed"},
        "replaces_an_extrapolation": (
            "Arm 1's horizon axis stopped at 60 minutes and the gap-to-break-even was "
            "projected forward on the flattest observed slope. Phase 8's grid already "
            "carries t0_close, t1_close and t3_close, so the axis is MEASURED past 60 "
            "minutes here rather than extrapolated."),
        "comparison": ("a long trade held from the detection anchor to a horizon earns its "
                       "markout and pays one round trip, so it clears when markout > "
                       f"{rt:.6f}. Reported as a SHARE, defined on every event."),
        "a12": ("t1_close and t3_close span session boundaries; every statistic is reported "
                "with and without flag_cross_session_extreme, untrimmed primary, flagged "
                "events never dropped"),
        "grid": d.to_dict("records"),
        "n_cells_where_more_than_half_clear": n_clear,
        "n_cells": int(len(unt)),
        "best_cell": {k: (best[k].item() if hasattr(best[k], "item") else best[k])
                      for k in ("latency_minutes", "horizon", "share_clearing_round_trip",
                                "median_markout_bp", "median_gap_to_cost_bp", "n", "events")},
        "phase_9_retracement_context": ret.to_dict("records"),
        "source": "research/phase_10e/t5_costed_markouts.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t5_costed_markouts.py",
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"cost line: {rt_bp} bp = {rt_c} cents (Phase 11)\n")
    print("SHARE OF EVENTS WHOSE MARKOUT CLEARS ONE ROUND TRIP (untrimmed, primary)\n")
    print(f"{'lat':>4} {'horizon':>10} {'share':>8} {'95% CI':>18} "
          f"{'med bp':>9} {'gap bp':>9} {'events':>8}")
    for r2 in unt.itertuples(index=False):
        ci = f"[{r2.ci_lo:.3f}, {r2.ci_hi:.3f}]" if np.isfinite(r2.ci_lo) else ""
        print(f"{r2.latency_minutes:>4} {str(r2.horizon):>10} "
              f"{r2.share_clearing_round_trip:>8.4f} {ci:>18} "
              f"{r2.median_markout_bp:>9.1f} {r2.median_gap_to_cost_bp:>9.1f} "
              f"{r2.events:>8,}")
    b = out["best_cell"]
    print(f"\nbest cell: latency {b['latency_minutes']}m, {b['horizon']} -- share "
          f"{b['share_clearing_round_trip']:.4f}, median markout "
          f"{b['median_markout_bp']:.1f} bp, gap to cost {b['median_gap_to_cost_bp']:+.1f} bp")
    print(f"cells where MORE THAN HALF of events clear: {n_clear} of {len(unt)}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
