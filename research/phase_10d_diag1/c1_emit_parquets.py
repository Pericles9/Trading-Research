"""
10d Diag1 charts addendum, C1 -- emit the three parquets the plotting script consumes.

NOTHING IS RECOMPUTED AS A MEASUREMENT. The frame pipeline is Diag1's, imported from
t1_frames.py, which in turn imports 10c's labelling path. The only difference from Diag1 T1
is what gets WRITTEN: T1 stored one summary row per frame, and the chart needs the per-BIN
density profile plus the ladder in long form. Same frames, same ladder, same numbers.

Coverage: the union of the 43 tape-review events and Diag1's 7 pre-registered subset,
45 events, at all three kernels. ACET and OST are in the subset but not the tape set --
10c declines both at 8 min -- so they appear at 32 min only. No event is dropped.

Every frame is emitted, thin ones included, with its density. `has_boundary` is False for a
thin frame so nothing downstream mistakes it for a resolved one; the chart washes it grey.

Writes incrementally through pyarrow.ParquetWriter -- the frames table runs to ~19M rows and
materialising it as one DataFrame is not worth the memory.

Usage: .venv/Scripts/python.exe research/phase_10d_diag1/c1_emit_parquets.py
"""
from __future__ import annotations

import importlib.util as ilu
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
_s = ilu.spec_from_file_location("t1f", os.path.join(HERE, "t1_frames.py"))
t1f = ilu.module_from_spec(_s); _s.loader.exec_module(t1f)
c10c = t1f.c10c

ART = os.path.join(ROOT, "results", "phase_10d_diag1", "artifacts")

FRAME_SCHEMA = pa.schema([
    ("event_id", pa.string()), ("kernel_min", pa.float64()),
    ("frame_idx", pa.int32()), ("frame_ts_ns", pa.int64()),
    ("local_median_s", pa.float64()), ("n_intervals", pa.int32()),
    ("has_boundary", pa.bool_()), ("bin_center_norm", pa.float64()),
    ("density", pa.float64())])
LADDER_SCHEMA = pa.schema([
    ("event_id", pa.string()), ("kernel_min", pa.float64()),
    ("frame_idx", pa.int32()), ("frame_ts_ns", pa.int64()),
    ("rank", pa.int32()), ("boundary_norm", pa.float64()),
    ("boundary_abs_s", pa.float64()), ("void", pa.float64())])
