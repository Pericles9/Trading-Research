"""
Chop regime C1, T6b -- Amendment 1 A1.3: the efficiency ratio's null band per cell, from a seeded sample of
development-slice windows.

Cell = t's segment x rung k x price tier at tau x basis. Eligible windows: every valid scale-free window of the T6 build
(midpoint cells: windows with a midpoint path; VWAP cells: every window -- the reference for vwap_fallback windows).
Per cell the windows are ranked by u = default_rng([seed, event_index, j, k, 97]).random() and the 2,000 smallest kept.
Each kept window is rebuilt from the grid (its segment view and quote view sliced to <= t, measures.bucket_path -- the
build's own code; the recomputed er is asserted equal to T6's) and nulls.null_er draws 20 resampled paths. The band = median, 5th and 95th values pooled over the cell's draws; cells with
fewer than 20 sampled windows are labelled. Beside it, the real er distribution of every eligible window in the cell
(a pre-t measure; no outcome is read).

Writes artifacts/t6b_null_bands.parquet, t6b_summary.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t6b_null_bands.py
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
import measures as M  # noqa: E402
import nulls as NL  # noqa: E402

CFG = C.load_cfg()
N3 = CFG["amendment_1"]["A1_3_null"]
SEED, DRAWS, CAP, MINW = N3["seed"], N3["draws_per_window"], N3["windows_per_cell_max"], N3["min_windows_label"]


def u_of(event_index: np.ndarray, j: np.ndarray, k: np.ndarray) -> np.ndarray:
    return np.array([np.random.default_rng([SEED, int(e), int(a), int(b), 97]).random() for e, a, b in zip(event_index, j, k)])


def one(args) -> dict:
    """Revisit only the sampled windows: each window's moment from the grid, its segment view and quote view sliced to <= t,
    its bucket path (measures.bucket_path, the build's own code), then nulls.null_er. The recomputed er is asserted equal
    to the T6 build's."""
    rec, want = args                                   # want: {(j, k): ([bases], {basis: T6 er})}
    pool = {}
    cfg = CFG
    nb = cfg["measures"]["scale_free_ladder"]["buckets"]
    eid, date = rec["event_id"], rec["event_date_canonical"]
    tape = C.Tape(eid, date)
    book = C.QuoteBook(C.read_quotes(eid), date, 1.0)
    js, ts, _ = C.moment_grid(int(rec["tau_ns"]), tape.t2000, cfg)
    tmap = dict(zip(js.tolist(), ts.tolist()))
    geo = (tape.op, tape.cl)
    for (j, k), (bases, er_t6) in sorted(want.items()):
        t = tmap[j]
        seg = tape.segment(t)
        v = tape.view(t, seg)
        qv = book.view(t)
        H = t - v["lo"]
        a = t - int(round(H / 2.0 ** k))
        bp = M.bucket_path(v, qv, a, t, nb, geo)
        info = {"event_id": eid, "event_index": rec["event_index"], "j": j, "k": k, "seg": seg, "v": v, "qv": qv, "bp": bp,
                "r_vwap": np.diff(bp["lp_vwap"]), "r_mid": np.diff(bp["lp_mid"]) if bp["mid_ok"] else None}
        for b in bases:
            r = info["r_mid"] if b == "mid" else info["r_vwap"]
            e = float(M.scale_free(r[None, :])["er"][0])
            assert (np.isnan(e) and np.isnan(er_t6[b])) or abs(e - er_t6[b]) <= 1e-9, f"{eid} j={j} k={k} {b}: er {e} differs from T6's {er_t6[b]}"
            res = NL.null_er(info, b, DRAWS, SEED)
            if res is None:
                continue
            key = NL.cell_key(seg, k, rec["price_tier"], b)
            pool.setdefault(key, []).append(res[0.0].astype(np.float32))
    return {k: np.concatenate(v) for k, v in pool.items()}


def main() -> int:
    t0 = time.perf_counter()
    pop = C.load_population()
    dev = C.dev_slice(pop).set_index("event_id")
    sf = pd.concat([pd.read_parquet(C.art(f"t6_sf_rungs_{y}.parquet"), columns=["event_id", "j", "k", "segment", "price_tier", "event_index", "mid_ok",
                                                                                "er_mid", "er_vwap"])
                    for y in sorted(dev["year"].unique())], ignore_index=True)
    sf["u"] = u_of(sf["event_index"].to_numpy(), sf["j"].to_numpy(), sf["k"].to_numpy())
    print(f"u for {len(sf):,} windows  {time.perf_counter() - t0:,.0f}s", flush=True)
    sel, real = [], []
    for bs in C.BASES:
        el = sf[sf["mid_ok"]] if bs == "mid" else sf
        for (seg, k, tier), g in el.groupby(["segment", "k", "price_tier"]):
            x = g[f"er_{bs}"].to_numpy(float)
            x = x[np.isfinite(x)]
            real.append({"cell": NL.cell_key(seg, k, tier, bs), "segment": seg, "k": int(k), "tier": tier, "basis": bs, "windows_in_cell": int(len(g)),
                         "real_er_n": int(x.size), **{f"real_q{q:02d}": (float(np.quantile(x, q / 100)) if x.size else np.nan) for q in (5, 25, 50, 75, 95)}})
            s = g.nsmallest(CAP, "u")
            sel.append(s.assign(basis=bs, er_t6=s[f"er_{bs}"])[["event_id", "j", "k", "basis", "er_t6"]])
    sel = pd.concat(sel, ignore_index=True)
    want = {}
    for r in sel.itertuples():
        w = want.setdefault(r.event_id, {}).setdefault((int(r.j), int(r.k)), ([], {}))
        w[0].append(r.basis)
        w[1][r.basis] = float(r.er_t6)
    jobs = [(dict(dev.loc[e].to_dict(), event_id=e), w) for e, w in want.items()]
    jobs.sort(key=lambda x: -x[0]["n_day_prints"])
    print(f"{len(sel):,} window-bases in {len(jobs):,} events", flush=True)
    pool = {}
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for n, r in enumerate(ex.map(one, jobs, chunksize=1)):
            for k, v in r.items():
                pool.setdefault(k, []).append(v)
            if (n + 1) % 1000 == 0:
                print(f"  {n + 1:,}/{len(jobs):,}  {time.perf_counter() - t0:,.0f}s", flush=True)
    nsel = sel.groupby(["basis", "k"]).size()
    out = []
    for r in real:
        draws = np.concatenate(pool[r["cell"]]) if r["cell"] in pool else np.zeros(0, np.float32)
        b = NL.band(draws)
        r.update({"windows_sampled": int(min(CAP, r["windows_in_cell"])), **{f"null_{a}": v for a, v in b.items()}})
        r["label_few_windows"] = r["windows_sampled"] < MINW
        out.append(r)
    O = pd.DataFrame(out).sort_values(["basis", "segment", "tier", "k"]).reset_index(drop=True)
    O["config_hash"] = C.cfg_hash()
    O.to_parquet(C.art("t6b_null_bands.parquet"), index=False)
    C.write_json("t6b_summary.json", {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t0, 1), "windows": int(len(sf)),
                                      "window_bases_sampled": int(len(sel)), "events_revisited": len(jobs), "cells": int(len(O)),
                                      "cells_labelled_few_windows": int(O["label_few_windows"].sum()), "draws_per_window": DRAWS, "cap": CAP,
                                      "sampled_by_basis_rung": {f"{b}|{k}": int(v) for (b, k), v in nsel.items()}})
    print(O[O["tier"] == "$1-3"][["cell", "windows_in_cell", "windows_sampled", "null_median", "null_p05", "null_p95", "real_q50"]].round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
