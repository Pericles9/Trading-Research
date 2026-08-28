"""
Order-of-work step 2: the reconciliation gate. HARD STOP on divergence.

`scale_field.allan_factor()` must reproduce Phase 10 v3's committed Allan curve rung
for rung on the same dyadic ladder. Any divergence means the point-process handling
differs from v3's, and everything after it is uninterpretable.

WHAT IS BEING RECONCILED, precisely. v3's `allan_fano` (research/phase_10/v3_t1_gate.py)
and this module's `allan_factor` are independent code paths over the same definition:

    A(T) = E[(N_{i+1} - N_i)^2] / (2 E[N])   over NON-OVERLAPPING windows of width T

Everything that is not the formula has to be matched explicitly or the comparison is
meaningless, and each of these was a real way to get a plausible wrong answer:

  * WINDOW ORIGIN. v3 tiles the D3 extended session [04:00 ET, post_end), NOT the
    data's own support, so empty stretches are real zeros rather than omissions
    (config/phase_10_v3.json gate.window_origin). This is why `allan_factor` grew
    t_start/t_end -- the origin cannot be inferred from the prints.
  * RAW PRINTS, TIES INTACT. v3 passes `t0["sip_timestamp"]` straight in. Ties are
    NOT collapsed for the Allan gate; collapsing is the interval channel's variant
    and applying it here would change every count.
  * THE PARTIAL TRAILING WINDOW IS DROPPED, never clipped into. Both paths mask to
    idx < n_win rather than clamping, so the last, short window contributes nothing.
  * min_windows = 8 (v3 gate.min_windows_for_a_rung). A rung with fewer windows is
    dropped for that event, not returned small.
  * FLOAT MAGNITUDE. Both paths rebase on the session start in int64 BEFORE the float
    divide. `ts/1e9` at epoch magnitude has a 238 ns ULP -- see scale_field._assert_resolved.

The bar is exact float reproduction, not approximate: the two paths run the same
arithmetic on the same integers, so the only admissible difference is association
order. Tolerance is config reconciliation.tolerance_rel (1e-12) and exists for that.

Also reports v3's committed knees as a PREDICTION for the continuous field, which is
what step 3's chart is checked against. They are not an input to anything here.

Usage: .venv/Scripts/python.exe research/scale_field/reconcile_allan.py
Exit:  0 reconciled · 2 DIVERGENCE, hard stop · 3 preconditions absent
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import COHORT_KEY, load_cohort, load_event_prints_meta, rel  # noqa: E402
from scale_field import allan_factor  # noqa: E402

OUT = "results/scale_field/artifacts/reconcile_allan.json"
OUT_ROWS = "results/scale_field/artifacts/reconcile_allan_rows.parquet"


def ladder(cfg: dict) -> list[float]:
    lad = cfg["reconciliation"]["ladder"]
    return [lad["base_seconds"] * 2.0 ** e
            for e in range(lad["min_exponent"], lad["max_exponent"] + 1)]


def main() -> int:
    cfg = adapter.load_config()
    chash = adapter.config_hash()
    rc = cfg["reconciliation"]
    tol = float(rc["tolerance_rel"])
    min_win = int(rc["min_windows_for_a_rung"])
    Ts = ladder(cfg)

    target_path = rel(rc["target_curves"])
    if not os.path.exists(target_path):
        print(f"PRECONDITION ABSENT: {rc['target_curves']} not on disk. It is a "
              f"gitignored regenerable artifact; regenerate with "
              f"research/phase_10/v3_t1_gate.py before reconciling.")
        return 3

    v3 = pd.read_parquet(target_path)
    v3 = v3[v3["observable"] == rc["observable"]].copy()
    v3["event_date_canonical"] = v3["event_date_canonical"].astype(str)
    v3["event_id"] = [adapter.make_event_id(r.ticker, r.event_date_canonical, r.momentum_pct)
                      for r in v3.itertuples(index=False)]

    cohort = load_cohort(cfg)          # asserts the frozen hash; raises on mismatch
    print(f"cohort {len(cohort)} events, {int(cohort['pooled'].sum())} pooled, "
          f"hash asserted OK")
    print(f"v3 target: {len(v3)} {rc['observable']} rows over "
          f"{v3['event_id'].nunique()} events, {v3['T'].nunique()} rungs")

    rows, t_start = [], time.perf_counter()
    for i, r in enumerate(cohort.itertuples(index=False), 1):
        ts, meta = load_event_prints_meta(r.event_id, None, cfg)
        if ts.size == 0:
            continue
        # Rebase on the session start in int64, THEN convert. The window becomes
        # [0, span) and every count is identical to v3's by construction.
        lo, hi = meta["window_start_ns"], meta["window_end_ns"]
        ts_s = (ts - lo).astype(np.float64) / 1e9
        span = (hi - lo) / 1e9
        for T in Ts:
            A, n_pairs = allan_factor(ts_s, T, t_start=0.0, t_end=span,
                                      min_windows=min_win)
            rows.append({"event_id": r.event_id, "ticker": r.ticker,
                         "event_date_canonical": r.event_date_canonical,
                         "momentum_pct": r.momentum_pct,
                         "cohort_group": r.cohort_group, "pooled": bool(r.pooled),
                         "T": float(T), "allan_here": float(A),
                         "n_pairs_here": int(n_pairs), "n_prints": int(ts.size)})
        if i % 25 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t_start:.0f}s)",
                  flush=True)

    here = pd.DataFrame(rows)
    here_ok = here[np.isfinite(here["allan_here"])]

    # Merge on the ELIGIBLE cells of each side. v3 simply omits a rung it declines;
    # this path records it as NaN with n_pairs = 0. Comparing the raw frames would
    # count that representational difference as 114 phantom divergences.
    m = v3.merge(here_ok, on=["event_id", "T"], how="outer", indicator=True,
                 suffixes=("_v3", "_here"))
    both = m[m["_merge"] == "both"].copy()
    both["abs_diff"] = (both["allan_here"] - both["allan"]).abs()
    both["rel_diff"] = both["abs_diff"] / both["allan"].abs().clip(lower=1e-300)
    diverged = both[both["rel_diff"] > tol]

    # A rung one side kept and the other declined IS a divergence -- the eligibility
    # rule differs, which is a point-process handling difference wearing a missing
    # row instead of a wrong number.
    v3_only = m[m["_merge"] == "left_only"]
    here_only = m[m["_merge"] == "right_only"]

    # Declined by BOTH is agreement, and is reported rather than left implicit.
    declined = here[~np.isfinite(here["allan_here"])]
    declined_by_both = declined.merge(v3[["event_id", "T"]], on=["event_id", "T"],
                                      how="left", indicator=True)
    declined_by_both = declined_by_both[declined_by_both["_merge"] == "left_only"]

    n_pair_mismatch = int((both["n_pairs_here"] != both["n_windows"] - 1).sum())

    ok = (len(diverged) == 0 and len(v3_only) == 0 and len(here_only) == 0
          and n_pair_mismatch == 0 and len(both) == len(v3))

    worst = both.nlargest(5, "rel_diff")[
        ["event_id", "T", "allan", "allan_here", "rel_diff"]].to_dict("records") \
        if len(both) else []

    summary = {
        "task": "reconciliation gate (order of work step 2)",
        "config_hash": chash,
        "cohort_manifest": cfg["cohort"]["manifest"],
        "cohort_content_hash": cfg["cohort"]["content_hash"],
        "cohort_hash_asserted": True,
        "target": rc["target_curves"],
        "observable": rc["observable"],
        "window_origin": rc["window_origin"],
        "min_windows_for_a_rung": min_win,
        "ties": "NOT collapsed -- v3's gate runs on raw prints",
        "tolerance_rel": tol,
        "n_events_read": int(here["event_id"].nunique()),
        "n_rungs_ladder": len(Ts),
        "n_cells_v3": int(len(v3)),
        "n_cells_here_finite": int(len(here_ok)),
        "n_cells_compared": int(len(both)),
        "n_cells_reproduced": int(len(both) - len(diverged)),
        "n_cells_diverged": int(len(diverged)),
        "n_cells_v3_only": int(len(v3_only)),
        "n_cells_here_only": int(len(here_only)),
        "n_rungs_declined_by_both": int(len(declined_by_both)),
        "rungs_declined_by_both": sorted(map(float, declined_by_both["T"].unique())),
        "declined_note": "The 2^13 = 8192 s rung. The D3 extended session is 57,600 s, "
                         "so it holds 7 non-overlapping windows against a floor of 8. "
                         "Both paths decline it; the agreement is the point.",
        "n_window_count_mismatches": n_pair_mismatch,
        "max_rel_diff": float(both["rel_diff"].max()) if len(both) else None,
        "max_abs_diff": float(both["abs_diff"].max()) if len(both) else None,
        "worst_cells": worst,
        "reconciled": bool(ok),
        "hard_stop": bool(not ok),
        "v3_knees_seconds": rc["v3_knees_seconds"],
        "v3_knees_role": rc["v3_knees_role"],
        "source": "research/scale_field/reconcile_allan.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scale_field/reconcile_allan.py",
    }

    os.makedirs(os.path.dirname(rel(OUT)), exist_ok=True)
    with open(rel(OUT), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    here.to_parquet(rel(OUT_ROWS), index=False)

    print(f"\ncells compared {summary['n_cells_compared']} / v3 {summary['n_cells_v3']}"
          f"   reproduced {summary['n_cells_reproduced']}"
          f"   diverged {summary['n_cells_diverged']}")
    print(f"v3-only rungs {summary['n_cells_v3_only']}   "
          f"here-only rungs {summary['n_cells_here_only']}   "
          f"window-count mismatches {n_pair_mismatch}")
    print(f"declined by BOTH {summary['n_rungs_declined_by_both']} cells at T="
          f"{summary['rungs_declined_by_both']} s (7 windows < floor of 8)")
    print(f"max relative difference {summary['max_rel_diff']:.3e} "
          f"(tolerance {tol:.0e})")
    if ok:
        print("RECONCILED — point-process handling matches v3 rung for rung.")
        return 0
    print("DIVERGENCE — HARD STOP. Do not proceed to the field. "
          "Commit state, post the criterion and the observed value, wait for instruction.")
    for w in worst:
        print(f"  {w['event_id']}  T={w['T']}  v3={w['allan']!r}  here={w['allan_here']!r}"
              f"  rel={w['rel_diff']:.3e}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
