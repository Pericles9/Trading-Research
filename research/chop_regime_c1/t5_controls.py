"""
Chop regime C1, T5 (Amendment 1 re-run) -- the A1.4 controls on the 53 quarantined events with tau.

The first T5 run (commit 1be4f65) stopped on escalation row 3; its record stays in that commit. This re-run follows
Amendment 1: the variance ratio is gone (A1.1), the midpoint is primary (A1.2), the efficiency ratio's reference is the
simulated null of A1.3 (research/chop_regime_c1/nulls.py), and row 3 is split (A1.5).

Every control reads the windows the build itself computes (measures.build_event's `on_window` hook).

  negative         the A1.3 null (20 draws per window) on every window, per cell = t's segment x rung x price tier at tau
                   x basis; reported, no band (it is the reference)
  positive, trend  the same draws plus a drift of d own-noise units of the null walk, d in {1, 2, 4}; pass: in every cell
                   holding >= 20 windows, median er at d = 4 above that cell's null 95th value (midpoint and VWAP)
  sweep            the same windows at 16 and 64 buckets: medians of er (both prices) and of cost_noise_h (primary, finest
                   rung); a move of more than 20% labels the measure bucket-dependent
  blindness        every event rebuilt with trade and quote prices x 10 and x 0.1: every bp and unitless measure
                   isclose(rtol = atol = 1e-9) with NaN / inf patterns equal; separately sub-$1 prices rounded to $0.01
  agreement        Spearman of er, midpoint vs VWAP, per rung and segment
  causality, segment   measures.causality_test / segment_test, re-run

Row 3a (HARD STOP): a presence or cost measure fails blindness. Row 3b (LOG): a scale-free measure fails its positive or
blindness control -> removed from the suite's conditions, kept as a column, shown in the suite header. A relative or
context measure failing blindness is handled as 3b (config amendment_1.A1_4_controls.blindness, declared).

Writes artifacts/t5_windows.parquet, t5_cells.parquet, t5_blindness.parquet, t5_blindness_detail.parquet,
t5_basis_agreement.parquet, t5_summary.json (replacing the first run's files; that run is in git at 1be4f65).

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
import nulls as NL  # noqa: E402

B1 = C.B1
CFG = C.load_cfg()
A1 = CFG["amendment_1"]
CT = A1["A1_4_controls"]
NB = CFG["measures"]["scale_free_ladder"]["buckets"]
DRAWS = A1["A1_3_null"]["draws_per_window"]
SEED = A1["A1_3_null"]["seed"]
DRIFTS = (0.0,) + tuple(float(d) for d in CT["positive_trend"]["drift_noise_units"])
SWEEP = [b for b in CT["null_parameter_sweep"]["buckets"] if b != NB]
MIN_W = A1["A1_3_null"]["min_windows_label"]
TOL = CFG["controls"]["blindness"]["tolerance"]

PRESENCE_COST = ["trade_rate", "raw_rate", "n_rate_rungs_valid", "spread_bp_t", "spread_tw_bp", "quote_age_s"] + \
                [f"cost_noise_{h}{s}" for h in C.HORIZONS for s in ("", "_mid", "_vwap")]
SCALE_FREE = ["er", "er0", "er_rel", "er_mid", "er0_mid", "er_rel_mid", "er_vwap", "er0_vwap", "er_rel_vwap", "er_allmax", "n_valid_rungs", "finest_rung"]
REL_CONTEXT = ["turnover_rate", "n_eff", "top3_share", "move_per_trade", "act_ratio", "leg_s", "giveback", "since_high_min", "since_high_vol"] + \
              [f"{c}_{b}" for c in ("leg_s", "giveback", "since_high_min", "since_high_vol") for b in C.BASES]
SF_RUNG = ["er", "er_mid", "er0_mid", "er_rel_mid", "er_vwap", "er0_vwap", "er_rel_vwap"]
GROUP = {**{c: "presence_cost" for c in PRESENCE_COST}, **{c: "scale_free" for c in SCALE_FREE + [f"rung:{c}" for c in SF_RUNG]},
         **{c: "relative_context" for c in REL_CONTEXT}}


# ------------------------------------------------------------------ per window

def window(info: dict, tier: str, out: dict, first: list) -> None:
    j, k, seg = info["j"], info["k"], info["seg"]
    base = {"event_id": info["event_id"], "j": j, "k": k, "seg": seg, "tier": tier}
    sweep = {nb: M.bucket_path(info["v"], info["qv"], info["a"], info["t"], nb, info["geo"]) for nb in SWEEP}
    for bs in C.BASES:
        r = info["r_mid"] if bs == "mid" else info["r_vwap"]
        if r is None:
            continue
        res = NL.null_er(info, bs, DRAWS, SEED, DRIFTS, identity_check=not first[0])
        if res is None:
            continue
        first[0] = True
        st = M.scale_free(r[None, :])
        row = dict(base, basis=bs, er=float(st["er"][0]), sum_r2=float(st["sum_r2"][0]), W_min=info["bp"]["W_min"], V=info["bp"]["V"],
                   spread_bp_t=info["spread_bp_t"], v_pre=info["v_pre"], mid_ok=bool(info["bp"]["mid_ok"]),
                   null_median=float(np.nanmedian(res[0.0])) if np.isfinite(res[0.0]).any() else np.nan)
        for nb, b2 in sweep.items():
            lp = None if b2 is None else (b2["lp_mid"] if bs == "mid" else b2["lp_vwap"])
            if lp is not None:
                s2 = M.scale_free(np.diff(lp)[None, :])
                row[f"er_nb{nb}"], row[f"sum_r2_nb{nb}"] = float(s2["er"][0]), float(s2["sum_r2"][0])
        out["rows"].append(row)
        key = NL.cell_key(seg, k, tier, bs)
        for d in DRIFTS:
            out["pool"].setdefault((key, d), []).append(res[d].astype(np.float32))


def one_event(rec: dict) -> dict:
    out = {"rows": [], "pool": {}}
    first = [False]
    tier = rec["price_tier"]
    o = M.build_event(rec, CFG, 1.0, [], on_window=lambda info: window(info, tier, out, first), with_hindsight=False)
    return {"rows": out["rows"], "pool": {k: np.concatenate(v) for k, v in out["pool"].items()}, "moments": o["rows"], "sf": o["sf_rungs"]}


# ------------------------------------------------------------------ blindness

def compare(name: str, ref: pd.DataFrame, d: pd.DataFrame, cols: list, level: str, eid: str, detail: list) -> dict:
    out = {}
    for c in cols:
        if c not in ref:
            continue
        a = ref[c].astype(float).to_numpy()
        b = d[c].astype(float).to_numpy() if level == "rung" else d[c].astype(float).reindex(ref.index).to_numpy()
        if a.size != b.size:
            out[c] = {"not_close": 0, "pattern": abs(a.size - b.size), "rel_only": np.nan}
            continue
        pat = (np.isnan(a) != np.isnan(b)) | (np.isinf(a) != np.isinf(b))
        m = np.isfinite(a) & np.isfinite(b)
        nc = m & ~np.isclose(b, a, rtol=TOL, atol=TOL, equal_nan=False)
        rel = float(np.max(np.abs(a[m] - b[m]) / np.maximum(np.abs(a[m]), 1e-12))) if m.any() else 0.0
        for i in np.flatnonzero(pat | nc):
            detail.append({"event_id": eid, "factor": name, "level": level, "column": c, "group": GROUP.get(c if level == "moment" else f"rung:{c}"),
                           "row": int(i), "value_x1": float(a[i]), "value_rescaled": float(b[i])})
        out[c] = {"not_close": int(nc.sum()), "pattern": int(pat.sum()), "rel_only": rel}
    return out


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
    detail = []
    per_col = {}
    for name in ("x10", "x0.1"):
        d, dsf = runs[name]
        cm = compare(name, ref, d, PRESENCE_COST + SCALE_FREE + REL_CONTEXT, "moment", eid, detail)
        cr = compare(name, ref_sf, dsf, SF_RUNG, "rung", eid, detail) if len(ref_sf) == len(dsf) else \
            {"count": {"not_close": 0, "pattern": abs(len(ref_sf) - len(dsf)), "rel_only": np.nan}}
        for c, v in list(cm.items()) + [(f"rung:{c}", v) for c, v in cr.items()]:
            g = per_col.setdefault(c, {"not_close": 0, "pattern": 0, "rel_only": 0.0})
            g["not_close"] += v["not_close"]
            g["pattern"] += v["pattern"]
            g["rel_only"] = max(g["rel_only"], v["rel_only"]) if np.isfinite(v["rel_only"]) else g["rel_only"]
    res["per_col"] = per_col
    d, _ = runs["round"]
    for c in ("er", "er_vwap", "spread_bp_t", "cost_noise_w15", "n_valid_rungs", "trade_rate"):
        if c in ref and c in d:
            a, b = ref[c].astype(float), d[c].astype(float).reindex(ref.index)
            m = a.notna() & b.notna()
            res[f"round_{c}_median_abs_change"] = float((a[m] - b[m]).abs().median()) if m.any() else np.nan
            res[f"round_{c}_changed_share"] = float((a[m] != b[m]).mean()) if m.any() else np.nan
    res["_detail"] = detail
    return res


# ------------------------------------------------------------------ main

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

    # ---------------- negative (reported) and positive trend (gated per cell with >= MIN_W windows)
    cnt = W.groupby(["seg", "k", "tier", "basis"]).size()
    cells = []
    for (key, d) in [x for x in pool if x[1] == 0.0]:
        seg, k, tier, bs = key.split("|")
        nw = int(cnt.get((seg, int(k), tier, bs), 0))
        rec = {"cell": key, "segment": seg, "k": int(k), "tier": tier, "basis": bs, "windows": nw, **{f"null_{a}": b for a, b in NL.band(pool[(key, 0.0)]).items()}}
        for dd in DRIFTS[1:]:
            x = pool[(key, dd)].astype(np.float64)
            x = x[np.isfinite(x)]
            rec[f"median_er_d{dd:g}"] = float(np.median(x)) if x.size else np.nan
        rec["gated"] = nw >= MIN_W
        rec["pass"] = bool(rec[f"median_er_d{DRIFTS[-1]:g}"] > rec["null_p95"]) if rec["gated"] else None
        cells.append(rec)
    CEL = pd.DataFrame(cells).sort_values(["basis", "segment", "k", "tier"]).reset_index(drop=True)
    CEL["config_hash"] = C.cfg_hash()
    CEL.to_parquet(C.art("t5_cells.parquet"), index=False)
    pos = {}
    for bs in C.BASES:
        g = CEL[(CEL["basis"] == bs) & CEL["gated"]]
        pos[bs] = {"cells": int((CEL["basis"] == bs).sum()), "cells_gated": int(len(g)), "cells_failing": g.loc[~g["pass"].astype(bool), "cell"].tolist(),
                   "pass": bool(g["pass"].astype(bool).all()) if len(g) else None,
                   "cells_below_min_windows": int((~CEL.loc[CEL["basis"] == bs, "gated"]).sum())}
    rung_tab = []
    for (bs, k), g in W.groupby(["basis", "k"]):
        keys = sorted({NL.cell_key(s, k, t, bs) for s, t in zip(g["seg"], g["tier"])})
        r = {"basis": bs, "k": int(k), "windows": int(len(g)), **{f"null_{a}": b for a, b in NL.band(np.concatenate([pool[(c, 0.0)] for c in keys])).items()},
             "real_er_median": float(g["er"].median())}
        for dd in DRIFTS[1:]:
            r[f"median_er_d{dd:g}"] = float(np.nanmedian(np.concatenate([pool[(c, dd)] for c in keys]).astype(np.float64)))
        rung_tab.append(r)
    RT = pd.DataFrame(rung_tab)

    # ---------------- sweep
    sweep = {}
    for bs in C.BASES:
        g = W[W["basis"] == bs]
        sweep[f"er_{bs}"] = {"32": float(g["er"].median()), **{str(nb): float(g[f"er_nb{nb}"].median()) for nb in SWEEP}}
    Wp = W[(W["basis"] == "mid") == W["mid_ok"]]                      # each window on its primary basis (A1.2)
    fin = Wp.loc[Wp.groupby(["event_id", "j"])["k"].idxmax()]
    for h in C.HORIZONS:
        vals = {}
        for nb, col in [(16, "sum_r2_nb16"), (32, "sum_r2"), (64, "sum_r2_nb64")]:
            s2 = fin[col]
            sig = np.sqrt(s2 / fin["W_min"] * C.WALL[h]) if h in C.WALL else np.sqrt(s2 / fin["V"] * C.VOL[h] * fin["v_pre"])
            with np.errstate(divide="ignore", invalid="ignore"):
                cn = fin["spread_bp_t"] / (1e4 * sig)
            vals[str(nb)] = float(cn.replace([np.inf, -np.inf], np.nan).median())
        sweep[f"cost_noise_{h}"] = vals
    for v in sweep.values():
        for nb in SWEEP:
            v[f"rel_change_{nb}"] = (v[str(nb)] - v["32"]) / abs(v["32"]) if v["32"] else np.nan
        v["bucket_dependent"] = bool(any(abs(v[f"rel_change_{nb}"]) > CT["null_parameter_sweep"]["label_threshold_rel"] for nb in SWEEP
                                         if np.isfinite(v[f"rel_change_{nb}"])))

    # ---------------- agreement
    sfx = sf.merge(mom[["event_id", "j", "segment"]], on=["event_id", "j"], how="left")
    agree = []
    for (k, seg), g in sfx.groupby(["k", "segment"]):
        a, b = g["er_mid"], g["er_vwap"]
        m = a.notna() & b.notna()
        agree.append({"rung": int(k), "segment": seg, "n": int(m.sum()), "spearman": float(a[m].rank().corr(b[m].rank())) if m.sum() >= 3 else np.nan})
    pd.DataFrame(agree).to_parquet(C.art("t5_basis_agreement.parquet"), index=False)

    # ---------------- blindness
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        bl = list(ex.map(blind_event, recs, chunksize=1))
    det = pd.DataFrame([x for r in bl for x in r.pop("_detail")],
                       columns=["event_id", "factor", "level", "column", "group", "row", "value_x1", "value_rescaled"])
    det.to_parquet(C.art("t5_blindness_detail.parquet"), index=False)
    per_col = {}
    for r in bl:
        for c, v in r.pop("per_col").items():
            g = per_col.setdefault(c, {"not_close": 0, "pattern": 0, "rel_only": 0.0})
            g["not_close"] += v["not_close"]
            g["pattern"] += v["pattern"]
            g["rel_only"] = max(g["rel_only"], v["rel_only"])
    BLd = pd.DataFrame(bl)
    BLd["config_hash"] = C.cfg_hash()
    BLd.to_parquet(C.art("t5_blindness.parquet"), index=False)
    failing_cols = {c: v for c, v in per_col.items() if v["not_close"] or v["pattern"]}
    by_group = {g: sorted(c for c in failing_cols if GROUP.get(c) == g) for g in ("presence_cost", "scale_free", "relative_context")}
    tests = {"causality": M.causality_test(), "segment": M.segment_test(), "bucket_equality": M.bucket_equality_test(100)}

    # ---------------- escalation
    row3a = bool(by_group["presence_cost"])
    removed = {}
    if pos["mid"]["pass"] is False:
        removed["er"] = "positive control (midpoint) fails in cells " + ", ".join(pos["mid"]["cells_failing"])
    if by_group["scale_free"]:
        removed["er"] = (removed["er"] + "; " if "er" in removed else "") + "blindness: " + ", ".join(by_group["scale_free"])
    for c in by_group["relative_context"]:
        removed[c] = "blindness (handled as 3b, declared)"
    summary = {
        "config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "events": len(recs),
        "windows_by_basis": W["basis"].value_counts().to_dict(), "cells": int(len(CEL)), "draws_per_window": DRAWS,
        "negative_reported": "t5_cells.parquet: null median, 5th, 95th per cell",
        "positive_trend": pos, "per_rung": RT.to_dict("records"),
        "sweep": sweep, "blindness": {"rule": CFG["controls"]["blindness"]["tolerance_rule"], "columns_failing": failing_cols, "by_group": by_group,
                                      "detail_rows": int(len(det)), "events_with_sub_dollar_prints": int((BLd["sub_dollar_share"] > 0).sum())},
        "tests": tests,
        "escalation": {"row1_causality_fires": not tests["causality"]["passes"], "row2_segment_fires": not tests["segment"]["passes"],
                       "row3a_fires": row3a, "row3b_removed": removed},
        "ar1_retired_values": {"mid": [2.443, -2.294], "vwap": [2.486, -2.348], "source": "first T5 run, commit 1be4f65, t5_summary.json"},
    }
    C.write_json("t5_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("positive_trend", "escalation", "sweep")}, indent=1, default=str))
    print(json.dumps(summary["blindness"], indent=1, default=str)[:3000])
    print(RT.round(3).to_string())
    if summary["escalation"]["row1_causality_fires"] or summary["escalation"]["row2_segment_fires"]:
        print("HARD STOP row 1/2")
        return 2
    if row3a:
        print(f"HARD STOP row 3a: presence or cost measure fails blindness: {by_group['presence_cost']}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
