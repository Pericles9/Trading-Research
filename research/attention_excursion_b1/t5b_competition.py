"""
Brief 1, T5b -- the competition check, built and run on the dates of the 50 dev events only. A
mechanism check: it touches no outcome of the crossing name j.

For each D1 crossing j on those dates and each name i already live at tau_j (tau_i < tau_j <= tau_i + L),
compare i's collapsed trade count in [tau_j, tau_j + W) against [tau_j - W, tau_j), for W in {5, 15, 60}
min, read side by side. Zero-count windows give no log ratio and are carried as a class with n.

Matched control (Amendment 3 A3.5, replacing run 3's uniform draw over the live span): moments t in
i's own live span that fall in the same octave of time since i's own crossing as tau_j
(floor(log2((t - tau_i) / 1 s)) == floor(log2((tau_j - tau_i) / 1 s))), in the same clock segment as
tau_j (the cross minutes are segments of their own), with no D1 crossing other than i's own within
+/- W and [t - W, t + W] inside 04:00-20:00. Drawn uniformly on a 1-second grid with the config seed.
A pair with no such moment is `no_match` -- never filled from outside its bin.

`window_crosses_segment` (both arms) marks a window [t - W, t + W) whose ends lie in different clock
segments -- a descriptor, not a filter.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t5b_competition.py
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

NS = 10**9


def ratio(ct: np.ndarray, t: int, W: int):
    a = int(np.searchsorted(ct, t - W, "left"))
    m = int(np.searchsorted(ct, t, "left"))
    b = int(np.searchsorted(ct, t + W, "left"))
    nb, na = m - a, b - m
    return na, nb, (np.log(na / nb) if na > 0 and nb > 0 else np.nan)


def main() -> int:
    cfg = C.load_cfg()
    c5 = cfg["t5b_competition"]
    tol = cfg["t5_attention"]["collapse_tol_ms"]
    Ws = [w * 60 * NS for w in c5["windows_min"]]
    livs = [(15, 15 * 60 * NS), (60, 60 * 60 * NS), ("rest_of_session", None)]
    k_ctl = c5["controls_per_pair"]
    rng = np.random.default_rng(c5["seed"])

    t2 = pd.read_parquet(C.art("t2_tau.parquet"))
    sl = pd.read_parquet(C.REPO / C.OUT / "slices.parquet", columns=["event_id", "dev_group"])
    dates = sorted(set(t2.merge(sl, on="event_id").query("dev_group == 'dev_v3'")["event_date_canonical"]))
    rows = []
    for date in dates:
        names = t2[(t2["event_date_canonical"] == date) & t2["tau_available"]].copy()
        names["tau"] = names["tau_ns"].astype("int64")
        t0400, t2000 = C.et_ns(date, "04:00:00"), C.et_ns(date, "20:00:00")
        op, cl = C.rth_bounds_ns(date)
        bounds = np.array([op, op + C.MIN_NS, cl, cl + C.MIN_NS], dtype=np.int64)

        def seg_code(t):                                  # index into C.SEGMENTS
            return np.searchsorted(bounds, t, "right")

        cts = {}
        for e in names["event_id"]:
            tr = C.read_trades(e, with_conditions=False)
            a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
            cts[e] = C.collapse_tol(tr["ts"][a:b], tol)
        taus = names.set_index("event_id")["tau"]
        all_tau = np.sort(taus.to_numpy())
        for j, tj in taus.items():
            sj = int(seg_code(tj))
            for lname, L in livs:
                live = taus[(taus < tj) & ((tj <= taus + L) if L is not None else True)]
                for i, ti in live.items():
                    span_end = t2000 if L is None else min(ti + L, t2000)
                    octave = math.floor(math.log2((tj - ti) / NS))
                    b_lo, b_hi = ti + int(round(2.0 ** octave * NS)), ti + int(round(2.0 ** (octave + 1) * NS))
                    key = {"date": date, "j": j, "i": i, "liveness": str(lname), "segment": C.SEGMENTS[sj],
                           "octave": octave, "sec_since_own_tau": (tj - ti) / NS}
                    for W, wmin in zip(Ws, c5["windows_min"]):
                        if L is not None and W >= L:
                            continue            # A2.5: structurally undefined (W >= L) -- not run
                        if tj - W < t0400 or tj + W > t2000:
                            rows.append({**key, "W_min": wmin, "arm": "crossing", "status": "window_outside_session"})
                            continue
                        na, nb, lr = ratio(cts[i], tj, W)
                        rows.append({**key, "W_min": wmin, "arm": "crossing", "t": tj, "n_after": na, "n_before": nb,
                                     "log_ratio": lr, "status": "ok" if np.isfinite(lr) else "zero_count",
                                     "window_crosses_segment": bool(seg_code(tj - W) != seg_code(tj + W - 1))})
                        # A3.5 matched control: same octave since i's own crossing, same segment, no crossing within +/- W
                        lo_t, hi_t = max(b_lo, t0400 + W), min(b_hi, span_end, t2000 - W)
                        if hi_t <= lo_t:
                            rows.append({**key, "W_min": wmin, "arm": "control", "status": "no_match",
                                         "no_match_reason": "octave_bin_outside_live_span", "n_eligible": 0})
                            continue
                        grid = np.arange(lo_t, hi_t, NS, dtype=np.int64)
                        grid = grid[seg_code(grid) == sj]
                        if grid.size == 0:
                            rows.append({**key, "W_min": wmin, "arm": "control", "status": "no_match",
                                         "no_match_reason": "no_moment_in_segment", "n_eligible": 0})
                            continue
                        others = all_tau[all_tau != ti]
                        pos = np.searchsorted(others, grid - W, "left")
                        pos2 = np.searchsorted(others, grid + W, "right")
                        elig = grid[pos2 == pos]
                        if elig.size == 0:
                            rows.append({**key, "W_min": wmin, "arm": "control", "status": "no_match",
                                         "no_match_reason": "every_moment_within_W_of_a_crossing", "n_eligible": 0})
                            continue
                        for t in rng.choice(elig, size=k_ctl, replace=elig.size < k_ctl):
                            t = int(t)
                            na, nb, lr = ratio(cts[i], t, W)
                            rows.append({**key, "W_min": wmin, "arm": "control", "t": t, "n_after": na, "n_before": nb,
                                         "log_ratio": lr, "status": "ok" if np.isfinite(lr) else "zero_count",
                                         "n_eligible": int(elig.size),
                                         "window_crosses_segment": bool(seg_code(t - W) != seg_code(t + W - 1))})
    out = pd.DataFrame(rows)
    out["config_hash"] = C.cfg_hash()
    out.to_parquet(C.art("t5b_competition.parquet"), index=False)
    ok = out[out["status"] == "ok"]
    summ = {}
    for (L, W), g in out.groupby(["liveness", "W_min"]):
        s = {}
        pairs_cross = g[g["arm"] == "crossing"][["j", "i"]].drop_duplicates()
        gc = g[g["arm"] == "control"]
        matched = gc[gc["status"] != "no_match"][["j", "i"]].drop_duplicates()
        s["matching"] = {"pairs": int(len(pairs_cross)),
                         "pairs_with_matched_control": int(len(matched)),
                         "pairs_no_match": int(gc[gc["status"] == "no_match"][["j", "i"]].drop_duplicates().shape[0]),
                         "no_match_reason": gc["no_match_reason"].value_counts().to_dict() if "no_match_reason" in gc else {},
                         "matched_moments_drawn": int((gc["status"] != "no_match").sum()),
                         "n_eligible_median": float(gc.loc[gc["status"] != "no_match", "n_eligible"].median())
                         if (gc["status"] != "no_match").any() else None}
        for arm, ga in g.groupby("arm"):
            v = ga.loc[ga["status"] == "ok", "log_ratio"]
            s[arm] = {"n_ok": int(v.size), "status": ga["status"].value_counts().to_dict(),
                      "median": float(v.median()) if v.size else None,
                      "p25": float(v.quantile(.25)) if v.size else None, "p75": float(v.quantile(.75)) if v.size else None,
                      "n_pairs": int(ga[["j", "i"]].drop_duplicates().shape[0]),
                      "window_crosses_segment": int(ga["window_crosses_segment"].fillna(False).astype(bool).sum())}
        # the crossing arm restricted to pairs that have a matched control -- the like-for-like comparison
        cm = g[(g["arm"] == "crossing") & (g["status"] == "ok")].merge(matched, on=["j", "i"])
        s["crossing_matched_pairs"] = {"n_ok": int(len(cm)), "median": float(cm["log_ratio"].median()) if len(cm) else None,
                                       "p25": float(cm["log_ratio"].quantile(.25)) if len(cm) else None,
                                       "p75": float(cm["log_ratio"].quantile(.75)) if len(cm) else None}
        summ[f"L={L}|W={W}"] = s
    undefined = {str(ln): [w for w in c5["windows_min"] if Ln is not None and w * 60 * NS >= Ln] for ln, Ln in livs}
    C.write_json(f"{C.ART}/t5b_summary.json", {"config_hash": C.cfg_hash(), "dates": len(dates), "cells": summ,
                                               "control_rule": cfg["amendment_3"]["t5b_matched_control"]["rule"],
                                               "structurally_undefined_cells": undefined,
                                               "undefined_rule": "W >= L: every moment of the live span is within W of the crossing, so no control moment exists (A2.5); not run",
                                               "crossings_with_any_live_name": int(ok[ok["arm"] == "crossing"]["j"].nunique())})
    for k, v in summ.items():
        print(k, v["matching"]["pairs"], "pairs;", v["matching"]["pairs_with_matched_control"], "matched;",
              {a: (v[a]["n_ok"], round(v[a]["median"], 3) if v[a]["median"] is not None else None) for a in ("crossing", "control") if a in v},
              "crossing|matched", v["crossing_matched_pairs"]["n_ok"],
              round(v["crossing_matched_pairs"]["median"], 3) if v["crossing_matched_pairs"]["median"] is not None else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
