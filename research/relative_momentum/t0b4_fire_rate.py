"""
R0-T0b (part 4): the fire rate, measured per run, on the runner family where it means
something, with the skipped population restored.

Written because the 2026-09-18 read of T0b infers from "run 6.96% vs fired 6.90%" that the
gate almost never says no once an event is run. T0b's two numbers are correct for what they
measure -- has this D1 event EVER been run on / EVER fired, anywhere in the results tree,
which is what T0b's D1-coverage columns need -- but they are a UNION over 101 result files
and many gate configurations. A union cannot measure a fire rate: an event counts as fired
if any one configuration ever fired on it once.

Two things have to be fixed to measure it honestly:

  1. Measure WITHIN a run, not across the tree.
  2. Count only the runner family for which n_pass_edges is the entry counter. The rapid
     runner (`entry_eligible` family) writes n_pass_edges = 0 on every row while recording
     nonzero pass->fail transitions and nonzero trades on those same rows -- it enters on
     first-pass, not on a rising edge. Reading its zeros as "the gate declined" would be a
     category error. See common.runner_family.
  3. Restore skipped_events.json -- events the runner attempted and abandoned before ever
     writing a summary row. per_event_summary.json alone silently drops them, so a fire
     rate computed on summary rows has the wrong denominator.

Reads only. Nothing under scanner-epg-momentum is executed or imported.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0b4_fire_rate.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t0b4_fire_rate.json"
OUT_PER_RUN = f"{C.ART}/t0b4_fire_rate_per_run.parquet"
OUT_SKIPPED = f"{C.ART}/t0b4_skipped_events.parquet"

HEADLINE = "scanner-epg-momentum/backtest/results/phase_f/val_full"


def load_skipped() -> pd.DataFrame:
    root = C.REPO / C.load_cfg()["gate"]["run_result_roots"][0]
    frames = []
    for p in sorted(root.rglob("skipped_events.json")):
        d = json.load(open(p))
        if not d:
            continue
        f = pd.DataFrame(d)
        f["run_dir"] = str(p.parent.relative_to(C.REPO)).replace("\\", "/")
        frames.append(f)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["ticker", "date", "reason", "run_dir"])


def main() -> int:
    d1 = C.load_d1()
    d1_keys = set(d1["ticker"] + "|" + d1["event_date_canonical"])

    runs = C.gate_run_events()
    runs["run_dir"] = (runs["run_path"].str.replace("\\", "/", regex=False)
                       .str.rsplit("/", n=1).str[0])
    runs["key"] = runs["ticker"].astype(str) + "|" + runs["date"].astype(str)
    edges = pd.to_numeric(runs["n_pass_edges"], errors="coerce")
    runs["fired"] = edges.fillna(0) >= 1

    rising = runs[runs["runner_family"] == "rising_edge"].copy()

    skipped = load_skipped()
    skipped["key"] = skipped["ticker"].astype(str) + "|" + skipped["date"].astype(str)
    skipped["in_d1"] = skipped["key"].isin(d1_keys)
    skipped.to_parquet(os.path.join(C.REPO, OUT_SKIPPED), index=False)
    skipped_by_run = skipped.groupby("run_dir").size().rename("n_skipped")

    per_run = runs.groupby(["run_dir", "runner_family"]).agg(
        n_summary_rows=("key", "size"),
        n_fired=("fired", "sum"),
    ).reset_index()
    per_run["n_skipped"] = (skipped_by_run.reindex(per_run["run_dir"]).fillna(0)
                            .astype(int).to_numpy())
    per_run["n_attempted"] = per_run["n_summary_rows"] + per_run["n_skipped"]
    is_rising = per_run["runner_family"] == "rising_edge"
    # NaN, not 0, for any run where n_pass_edges is not the entry counter.
    per_run["fire_rate_of_summary_rows"] = pd.NA
    per_run.loc[is_rising, "fire_rate_of_summary_rows"] = (
        per_run.loc[is_rising, "n_fired"] / per_run.loc[is_rising, "n_summary_rows"])
    per_run["fire_rate_of_attempted"] = pd.NA
    per_run.loc[is_rising, "fire_rate_of_attempted"] = (
        per_run.loc[is_rising, "n_fired"] / per_run.loc[is_rising, "n_attempted"])
    per_run = per_run.sort_values(["runner_family", "n_summary_rows"],
                                  ascending=[True, False]).reset_index(drop=True)
    per_run.to_parquet(os.path.join(C.REPO, OUT_PER_RUN), index=False)

    rr = per_run[is_rising.to_numpy()] if len(per_run) else per_run
    rr = per_run[per_run["runner_family"] == "rising_edge"]

    hl = per_run[per_run["run_dir"] == HEADLINE]
    hl_row = hl.iloc[0].to_dict() if len(hl) else None
    sk_hl = skipped[skipped["run_dir"] == HEADLINE]

    summary = {
        "task": "R0-T0b (part 4) fire rate per run, rising-edge runner only, "
                "skipped events restored",
        "config_hash": C.cfg_hash(),
        "why": "T0b's run/fired pair is a union across 101 result files and many gate "
               "configurations, and a union cannot measure a fire rate. Measured within a "
               "run, on the runner family where n_pass_edges is the entry counter.",
        "union_as_reported_in_T0b": {
            "n_distinct_events_ever_run": int(runs["key"].nunique()),
            "n_distinct_events_ever_fired": int(runs.loc[runs["fired"], "key"].nunique()),
            "reading": "correct for 'has this event ever been run / ever fired', which is "
                       "what T0b's D1-coverage columns need. NOT a fire rate.",
        },
        "runner_families": {
            fam: {"n_runs": int(g["run_dir"].nunique()), "n_summary_rows": int(len(g)),
                  "n_fired": int(g["fired"].sum())}
            for fam, g in runs.groupby("runner_family")
        },
        "entry_eligible_family_note":
            "n_pass_edges is 0 on every row of this family while n_passtofail_transitions "
            "and n_trades_in_event are nonzero on those same rows -- the rapid runner enters "
            "on first-pass, not on a rising edge. UNMEASURABLE on this axis, not negative. "
            "Excluded from every fire rate below and never counted as a decline.",
        "rising_edge_family": {
            "n_runs": int(rr["run_dir"].nunique()),
            "n_summary_rows": int(rr["n_summary_rows"].sum()),
            "n_fired": int(rr["n_fired"].sum()),
            "pooled_fire_rate_of_summary_rows": float(rr["n_fired"].sum()
                                                      / rr["n_summary_rows"].sum()),
            "n_runs_with_zero_fires": int((rr["n_fired"] == 0).sum()),
            "fire_rate_quantiles_of_summary_rows": {
                str(q): float(pd.to_numeric(rr["fire_rate_of_summary_rows"]).quantile(q))
                for q in (0.0, 0.25, 0.5, 0.75, 1.0)
            },
        },
        "headline_run": {
            "run_dir": HEADLINE, "profit_factor": 1.9194,
            **({k: (float(v) if isinstance(v, float) else v)
                for k, v in hl_row.items() if k != "run_dir"} if hl_row else {}),
            "skipped_reasons": sk_hl.groupby("reason").size().astype(int).to_dict(),
            "reading": "the fire rate of the run the reproducible PF is computed on, once "
                       "the events the runner abandoned before the gate are put back in the "
                       "denominator.",
        },
        "skipped_events": {
            "n_rows_all_runs": int(len(skipped)),
            "n_distinct_events": int(skipped["key"].nunique()),
            "n_distinct_events_in_D1": int(skipped.loc[skipped["in_d1"], "key"].nunique()),
            "reasons_all_runs": skipped.groupby("reason").size().astype(int).to_dict(),
        },
        "rising_edge_runs": rr.to_dict("records"),
        "outputs": [OUT_PER_RUN, OUT_SKIPPED],
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rising_edge_runs"},
                     indent=2, default=str))
    print("\nrising-edge runs (top 15 by size):")
    print(rr.head(15).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
