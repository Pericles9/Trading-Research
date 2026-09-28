"""
v0-T0: the population, and its coverage, stated plainly.

Facet 1 choice (the brief allows either): the EXISTING fired population, used as-is. Re-running
the gate's logic causally against all of D1 is not a small lift -- it means executing or
re-implementing epg_replay.py's online Hawkes refit over ~15,763 events -- and the existing
population is on disk with a full per-trade record.

Coverage is reported at every join and nothing is dropped. The brief: "state population coverage
plainly rather than assume it equals all of D1."

Usage: .venv/Scripts/python.exe research/relative_momentum_v0/t0_population.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v0 import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t0_population.json"
OUT_PARQUET = f"{C.ART}/t0_candidates.parquet"


def main() -> int:
    cfg = C.load_cfg()
    fw = C.first_window_trades()
    d1 = C.load_d1()
    d1["key"] = d1["ticker"] + "|" + d1["event_date_canonical"]

    steps = [{"step": "gate first-window trades (one per event)", "n": int(len(fw))}]

    fw = fw.merge(d1[["key", "event_id", "momentum_pct"]], on="key", how="left")
    fw["in_d1"] = fw["event_id"].notna()
    steps.append({"step": "of which in D1", "n": int(fw["in_d1"].sum()),
                  "n_outside_D1": int((~fw["in_d1"]).sum()),
                  "note": "outside-D1 events are carried in the artifact, flagged, not dropped. "
                          "R0-T0b resolved them: warrants, preferreds, fund products, and "
                          "in-scope-class events flagged flag_trades_mom_outlier."})

    pc = pd.read_parquet(C.REPO / C.PRIOR_CLOSE)
    pc["key"] = pc["ticker"] + "|" + pc["event_date_canonical"]
    fw = fw.merge(pc[["key", "prior_close", "prior_close_available"]], on="key", how="left")
    fw["prior_close_available"] = fw["prior_close_available"].fillna(False)
    steps.append({"step": "with a tick-derived prior close (move_at computable)",
                  "n": int(fw["prior_close_available"].sum()),
                  "n_missing": int((~fw["prior_close_available"]).sum())})

    base_path = C.REPO / C.BASELINE
    if base_path.exists():
        be = pd.read_parquet(base_path)
        be = be.rename(columns={"event_id": "event_id_be"})
        fw = fw.merge(be[["event_id_be", "B_e", "n_baseline_sessions",
                          "total_baseline_dollar_volume"]],
                      left_on="event_id", right_on="event_id_be", how="left").drop(
                          columns=["event_id_be"])
        # The inferred definition, checked rather than assumed.
        r = (fw["total_baseline_dollar_volume"] / fw["B_e"]).dropna().round(4)
        divisor = {"unique_values": sorted(r.unique().tolist())[:5],
                   "n_distinct": int(r.nunique()),
                   "reading": "117 = 3 sessions x 39 ten-minute blocks in a 6.5-hour RTH "
                              "session, so B_e is mean dollar volume per 10-minute RTH block "
                              "over 3 prior sessions."}
    else:
        fw["B_e"] = pd.NA
        fw["n_baseline_sessions"] = pd.NA
        divisor = {"error": "baseline artifact not present"}
    fw["baseline_available"] = fw["B_e"].notna() & (pd.to_numeric(fw["B_e"], errors="coerce") > 0)
    steps.append({"step": "with E2 baseline B_e (score computable)",
                  "n": int(fw["baseline_available"].sum()),
                  "n_missing": int((~fw["baseline_available"]).sum())})

    fw["folder"] = [C.event_folder(t, d) for t, d in zip(fw["ticker"], fw["date"])]
    fw["folder_available"] = fw["folder"].notna()
    steps.append({"step": "with a resolvable filtered/ event folder (tick window readable)",
                  "n": int(fw["folder_available"].sum()),
                  "n_missing": int((~fw["folder_available"]).sum())})

    fw["scorable"] = (fw["in_d1"] & fw["baseline_available"] & fw["folder_available"])
    fw["evaluable"] = fw["scorable"] & fw["prior_close_available"]
    steps.append({"step": "SCORABLE (in D1, baseline, folder)", "n": int(fw["scorable"].sum())})
    steps.append({"step": "EVALUABLE (scorable + prior close, so move_at is defined too)",
                  "n": int(fw["evaluable"].sum())})

    fw.to_parquet(C.REPO / OUT_PARQUET, index=False)

    d1_total = int(len(d1))
    summary = {
        "task": "v0-T0 population and coverage",
        "config_hash": C.cfg_hash(),
        "facet1_choice": cfg["facet1_entry_exit"]["choice"],
        "facet1_source": C.PER_TRADE,
        "facet1_note": cfg["facet1_entry_exit"]["choice_rationale"],
        "coverage_steps": steps,
        "coverage_against_D1": {
            "n_D1": d1_total,
            "n_candidates_in_D1": int(fw["in_d1"].sum()),
            "share_of_D1": float(fw["in_d1"].sum() / d1_total),
            "statement": f"This build runs on {int(fw['evaluable'].sum())} of {d1_total} D1 "
                         f"events ({fw['evaluable'].sum() / d1_total:.2%}). It is NOT a "
                         f"measurement over D1. The population is the val-split slice the gate "
                         f"was actually run on: dates "
                         f"{fw['date'].min()} to {fw['date'].max()}.",
        },
        "date_range": {"min": fw["date"].min(), "max": fw["date"].max(),
                       "n_session_dates": int(fw["date"].nunique())},
        "B_e_divisor_check": divisor,
        "exit_mix_first_window": {
            "natural_exit_reason": fw["natural_exit_reason"].value_counts().to_dict(),
            "realized_exit_reason": fw["exit_reason"].value_counts().to_dict(),
            "note": "the brief specifies window-close exit; natural_exit_* is that exit. The "
                    "LULD rows are carried, not dropped.",
        },
        "natural_hold_sec": {
            k: float(v) for k, v in
            fw["natural_hold_sec"].describe(percentiles=[.25, .5, .75]).items()
        },
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
