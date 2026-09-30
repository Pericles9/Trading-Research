"""
Shape classifier S2, T7 -- permutation importance per type for M3 (class weight none, the real run's setting),
on each fold's primary test set, at every decision time, for both labels (Amendment 1: remaining-path type, primary;
whole-path type, secondary; at tau the remaining rows are the whole rows).

For each input column: permute it within the primary test rows (5 repeats, seeded), predict once per repeat, and
take the drop in each type's one-vs-rest AUC. An input's share of a type's importance = its mean drop / the sum of
the positive mean drops over all inputs. Escalation row 4: a share above 0.5 is a LOG row, and that input gets a
manual timing re-check (its construction and its T0 latest-timestamp audit are restated in the report).

Writes artifacts/t7_importance.parquet, t7_row4.parquet, t7_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t7_importance.py
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "3")

import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402
import t4_models as T4  # noqa: E402

REPEATS = 5


def job(args):
    label, fold, tkey, setting = args
    D = T4.load_data()
    M = D["masks"][fold]
    num, boo, cat = T4.inputs_for(tkey)
    y = S.y_codes(S.labels_at(D["pop"], label, tkey))
    fin = T4.frame(tkey, fold, "final", None, label)
    fin = fin[y[fin["row"].to_numpy()] >= 0]
    tr, te = fin[M["train"][fin["row"]]], fin[M["primary"][fin["row"]]]
    prep, mdl = T4.m3_fit(tr, y[tr["row"]], num, boo, cat, setting, "none", S.SEED)
    X = prep.transform(te)
    yt = y[te["row"]]
    base = T4.full_proba(mdl, X)
    b_auc = np.array([S.auc_weighted(yt == i, base[:, i]) for i in range(6)])
    rng = np.random.default_rng([S.SEED, fold, S.TIMES.index(tkey)])
    rows = []
    for j, name in enumerate(prep.names()):
        drops = np.zeros((REPEATS, 6))
        for r in range(REPEATS):
            Xp = X.copy()
            Xp[:, j] = Xp[rng.permutation(len(Xp)), j]
            p = T4.full_proba(mdl, Xp)
            drops[r] = b_auc - np.array([S.auc_weighted(yt == i, p[:, i]) for i in range(6)])
        for i, t in enumerate(S.TYPES):
            rows.append({"label": label, "fold": fold, "time": tkey, "input": name, "type": t, "base_auc": b_auc[i], "mean_drop": drops[:, i].mean(),
                         "sd_drop": drops[:, i].std(), "n": int(len(te)), "n_type": int((yt == i).sum())})
    return rows


def main() -> int:
    t_start = time.perf_counter()
    js = S.read_json("t4_summary.json")["jobs"]
    jobs = [(j["label"], j["fold"], j["time"], j["chosen"]["M3|none"]) for j in js if not j.get("copied_from")]
    rows = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for r in ex.map(job, jobs):
            rows += r
    imp = pd.DataFrame(rows)
    # tau: the remaining label is the whole label (A1.3); its rows are the whole-label rows
    imp = pd.concat([imp, imp[(imp["label"] == "whole") & (imp["time"] == "tau")].assign(label="remaining")], ignore_index=True)
    pos = imp["mean_drop"].clip(lower=0)
    imp["share"] = imp["mean_drop"] / pos.groupby([imp["label"], imp["fold"], imp["time"], imp["type"]]).transform("sum")
    imp["config_hash"] = S.cfg_hash()
    imp.to_parquet(S.art("t7_importance.parquet"), index=False)
    r4 = imp[imp["share"] > 0.5].copy()
    r4["row"], r4["tier"] = 4, "LOG"
    r4.to_parquet(S.art("t7_row4.parquet"), index=False)
    top = imp.sort_values("share", ascending=False).groupby(["label", "type", "time"]).head(1)
    S.write_json("t7_summary.json", {"config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "repeats": REPEATS,
                                     "row4_log": {"n_cells": int(len(r4)), "inputs": sorted(r4["input"].unique().tolist()),
                                                  "cells": r4[["label", "fold", "time", "type", "input", "share", "mean_drop", "base_auc", "n_type"]].to_dict("records")},
                                     "top_input_by_type_time": top[["label", "type", "time", "fold", "input", "share"]].to_dict("records")})
    print(f"row 4 LOG cells: {len(r4)}; inputs: {sorted(r4['input'].unique().tolist())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
