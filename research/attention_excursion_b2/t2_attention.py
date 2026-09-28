"""
Brief 2, T2 -- the attention axes on all of D1 with tau, one date at a time. Everything is at or before
tau; every quantity goes through Brief 1's causality assertion (attention.py, unchanged).

A1   turnover: shares 04:00 -> tau / shs_shares_outstanding_corrected; shs_asof_ns >= tau is a LOG row
     (escalation row 5) and makes turnover `unavailable_asof_violation`.
A2   acceleration: segment-anchored ladder (04:00 / open + 60 s / close + 60 s, Amendment 3), each rung
     judged on its own, extent by R1 (exact window-count cutoff, rungs 0 and 1 always), a2_ignition
     (rung 0 or 1 from_nothing), the cross-minute class (A2 unavailable), count and kernel versions.
     Brief 1's attention.assert_segment_windows runs on every ladder (escalation row 3).
A3   filings accepted strictly before tau: within 24 h, hours since the last, the last form.
Levels (new): per valid rung window [tau - W_k, tau] -- collapsed trades per minute, dollars per minute,
     shares per minute -- and n_collapsed_seg_tau. Plain counts and sums over time; no baseline.
Cross-section: live sets over all D1 names on the date for L in {15 min, 60 min, rest of session};
     live_n; flow_share_k and accel_rank_k over the crosser's valid rung windows (identical clock windows
     for every live name, A3.4); each live name's move_at and age at tau_j.

Check: on the dev sample the valid rungs (k, counts, accel) must equal Brief 1's Amendment 3
t5_a2_rungs.parquet -- R1 drops only rungs that cannot be valid -- and flow_share / accel_rank must equal
Brief 1's t5_cross_sectional.parquet.

Writes artifacts/t2_attention.parquet, t2_a2_rungs.parquet, t2_cross_sectional.parquet,
t2_live_names.parquet, t2_summary.json.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/t2_attention.py
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

C1, A, I = B.C1, B.A, B.I
RAW_SEC = str(B.REPO / "data" / "raw" / "fundamentals" / "sec" / "2026-09-12" / "submissions")
FUND_COLS = ["event_id", "cik", "t0_ns", "shs_shares_outstanding_corrected", "shs_asof_ns", "shs_accepted_ns", "shs_lag_ns",
             "shs_quality", "shs_share_count_suspect", "shs_correction_applied", "shs_zero_artifact",
             "flg_last_form", "flg_dilution_form_before_t0"]
_SF = None
_CIK: dict = {}


def load_day(event_id: str, date: str, tol_ms: float) -> dict:
    """Brief 1 t5_attention.load_day, with the day's slices copied so the event folder's other days are
    freed, and a running dollar sum for the cross-section."""
    tr = C1.read_trades(event_id, with_conditions=False)
    t0400, t2000 = C1.et_ns(date, "04:00:00"), C1.et_ns(date, "20:00:00")
    a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
    ts, px, sz = tr["ts"][a:b].copy(), tr["px"][a:b].copy(), tr["sz"][a:b].copy()
    del tr
    assert ts.size < 2 or bool(np.all(ts[1:] >= ts[:-1])), "prints not sorted by time"
    return {"ts": ts, "px": px, "sz": sz, "ct": C1.collapse_tol(ts, tol_ms), "t0400": t0400, "t2000": t2000,
            "cum_dv": np.r_[0.0, np.cumsum(px * sz)]}


def _upto(arr: np.ndarray, tau: int) -> int:
    """Index one past the last element at or before tau, with the causality assertion: the arrays are
    sorted, so checking the last element taken is checking all of them."""
    hi = int(np.searchsorted(arr, tau, "right"))
    if hi and int(arr[hi - 1]) > tau:
        raise AssertionError(A.POST_TAU_MSG)
    return hi


def xs_dollar(day: dict, lo_ns: int, tau: int) -> float:
    """Dollar volume over (lo, tau] -- attention.dollar_volume's interval -- from the running sum."""
    hi = _upto(day["ts"], tau)
    lo = min(int(np.searchsorted(day["ts"], lo_ns, "right")), hi)
    return float(day["cum_dv"][hi] - day["cum_dv"][lo])


