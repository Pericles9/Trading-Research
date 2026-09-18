"""
v1-T5 (Fix 3): true D1 concurrency, measured directly. A cheap read, not a rebuild.

This is the design written as Part I T1 of prompts/relative_momentum_r0.md, which never ran
because T0b stopped the brief. It runs here because it decides whether the expensive thing --
a full causal re-derivation of the gate over all of D1, including the online Hawkes refit -- is
worth doing at all. If D1's own concurrency is thin, no population correction rescues gate 2.

THE CANDIDATE MOMENT IS A PROXY, and it has to be. The gate's own first rising edge does not
exist for D1: R0-T0b established the gate has never been run on 93% of D1 and on no event dated
before 2023-11-17. The proxy is the programme's own momentum definition:

    tau_D1 = the first minute bar on the event day whose HIGH reaches prior_close * 1.30,
             taken at that bar's first_trade_ts

It is causal, tick-derived (event_minute_bars_v2 is Phase 6b's tick aggregate; D5 A11 says reuse
needs no citation), and computable for every D1 event. It is NOT the EPG rising edge: EPG fires
on trade-arrival intensity, so it fires later than the raw crossing in general. This proxy is
therefore an UPPER bound on how early a candidate appears and, with a fixed liveness window, an
upper bound on concurrency. Stated before the numbers.

LIVENESS is a declared sweep, never selected from: 9, 15, 30, 60 minutes and no cap. 9 minutes
is the empirical median first-window duration measured in v0 (540 s), the closest available
stand-in for the gate's own window-close definition, which does not exist for D1.

Faceted by year, mandatory.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/t5_d1_concurrency.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import common as C  # noqa: E402
from src.data.db import get_connection  # noqa: E402

OUT_JSON = f"{C.ART}/t5_d1_concurrency.json"
OUT_TAU = f"{C.ART}/t5_d1_candidate_moments.parquet"
OUT_GRID = f"{C.ART}/t5_d1_grid.parquet"

SQL = """
WITH pc AS (
  SELECT ticker, event_date_canonical, prior_close
  FROM read_parquet('{pc}')
  WHERE prior_close_available AND prior_close > 0
)
SELECT b.ticker,
       CAST(b.event_date_canonical AS VARCHAR) AS event_date_canonical,
       min(b.first_trade_ts) AS tau_ns
FROM event_minute_bars_v2 b
JOIN pc ON pc.ticker = b.ticker
       AND CAST(b.event_date_canonical AS VARCHAR) = pc.event_date_canonical
WHERE b.session_offset = 0
  AND b.first_trade_ts IS NOT NULL
  AND b.high >= pc.prior_close * {mult}
