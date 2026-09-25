"""
Brief 2, T3 -- the competition check on every D1 date (R2, R3). A mechanism check: it reads no excursion.

Pairs: for each D1 crossing j and each name i already live at tau_j (tau_i < tau_j <= tau_i + L), the
log-ratio of i's collapsed (10 ms) trades in [tau_j, tau_j + W) against [tau_j - W, tau_j), W in {5, 15, 60}
min, W < L (A2.5). Baseline moments (R2): every live name i at every clock minute t > tau_i up to 20:00,
with no D1 crossing other than i's own within [t - W, t + W]; pooled by
(year, clock segment, L, W, age octave), age = time since i's own tau, octave = floor(log2(age s)).
Excess = pair log-ratio - its cell's median. Cells with fewer than 20 finite moments: baseline_thin,
shown and not read. R3: a pair or moment counts only if [t - W, t + W] lies inside one clock segment with no
cross minute; invalid ones are `window_crosses_segment`, excluded on both sides, and counted; every
retained window is re-checked by b2common.assert_windows (escalation row 3). Zero-count windows are a class
on both sides. No draws, so no seed.

Writes artifacts/t3_pairs.parquet, t3_baseline_cells.parquet, t3_summary.json. The ~10^7 baseline moments
themselves are aggregated in memory into the cell table and not written; the run is deterministic.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/t3_competition.py
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402

C1 = B.C1
NS, MIN_NS = B.NS, B.MIN_NS
LIV = [("15", 15 * MIN_NS), ("60", 60 * MIN_NS), ("rest_of_session", None)]
SEG = np.array(C1.SEGMENTS, dtype=object)


def ratios(ct: np.ndarray, t: np.ndarray, W: int):
    """Brief 1 t5b_competition.ratio, vectorised over t: n in [t, t + W) over n in [t - W, t)."""
    a = np.searchsorted(ct, t - W, "left")
    m = np.searchsorted(ct, t, "left")
    b = np.searchsorted(ct, t + W, "left")
    nb, na = m - a, b - m
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.where((na > 0) & (nb > 0), np.log(na / np.where(nb > 0, nb, 1)), np.nan)
    return na, nb, lr


def process_date(args):
    date, names, windows_min, tol = args
    bounds, t0400, t2000, op, cl = B.seg_bounds(date)
    year = int(date[:4])
    cts = {}
    for e in names["event_id"]:
        tr = C1.read_trades(e, with_conditions=False)
        a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
        cts[e] = C1.collapse_tol(tr["ts"][a:b].copy(), tol)
        del tr
    ev = names["event_id"].to_numpy()
    tau = names["tau_ns"].to_numpy(np.int64)
    order = np.argsort(tau, kind="stable")
    all_tau = tau[order]
    pairs, base, counts = {}, {"seg": [], "W": [], "oct": [], "in15": [], "in60": [], "lr": []}, []
    for idx_i in range(len(ev)):
        i, ti = ev[idx_i], int(tau[idx_i])
        ct = cts[i]
        # ------------------------------------------------ pairs (i live at tau_j)
        later = tau > ti
        for lname, L in LIV:
            m = later & ((tau <= ti + L) if L is not None else True)
            if not m.any():
                continue
            tj, js = tau[m], ev[m]
            for wmin in windows_min:
                W = wmin * MIN_NS
                if L is not None and W >= L:
                    continue                                   # A2.5: structurally undefined, not run
                ok = B.window_valid(tj, W, bounds, t0400, t2000)
                B.assert_windows(tj[ok], W, bounds, t0400, t2000)          # row 3
                na, nb, lr = ratios(ct, tj, W)
                age = (tj - ti) / NS
                st = np.where(~ok, "window_crosses_segment", np.where(np.isfinite(lr), "ok", "zero_count"))
                n = tj.size
                for col, val in (("j", js), ("i", np.full(n, i, dtype=object)), ("liveness", np.full(n, lname, dtype=object)),
                                 ("W_min", np.full(n, wmin, dtype=np.int16)), ("segment", SEG[np.searchsorted(bounds, tj, "right")]),
                                 ("age_s", age), ("octave", B.octave(age)), ("n_after", np.where(ok, na, -1)),
                                 ("n_before", np.where(ok, nb, -1)), ("log_ratio", np.where(ok, lr, np.nan)), ("status", st)):
                    pairs.setdefault(col, []).append(val)
        # ------------------------------------------------ baseline moments (R2)
        grid = np.arange((ti // MIN_NS + 1) * MIN_NS, t2000 + 1, MIN_NS, dtype=np.int64)
        others = np.delete(all_tau, int(np.searchsorted(all_tau, ti, "left")))      # i's own crossing is allowed
        in15_all, in60_all = (grid - ti) <= 15 * MIN_NS, (grid - ti) <= 60 * MIN_NS
        for wmin in windows_min:
            W = wmin * MIN_NS
            ok = B.window_valid(grid, W, bounds, t0400, t2000)
            p1 = np.searchsorted(others, grid - W, "left")
            p2 = np.searchsorted(others, grid + W, "right")
            free = p1 == p2
            for lname, lm in (("15", in15_all), ("60", in60_all), ("rest_of_session", np.ones_like(in15_all))):
                counts.append((lname, wmin, int(lm.sum()), int((lm & ~ok).sum()), int((lm & ok & ~free).sum())))
            keep = ok & free
            g = grid[keep]
            B.assert_windows(g, W, bounds, t0400, t2000)                            # row 3
            if g.size == 0:
                continue
            _, _, lr = ratios(ct, g, W)
            base["seg"].append(np.searchsorted(bounds, g, "right").astype(np.int8))
            base["W"].append(np.full(g.size, wmin, dtype=np.int8))
            base["oct"].append(B.octave((g - ti) / NS).astype(np.int8))
            base["in15"].append(in15_all[keep])
            base["in60"].append(in60_all[keep])
            base["lr"].append(lr)
    pr = pd.DataFrame({k: np.concatenate(v) for k, v in pairs.items()}) if pairs else pd.DataFrame()
    pr.insert(0, "year", year)
    pr.insert(0, "date", date)
    bs = {k: (np.concatenate(v) if v else np.array([])) for k, v in base.items()}
    bs["year"] = np.full(bs["lr"].size, year, dtype=np.int16)
    return pr, bs, counts


def main() -> int:
    t_start = time.perf_counter()
    cfg = B.load_cfg()
    r2 = cfg["brief2_diff"]["R2"]
    min_n = r2["min_baseline_moments"]
    windows_min = cfg["t5b_competition"]["windows_min"]
    tol = cfg["t5_attention"]["collapse_tol_ms"]
    pop = pd.read_parquet(B.art("t0_population.parquet"))
    pop = pop[pop["tau_available"]]
    jobs = [(d, g[["event_id", "tau_ns"]].reset_index(drop=True), windows_min, tol) for d, g in pop.groupby("event_date_canonical")]
    jobs.sort(key=lambda j: -len(j[1]))
    prs, parts, counts = [], {k: [] for k in ("year", "seg", "W", "oct", "in15", "in60", "lr")}, []
    with ProcessPoolExecutor(max_workers=int(os.environ.get("B2_DATE_WORKERS", "5"))) as ex:
        for k, (pr, bs, cn) in enumerate(ex.map(process_date, jobs, chunksize=1)):
            prs.append(pr)
            for key in parts:
                parts[key].append(bs[key])
            counts += cn
            if (k + 1) % 100 == 0:
                print(f"  {k + 1:,}/{len(jobs):,} dates  {time.perf_counter() - t_start:,.0f}s", flush=True)
    pairs = pd.concat(prs, ignore_index=True)
    for c in ("W_min", "octave"):                      # dates with no pair contribute column-less frames
        assert pairs[c].notna().all()
        pairs[c] = pairs[c].astype(int)
    for c in ("n_after", "n_before"):
        pairs[c] = pairs[c].where(pairs[c] >= 0).astype("Int64")
    bm = pd.DataFrame({k: np.concatenate(v) for k, v in parts.items()})
    bm["seg"] = bm["seg"].astype(np.int8)
    print(f"pairs {len(pairs):,}; baseline moments {len(bm):,}", flush=True)

    # ------------------------------------------------ baseline cells, per liveness
    cells = []
    for lname in ("15", "60", "rest_of_session"):
        sub = bm if lname == "rest_of_session" else bm[bm["in15" if lname == "15" else "in60"]]
        g = sub.groupby(["year", "seg", "W", "oct"])["lr"]
        c = pd.DataFrame({"n_moments": g.size(), "n_finite": g.count(), "median": g.median(),
                          "p25": g.quantile(.25), "p75": g.quantile(.75)}).reset_index()
        c["liveness"] = lname
        cells.append(c)
    cells = pd.concat(cells, ignore_index=True).rename(columns={"W": "W_min", "oct": "octave"})
    cells["segment"] = SEG[cells.pop("seg").to_numpy().astype(int)]
    cells["W_min"] = cells["W_min"].astype(int)
    cells["octave"] = cells["octave"].astype(int)
    cells["year"] = cells["year"].astype(int)
    cells["n_zero_count"] = cells["n_moments"] - cells["n_finite"]
    cells["baseline_thin"] = cells["n_finite"] < min_n
    cells["config_hash"] = B.cfg_hash()
    cells.to_parquet(B.art("t3_baseline_cells.parquet"), index=False)

    key = ["liveness", "year", "segment", "W_min", "octave"]
    pairs = pairs.merge(cells[key + ["n_finite", "median"]].rename(columns={"n_finite": "baseline_n", "median": "baseline_median"}),
                        on=key, how="left")
    pairs["baseline_n"] = pairs["baseline_n"].fillna(0).astype(int)
    pairs["baseline_thin"] = pairs["baseline_n"] < min_n
    pairs["excess"] = np.where(pairs["status"] == "ok", pairs["log_ratio"] - pairs["baseline_median"], np.nan)
    pairs["config_hash"] = B.cfg_hash()
    for c in ("liveness", "segment", "status", "date"):
        pairs[c] = pairs[c].astype("category")
    pairs.to_parquet(B.art("t3_pairs.parquet"), index=False)

    # ------------------------------------------------ summary
    cn = pd.DataFrame(counts, columns=["liveness", "W_min", "moments_in_span", "invalid_r3", "excluded_other_crossing"])
    cn = cn.groupby(["liveness", "W_min"]).sum()

    def dist(v):
        v = pd.Series(v).dropna()
        return {"n": int(v.size), "median": float(v.median()) if v.size else None, "p25": float(v.quantile(.25)) if v.size else None,
                "p75": float(v.quantile(.75)) if v.size else None, "mean": float(v.mean()) if v.size else None}

    per_cell, row8 = {}, {}
    for (L, W), g in pairs.groupby(["liveness", "W_min"], observed=True):
        okp = g[g["status"] == "ok"]
        read = okp[~okp["baseline_thin"]]
        thin_share = float(okp["baseline_thin"].mean()) if len(okp) else None
        cc = cells[(cells["liveness"] == L) & (cells["W_min"] == W)]
        b = cn.loc[(L, W)] if (L, W) in cn.index else None
        per_cell[f"L={L}|W={W}"] = {
            "pairs": int(len(g)), "status": g["status"].value_counts().to_dict(),
            "share_lost_r3": float((g["status"] == "window_crosses_segment").mean()),
            "excess_read": dist(read["excess"]), "excess_thin_cells": dist(okp[okp["baseline_thin"]]["excess"]),
            "log_ratio_read": dist(read["log_ratio"]),
            "pairs_in_thin_cells_share": thin_share,
            "baseline": {"cells": int(len(cc)), "thin_cells": int(cc["baseline_thin"].sum()), "moments": int(cc["n_moments"].sum()),
                         "finite_moments": int(cc["n_finite"].sum()), "zero_count_moments": int(cc["n_zero_count"].sum()),
                         "moments_in_span": int(b["moments_in_span"]) if b is not None else None,
                         "lost_r3": int(b["invalid_r3"]) if b is not None else None,
                         "excluded_other_crossing": int(b["excluded_other_crossing"]) if b is not None else None},
            "by_year": {str(y): dist(gy["excess"]) for y, gy in read.groupby("year")},
            "by_segment": {str(s): dist(gs["excess"]) for s, gs in read.groupby("segment", observed=True)},
        }
        row8[f"L={L}|W={W}"] = thin_share

    # ------------------------------------------------ Brief 1's T5b crossing ratios on the dev dates, reproduced
    b1 = pd.read_parquet(B.b1_art("t5b_competition.parquet"))
    b1 = b1[(b1["arm"] == "crossing") & (b1["status"].isin(["ok", "zero_count"]))][["j", "i", "liveness", "W_min", "n_after", "n_before", "log_ratio"]]
    mine = pairs[pairs["status"].isin(["ok", "zero_count"])][["j", "i", "liveness", "W_min", "n_after", "n_before", "log_ratio"]].copy()
    mine["liveness"] = mine["liveness"].astype(str)
    b1["liveness"] = b1["liveness"].astype(str)
    mm = b1.merge(mine, on=["j", "i", "liveness", "W_min"], how="inner", suffixes=("_b1", "_b2"))
    same = bool(len(mm) and (mm["n_after_b1"] == mm["n_after_b2"]).all() and (mm["n_before_b1"] == mm["n_before_b2"]).all())
    esc = cfg["brief2"]["escalation"]
    summary = {
        "config_hash": B.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "dates": len(jobs),
        "pairs": int(len(pairs)), "baseline_moments_finite_and_zero": int(len(bm)),
        "baseline_cells": int(len(cells)), "baseline_thin_cells": int(cells["baseline_thin"].sum()),
        "cells": per_cell,
        "row_8": {"criterion": esc["row_8"]["criterion"], "tier": "LOG", "by_cell": row8,
                  "fires": bool(any(v is not None and v > esc["row_8"]["threshold"] for v in row8.values()))},
        "row_3_windows": "b2common.assert_windows on every retained pair and baseline window; none raised",
        "dev_dates_reproduce_brief1_t5b_crossing": {"value": same, "matched_rows": int(len(mm)),
                                                    "brief1_rows_valid_or_zero": int(len(b1)),
                                                    "note": "Brief 1 rows whose window crosses a segment are now excluded (R3), so fewer match"},
        "rule": {k: r2[k] for k in ("baseline_cell", "baseline_moments", "excess", "zero_counts", "thin_cells")},
    }
    B.write_json("t3_summary.json", summary)
    for k, v in per_cell.items():
        print(k, v["pairs"], "lost", round(v["share_lost_r3"], 3), "excess", v["excess_read"], "thin", v["pairs_in_thin_cells_share"])
    print(summary["row_8"]["fires"], summary["dev_dates_reproduce_brief1_t5b_crossing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
