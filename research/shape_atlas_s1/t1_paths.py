"""
Shape atlas S1, T1 -- the three views of every event's path, and each event's own null. Exploratory,
hindsight used by design; nothing here is a tested result.

One tick pass over all of D1 with tau (b2's tau, spike-guarded). Per event:
  post       prints strictly after tau to the last print <= 20:00, N in {50, 100, 200} (b2's vector,
             rebuilt with the same bucketize and checked against b2's components)
  run-up     segment start (04:00 / open + 60 s / close + 60 s) -> tau print, N = 100; plus the
             descriptors (u_launch, height, drawdown, pushes, duration) and the overnight gap_share
  whole day  first print >= 04:00 -> last print <= 20:00, N = 100, with u_tau
  null       200 draws with replacement of the event's own demeaned bucket log returns, through the
             identical pipeline (s1common.path_pipeline), for the post-tau view at every rung:
             rise_pct, fall_pct, the null's median rise (sigma and bp), each draw's theory type, and
             the joint (u_peak, rise_s) histogram of the draws.

Writes artifacts/s1_events.parquet (one row per event), s1_paths_{post,runup,whole_day}.parquet (the
N = 100 bucket log path, relative to element 0, float64 -- the clustering and its null are rebuilt
from these), s1_prior_close_{runup,whole_day}.parquet (the G-point log(price / prior close) path),
s1_null_joint_hist.parquet, t1_summary.json.

Usage: .venv/Scripts/python.exe research/shape_atlas_s1/t1_paths.py
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1common as S  # noqa: E402

C1, I = S.C1, S.I
CFG = S.load_cfg()
G = CFG["views"]["resample"]["G"]
ND = CFG["null"]["draws"]
U_EDGES = np.linspace(0.0, 1.0, 21)
R_EDGES = np.array([float(x) for x in CFG["joint_peak_rise"]["rise_s_edges"][:-1]] + [np.inf])


def post_view(ev: dict, ts, px, sz, N: int) -> tuple[dict, np.ndarray | None, np.ndarray]:
    b = I.bucketize(ts, px, sz, N)
    hist = np.zeros((20, len(R_EDGES) - 1))
    if not b["ok"]:
        return {f"post{N}_available": False, f"post{N}_reason": b["reason"]}, None, hist
    lp = np.log(np.r_[ev["tau_price"], b["vwap"]])
    _, c, _ = S.real_pipeline(lp, G)
    out = {f"post{N}_available": True, f"post{N}_max_bucket_vol_rel_err": b["max_bucket_vol_rel_err"]}
    for k in ("u_peak", "rise_s", "fall_s", "dip_before_peak_s", "terminal_s", "rise_bp", "fall_bp", "sigma_path", "peak_tied"):
        out[f"post{N}_{k}"] = c[k][0]
    _, nc, _ = S.null_pipeline(lp, S.null_index(CFG, ev["event_index"], "post", N, ND), G)
    ok = ~nc["sigma_zero"]
    if c["sigma_zero"][0] or not ok.any():
        out[f"post{N}_null_ok"] = False
        return out, lp - lp[0], hist
    rs, fs = nc["rise_s"][ok], nc["fall_s"][ok]
    out.update({f"post{N}_null_ok": True, f"post{N}_null_n": int(ok.sum()),
                f"post{N}_rise_pct": S.pct_vs(rs, c["rise_s"][0]), f"post{N}_fall_pct": S.pct_vs(fs, c["fall_s"][0]),
                f"post{N}_null_median_rise_s": float(np.median(rs)), f"post{N}_null_median_fall_s": float(np.median(fs)),
                f"post{N}_null_median_rise_bp": float(np.median(nc["rise_bp"][ok])),
                f"post{N}_null_median_u_peak": float(np.median(nc["u_peak"][ok]))})
    types = S.theory_type(S.pct_leave_one_out(rs), S.pct_leave_one_out(fs), nc["u_peak"][ok])
    for t in S.TYPES:
        out[f"post{N}_null_share_{t}"] = float(np.mean(types == t))
    h, _, _ = np.histogram2d(nc["u_peak"][ok], np.clip(rs, 0, None), bins=[U_EDGES, R_EDGES])
    hist = h / ok.sum()                                          # each event weighs 1 in the pooled null
    return out, lp - lp[0], hist


def pushes(lp: np.ndarray, sigma_b: float) -> int:
    """Drawdowns of at least 1 sigma_b from the running max, recovered (a new high above that max)
    before the end of the run-up."""
    n, peak, in_dd = 0, lp[0], False
    for x in lp[1:]:
        if x > peak:
            if in_dd:
                n += 1
                in_dd = False
            peak = x
        elif peak - x >= sigma_b:
            in_dd = True
    return n


def one(ev: dict):
    tr = C1.read_trades(ev["event_id"], with_conditions=False)
    date, tau = ev["event_date_canonical"], int(ev["tau_ns"])
    t0400, t2000 = C1.et_ns(date, "04:00:00"), C1.et_ns(date, "20:00:00")
    a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
    ts, px, sz = tr["ts"][a:b], tr["px"][a:b], tr["sz"][a:b]
    del tr
    row = {"event_id": ev["event_id"], "event_index": ev["event_index"]}
    paths, pcs, hists = {}, {}, {}
    # ------------------------------------------------ post-tau, three rungs
    k = int(np.searchsorted(ts, tau, "right"))
    for N in (50, 100, 200):
        if ts.size - k < 2:
            row[f"post{N}_available"], row[f"post{N}_reason"] = False, "path_too_short"
            hists[N] = np.zeros((20, len(R_EDGES) - 1))
            continue
        o, lp, h = post_view(ev, ts[k:], px[k:], sz[k:], N)
        row.update(o)
        hists[N] = h
        if N == 100 and lp is not None:
            paths["post"] = lp
    # ------------------------------------------------ gap and whole day
    pc = float(ev["prior_close_exact"])
    row["gap_share"] = float(np.log(px[0] / pc) / np.log(1.30)) if ts.size else np.nan
    row["first_print_ns"] = int(ts[0]) if ts.size else None
    if ts.size >= 2:
        bw = I.bucketize(ts[1:], px[1:], sz[1:], 100)
        if bw["ok"]:
            lp = np.log(np.r_[px[0], bw["vwap"]])
            _, c, _ = S.real_pipeline(lp, G)
            pos = sz[1:] > 0
            row.update({"whole_available": not bool(c["sigma_zero"][0]), "whole_reason": "sigma_zero" if c["sigma_zero"][0] else None,
                        "whole_u_tau": float(sz[1:][pos & (ts[1:] <= tau)].sum() / bw["V"]),
                        "whole_n_prints": int(ts.size), "whole_max_bucket_vol_rel_err": bw["max_bucket_vol_rel_err"]})
            for kk in ("u_peak", "rise_s", "fall_s", "terminal_s", "sigma_path"):
                row[f"whole_{kk}"] = c[kk][0]
            paths["whole_day"] = lp - lp[0]
            pcs["whole_day"] = S.resample_levels(np.log(np.r_[px[0], bw["vwap"]] / pc), G)[0]
        else:
            row.update({"whole_available": False, "whole_reason": bw["reason"]})
    else:
        row.update({"whole_available": False, "whole_reason": "fewer_than_2_prints"})
    # ------------------------------------------------ run-up
    op, cl = C1.rth_bounds_ns(date)
    seg = C1.clock_segment(tau, op, cl)
    row["tau_anchor_segment"] = seg
    if seg in C1.AUCTION:
        row.update({"runup_available": False, "runup_reason": "tau_in_auction_minute"})
    else:
        s0 = C1.segment_start_ns(seg, date, op, cl)
        i0 = int(np.searchsorted(ts, s0, "left"))
        rts, rpx, rsz = ts[i0:k], px[i0:k], sz[i0:k]
        row["runup_n_prints"] = int(rts.size)
        row["runup_thin"] = bool(rts.size < 250)
        if rts.size < 2:
            row.update({"runup_available": False, "runup_reason": "no_print_before_tau"})
        else:
            br = I.bucketize(rts[1:], rpx[1:], rsz[1:], 100)
            if not br["ok"]:
                row.update({"runup_available": False, "runup_reason": br["reason"]})
            else:
                lp = np.log(np.r_[rpx[0], br["vwap"]])
                _, c, _ = S.real_pipeline(lp, G)
                sp = float(c["sigma_path"][0])
                ok = sp > 0
                row.update({"runup_available": bool(ok), "runup_reason": None if ok else "sigma_zero",
                            "runup_max_bucket_vol_rel_err": br["max_bucket_vol_rel_err"],
                            "runup_sigma_path": sp, "runup_u_launch": float(np.argmin(lp) / 100),
                            "runup_height_s": float((np.log(ev["tau_price"]) - lp.min()) / sp) if ok else np.nan,
                            "runup_max_drawdown_s": float(np.max(np.maximum.accumulate(lp) - lp) / sp) if ok else np.nan,
                            "runup_pushes": pushes(lp, sp / np.sqrt(100)) if ok else None,
                            "runup_minutes": (tau - int(rts[0])) / 6e10, "runup_shares": float(rsz.sum())})
                for kk in ("u_peak", "rise_s", "fall_s", "terminal_s"):
                    row[f"runup_{kk}"] = c[kk][0]
                if ok:
                    paths["runup"] = lp - lp[0]
                    pcs["runup"] = S.resample_levels(np.log(np.r_[rpx[0], br["vwap"]] / pc), G)[0]
    return row, paths, pcs, hists


def main() -> int:
    t_start = time.perf_counter()
    pop = pd.read_parquet(S.src("population"))
    pop = pop[pop["tau_available"]].sort_values("event_id").reset_index(drop=True)
    assert len(pop) == 15519
    B2 = S.B2
    B2.assert_int64(pop)
    pop["event_index"] = np.arange(len(pop))
    recs = pop[["event_id", "event_index", "event_date_canonical", "tau_ns", "tau_price", "prior_close_exact"]].to_dict("records")

    # section 9 identity test on a real path before anything runs
    probe = one(recs[0])
    assert "post" in probe[1]
    lp = probe[1]["post"]
    ident = S.identity_test(lp, G)
    assert ident, "null identity test failed"
    assert S.null_index(CFG, 0, "post", 100, 5).tolist() == S.null_index(CFG, 0, "post", 100, 200)[:5].tolist(), "null draws not row-stable"

    rows, P = [], {v: {} for v in ("post", "runup", "whole_day")}
    PC = {v: {} for v in ("runup", "whole_day")}
    H = {N: {} for N in (50, 100, 200)}
    with ProcessPoolExecutor(max_workers=S.B2.cpu_workers()) as ex:
        for n, (row, paths, pcs, hists) in enumerate(ex.map(one, recs, chunksize=25)):
            rows.append(row)
            for v, p in paths.items():
                P[v][row["event_id"]] = p
            for v, p in pcs.items():
                PC[v][row["event_id"]] = p
            for N, h in hists.items():
                H[N][row["event_id"]] = h
            if (n + 1) % 2000 == 0:
                print(f"  {n + 1:,}/{len(recs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    ev = pd.DataFrame(rows)
    keep = ["event_id", "ticker", "event_date_canonical", "year", "tau_ns", "tau_price", "prior_close_exact", "tau_session_segment",
            "sec_from_0400", "sec_from_0930", "tau_close_sensitive", "flag_cross_session_extreme", "dev_group", "price_tier"]
    ev = pop[keep].merge(ev, on="event_id", how="left")
    assert len(ev) == len(pop)
    ev["tau_ns"] = ev["tau_ns"].astype("Int64")
    B2.assert_int64(ev)
    ev["config_hash"] = S.cfg_hash()
    ev.to_parquet(S.art("s1_events.parquet"), index=False)
    for v, d in P.items():
        ids = sorted(d)
        arr = np.vstack([d[e] for e in ids])
        assert arr.shape[1] == 101
        df = pd.DataFrame(arr, columns=[f"b{i:03d}" for i in range(101)])
        df.insert(0, "event_id", ids)
        df.to_parquet(S.art(f"s1_paths_{v}.parquet"), index=False)
    for v, d in PC.items():
        ids = sorted(d)
        arr = np.vstack([d[e] for e in ids]).astype(np.float32)
        assert arr.shape[1] == G, "prior-close path does not have G points"
        df = pd.DataFrame(arr, columns=[f"g{i:03d}" for i in range(G)])
        df.insert(0, "event_id", ids)
        df.to_parquet(S.art(f"s1_prior_close_{v}.parquet"), index=False)
    hrows = []
    yr = ev.set_index("event_id")["year"]
    for N, d in H.items():
        for y in sorted(set(yr)) + ["all"]:
            ids = [e for e in d if y == "all" or yr[e] == y]
            tot = np.sum([d[e] for e in ids], axis=0)
            for i in range(tot.shape[0]):
                for j in range(tot.shape[1]):
                    hrows.append({"N": N, "year": str(y), "u_lo": U_EDGES[i], "u_hi": U_EDGES[i + 1], "r_lo": R_EDGES[j],
                                  "r_hi": R_EDGES[j + 1], "null_events_weight": float(tot[i, j]), "events": len(ids)})
    pd.DataFrame(hrows).to_parquet(S.art("s1_null_joint_hist.parquet"), index=False)

    # ------------------------------------------------ b2 reuse check (post-tau components)
    b2 = pd.read_parquet(S.src("excursion"), columns=["event_id", "N", "vector_available", "u_peak", "rise_s", "fall_s", "dip_before_peak_s",
                                                      "terminal_s", "rise_bp", "fall_bp"])
    diffs = {}
    for N in (50, 100, 200):
        m = b2[(b2["N"] == N) & (b2["vector_available"] == True)].merge(ev, on="event_id")  # noqa: E712
        for c in ("u_peak", "rise_s", "fall_s", "dip_before_peak_s", "terminal_s", "rise_bp", "fall_bp"):
            d = (m[c] - m[f"post{N}_{c}"]).abs() / np.maximum(1.0, m[c].abs())      # relative above 1, absolute below
            diffs[f"N={N}:{c}"] = float(d.max())
    worst = max(diffs.values())
    avail = {v: int(ev[f"{v}_available"].fillna(False).astype(bool).sum()) for v in ("post100", "runup", "whole")}
    summary = {
        "config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "events": int(len(ev)),
        "coverage": {"post": {N: int(ev[f"post{N}_available"].fillna(False).astype(bool).sum()) for N in (50, 100, 200)},
                     "post_null_ok": {N: int(ev[f"post{N}_null_ok"].fillna(False).astype(bool).sum()) for N in (50, 100, 200)},
                     "runup": avail["runup"], "runup_reasons": ev.loc[~ev["runup_available"].fillna(False).astype(bool), "runup_reason"].value_counts().to_dict(),
                     "runup_thin": int(ev["runup_thin"].fillna(False).astype(bool).sum()),
                     "whole_day": avail["whole"], "whole_reasons": ev.loc[~ev["whole_available"].fillna(False).astype(bool), "whole_reason"].value_counts().to_dict(),
                     "paths_written": {v: len(d) for v, d in P.items()}},
        "assertions": {"bucket_volume_conservation": "instruments.bucketize asserts on every view and rung; none raised",
                       "max_bucket_vol_rel_err": {v: float(ev[c].max()) for v, c in (("post100", "post100_max_bucket_vol_rel_err"),
                                                                                      ("runup", "runup_max_bucket_vol_rel_err"),
                                                                                      ("whole_day", "whole_max_bucket_vol_rel_err")) if c in ev},
                       "resampled_paths_have_G_points": f"asserted in s1common.resample (G = {G}) on every path",
                       "tau_ns_int64": True, "null_identity_test": bool(ident), "null_draws_row_stable": True,
                       "post_components_equal_b2": {"max_diff": worst, "rule": "|b2 - s1| / max(1, |b2|) <= 1e-9", "by_component": diffs,
                                                    "passes": bool(worst <= 1e-9)}},
    }
    assert worst <= 1e-9, f"post-tau components differ from b2 by {worst}"
    S.write_json("t1_summary.json", summary)
    print({k: summary[k] for k in ("seconds", "events", "coverage")})
    print(summary["assertions"]["post_components_equal_b2"]["max_diff"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
