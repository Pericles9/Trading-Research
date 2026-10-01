"""
Chop regime C1, T7 -- gallery flags on every development-slice moment, the embedded sample, the gallery pools and their
strips (brief section 5 and 7, Amendment 1 A1.3's G2 rule).

  flags     g1  at the finest rate rung n_eff <= 5 and top3_share >= 0.6
            g2  turnover_t < 1%, dollar_flow >= $20,000/min at the finest rate rung, and at every valid scale-free rung
                k in 1..4 (at least one) er inside its cell's null [5th, 95th] values (t6b_null_bands; the rung's own basis)
            g3  leg_s >= 2, 0.1 <= giveback <= 0.6, and in hindsight the highest non-spike print in (t, t + 60 min] is above the
                leg high by at least the quoted spread at t (dollars) and by at least sigma_w60 in log units
            "gallery finder, not a filter": none of these is a condition
  sample    the largest fraction f on a 0.01 grid such that ceil(f x n) events of every year x tau-segment stratum (a seeded
            permutation; whole events) fit the 100 MB budget with the strips' worst case reserved; sized with the page's own
            encoder (suitedata)
  pools     from the embedded events' non-auction moments, seeded: up to 150 per finder, and a random pool of 300
  strips    per pooled moment: prints (dots) from max(segment start, t - 60 min) to t + 60 min (cut at 20:00), at most 2,000
            (the highest and lowest prints and the prints either side of t kept, then an even stride); D17-valid bid and ask
            as step lines (at most 1,000 change points); 200 volume bars

Writes artifacts/t7_flags.parquet, t7_sample.parquet (event -> embedded), t7_pools.parquet, t7_summary.json; the strips to
cache/t7_strips.npz (rebuildable, git-ignored).

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t7_galleries.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402
import nulls as NL  # noqa: E402
import suitedata as SD  # noqa: E402

CFG = C.load_cfg()
GA = CFG["galleries"]
SEED = GA["pool_seed"]
BUDGET = CFG["suite"]["size_budget_bytes"]
STRIP_MAX_PRINTS, STRIP_MAX_QUOTES, STRIP_BARS = GA["strip"]["max_prints"], 1000, GA["strip"]["volume_bars"]
RANDOM_POOL = 300
FIXED_RESERVE = 6_000_000                     # plotly.min.js (4.8 MB) + the page's code and the small tables


def load_moments() -> pd.DataFrame:
    years = sorted(C.dev_slice(C.load_population())["year"].unique())
    return pd.concat([pd.read_parquet(C.art(f"t6_moments_{y}.parquet")) for y in years], ignore_index=True)


def load_sf(cols) -> pd.DataFrame:
    years = sorted(C.dev_slice(C.load_population())["year"].unique())
    return pd.concat([pd.read_parquet(C.art(f"t6_sf_rungs_{y}.parquet"), columns=cols) for y in years], ignore_index=True)


def flags(m: pd.DataFrame, bands: pd.DataFrame) -> pd.DataFrame:
    g = GA
    f = pd.DataFrame({"moment_uid": m["moment_uid"]})
    f["g1"] = (m["n_eff"] <= g["G1_low_volume_pop"]["n_eff_max"]) & (m["top3_share"] >= g["G1_low_volume_pop"]["top3_share_min"])
    # g2: every valid scale-free rung k in 1..4 inside its cell's null band
    sf = load_sf(["moment_uid", "k", "segment", "price_tier", "er", "price_basis"])
    sf = sf[sf["k"].between(1, 4)].copy()
    sf["basis"] = np.where(sf["price_basis"] == "mid", "mid", "vwap")
    sf["cell"] = sf["segment"] + "|" + sf["k"].astype(str) + "|" + sf["price_tier"] + "|" + sf["basis"]
    b = bands.set_index("cell")
    sf["inb"] = (sf["er"] >= sf["cell"].map(b["null_p05"])) & (sf["er"] <= sf["cell"].map(b["null_p95"]))
    agg = sf.groupby("moment_uid")["inb"].agg(["all", "size"])
    g2r = g["G2_higher_float_noise"]
    f["g2"] = (m["turnover_t"] < g2r["turnover_t_max"]) & (m["dollar_flow"] >= g2r["dollar_flow_min_usd_per_min"]) & \
              m["moment_uid"].map(agg["all"]).fillna(False).astype(bool) & (m["moment_uid"].map(agg["size"]).fillna(0) >= 1)
    g3r = g["G3_pause_between_legs"]
    with np.errstate(divide="ignore", invalid="ignore"):
        up = np.log(m["g3_fwd_max_px"] / m["leg_high_px"])
    f["g3"] = (m["leg_s"] >= g3r["leg_s_min"]) & m["giveback"].between(g3r["giveback_min"], g3r["giveback_max"]) & m["quote_at_t"].fillna(False).astype(bool) & \
              ((m["g3_fwd_max_px"] - m["leg_high_px"]) >= (m["ask_t"] - m["bid_t"])) & (up >= m["sigma_w60"])
    for c in ("g1", "g2", "g3"):
        f[c] = f[c].fillna(False).astype(bool)
    return f


def stratum_order(ev: pd.DataFrame) -> pd.DataFrame:
    """A seeded permutation inside each year x tau-segment stratum; rank / size gives each event its inclusion threshold."""
    rng = np.random.default_rng(CFG["suite"]["sample"]["seed"])
    ev = ev.sort_values("event_id").reset_index(drop=True)
    ev["perm"] = rng.permutation(len(ev))
    ev["rank"] = ev.groupby(["year", "tau_segment"])["perm"].rank(method="first").astype(int)
    ev["n_stratum"] = ev.groupby(["year", "tau_segment"])["event_id"].transform("size")
    return ev


def in_sample(ev: pd.DataFrame, f: float) -> pd.Series:
    return ev["rank"] <= np.ceil(np.round(f * ev["n_stratum"], 9))


# ------------------------------------------------------------------ strips

def strip_for(args) -> list[dict]:
    rec, ms = args
    eid, date = rec["event_id"], rec["event_date_canonical"]
    tr = C.B1.read_trades(eid, with_conditions=False)
    q = C.read_quotes(eid)
    op, cl = C.B1.rth_bounds_ns(date)
    t2000 = C.B1.et_ns(date, "20:00:00")
    out = []
    for m in ms:
        t, seg = int(m["t_ns"]), m["segment"]
        lo = max(C.B1.segment_start_ns(seg, date, op, cl), t - 60 * C.MIN_NS)
        hi = min(t + 60 * C.MIN_NS, t2000)
        a, b = int(np.searchsorted(tr["ts"], lo, "left")), int(np.searchsorted(tr["ts"], hi, "right"))
        ts, px, sz = tr["ts"][a:b], tr["px"][a:b], tr["sz"][a:b]
        keep = np.arange(ts.size)
        if ts.size > STRIP_MAX_PRINTS:
            must = {int(np.argmax(px)), int(np.argmin(px))}
            k = int(np.searchsorted(ts, t, "right"))
            must |= {max(k - 1, 0), min(k, ts.size - 1)}
            rest = np.setdiff1d(keep, np.array(sorted(must)))
            take = rest[np.linspace(0, rest.size - 1, STRIP_MAX_PRINTS - len(must)).astype(int)]
            keep = np.union1d(take, np.array(sorted(must)))
        nb = STRIP_BARS
        edges = np.linspace(lo, hi, nb + 1)
        vol = np.histogram(ts, bins=edges, weights=sz)[0] if ts.size else np.zeros(nb)
        qt, qb, qa = np.zeros(0), np.zeros(0), np.zeros(0)
        if q is not None:
            qa_, qb_ = int(np.searchsorted(q["ts"], lo, "left")), int(np.searchsorted(q["ts"], hi, "right"))
            bid, ask, bs, as_ = q["bid"][qa_:qb_], q["ask"][qa_:qb_], q["bsz"][qa_:qb_], q["asz"][qa_:qb_]
            ok = ~C.d17_excluded(bid, ask, bs, as_)
            qts, bid, ask = q["ts"][qa_:qb_][ok], bid[ok], ask[ok]
            # the prevailing valid quote at the strip start (searched back over up to 20,000 rows), then the change points
            back = slice(max(0, qa_ - 20000), qa_)
            okb = np.flatnonzero(~C.d17_excluded(q["bid"][back], q["ask"][back], q["bsz"][back], q["asz"][back]))
            if okb.size:
                ip = back.start + int(okb[-1])
                qts, bid, ask = np.r_[lo, qts], np.r_[q["bid"][ip], bid], np.r_[q["ask"][ip], ask]
            if qts.size:
                chg = np.r_[True, (bid[1:] != bid[:-1]) | (ask[1:] != ask[:-1])]
                qts, bid, ask = qts[chg], bid[chg], ask[chg]
                if qts.size > STRIP_MAX_QUOTES:
                    ii = np.linspace(0, qts.size - 1, STRIP_MAX_QUOTES).astype(int)
                    qts, bid, ask = qts[ii], bid[ii], ask[ii]
            qt, qb, qa = (qts - t) / 1e9, bid, ask
        out.append({"moment_uid": int(m["moment_uid"]), "pt": ((ts[keep] - t) / 1e9).astype(np.float32), "pp": px[keep].astype(np.float32),
                    "qt": np.asarray(qt, np.float32), "qb": np.asarray(qb, np.float32), "qa": np.asarray(qa, np.float32),
                    "vb": vol.astype(np.float32), "lo_s": (lo - t) / 1e9, "hi_s": (hi - t) / 1e9, "n_prints": int(ts.size)})
    return out


def main() -> int:
    t0 = time.perf_counter()
    import suite_table as ST                                                             # the page's table (shared with T8)
    m = load_moments()
    bands = pd.read_parquet(C.art("t6b_null_bands.parquet"))
    fl = flags(m, bands)
    fl["config_hash"] = C.cfg_hash()
    fl.to_parquet(C.art("t7_flags.parquet"), index=False)
    m = m.merge(fl[["moment_uid", "g1", "g2", "g3"]], on="moment_uid", how="left")
    print(f"flags {time.perf_counter() - t0:,.0f}s  g1 {int(fl.g1.sum()):,} g2 {int(fl.g2.sum()):,} g3 {int(fl.g3.sum()):,}", flush=True)

    # ---------------- the embedded sample
    pop = C.load_population()
    ev = stratum_order(C.dev_slice(pop)[["event_id", "year", "tau_segment"]])
    worst_strip = (STRIP_MAX_PRINTS * 8 + STRIP_MAX_QUOTES * 12 + STRIP_BARS * 4) * 4 / 3 * 1.01
    n_pool = 3 * GA["pool_per_finder"] + RANDOM_POOL
    reserve = FIXED_RESERVE + n_pool * worst_strip
    sized = {}

    sfe = load_sf(["moment_uid", "event_id", "k", "er"])

    def table_bytes(f: float) -> int:
        ids = set(ev.loc[in_sample(ev, f), "event_id"])
        tab, evt = ST.build(m[m["event_id"].isin(ids)], pop, sfe[sfe["event_id"].isin(ids)])
        tab.pop("_rows")
        b = SD.size_of(tab) + len(json.dumps(evt))
        sized[round(f, 2)] = b
        return b

    lo_f, hi_f = 0, 100
    if table_bytes(1.0) + reserve <= BUDGET:
        f = 1.0
    else:
        while hi_f - lo_f > 1:
            mid = (lo_f + hi_f) // 2
            if table_bytes(mid / 100) + reserve <= BUDGET:
                lo_f = mid
            else:
                hi_f = mid
        f = lo_f / 100
    ev["embedded"] = in_sample(ev, f)
    ev[["event_id", "year", "tau_segment", "perm", "rank", "n_stratum", "embedded"]].to_parquet(C.art("t7_sample.parquet"), index=False)
    emb = set(ev.loc[ev["embedded"], "event_id"])
    print(f"sample f = {f:.2f}: {len(emb):,} of {len(ev):,} events  {time.perf_counter() - t0:,.0f}s", flush=True)

    # ---------------- pools
    me = m[m["event_id"].isin(emb) & m["segment"].isin(C.SEGS)].reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    pools = []
    for name, sel in (("G1", me["g1"]), ("G2", me["g2"]), ("G3", me["g3"]), ("random", pd.Series(True, index=me.index))):
        idx = np.flatnonzero(sel.to_numpy())
        cap = RANDOM_POOL if name == "random" else GA["pool_per_finder"]
        pick = np.sort(rng.choice(idx, size=min(cap, idx.size), replace=False)) if idx.size else np.zeros(0, int)
        pools.append(pd.DataFrame({"moment_uid": me.loc[pick, "moment_uid"].to_numpy(), "pool": name, "pool_size_available": idx.size}))
    P = pd.concat(pools, ignore_index=True)
    P.to_parquet(C.art("t7_pools.parquet"), index=False)
    uniq = me[me["moment_uid"].isin(P["moment_uid"])]
    jobs = []
    for eid, g in uniq.groupby("event_id"):
        r = pop.set_index("event_id").loc[eid]
        jobs.append(({"event_id": eid, "event_date_canonical": r["event_date_canonical"]}, g[["moment_uid", "t_ns", "segment"]].to_dict("records")))
    strips = []
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for r in ex.map(strip_for, jobs, chunksize=4):
            strips.extend(r)
    cache = C.REPO / C.OUT / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    np.save(cache / "t7_strips.npy", np.array(strips, dtype=object), allow_pickle=True)
    strip_bytes = sum((s["pt"].nbytes + s["pp"].nbytes + s["qt"].nbytes + s["qb"].nbytes + s["qa"].nbytes + s["vb"].nbytes) for s in strips)
    summ = {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t0, 1),
            "flags": {c: int(fl[c].sum()) for c in ("g1", "g2", "g3")}, "flags_moment_minutes": {c: int(m.loc[m[c], "weight"].sum()) for c in ("g1", "g2", "g3")},
            "sample": {"fraction": f, "events_embedded": len(emb), "events": int(len(ev)), "events_share": len(emb) / len(ev),
                       "moments_embedded": int(m["event_id"].isin(emb).sum()), "moments": int(len(m)), "reserve_bytes": int(reserve),
                       "table_bytes_by_f": sized, "by_stratum": ev.groupby(["year", "tau_segment"])["embedded"].agg(["sum", "size"]).reset_index().to_dict("records"),
                       "row5_fires": bool(len(emb) / len(ev) < 0.5)},
            "pools": P.groupby("pool").agg(n=("moment_uid", "size"), available=("pool_size_available", "first")).to_dict("index"),
            "strips": {"n": len(strips), "raw_bytes": int(strip_bytes), "max_prints_in_window": int(max(s["n_prints"] for s in strips)) if strips else 0}}
    C.write_json("t7_summary.json", summ)
    print(json.dumps({k: summ[k] for k in ("flags", "sample", "pools", "strips")}, indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
