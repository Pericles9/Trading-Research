"""
Shape classifier S2, T5 -- the section 6 controls, under Cooper's rulings R4 and R5 (config cooper_rulings_2026_09_28).

  negative  10 independent label shuffles per fold: the training window's labels permuted (seeded by shuffle and
            fold), the Group C typical paths rebuilt from the permuted labels, M1-M4 (both class weights) refitted at
            the real run's chosen settings, each fold's primary test set scored. Row 2 reads the mean AUC over the
            3 folds x 10 shuffles per type x model x decision time against [0.45, 0.55]; single-shuffle per-fold
            values are kept beside it.
  positive  M2 and M3 (both class weights, real run's settings) with a leak added at every decision time:
            'rules' = the three numbers S1's type rules read (post100_rise_pct, post100_fall_pct, post100_u_peak),
            gated by row 3 (every type's per-fold primary AUC >= 0.95); 'terminal_log' = the brief's construction,
            reported, ungated.
  baseline  M1 vs M0 at tau, read from T4's scores.

Writes artifacts/t5_negative.parquet, t5_negative_gate.parquet, t5_positive.parquet, t5_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t5_controls.py
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "3")

import ast  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402
import t2_checkpoints as T2  # noqa: E402
import t4_models as T4  # noqa: E402

SHUFFLES = 10
LEAKS = {"rules": ("post100_rise_pct", "post100_fall_pct", "post100_u_peak"), "terminal_log": ("terminal_log",)}


def chosen_settings() -> dict:
    js = S.read_json("t4_summary.json")["jobs"]
    out = {}
    for j in js:
        out[(j["fold"], j["time"])] = {tuple(k.split("|")): v for k, v in j["chosen"].items()}
    return out


def primary_auc(res: dict, labels_true: np.ndarray, extra_key: dict) -> list[dict]:
    D = T4.load_data()
    pr = res["pred"]
    pr = pr[pr["primary"] & (pr["model"] != "M0")]
    rows = []
    for (mdl, cw), g in pr.groupby(["model", "cw"]):
        yy = S.y_codes(labels_true[g["event_id"].map(D["pos"]).to_numpy()])
        for i, t in enumerate(S.TYPES):
            rows.append({**extra_key, "model": mdl, "cw": cw, "type": t, "n": int(len(g)), "n_type": int((yy == i).sum()),
                         "auc": S.auc_weighted(yy == i, g[f"p_{t}"].to_numpy(float))})
    return rows


def neg_job(args):
    r, fold, fixed_all = args
    D = T4.load_data()
    pop = D["pop"]
    lab = pop["type100"].to_numpy().copy()
    M = D["masks"][fold]
    tr_idx = np.flatnonzero(M["train"])
    rng = np.random.default_rng([S.SEED, r, fold])
    lab[tr_idx] = lab[tr_idx][rng.permutation(tr_idx.size)]
    (y0, y1), yt = S.FOLDS[fold]
    yr = pop["year"].to_numpy()
    gc, _ = T2.group_c(pop, D["P"], D["ck"], pd.Series(lab), {(fold, "final"): (M["train"], (yr >= y0) & (yr <= yt))})
    true = pop["type100"].to_numpy()
    rows = []
    for t in S.TIMES:
        res = T4.run_job(fold, t, labels=lab, gc=gc, fixed=fixed_all[(fold, t)], models=("M1", "M2", "M3", "M4"))
        rows += primary_auc(res, true, {"shuffle": r, "fold": fold, "time": t})
    return rows


def pos_job(args):
    leak, fold, t, fixed = args
    D = T4.load_data()
    res = T4.run_job(fold, t, fixed=fixed, extra=LEAKS[leak], models=("M2", "M3"))
    return primary_auc(res, D["pop"]["type100"].to_numpy(), {"leak": leak, "fold": fold, "time": t})


def main() -> int:
    t_start = time.perf_counter()
    fixed = chosen_settings()
    # ---------------- positive
    pos = []
    jobs = [(lk, f, t, fixed[(f, t)]) for lk in LEAKS for t in S.TIMES for f in S.FOLDS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        for rows in ex.map(pos_job, jobs):
            pos += rows
    pos = pd.DataFrame(pos)
    pos["config_hash"] = S.cfg_hash()
    pos.to_parquet(S.art("t5_positive.parquet"), index=False)
    gated = pos[pos["leak"] == "rules"]
    row3 = gated[gated["auc"] < 0.95]
    print(f"positive done {time.perf_counter() - t_start:,.0f}s; row 3 cells below 0.95: {len(row3)}", flush=True)
    # ---------------- negative
    neg = []
    jobs = [(r, f, fixed) for r in range(SHUFFLES) for f in S.FOLDS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        for n, rows in enumerate(ex.map(neg_job, jobs)):
            neg += rows
            print(f"  negative {n + 1}/{len(jobs)}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    neg = pd.DataFrame(neg)
    neg["config_hash"] = S.cfg_hash()
    neg.to_parquet(S.art("t5_negative.parquet"), index=False)
    gate = neg.groupby(["model", "cw", "time", "type"]).agg(mean_auc=("auc", "mean"), sd_auc=("auc", "std"), draws=("auc", "size"),
                                                            min_auc=("auc", "min"), max_auc=("auc", "max"),
                                                            single_outside=("auc", lambda s: int(((s < 0.45) | (s > 0.55)).sum()))).reset_index()
    gate["outside"] = (gate["mean_auc"] < 0.45) | (gate["mean_auc"] > 0.55)
    gate.to_parquet(S.art("t5_negative_gate.parquet"), index=False)
    row2 = gate[gate["outside"]]

    # ---------------- baseline (T4 scores)
    auc = pd.read_parquet(S.art("t4_auc.parquet"))
    ll = pd.read_parquet(S.art("t4_logloss.parquet"))
    b = auc[(auc["time"] == "tau") & (auc["label_N"] == 100) & auc["model"].isin(["M0", "M1"])]
    base = b.groupby(["model", "read", "type"])["auc"].mean().unstack("type").reindex(columns=S.TYPES)
    llb = ll[(ll["time"] == "tau") & ll["model"].isin(["M0", "M1"])].groupby(["model", "read"])[["log_loss", "skill"]].mean()

    S.write_json("t5_summary.json", {
        "config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1),
        "row2_negative": {"rule": "mean per-fold primary AUC over 3 folds x 10 shuffles in [0.45, 0.55], per type x model x decision time",
                          "cells": int(len(gate)), "outside": int(len(row2)), "fires": bool(len(row2) > 0),
                          "outside_cells": row2.to_dict("records"),
                          "mean_auc_range": [float(gate["mean_auc"].min()), float(gate["mean_auc"].max())],
                          "single_shuffle_cells_outside_band": int(gate["single_outside"].sum()), "single_shuffle_cells": int(len(neg))},
        "row3_positive": {"rule": "rules leak: every type's per-fold primary AUC >= 0.95 (M2, M3, both class weights, every decision time)",
                          "cells": int(len(gated)), "below": int(len(row3)), "fires": bool(len(row3) > 0), "below_cells": row3.to_dict("records"),
                          "min_auc": float(gated["auc"].min())},
        "positive_terminal_log": {"by_type_mean": pos[pos["leak"] == "terminal_log"].groupby("type")["auc"].mean().reindex(S.TYPES).to_dict(),
                                  "by_type_min": pos[pos["leak"] == "terminal_log"].groupby("type")["auc"].min().reindex(S.TYPES).to_dict()},
        "baseline_tau": {"auc_mean_over_folds": {f"{m}|{r}": v for (m, r), v in base.to_dict("index").items()},
                         "log_loss_mean_over_folds": {f"{m}|{r}": v for (m, r), v in llb.to_dict("index").items()}},
    })
    print(f"row 2: {len(row2)} of {len(gate)} cells outside; row 3: {len(row3)} of {len(gated)} cells below 0.95")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