TAPE_SCHEMA = pa.schema([("event_id", pa.string()), ("ts_ns", pa.int64()),
                         ("price", pa.float64())])


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d_diag1_charts.json"),
              encoding="utf-8") as f:
        CC = json.load(f)
    with open(os.path.join(ROOT, "config", "phase_10d_diag1.json"), encoding="utf-8") as f:
        C1 = json.load(f)
    with open(os.path.join(ROOT, CC["upstream"]["tape_review_manifest"]),
              encoding="utf-8") as f:
        tape_man = json.load(f)

    tape_set = [(c["ticker"], c["event_date_canonical"]) for c in tape_man["charts"]]
    subset = [(e["ticker"], e["event_date_canonical"]) for e in C1["event_subset"]["events"]]
    want = list(dict.fromkeys(tape_set + subset))
    assert len(want) == CC["coverage"]["n_events_expected"], (
        f"{len(want)} events, config expects {CC['coverage']['n_events_expected']}")

    cfg10c = c10c.load_cfg()
    F = float(c10c.class_m(cfg10c)["D4_median_precision_factor"])
    d1_us = float(c10c.class_m(cfg10c)["D1_sweep_floor_us"])
    KERNELS = CC["coverage"]["kernels_min"]
    div = int(C1["frames"]["step_divisor"])
    min_iv = int(CC["emission"]["thin_floor_intervals"])
    assert min_iv == int(C1["frames"]["min_intervals_per_frame"]), (
        "thin floor must match Diag1's, or the wash marks a different set than the "
        "ladder declined")
    tape_max = int(CC["emission"]["tape_max_points_per_event"])

    dev = c10c.load_dev_sample(cfg10c)
    dev = dev[dev.apply(lambda r: (r.ticker, r.event_date_canonical) in want, axis=1)]
    assert len(dev) == len(want), f"resolved {len(dev)} of {len(want)}"

    fw = pq.ParquetWriter(os.path.join(ART, "diag1_frames.parquet"), FRAME_SCHEMA,
                          compression="zstd")
    lw = pq.ParquetWriter(os.path.join(ART, "diag1_ladder.parquet"), LADDER_SCHEMA,
                          compression="zstd")
    tw = pq.ParquetWriter(os.path.join(ART, "diag1_tape.parquet"), TAPE_SCHEMA,
                          compression="zstd")

    n_frame_rows = n_lad_rows = n_tape_rows = 0
    cells_ok = cells_declined = 0
    t0 = time.perf_counter()

    for i, r in enumerate(dev.itertuples(index=False), 1):
        eid = f"{r.ticker} {r.event_date_canonical}"
        tape_written = False
        for k_min in KERNELS:
            ev = t1f.event_arrays(cfg10c, r, F, d1_us, k_min)
            if ev is None:
                cells_declined += 1
                continue

            if not tape_written:
                ts, px = ev["agg_ts"], ev["agg_px"]
                if ts.size > tape_max:
                    idx = np.unique(np.concatenate([
                        np.linspace(0, ts.size - 1, tape_max).astype(np.int64),
                        [0, ts.size - 1]]))
                else:
                    idx = np.arange(ts.size)
                tw.write_table(pa.Table.from_pydict(
                    {"event_id": pa.array([eid] * idx.size, pa.string()),
                     "ts_ns": pa.array(ts[idx].astype(np.int64), pa.int64()),
                     "price": pa.array(px[idx].astype(np.float64), pa.float64())},
                    schema=TAPE_SCHEMA))
                n_tape_rows += int(idx.size)
                tape_written = True

            ok_fin = ev["ok"] & np.isfinite(ev["norm"])
            nv = ev["norm"][ok_fin]
            if nv.size < C1["upstream"]["cell_level_ok_minimum"]:
                cells_declined += 1
                continue
            cells_ok += 1

            # the event's full-session grid -- 10c's rule, fixed across every frame
            e_lo = np.floor(nv.min() * 10) / 10
            e_hi = np.ceil(nv.max() * 10) / 10 + 0.1
            bins = np.arange(e_lo, e_hi, 0.1)
            centers = (bins[:-1] + bins[1:]) / 2.0
            nb = centers.size

            mid_ok = ev["mid"][ok_fin]
            norm_ok = ev["norm"][ok_fin]
            locmed_ok = ev["loc_med"][ok_fin]
            o = np.argsort(mid_ok, kind="stable")
            mid_ok, norm_ok, locmed_ok = mid_ok[o], norm_ok[o], locmed_ok[o]

            step_ns = k_min * 60.0 * 1e9 / div
            half = k_min * 60.0 * 1e9 / 2.0
            t_lo, t_hi = float(ev["bounds"]["start_ns"]), float(ev["bounds"]["end_ns"])
            times = t_lo + np.arange(int(np.floor((t_hi - t_lo) / step_ns)) + 1) * step_ns
            lo = np.searchsorted(mid_ok, times - half, "left")
            hi = np.searchsorted(mid_ok, times + half, "right")

            f_ts, f_lm, f_n, f_hb, f_bc, f_de, f_fi = [], [], [], [], [], [], []
            l_fi, l_ts, l_rk, l_bn, l_ba, l_vd = [], [], [], [], [], []

            for fi, (t, a, b) in enumerate(zip(times, lo, hi)):
                n_in = int(b - a)
                lm = float(10.0 ** np.median(locmed_ok[a:b])) if n_in else np.nan
                if n_in:
                    cnt, _ = np.histogram(norm_ok[a:b], bins=bins)
                    tot = cnt.sum()
                    dens = cnt / (tot * 0.1) if tot else np.zeros(nb)
                else:
                    dens = np.zeros(nb)
                has_b = False
                if n_in >= min_iv:
                    H = t1f.hist_ladder(norm_ok[a:b], bins, centers)
                    if H and H["ladder"]:
                        has_b = H["winner"] is not None
                        for rank, tr in enumerate(sorted(H["ladder"],
                                                         key=lambda z: -z["void"])):
                            l_fi.append(fi); l_ts.append(int(t)); l_rk.append(rank)
                            l_bn.append(tr["loc"])
                            l_ba.append(lm * 10.0 ** tr["loc"])
                            l_vd.append(tr["void"])
                f_fi.append(np.full(nb, fi, np.int32))
                f_ts.append(np.full(nb, int(t), np.int64))
                f_lm.append(np.full(nb, lm))
                f_n.append(np.full(nb, n_in, np.int32))
                f_hb.append(np.full(nb, has_b, bool))
                f_bc.append(centers)
                f_de.append(dens)

            nrows = len(f_fi) * nb
            fw.write_table(pa.Table.from_pydict({
                "event_id": pa.array([eid] * nrows, pa.string()),
                "kernel_min": pa.array(np.full(nrows, float(k_min)), pa.float64()),
                "frame_idx": pa.array(np.concatenate(f_fi), pa.int32()),
                "frame_ts_ns": pa.array(np.concatenate(f_ts), pa.int64()),
                "local_median_s": pa.array(np.concatenate(f_lm), pa.float64()),
                "n_intervals": pa.array(np.concatenate(f_n), pa.int32()),
                "has_boundary": pa.array(np.concatenate(f_hb), pa.bool_()),
                "bin_center_norm": pa.array(np.concatenate(f_bc), pa.float64()),
                "density": pa.array(np.concatenate(f_de), pa.float64())},
                schema=FRAME_SCHEMA))
            n_frame_rows += nrows

            if l_fi:
                lw.write_table(pa.Table.from_pydict({
                    "event_id": pa.array([eid] * len(l_fi), pa.string()),
                    "kernel_min": pa.array(np.full(len(l_fi), float(k_min)), pa.float64()),
                    "frame_idx": pa.array(np.array(l_fi, np.int32), pa.int32()),
                    "frame_ts_ns": pa.array(np.array(l_ts, np.int64), pa.int64()),
                    "rank": pa.array(np.array(l_rk, np.int32), pa.int32()),
                    "boundary_norm": pa.array(np.array(l_bn), pa.float64()),
                    "boundary_abs_s": pa.array(np.array(l_ba), pa.float64()),
                    "void": pa.array(np.array(l_vd), pa.float64())},
                    schema=LADDER_SCHEMA))
                n_lad_rows += len(l_fi)

        if i % 5 == 0:
            print(f"  {i}/{len(dev)}  frames {n_frame_rows:,}  ladder {n_lad_rows:,}  "
                  f"({time.perf_counter()-t0:.0f}s)", flush=True)

    fw.close(); lw.close(); tw.close()
    out = {"task": "C1", "events": int(len(dev)),
           "tape_review_events": len(tape_set), "subset_events": len(subset),
           "kernels": KERNELS, "cells_ok": cells_ok, "cells_declined": cells_declined,
           "frame_rows": n_frame_rows, "ladder_rows": n_lad_rows,
           "tape_rows": n_tape_rows,
           "wall_clock_s": round(time.perf_counter() - t0, 1),
           "megabytes": {k: round(os.path.getsize(os.path.join(ART, f"diag1_{k}.parquet"))
                                  / 1e6, 1) for k in ("frames", "ladder", "tape")},
           "note": ("Same frames and same ladder as Diag1 T1, written in the long form the "
                    "plotting script consumes. No measurement is recomputed or changed.")}
    with open(os.path.join(ART, "c1_emit.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    for k, v in out.items():
        print(f"  {k:<22} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
