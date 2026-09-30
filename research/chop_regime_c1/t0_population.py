"""
Chop regime C1, T0 -- freeze checks, population, the quote-size unit census, the section 6 tests, and timing.

  population    the development slice (slices.parquet) against S2's tau table and b2's tau_available; the 56
                quarantined events; tau from S2's t1_group_a c__tau_d_ns (the tau S2's entries used), int64 on read,
                equal to S2's tau checkpoint d_ns
  census        per year 2020-22, a seeded sample of development-slice events: D17-valid displayed sizes (share that
                are multiples of 100) and, in regular hours, every trade printing at the D16 touch against the displayed
                size on the touched side; the config's rule decides shares / lots / not established (row 4)
  tests         the causality and segment tests (rows 1, 2) and buckets_core against Brief 1's bucketize
  timing        T1-T4 plus the hindsight columns on every quarantined event with tau, one process, wall time per event;
                wall ~ a + b x prints fitted by least squares and summed over the development slice's per-event print
                counts (S2 t2_event_meta n_day_prints), divided by the worker count (row 10: > 6 hours is a HARD STOP)

Writes artifacts/t0_population.parquet, t0_census.parquet, t0_timing.parquet, t0_summary.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t0_population.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402
import measures as M  # noqa: E402

B1 = C.B1


def census_event(eid: str, date: str) -> dict:
    q = C.read_quotes(eid)
    if q is None:
        return {"event_id": eid, "has_quotes": False}
    t0400, t2000 = B1.et_ns(date, "04:00:00"), B1.et_ns(date, "20:00:00")
    m = (q["ts"] >= t0400) & (q["ts"] < t2000)
    exc = C.d17_excluded(q["bid"][m], q["ask"][m], q["bsz"][m], q["asz"][m])
    bs, as_ = q["bsz"][m][~exc], q["asz"][m][~exc]
    sizes = np.r_[bs, as_]
    out = {"event_id": eid, "has_quotes": True, "n_valid_quotes": int((~exc).sum()), "n_sizes": int(sizes.size),
           "n_mult100": int((np.mod(sizes, 100) == 0).sum()), "size_median": float(np.median(sizes)) if sizes.size else np.nan}
    # regular-hours trades at the D16 touch
    book = C.QuoteBook(q, date, 1.0)
    rth = book.seg[1]
    tr = B1.read_trades(eid, with_conditions=False)
    op, cl = B1.rth_bounds_ns(date)
    k = (tr["ts"] >= op) & (tr["ts"] < cl)
    ts, px, sz = tr["ts"][k], tr["px"][k], tr["sz"][k]
    if rth is None or rth["vts"].size == 0 or ts.size == 0:
        out.update({"n_at_touch": 0})
        return out
    i = np.searchsorted(rth["vts"], ts, "right") - 1
    ok = i >= 0
    i = np.maximum(i, 0)
    at_ask = ok & (px == rth["vask"][i]) & (sz > 0)
    at_bid = ok & (px == rth["vbid"][i]) & (sz > 0) & ~at_ask
    disp = np.where(at_ask, rth["vasz"][i], rth["vbsz"][i])
    sel = at_ask | at_bid
    ratio = sz[sel] / disp[sel]
    out.update({"n_at_touch": int(sel.sum()), "ratio_median": float(np.median(ratio)) if ratio.size else np.nan,
                "share_trade_le_displayed": float((ratio <= 1).mean()) if ratio.size else np.nan, "_ratios": ratio})
    return out


def main() -> int:
    t_start = time.perf_counter()
    cfg = C.load_cfg()
    pop = C.load_population()
    sl = pd.read_parquet(C.src("slices"))
    b2 = pd.read_parquet(C.src("b2_population"), columns=["event_id", "tau_available", "tau_reason", "tau_ns"])
    ck = pd.read_parquet(C.src("s2_checkpoints"), columns=["event_id", "time", "d_ns"])
    ck = ck[ck["time"] == "tau"].set_index("event_id")["d_ns"]

    # ---------------- population asserts
    dev_all = sl[sl["slice"] == "development"]
    q_all = sl[sl["slice"] == "dev_quarantine"]
    b2x = b2.set_index("event_id")
    dev_tau = int(b2x.loc[dev_all["event_id"], "tau_available"].sum())
    q_tau = int(b2x.loc[q_all["event_id"], "tau_available"].sum())
    dev = C.dev_slice(pop)
    qu = C.quarantine(pop)
    assert len(dev) == dev_tau, f"development slice with tau: C1 {len(dev)} vs b2 {dev_tau}"
    assert len(qu) == q_tau, f"quarantine with tau: C1 {len(qu)} vs b2 {q_tau}"
    assert set(qu["dev_group"]) <= {"dev_v3", "dev_v4_sidecar"} and dev["dev_group"].isna().all()
    assert not set(dev["event_id"]) & set(qu["event_id"])
    d0, d1 = cfg["population"]["slice_dates"]
    assert dev["event_date_canonical"].between(d0, d1).all(), "a development-slice event outside 2020-22"
    assert pop["tau_ns"].dtype == np.int64
    tau_vs_s2 = pop["event_id"].map(ck).astype("int64")
    assert (tau_vs_s2 == pop["tau_ns"]).all(), "C1 tau differs from S2's tau checkpoint"
    assert (pop["tau_ns"] >= pop["tau_stored_ns"]).all() and (pop["tau_ns"] >= pop["tau_exact_ns"]).all()
    no_tau_q = q_all[~q_all["event_id"].isin(qu["event_id"])].merge(b2[["event_id", "tau_reason"]], on="event_id")
    no_tau_dev = dev_all[~dev_all["event_id"].isin(dev["event_id"])].merge(b2[["event_id", "tau_reason"]], on="event_id")
    pop.to_parquet(C.art("t0_population.parquet"), index=False)

    # ---------------- tests
    tests = {"causality": M.causality_test(), "segment": M.segment_test(), "bucket_equality": M.bucket_equality_test(200)}
    assert tests["causality"]["passes"], f"HARD STOP row 1: {tests['causality']}"
    assert tests["segment"]["passes"], f"HARD STOP row 2: {tests['segment']}"
    assert tests["bucket_equality"]["passes"], f"bucket construction differs from Brief 1's: {tests['bucket_equality']}"
    print("tests pass", flush=True)

    # ---------------- quote-size census
    cc = cfg["measures"]["quote_size_census"]
    rng = np.random.default_rng(cc["seed"])
    rows, years = [], {}
    for y in cc["years"]:
        ev = dev[dev["year"] == y].sort_values("event_id")
        pick = ev.iloc[np.sort(rng.choice(len(ev), size=min(cc["sample_events_per_year"], len(ev)), replace=False))]
        ratios = []
        for r in pick.itertuples():
            c = census_event(r.event_id, r.event_date_canonical)
            ratios.append(c.pop("_ratios", np.zeros(0)))
            rows.append({"year": y, **c})
        yr = pd.DataFrame([x for x in rows if x["year"] == y])
        rat = np.concatenate(ratios) if ratios else np.zeros(0)
        n_sizes, n_m100 = int(yr["n_sizes"].fillna(0).sum()), int(yr["n_mult100"].fillna(0).sum())
        share_m100 = n_m100 / n_sizes if n_sizes else np.nan
        med_ratio = float(np.median(rat)) if rat.size else np.nan
        if share_m100 >= 0.95 and med_ratio <= 1:
            unit, mult = "shares", 1.0
        elif share_m100 <= 0.05 and med_ratio >= 10:
            unit, mult = "lots", 100.0
        else:
            unit, mult = "not_established", None
        years[str(y)] = {"events": int(len(yr)), "events_with_quotes": int(yr["has_quotes"].sum()), "sizes": n_sizes, "share_multiple_of_100": share_m100,
                         "size_median_of_event_medians": float(yr["size_median"].median()), "at_touch_trades": int(rat.size),
                         "median_trade_over_displayed": med_ratio, "share_trade_le_displayed": float((rat <= 1).mean()) if rat.size else np.nan,
                         "unit": unit, "depth_multiplier": mult}
        print(y, years[str(y)], flush=True)
    pd.DataFrame(rows).to_parquet(C.art("t0_census.parquet"), index=False)

    # ---------------- timing: T1-T4 and the hindsight columns on the quarantined events
    halts = B1.load_halt_labels()
    trows = []
    for rec in qu.to_dict("records"):
        mult = years.get(str(rec["year"]), {}).get("depth_multiplier", 1.0)
        t0 = time.perf_counter()
        out = M.build_event(rec, cfg, mult, halts.get(f"{rec['ticker']}|{rec['event_date_canonical']}", []))
        trows.append({"event_id": rec["event_id"], "seconds": time.perf_counter() - t0, "n_prints": out["n_prints"], "n_quotes": out["n_quotes"],
                      "moments": len(out["rows"]), "rate_rungs": len(out["rate_rungs"]), "sf_rungs": len(out["sf_rungs"])})
    tm = pd.DataFrame(trows)
    tm.to_parquet(C.art("t0_timing.parquet"), index=False)
    X = np.c_[np.ones(len(tm)), tm["n_prints"].to_numpy(float)]
    coef, *_ = np.linalg.lstsq(X, tm["seconds"].to_numpy(), rcond=None)
    dp = dev["n_day_prints"].to_numpy(float)
    assert np.isfinite(dp).all(), "a development-slice event without S2's print count"
    serial_s = float(np.maximum(coef[0] + coef[1] * dp, 0).sum())
    workers = C.B2.cpu_workers()
    wall_h = serial_s / workers / 3600
    timing = {"events_timed": int(len(tm)), "seconds_total": float(tm["seconds"].sum()), "seconds_median": float(tm["seconds"].median()),
              "seconds_max": float(tm["seconds"].max()), "fit": {"a_s": float(coef[0]), "b_s_per_print": float(coef[1])},
              "dev_events": int(len(dev)), "dev_prints_total": float(dp.sum()), "serial_hours": serial_s / 3600, "workers": workers,
              "extrapolated_wall_hours": wall_h, "ceiling_hours": cfg["runtime_ceiling_hours"], "row10_fires": bool(wall_h > cfg["runtime_ceiling_hours"])}
    summary = {
        "config_hash": C.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1),
        "tau_source": "results/shape_classifier/s2/artifacts/t1_group_a.parquet c__tau_d_ns (S2 tau_d = max(stored tau, crossing print)); int64 on read; equals S2 t2_checkpoints d_ns at 'tau' for every event",
        "population": {"slices_development": int(len(dev_all)), "development_with_tau": int(len(dev)), "b2_development_tau_available": dev_tau,
                       "development_without_tau": no_tau_dev["tau_reason"].value_counts().to_dict(),
                       "slices_quarantine": int(len(q_all)), "quarantine_with_tau": int(len(qu)), "b2_quarantine_tau_available": q_tau,
                       "quarantine_without_tau": no_tau_q[["event_id", "tau_reason"]].to_dict("records"),
                       "quarantine_by_group": qu["dev_group"].value_counts().to_dict(),
                       "development_by_year": dev["year"].value_counts().sort_index().to_dict(),
                       "development_by_tau_segment": dev["tau_segment"].value_counts().to_dict(),
                       "development_quotes_ingested_false": int((~dev["quotes_ingested"]).sum()),
                       "development_quotes_event_day_false": int((~dev["quotes_event_day"]).sum()),
                       "development_v_pre_undefined": int(dev["v_pre"].isna().sum()),
                       "development_shares_outstanding_missing": int(dev["shs"].isna().sum()),
                       "tau_after_stored": int((pop["tau_ns"] > pop["tau_stored_ns"]).sum())},
        "tests": tests, "quote_size_census": years, "row4_years": [y for y, v in years.items() if v["unit"] == "not_established"],
        "timing": timing,
    }
    C.write_json("t0_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("population", "quote_size_census", "timing")}, indent=1, default=str))
    if timing["row10_fires"]:
        print(f"HARD STOP row 10: extrapolated wall {wall_h:.2f} h > {cfg['runtime_ceiling_hours']} h")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
