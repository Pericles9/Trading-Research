#!/usr/bin/env python
"""Gate D's cohort: a print-count-STRATIFIED draw from the D1 pool.

WHY NOT SIMPLY MORE OF THE PANEL COHORT. The panel cohort is a joint [p70, p80]
filter on BOTH print count and momentum_pct, so its print count runs 66,451-123,044
-- a range of 1.85x. Gate D regresses a shaded fraction ON print count. Drawing more
events from a band that narrow adds n and adds no leverage: the regression would be
underpowered in the only direction that matters however many events were drawn. The
extension therefore widens the axis being regressed on, and reports the achieved
range beside the slope.

Momentum is NOT held inside [p70, p80] here. Holding it would re-narrow the pool and
Gate D is about print count; momentum_pct is carried per event so it can be entered
as a covariate rather than assumed away.

Everything else follows the panel cohort's committed procedure exactly: D1 =
momentum_events_canonical WHERE in_scope AND source_file = 'file1' via the Phase 10
stratification pool, readability = clean_window AND trades_ingested, a stable
mergesort on (ticker, event_date_canonical, momentum_pct) BEFORE the seeded draw.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

import adapter                                    # noqa: E402
import event_panels as ep                         # noqa: E402
from adapter import rel                           # noqa: E402

KEY = ["ticker", "event_date_canonical", "momentum_pct"]
SEED = 42
PER_DECILE = 6


def main() -> int:
    cfg = ep.load_config()
    pool = pd.read_parquet(rel(cfg["paths"]["pool"]))
    pool["event_date_canonical"] = pool["event_date_canonical"].astype(str)
    pool["momentum_pct"] = pool["momentum_pct"].round(2)

    readable = pool[pool["clean_window"].fillna(False)
                    & pool["trades_ingested"].fillna(False)].copy()
    # a floor on prints: the field needs a tape. 5,000 prints over the extended
    # session is ~0.09/s, at which s_min is 26 s and the fine band does not exist.
    readable = readable[readable["t0_print_count"] >= 5000]
    readable = readable.sort_values(KEY, kind="mergesort").reset_index(drop=True)

    q = np.quantile(readable["t0_print_count"], np.linspace(0, 1, 11))
    rng = np.random.default_rng(SEED)
    take = []
    for i in range(10):
        lo, hi = q[i], q[i + 1]
        band = readable[(readable["t0_print_count"] >= lo)
                        & (readable["t0_print_count"] < (hi if i < 9 else hi + 1))]
        if len(band) == 0:
            continue
        idx = np.sort(rng.choice(len(band), size=min(PER_DECILE, len(band)),
                                 replace=False))
        b = band.iloc[idx].copy()
        b["print_decile"] = i + 1
        take.append(b)
    drawn = pd.concat(take).reset_index(drop=True)
    drawn["event_id"] = [adapter.make_event_id(r.ticker, r.event_date_canonical,
                                               r.momentum_pct)
                         for r in drawn.itertuples(index=False)]
    drawn = ep.attach_flags(drawn, cfg)

    out = os.path.join(REPO_ROOT, "results", "scale_field", "artifacts",
                       "instrument_gates")
    os.makedirs(out, exist_ok=True)
    cols = (KEY + ["event_id", "t0_print_count", "print_decile", "coverage_class"]
            + [c for c in ep.FLAG_COLS if c in drawn])
    drawn[cols].to_csv(os.path.join(out, "gateD_cohort.csv"), index=False)

    pc = drawn["t0_print_count"]
    print(f"readable pool n = {len(readable)}   drawn n = {len(drawn)}")
    print(f"print count  min {pc.min():,}  median {pc.median():,.0f}  max {pc.max():,}"
          f"   range {pc.max()/pc.min():.1f}x   log10 span {np.log10(pc.max()/pc.min()):.2f}")
    print(f"momentum_pct min {drawn['momentum_pct'].min():.2f} "
          f"max {drawn['momentum_pct'].max():.2f}")
    print("per decile:", drawn.groupby("print_decile").size().to_dict())
    print("wrote", os.path.join(out, "gateD_cohort.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
