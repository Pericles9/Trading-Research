"""
Phase 10d T4 -- assembly across the pre-registered grid. First real-event read; the T2
control gate passed before this script existed in runnable form.

The LABELLING stage is 10c's, imported and called, never re-implemented: tie collapse,
D1 sweep aggregation, centered clock-time rolling median clipped at the session blocks,
the per-event derived data floor, the Poisson peak-survival rule, and the argmax-void
envelope boundary. 10d touches only what happens to the label array afterwards.

Outputs
  t4_cell_summary.parquet  per (event, kernel, K, d, min_prints, sep) -- count, duration
                           quantiles, n_prints composition, prints inside bursts, move share
  t4_subbursts.parquet     per sub-burst, every grid cell, degeneracy flagged
  t4_break_cause.parquet   per (event, kernel) run-break census by cause  [T4c]
  t4_waterfall.json        row counts in and out of every filter

Usage: .venv/Scripts/python.exe research/phase_10d/t4_assembly.py
"""
from __future__ import annotations

import hashlib
import importlib.util as ilu
import itertools
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
# NOTE: research/phase_10 and research/phase_10c BOTH define common.py. Only
# phase_10 goes on sys.path; 10c's is loaded by explicit spec, exactly as
# research/phase_10c/s1_t1_subbursts.py does it. Adding phase_10c to sys.path
# shadows the name and raises a circular ImportError.
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(ROOT, "research", "phase_10c", "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
_s2 = ilu.spec_from_file_location("s1t1", os.path.join(ROOT, "research", "phase_10c",
                                                      "s1_t1_subbursts.py"))
s1t1 = ilu.module_from_spec(_s2); _s2.loader.exec_module(s1t1)

from assemble import (SEP_BRIDGEABLE, SEP_HARD_BREAK, assemble,  # noqa: E402
                      break_cause_census, label_intervals, raw_runs)

ART = os.path.join(ROOT, "results", "phase_10d", "artifacts")
KEY = ["ticker", "event_date_canonical"]


def conf():
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        return json.load(f)


def chash_of(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8]


def qstats(a):
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return dict(n=0, q25=np.nan, median=np.nan, q75=np.nan, max=np.nan, total=0.0)
    return dict(n=int(a.size), q25=float(np.quantile(a, .25)), median=float(np.median(a)),
                q75=float(np.quantile(a, .75)), max=float(a.max()), total=float(a.sum()))


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    C10D = conf()
    chash = chash_of(C10D)

    cfg10c = c10c.load_cfg()
    chash10c = c10c.cfg_hash()
    # cfg_hash() hashes raw bytes and is therefore line-ending sensitive. Assert against
    # both forms so the check means "this is the committed 10c config", not "this checkout
    # happens to use the same newline convention as the machine that wrote the digest".
    with open(rel("config/phase_10c.json"), "rb") as _f:
        _b = _f.read()
    _CRLF, _LF = bytes([13, 10]), bytes([10])
    chash10c_lf = hashlib.sha256(_b.replace(_CRLF, _LF)).hexdigest()[:8]
    exp_raw = C10D["upstream_10c"]["config_hash_expected_raw_crlf"]
    exp_lf = C10D["upstream_10c"]["config_hash_expected_lf"]
    assert chash10c in (exp_raw, exp_lf) or chash10c_lf == exp_lf, (
        f"10c config hash raw={chash10c} lf={chash10c_lf} matches neither pre-registered "
        f"value (raw {exp_raw} / lf {exp_lf})")
    F = float(c10c.class_m(cfg10c)["D4_median_precision_factor"])
    d1_us = float(c10c.class_m(cfg10c)["D1_sweep_floor_us"])
    KERNELS = C10D["upstream_10c"]["kernels_min"]
    VARIANTS = C10D["upstream_10c"]["variants"]

    Ks = C10D["merge_grid"]["K"]
    ds = C10D["merge_grid"]["d"]
    MPS = C10D["min_prints_grid"]["values"]
    SEPS = C10D["separator_grid"]["values"]
    DEGEN = {tuple(x) for x in C10D["merge_grid"]["degenerate_cells"]}
    # 12 non-degenerate + the identity representative of the 8 degenerate copies
    KD = [(0, 0.0)] + [(K, d) for K, d in itertools.product(Ks, ds) if (K, d) not in DEGEN]
    assert len(KD) == 13, len(KD)

    dev = c10c.load_dev_sample(cfg10c)
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)

    wf = {"events_in_dev_sample": int(len(dev)), "events_with_prints": 0,
          "prints_raw": 0, "prints_tie_collapsed": 0, "prints_after_D1": 0,
          "intervals": 0, "zero_intervals_dropped": 0,
          "event_kernel_cells": 0, "cells_insufficient_context": 0,
          "cells_no_threshold": 0, "cells_ok": 0,
          "assembly_configurations": 0, "subburst_rows": 0}

    cell_rows, sb_rows, bc_rows, ctx_rows = [], [], [], []
    t0 = time.perf_counter()

    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg10c, r.ticker, r.event_date_canonical,
                                  r.momentum_pct, offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        wf["events_with_prints"] += 1
        raw_ts = s0["sip_timestamp"].to_numpy()
        raw_px = s0["price"].to_numpy(dtype=np.float64)
        wf["prints_raw"] += int(raw_ts.size)

        # ---- 10c's tie collapse + D1 aggregation, verbatim
        uniq, inv = np.unique(raw_ts, return_inverse=True)
        wf["prints_tie_collapsed"] += int(uniq.size)
        sz = s0["size"].to_numpy(dtype=np.float64)
        wsum = np.bincount(inv, weights=raw_px * sz, minlength=uniq.size)
        ssum = np.bincount(inv, weights=sz, minlength=uniq.size)
        px_u = np.where(ssum > 0, wsum / np.maximum(ssum, 1e-12),
                        np.bincount(inv, weights=raw_px, minlength=uniq.size)
                        / np.maximum(np.bincount(inv, minlength=uniq.size), 1))
        agg_ts, _ = c10c.sweep_aggregate(uniq, d1_us)
        gi = np.searchsorted(uniq, agg_ts)
        bnd = np.append(gi, uniq.size)
        grp = np.repeat(np.arange(agg_ts.size), np.diff(bnd))
        gw = np.bincount(grp, weights=px_u[:uniq.size] * ssum, minlength=agg_ts.size)
        gs = np.bincount(grp, weights=ssum, minlength=agg_ts.size)
        agg_px = np.where(gs > 0, gw / np.maximum(gs, 1e-12), px_u[gi])
        wf["prints_after_D1"] += int(agg_ts.size)
        if agg_ts.size < 20:
            continue

        dt_s = np.diff(agg_ts).astype(np.float64) / 1e9
        keep = dt_s > 0
        wf["zero_intervals_dropped"] += int((~keep).sum())
        # 10c indexes agg_ts with FILTERED interval indices. That is only sound when the
        # filter drops nothing. Asserted rather than assumed -- a failure here is a 10c
        # defect to report, not something to work around.
        assert keep.all(), (f"{r.ticker} {r.event_date_canonical}: "
                            f"{int((~keep).sum())} zero-length intervals -- 10c's "
                            f"agg_ts[run[0]] indexing would be misaligned")
        li = np.log10(dt_s[keep])
        mid = ((agg_ts[:-1].astype(np.float64) + agg_ts[1:].astype(np.float64)) / 2.0)[keep]
        wf["intervals"] += int(li.size)

        b = c10c.session_bounds(r.event_date_canonical)
        if b is None:
            continue
        sigma = float(np.std(li, ddof=1))
        floor = c10c.median_se_min_count(sigma, F)
        edges = np.array([b["start_ns"], b["rth_open_ns"], b["rth_close_ns"], b["end_ns"]],
                         dtype=np.float64)
        seg_i = np.clip(np.searchsorted(edges, mid, "right") - 1, 0, len(edges) - 2)

        tot_move = float(np.abs(np.diff(agg_px)).sum())
        n_prints_session = int(agg_ts.size)
        peak_idx = int(np.argmax(agg_px))
        peak_ns = int(agg_ts[peak_idx])

        # ---- per-variant segment / anchor context (variant changes only this)
        for v in VARIANTS:
            row = det[(det.ticker == r.ticker)
                      & (det.event_date_canonical == r.event_date_canonical)
                      & (np.isclose(det.threshold, v))]
            seg, det_ns = s1t1.variant_segment(
                row.iloc[0].to_dict() if len(row) else None, cal)
            ctx_rows.append({"ticker": r.ticker,
                             "event_date_canonical": r.event_date_canonical,
                             "variant": float(v), "segment": seg,
                             "det_ns": det_ns, "peak_ns": peak_ns})

        for k_min in KERNELS:
            wf["event_kernel_cells"] += 1
            half = k_min * 60.0 * 1e9 / 2.0
            ser = pd.Series(li, index=pd.to_datetime(mid.astype("int64"), unit="ns"))
            loc_med = np.full(li.size, np.nan)
            wcount = np.zeros(li.size)
            win = f"{int(k_min)}min"
            for _bi in np.unique(seg_i):
                m_ = seg_i == _bi
                sub = ser[m_]
                if sub.size == 0:
                    continue
                _roll = sub.rolling(win, center=True, min_periods=1)
                loc_med[m_] = _roll.median().to_numpy()
                wcount[m_] = _roll.count().to_numpy()

            ok = wcount >= floor if np.isfinite(floor) else np.zeros(li.size, bool)
            base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                    "cohort_group": r.cohort_group, "is_sidecar": bool(r.is_sidecar),
                    "kernel_min": float(k_min), "sigma_log10": sigma,
                    "derived_floor": float(floor), "n_intervals": int(li.size),
                    "n_prints_session": n_prints_session,
                    "ok_fraction": float(ok.mean())}

            if ok.sum() < C10D["upstream_10c"]["cell_level_ok_minimum"]:
                wf["cells_insufficient_context"] += 1
                cell_rows.append({**base, "label": "insufficient_context",
                                  "threshold_norm": np.nan, "void": np.nan,
                                  "K": np.nan, "d": np.nan, "min_prints": np.nan,
                                  "sep": None, "degenerate": None, "n_objects": 0})
                continue

            norm = li - loc_med
            nv = norm[ok & np.isfinite(norm)]
            e_lo, e_hi = np.floor(nv.min() * 10) / 10, np.ceil(nv.max() * 10) / 10 + 0.1
            bins = np.arange(e_lo, e_hi, 0.1)
            cnt, _ = np.histogram(nv, bins=bins)
            centers = (bins[:-1] + bins[1:]) / 2.0
            dens = cnt / (cnt.sum() * 0.1)
            pks, _ = s1t1.peaks_poisson(cnt)
            env = s1t1.envelope_boundary(centers, dens, pks) if pks.size >= 2 else None
            if env is None:
                wf["cells_no_threshold"] += 1
                cell_rows.append({**base, "label": "no_threshold", "threshold_norm": np.nan,
                                  "void": np.nan, "K": np.nan, "d": np.nan,
                                  "min_prints": np.nan, "sep": None, "degenerate": None,
                                  "n_objects": 0})
                continue

            wf["cells_ok"] += 1
            thr = float(env["loc"])
            inb = label_intervals(norm, ok, thr)

            # ---- T4c break-cause census, on the raw (unmerged) run structure
            bc = break_cause_census(inb, norm, ok, thr)
            bc_rows.append({**{kk: base[kk] for kk in
                               ("ticker", "event_date_canonical", "kernel_min")},
                            "threshold_norm": thr, "void": float(env["void"]), **bc})

            for (K, dd), mp, sp in itertools.product(KD, MPS, SEPS):
                res = assemble(norm, ok, agg_ts, thr, K=K, d=dd, min_prints=mp, sep=sp,
                               inb=inb)
                wf["assembly_configurations"] += 1
                dur = res["duration_s"]
                st = qstats(dur)
                npr = res["n_prints"]
                cell_rows.append({
                    **base, "label": "ok", "threshold_norm": thr,
                    "void": float(env["void"]), "K": int(K), "d": float(dd),
                    "min_prints": int(mp), "sep": sp,
                    "degenerate": bool((K, dd) == (0, 0.0)),
                    "n_objects": res["n_objects"],
                    "n_objects_before_floor": res["n_objects_before_floor"],
                    "n_deleted_by_floor": res["n_deleted_by_floor"],
                    "dur_q25": st["q25"], "dur_median": st["median"],
                    "dur_q75": st["q75"], "dur_max": st["max"], "dur_total": st["total"],
                    "n_prints_in_bursts": int(npr.sum()) if npr.size else 0,
                    "share_2print": float((npr == 2).mean()) if npr.size else np.nan,
                    "n_2print": int((npr == 2).sum()) if npr.size else 0,
                    "prints_share_of_session": (float(npr.sum()) / n_prints_session
                                                if n_prints_session else np.nan),
                    "n_merges_total": int(res["n_merges"].sum()) if res["n_objects"] else 0,
                })
                # per-sub-burst detail
                if res["n_objects"]:
                    s_i, e_i = res["start_idx"], res["end_idx"]
                    mv = np.abs(agg_px[e_i + 1] - agg_px[s_i])
                    sb_rows.append(pd.DataFrame({
                        "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                        "kernel_min": np.float32(k_min), "K": np.int8(K),
                        "d": np.float32(dd), "min_prints": np.int8(mp), "sep": sp,
                        "start_ns": res["start_ns"], "end_ns": res["end_ns"],
                        "duration_s": dur.astype(np.float64),
                        "n_prints": npr.astype(np.int32),
                        "n_intervals_burst": res["n_intervals_burst"].astype(np.int32),
                        "n_merges": res["n_merges"].astype(np.int16),
                        "abs_move": mv.astype(np.float64),
                        "move_share": (mv / tot_move if tot_move > 0
                                       else np.full(mv.size, np.nan)).astype(np.float64),
                        "peak_ns": np.int64(peak_ns),
                    }))
                    wf["subburst_rows"] += res["n_objects"]

        if i % 5 == 0:
            print(f"  {i}/{len(dev)}  ({time.perf_counter()-t0:.0f}s, "
                  f"{wf['assembly_configurations']:,} configs)", flush=True)

    cells = pd.DataFrame(cell_rows)
    sb = pd.concat(sb_rows, ignore_index=True) if sb_rows else pd.DataFrame()
    bc = pd.DataFrame(bc_rows)
    ctx = pd.DataFrame(ctx_rows)

    os.makedirs(ART, exist_ok=True)
    cells.to_parquet(os.path.join(ART, "t4_cell_summary.parquet"), index=False)
    sb.to_parquet(os.path.join(ART, "t4_subbursts.parquet"), index=False,
                  compression="zstd")
    bc.to_parquet(os.path.join(ART, "t4_break_cause.parquet"), index=False)
    ctx.to_parquet(os.path.join(ART, "t4_variant_context.parquet"), index=False)

    wf["wall_clock_s"] = round(time.perf_counter() - t0, 1)
    wf["config_hash"] = chash
    wf["config_hash_10c_raw"] = chash10c
    wf["config_hash_10c_lf"] = chash10c_lf
    wf["config_hash_10c_recorded_by_stage1_digest"] = "998c2461"
    wf["_config_hash_note"] = (
        "Stage 1's digest records 998c2461, which is the config as of commit "
        "0f079a9. Commit 39ec87e edited config/phase_10c.json inside Stage 1, "
        "before 692d9d0 produced the T1 artifacts, so the recorded hash is stale "
        "by one commit. 10d asserts the committed file and reports the gap.")
    wf["kd_cells_computed"] = len(KD)
    wf["kd_cells_degenerate_collapsed"] = len(DEGEN)
    wf["_degenerate_note"] = (
        "8 of the 20 (K,d) combinations are bit-identical to the identity and are "
        "COLLAPSED to the single (0, 0.0) row rather than written 8 times. C1 proved the "
        "identity at T2. The row is flagged degenerate=True in t4_cell_summary.parquet.")
    with open(os.path.join(ART, "t4_waterfall.json"), "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)

    print("\nwaterfall:")
    for k, v in wf.items():
        if not k.startswith("_"):
            print(f"  {k:<34} {v}")
    print(f"\ncell_summary {len(cells):,} rows | subbursts {len(sb):,} rows "
          f"({os.path.getsize(os.path.join(ART,'t4_subbursts.parquet'))/1e6:.0f} MB) | "
          f"break_cause {len(bc):,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
