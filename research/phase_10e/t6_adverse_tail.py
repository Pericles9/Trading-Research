#!/usr/bin/env python
"""
Post-10e — the adverse tail, read from the short side.

WHY THIS EXISTS, AND WHY IT COMES BEFORE ANY NUMBER IS REPEATED. Re-reading the committed
artifacts with the sign reversed makes the median look strong: the median event fades from
its detection anchor at every horizon. **The median is the wrong statistic for a short.** A
short on a momentum spike has bounded gain and unbounded loss, so "the median event fades
3.5% by the close" says nothing about the events that double again — and those decide
whether the position survives. Nobody has read that tail.

TWO TAILS, AND THE SECOND IS THE ONE THAT ACTUALLY STOPS YOU OUT.

  TERMINAL TAIL  — Phase 8's markout grid, sign-flipped. A long's markout `m` is a short's
                   loss of `+m`, so the short's adverse tail is the RIGHT tail of markout.
                   p90 / p95 / p99 / worst observed, per (latency, horizon), with A12
                   carried because t1_close and t3_close span session boundaries.

  PATH TAIL      — Phase 10e's own T2 excursion table. A short is not held to the horizon if
                   it is stopped first, so what matters is the MAXIMUM ADVERSE EXCURSION
                   inside the horizon, which for a short is the long's MFE. Reported as a
                   distribution and as the share exceeding plausible stop levels in
                   round-trip multiples.

**The path tail is the binding one.** A position that ends the day down can still have been
closed out at a loss hours earlier.

NEUTRALITY. This reports distributions. It does not characterise them, does not compare the
short to the long, and does not repeat the median-based capture figures the read that
prompted it flagged as not-yet-a-result.

D19: bp and cents together. D4: markout and excursion are tick- and bar-derived.

Usage: .venv/Scripts/python.exe research/phase_10e/t6_adverse_tail.py
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
OUT = "results/phase_10e/artifacts/t6_adverse_tail.json"
ORDER = ["det+5", "det+15", "det+30", "det+60", "t0_close", "t1_close", "t3_close"]


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    rt_bp = cfg["cost"]["round_trip_bp"]; rt = rt_bp / 10000.0
    rt_c = cfg["cost"]["round_trip_cents"]
    stops = [1, 2, 3, 5, 10]                     # round-trip multiples

    # ---------- TERMINAL TAIL: Phase 8 markout, sign-flipped ----------------
    g = pd.read_parquet(os.path.join(
        REPO, "results/phase_8/artifacts/a102_detection_markout_grid.parquet"))
    fl = pd.read_parquet(os.path.join(
        REPO, "results/phase_9/artifacts/t1_cross_session_flags.parquet"))
    fl = fl[fl.session_pair == "tm1_t0"][["ticker", "event_date_canonical", "mp",
                                          "flag_cross_session_extreme"]]
    g = g.merge(fl, on=["ticker", "event_date_canonical", "mp"], how="left")
    g["flag_cross_session_extreme"] = g.flag_cross_session_extreme.fillna(False)
    g = g[g.markout.notna()]

    term = []
    for (lat, hor), s in g.groupby(["latency", "horizon"]):
        for label, sub in (("untrimmed", s),
                           ("a12_flag_removed", s[~s.flag_cross_session_extreme])):
            if not len(sub):
                continue
            adv = sub.markout * 10000            # short's LOSS in bp = long's gain
            row = {"latency_minutes": int(lat), "horizon": hor, "set": label,
                   "n": int(len(sub)),
                   "median_adverse_bp": float(adv.median()),
                   "p75_adverse_bp": float(adv.quantile(.75)),
                   "p90_adverse_bp": float(adv.quantile(.90)),
                   "p95_adverse_bp": float(adv.quantile(.95)),
                   "p99_adverse_bp": float(adv.quantile(.99)),
                   "worst_observed_bp": float(adv.max()),
                   "mean_adverse_bp": float(adv.mean())}
            for k in stops:
                row[f"share_adverse_gt_{k}x_rt"] = float((adv > k * rt_bp).mean())
            term.append(row)
    t = pd.DataFrame(term)
    t["horizon"] = pd.Categorical(t.horizon, ORDER, ordered=True)
    t = t.sort_values(["set", "latency_minutes", "horizon"])

    # worst events by name, untrimmed, at the day horizons
    worst = (g[g.horizon.isin(["t0_close", "t1_close", "t3_close"]) & (g.latency == 5)]
             .nlargest(8, "markout")[["ticker", "event_date_canonical", "mp", "horizon",
                                      "markout", "flag_cross_session_extreme"]])
    worst["adverse_bp"] = worst.markout * 10000

    # ---------- PATH TAIL: Phase 10e T2 MFE, the excursion that stops you out ----
    L = cfg["named_cell"]["latency_minutes"]
    hors = cfg["arm1"]["horizons_minutes"]
    c = duckdb.connect(); c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"create view t2 as select * from read_parquet('{os.path.join(A,'t2_excursion.parquet')}')")
    path = []
    for scope, where in (("all_entries", ""),
                         ("within_14min_of_anchor", "and minutes_since_anchor <= 14")):
        for H in hors:
            e = f"(mfe_h{H} / fill_price - 1) * 10000"
            q = ", ".join(
                [f"quantile_cont({e}, {p}) as q{int(p*100)}" for p in
                 (.5, .75, .9, .95, .99)] +
                [f"max({e}) as worst", f"avg({e}) as mean", "count(*) as n"] +
                [f"avg(case when {e} > {k*rt_bp} then 1.0 else 0.0 end) as s{k}"
                 for k in stops])
            d = c.execute(f"""select {q} from t2
                              where latency_minutes = {L} and det_segment = 'rth' {where}
                              """).fetchdf().iloc[0]
            row = {"scope": scope, "horizon_minutes": H, "n": int(d["n"]),
                   "median_adverse_bp": float(d["q50"]), "p75_adverse_bp": float(d["q75"]),
                   "p90_adverse_bp": float(d["q90"]), "p95_adverse_bp": float(d["q95"]),
                   "p99_adverse_bp": float(d["q99"]),
                   "worst_observed_bp": float(d["worst"]),
                   "mean_adverse_bp": float(d["mean"])}
            for k in stops:
                row[f"share_adverse_gt_{k}x_rt"] = float(d[f"s{k}"])
            path.append(row)
    pt = pd.DataFrame(path)

    out = {
        "task": "Post-10e -- the adverse tail read from the short side",
        "why_before_anything_is_repeated": (
            "the median is the wrong statistic for a position with bounded gain and unbounded "
            "loss; the tail decides whether it survives, and it had not been read"),
        "cost_line": {"round_trip_bp": rt_bp, "round_trip_cents": rt_c},
        "stop_levels_round_trip_multiples": stops,
        "stop_levels_bp": [k * rt_bp for k in stops],
        "sign_convention": ("a long's markout m is a short's loss of +m, so the short's "
                            "adverse tail is the RIGHT tail of markout, and the short's "
                            "adverse EXCURSION is the long's MFE"),
        "terminal_tail_phase8": t.to_dict("records"),
        "worst_named_events_latency5": worst.to_dict("records"),
        "path_tail_phase10e_t2": pt.to_dict("records"),
        "path_tail_note": ("the binding one -- a short is not held to the horizon if it is "
                           "stopped first, so the maximum adverse excursion INSIDE the "
                           "horizon is what closes the position"),
        "a12": "carried on the terminal tail; t1_close and t3_close span session boundaries",
        "not_done_here": ["no comparison to the long side",
                          "no characterisation of the distributions",
                          "no repetition of the median-based capture figures",
                          "locate availability and halt risk are NOT addressed and each can "
                          "close this independently"],
        "source": "research/phase_10e/t6_adverse_tail.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t6_adverse_tail.py",
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"stop levels: {[f'{k}x = {k*rt_bp:.0f} bp' for k in stops]}\n")
    print("TERMINAL TAIL -- Phase 8 markout, sign-flipped (adverse = short's loss), latency 5, untrimmed")
    print(f"{'horizon':>10} {'med':>8} {'p90':>9} {'p95':>9} {'p99':>10} {'worst':>11} "
          f"{'>2x':>7} {'>5x':>7} {'>10x':>7}")
    for r in t[(t.set == "untrimmed") & (t.latency_minutes == 5)].itertuples(index=False):
        print(f"{str(r.horizon):>10} {r.median_adverse_bp:>8.0f} {r.p90_adverse_bp:>9.0f} "
              f"{r.p95_adverse_bp:>9.0f} {r.p99_adverse_bp:>10.0f} "
              f"{r.worst_observed_bp:>11,.0f} {r.share_adverse_gt_2x_rt:>7.3f} "
              f"{r.share_adverse_gt_5x_rt:>7.3f} {r.share_adverse_gt_10x_rt:>7.3f}")
    print("\nPATH TAIL -- max adverse excursion INSIDE the horizon (Phase 10e T2), rth, latency 5")
    for scope in ("all_entries", "within_14min_of_anchor"):
        print(f"  {scope}")
        print(f"{'H':>6} {'med':>8} {'p90':>9} {'p95':>9} {'p99':>10} {'worst':>11} "
              f"{'>2x':>7} {'>5x':>7} {'>10x':>7}")
        for r in pt[pt.scope == scope].itertuples(index=False):
            print(f"{r.horizon_minutes:>6} {r.median_adverse_bp:>8.0f} "
                  f"{r.p90_adverse_bp:>9.0f} {r.p95_adverse_bp:>9.0f} "
                  f"{r.p99_adverse_bp:>10.0f} {r.worst_observed_bp:>11,.0f} "
                  f"{r.share_adverse_gt_2x_rt:>7.3f} {r.share_adverse_gt_5x_rt:>7.3f} "
                  f"{r.share_adverse_gt_10x_rt:>7.3f}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
