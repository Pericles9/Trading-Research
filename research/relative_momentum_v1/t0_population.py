"""
v1-T0 (Fix 2): the population, with the gap gate ON.

v0's population had gap_gate_enabled = false on every event, so entries ran as low as -23%
intraday and the tested cohort was not the programme's +30% momentum definition. This applies
the runner's own gap gate, reconstructed tick-exactly (common.reconstruct_gap_gate), and takes
the first PASS window that produces an entry under it.

Threshold is applied to move_at against the tick-derived prior close, not to the gate's own
intraday_pct: D4, and v0-T4 measured the two at Spearman 0.314. The gate's own measure is
reported as a variant so the difference is visible rather than asserted.

Score, gates and evaluation all key off the NEW entry instant, not v0's.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/t0_population.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t0_population.json"
OUT_PARQUET = f"{C.ART}/t0_candidates.parquet"


def main() -> int:
    cfg = C.load_cfg()
    thr = cfg["fix2_population_gap_gate_on"]["threshold"]
    W = cfg["score"]["W_seconds"]

    pt = pd.read_parquet(C.REPO / C.PER_TRADE)
    fw = pt[pt["entry_type"] == "first"].copy()
    fw["date"] = fw["date"].astype(str).str.slice(0, 10)
    fw["key"] = fw["ticker"] + "|" + fw["date"]

    pc = pd.read_parquet(C.REPO / C.PRIOR_CLOSE)
    pc["key"] = pc["ticker"] + "|" + pc["event_date_canonical"]
    pcmap = dict(zip(pc.loc[pc["prior_close_available"], "key"],
                     pc.loc[pc["prior_close_available"], "prior_close"]))

    d1 = C.load_d1()
    d1["key"] = d1["ticker"] + "|" + d1["event_date_canonical"]
    d1map = dict(zip(d1["key"], d1["event_id"]))

    rows = []
    t0 = time.time()
    keys = sorted(fw["key"].unique())
    for n, key in enumerate(keys, 1):
        g = fw[fw["key"] == key]
        tk, dt = key.split("|")
        rec = {"key": key, "ticker": tk, "date": dt,
               "n_pass_windows_in_run": int(len(g)),
               "event_id": d1map.get(key), "in_d1": key in d1map,
               "v0_entry_ts": int(g["entry_ts"].min())}
        prior = pcmap.get(key)
        if prior is None or not (prior > 0):
            rows.append({**rec, "ok": False, "reason": "no_prior_close"})
            continue
        folder = C.event_folder(tk, dt)
        if folder is None:
            rows.append({**rec, "ok": False, "reason": "no_folder"})
            continue
        t = C.read_ticks(folder)
        if t is None:
            rows.append({**rec, "ok": False, "reason": "no_trades_parquet"})
            continue
        ts, px, sz = t
        res = C.reconstruct_gap_gate(ts, px, g, float(prior), thr)
        if not res.get("ok"):
            rows.append({**rec, "ok": False, "reason": res["reason"],
                         "prior_close": float(prior),
                         "n_windows_blocked": res.get("n_windows_blocked")})
            continue
        vol = C.window_dollar_volume(ts, px, sz, res["entry_ts"], W)
        rows.append({**rec, "ok": True, "prior_close": float(prior), **res, **vol})
        if n % 250 == 0:
            print(f"  {n}/{len(keys)}  {time.time() - t0:.0f}s", flush=True)

    d = pd.DataFrame(rows)
    d["move_at_entry"] = np.where(
        d["ok"].fillna(False) & (d["prior_close"] > 0),
        (d["entry_price"] - d["prior_close"]) / d["prior_close"], np.nan)
    d["natural_hold_sec"] = (d["natural_exit_ts"] - d["entry_ts"]) / C.NS
    d["gross_pnl_pct"] = np.where(
        d["ok"].fillna(False) & (d["entry_price"] > 0),
        (d["natural_exit_price"] / d["entry_price"] - 1.0) * 100.0, np.nan)

    # the secondary variant: the gate's OWN measure, so the two conditions can be compared
    v0first = fw.sort_values("entry_ts").groupby("key", as_index=False).first()
    d = d.merge(v0first[["key", "intraday_pct_at_entry", "session_bucket"]], on="key", how="left")

    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    ok = d[d["ok"].fillna(False)]
    steps = [
        {"step": "events with at least one PASS window in the original run",
         "n": int(len(d))},
        {"step": "gap gate ON: events with a window that produces an entry",
         "n": int(len(ok)),
         "n_all_windows_blocked": int((d["reason"] == "all_windows_blocked").sum()),
         "n_no_prior_close": int((d["reason"] == "no_prior_close").sum())},
        {"step": "of which in D1", "n": int(ok["in_d1"].sum()),
         "n_outside_D1": int((~ok["in_d1"]).sum())},
    ]

    summary = {
        "task": "v1-T0 population with the gap gate ON (Fix 2)",
        "config_hash": C.cfg_hash(),
        "method": cfg["fix2_population_gap_gate_on"]["method"],
        "threshold": thr,
        "threshold_measure": cfg["fix2_population_gap_gate_on"]["threshold_measure_primary"],
        "coverage_steps": steps,
        "entry_kind": ok["entry_kind"].value_counts().to_dict(),
        "entry_kind_note": "immediate = the window's rising edge already met +30%. queued = the "
                           "gate waited inside the window and entered on the first qualifying "
                           "tick, which is the runner's own documented behaviour, not a hard block.",
        "queued_wait_sec": {f"p{int(q * 100)}": round(float(np.nanquantile(
            ok.loc[ok["entry_kind"] == "queued", "wait_sec"], q)), 1)
            for q in (.25, .5, .75, .95)} if (ok["entry_kind"] == "queued").any() else {},
        "n_windows_blocked_before_entry": {
            f"p{int(q * 100)}": float(np.nanquantile(ok["n_windows_blocked_before"], q))
            for q in (.5, .75, .95, 1.0)},
        "move_at_entry_quantiles": {f"p{int(q * 100)}": round(float(np.nanquantile(
            ok["move_at_entry"], q)), 4) for q in (0, .05, .25, .5, .75, .95, 1.0)},
        "move_at_entry_min_check": {
            "n_below_threshold": int((ok["move_at_entry"] < thr - 1e-9).sum()),
            "note": "the fill is the NEXT tick after the trigger, so a fill can land marginally "
                    "below the trigger level if the next print is lower. That is the runner's "
                    "own convention, reproduced, not a leak.",
        },
        "v0_comparison": {
            "v0_population_n": 1027,
            "v0_entry_intraday_pct_median": 0.1125,
            "v1_move_at_entry_median": round(float(ok["move_at_entry"].median()), 4),
            "n_entry_ts_changed_vs_v0": int((ok["entry_ts"] != ok["v0_entry_ts"]).sum()),
            "share_entry_ts_changed": round(float((ok["entry_ts"] != ok["v0_entry_ts"]).mean()), 4),
        },
        "gate_own_measure_variant": {
            "n_with_gate_intraday_ge_30": int((ok["intraday_pct_at_entry"] >= thr).sum()),
            "note": "the gate's own intraday_pct_at_entry on the v0 first window, for comparison "
                    "only. Spearman against move_at was 0.314 in v0-T4.",
        },
        "natural_hold_sec": {k: round(float(v), 1) for k, v in
                             ok["natural_hold_sec"].describe(
                                 percentiles=[.25, .5, .75]).items()},
        "session_bucket_at_v0_edge": ok["session_bucket"].value_counts().to_dict(),
        "output_parquet": OUT_PARQUET,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
