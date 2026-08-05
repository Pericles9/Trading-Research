"""
Phase 10 v2 R1.3 -- derive the detection anchor per D7.

  R1.3a  recompute the tick-derived T-1 regular-hours close; flag undefined
  R1.3b  find the trigger crossing; resolve it to every poll boundary
  R1.3c  never-crosses: flag, carry, report as their own row -- NEVER imputed
  R1.3d  detection segment (premarket / rth / post), a conditioning variable

Also joins Phase 9's flag_cross_session_extreme on the (T-1, T0) pair, because
the D7 trigger IS a cross-session ratio and therefore sits inside D4 Amendment
A12's scope: a corporate action between T-1 and T=0 changes the price basis, so
a never-cross can be a split rather than a weak move. Phase 9 measured (T-1,T0)
as its highest-flag-rate pair at 5.66% and left it unexamined.

D4: the reference price is the last T-1 regular-hours TRADE PRICE from
data/filtered/. No spine numeric is read anywhere in this module.

Usage: .venv/Scripts/python.exe research/phase_10/v2_r13_detection.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, NEVER_POOLED, POOLED, config_hash_v2, load_config_v2,
    load_frozen_cohort, quantiles, read_event_trades, rel, session_window, write_json,
)

OUT = "v2_r13_detection.parquet"
OUT_REF = "v2_r13_reference_price.parquet"
OUT_SUMMARY = "v2_r13_detection.json"


def reference_price(cfg, ticker, date, mom) -> dict:
    """R1.3a -- last trade price in the T-1 REGULAR-hours window, tick-derived."""
    d = read_event_trades(cfg, ticker, date, mom, offsets=(-1,))
    w = session_window(date, -1)
    sub = d.get(-1)
    if w is None or sub is None or len(sub) == 0:
        return {"reference_price": np.nan, "reference_undefined": True,
                "reference_reason": "no T-1 session or no T-1 prints",
                "n_tm1_rth_prints": 0}
    ts = sub["sip_timestamp"].to_numpy()
    px = sub["price"].to_numpy(dtype=float)
    m = (ts >= w["rth_open_ns"]) & (ts < w["rth_close_ns"])
    if not m.any():
        return {"reference_price": np.nan, "reference_undefined": True,
                "reference_reason": "T-1 collected but no regular-hours print",
                "n_tm1_rth_prints": 0}
    return {"reference_price": float(px[m][-1]), "reference_undefined": False,
            "reference_reason": None, "n_tm1_rth_prints": int(m.sum())}


def resolve_poll(cross_ns: int, start_ns: int, interval_s: int) -> int:
    """First poll boundary at or after the crossing. interval 0 = instantaneous."""
    if interval_s == 0:
        return int(cross_ns)
    step = int(interval_s) * 1_000_000_000
    off = int(cross_ns) - int(start_ns)
    return int(start_ns) + int(np.ceil(off / step)) * step


def segment_of(ns: int, w: dict) -> str:
    if ns < w["rth_open_ns"]:
        return "premarket"
    if ns < w["rth_close_ns"]:
        return "rth"
    return "post"


def main() -> int:
    cfg = load_config_v2()
    chash = config_hash_v2()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_frozen_cohort(cfg)
    da = cfg["detection_anchor"]
    thresholds = da["thresholds"]
    polls = da["poll_intervals_seconds"]

    rows, refs = [], []
    t_start = time.perf_counter()
    for i, r in enumerate(cohort.itertuples(index=False), 1):
        ref = reference_price(cfg, r.ticker, r.event_date_canonical, r.momentum_pct)
        base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group}
        refs.append({**base, **ref})

        d0 = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d0.get(0)
        w = session_window(r.event_date_canonical, 0)
        ts = np.zeros(0, dtype=np.int64) if t0 is None else t0["sip_timestamp"].to_numpy()
        px = np.zeros(0) if t0 is None else t0["price"].to_numpy(dtype=float)

        for thr in thresholds:
            rec = {**base, "threshold": float(thr),
                   "reference_price": ref["reference_price"],
                   "reference_undefined": ref["reference_undefined"],
                   "n_t0_prints": int(ts.size)}
            if ref["reference_undefined"] or ts.size == 0:
                rec.update({"never_crosses": True, "cross_ns": None,
                            "cross_reason": "reference undefined" if ref["reference_undefined"]
                                            else "no T=0 prints"})
                for p in polls:
                    rec[f"det_ns_poll{p}"] = None
                    rec[f"det_segment_poll{p}"] = None
                    rec[f"det_after_window_end_poll{p}"] = None
                rows.append(rec)
                continue

            level = float(thr) * ref["reference_price"]
            hit = np.flatnonzero(px >= level)
            if hit.size == 0:
                # R1.3c -- never-crosses. Flagged and carried. Never imputed.
                rec.update({"never_crosses": True, "cross_ns": None,
                            "cross_reason": "running max never reaches threshold x reference",
                            "max_t0_price": float(px.max()),
                            "max_over_reference": float(px.max() / ref["reference_price"])})
                for p in polls:
                    rec[f"det_ns_poll{p}"] = None
                    rec[f"det_segment_poll{p}"] = None
                    rec[f"det_after_window_end_poll{p}"] = None
                rows.append(rec)
                continue

            cross_ns = int(ts[hit[0]])
            rec.update({"never_crosses": False, "cross_ns": cross_ns, "cross_reason": None,
                        "cross_idx": int(hit[0]), "cross_price": float(px[hit[0]]),
                        "max_t0_price": float(px.max()),
                        "max_over_reference": float(px.max() / ref["reference_price"])})
            for p in polls:
                dns = resolve_poll(cross_ns, w["start_ns"], p)
                after = dns >= w["end_ns"]
                rec[f"det_ns_poll{p}"] = dns
                rec[f"det_segment_poll{p}"] = segment_of(dns, w)
                rec[f"det_after_window_end_poll{p}"] = bool(after)
                rec[f"det_seconds_from_open_poll{p}"] = float(dns - w["start_ns"]) / 1e9
            rows.append(rec)

        if i % 25 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t_start:.0f}s)", flush=True)

    det = pd.DataFrame(rows)
    ref_df = pd.DataFrame(refs)

    # ---- A12: join Phase 9's (T-1, T0) cross-session magnitude flag, never re-derive
    fp = rel(cfg["paths"]["phase9_cross_session_flags"])
    if os.path.exists(fp):
        f9 = pd.read_parquet(fp)
        pair_col = next((c for c in f9.columns if "pair" in c.lower()), None)
        mp_col = "momentum_pct" if "momentum_pct" in f9.columns else (
            "mp" if "mp" in f9.columns else None)
        if pair_col and mp_col:
            f9 = f9.rename(columns={mp_col: "momentum_pct"})
            f9["event_date_canonical"] = f9["event_date_canonical"].astype(str)
            f9["momentum_pct"] = f9["momentum_pct"].round(2)
            sel = f9[f9[pair_col].astype(str).str.lower().str.replace("-", "_")
                     .isin(["tm1_t0", "('tm1', 't0')", "tm1,t0"])]
            if len(sel) and "flag_cross_session_extreme" in sel.columns:
                det = det.merge(sel[COHORT_KEY + ["flag_cross_session_extreme"]],
                                on=COHORT_KEY, how="left")
    if "flag_cross_session_extreme" not in det.columns:
        det["flag_cross_session_extreme"] = pd.NA

    det.to_parquet(os.path.join(out_dir, OUT), index=False)
    ref_df.to_parquet(os.path.join(out_dir, OUT_REF), index=False)

    # -------------------------------------------------------------- summaries
    ref_thr = da["threshold_reference_point"]
    at_ref = det[np.isclose(det["threshold"], ref_thr)]
    pooled = at_ref[at_ref["cohort_group"].isin(POOLED)]

    def by_group(df, col, agg="sum"):
        return df.groupby("cohort_group")[col].agg(["size", agg]).to_dict("index")

    nc_share_pooled = float(pooled["never_crosses"].mean()) if len(pooled) else float("nan")
    row7_thr = cfg["failure_criteria"]["row_7"]["threshold_max_share"]

    summary = {
        "phase": "10", "version": "v2", "task": "R1.3", "config_hash": chash,
        "decision": "D7 — the detection anchor is derived, not sourced",
        "anchor_independence_statement": cfg["reporting"]["anchor_independence_statement"],
        "n_events": int(len(cohort)),
        "thresholds": thresholds, "poll_intervals_seconds": polls,
        "reference_point": {"threshold": ref_thr, "poll_interval_seconds": da["poll_interval_reference_point"]},

        "r1_3a_reference_price": {
            "n_undefined": int(ref_df["reference_undefined"].sum()),
            "undefined_by_group": by_group(ref_df, "reference_undefined"),
            "undefined_events": ref_df.loc[ref_df["reference_undefined"],
                                           COHORT_KEY + ["cohort_group", "reference_reason"]].to_dict("records"),
            "rule": "carried and flagged, never imputed",
        },

        "r1_3c_never_crosses": {
            "at_reference_threshold": float(ref_thr),
            "n_pooled": int(len(pooled)),
            "n_never_crosses_pooled": int(pooled["never_crosses"].sum()),
            "share_pooled": nc_share_pooled,
            "by_group_at_reference": by_group(at_ref, "never_crosses"),
            "by_threshold": {
                str(t): {
                    "n_pooled": int((np.isclose(det["threshold"], t) & det["cohort_group"].isin(POOLED)).sum()),
                    "n_never_crosses_pooled": int(det.loc[np.isclose(det["threshold"], t)
                                                          & det["cohort_group"].isin(POOLED),
                                                          "never_crosses"].sum()),
                } for t in thresholds
            },
            "events_at_reference": at_ref.loc[at_ref["never_crosses"],
                                              COHORT_KEY + ["cohort_group", "cross_reason",
                                                            "max_over_reference"]].to_dict("records"),
            "d4_explanation": cfg["detection_anchor"]["never_crosses"]["expected_cause"],
            "a12_breakout": {
                "note": "the D7 trigger is a cross-session ratio, so A12 applies",
                "n_flagged_cross_session_extreme": int(
                    at_ref["flag_cross_session_extreme"].fillna(False).astype(bool).sum()),
                "n_never_crosses_and_flagged": int(
                    (at_ref["never_crosses"] & at_ref["flag_cross_session_extreme"].fillna(False).astype(bool)).sum()),
            },
        },

        "r1_3b_detection_time": {
            f"poll_{p}s": {
                "label": "instantaneous — UPPER BOUND ON RUNWAY, physically impossible"
                         if p == 0 else f"{p}s poll",
                "seconds_from_0400_pooled": quantiles(
                    pooled.loc[~pooled["never_crosses"], f"det_seconds_from_open_poll{p}"]),
                "n_after_window_end": int(
                    pooled[f"det_after_window_end_poll{p}"].fillna(False).astype(bool).sum()),
            } for p in polls
        },

        "r1_3d_detection_segment": {
            f"poll_{p}s": {
                "pooled": pooled.loc[~pooled["never_crosses"], f"det_segment_poll{p}"]
                                .value_counts().to_dict(),
                "by_group": {
                    g: sub.loc[~sub["never_crosses"], f"det_segment_poll{p}"].value_counts().to_dict()
                    for g, sub in at_ref.groupby("cohort_group")
                },
            } for p in polls
        },

        "failure_row_7": {
            "mode": cfg["failure_criteria"]["row_7"]["mode"],
            "observed_share": nc_share_pooled,
            "threshold": row7_thr,
            "pass": bool(nc_share_pooled <= row7_thr),
        },

        "timing": {"total_seconds": round(time.perf_counter() - t_start, 1),
                   "ceiling": cfg["runtime_ceilings"]["detection_anchor_seconds_aggregate"]},
        "source": "research/phase_10/v2_r13_detection.py:main",
        "artifacts": [f"{cfg['paths']['out_artifacts']}{OUT}",
                      f"{cfg['paths']['out_artifacts']}{OUT_REF}"],
    }
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    print(f"reference price undefined: {summary['r1_3a_reference_price']['n_undefined']}/{len(cohort)}")
    print(f"never-crosses @ thr {ref_thr}: {summary['r1_3c_never_crosses']['n_never_crosses_pooled']}"
          f"/{len(pooled)} pooled = {nc_share_pooled:.3f}  (row 7 threshold {row7_thr})")
    for p in polls:
        q = summary["r1_3b_detection_time"][f"poll_{p}s"]["seconds_from_0400_pooled"]
        lbl = "instant" if p == 0 else f"{p}s"
        print(f"  poll {lbl:>7}: n={q['n']:>3} det median {q['q50']:,.0f}s from 04:00")
    rp = da["poll_interval_reference_point"]
    print(f"segments @ poll {rp}s: {summary['r1_3d_detection_segment']['poll_' + str(rp) + 's']['pooled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
