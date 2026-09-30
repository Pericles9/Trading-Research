"""
Shape classifier S2, T2 -- the decision times, Group B (the path since tau) and Group C (atlas matching).

One tick pass over the population. Per event:
  decision times   tau; tau + 1, 2, 5, 10, 20 min (not_reached past 20:00); the four volume checkpoints (the first
                   print after tau at which shares since tau reach 0.25/0.5/1/2 x ref_shares; not_reached if never
                   before 20:00; undefined where ref_shares is undefined, i.e. tau in an auction minute)
  Group B          at each reached checkpoint after tau, from the prints with tau < ts <= d ONLY (the arrays are
                   sliced to ts <= d before any feature is computed); spike rule per config (confirmed by d)
  tcs_state        R1: tau_close_sensitive as far as it is settled at d
  forward returns  from every reached decision time: entry at the first print after d (and >= d + 1 s, d + 5 s),
                   exit at the last print <= d + 10 / 30 / 60 min and <= 20:00 (gross; costs applied in T6)
  master path      x(t) = log(last print <= tau + t / tau price) on the master grid (Group C and M4; cache)
  tau confirmation the gap from the tau print to its successor (the spike guard reads it; documented in T0)

Then Group C: per fold and stage (tune: typical paths from the sub-train years; final: from all training years),
each type's typical path = pointwise median of its training events' master paths; each event's distance to each
typical path at each checkpoint after tau = RMS over the 20 query points t_g = E (g + 1) / 20.

Writes artifacts/t2_checkpoints.parquet (event x decision time), t2_forward.parquet (forward returns), t2_group_c.parquet, t2_typical_paths.parquet,
t2_event_meta.parquet (tau confirmation lag, the day's last print), t2_summary.json; cache/master_paths.npy + cache/master_paths_events.parquet (rebuildable, not committed).

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t2_checkpoints.py
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
import s2common as S  # noqa: E402

C1 = S.C1
CFG = S.load_cfg()
TOL_MS = 10.0
GRID = S.master_grid_s()
GRID_NS = GRID * S.NS
LAT = {"lat0": None, "lat1s": 1 * S.NS, "lat5s": 5 * S.NS}
HOR = {"h10": 600 * S.NS, "h30": 1800 * S.NS, "h60": 3600 * S.NS, "to2000": None}
RV_STEP = 5 * S.NS
HALT_GAP = 300 * S.NS
CFG_B1 = json.load(open(S.REPO / "config/attention_excursion_b1.json"))["t2_tau"]
MB_CLOSE = "results/relative_momentum/r0/artifacts/t0a2_prior_close.parquet"     # b1's minute-bar close (common.MB_CLOSE)


def group_b(ts, px, sz, ct, spk, tau, p_tau, d, pre_tr, pre_dl, sigma_pre, ref, op, cl) -> dict:
    """Group B at decision time d from the post-tau prints (ts > tau). Every array is cut to ts <= d here, so
    nothing after d can enter."""
    j = int(np.searchsorted(ts, d, "right"))
    ts, px, sz = ts[:j], px[:j], sz[:j]
    assert ts.size == 0 or ts[-1] <= d
    ct = ct[: int(np.searchsorted(ct, d, "right"))]
    E = d - tau
    E_min = max(E, S.NS) / S.MIN_NS
    keep = ~spk[:j].copy()
    if j:
        keep[-1] = True                                 # the last print cannot be confirmed as a spike by d
    kt, kp = ts[keep], px[keep]
    lp_tau = np.log(p_tau)
    lp = np.log(kp) if kp.size else np.zeros(0)
    ret = float(lp[-1] - lp_tau) if lp.size else 0.0
    if lp.size and lp.max() > lp_tau:
        i_hi = int(np.argmax(lp))
        high, t_hi = float(lp[i_hi] - lp_tau), int(kt[i_hi])
    else:
        high, t_hi = 0.0, tau
    n = int(ct.size)
    mid = tau + E // 2
    n1 = int(np.searchsorted(ct, mid, "right"))
    n2 = n - n1
    dollars = float((px * sz).sum())
    shares = float(sz.sum())
    # 5 s grid of the last kept price, from tau to d
    g = np.r_[tau + RV_STEP * np.arange(1, int(E // RV_STEP) + 1), d]
    g = g[g <= d]
    gi = np.searchsorted(kt, g, "right") - 1
    gp = np.where(gi >= 0, np.log(kp[np.maximum(gi, 0)]) if kp.size else lp_tau, lp_tau)
    rv = float(np.sqrt(np.sum(np.diff(np.r_[lp_tau, gp]) ** 2)))
    times = np.r_[tau, ts, d]
    gaps = np.diff(times)
    rth_gap = (times[:-1] >= op) & (times[1:] <= cl) & (gaps >= HALT_GAP)
    tr_rate = (n + 0.5) / E_min
    dl_rate = (dollars + 1.0) / E_min
    scale = sigma_pre * np.sqrt(E_min) if np.isfinite(sigma_pre) and sigma_pre > 0 else np.nan
    out = {"elapsed_min": E / S.MIN_NS, "ret_log": ret, "high_log": high, "dd_log": high - ret,
           "u_high": (t_hi - tau) / E if E > 0 else 0.0,
           "log10_post_trades_per_min": np.log10(tr_rate), "log10_post_dollars_per_min": np.log10(dl_rate),
           "lr_trade_rate": np.log(tr_rate / pre_tr) if pre_tr > 0 else np.nan,
           "lr_dollar_rate": np.log(dl_rate / pre_dl) if pre_dl > 0 else np.nan,
           "accel_post": float(np.log((n2 + 0.5) / (n1 + 0.5))), "rv_post": rv,
           "max_gap_s": float(gaps.max()) / S.NS, "since_last_print_s": float(d - (ts[-1] if ts.size else tau)) / S.NS,
           "gap_halt_proxy": bool(rth_gap.any()),
           "vol_progress": np.log10(max(shares, 1.0) / ref) if np.isfinite(ref) and ref > 0 else np.nan,
           "z_ret": ret / scale, "z_high": high / scale, "z_dd": (high - ret) / scale, "rv_ratio": rv / scale,
           "n_post_prints": int(ts.size), "shares_since_tau": shares,
           "ts__B": int(max(ts[-1], tau)) if ts.size else tau}
    return out


def forward(ts, px, d, t2000) -> dict:
    """Gross forward returns from decision time d (all prints of the day after tau; long side)."""
    out = {}
    for ln, lag in LAT.items():
        e = int(np.searchsorted(ts, d, "right")) if lag is None else int(np.searchsorted(ts, d + lag, "left"))
        if e >= ts.size or ts[e] > t2000:
            for h in HOR:
                out[f"fr_{ln}_{h}_state"] = "no_entry"
            continue
        pe, te = px[e], ts[e]
        out[f"entry_{ln}_ns"] = int(te)
        for h, hv in HOR.items():
            end = t2000 if hv is None else d + hv
            if end > t2000:
                out[f"fr_{ln}_{h}_state"] = "horizon_past_2000"
                continue
            x = int(np.searchsorted(ts, end, "right")) - 1
            if x < e:
                out[f"fr_{ln}_{h}_state"] = "no_print_in_horizon"
                continue
            out[f"fr_{ln}_{h}_state"] = "ok"
            out[f"fr_{ln}_{h}_gross_bp"] = (px[x] / pe - 1.0) * 1e4
            out[f"fr_{ln}_{h}_gross_cents"] = (px[x] - pe) * 100.0
            out[f"fr_{ln}_{h}_entry_px"] = pe
    return out


def one(rec: dict):
    tr = C1.read_trades(rec["event_id"], with_conditions=False)
    date, tau, p_tau = rec["event_date_canonical"], int(rec["tau_d_ns"]), float(rec["tau_price"])     # tau = tau_d
    t0400, t2000 = C1.et_ns(date, "04:00:00"), C1.et_ns(date, "20:00:00")
    a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
    # the minute-bar-close crossing print, exactly as b1 computed it (first_crossing, 1.30 x the minute-bar close,
    # spike guard 3% / 3%) on the FULL arrays with lo / hi = the 04:00 / 20:00 indices, so the 04:00 print is judged
    # against its predecessor (Amendment 1 A1.2) -- a future event for most decision times; only its having
    # happened by d is ever used
    mb = rec["mb_close"]
    i_mb = C1.first_crossing(tr["px"], a, b, CFG_B1["crossing_multiple"] * mb, CFG_B1["spike_guard"]["deviation_threshold"],
                             CFG_B1["spike_guard"]["neighbour_agreement"])[0] if pd.notna(mb) and mb > 0 else None
    tau_mb_x = int(tr["ts"][i_mb]) if i_mb is not None else None
    ts, px, sz = tr["ts"][a:b].copy(), tr["px"][a:b].copy(), tr["sz"][a:b].copy()
    del tr
    op, cl = C1.rth_bounds_ns(date)
    spk_all = S.spike_flags(px)
    # the tau print and its successor (the spike guard's read)
    at = np.flatnonzero((ts == int(rec["tau_exact_ns"])) & (px == p_tau))
    i_tau = int(at[0])
    confirm_lag = (int(ts[i_tau + 1]) - tau) / S.NS if i_tau + 1 < ts.size else np.nan
    k = int(np.searchsorted(ts, tau, "right"))
    pts, ppx, psz, pspk = ts[k:], px[k:], sz[k:], spk_all[k:]
    ct = C1.collapse_tol(pts, TOL_MS) if pts.size else np.zeros(0, dtype=np.int64)
    # master path
    gt = tau + GRID_NS
    gi = np.searchsorted(pts, gt, "right") - 1
    path = np.where(gi >= 0, np.log(ppx[np.maximum(gi, 0)] / p_tau) if ppx.size else 0.0, 0.0).astype(np.float32)
    path[gt > t2000] = np.nan
    # decision times
    ref = float(rec["ref_shares"]) if pd.notna(rec["ref_shares"]) else np.nan
    cum = np.cumsum(psz)
    rows = []
    dts = {"tau": ("reached", tau)}
    for key, mins in S.WALL.items():
        d = tau + mins * S.MIN_NS
        dts[key] = ("reached", d) if d <= t2000 else ("not_reached", None)
    for key, mult in S.VOL.items():
        if not np.isfinite(ref):
            dts[key] = ("undefined", None)
            continue
        i = int(np.searchsorted(cum, mult * ref, "left"))
        dts[key] = ("reached", int(pts[i])) if i < pts.size else ("not_reached", None)
    for key in S.TIMES:
        state, d = dts[key]
        row = {"event_id": rec["event_id"], "time": key, "state": state, "d_ns": d}
        if state == "reached":
            row["tcs_state"] = S.tcs_state(int(rec["tau_exact_ns"]), tau, tau_mb_x, d)
            row["ts__tcs"] = S.tcs_latest_ts(tau_mb_x, d)
            if key != "tau":
                row.update(group_b(pts, ppx, psz, ct, pspk, tau, p_tau, d, rec["pre_trades_per_min"], rec["pre_dollars_per_min"],
                                   rec["sigma_pre"], ref, op, cl))
            row.update(forward(ts, px, d, t2000))
        rows.append(row)
    return rows, path, {"event_id": rec["event_id"], "tau_confirm_lag_s": confirm_lag, "n_day_prints": int(ts.size), "n_post_prints": int(pts.size),
                        "last_print_ns": int(ts[-1]), "last_print_px": float(px[-1]), "tau_mb_exact_ns": tau_mb_x}


def group_c(pop: pd.DataFrame, P: np.ndarray, ck: pd.DataFrame, labels: pd.Series, masks_by_stage: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Typical paths (pointwise median by type over the stage's training events) and each event's six
    distances at each reached checkpoint after tau. `labels` indexed like pop (may be permuted by T5)."""
    pos = pd.Series(np.arange(len(pop)), index=pop["event_id"])
    after = ck[(ck["time"] != "tau") & (ck["state"] == "reached")]
    rows, typ_rows = [], []
    for (fold, stage), (train_mask, row_mask) in masks_by_stage.items():
        typ = np.full((len(S.TYPES), GRID.size), np.nan, dtype=np.float32)
        for ti, t in enumerate(S.TYPES):
            m = train_mask & (labels.to_numpy() == t)
            if m.any():
                with np.errstate(all="ignore"):
                    typ[ti] = np.nanmedian(P[m], axis=0)
            typ_rows.append(pd.DataFrame({"fold": fold, "stage": stage, "type": t, "grid_s": GRID, "x_median": typ[ti],
                                          "n_events": int(m.sum())}))
        sub = after[after["event_id"].map(pos).map(lambda i: bool(row_mask[i]))]
        if sub.empty:
            continue
        ii = sub["event_id"].map(pos).to_numpy()
        q = S.query_index(sub["elapsed_min"].to_numpy() * 60.0, GRID)
        xe = P[ii[:, None], q]
        dist = np.sqrt(np.nanmean((xe[:, None, :] - typ[:, q].transpose(1, 0, 2)) ** 2, axis=2))
        df = pd.DataFrame(dist.astype(np.float32), columns=[f"dist_{t}" for t in S.TYPES])
        df.insert(0, "event_id", sub["event_id"].to_numpy())
        df.insert(1, "time", sub["time"].to_numpy())
        df.insert(2, "fold", fold)
        df.insert(3, "stage", stage)
        rows.append(df)
    return pd.concat(rows, ignore_index=True), pd.concat(typ_rows, ignore_index=True)


