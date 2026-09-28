"""
R0-T0b: THE OVERLAP JOIN. A stopping gate (brief section I.1).

Question: is the event set behind the participation gate's reported profit factors the
same population as Mom-DB's D1? Asserted in BOTH directions, in executable code.

Three nested gate populations are joined, because "the participation gate's event set"
is not one set:

  G_list  -- the gate's own admissible universe. scanner-epg-momentum/backtest/data/
             loaders/trades.py::list_events: a data/filtered folder whose name parses,
             carries a date, has mom_pct >= 50.0, and has trades.parquet. This is the
             largest population the backtest could ever address.
  G_run   -- (ticker, date) the gate was actually executed on: every per_event_summary.json
             under scanner-epg-momentum/backtest/results.
  G_fired -- G_run rows with n_pass_edges >= 1: the gate actually produced a rising edge.

Plus G_pf: the single run behind the headline profit factor this brief cites.

Nothing in scanner-epg-momentum is executed or imported. Its selection rule is
re-implemented read-only in common.py.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0b_overlap_join.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t0b_overlap_join.json"
OUT_LIST = f"{C.ART}/t0b_gate_listable.parquet"
OUT_RUN = f"{C.ART}/t0b_gate_runs.parquet"
OUT_MEMBERSHIP = f"{C.ART}/t0b_membership.parquet"


def both_ways(name: str, left: set, right: set, left_label: str, right_label: str,
              sample: int = 5) -> dict:
    """Set relationship asserted in both directions, with counts and samples."""
    only_l = left - right
    only_r = right - left
    inter = left & right
    return {
        "name": name,
        f"n_{left_label}": len(left),
        f"n_{right_label}": len(right),
        "n_intersection": len(inter),
        f"n_only_in_{left_label}": len(only_l),
        f"n_only_in_{right_label}": len(only_r),
        "n_symmetric_difference": len(only_l) + len(only_r),
        f"share_of_{left_label}_covered": (len(inter) / len(left)) if left else None,
        f"share_of_{right_label}_covered": (len(inter) / len(right)) if right else None,
        f"sample_only_in_{left_label}": sorted(only_l)[:sample],
        f"sample_only_in_{right_label}": sorted(only_r)[:sample],
    }


def main() -> int:
    cfg = C.load_cfg()
    d1 = C.load_d1()
    universe = C.load_universe()

    # ---- gate populations -------------------------------------------------
    rule = cfg["gate"]["event_lister_rule"]
    listable = C.gate_listable_events(min_mom=rule["min_mom_pct"],
                                      require_date=rule["require_date_in_folder_name"])
    listable.to_parquet(os.path.join(C.REPO, OUT_LIST), index=False)
    g_list = listable[listable["admitted"]].copy()

    runs = C.gate_run_events()
    runs.to_parquet(os.path.join(C.REPO, OUT_RUN), index=False)
    runs["key"] = runs["ticker"].astype(str) + "|" + runs["date"].astype(str)

    edges = pd.to_numeric(runs["n_pass_edges"], errors="coerce")
    fired_keys = set(runs.loc[edges.fillna(0) >= 1, "key"])
    run_keys = set(runs["key"])

    pf_path = cfg["gate"]["cited_headline_runs"]["scanner_phase_F_val_full"]["path"]
    run_path_norm = runs["run_path"].str.replace("\\", "/", regex=False)
    pf_runs = runs[run_path_norm.str.startswith(pf_path)].copy()
    pf_keys = set(pf_runs["key"])
    pf_edges = pd.to_numeric(pf_runs["n_pass_edges"], errors="coerce")
    pf_fired_keys = set(pf_runs.loc[pf_edges.fillna(0) >= 1, "key"])

    # ---- keys -------------------------------------------------------------
    d1_keys = set(d1["ticker"] + "|" + d1["event_date_canonical"])
    universe_keys = set(universe["ticker"] + "|" + universe["event_date_canonical"])
    d1_ids = set(d1["event_id"])
    glist_keys = set(g_list["ticker"] + "|" + g_list["date"])
    glist_ids = set(g_list["event_id"])

    rels = [
        both_ways("G_list_vs_D1", glist_keys, d1_keys, "G_list", "D1"),
        both_ways("G_list_vs_D1_on_event_id", glist_ids, d1_ids, "G_list_id", "D1_id"),
        both_ways("G_list_vs_in_scope_all_source_files", glist_keys, universe_keys,
                  "G_list", "in_scope_all"),
        both_ways("G_run_vs_D1", run_keys, d1_keys, "G_run", "D1"),
        both_ways("G_fired_vs_D1", fired_keys, d1_keys, "G_fired", "D1"),
        both_ways("G_pf_valfull_vs_D1", pf_keys, d1_keys, "G_pf", "D1"),
        both_ways("G_pf_valfull_fired_vs_D1", pf_fired_keys, d1_keys, "G_pf_fired", "D1"),
        both_ways("G_run_vs_G_list", run_keys, glist_keys, "G_run", "G_list"),
    ]

    # ---- why G_list excludes what it excludes ------------------------------
    # The rejected side of the gate's own lister, against D1, so the exclusion is a
    # reported population rather than an absence.
    listable["key"] = listable["ticker"].astype(str) + "|" + listable["date"].astype(str)
    rej = listable[~listable["admitted"]].copy()
    rej["in_d1"] = rej["key"].isin(d1_keys)
    reject_breakdown = (rej.groupby(["reject_reason", "in_d1"]).size()
                        .rename("n").reset_index()
                        .sort_values("n", ascending=False).to_dict("records"))

    # D1 events the gate's lister never admits, by reason, resolved per D1 row.
    lk = listable[~listable["key"].duplicated()].set_index("key")
    d1_tmp = d1.copy()
    d1_tmp["key"] = d1_tmp["ticker"] + "|" + d1_tmp["event_date_canonical"]
    d1_tmp["gate_admitted"] = d1_tmp["key"].isin(glist_keys)
    d1_tmp["gate_reject_reason"] = d1_tmp["key"].map(lk["reject_reason"]).fillna(
        "no_matching_filtered_folder")
    d1_tmp.loc[d1_tmp["gate_admitted"], "gate_reject_reason"] = None
    d1_tmp["gate_run"] = d1_tmp["key"].isin(run_keys)
    d1_tmp["gate_fired"] = d1_tmp["key"].isin(fired_keys)
    d1_tmp["in_pf_run"] = d1_tmp["key"].isin(pf_keys)
    d1_tmp[["event_id", "ticker", "event_date_canonical", "momentum_pct", "year",
            "gate_admitted", "gate_reject_reason", "gate_run", "gate_fired",
            "in_pf_run"]].to_parquet(os.path.join(C.REPO, OUT_MEMBERSHIP), index=False)

    d1_excluded_by_reason = (d1_tmp[~d1_tmp["gate_admitted"]]
                             .groupby("gate_reject_reason").size().sort_values(ascending=False)
                             .astype(int).to_dict())
    by_year = d1_tmp.groupby("year").agg(
        n_d1=("event_id", "size"),
        n_gate_admitted=("gate_admitted", "sum"),
        n_gate_run=("gate_run", "sum"),
        n_gate_fired=("gate_fired", "sum"),
    ).astype(int).reset_index().to_dict("records")

    # ---- the criterion ----------------------------------------------------
    n_d1 = len(d1_keys)
    share_d1_run = len(run_keys & d1_keys) / n_d1
    share_d1_fired = len(fired_keys & d1_keys) / n_d1
    share_d1_listable = len(glist_keys & d1_keys) / n_d1
    share_pf_in_d1 = (len(pf_keys & d1_keys) / len(pf_keys)) if pf_keys else None

    criterion = {
        "statement": "Are the participation gate's event set and D1 the same population?",
        "share_of_D1_the_gate_lister_would_even_admit": share_d1_listable,
        "share_of_D1_the_gate_was_ever_run_on": share_d1_run,
        "share_of_D1_the_gate_ever_fired_on": share_d1_fired,
        "share_of_the_headline_PF_run_that_is_inside_D1": share_pf_in_d1,
        "materially_disjoint": bool(share_d1_run < 0.50),
        "materially_disjoint_rule": "share_of_D1_the_gate_was_ever_run_on < 0.50 -- a stated "
                                    "round threshold declared in this script, not fitted. The "
                                    "brief sets no numeric bar ('materially disjoint'); the "
                                    "decision is Cooper's and the number below is what it is "
                                    "read on.",
    }

    summary = {
        "task": "R0-T0b overlap join (STOPPING GATE)",
        "config_hash": C.cfg_hash(),
        "gate_populations": {
            "G_list": {"n": len(glist_keys),
                       "rule": f"data/filtered folder, parseable name, date present, "
                               f"mom_pct >= {rule['min_mom_pct']}, trades.parquet present",
                       "n_folders_scanned": int(len(listable))},
            "G_run": {"n": len(run_keys),
                      "n_per_event_summary_rows": int(len(runs)),
                      "n_result_files": int(runs["run_path"].nunique())},
            "G_fired": {"n": len(fired_keys), "rule": cfg["gate"]["fired_definition"]},
            "G_pf_valfull": {"n": len(pf_keys), "n_fired": len(pf_fired_keys),
                             "path": pf_path,
                             "profit_factor": cfg["gate"]["cited_headline_runs"]
                                                 ["scanner_phase_F_val_full"]["profit_factor"]},
        },
        "D1": {"n": n_d1, "rule": cfg["universe"]["membership_rule"]},
        "set_relationships": rels,
        "gate_lister_rejections_vs_D1": reject_breakdown,
        "D1_events_the_gate_lister_excludes_by_reason": d1_excluded_by_reason,
        "by_year": by_year,
        "criterion": criterion,
        "outputs": [OUT_LIST, OUT_RUN, OUT_MEMBERSHIP],
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
