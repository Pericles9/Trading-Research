"""
Shape classifier S2, T3 -- the folds and the ticker-blocked test sets (brief section 5), for both labels
(Amendment 1: the remaining-path type, primary; the whole-path type, secondary).

Rolling origin, time-ordered: fold 1 trains 2020-2021 and tests 2022, fold 2 trains 2020-2022 / tests 2023, fold 3
trains 2020-2023 / tests 2024. Primary read = test events whose ticker never appears in the fold's training years;
secondary = all test events. Dev and sidecar events are in no fold; events without the whole-path label are in no
fold; an event without the remaining-path label at a checkpoint is counted there and never fitted or scored.
Inside each training window the tuning split: sub-train = training years before the last, validation = the last
training year's events with tickers not in the sub-train years.

Counts per label x fold x role x type x decision time x state (reached / not_reached / undefined; for the remaining
label, reached events without a label are counted under 'unlabelled'), and escalation row 5 per label (a fold's
primary test set with fewer than 20 labelled events of a type at a decision time -> LOG; shown, not read).

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
        mem.append(pd.DataFrame({"event_id": pop["event_id"], "fold": f, **{r: m[r] for r in ROLES}}))
    mem = pd.concat(mem, ignore_index=True)
    mem.to_parquet(S.art("t3_membership.parquet"), index=False)

    rem = S.remaining_table()[["event_id", "time", "rem_type"]]
    whole = pop.set_index("event_id")["type100"]
    rows = []
    for label in S.LABELS:
        x = ck.merge(mem, on="event_id")
        if label == "whole":
            x["type"] = x["event_id"].map(whole)
        else:
            x = x.merge(rem, on=["event_id", "time"], how="left").rename(columns={"rem_type": "type"})
            x.loc[(x["state"] == "reached") & x["type"].isna(), "state"] = "unlabelled"
        for (f, t, st), g in x.groupby(["fold", "time", "state"]):
            for r in ROLES:
                vc = g[g[r]]["type"].value_counts()
                n_all = int(g[r].sum())
                for ty in S.TYPES:
                    rows.append({"label": label, "fold": f, "time": t, "state": st, "role": r, "type": ty, "n": int(vc.get(ty, 0)), "n_role": n_all})
    cnt = pd.DataFrame(rows)
    cnt.to_parquet(S.art("t3_counts.parquet"), index=False)
    p = cnt[(cnt["role"] == "primary") & (cnt["state"] == "reached")]
    r5 = p[p["n"] < 20].copy()
    r5["row"], r5["tier"] = 5, "LOG"
    r5.to_parquet(S.art("t3_row5.parquet"), index=False)

    ex = {"dev_v3": int((pop["dev_group"] == "dev_v3").sum()), "dev_v4_sidecar": int((pop["dev_group"] == "dev_v4_sidecar").sum()),
          "unlabelled_non_dev": int((pop["type100"].isna() & ~pop["excluded_dev"]).sum())}
    base = {}
    for f in S.FOLDS:
        mm = mem[mem["fold"] == f]
        base[f] = {r: {"events": int(mm[r].sum()), "tickers": int(pop.loc[mm[r].to_numpy(), "ticker"].nunique()),
                       "types": pop.loc[mm[r].to_numpy(), "type100"].value_counts().reindex(S.TYPES).fillna(0).astype(int).to_dict()}
                   for r in ROLES}
    S.write_json("t3_summary.json", {
        "config_hash": S.cfg_hash(), "excluded": ex, "folds": base,
        "row5_log": {lab: {"n_cells": int((r5["label"] == lab).sum()), "cells": r5[r5["label"] == lab][["fold", "time", "type", "n"]].to_dict("records")}
                     for lab in S.LABELS},
        "primary_reached_labelled": {lab: {t: p[(p["label"] == lab) & (p["time"] == t)].groupby("type")["n"].sum().reindex(S.TYPES).astype(int).to_dict()
                                           for t in S.TIMES} for lab in S.LABELS},
    })
    print(ex)
    for f in S.FOLDS:
        print(f, {r: base[f][r]["events"] for r in ROLES})
    for lab in S.LABELS:
        print(lab, "row 5 LOG cells:", int((r5["label"] == lab).sum()))
        print(r5[r5["label"] == lab].groupby(["fold", "type"]).size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
