"""
Shape classifier S2, T3 -- the folds and the ticker-blocked test sets (brief section 5).

Rolling origin, time-ordered: fold 1 trains 2020-2021 and tests 2022, fold 2 trains 2020-2022 / tests 2023, fold 3
trains 2020-2023 / tests 2024. Primary read = test events whose ticker never appears in the fold's training years;
secondary = all test events. Dev and sidecar events are in no fold; unlabelled events are counted, never used.
Inside each training window the tuning split: sub-train = training years before the last, validation = the last
training year's events with tickers not in the sub-train years.

Counts per fold x role x type x decision time x state (reached / not_reached / undefined), and escalation row 5
(any fold's primary test set with fewer than 20 events of a type, among the events that reached the decision
time -> LOG; that type is shown and not read in that fold at that decision time).

Writes artifacts/t3_membership.parquet, t3_counts.parquet, t3_row5.parquet, t3_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t3_folds.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

ROLES = ["train", "sub", "val", "test", "primary"]


def main() -> int:
    pop = S.load_population()
    ck = pd.read_parquet(S.art("t2_checkpoints.parquet"), columns=["event_id", "time", "state"])
    mem = []
    for f in S.FOLDS:
        m = S.fold_masks(pop, f)
        df = pd.DataFrame({"event_id": pop["event_id"], "fold": f, **{r: m[r] for r in ROLES}})
        mem.append(df)
    mem = pd.concat(mem, ignore_index=True)
    mem.to_parquet(S.art("t3_membership.parquet"), index=False)

    lab = pop.set_index("event_id")["type100"]
    x = ck.merge(mem, on="event_id")
    x["type"] = x["event_id"].map(lab)
    rows = []
    for (f, t, st), g in x.groupby(["fold", "time", "state"]):
        for r in ROLES:
            gg = g[g[r]]
            vc = gg["type"].value_counts()
            for ty in S.TYPES:
                rows.append({"fold": f, "time": t, "state": st, "role": r, "type": ty, "n": int(vc.get(ty, 0))})
    cnt = pd.DataFrame(rows)
    cnt.to_parquet(S.art("t3_counts.parquet"), index=False)
    p = cnt[(cnt["role"] == "primary") & (cnt["state"] == "reached")]
    r5 = p[p["n"] < 20].copy()
    r5["row"] = 5
    r5["tier"] = "LOG"
    r5.to_parquet(S.art("t3_row5.parquet"), index=False)

    ex = {"dev_v3": int((pop["dev_group"] == "dev_v3").sum()), "dev_v4_sidecar": int((pop["dev_group"] == "dev_v4_sidecar").sum()),
          "unlabelled_non_dev": int((pop["type100"].isna() & ~pop["excluded_dev"]).sum())}
    base = {}
    for f in S.FOLDS:
        mm = mem[mem["fold"] == f]
        base[f] = {r: {"events": int(mm[r].sum()), "tickers": int(pop.loc[mm[r].to_numpy(), "ticker"].nunique()),
                       "types": pop.loc[mm[r].to_numpy(), "type100"].value_counts().reindex(S.TYPES).fillna(0).astype(int).to_dict()}
                   for r in ROLES}
    tau_primary = p[p["time"] == "tau"].pivot_table(index="fold", columns="type", values="n").reindex(columns=S.TYPES)
    S.write_json("t3_summary.json", {
        "config_hash": S.cfg_hash(), "excluded": ex, "folds": base,
        "row5_log": {"n_cells": int(len(r5)), "cells": r5[["fold", "time", "type", "n"]].to_dict("records")},
        "primary_at_tau": {int(k): v for k, v in tau_primary.to_dict("index").items()},
    })
    print(ex)
    for f in S.FOLDS:
        print(f, {r: base[f][r]["events"] for r in ROLES}, base[f]["primary"]["types"])
    print("row 5 LOG cells:", len(r5))
    print(r5.groupby(["fold", "type"]).size())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
