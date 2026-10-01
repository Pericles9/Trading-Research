"""
Chop regime C1, T5a -- diagnosis of the whole-pipeline control's construction, before T5 is gated on it.

Brief section 6 specifies the whole-pipeline null as "the window's print-level returns shuffled and re-integrated with
the prints' own times and sizes kept" (and the same for midpoint changes at quote-update level), with the reference
control's pass bands. A permutation keeps the sum of the returns, so every shuffled path starts and ends where the real
window does: it is a bridge carrying the window's own net move, not a noise path. The efficiency ratio reads the net move
directly, so the shuffled er_rel inherits the real window's trend (or, where the real net move is small against the
shuffled wander, is pulled below 1 by the tied endpoints).

This script measures three constructions on the same windows (the 53 quarantined events, every valid scale-free window,
both prices), so Cooper can choose with numbers:
  literal     the brief's text: raw returns permuted
  bridge0     demeaned returns permuted (a bridge from the start back to the start)
  bootstrap   demeaned returns drawn with replacement (a free walk; the reference control's and S1's null)
Each with 20 draws per window, seeded; statistics as the reference control's bands read them.

Writes artifacts/t5a_whole_pipeline_diagnosis.parquet (per construction x basis x rung) and t5a_summary.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t5a_whole_pipeline_diagnosis.py
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

CFG = C.load_cfg()
CT = CFG["controls"]
NB = CFG["measures"]["scale_free_ladder"]["buckets"]
S = CT["negative_whole_pipeline"]["shuffles_per_window"]
KINDS = ("literal", "bridge0", "bootstrap")


def draws(x: np.ndarray, kind: str, rng) -> np.ndarray:
    """(S, len(x)) step sequences for one construction."""
    if kind == "literal":
        return rng.permuted(np.tile(x, (S, 1)), axis=1)
    d = x - x.mean()
    if kind == "bridge0":
        return rng.permuted(np.tile(d, (S, 1)), axis=1)
    return d[rng.integers(0, d.size, size=(S, d.size))]


def window(info: dict, eidx: int, out: list) -> None:
    bp, v, qv = info["bp"], info["v"], info["qv"]
    lo, hi = bp["lo"], bp["hi"]
    ts, px, sz = v["ts"][lo:hi], v["px"][lo:hi], v["sz"][lo:hi]
    cv_end = np.cumsum(sz)
    b = M.buckets_core(ts, px, cv_end, np.cumsum(px * sz), NB)
    own, first = b["own"], b["first"]
    E_ = np.arange(1, NB + 1, dtype=np.float64) * (b["V"] / NB)
    E_[-1] = b["V"]
    for ki, kind in enumerate(KINDS):
        rng = np.random.default_rng([CT["seed"], eidx, info["j"], info["k"], 7, ki])
        # VWAP: print-level log returns
        dl = np.diff(np.log(px))
        if dl.size >= 1:
            syn = np.c_[np.zeros(S), np.cumsum(draws(dl, kind, rng), axis=1)]
            dev = np.expm1(syn - syn[:, [first]])
            cd = np.cumsum(dev * sz[None, :], axis=1)
            F = cd[:, own] - (cv_end[own] - E_)[None, :] * dev[:, own]
            u = np.diff(np.c_[np.zeros(S), F], axis=1) / (b["V"] / NB)
            st = M.scale_free(np.diff(np.log1p(np.c_[dev[:, first], u]), axis=1))
            out.append({"kind": kind, "basis": "vwap", "k": info["k"], "er_rel_mean": float(np.nanmean(st["er_rel"])) if np.isfinite(st["er_rel"]).any() else np.nan,
                        "z2": st["vz2"].astype(np.float32), "z4": st["vz4"].astype(np.float32)})
        # midpoint: quote-update log midpoint changes
        if info["r_mid"] is not None:
            vts, vlm = qv["vts"], qv["vlogmid"]
            i0 = int(np.searchsorted(vts, bp["t_first"], "right")) - 1
            dm = np.diff(vlm[i0:])
            idx = np.searchsorted(vts, np.r_[bp["t_first"], bp["t_end"]], "right") - 1 - i0
            path = vlm[i0] + np.c_[np.zeros(S), np.cumsum(draws(dm, kind, rng), axis=1)] if dm.size else np.full((S, 1), vlm[i0])
            st = M.scale_free(np.diff(path[:, idx], axis=1))
            out.append({"kind": kind, "basis": "mid", "k": info["k"], "er_rel_mean": float(np.nanmean(st["er_rel"])) if np.isfinite(st["er_rel"]).any() else np.nan,
                        "z2": st["vz2"].astype(np.float32), "z4": st["vz4"].astype(np.float32)})


def one(rec: dict) -> list:
    out = []
    M.build_event(rec, CFG, 1.0, [], on_window=lambda info: window(info, int(rec["event_index"]), out), with_hindsight=False)
    return out


def main() -> int:
    t0 = time.perf_counter()
    recs = C.quarantine(C.load_population()).to_dict("records")
    rows = []
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for r in ex.map(one, recs, chunksize=1):
            rows.extend(r)
    df = pd.DataFrame(rows)
    nr = CT["negative_references"]
    res = []
    for (kind, bs), g in df.groupby(["kind", "basis"]):
        for k in sorted(g["k"].unique()) + ["all"]:
            gk = g if k == "all" else g[g["k"] == k]
            z2, z4 = np.concatenate(gk["z2"].to_list()), np.concatenate(gk["z4"].to_list())
            z2, z4 = z2[np.isfinite(z2)], z4[np.isfinite(z4)]
            e = float(gk["er_rel_mean"].median())
            r = {"kind": kind, "basis": bs, "rung": str(k), "windows": int(len(gk)), "er_statistic_median": e,
                 "vz2_median": float(np.median(z2)), "vz2_sd": float(np.std(z2)), "vz4_median": float(np.median(z4)), "vz4_sd": float(np.std(z4))}
            r["pass"] = bool(nr["er_ratio_band"][0] <= e <= nr["er_ratio_band"][1] and all(abs(r[f"vz{q}_median"]) < nr["vz_abs_median_max"]
                                                                                          and nr["vz_sd_band"][0] <= r[f"vz{q}_sd"] <= nr["vz_sd_band"][1] for q in (2, 4)))
            res.append(r)
    res = pd.DataFrame(res)
    res["config_hash"] = C.cfg_hash()
    res.to_parquet(C.art("t5a_whole_pipeline_diagnosis.parquet"), index=False)
    allr = res[res["rung"] == "all"]
    summ = {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t0, 1), "events": len(recs), "draws_per_window": S,
            "pooled": allr.drop(columns=["config_hash"]).to_dict("records"),
            "passes_every_rung": {f"{kd}|{bs}": bool(res[(res["kind"] == kd) & (res["basis"] == bs) & (res["rung"] != "all")]["pass"].all())
                                  for kd in KINDS for bs in C.BASES}}
    C.write_json("t5a_summary.json", summ)
    print(allr.drop(columns=["config_hash"]).round(3).to_string())
    print(json.dumps(summ["passes_every_rung"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
