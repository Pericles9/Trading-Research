"""
Chop regime C1, Amendment 3 W1 -- the chart wall's events, 1-minute candles, halts and segment marks.

  order    every development-slice event with tau (the quarantine excluded), stratified by year x tau's segment: within
           each stratum a seeded permutation; events enter in increasing (rank - 0.5) / stratum size, which allocates in
           proportion to stratum size at every prefix (ties by event_id). W1 builds the first 600; W3 keeps the longest
           prefix that fits the 60 MB budget (never below 300).
  candles  from c1common.Tape -- every print 04:00-20:00 that every C1 measure and the b1 / b2 / S1 / S2 tick builds read
           (read_trades; no condition-code filter, no spike guard): minute = floor((ts - 04:00) / 60 s); open / close =
           the first / last print of the minute in (sip_timestamp, sequence_number) order; high / low; share volume. From
           the first print's minute to the last print's; a minute with no print has no candle (NaN) and volume 0.
  marks    tau (S2's tau_d) in minutes after 04:00 and its price; the crossing level = S1's prior_close_exact x 1.30; the
           XNYS open and close of the date (early closes included); halts = the event's labels plus every consecutive-print
           gap >= 300 s with both prints in [open, close) (b2 / S2's rule); S1's theory type at N = 100 (a viewing label).

Writes artifacts/w1_events.parquet, w1_summary.json; cache/w1_candles.npy (rebuildable, git-ignored).

Usage: .venv/Scripts/python.exe research/chop_regime_c1/w1_wall_events.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402

CFG = C.load_cfg()
A3 = CFG["amendment_3"]
B1 = C.B1
MIN = C.MIN_NS


def wall_order(dev: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(A3["W1_sample"]["seed"])
    ev = dev[["event_id", "year", "tau_segment"]].sort_values("event_id").reset_index(drop=True)
    ev["perm"] = rng.permutation(len(ev))
    ev["rank"] = ev.groupby(["year", "tau_segment"])["perm"].rank(method="first").astype(int)
    ev["n_stratum"] = ev.groupby(["year", "tau_segment"])["event_id"].transform("size")
    ev["key"] = (ev["rank"] - 0.5) / ev["n_stratum"]
    ev = ev.sort_values(["key", "event_id"]).reset_index(drop=True)
    ev["order"] = np.arange(len(ev))
    return ev


def one(rec: dict) -> dict:
    eid, date = rec["event_id"], rec["event_date_canonical"]
    tape = C.Tape(eid, date)
    ts, px, sz = tape.ts, tape.px, tape.sz
    m = ((ts - tape.t0400) // MIN).astype(np.int64)
    m0, m1 = int(m[0]), int(m[-1])
    n = m1 - m0 + 1
    o = np.full(n, np.nan)
    h, lo, c = o.copy(), o.copy(), o.copy()
    v = np.zeros(n)
    k = m - m0
    starts = np.r_[0, np.flatnonzero(np.diff(k)) + 1]
    ends = np.r_[starts[1:], k.size]
    for a, b in zip(starts, ends):                        # prints are sorted by (sip_timestamp, sequence_number)
        i = k[a]
        o[i], c[i] = px[a], px[b - 1]
        h[i], lo[i] = px[a:b].max(), px[a:b].min()
        v[i] = sz[a:b].sum()
    assert np.isclose(v.sum(), sz.sum()), "candle volume does not conserve the prints' shares"
    op, cl = tape.op, tape.cl
    halts = [[(s - tape.t0400) / MIN, (e - tape.t0400) / MIN] for s, e in rec["halt_labels"]]
    g = np.diff(ts)
    gi = np.flatnonzero((g >= C.HALT_GAP_NS) & (ts[:-1] >= op) & (ts[1:] < cl))
    halts += [[(int(ts[i]) - tape.t0400) / MIN, (int(ts[i + 1]) - tape.t0400) / MIN] for i in gi]
    return {"event_id": eid, "m0": m0, "n_min": n, "o": o.astype(np.float32), "h": h.astype(np.float32), "l": lo.astype(np.float32), "c": c.astype(np.float32),
            "v": v.astype(np.float32), "open_min": (op - tape.t0400) / MIN, "close_min": (cl - tape.t0400) / MIN,
            "tau_min": (int(rec["tau_ns"]) - tape.t0400) / MIN, "halts": halts, "n_halt_labels": len(rec["halt_labels"]), "n_halt_gaps": int(gi.size),
            "n_prints": int(ts.size), "n_candles": int(np.isfinite(o).sum())}


def main() -> int:
    t0 = time.perf_counter()
    pop = C.load_population()
    dev = C.dev_slice(pop)
    order = wall_order(dev)
    take = order.head(A3["W1_sample"]["target_events"])
    s1 = pd.read_parquet(C.src("s1_events"), columns=["event_id", "prior_close_exact"])
    tt = pd.read_parquet(C.src("s1_events").parent / "s1_theory_types.parquet")
    tt = tt[(tt["N"] == 100) & (tt["type_state"] == "typed")].set_index("event_id")["theory_type"]
    mult = json.load(open(C.REPO / "config/attention_excursion_b1.json"))["t2_tau"]["crossing_multiple"]
    d = take.merge(dev, on=["event_id", "year", "tau_segment"], how="left").merge(s1, on="event_id", how="left")
    assert d["slice"].eq("development").all() and len(d) == len(take)
    halts = B1.load_halt_labels()
    recs = [{"event_id": r.event_id, "event_date_canonical": r.event_date_canonical, "tau_ns": int(r.tau_ns),
             "halt_labels": halts.get(f"{r.ticker}|{r.event_date_canonical}", [])} for r in d.itertuples()]
    out = []
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for r in ex.map(one, recs, chunksize=4):
            out.append(r)
    byid = {r["event_id"]: r for r in out}
    cache = C.REPO / C.OUT / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    np.save(cache / "w1_candles.npy", np.array([byid[e] for e in d["event_id"]], dtype=object), allow_pickle=True)
    E = pd.DataFrame({"event_id": d["event_id"], "order": d["order"], "ticker": d["ticker"], "date": d["event_date_canonical"], "year": d["year"],
                      "tau_segment": d["tau_segment"], "price_tier": d["price_tier"], "s1_type": d["event_id"].map(tt), "tau_ns": d["tau_ns"].astype("int64"),
                      "tau_price": d["tau_price"], "cross_level": d["prior_close_exact"] * mult, "event_index": d["event_index"],
                      "in_suite_sample": d["event_id"].isin(set(pd.read_parquet(C.art("t7_sample.parquet")).query("embedded")["event_id"]))})
    for c in ("m0", "n_min", "open_min", "close_min", "tau_min", "n_halt_labels", "n_halt_gaps", "n_prints", "n_candles"):
        E[c] = E["event_id"].map({k: v[c] for k, v in byid.items()})
    E["halts"] = E["event_id"].map({k: json.dumps(v["halts"]) for k, v in byid.items()})
    assert (E["tau_price"] >= E["cross_level"] - 1e-9).all(), "a tau price below the crossing level"
    E["config_hash"] = C.cfg_hash()
    E.to_parquet(C.art("w1_events.parquet"), index=False)
    summ = {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t0, 1), "events": int(len(E)), "development_events": int(len(dev)),
            "by_stratum": E.groupby(["year", "tau_segment"]).size().rename("n").reset_index().to_dict("records"),
            "in_suite_sample": int(E["in_suite_sample"].sum()), "candle_minutes": int(E["n_min"].sum()), "candles": int(E["n_candles"].sum()),
            "halt_labels": int(E["n_halt_labels"].sum()), "halt_gaps": int(E["n_halt_gaps"].sum()), "s1_type_missing": int(E["s1_type"].isna().sum())}
    C.write_json("w1_summary.json", summ)
    print(json.dumps({k: v for k, v in summ.items() if k != "by_stratum"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