def xs_counts(day: dict, tau: int, lo_ns: int, mid_ns: int) -> tuple[int, int]:
    """attention.window_counts' half-window counts, index-bounded at tau."""
    ct = day["ct"]
    hi = _upto(ct, tau)
    im = min(int(np.searchsorted(ct, mid_ns, "left")), hi)
    ia = min(int(np.searchsorted(ct, lo_ns, "left")), hi)
    return hi - im, im - ia


def xs_last_price(day: dict, tau: int) -> float:
    hi = _upto(day["ts"], tau)
    return float(day["px"][hi - 1]) if hi else float("nan")


def cut(day: dict, tau: int) -> dict:
    """Brief 1 t5_attention.cut: prints at or before tau only."""
    k = int(np.searchsorted(day["ts"], tau, "right"))
    kc = int(np.searchsorted(day["ct"], tau, "right"))
    return {"ts": day["ts"][:k], "px": day["px"][:k], "sz": day["sz"][:k], "ct": day["ct"][:kc]}


def share_volume(ts: np.ndarray, sz: np.ndarray, lo_ns: int, tau_ns: int) -> float:
    """Shares over (lo, tau] -- the same interval as attention.dollar_volume."""
    A.assert_causal(ts, tau_ns)
    return float(sz[ts > lo_ns].sum())


def filings(cik) -> pd.DataFrame:
    k = str(cik)
    if k not in _CIK:
        _CIK[k] = A.load_cik_filings(RAW_SEC, k)
    return _CIK[k]


