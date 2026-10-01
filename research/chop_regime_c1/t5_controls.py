"""
Chop regime C1, T5 -- the section 6 controls on the 53 quarantined events with tau, and the primary-price ruling.

Every control reads the windows the build itself computes: measures.build_event walks each event's moments and calls
`on_window` for every valid scale-free window (>= 64 collapsed trades, 32 buckets), handing over the sliced tape and
quote book, the bucket paths and the 32 returns on both prices. Nothing below re-derives a window.

  negative, references       200 seeded resamples (with replacement) of the window's own demeaned returns, per basis
  negative, whole pipeline   20 seeded shuffles per window: VWAP -- the window's print-to-print log returns shuffled and
                             re-integrated with every print's time and size kept, then bucketed by measures.buckets_core;
                             midpoint -- the window's quote-update log midpoint changes (from the midpoint prevailing at
                             the first print) shuffled, re-integrated with the quote times kept, sampled at the first print
                             and each bucket's last print
  positive, trend            50 resamples + a drift of d own-noise units across the window, d in {1, 2, 4}
  positive, autocorrelation  50 resamples through AR(1), phi = +0.5 and -0.5; edge of detectability phi = +-0.25, d = 1
  null-parameter sweep       the same windows at 16 and 64 buckets
  blindness                  every event rebuilt with trade and quote prices x 10 and x 0.1; separately sub-$1 prices
                             rounded to the $0.01 grid
  price-basis agreement      Spearman of vz2 and er_rel, midpoint vs VWAP, per rung and segment
  causality, segment         measures.causality_test / segment_test

The ruling table (config controls.primary_basis_ruling) picks the primary price from the whole-pipeline control; the
reference and positive controls are gated on every basis the ruling keeps. Any gated miss is a HARD STOP (row 3).

Writes artifacts/t5_windows.parquet (per window x basis), t5_pooled.parquet (per control x basis x rung), t5_blindness.parquet,
t5_summary.json (the control table and the ruling).

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t5_controls.py
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

B1 = C.B1
CFG = C.load_cfg()
CT = CFG["controls"]
NB = CFG["measures"]["scale_free_ladder"]["buckets"]
BASIS_CODE = {"mid": 0, "vwap": 1}
SQ = M.SQ2PI


def er_rel_of(R: np.ndarray) -> np.ndarray:
    return M.scale_free(R)["er_rel"]


def resample(d: np.ndarray, rng, n_draw: int) -> np.ndarray:
    return d[rng.integers(0, d.size, size=(n_draw, d.size))]


def ar1(E: np.ndarray, phi: float) -> np.ndarray:
    X = np.empty_like(E)
    X[:, 0] = E[:, 0]
    for i in range(1, E.shape[1]):
        X[:, i] = phi * X[:, i - 1] + E[:, i]
    return X


class Acc:
    def __init__(self):
        self.rows = []
        self.pool = {}

    def add(self, key, arr):
        self.pool.setdefault(key, []).append(np.asarray(arr, dtype=np.float32))


def window_controls(info: dict, eidx: int, acc: Acc) -> None:
    j, k = info["j"], info["k"]
    seed = CT["seed"]
    bp, v, qv = info["bp"], info["v"], info["qv"]
    lo, hi = bp["lo"], bp["hi"]
    ts, px, sz = v["ts"][lo:hi], v["px"][lo:hi], v["sz"][lo:hi]
    cv_end = np.cumsum(sz)
    base = {"event_id": info["event_id"], "j": j, "k": k, "seg": info["seg"], "W_s": info["W_s"], "n_prints": int(hi - lo)}
    # ---------------- sweep: the same window at 16 and 64 buckets (real data)
    sweep = {}
    for nb in CT["null_parameter_sweep"]["buckets"]:
        if nb == NB:
            continue
        b2 = M.bucket_path(v, qv, info["a"], info["t"], nb, info["geo"])
        sweep[nb] = b2
    for bs in C.BASES:
        r = info["r_mid"] if bs == "mid" else info["r_vwap"]
        if r is None or not np.isfinite(r).all():
            continue
        rng = np.random.default_rng([seed, eidx, j, k, BASIS_CODE[bs]])
        row = dict(base, basis=bs)
        st = M.scale_free(r[None, :])
        row.update({"er_rel": float(st["er_rel"][0]), "vz2": float(st["vz2"][0]), "vz4": float(st["vz4"][0]), "sum_r2": float(st["sum_r2"][0]),
                    "W_min": bp["W_min"], "V": bp["V"]})
        d = r - r.mean()
        s, mad = float(np.sqrt((d * d).mean())), float(np.abs(d).mean())
        er0 = SQ / np.sqrt(r.size) * s / mad if mad > 0 else np.nan
        # ---------------- negative: the references
        Rs = resample(d, rng, CT["negative_references"]["resamples_per_window"])
        sr = M.scale_free(Rs)
        row["ref_er_ratio"] = float(np.nanmean(sr["er"]) / er0) if np.isfinite(er0) else np.nan
        acc.add((bs, "ref_vz2", k), sr["vz2"][np.isfinite(sr["vz2"])])            # float32 storage; pooled sd in float64
        acc.add((bs, "ref_vz4", k), sr["vz4"][np.isfinite(sr["vz4"])])
        # ---------------- positive: trend and autocorrelation (+ edge)
        n_pos = CT["positive_trend"]["resamples_per_window"]
        E = resample(d, rng, n_pos)
        for dd in sorted(set(CT["positive_trend"]["drift_noise_units"]) | {CT["edge_of_detectability"]["drift"]}):
            x = er_rel_of(E + dd * s / np.sqrt(r.size))
            acc.add((bs, f"trend_d{dd}", k), x[np.isfinite(x)])
        for phi in sorted(set(CT["positive_autocorrelation"]["phi"]) | set(CT["edge_of_detectability"]["phi"])):
            z = M.scale_free(ar1(E, phi))["vz2"]
            acc.add((bs, f"ar_{phi:+.2f}", k), z[np.isfinite(z)])
        # ---------------- negative: the whole pipeline
        S = CT["negative_whole_pipeline"]["shuffles_per_window"]
        Rw = None
        if bs == "vwap":
            dl = np.diff(np.log(px))
            if dl.size >= 1:
                # measures.vwap_log_path, vectorised over the shuffles: the owners depend on volume only; the value sums
                # run on each synthetic print's deviation from the synthetic first print with volume
                sh = np.r_[dl[None, :], rng.permuted(np.tile(dl, (S, 1)), axis=1)]           # row 0: the identity (wiring check)
                syn = np.c_[np.zeros(S + 1), np.cumsum(sh, axis=1)]                               # log price - log px[0]
                b = M.buckets_core(ts, px, cv_end, np.cumsum(px * sz), NB)
                own, first = b["own"], b["first"]
                dev = np.expm1(syn - syn[:, [first]])
                cd = np.cumsum(dev * sz[None, :], axis=1)
                E_ = np.arange(1, NB + 1, dtype=np.float64) * (b["V"] / NB)
                E_[-1] = b["V"]
                F = cd[:, own] - (cv_end[own] - E_)[None, :] * dev[:, own]
                u = np.diff(np.c_[np.zeros(S + 1), F], axis=1) / (b["V"] / NB)
                Rw = np.diff(np.log1p(np.c_[dev[:, first], u]), axis=1)
                assert np.allclose(Rw[0], r, rtol=1e-7, atol=1e-10), "whole-pipeline VWAP identity differs from the build's returns"
                Rw = Rw[1:]
        else:
            vts, vlm = qv["vts"], qv["vlogmid"]
            i0 = int(np.searchsorted(vts, bp["t_first"], "right")) - 1
            if i0 >= 0:
                dm = np.diff(vlm[i0:])
                times = np.r_[bp["t_first"], bp["t_end"]]
                idx = np.searchsorted(vts, times, "right") - 1 - i0
                if dm.size >= 1:
                    sh = np.r_[dm[None, :], rng.permuted(np.tile(dm, (S, 1)), axis=1)]        # row 0: the identity (wiring check)
                    path = vlm[i0] + np.c_[np.zeros(S + 1), np.cumsum(sh, axis=1)]
                else:
                    path = np.full((S + 1, 1), vlm[i0])
                Rw = np.diff(path[:, idx], axis=1)
                assert np.allclose(Rw[0], r, rtol=1e-7, atol=1e-10), "whole-pipeline midpoint identity differs from the build's returns"
                Rw = Rw[1:]
        if Rw is not None:
            sw = M.scale_free(Rw)
            er = sw["er_rel"][np.isfinite(sw["er_rel"])]
            row["wp_er_rel_mean"] = float(er.mean()) if er.size else np.nan
            acc.add((bs, "wp_vz2", k), sw["vz2"][np.isfinite(sw["vz2"])])
            acc.add((bs, "wp_vz4", k), sw["vz4"][np.isfinite(sw["vz4"])])
        # ---------------- sweep values on real data
        for nb, b2 in sweep.items():
            if b2 is None:
                continue
            lp2 = b2["lp_mid"] if bs == "mid" else b2["lp_vwap"]
            if lp2 is None:
                continue
            s2 = M.scale_free(np.diff(lp2)[None, :])
            row[f"er_rel_nb{nb}"], row[f"vz2_nb{nb}"], row[f"sum_r2_nb{nb}"] = float(s2["er_rel"][0]), float(s2["vz2"][0]), float(s2["sum_r2"][0])
        row["spread_bp_t"], row["v_pre"] = info["spread_bp_t"], info["v_pre"]
        acc.rows.append(row)


def one_event(rec: dict) -> dict:
    acc = Acc()
    eidx = int(rec["event_index"])
    halts = []
    out = M.build_event(rec, CFG, 1.0, halts, on_window=lambda info: window_controls(info, eidx, acc), with_hindsight=False)
    return {"rows": acc.rows, "pool": {k: np.concatenate(v) if v else np.zeros(0, np.float32) for k, v in acc.pool.items()},
            "moments": out["rows"], "sf": out["sf_rungs"]}


# ------------------------------------------------------------------ blindness

INVARIANT = ["spread_bp_t", "quote_age_s", "trade_rate", "turnover_rate", "n_eff", "top3_share", "move_per_trade", "spread_tw_bp", "act_ratio",
             "n_valid_rungs", "finest_rung", "n_rate_rungs_valid"] + [f"{c}_{b}" for b in C.BASES for c in
                                                                        ("er", "er0", "er_rel", "vr2", "vr4", "vz2", "vz4", "leg_s", "giveback")] + \
            [f"cost_noise_{h}_{b}" for h in C.HORIZONS for b in C.BASES]
TOL = CT["blindness"]["tolerance"]
INV_SF = [f"{c}_{b}" for b in C.BASES for c in ("er", "er0", "er_rel", "vr2", "vr4", "vz2", "vz4")]


def blind_event(rec: dict) -> dict:
    eid, date = rec["event_id"], rec["event_date_canonical"]
    tr = B1.read_trades(eid, with_conditions=False)
    q = C.read_quotes(eid)
    runs = {}
    for name, f in (("x1", None), ("x10", 10.0), ("x0.1", 0.1), ("round", "round")):
        t2, q2 = dict(tr), None if q is None else dict(q)
        if f == "round":
            t2["px"] = np.where(tr["px"] < 1.0, np.round(tr["px"], 2), tr["px"])
            if q2 is not None:
                q2["bid"] = np.where(q["bid"] < 1.0, np.round(q["bid"], 2), q["bid"])
                q2["ask"] = np.where(q["ask"] < 1.0, np.round(q["ask"], 2), q["ask"])
        elif f is not None:
            t2["px"] = tr["px"] * f
            if q2 is not None:
                q2["bid"], q2["ask"] = q["bid"] * f, q["ask"] * f
        o = M.build_event(rec, CFG, 1.0, [], tape=C.Tape(eid, date, tr=t2), quotes=q2, with_hindsight=False)
        runs[name] = (pd.DataFrame(o["rows"]).set_index("j"), pd.DataFrame(o["sf_rungs"]))
    ref, ref_sf = runs["x1"]
    res = {"event_id": eid, "sub_dollar_share": float((tr["px"] < 1.0).mean())}
    for name in ("x10", "x0.1"):
        d, dsf = runs[name]
        worst, worst_col, n_not_close, nan_mismatch = 0.0, None, 0, 0
        pairs = [(c, ref[c].astype(float).to_numpy(), d[c].astype(float).reindex(ref.index).to_numpy()) for c in INVARIANT if c in ref]
        if len(ref_sf) == len(dsf):
            pairs += [(c, ref_sf[c].to_numpy(float), dsf[c].to_numpy(float)) for c in INV_SF if len(ref_sf)]
        else:
            nan_mismatch += abs(len(ref_sf) - len(dsf))
        for c, a, b in pairs:
            nan_mismatch += int((np.isnan(a) != np.isnan(b)).sum()) + int((np.isinf(a) != np.isinf(b)).sum())
            m = np.isfinite(a) & np.isfinite(b)
            if m.any():
                rel = np.abs(a[m] - b[m]) / np.maximum(np.abs(a[m]), 1e-12)
                if rel.max() > worst:
                    worst, worst_col = float(rel.max()), c
                n_not_close += int((~np.isclose(b[m], a[m], rtol=TOL, atol=TOL)).sum())
        res[f"{name}_max_rel_diff_relative_only"] = worst
        res[f"{name}_worst_column"] = worst_col
        res[f"{name}_values_not_close"] = n_not_close
        res[f"{name}_nan_pattern_mismatches"] = nan_mismatch
    d, _ = runs["round"]
    for c in ("er_rel_mid", "er_rel_vwap", "vz2_mid", "vz2_vwap", "spread_bp_t", "cost_noise_w15_mid", "n_valid_rungs"):
        if c in ref and c in d:
            a, b = ref[c].astype(float), d[c].astype(float).reindex(ref.index)
            m = a.notna() & b.notna()
            res[f"round_{c}_median_abs_change"] = float((a[m] - b[m]).abs().median()) if m.any() else np.nan
            res[f"round_{c}_changed_share"] = float((a[m] != b[m]).mean()) if m.any() else np.nan
    return res


# ------------------------------------------------------------------ main

def band(x, lo, hi):
    return bool(np.isfinite(x) and lo <= x <= hi)


def main() -> int:
    t_start = time.perf_counter()
    pop = C.load_population()
    qu = C.quarantine(pop)
    recs = qu.to_dict("records")
    rows, pool, moments, sfs = [], {}, [], []
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for n, r in enumerate(ex.map(one_event, recs, chunksize=1)):
            rows.extend(r["rows"])
            moments.extend(r["moments"])
            sfs.extend(r["sf"])
            for kk, vv in r["pool"].items():
                pool.setdefault(kk, []).append(vv)
            print(f"  controls {n + 1}/{len(recs)}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    pool = {k: np.concatenate(v) for k, v in pool.items()}
    W = pd.DataFrame(rows)
    W["config_hash"] = C.cfg_hash()
    W.to_parquet(C.art("t5_windows.parquet"), index=False, compression="zstd")
    mom = pd.DataFrame(moments)
    sf = pd.DataFrame(sfs)

    nr, nw = CT["negative_references"], CT["negative_whole_pipeline"]
    rungs = sorted(W["k"].unique())
    pooled = []

    def zstats(key):
        x = pool.get(key, np.zeros(0)).astype(np.float64)
        return {"n": int(x.size), "median": float(np.median(x)) if x.size else np.nan, "sd": float(np.std(x)) if x.size else np.nan}

    table = {}
    for bs in C.BASES:
        wb = W[W["basis"] == bs]
        # references and whole pipeline, per rung and pooled
        for ctl, er_col, zkey in (("references", "ref_er_ratio", "ref"), ("whole_pipeline", "wp_er_rel_mean", "wp")):
            per = []
            for k in rungs + ["all"]:
                wk = wb if k == "all" else wb[wb["k"] == k]
                er = wk[er_col].dropna()
                if k == "all":
                    z2 = np.concatenate([pool.get((bs, f"{zkey}_vz2", kk), np.zeros(0)) for kk in rungs]).astype(np.float64)
                    z4 = np.concatenate([pool.get((bs, f"{zkey}_vz4", kk), np.zeros(0)) for kk in rungs]).astype(np.float64)
                    s2 = {"n": int(z2.size), "median": float(np.median(z2)) if z2.size else np.nan, "sd": float(np.std(z2)) if z2.size else np.nan}
                    s4 = {"n": int(z4.size), "median": float(np.median(z4)) if z4.size else np.nan, "sd": float(np.std(z4)) if z4.size else np.nan}
                else:
                    s2, s4 = zstats((bs, f"{zkey}_vz2", k)), zstats((bs, f"{zkey}_vz4", k))
                er_med = float(er.median()) if len(er) else np.nan
                ok_er = band(er_med, *nr["er_ratio_band"]) if len(er) else True
                ok_z = all((s["n"] == 0) or (abs(s["median"]) < nr["vz_abs_median_max"] and band(s["sd"], *nr["vz_sd_band"])) for s in (s2, s4))
                rec = {"control": ctl, "basis": bs, "rung": str(k), "windows": int(len(er)), "er_statistic_median": er_med,
                       "vz2_n": s2["n"], "vz2_median": s2["median"], "vz2_sd": s2["sd"], "vz4_n": s4["n"], "vz4_median": s4["median"], "vz4_sd": s4["sd"],
                       "pass_er": ok_er, "pass_vz": ok_z, "pass": bool(ok_er and ok_z)}
                per.append(rec)
                pooled.append(rec)
            table[f"{ctl}|{bs}"] = {"pass": all(r["pass"] for r in per if r["rung"] != "all"), "failing_rungs": [r["rung"] for r in per if r["rung"] != "all" and not r["pass"]],
                                    "all_rungs": [r for r in per if r["rung"] == "all"][0]}
        # positive: trend, autocorrelation, edge
        tr = {}
        for dd in sorted(set(CT["positive_trend"]["drift_noise_units"]) | {CT["edge_of_detectability"]["drift"]}):
            x = np.concatenate([pool.get((bs, f"trend_d{dd}", kk), np.zeros(0)) for kk in rungs])
            tr[dd] = float(np.median(x)) if x.size else np.nan
            per_rung = {str(kk): float(np.median(pool[(bs, f"trend_d{dd}", kk)])) for kk in rungs if (bs, f"trend_d{dd}", kk) in pool and pool[(bs, f"trend_d{dd}", kk)].size}
            pooled.append({"control": f"trend_d{dd}", "basis": bs, "rung": "all", "windows": int(x.size), "er_statistic_median": tr[dd], "per_rung": json.dumps(per_rung)})
        ds = CT["positive_trend"]["drift_noise_units"]
        trend_ok = all(tr[ds[i]] < tr[ds[i + 1]] for i in range(len(ds) - 1)) and tr[4] > 2.0
        table[f"positive_trend|{bs}"] = {"pass": bool(trend_ok), "median_er_rel_by_d": {str(k): v for k, v in tr.items()}}
        ar = {}
        for phi in sorted(set(CT["positive_autocorrelation"]["phi"]) | set(CT["edge_of_detectability"]["phi"])):
            x = np.concatenate([pool.get((bs, f"ar_{phi:+.2f}", kk), np.zeros(0)) for kk in rungs])
            ar[phi] = float(np.median(x)) if x.size else np.nan
            per_rung = {str(kk): float(np.median(pool[(bs, f"ar_{phi:+.2f}", kk)])) for kk in rungs if (bs, f"ar_{phi:+.2f}", kk) in pool and pool[(bs, f"ar_{phi:+.2f}", kk)].size}
            pooled.append({"control": f"ar_{phi:+.2f}", "basis": bs, "rung": "all", "windows": int(x.size), "vz2_median": ar[phi], "per_rung": json.dumps(per_rung)})
        table[f"positive_autocorrelation|{bs}"] = {"pass": bool(ar[0.5] >= 1.64 and ar[-0.5] <= -1.64), "median_vz2_by_phi": {f"{k:+.2f}": v for k, v in ar.items()}}
        table[f"edge_of_detectability|{bs}"] = {"report_only": True, "median_vz2_phi_+0.25": ar[0.25], "median_vz2_phi_-0.25": ar[-0.25], "median_er_rel_d1": tr[1]}
        # null-parameter sweep: medians per setting; cost_noise on the finest rung
        sw = {}
        for c in ("er_rel", "vz2"):
            m32 = float(wb[c].median())
            sw[c] = {"32": m32}
            for nb in (16, 64):
                mm = float(wb[f"{c}_nb{nb}"].median()) if f"{c}_nb{nb}" in wb else np.nan
                sw[c][str(nb)] = mm
                sw[c][f"rel_change_{nb}"] = (mm - m32) / abs(m32) if m32 != 0 else np.nan
                sw[c][f"abs_change_{nb}"] = mm - m32
            sw[c]["bucket_dependent"] = bool(any(abs(sw[c][f"rel_change_{nb}"]) > CT["null_parameter_sweep"]["label_threshold_rel"] for nb in (16, 64)
                                                 if np.isfinite(sw[c][f"rel_change_{nb}"])))
        fin = wb.loc[wb.groupby(["event_id", "j"])["k"].idxmax()]
        for h in C.HORIZONS:
            vals = {}
            for nb, col in ((16, "sum_r2_nb16"), (32, "sum_r2"), (64, "sum_r2_nb64")):
                s2 = fin[col]
                if h in C.WALL:
                    sig = np.sqrt(s2 / fin["W_min"] * C.WALL[h])
                else:
                    sig = np.sqrt(s2 / fin["V"] * C.VOL[h] * fin["v_pre"])
                cn = fin["spread_bp_t"] / (1e4 * sig)
                vals[str(nb)] = float(cn.replace([np.inf, -np.inf], np.nan).median())
            m32 = vals["32"]
            vals["rel_change_16"], vals["rel_change_64"] = (vals["16"] - m32) / m32, (vals["64"] - m32) / m32
            vals["bucket_dependent"] = bool(abs(vals["rel_change_16"]) > 0.2 or abs(vals["rel_change_64"]) > 0.2)
            sw[f"cost_noise_{h}"] = vals
        table[f"null_parameter_sweep|{bs}"] = {"report_only": True, **sw}
        # price-basis agreement (T5 part; the development slice's in T6)
    agree = []
    sfx = sf.merge(mom[["event_id", "j", "segment"]], on=["event_id", "j"], how="left")
    for (k, seg), g in sfx.groupby(["k", "segment"]):
        for c in ("vz2", "er_rel"):
            a, b = g[f"{c}_mid"], g[f"{c}_vwap"]
            m = a.notna() & b.notna()
            agree.append({"rung": int(k), "segment": seg, "measure": c, "n": int(m.sum()),
                          "spearman": float(a[m].rank().corr(b[m].rank())) if m.sum() >= 3 else np.nan})
    agree = pd.DataFrame(agree)

    # ---------------- the ruling
    wp_mid, wp_vwap = table["whole_pipeline|mid"]["pass"], table["whole_pipeline|vwap"]["pass"]
    if wp_mid and wp_vwap:
        primary, kept, ruling = "mid", ["mid", "vwap"], "mid_pass_vwap_pass"
    elif wp_mid:
        primary, kept, ruling = "mid", ["mid"], "mid_pass_vwap_fail"
    elif wp_vwap:
        primary, kept, ruling = "vwap", ["vwap"], "mid_fail_vwap_pass"
    else:
        primary, kept, ruling = None, [], "both_fail"
    gated = {f"whole_pipeline|{b}": table[f"whole_pipeline|{b}"]["pass"] for b in kept}
    for b in kept:
        for ctl in ("references", "positive_trend", "positive_autocorrelation"):
            gated[f"{ctl}|{b}"] = table[f"{ctl}|{b}"]["pass"]

    # ---------------- blindness
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        bl = pd.DataFrame(list(ex.map(blind_event, recs, chunksize=1)))
    bl["config_hash"] = C.cfg_hash()
    bl.to_parquet(C.art("t5_blindness.parquet"), index=False)
    blind_ok = bool(bl[["x10_values_not_close", "x0.1_values_not_close", "x10_nan_pattern_mismatches", "x0.1_nan_pattern_mismatches"]].sum().sum() == 0)
    gated["blindness"] = blind_ok
    tests = {"causality": M.causality_test(), "segment": M.segment_test()}
    gated["causality"], gated["segment"] = tests["causality"]["passes"], tests["segment"]["passes"]

    pd.DataFrame(pooled).to_parquet(C.art("t5_pooled.parquet"), index=False)
    agree.to_parquet(C.art("t5_basis_agreement.parquet"), index=False)
    hard_stop = (primary is None) or not all(gated.values())
    summary = {"config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "events": int(len(recs)),
               "windows_by_basis": W["basis"].value_counts().to_dict(), "windows_by_rung": W[W["basis"] == "vwap"]["k"].value_counts().sort_index().to_dict(),
               "moments": int(len(mom)), "table": table, "ruling": {"case": ruling, "primary": primary, "kept": kept,
                                                                  "whole_pipeline_mid_pass": wp_mid, "whole_pipeline_vwap_pass": wp_vwap},
               "gated": gated, "blindness": {"passes": blind_ok, "rule": CT["blindness"]["tolerance_rule"],
                                             "values_not_close": int(bl[["x10_values_not_close", "x0.1_values_not_close"]].sum().sum()),
                                             "x10_max_rel_diff_relative_only": float(bl["x10_max_rel_diff_relative_only"].max()),
                                             "x0.1_max_rel_diff_relative_only": float(bl["x0.1_max_rel_diff_relative_only"].max()),
                                             "nan_pattern_mismatches": int(bl[["x10_nan_pattern_mismatches", "x0.1_nan_pattern_mismatches"]].sum().sum()),
                                             "events_with_sub_dollar_prints": int((bl["sub_dollar_share"] > 0).sum())},
               "tests": tests, "hard_stop_row3": bool(hard_stop)}
    C.write_json("t5_summary.json", summary)
    print(json.dumps({"ruling": summary["ruling"], "gated": gated, "blindness": summary["blindness"]}, indent=1, default=str))
    for k2, v2 in table.items():
        print(k2, json.dumps(v2, default=str)[:600])
    if hard_stop:
        print("HARD STOP row 3: a section 6 control misses its pass band")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
