"""
Chop regime C1, Amendment 3 W2 -- the chart wall's filter table: T1-T4 at every minute from tau to the last minute before
20:00, for the W1 events.

The measure code is unchanged: measures.build_event with a copy of the config whose moments.wall_minutes_every_1 is 960,
so c1common.moment_grid yields tau + j min for every j until 20:00 at weight 1 (its weights-sum assertion holds). The
causality and segment assertions run inside every measure function, as in T6. g1, g2 (against the t6b null bands) and g3
(which reads the forward window) come from t7_galleries.flags on the wall's own moments and rungs; the forward values are
used for g3 and then dropped -- the table keeps the condition, override and er columns, the segment and the flags only.

Writes cache/w2_moments.parquet and cache/w2_er_rungs.parquet (rebuildable, git-ignored), artifacts/w2_summary.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/w2_wall_filter.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402
import measures as M  # noqa: E402
import t7_galleries as T7  # noqa: E402

CFG = C.load_cfg()
WCFG = copy.deepcopy(CFG)
WCFG["moments"]["wall_minutes_every_1"] = 960
KEEP = ["event_id", "j", "t_ns", "weight", "segment", "measure_state", "quote_at_t", "no_print_since_last_moment", "halt_state", "price_basis", "context_basis",
        "tcs_state", "trade_rate", "dollar_flow", "spread_bp_t", "spread_c_t", "quote_age_s", "depth_ask_usd", "turnover_rate", "n_eff", "top3_share",
        "move_per_trade", "leg_s", "giveback", "act_ratio", "er", "er_allmax"] + [f"cost_noise_{h}" for h in C.HORIZONS]
FLAG_INPUTS = ["turnover_t", "g3_fwd_max_px", "leg_high_px", "ask_t", "bid_t", "sigma_w60"]
_HALTS = None


def one(rec: dict) -> dict:
    global _HALTS
    if _HALTS is None:
        _HALTS = C.B1.load_halt_labels()
    t0 = time.perf_counter()
    o = M.build_event(rec, WCFG, 1.0, _HALTS.get(f"{rec['ticker']}|{rec['event_date_canonical']}", []))
    m = pd.DataFrame(o["rows"])
    for c in KEEP + FLAG_INPUTS:
        if c not in m:
            m[c] = np.nan
    m = m[KEEP + FLAG_INPUTS].copy()
    m["t_ns"] = pd.array([int(x) for x in m["t_ns"]], dtype="Int64")
    sf = pd.DataFrame(o["sf_rungs"])
    sf = sf[["j", "k", "er", "price_basis"]] if len(sf) else pd.DataFrame(columns=["j", "k", "er", "price_basis"])
    return {"event_id": rec["event_id"], "m": m, "sf": sf, "seconds": time.perf_counter() - t0, "n_prints": o["n_prints"]}


def main() -> int:
    t_start = time.perf_counter()
    pop = C.load_population().set_index("event_id")
    E = pd.read_parquet(C.art("w1_events.parquet"))
    recs = []
    for e in E["event_id"]:
        r = pop.loc[e].to_dict()
        r["event_id"] = e
        recs.append(r)
    recs.sort(key=lambda r: -r["n_day_prints"])
    res = []
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for n, r in enumerate(ex.map(one, recs, chunksize=1)):
            res.append(r)
            if (n + 1) % 100 == 0:
                print(f"  {n + 1}/{len(recs)}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    build_s = time.perf_counter() - t_start
    m = pd.concat([r["m"] for r in res], ignore_index=True)
    m["t_ns"] = C.as_int64(m["t_ns"])
    ev = E.set_index("event_id")
    m["event_index"] = m["event_id"].map(ev["event_index"]).astype(int)
    m["price_tier"] = m["event_id"].map(ev["price_tier"])
    m["moment_uid"] = m["event_index"].astype(np.int64) * 2048 + m["j"].astype(np.int64)
    m["dev_slice"] = m["event_id"].map(pop["slice"]).eq("development")
    assert m["dev_slice"].all(), "a non-development row in the wall's filter table"
    # every event's moments are tau + j min for j = 0..n-1, weight 1, strictly before 20:00
    for eid, g in m.groupby("event_id", sort=False):
        assert (g["j"].to_numpy() == np.arange(len(g))).all() and (g["weight"] == 1).all(), f"{eid}: the wall grid is not every minute"
        assert int(g["t_ns"].iloc[0]) == int(ev.loc[eid, "tau_ns"]), f"{eid}: the wall grid does not start at tau"
    sf = []
    for r in res:
        s = r["sf"].copy()
        s["event_id"] = r["event_id"]
        sf.append(s)
    sf = pd.concat(sf, ignore_index=True)
    sf["moment_uid"] = sf["event_id"].map(ev["event_index"]).astype(np.int64) * 2048 + sf["j"].astype(np.int64)
    sf = sf.merge(m[["moment_uid", "segment", "price_tier"]], on="moment_uid", how="left")
    bands = pd.read_parquet(C.art("t6b_null_bands.parquet"))
    fl = T7.flags(m, bands, sf[["moment_uid", "k", "segment", "price_tier", "er", "price_basis"]])
    m = m.merge(fl, on="moment_uid", how="left")
    m = m.drop(columns=["g3_fwd_max_px"])                           # the forward value served g3 and is not kept
    cache = C.REPO / C.OUT / "cache"
    pm, ps = cache / "w2_moments.parquet", cache / "w2_er_rungs.parquet"
    m.to_parquet(pm, index=False)
    sf[sf["k"] <= 6][["moment_uid", "event_id", "j", "k", "er", "price_basis"]].to_parquet(ps, index=False)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()[:16]  # noqa: E731
    seg = m.groupby("segment").agg(minutes=("j", "size"), no_scale_free=("er", lambda s: float(s.isna().mean()))).to_dict("index")
    summ = {"config_hash": C.cfg_hash(), "build_seconds": round(build_s, 1), "seconds": round(time.perf_counter() - t_start, 1), "events": int(len(res)),
            "minutes": int(len(m)), "per_segment": seg, "flags": {c: int(m[c].sum()) for c in ("g1", "g2")}, "worker_seconds_max": float(max(r["seconds"] for r in res)),
            "grid": "tau + j min, every minute until 20:00, weight 1 (moments.wall_minutes_every_1 = 960)",
            "assertions": ["causality and segment inside every measure function", "every minute from tau", "development slice only"],
            "cache": {pm.name: {"rows": int(len(m)), "sha256_16": sha(pm)}, ps.name: {"rows": int((sf["k"] <= 6).sum()), "sha256_16": sha(ps)}}}
    C.write_json("w2_summary.json", summ)
    print(json.dumps(summ, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