def process_date(args):
    global _SF
    if _SF is None:
        _SF = C1.scale_field()
    date, recs, names, par = args
    n_min, coef, kmax, tol = par["n_min"], par["coef"], par["kmax"], par["tol"]
    op, cl = C1.rth_bounds_ns(date)
    days = {r["event_id"]: load_day(r["event_id"], date, tol) for r in names}
    ev_rows, rung_rows, xs_rows, live_rows, log5 = [], [], [], [], []
    liv = [("15", 15 * 60), ("60", 3600), ("rest_of_session", None)]
    taus = {r["event_id"]: int(r["tau_ns"]) for r in names}
    pcs = {r["event_id"]: float(r["prior_close_exact"]) for r in names}
    for r in recs:
        base = {"event_id": r["event_id"], "ticker": r["ticker"], "event_date_canonical": date, "dev_group": r["dev_group"],
                "slice": r["slice"], "tau_session_segment": r["tau_session_segment"], "tau_close_sensitive": r["tau_close_sensitive"],
                "flag_cross_session_extreme": r["flag_cross_session_extreme"], "sec_from_0930": r["sec_from_0930"]}
        if not r["tau_available"]:
            ev_rows.append({**base, "attention_available": False, "reason": f"tau_unavailable:{r['tau_reason']}"})
            continue
        tau = int(r["tau_ns"])
        day = days[r["event_id"]]
        t0400 = day["t0400"]
        j = cut(day, tau)
        # ---------------- A1
        shares = A.a1_shares(j["ts"], j["sz"], tau, t0400)
        shs = r["shs_shares_outstanding_corrected"]
        asof_viol = pd.notna(r["shs_asof_ns"]) and int(r["shs_asof_ns"]) >= tau
        acc_viol = pd.notna(r["shs_accepted_ns"]) and int(r["shs_accepted_ns"]) >= tau
        if asof_viol:
            log5.append({"event_id": r["event_id"], "shs_asof_ns": int(r["shs_asof_ns"]), "tau_ns": tau})
            a1_state, turnover = "unavailable_asof_violation", np.nan
        elif pd.isna(shs):
            a1_state, turnover = ("unavailable_zero_artifact" if (pd.notna(r["shs_zero_artifact"]) and bool(r["shs_zero_artifact"])) else "unavailable_no_count"), np.nan
        elif shares == 0:
            a1_state, turnover = "zero", 0.0
        else:
            a1_state, turnover = "value", shares / float(shs)
        # ---------------- A2 (segment anchor, R1 extent)
        seg = C1.clock_segment(tau, op, cl)
        seg_start = C1.segment_start_ns(seg, date, op, cl)
        auction = seg in C1.AUCTION
        if auction:
            cs, lad, valid, kern, cutoff = j["ct"][:0], [], [], {}, None
        else:
            cs = j["ct"][j["ct"] >= seg_start]
            lad, cutoff = B.a2_ladder_r1(cs, tau, seg_start, n_min, coef, kmax)
            A.assert_segment_windows(lad, tau, seg_start, op, cl)                 # row 3
            valid = [x for x in lad if x["valid"]]
            kern = I.a2_kernel(cs, tau, seg_start, [x["k"] for x in valid], _SF.field_exact, 4.0)
        for x in lad:
            kk = kern.get(x["k"], {"defined": False, "accel_kernel": np.nan})
            row = {**{k: base[k] for k in ("event_id", "event_date_canonical", "dev_group", "slice")},
                   "tau_anchor_segment": seg, **x, "kernel_defined": kk["defined"], "accel_kernel": kk["accel_kernel"]}
            if x["valid"]:
                mins = x["W_s"] / 60.0
                row["trades_per_min"] = (x["n_recent"] + x["n_older"]) / mins
                row["dollars_per_min"] = A.dollar_volume(j["ts"], j["px"], j["sz"], x["win_lo_ns"], tau) / mins
                row["shares_per_min"] = share_volume(j["ts"], j["sz"], x["win_lo_ns"], tau) / mins
            rung_rows.append(row)
        valid_ks = [x["k"] for x in valid]
        inval = pd.Series([x["class"] for x in lad if not x["valid"]], dtype=object).value_counts().to_dict()
        a2v = not auction
        # ---------------- A3
        if pd.notna(r["cik"]):
            fl = filings(r["cik"])
            before = fl[fl["accepted_ns"] < tau]
            a3 = A.a3_filings(before["accepted_ns"].to_numpy(), before["form"].to_numpy(), tau)
            a3["a3_available"] = True
            a3["n_filings_on_record"] = int(len(fl))
        else:
            a3 = {"a3_available": False}
        ev_rows.append({**base, "attention_available": True, "tau_ns": tau,
                        "tau_anchor_segment": seg, "tau_in_auction_minute": auction,
                        "a2_state": "unavailable_auction_minute" if auction else "value",
                        "a2_anchor_ns": seg_start, "H_s": (tau - seg_start) / 1e9 if a2v else np.nan,
                        "H_0400_s": (tau - t0400) / 1e9, "n_collapsed_seg_tau": int(cs.size) if a2v else None,
                        "n_raw_prints_0400_tau": int(j["ts"].size), "n_collapsed_0400_tau": int(j["ct"].size),
                        "shares_0400_tau": shares, "shs_shares_outstanding_corrected": shs, "turnover": turnover,
                        "a1_state": a1_state, "shs_asof_violation": bool(asof_viol), "shs_accepted_after_tau": bool(acc_viol),
                        "shs_lag_ns": r["shs_lag_ns"], "shs_quality": r["shs_quality"],
                        "shs_share_count_suspect": r["shs_share_count_suspect"],
                        "flg_dilution_form_before_t0": r["flg_dilution_form_before_t0"],
                        "flg_last_form_t0_relative": r["flg_last_form"],
                        "t0_minus_tau_s": (int(r["t0_ns"]) - tau) / 1e9 if pd.notna(r["t0_ns"]) else np.nan,
                        "a2_rungs_generated": len(lad) if a2v else None, "a2_cutoff_k": cutoff,
                        "a2_valid_rungs": len(valid) if a2v else None,
                        "a2_valid_pattern": ",".join(str(k) for k in valid_ks) if a2v else None,
                        "a2_first_valid_k": valid_ks[0] if valid_ks else None,
                        "a2_last_valid_k": valid_ks[-1] if valid_ks else None,
                        "a2_valid_contiguous": bool(valid_ks and valid_ks == list(range(valid_ks[0], valid_ks[-1] + 1))) if a2v else None,
                        "a2_invalid_counting_noise": int(inval.get("counting_noise", 0)) if a2v else None,
                        "a2_invalid_from_nothing": int(inval.get("from_nothing", 0)) if a2v else None,
                        "a2_invalid_resolution_floor": int(inval.get("resolution_floor", 0)) if a2v else None,
                        "a2_ignition": bool(any(x["k"] <= 1 and x["class"] == "from_nothing" for x in lad)) if a2v else None,
                        **a3})
        # ---------------- cross-section
        for lname, lsec in liv:
            live = [e for e, ti in taus.items() if ti <= tau and (lsec is None or tau <= ti + lsec * 10**9)]
            assert r["event_id"] in live, "j must be in its own live set"
            for e in live:
                live_rows.append({"event_id": r["event_id"], "liveness": lname, "live_event_id": e, "is_self": e == r["event_id"],
                                  "sec_since_own_tau": (tau - taus[e]) / 1e9,
                                  "move_at_at_tau_j": xs_last_price(days[e], tau) / pcs[e] - 1.0})
            if not valid:
                xs_rows.append({"event_id": r["event_id"], "liveness": lname, "live_n": len(live), "k": None,
                                "reason": "a2_unavailable_auction_minute" if auction else "no_valid_rung"})
            for x in valid:
                lo = x["win_lo_ns"]
                dv = {e: xs_dollar(days[e], lo, tau) for e in live}
                acc = {}
                for e in live:
                    nr, no = xs_counts(days[e], tau, lo, x["win_mid_ns"])
                    if nr >= n_min and no >= n_min:
                        acc[e] = np.log(nr / no)
                tot = sum(dv.values())
                ranked = sorted(acc.items(), key=lambda kv: -kv[1])
                rank = next((i + 1 for i, (e, _) in enumerate(ranked) if e == r["event_id"]), None)
                xs_rows.append({"event_id": r["event_id"], "liveness": lname, "live_n": len(live), "k": x["k"],
                                "reason": None, "W_s": x["W_s"], "win_lo_ns": lo, "win_mid_ns": x["win_mid_ns"],
                                "dollar_volume_j": dv[r["event_id"]], "dollar_volume_live": tot,
                                "flow_share": dv[r["event_id"]] / tot if tot > 0 else np.nan,
                                "n_ranked": len(ranked), "accel_rank": rank,
                                "accel_rank_pct": (rank - 1) / (len(ranked) - 1) if rank and len(ranked) > 1 else np.nan})
    return ev_rows, rung_rows, xs_rows, live_rows, log5


