"""
Brief 1, T5b -- the competition check, built and run on the dates of the 50 dev events only. A
mechanism check: it touches no outcome of the crossing name j.

For each D1 crossing j on those dates and each name i already live at tau_j (tau_i < tau_j <= tau_i + L),
compare i's collapsed trade count in [tau_j, tau_j + W) against [tau_j - W, tau_j), for W in {5, 15, 60}
min, read side by side. Matched control: moments t in i's own live span with no other D1 crossing within
+/- W, drawn uniformly on a 1-second grid with the config seed, same ratio. Zero-count windows give no
log ratio and are carried as a class with n.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t5b_competition.py
"""
from __future__ import annotations

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
        cts = {}
        for e in names["event_id"]:
            tr = C.read_trades(e, with_conditions=False)
            a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
            cts[e] = C.collapse_tol(tr["ts"][a:b], tol)
        taus = names.set_index("event_id")["tau"]
        all_tau = np.sort(taus.to_numpy())
        for j, tj in taus.items():
            for lname, L in livs:
                live = taus[(taus < tj) & ((tj <= taus + L) if L is not None else True)]
                for i, ti in live.items():
                    span_end = t2000 if L is None else min(ti + L, t2000)
                    for W, wmin in zip(Ws, c5["windows_min"]):
                        if L is not None and W >= L:
                            continue            # A2.5: structurally undefined (W >= L) -- not run
                        if tj - W < t0400 or tj + W > t2000:
                            rows.append({"date": date, "j": j, "i": i, "liveness": str(lname), "W_min": wmin, "arm": "crossing",
                                         "status": "window_outside_session"})
                            continue
                        na, nb, lr = ratio(cts[i], tj, W)
                        rows.append({"date": date, "j": j, "i": i, "liveness": str(lname), "W_min": wmin, "arm": "crossing",
                                     "t": tj, "n_after": na, "n_before": nb, "log_ratio": lr,
                                     "status": "ok" if np.isfinite(lr) else "zero_count"})
                        # matched controls for the same i
                        lo_t, hi_t = max(ti, t0400 + W), min(span_end, t2000 - W)
                        if hi_t <= lo_t:
                            rows.append({"date": date, "j": j, "i": i, "liveness": str(lname), "W_min": wmin, "arm": "control",
                                         "status": "no_eligible_moment"})
                            continue
                        grid = np.arange(lo_t, hi_t, NS, dtype=np.int64)
                        others = all_tau[all_tau != ti]
                        pos = np.searchsorted(others, grid - W, "left")
                        pos2 = np.searchsorted(others, grid + W, "right")
                        elig = grid[pos2 == pos]
                        if elig.size == 0:
                            rows.append({"date": date, "j": j, "i": i, "liveness": str(lname), "W_min": wmin, "arm": "control",
                                         "status": "no_eligible_moment"})
                            continue
                        for t in rng.choice(elig, size=k_ctl, replace=elig.size < k_ctl):
                            na, nb, lr = ratio(cts[i], int(t), W)
                            rows.append({"date": date, "j": j, "i": i, "liveness": str(lname), "W_min": wmin, "arm": "control",
                                         "t": int(t), "n_after": na, "n_before": nb, "log_ratio": lr,
                                         "status": "ok" if np.isfinite(lr) else "zero_count"})
    out = pd.DataFrame(rows)
    out["config_hash"] = C.cfg_hash()
    out.to_parquet(C.art("t5b_competition.parquet"), index=False)
    ok = out[out["status"] == "ok"]
    summ = {}
    for (L, W), g in out.groupby(["liveness", "W_min"]):
        s = {}
        for arm, ga in g.groupby("arm"):
            v = ga.loc[ga["status"] == "ok", "log_ratio"]
            s[arm] = {"n_ok": int(v.size), "status": ga["status"].value_counts().to_dict(),
                      "median": float(v.median()) if v.size else None,
                      "p25": float(v.quantile(.25)) if v.size else None, "p75": float(v.quantile(.75)) if v.size else None,
                      "n_pairs": int(ga[["j", "i"]].drop_duplicates().shape[0])}
        summ[f"L={L}|W={W}"] = s
    undefined = {str(ln): [w for w in c5["windows_min"] if Ln is not None and w * 60 * NS >= Ln] for ln, Ln in livs}
    C.write_json(f"{C.ART}/t5b_summary.json", {"config_hash": C.cfg_hash(), "dates": len(dates), "cells": summ,
                                               "structurally_undefined_cells": undefined,
                                               "undefined_rule": "W >= L: every moment of the live span is within W of the crossing, so no control moment exists (A2.5); not run",
                                               "crossings_with_any_live_name": int(ok[ok["arm"] == "crossing"]["j"].nunique())})
    print(len(dates), "dates;", {k: {a: (v[a]["n_ok"], round(v[a]["median"], 3) if v[a]["median"] is not None else None)
                                     for a in v} for k, v in summ.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