def stage_masks(pop: pd.DataFrame) -> dict:
    out = {}
    for f in S.FOLDS:
        m = S.fold_masks(pop, f)
        (y0, y1), yt = S.FOLDS[f]
        yr = pop["year"].to_numpy()
        out[(f, "tune")] = (m["sub"], (yr >= y0) & (yr <= y1))
        out[(f, "final")] = (m["train"], (yr >= y0) & (yr <= yt))
    return out


def write_split(ck: pd.DataFrame) -> None:
    """Two files (git size): t2_checkpoints.parquet = states, decision times, Group B, the R1 state and the latest
    timestamps; t2_forward.parquet = the forward-return columns, with one entry price per latency (the same entry
    serves every horizon). zstd-compressed; values unchanged."""
    fcols = [c for c in ck.columns if c.startswith(("fr_", "entry_"))]
    fw = ck[["event_id", "time"] + fcols].copy()
    for ln in LAT:
        px = [f"fr_{ln}_{h}_entry_px" for h in HOR if f"fr_{ln}_{h}_entry_px" in fw]
        if px:
            fw[f"entry_{ln}_px"] = fw[px].bfill(axis=1).iloc[:, 0]
            fw = fw.drop(columns=px)
    fw["config_hash"] = ck["config_hash"].iloc[0]
    ck.drop(columns=fcols).to_parquet(S.art("t2_checkpoints.parquet"), index=False, compression="zstd", compression_level=19)
    fw.to_parquet(S.art("t2_forward.parquet"), index=False, compression="zstd", compression_level=19)