GROUP BY 1, 2
"""


def main() -> int:
    cfg = C.load_cfg()
    f3 = cfg["fix3_d1_concurrency"]
    mult = 1.0 + cfg["fix2_population_gap_gate_on"]["threshold"]
    caps = f3["liveness_sweep_minutes"]
    step = f3["grid_step_minutes"]

    d1 = C.load_d1()
    d1["key"] = d1["ticker"] + "|" + d1["event_date_canonical"]

    t0 = time.time()
    con = get_connection(read_only=True)
    tau = con.execute(SQL.format(pc=(C.REPO / C.PRIOR_CLOSE).as_posix(), mult=mult)).df()
    print(f"crossing query: {len(tau)} events in {time.time() - t0:.0f}s", flush=True)

    tau["key"] = tau["ticker"] + "|" + tau["event_date_canonical"]
    d = d1.merge(tau[["key", "tau_ns"]], on="key", how="left")
    assert len(d) == len(d1), "crossing join changed the D1 row count"

    d["tau_available"] = d["tau_ns"].notna()
    ts = pd.to_datetime(d["tau_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    d["tau_et"] = ts
    d["tau_tod_sec"] = (ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second).astype("Float64")
    d["tau_tod_hhmm"] = ts.dt.strftime("%H:%M")
    d.to_parquet(C.REPO / OUT_TAU, index=False)

    have = d[d["tau_available"]].copy()

    # ---- per session date ------------------------------------------------
    per_date = have.groupby("event_date_canonical").size().rename("n_with_tau").to_frame()
    per_date["n_d1"] = d1.groupby("event_date_canonical").size()
    per_date = per_date.fillna(0).astype(int).reset_index()
    per_date["year"] = per_date["event_date_canonical"].str[:4]

    # ---- concurrency AT CANDIDATE MOMENTS, directly comparable to v1-T2 ---
    at_moment = {}
    for cap in caps + ["no_cap"]:
        counts = []
        for _, g in have.groupby("event_date_canonical"):
            t = g["tau_tod_sec"].to_numpy(dtype=float)
            if cap == "no_cap":
                end = np.full(t.shape, 20 * 3600.0)
            else:
                end = t + cap * 60.0
            for i in range(t.size):
                counts.append(int(((t <= t[i]) & (end >= t[i])).sum()))
        c = np.asarray(counts)
        at_moment[str(cap)] = {
            "n_candidate_moments": int(c.size),
            "median": float(np.median(c)),
            "share_alone": round(float((c == 1).mean()), 4),
            "share_two_or_more": round(float((c >= 2).mean()), 4),
            "quantiles": {f"p{int(p * 100)}": float(np.quantile(c, p))
                          for p in (.25, .5, .75, .9, .95, 1.0)},
            "distribution": {str(int(k)): int(v) for k, v in
                             pd.Series(c).value_counts().sort_index().head(12).items()},
        }

    # ---- the 5-minute grid, the brief's literal ask, faceted by year -----
    grid_sec = np.arange(4 * 3600, 20 * 3600 + 1, step * 60, dtype=float)
    rows = []
    for (date, year), g in have.assign(year=have["event_date_canonical"].str[:4]).groupby(
            ["event_date_canonical", "year"]):
        t = g["tau_tod_sec"].to_numpy(dtype=float)
        for cap in caps + ["no_cap"]:
            end = (np.full(t.shape, 20 * 3600.0) if cap == "no_cap" else t + cap * 60.0)
            live = ((t[None, :] <= grid_sec[:, None])
                    & (end[None, :] >= grid_sec[:, None])).sum(axis=1)
            rows.append(pd.DataFrame({"event_date_canonical": date, "year": year,
                                      "liveness": str(cap), "grid_sec": grid_sec,
                                      "n_live": live}))
    grid = pd.concat(rows, ignore_index=True)
    grid.to_parquet(C.REPO / OUT_GRID, index=False)

    def grid_stats(g: pd.DataFrame) -> dict:
        nz = g.loc[g["n_live"] >= 1, "n_live"].to_numpy()
        allv = g["n_live"].to_numpy()
        return {
            "n_grid_points": int(len(g)),
            "share_grid_points_with_any_candidate": round(float((allv >= 1).mean()), 4),
            "median_over_all_grid_points": float(np.median(allv)),
            "median_where_at_least_one_live": float(np.median(nz)) if nz.size else None,
            "share_two_or_more_where_any_live": round(float((nz >= 2).mean()), 4)
                                                if nz.size else None,
            "p90_where_any_live": float(np.quantile(nz, .9)) if nz.size else None,
            "max": int(allv.max()),
        }

    by_liveness = {k: grid_stats(g) for k, g in grid.groupby("liveness")}
    by_year = {}
    for cap, g in grid.groupby("liveness"):
        by_year[cap] = {y: grid_stats(gy) for y, gy in g.groupby("year")}

    tod = have["tau_tod_hhmm"].str.slice(0, 2).value_counts().sort_index()

    summary = {
        "task": "v1-T5 (Fix 3) true D1 concurrency -- a cheap read, not a rebuild",
        "config_hash": C.cfg_hash(),
        "candidate_moment_proxy": f3["candidate_moment_proxy"],
        "proxy_is_an_upper_bound": "EPG fires on trade-arrival intensity, so it fires later than "
                                   "the raw +30% crossing. With a fixed liveness window this "
                                   "proxy therefore OVERSTATES how early candidates appear and "
                                   "overstates concurrency. The numbers below are a ceiling on "
                                   "what a full-D1 gate re-derivation could find.",
        "coverage": {
            "n_d1": int(len(d1)),
            "n_with_crossing": int(have.shape[0]),
            "share": round(float(have.shape[0] / len(d1)), 4),
            "n_without_crossing": int((~d["tau_available"]).sum()),
            "no_crossing_note": "an event with no minute bar reaching +30% of the tick-derived "
                                "prior close on the event day. Carried with tau_available = "
                                "FALSE, never dropped. momentum_pct is a vendor RTH-scoped "
                                "day's-high measure on an adjusted basis (D4), so it does not "
                                "have to agree with a tick recompute.",
        },
        "events_per_session_date": {
            "d1_per_date_median": float(per_date["n_d1"].median()),
            "with_tau_per_date_median": float(per_date["n_with_tau"].median()),
            "with_tau_per_date_quantiles": {
                f"p{int(p * 100)}": float(np.quantile(per_date["n_with_tau"], p))
                for p in (.25, .5, .75, .9, .95, 1.0)},
            "n_session_dates": int(len(per_date)),
            "by_year": per_date.groupby("year").agg(
                n_dates=("event_date_canonical", "size"),
                n_events=("n_with_tau", "sum"),
                per_date_median=("n_with_tau", "median")).reset_index().to_dict("records"),
            "reading": "reported as a distribution, not a mean. 15,763 events over five years "
                       "averages to a number almost no day resembles.",
        },
        "crossing_clock_time_by_hour_et": {str(k): int(v) for k, v in tod.items()},
        "concurrency_at_candidate_moments": at_moment,
        "concurrency_on_5min_grid": by_liveness,
        "concurrency_on_5min_grid_by_year": by_year,
        "v1_gate_population_reference": {
            "share_alone": 0.8948, "median_live": 1.0, "n": 903,
            "note": "v1-T2's measured concurrency on the gap-gated gate population, for contrast.",
        },
        "outputs": [OUT_TAU, OUT_GRID],
        "elapsed_sec": round(time.time() - t0, 1),
    }
    C.write_json(OUT_JSON, summary)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("concurrency_on_5min_grid_by_year",)},
                     indent=2, default=str))
    print("\n5-MIN GRID, BY YEAR")
    for cap in [str(c) for c in caps] + ["no_cap"]:
        print(f"\n liveness = {cap}")
        print(pd.DataFrame(by_year[cap]).T.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
