"""
Brief 1, T5 -- both attention axes on the dev sample (50) and the sidecar (6, own row). No excursion
component is read here; attention is built, not related to anything.

Absolute axis  A1 turnover (shares 04:00 -> tau / split-corrected shares outstanding; row 5 LOG on
               shs_asof_ns >= tau_ns), A2 acceleration (top-anchored count ladder + the one-sided
               kernel check), A3 SEC filings strictly before tau (rebuilt from F1's raw archive
               relative to tau, not t0).
Cross-section  for liveness L in {15 min, 60 min, rest of session}: live set = D1 events on the same
               date with tau_i <= tau_j <= tau_i + L. live_n; flow_share_k over each of j's valid A2
               windows; accel_rank_k among live names clearing the counting-noise stop; per live name
               move_at at tau_j and seconds since its own tau.

Every print that reaches an attention quantity is cut at tau and asserted (attention.assert_causal);
the II.5 test that feeds a post-tau print to each function runs first and must pass.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t5_attention.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attention as A  # noqa: E402
import common as C  # noqa: E402
import instruments as I  # noqa: E402

RAW_SEC = str(C.REPO / "data" / "raw" / "fundamentals" / "sec" / "2026-09-12" / "submissions")


def load_day(event_id: str, date: str, tol_ms: float) -> dict:
    tr = C.read_trades(event_id, with_conditions=False)
    t0400, t2000 = C.et_ns(date, "04:00:00"), C.et_ns(date, "20:00:00")
    a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
    ts, px, sz = tr["ts"][a:b], tr["px"][a:b], tr["sz"][a:b]
    return {"ts": ts, "px": px, "sz": sz, "ct": C.collapse_tol(ts, tol_ms), "t0400": t0400, "t2000": t2000}


def cut(day: dict, tau: int) -> dict:
    k = int(np.searchsorted(day["ts"], tau, "right"))
    kc = int(np.searchsorted(day["ct"], tau, "right"))
    return {"ts": day["ts"][:k], "px": day["px"][:k], "sz": day["sz"][:k], "ct": day["ct"][:kc]}


def main() -> int:
    cfg = C.load_cfg()
    a5 = cfg["t5_attention"]
    tol = a5["collapse_tol_ms"]
    n_min = a5["a2_acceleration"]["counting_noise_stop"]["n_min"]
    coef = a5["a2_acceleration"]["resolution_floor"]["coef"]
    kmax = a5["a2_acceleration"]["k_max"]
    trunc = 4.0
    liv = [(15, 15 * 60), (60, 3600), ("rest_of_session", None)]
    sf = C.scale_field()

    test = A.causality_test(sf.field_exact)
    C.write_json(f"{C.ART}/t5_causality_test.json", test)
    assert test["passes"], f"II.5 causality test failed: {test}"

    t2 = pd.read_parquet(C.art("t2_tau.parquet"))
    sl = pd.read_parquet(C.REPO / C.OUT / "slices.parquet", columns=["event_id", "dev_group"])
    t2 = t2.merge(sl, on="event_id", how="left")
    dev = t2[t2["dev_group"].notna()].copy()
    ef = C.load_fundamentals_corrected()
    ef = ef[["event_id", "cik", "t0_ns", "shs_shares_outstanding_corrected", "shs_asof_ns", "shs_accepted_ns", "shs_lag_ns",
             "shs_quality", "shs_share_count_suspect", "shs_correction_applied", "shs_zero_artifact",
             "flg_last_form", "flg_last_accepted_ns", "flg_dilution_form_before_t0", "flg_n_filings_24h"]]
    dev = dev.merge(ef, on="event_id", how="left")

    ev_rows, rung_rows, xs_rows, live_rows, log5 = [], [], [], [], []
    for date, dd in dev.groupby("event_date_canonical"):
        names = t2[(t2["event_date_canonical"] == date) & t2["tau_available"]]
        days = {r.event_id: load_day(r.event_id, date, tol) for r in names.itertuples()}
        for r in dd.itertuples():
            base = {"event_id": r.event_id, "ticker": r.ticker, "event_date_canonical": date, "dev_group": r.dev_group,
                    "tau_session_segment": r.tau_session_segment, "tau_close_sensitive": r.tau_close_sensitive,
                    "flag_cross_session_extreme": r.flag_cross_session_extreme,
                    "sec_from_0930": r.sec_from_0930, "open_adjacent_0930": None}
            if not r.tau_available:
                ev_rows.append({**base, "attention_available": False, "reason": f"tau_unavailable:{r.tau_reason}"})
                continue
            tau = int(r.tau_ns)
            day = days[r.event_id]
            t0400 = day["t0400"]
            j = cut(day, tau)
            # ---------------- A1
            shares = A.a1_shares(j["ts"], j["sz"], tau, t0400)
            shs = r.shs_shares_outstanding_corrected
            asof_viol = pd.notna(r.shs_asof_ns) and int(r.shs_asof_ns) >= tau
            acc_viol = pd.notna(r.shs_accepted_ns) and int(r.shs_accepted_ns) >= tau
            if asof_viol:
                log5.append({"event_id": r.event_id, "shs_asof_ns": int(r.shs_asof_ns), "tau_ns": tau})
            if asof_viol:
                a1_state, turnover = "unavailable_asof_violation", np.nan
            elif pd.isna(shs):
                a1_state, turnover = ("unavailable_zero_artifact" if bool(r.shs_zero_artifact) else "unavailable_no_count"), np.nan
            elif shares == 0:
                a1_state, turnover = "zero", 0.0
            else:
                a1_state, turnover = "value", shares / float(shs)
            # ---------------- A2
            lad = I.a2_count_ladder(j["ct"], tau, t0400, n_min, coef, kmax)
            valid = [x for x in lad if x["valid"]]
            kern = I.a2_kernel(j["ct"], tau, t0400, [x["k"] for x in valid], sf.field_exact, trunc)
            for x in lad:
                kk = kern.get(x["k"], {"defined": False, "accel_kernel": np.nan})
                rung_rows.append({**base, **{k: v for k, v in x.items() if k not in ("win_lo_ns", "win_mid_ns")},
                                  "kernel_defined": kk["defined"], "accel_kernel": kk["accel_kernel"]})
            # A2.4: every rung is judged on its own -- no stop. The pattern of valid rungs is carried.
            valid_ks = [x["k"] for x in lad if x["valid"]]
            inval = pd.Series([x["class"] for x in lad if not x["valid"]], dtype=object).value_counts().to_dict()
            # ---------------- A3
            if pd.notna(r.cik):
                fl = A.load_cik_filings(RAW_SEC, str(r.cik))
                before = fl[fl["accepted_ns"] < tau]
                a3 = A.a3_filings(before["accepted_ns"].to_numpy(), before["form"].to_numpy(), tau)
                a3["a3_available"] = True
                a3["n_filings_on_record"] = int(len(fl))
            else:
                a3 = {"a3_available": False}
            ev_rows.append({**base, "attention_available": True, "tau_ns": tau, "H_s": (tau - t0400) / 1e9,
                            "n_raw_prints_0400_tau": int(j["ts"].size), "n_collapsed_0400_tau": int(j["ct"].size),
                            "shares_0400_tau": shares, "shs_shares_outstanding_corrected": shs, "turnover": turnover,
                            "a1_state": a1_state, "shs_asof_violation": bool(asof_viol), "shs_accepted_after_tau": bool(acc_viol),
                            "shs_lag_ns": r.shs_lag_ns, "shs_quality": r.shs_quality,
                            "shs_share_count_suspect": r.shs_share_count_suspect,
                            "flg_dilution_form_before_t0": r.flg_dilution_form_before_t0,
                            "flg_last_form_t0_relative": r.flg_last_form,
                            "t0_minus_tau_s": (int(r.t0_ns) - tau) / 1e9 if pd.notna(r.t0_ns) else np.nan,
                            "a2_valid_rungs": len(valid), "a2_rungs_computed": len(lad),
                            "a2_valid_pattern": ",".join(str(k) for k in valid_ks),
                            "a2_first_valid_k": valid_ks[0] if valid_ks else None,
                            "a2_last_valid_k": valid_ks[-1] if valid_ks else None,
                            "a2_valid_contiguous": bool(valid_ks and valid_ks == list(range(valid_ks[0], valid_ks[-1] + 1))),
                            "a2_invalid_counting_noise": int(inval.get("counting_noise", 0)),
                            "a2_invalid_from_nothing": int(inval.get("from_nothing", 0)),
                            "a2_invalid_resolution_floor": int(inval.get("resolution_floor", 0)),
                            "a2_rung0_from_nothing": bool(lad and lad[0]["class"] == "from_nothing"), **a3})
            # ---------------- cross-section
            for lname, lsec in liv:
                if lsec is None:
                    live = names[names["tau_ns"].astype("int64") <= tau]
                else:
                    ti = names["tau_ns"].astype("int64")
                    live = names[(ti <= tau) & (tau <= ti + lsec * 10**9)]
                assert r.event_id in set(live["event_id"]), "j must be in its own live set"
                cuts = {e: cut(days[e], tau) for e in live["event_id"]}
                for lr in live.itertuples():
                    c = cuts[lr.event_id]
                    live_rows.append({"event_id": r.event_id, "liveness": str(lname), "live_event_id": lr.event_id,
                                      "is_self": lr.event_id == r.event_id,
                                      "sec_since_own_tau": (tau - int(lr.tau_ns)) / 1e9,
                                      "move_at_at_tau_j": A.last_price(c["ts"], c["px"], tau) / float(lr.prior_close_exact) - 1.0,
                                      "live_tau_close_sensitive": lr.tau_close_sensitive})
                if not valid:
                    xs_rows.append({"event_id": r.event_id, "liveness": str(lname), "live_n": len(live), "k": None})
                for x in valid:
                    lo = x["win_lo_ns"]
                    dv = {e: A.dollar_volume(c["ts"], c["px"], c["sz"], lo, tau) for e, c in cuts.items()}
                    acc = {}
                    for e, c in cuts.items():
                        nr, no = A.window_counts(c["ct"], tau, lo, x["win_mid_ns"])
                        if nr >= n_min and no >= n_min:
                            acc[e] = np.log(nr / no)
                    tot = sum(dv.values())
                    ranked = sorted(acc.items(), key=lambda kv: -kv[1])
                    rank = next((i + 1 for i, (e, _) in enumerate(ranked) if e == r.event_id), None)
                    xs_rows.append({"event_id": r.event_id, "liveness": str(lname), "live_n": len(live), "k": x["k"],
                                    "W_s": x["W_s"], "dollar_volume_j": dv[r.event_id], "dollar_volume_live": tot,
                                    "flow_share": dv[r.event_id] / tot if tot > 0 else np.nan,
                                    "n_ranked": len(ranked), "accel_rank": rank,
                                    "accel_rank_pct": (rank - 1) / (len(ranked) - 1) if rank and len(ranked) > 1 else np.nan})
    ev = pd.DataFrame(ev_rows)
    ev["tau_ns"] = ev["tau_ns"].astype("Int64")          # int64 end to end (config t2_tau.int64)
    assert str(ev["tau_ns"].dtype) == "Int64"
    rg = pd.DataFrame(rung_rows)
    xs = pd.DataFrame(xs_rows)
    lv = pd.DataFrame(live_rows)
    for df, name in [(ev, "t5_attention"), (rg, "t5_a2_rungs"), (xs, "t5_cross_sectional"), (lv, "t5_live_names")]:
        df["config_hash"] = C.cfg_hash()
        df.to_parquet(C.art(f"{name}.parquet"), index=False)

    dv3 = ev[(ev["dev_group"] == "dev_v3") & ev["attention_available"]]
    rgv = rg[(rg["dev_group"] == "dev_v3") & rg["valid"]]
    sp = {int(k): {"n": int(g[["accel", "accel_kernel"]].dropna().shape[0]),
                   "spearman_count_vs_kernel": A.spearman(g["accel"], g["accel_kernel"])}
          for k, g in rgv.groupby("k")}
    xsd = xs[xs["event_id"].isin(dv3["event_id"])]
    summary = {
        "config_hash": C.cfg_hash(),
        "II5_causality_test": test,
        "events": {"dev_v3_with_attention": int(len(dv3)), "sidecar_rows": int((ev["dev_group"] == "dev_v4_sidecar").sum())},
        "a1": {"state": dv3["a1_state"].value_counts().to_dict(),
               "turnover": {"median": float(dv3["turnover"].median()), "p25": float(dv3["turnover"].quantile(.25)),
                            "p75": float(dv3["turnover"].quantile(.75)), "n": int(dv3["turnover"].notna().sum())},
               "share_count_suspect": int(dv3["shs_share_count_suspect"].fillna(False).astype(bool).sum()),
               "dilution_form_before_t0": int(dv3["flg_dilution_form_before_t0"].fillna(False).astype(bool).sum()),
               "shs_accepted_after_tau": int(dv3["shs_accepted_after_tau"].sum())},
        "row_5": {"criterion": "shs_asof_ns >= tau_ns for any event", "tier": "LOG, per event",
                  "n": len(log5), "events": log5},
        "a2": {"valid_rungs_distribution": dv3["a2_valid_rungs"].value_counts().sort_index().to_dict(),
               "valid_rungs_median": float(dv3["a2_valid_rungs"].median()),
               "rule": "per-rung validity, no sequential stop (Amendment 2 A2.4)",
               "valid_pattern_top": dv3["a2_valid_pattern"].value_counts().head(12).to_dict(),
               "first_valid_k_distribution": dv3["a2_first_valid_k"].value_counts(dropna=False).sort_index().to_dict(),
               "valid_contiguous_events": int(dv3["a2_valid_contiguous"].sum()),
               "invalid_rung_classes": {"counting_noise": int(dv3["a2_invalid_counting_noise"].sum()),
                                        "from_nothing": int(dv3["a2_invalid_from_nothing"].sum()),
                                        "resolution_floor": int(dv3["a2_invalid_resolution_floor"].sum())},
               "resolution_floor_ever_binding": int((rg["class"] == "resolution_floor").sum()),
               "rung0_from_nothing_events": int(dv3["a2_rung0_from_nothing"].sum()),
               "zero_valid_rung_events": int((dv3["a2_valid_rungs"] == 0).sum()),
               "kernel_defined_valid_rungs": int(rgv["kernel_defined"].sum()), "valid_rungs_total": int(len(rgv)),
               "spearman_count_vs_kernel_by_rung": sp},
        "a3": {"available": int(dv3["a3_available"].fillna(False).sum()),
               "filing_24h": int(dv3["filing_24h"].fillna(False).astype(bool).sum()),
               "hours_since_last_filing_median": float(dv3["hours_since_last_filing"].median()),
               "t0_before_tau": int((dv3["t0_minus_tau_s"] < 0).sum()), "t0_after_tau": int((dv3["t0_minus_tau_s"] > 0).sum())},
        "cross_sectional": {str(L): {"live_n_distribution": g.drop_duplicates("event_id")["live_n"].value_counts().sort_index().to_dict(),
                                     "alone_events": int((g.drop_duplicates("event_id")["live_n"] == 1).sum())}
                            for L, g in xsd.groupby("liveness")},
        "names_read": int(sum(1 for _ in lv["live_event_id"].unique())),
    }
    C.write_json(f"{C.ART}/t5_summary.json", summary)
    print({k: summary[k] for k in ("events", "a1", "row_5")})
    print(summary["a2"])
    print(summary["a3"], summary["cross_sectional"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