def main() -> int:
    if "--split-existing" in sys.argv:                       # one-off: split a combined t2_checkpoints.parquet in place
        ck = pd.read_parquet(S.art("t2_checkpoints.parquet"))
        write_split(ck)
        back = pd.read_parquet(S.art("t2_checkpoints.parquet")).merge(pd.read_parquet(S.art("t2_forward.parquet")).drop(columns="config_hash"),
                                                                     on=["event_id", "time"])
        for c in [c for c in ck.columns if c in back.columns]:
            assert ck[c].equals(back[c]) or (ck[c].isna().equals(back[c].isna()) and (ck[c].dropna() == back[c].dropna()).all()), c
        for ln in LAT:
            for h in HOR:
                c = f"fr_{ln}_{h}_entry_px"
                if c in ck:
                    m = ck[c].notna()
                    assert (ck.loc[m, c].to_numpy() == back.loc[m, f"entry_{ln}_px"].to_numpy()).all(), c
        print("split ok", len(ck))
        return 0
    t_start = time.perf_counter()
    pop = S.load_population()
    A = pd.read_parquet(S.art("t1_group_a.parquet"), columns=["event_id", "c__ref_shares", "c__pre_trades_per_min", "c__pre_dollars_per_min",
                                                                "sigma_pre", "c__tau_ns_mb", "c__tau_exact_ns", "c__tau_d_ns"])
    d = pop.merge(A, on="event_id", how="left")
    assert len(d) == len(pop)
    mb = pd.read_parquet(S.REPO / MB_CLOSE, columns=["event_id", "prior_close", "prior_close_available"])
    mb["mb_close"] = mb["prior_close"].where(mb["prior_close_available"].fillna(False).astype(bool))
    d = d.merge(mb[["event_id", "mb_close"]], on="event_id", how="left")
    d = d.rename(columns={"c__ref_shares": "ref_shares", "c__pre_trades_per_min": "pre_trades_per_min",
                          "c__pre_dollars_per_min": "pre_dollars_per_min", "c__tau_ns_mb": "tau_ns_mb",
                          "c__tau_exact_ns": "tau_exact_ns", "c__tau_d_ns": "tau_d_ns"})
    recs = d[["event_id", "event_date_canonical", "tau_ns", "tau_exact_ns", "tau_d_ns", "tau_price", "ref_shares", "pre_trades_per_min", "pre_dollars_per_min",
              "sigma_pre", "tau_ns_mb", "mb_close"]].to_dict("records")
    rows, paths, meta = [], {}, []
    with ProcessPoolExecutor(max_workers=S.B2.cpu_workers()) as ex:
        for n, (r, p, m) in enumerate(ex.map(one, recs, chunksize=20)):
            rows.extend(r)
            paths[m["event_id"]] = p
            meta.append(m)
            if (n + 1) % 2000 == 0:
                print(f"  {n + 1:,}/{len(recs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    ck = S.ns_frame(rows, ["d_ns", "ts__B", "ts__tcs", "entry_lat0_ns", "entry_lat1s_ns", "entry_lat5s_ns"])
    # ---------------- T0 assertion on Group B and the tcs state: latest timestamp <= d, per event and time
    r = ck[ck["state"] == "reached"]
    vB = int((r["ts__B"].dropna() > r.loc[r["ts__B"].notna(), "d_ns"]).sum())
    vT = int((r["ts__tcs"] > r["d_ns"]).sum())
    tau_map = d.set_index("event_id")["tau_d_ns"]
    assert (r.loc[r["time"] == "tau", "d_ns"].to_numpy() == r.loc[r["time"] == "tau", "event_id"].map(tau_map).to_numpy()).all()
    ck["config_hash"] = S.cfg_hash()
    write_split(ck)
    assert vB == 0 and vT == 0, f"HARD STOP row 1 (Group B / tcs): B {vB}, tcs {vT}"

    P = np.vstack([paths[e] for e in pop["event_id"]])
    np.save(S.cache("master_paths.npy"), P)
    pd.DataFrame({"event_id": pop["event_id"]}).to_parquet(S.cache("master_paths_events.parquet"), index=False)
    print(f"tick pass {time.perf_counter() - t_start:,.0f}s")

    gc, typ = group_c(pop, P, ck, pop["type100"], stage_masks(pop))
    gc["config_hash"] = S.cfg_hash()
    gc.to_parquet(S.art("t2_group_c.parquet"), index=False)
    typ.to_parquet(S.art("t2_typical_paths.parquet"), index=False)

    meta = S.ns_frame(meta, ["tau_mb_exact_ns", "last_print_ns"])
    meta.to_parquet(S.art("t2_event_meta.parquet"), index=False)
    mm = meta.merge(d[["event_id", "tau_ns_mb"]], on="event_id")
    both = mm["tau_mb_exact_ns"].notna() & mm["tau_ns_mb"].notna()
    dmb = (mm.loc[both, "tau_mb_exact_ns"].astype("int64") - S.as_int64(mm.loc[both, "tau_ns_mb"]).astype("int64")).abs()
    mb_check = {"both": int(both.sum()), "within_128ns_of_b1": int((dmb <= S.TAU_ROUND_NS).sum()), "max_abs_ns": int(dmb.max()) if len(dmb) else None,
                "exact_only": int((mm["tau_mb_exact_ns"].notna() & mm["tau_ns_mb"].isna()).sum()),
                "b1_only": int((mm["tau_mb_exact_ns"].isna() & mm["tau_ns_mb"].notna()).sum())}
    fin = mm.merge(d[["event_id", "tau_exact_ns"]], on="event_id").merge(
        pd.read_parquet(S.art("t1_group_a.parquet"), columns=["event_id", "c__tau_close_sensitive"]), on="event_id")
    gap = (fin["tau_exact_ns"].astype("Int64") - fin["tau_mb_exact_ns"]).abs()
    settled = np.where(fin["tau_mb_exact_ns"].isna(), True, (gap > 60 * S.NS).fillna(False).to_numpy(dtype=bool))
    tcs_check = {"events": int(len(fin)), "equal_to_b1_flag": int((settled == fin["c__tau_close_sensitive"].astype(bool)).sum())}
    cnt = ck.groupby(["time", "state"]).size().unstack(fill_value=0).reindex(S.TIMES)
    lag = meta["tau_confirm_lag_s"]
    summary = {
        "config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "events": int(len(pop)),
        "states": {t: {k: int(v) for k, v in cnt.loc[t].items()} for t in S.TIMES},
        "latest_timestamp_violations": {"group_b": vB, "tcs_state": vT},
        "tcs_state_counts": {t: ck[(ck["time"] == t) & (ck["state"] == "reached")]["tcs_state"].value_counts().to_dict() for t in S.TIMES},
        "tau_confirmation": {"definition": "seconds from the tau print to its successor in the sorted print sequence (the spike guard reads that successor)",
                             "n": int(lag.notna().sum()), "zero_share": float((lag == 0).mean()),
                             "quantiles_s": {str(q): float(lag.quantile(q)) for q in (0.5, 0.9, 0.99, 1.0)}},
        "minute_bar_crossing_vs_b1": mb_check,
        "tcs_final_vs_b1": tcs_check,
        "master_grid_points": int(GRID.size), "group_c_rows": int(len(gc)),
        "elapsed_min_at_volume_checkpoints": {t: {str(q): float(ck[(ck["time"] == t) & (ck["state"] == "reached")]["elapsed_min"].quantile(q))
                                                  for q in (0.1, 0.5, 0.9)} for t in S.VOL},
    }
    S.write_json("t2_summary.json", summary)
    print(summary["states"])
    print(summary["tau_confirmation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
