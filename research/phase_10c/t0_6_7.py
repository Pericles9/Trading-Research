"""
Phase 10c Stage 0 -- T0.6 detection-anchor migration, T0.7 population counts.

T0.6 resolves A1.6's open question (is poll0 a default or a decision?).
T0.7 resolves A1.7 (D14_population and D15_stage3_scope).

The canonical universe view runs a live DISTINCT scan over billions of rows, so
it is materialised ONCE and every count is taken from that single pass.

Usage: .venv/Scripts/python.exe research/phase_10c/t0_6_7.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_spec = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_spec)
_spec.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"


def t0_6(cfg):
    variants = cfg["stage_0_sweeps"]["T0_6_anchor_variants"]
    d = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    keep = ["ticker", "event_date_canonical"] + [f"det_segment_{v}" for v in variants] \
        + [f"det_ns_{v}" for v in variants]
    d = d[keep].drop_duplicates(subset=["ticker", "event_date_canonical"]).reset_index(drop=True)

    seg = {v: d[f"det_segment_{v}"] for v in variants}
    base = variants[0]
    out = {"n_events": int(len(d)), "variants": variants, "base_variant": base,
           "segment_counts": {v: seg[v].value_counts(dropna=False).to_dict() for v in variants}}

    # pairwise migration counts against the base
    mig = {}
    for v in variants[1:]:
        ct = pd.crosstab(seg[base], seg[v], dropna=False)
        moved = int((seg[base].astype(str) != seg[v].astype(str)).sum())
        mig[f"{base}_to_{v}"] = {"n_moved": moved,
                                 "share_moved": float(moved / len(d)) if len(d) else np.nan,
                                 "matrix": {str(a): {str(b): int(ct.loc[a, b]) for b in ct.columns}
                                            for a in ct.index}}
    out["migration_vs_base"] = mig
    out["headline_poll0_vs_poll60"] = mig.get(f"{base}_to_{variants[-1]}", {}).get("n_moved")

    # anchor time shift, in seconds, base vs each variant
    shifts = {}
    for v in variants[1:]:
        dt = (d[f"det_ns_{v}"].astype("float64") - d[f"det_ns_{base}"].astype("float64")) / 1e9
        dt = dt.replace([np.inf, -np.inf], np.nan).dropna()
        shifts[v] = {"n": int(dt.size), "median_s": float(dt.median()),
                     "p90_abs_s": float(dt.abs().quantile(0.9)),
                     "max_abs_s": float(dt.abs().max())}
    out["anchor_shift_seconds_vs_base"] = shifts
    return out, d


def t0_7(cfg, per_event_seconds):
    import duckdb
    p = os.environ.get("MOM_DB_DUCKDB_PATH", r"E:\Trading Research\data\duckdb\main.duckdb")
    con = duckdb.connect(p, read_only=True)
    t = time.perf_counter()
    # ONE pass over the canonical view (config _universe_note)
    q = """
        SELECT in_scope, trades_ingested, quotes_ingested, coverage_class,
               trades_full_window, COUNT(*) AS n
        FROM momentum_events_canonical
        GROUP BY 1,2,3,4,5
    """
    g = con.execute(q).fetchdf()
    con.close()
    scan_s = time.perf_counter() - t

    def cnt(mask):
        return int(g.loc[mask, "n"].sum())

    ins = g["in_scope"] == True                                     # noqa: E712
    tr = g["trades_ingested"] == True                               # noqa: E712
    qt = g["quotes_ingested"] == True                               # noqa: E712
    fw = g["coverage_class"] == "full_window"

    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))
    non_pooled = ("dev_v4_sidecar", "row_cap_census")
    cands = {
        "phase10_analysis_cohort": int((~coh["cohort_group"].isin(non_pooled)).sum()),
        "phase10_frozen_cohort": int(len(coh)),
        "in_scope": cnt(ins),
        "in_scope_and_trades_ingested": cnt(ins & tr),
        "in_scope_trades_and_quotes_ingested": cnt(ins & tr & qt),
        "in_scope_trades_ingested_full_window": cnt(ins & tr & fw),
    }
    n_k_stage3 = len(cfg["stage_0_sweeps"]["T0_5_candidate_kernels_min"])
    est = {k: {"n_events": v,
               "stage1_est_seconds": round(v * per_event_seconds, 1),
               "stage1_est_hours": round(v * per_event_seconds / 3600.0, 2),
               "stage3_est_hours_at_%d_kernels" % n_k_stage3:
                   round(v * per_event_seconds * n_k_stage3 / 3600.0, 2)}
           for k, v in cands.items()}
    return {"canonical_scan_seconds": round(scan_s, 1),
            "per_event_seconds_from_stage0": round(per_event_seconds, 3),
            "stage3_kernel_count_assumed": n_k_stage3,
            "candidate_populations": cands, "compute_estimates": est,
            "note": ("Stage 1 is one kernel; Stage 3 is the population times N kernels (A1.7). "
                     "Per-event seconds is measured from the Stage 0 dev-sample pass and covers "
                     "the tick read plus one interval pass; it is a lower bound for Stage 1, "
                     "which additionally builds the normalisation window and selects a threshold.")}


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    six, det = t0_6(cfg)
    c10c.write_json(rel(f"{ART}/t0_6_anchor_migration.json"), {"config_hash": chash, **six})
    det.to_parquet(rel(f"{ART}/t0_6_anchor_variants.parquet"), index=False)

    wf_path = rel(f"{ART}/t0_waterfall.json")
    pes = 1.0
    if os.path.exists(wf_path):
        import json
        wf = json.load(open(wf_path, encoding="utf-8"))
        n = max(wf.get("events_with_trades", 1), 1)
        pes = wf.get("timing_seconds", 1.0) / n
    seven = t0_7(cfg, pes)
    c10c.write_json(rel(f"{ART}/t0_7_population.json"), {"config_hash": chash, **seven})

    print("T0.6 detection-anchor migration")
    print(f"   events {six['n_events']}   base {six['base_variant']}")
    for k, v in six["migration_vs_base"].items():
        print(f"   {k}: moved {v['n_moved']} ({v['share_moved']:.4f})")
    print(f"   segment counts: {six['segment_counts']}")
    print("\nT0.7 candidate populations")
    for k, v in seven["compute_estimates"].items():
        print(f"   {k:38s} n={v['n_events']:>6}  stage1 ~{v['stage1_est_hours']:>7.2f} h")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
