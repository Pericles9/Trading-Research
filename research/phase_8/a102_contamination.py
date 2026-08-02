"""
Phase 8 A10.2b - contamination test (the gate).

Does the Phase 8 headline participation gradient survive at an anchor with no
remaining T0 hindsight? t0_close is the only anchor where the entire T0 move -
including the high that defined D1 membership - is already past.

Markout: t0_close -> t1_close and t0_close -> t3_close (signed log return),
bucketed by the SAME participation quintile that defines the headline gradient:
the PRE-OPEN quintile pq_rth_open (participation at RTH open, chart 05's bucket).
Using pq_rth_open - not pq_t0_close - is deliberate: the test is whether that
specific gradient carries information beyond T0 selection arithmetic.

Reading rule (A10.2 §3, frozen; the agent states which row matches, nothing more):
  gradient present + monotonic at t0_close->t1_close -> participation carries
    information the selection criterion does not already guarantee
  flat / non-monotonic -> the rth_open gradient is consistent with selection
    arithmetic; Phase 8's headline is not established as a forward edge

Scan-free; reuses t5_markout_grid.parquet (t0_close-anchored markouts) + the
pq_rth_open quintile from t3_participation.parquet. Flagged union excluded.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

GRID = "results/phase_8/artifacts/t5_markout_grid.parquet"
T3 = "results/phase_8/artifacts/t3_participation.parquet"
OUT_JSON = "results/phase_8/artifacts/a102_contamination_test.json"
OUT_PARQUET = "results/phase_8/artifacts/a102_contamination.parquet"
KEY = ["ticker", "event_date_canonical", "mp"]
HORIZONS = ["t1_close", "t3_close"]


def _cell(s):
    s = s.dropna()
    return {"n": int(len(s)), "median": (float(s.median()) if len(s) else None),
            "iqr": ([float(s.quantile(.25)), float(s.quantile(.75))] if len(s) else [None, None])}


def main():
    g = pd.read_parquet(GRID)
    g["event_date_canonical"] = pd.to_datetime(g["event_date_canonical"])
    t3 = pd.read_parquet(T3); t3["event_date_canonical"] = pd.to_datetime(t3["event_date_canonical"])
    pqro = t3[KEY + ["pq_rth_open"]].copy()

    sub = g[(g.anchor_name == "t0_close") & (g.horizon_name.isin(HORIZONS))
            & g.markout.notna() & (~g.in_flagged_union)].copy()
    sub = sub.drop(columns=["pq"]).merge(pqro, on=KEY, how="left")
    sub = sub[sub.pq_rth_open.notna()]
    sub.to_parquet(OUT_PARQUET, index=False)

    summary = {"phase": "8", "task": "A10.2b",
               "source": "research/phase_8/a102_contamination.py:main",
               "scan_free": True,
               "bucket": "pq_rth_open (pre-open participation quintile; the headline gradient's bucket)",
               "grids": {}}
    for h in HORIZONS:
        for era in ["era_2020_2021", "era_2022_2024"]:
            cells = {}
            for q in [1, 2, 3, 4, 5]:
                s = sub[(sub.horizon_name == h) & (sub.era == era) & (sub.pq_rth_open == q)]["markout"]
                cells[f"Q{q}"] = _cell(s)
            summary["grids"][f"t0_close->{h}|{era}"] = cells

    # monotonicity read on t0_close->t1_close (pooled eras and per era), median by quintile
    def medians(h, era=None):
        d = sub[(sub.horizon_name == h)]
        if era:
            d = d[d.era == era]
        return [float(d[d.pq_rth_open == q]["markout"].median()) for q in [1, 2, 3, 4, 5]]

    t1_pooled = medians("t1_close")
    mono_dec = all(t1_pooled[i] >= t1_pooled[i + 1] for i in range(4))
    spread = t1_pooled[0] - t1_pooled[4]
    summary["t0_close_to_t1_close_median_by_quintile_pooled"] = t1_pooled
    summary["t0_close_to_t1_close_median_by_quintile_2020_2021"] = medians("t1_close", "era_2020_2021")
    summary["t0_close_to_t1_close_median_by_quintile_2022_2024"] = medians("t1_close", "era_2022_2024")
    summary["monotonic_decreasing_pooled"] = bool(mono_dec)
    summary["q1_minus_q5_spread_pooled"] = spread
    summary["reading_rule_note"] = ("descriptive only; the REPORT states which of the two A10.2 §3 rows "
                                    "chart 12 matches and nothing more (escalation row 16)")
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "grids"}, indent=2, default=str))
    print("\nt0_close->t1_close median by pq_rth_open quintile:")
    print("  pooled  :", [round(x, 4) for x in t1_pooled])
    print("  2020-21 :", [round(x, 4) for x in summary['t0_close_to_t1_close_median_by_quintile_2020_2021']])
    print("  2022-24 :", [round(x, 4) for x in summary['t0_close_to_t1_close_median_by_quintile_2022_2024']])


if __name__ == "__main__":
    main()
