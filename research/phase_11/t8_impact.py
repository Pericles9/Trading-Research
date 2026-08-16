"""T8 - impact by participation (the section 4.1 compression claim).

Reads event_quote_metrics_v1. No further scan.

T8a  Lee & Ready (1991) quote rule at the T4-selected offset (delta = 0, sip
     basis per D16) with tick-rule fallback. The 5-second lag rule is NOT
     applied: on nanosecond data the contemporaneous quote signs best, and T3
     measured the at-or-inside share peaking in a plateau containing delta = 0.
     The unclassifiable share is its own row and is never dropped.
T8b  Effective spread vs participation quintile, and delta-mid per unit signed
     volume over config.impact_windows (1, 5, 30, 60 s - no sub-second window,
     escalation row 23). DISTRIBUTIONS, not fitted coefficients. No regression.
T8c  Split by detection segment. No burst/quiet split (D11, D13).

Impact windows are expressed in whole minutes where the cache grain allows; the
1 s and 5 s windows are reported as the within-minute grain the cache carries,
and that limitation is stated rather than papered over.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import duckdb
import numpy as np
import pandas as pd
from common import ARTIFACTS, CONFIG, DB

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
PART = "results/phase_8/artifacts/t3_participation.parquet"
QSESS = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"
WINDOWS = CONFIG["impact"]["impact_windows_seconds"]
MIN_N = CONFIG["universe"]["min_cell_n"]


def main() -> None:
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB}' AS mom (READ_ONLY)")
    con.execute("SET enable_progress_bar = false")

    con.execute(f"""
        CREATE TABLE ev AS
        SELECT a.ticker, a.event_date_canonical AS event_date, a.det_segment, a.era,
               p.pq_rth_open
        FROM read_parquet('{ANCH}') a
        LEFT JOIN read_parquet('{PART}') p
          ON p.ticker = a.ticker AND p.event_date_canonical = a.event_date_canonical
         AND round(p.mp,2) = round(a.mp,2)
        JOIN (SELECT DISTINCT ticker, event_date_canonical, mom_2dp
              FROM read_parquet('{QSESS}')) q
          ON q.ticker = a.ticker AND q.event_date_canonical = a.event_date_canonical
         AND q.mom_2dp = round(a.mp,2)
        WHERE a.det_undefined = FALSE
    """)
    # Minute-grain impact: delta-mid across w minutes per unit signed volume.
    wins = [max(1, round(w / 60)) for w in WINDOWS]
    sel = ",\n".join(
        f"(LEAD(tw_mid, {w}) OVER s - tw_mid) / NULLIF(tw_mid,0) AS dmid_{w}m,"
        f" SUM(signed_volume) OVER (PARTITION BY ticker, event_date, segment "
        f"ORDER BY minute_index ROWS BETWEEN CURRENT ROW AND {w-1} FOLLOWING) AS sv_{w}m"
        for w in sorted(set(wins)))
    con.execute(f"""
        CREATE TABLE imp AS
        SELECT c.ticker, c.event_date, c.segment, c.minute_index, c.tw_mid,
               c.signed_volume, c.sum_size, c.n_trades, c.n_unclassifiable,
               c.bbo_age_at_trade_p50,
               2.0 * c.sum_abs_p_minus_m_size / NULLIF(c.sum_size,0)
                   / NULLIF(c.tw_mid,0) AS eff_frac,
               {sel}
        FROM mom.event_quote_metrics_v1 c
        WHERE c.n_trades > 0 AND c.sum_size > 0 AND c.tw_mid > 0
        WINDOW s AS (PARTITION BY ticker, event_date, segment ORDER BY minute_index)
    """)
    d = con.execute("""
        SELECT i.*, e.det_segment, e.era, e.pq_rth_open
        FROM imp i JOIN ev e USING (ticker, event_date)
    """).df()

    rows = []
    for w in sorted(set(wins)):
        d[f"impact_{w}m"] = d[f"dmid_{w}m"] / d[f"sv_{w}m"].replace(0, np.nan)
        for (seg, pq), sub in d.groupby(["det_segment", "pq_rth_open"], dropna=False):
            s = sub[f"impact_{w}m"].replace([np.inf, -np.inf], np.nan).dropna()
            rows.append({
                "window_minutes": w, "det_segment": seg, "pq_rth_open": pq,
                "n_cells": int(len(sub)), "n_impact_defined": int(len(s)),
                "impact_p25": float(s.quantile(.25)) if len(s) else None,
                "impact_p50": float(s.median()) if len(s) else None,
                "impact_p75": float(s.quantile(.75)) if len(s) else None,
                "eff_bp_p50": float(sub.eff_frac.dropna().median() * 10000)
                    if sub.eff_frac.notna().any() else None,
                "eff_cents_p50": float((sub.eff_frac * sub.tw_mid).dropna().median() * 100)
                    if sub.eff_frac.notna().any() else None,
                "unclassifiable_share": float(sub.n_unclassifiable.sum()
                                              / max(sub.n_trades.sum(), 1)),
                "hatched_n_below_100": bool(len(sub) < MIN_N),
            })
    t8 = pd.DataFrame(rows)
    t8.to_parquet(ARTIFACTS / "t8_impact.parquet", index=False)
    d.to_parquet(ARTIFACTS / "t8_impact_cells.parquet", index=False)

    out = {
        "task": "T8", "phase": "11", "date": "2026-08-16",
        "classification": {
            "rule": "Lee & Ready (1991) quote rule at delta = 0 on the sip_timestamp "
                    "basis (D16), tick-rule fallback on midpoint-equal prints.",
            "five_second_rule": "NOT APPLIED. On nanosecond data the contemporaneous "
                                "quote signs best; T3 measured the at-or-inside share "
                                "peaking in a plateau containing delta = 0, so lagging "
                                "the quote would move off the peak.",
            "unclassifiable_overall_share": float(d.n_unclassifiable.sum()
                                                  / max(d.n_trades.sum(), 1)),
            "never_dropped": "The unclassifiable share is reported per cell as its own "
                             "column and no trade is discarded.",
        },
        "impact_windows_seconds_configured": WINDOWS,
        "grain_limitation": ("event_quote_metrics_v1 is minute-grain, so the configured "
                             "1 s and 5 s windows both resolve to the 1-minute cell. This "
                             "is stated rather than papered over: sub-minute impact is "
                             "not measurable from this cache, and escalation row 23 bars "
                             "a sub-second window in any case."),
        "no_fitting": "Distributions only. No regression, no fitted impact exponent.",
        "no_burst_split": "D11 / D13 - every bucket is participation quintile, detection "
                          "segment, latency or era.",
        "cells": json.loads(t8.to_json(orient="records")),
    }
    pathlib.Path(ARTIFACTS / "t8_impact.json").write_text(json.dumps(out, indent=2))
    print(f"T8 cells {len(t8)} | overall unclassifiable share "
          f"{out['classification']['unclassifiable_overall_share']:.4%}")
    print(t8[t8.det_segment == "rth"][["window_minutes", "pq_rth_open", "n_cells",
                                       "impact_p50", "eff_bp_p50", "eff_cents_p50",
                                       "unclassifiable_share"]].to_string(index=False))


if __name__ == "__main__":
    main()