def main() -> int:
    t_start = time.perf_counter()
    cfg = B.load_cfg()
    a5 = cfg["t5_attention"]
    par = {"n_min": a5["a2_acceleration"]["counting_noise_stop"]["n_min"], "coef": a5["a2_acceleration"]["resolution_floor"]["coef"],
           "kmax": a5["a2_acceleration"]["k_max"], "tol": a5["collapse_tol_ms"]}
    pop = pd.read_parquet(B.art("t0_population.parquet"))
    ef = C1.load_fundamentals_corrected()[FUND_COLS]
    pop = pop.merge(ef, on="event_id", how="left")
    assert len(pop) == 15763
    jobs = []
    for date, dd in pop.groupby("event_date_canonical"):
        recs = dd.to_dict("records")
        names = dd[dd["tau_available"]][["event_id", "tau_ns", "prior_close_exact"]].to_dict("records")
        jobs.append((date, recs, names, par))
    jobs.sort(key=lambda j: -len(j[2]))                     # the busiest dates first
    ev, rg, xs, lv, log5 = [], [], [], [], []
    with ProcessPoolExecutor(max_workers=int(os.environ.get("B2_DATE_WORKERS", "5"))) as ex:
        for k, res in enumerate(ex.map(process_date, jobs, chunksize=1)):
            for acc, part in zip((ev, rg, xs, lv, log5), res):
                acc += part
            if (k + 1) % 100 == 0:
                print(f"  {k + 1:,}/{len(jobs):,} dates  {time.perf_counter() - t_start:,.0f}s", flush=True)
    ev = pd.DataFrame(ev)
    for c in ("tau_ns", "a2_anchor_ns", "a2_rungs_generated", "a2_cutoff_k", "a2_valid_rungs", "n_collapsed_seg_tau", "a2_first_valid_k",
              "a2_last_valid_k", "a2_invalid_counting_noise", "a2_invalid_from_nothing", "a2_invalid_resolution_floor"):
        ev[c] = ev[c].astype("Int64")
    for c in ("a2_valid_contiguous", "a2_ignition", "tau_in_auction_minute"):
        ev[c] = ev[c].astype("boolean")
    B.assert_int64(ev)
    rg, xs, lv = pd.DataFrame(rg), pd.DataFrame(xs), pd.DataFrame(lv)
    for c in ("win_lo_ns", "win_mid_ns"):
        rg[c] = rg[c].astype("Int64")
        xs[c] = xs[c].astype("Int64")
    xs["k"] = xs["k"].astype("Int64")
    for df, name in [(ev, "t2_attention"), (rg, "t2_a2_rungs"), (xs, "t2_cross_sectional"), (lv, "t2_live_names")]:
        assert "open_adjacent_0930" not in df, "R5"
        df["config_hash"] = B.cfg_hash()
        df.to_parquet(B.art(f"{name}.parquet"), index=False)

    # ------------------------------------------------ Brief 1 (Amendment 3) dev rows, reproduced
    b1r = pd.read_parquet(B.b1_art("t5_a2_rungs.parquet"))
    b1r = b1r[b1r["valid"]].sort_values(["event_id", "k"])[["event_id", "k", "n_recent", "n_older", "accel", "accel_kernel"]].reset_index(drop=True)
    mine = rg[rg["valid"] & rg["event_id"].isin(set(b1r["event_id"]) | set(ev.loc[ev["dev_group"].notna(), "event_id"]))]
    mine = mine[mine["dev_group"].notna()].sort_values(["event_id", "k"])[["event_id", "k", "n_recent", "n_older", "accel", "accel_kernel"]].reset_index(drop=True)
    same_valid = len(mine) == len(b1r) and all(
        np.array_equal(mine[c].to_numpy(), b1r[c].to_numpy()) if c in ("event_id", "k", "n_recent", "n_older")
        else np.allclose(mine[c].to_numpy(float), b1r[c].to_numpy(float), rtol=0, atol=0, equal_nan=True)
        for c in mine.columns)
    b1x = pd.read_parquet(B.b1_art("t5_cross_sectional.parquet"))
    b1x = b1x[b1x["k"].notna()].sort_values(["event_id", "liveness", "k"])[["event_id", "liveness", "k", "live_n", "flow_share", "accel_rank"]].reset_index(drop=True)
    mx = xs[xs["k"].notna() & xs["event_id"].isin(b1x["event_id"])].sort_values(["event_id", "liveness", "k"])[
        ["event_id", "liveness", "k", "live_n", "flow_share", "accel_rank"]].reset_index(drop=True)
    same_xs = len(mx) == len(b1x) and bool((mx[["event_id", "liveness"]].astype(str).values == b1x[["event_id", "liveness"]].astype(str).values).all()) \
        and np.array_equal(mx["k"].to_numpy(int), b1x["k"].to_numpy(int)) and np.array_equal(mx["live_n"].to_numpy(int), b1x["live_n"].to_numpy(int)) \
        and np.allclose(mx["flow_share"].to_numpy(float), b1x["flow_share"].to_numpy(float), rtol=0, atol=1e-9, equal_nan=True) \
        and np.allclose(mx["accel_rank"].to_numpy(float), b1x["accel_rank"].to_numpy(float), rtol=0, atol=0, equal_nan=True)

    esc = cfg["brief2"]["escalation"]
    wa = ev[ev["attention_available"]]
    a2e = wa[wa["a2_state"] == "value"]
    rgv = rg[rg["valid"]]
    summary = {
        "config_hash": B.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "dates": len(jobs),
        "events": {"d1": int(len(ev)), "with_attention": int(len(wa)), "with_a2": int(len(a2e)),
                   "a2_unavailable_auction_minute": int((wa["a2_state"] != "value").sum())},
        "a1": {"state": wa["a1_state"].value_counts().to_dict(),
               "turnover": {"median": float(wa["turnover"].median()), "n": int(wa["turnover"].notna().sum())},
               "shs_accepted_after_tau": int(wa["shs_accepted_after_tau"].sum())},
        "row_5": {"criterion": esc["row_5"]["criterion"], "tier": "LOG, per event", "n": len(log5), "events": log5},
        "a2": {"valid_rungs_distribution": {str(k): int(v) for k, v in a2e["a2_valid_rungs"].value_counts().sort_index().items()},
               "valid_rungs_median": float(a2e["a2_valid_rungs"].median()),
               "zero_valid_rung_events": int((a2e["a2_valid_rungs"] == 0).sum()),
               "rungs_generated_total": int(a2e["a2_rungs_generated"].sum()), "valid_rungs_total": int(len(rgv)),
               "cutoff_by": {"exact_count": int(a2e["a2_cutoff_k"].notna().sum()), "floor_or_k_max": int(a2e["a2_cutoff_k"].isna().sum())},
               "invalid_rung_classes": rg.loc[~rg["valid"], "class"].value_counts().to_dict(),
               "resolution_floor_binding": int((rg["class"] == "resolution_floor").sum()),
               "a2_ignition_events": int(a2e["a2_ignition"].sum()),
               "by_segment": {sg: {"events": int(len(g)), "valid_rungs_median": float(g["a2_valid_rungs"].median()),
                                   "zero_valid": int((g["a2_valid_rungs"] == 0).sum()), "ignition": int(g["a2_ignition"].sum()),
                                   "H_s_median": float(g["H_s"].median())} for sg, g in a2e.groupby("tau_anchor_segment")},
               "kernel_defined_valid_rungs": int(rgv["kernel_defined"].sum())},
        "levels": {c: {"n": int(rgv[c].notna().sum()), "median": float(rgv[c].median()), "p05": float(rgv[c].quantile(.05)),
                       "p95": float(rgv[c].quantile(.95))} for c in ("trades_per_min", "dollars_per_min", "shares_per_min")},
        "a3": {"available": int(wa["a3_available"].fillna(False).astype(bool).sum()),
               "filing_24h": int(wa["filing_24h"].fillna(False).astype(bool).sum())},
        "cross_sectional": {L: {"events": int(g["event_id"].nunique()),
                                "live_n_median": float(g.drop_duplicates("event_id")["live_n"].median()),
                                "alone_events": int((g.drop_duplicates("event_id")["live_n"] == 1).sum()),
                                "rows_with_window": int(g["k"].notna().sum()),
                                "reason_no_window": g[g["k"].isna()]["reason"].value_counts().to_dict()}
                            for L, g in xs.groupby("liveness")},
        "live_name_rows": int(len(lv)),
        "dev_reproduces_brief1_a3_valid_rungs": {"value": bool(same_valid), "rows": int(len(b1r))},
        "dev_reproduces_brief1_a3_cross_section": {"value": bool(same_xs), "rows": int(len(b1x)),
                                                   "flow_share_max_abs_diff": float(np.nanmax(np.abs(mx["flow_share"].to_numpy(float) - b1x["flow_share"].to_numpy(float))))
                                                   if len(mx) == len(b1x) and len(mx) else None,
                                                   "note": "the cross-section sums dollars from a running sum (b2 xs_dollar); tolerance 1e-9"},
        "II5": {"causality": "attention.assert_causal on every quantity (Brief 1, unchanged); none raised",
                "a2_segment": "attention.assert_segment_windows on every ladder; none raised",
                "r1_cutoff": "b2common.a2_ladder_r1 asserts the cutoff rung is below 2 x n_min and nothing at or past it is valid"},
    }
    B.write_json("t2_summary.json", summary)
    print({k: summary[k] for k in ("seconds", "events", "row_5")})
    print(summary["a2"])
    print(summary["dev_reproduces_brief1_a3_valid_rungs"], summary["dev_reproduces_brief1_a3_cross_section"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
