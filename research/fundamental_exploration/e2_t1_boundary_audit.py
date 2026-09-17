"""
E2-T1: distance-to-boundary audit. Run before anything is read off a momentum chart.

The universe is selected on log_vol ~ log_mom (quantile q=0.05) -- momentum and anything
correlated with event_volume are conditionally dependent inside the sample even if
independent in the population, a selection artefact rather than a finding. Computes
log10(event_volume / min_volume_threshold) per D1 event, reported by the fundamental
splits E2-T5/T6 actually use, under D4 Amendment A13's exemption (diagnostic read of
event_volume/min_volume_threshold paired together, entering no other computed quantity
-- these two columns are read from the RAW momentum_events table, never joined into any
other output).

log_vol/log_mom/log_vol_threshold are NOT persisted columns (transient pandas variables
inside data/collection_scripts/filter_events_power_law.py, which is itself on CLAUDE.md's
banned-execution list and is never run here) -- only their product, min_volume_threshold,
survives to disk on momentum_events. See prompts/fundamental_exploration_e2.md SS8.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t1_boundary_audit.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

N_DECILES = C.load_cfg()["deciles"]["n"]


def stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)), "mean": float(s.mean()),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.quantile(0.50)), "p75": float(s.quantile(0.75)),
        "p90": float(s.quantile(0.90)), "min": float(s.min()), "max": float(s.max()),
    }


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame_key = frame[["ticker", "event_date_canonical", "momentum_pct"]].copy()

    con = C.connect(read_only=True)
    con.register("d1_key", frame_key)
    raw = con.execute("""
        SELECT k.ticker, k.event_date_canonical, k.momentum_pct,
               m.event_volume, m.min_volume_threshold
        FROM d1_key k
        JOIN momentum_events m
          ON m.ticker = k.ticker AND m.momentum_pct = k.momentum_pct
         AND COALESCE(m.date, m.event_date) = k.event_date_canonical
    """).df()
    con.close()

    raw["event_id"] = raw.apply(C.event_id, axis=1)
    n_missing_threshold = int(raw["min_volume_threshold"].isna().sum())
    n_missing_volume = int(raw["event_volume"].isna().sum())
    raw["distance_log10"] = np.log10(raw["event_volume"] / raw["min_volume_threshold"])

    d1_fund = pd.read_parquet(f"{C.ART_E2}/e2_d1_fundamentals.parquet")
    d1_fund = C.add_corrected_shares_outstanding(d1_fund)
    d1_fund = d1_fund.merge(C.load_detection_price(), on="event_id", how="left")
    df = raw.merge(d1_fund, on="event_id", how="inner")
    assert len(df) == len(frame_key), f"join lost rows: {len(df)} vs {len(frame_key)}"

    df["shs_decile"] = pd.qcut(df["shs_shares_outstanding_corrected"], N_DECILES, labels=False, duplicates="drop")
    df["flg_lag_days"] = df["flg_lag_ns"] / 86_400e9
    df["flg_lag_bucket"] = pd.cut(
        df["flg_lag_days"], bins=[-0.001, 1, 7, 30, 90, np.inf],
        labels=["<=1d", "1-7d", "7-30d", "30-90d", ">90d"],
    )

    splits = {}
    overall = stats(df["distance_log10"])
    splits["overall"] = {"overall": overall}

    for label, s in [("S%d" % d, df[df["shs_decile"] == d]["distance_log10"]) for d in sorted(df["shs_decile"].dropna().unique())]:
        splits.setdefault("shs_decile", {})[label] = stats(s)
    splits["shs_decile"]["no_shs_data"] = stats(df[df["shs_decile"].isna()]["distance_log10"])

    for val in [True, False]:
        splits.setdefault("flg_dilution_form_before_t0", {})[str(val)] = stats(
            df[(df["flg_quality"] != "unavailable") & (df["flg_dilution_form_before_t0"] == val)]["distance_log10"]
        )
    for val in [True, False]:
        splits.setdefault("spl_reverse_split_365d", {})[str(val)] = stats(
            df[df["spl_reverse_split_365d"] == val]["distance_log10"]
        )
    for label in ["<=1d", "1-7d", "7-30d", "30-90d", ">90d"]:
        splits.setdefault("flg_lag_bucket", {})[label] = stats(
            df[df["flg_lag_bucket"] == label]["distance_log10"]
        )
    splits.setdefault("si_quality", {})
    for val in df["si_quality"].dropna().unique():
        splits["si_quality"][val] = stats(df[df["si_quality"] == val]["distance_log10"])

    # flag any split whose median sits materially closer to the boundary (distance_log10 -> 0)
    # than the overall population median -- "materially" read here as within half the overall
    # median's own log10-distance, a plain, stated comparison, not a formal test.
    overall_median = overall["median"]
    flagged = []
    for split_name, groups in splits.items():
        if split_name == "overall":
            continue
        for group_label, s in groups.items():
            if s.get("n", 0) >= 20 and s["median"] < overall_median * 0.5:
                flagged.append({"split": split_name, "group": group_label, "n": s["n"], "median": s["median"]})

    df.to_parquet(f"{C.ART_E2}/e2_t1_boundary_audit.parquet", index=False)

    summary = {
        "task": "E2-T1 distance-to-boundary audit",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_total": len(df),
        "n_missing_event_volume": n_missing_volume,
        "n_missing_min_volume_threshold": n_missing_threshold,
        "overall_distance_log10": overall,
        "splits": splits,
        "flagged_materially_closer_to_boundary": flagged,
        "flagged_note": "median distance_log10 < half the overall population's median, n>=20 -- a plain "
                        "stated comparison, not a formal test. Empty list means no split's audit came back "
                        "differently enough from the population as a whole to flag here.",
    }
    C.write_json(f"{C.ART_E2}/e2_t1_boundary_audit_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
