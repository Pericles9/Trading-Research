"""
Shape classifier S2, T5 -- the section 6 controls, under Cooper's rulings R4 and R5 and Amendment 1 (A1.1: row 3
gates M3; M2 is reported beside it, ungated), for both labels (A1.3: the remaining-path type, primary; the
whole-path type, secondary).

  negative  10 independent label shuffles per fold: the training window's labels permuted, the Group C typical
            paths rebuilt from the permuted labels, M1-M4 (both class weights) refitted at the real run's chosen
            settings, each fold's primary test set scored against the true labels. The whole label is one
            permutation per (shuffle, fold) across decision times; the remaining label differs by decision time, so
            it is permuted per decision time. Row 2 reads the mean AUC over the 3 folds x 10 shuffles per label x
            type x model x decision time against [0.45, 0.55]; single-shuffle per-fold values are kept beside it.
  positive  M2 and M3 (both class weights, real run's settings) with a leak added at every decision time, per label:
            'rules' = the three numbers S1's type rules read, for that label's path (whole: post100 rise_pct,
            fall_pct, u_peak; remaining: the remaining path's, T3a), gated by row 3 on M3 (every per-fold primary
            AUC >= 0.95); 'terminal_log' = the brief's construction, for that label's path, reported, ungated.
  baseline  M1 vs M0 at tau, read from T4's scores.
At tau the remaining label is the whole label (A1.3), so its control rows are the whole-label rows, copied.

Writes artifacts/t5_negative.parquet, t5_negative_gate.parquet, t5_positive.parquet, t5_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t5_controls.py
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
import t2_checkpoints as T2  # noqa: E402
import t4_models as T4  # noqa: E402

SHUFFLES = 10
LEAKS = {"rules": ("leak_rise_pct", "leak_fall_pct", "leak_u_peak"), "terminal_log": ("leak_terminal_log",)}
GATED_MODELS = ("M3",)                      # Amendment 1 A1.1


def chosen_settings() -> dict:
    out = {}
    for j in S.read_json("t4_summary.json")["jobs"]:
        out[(j["label"], j["fold"], j["time"])] = {tuple(k.split("|")): v for k, v in j["chosen"].items()}
    return out


def primary_auc(res: dict, labels_true: np.ndarray, key: dict) -> list[dict]:
    D = T4.load_data()
    pr = res["pred"]
    pr = pr[pr["primary"] & (pr["model"] != "M0")]
    rows = []
    for (mdl, cw), g in pr.groupby(["model", "cw"]):
        yy = S.y_codes(labels_true[g["event_id"].map(D["pos"]).to_numpy()])
        for i, t in enumerate(S.TYPES):
            rows.append({**key, "model": mdl, "cw": cw, "type": t, "n": int(len(g)), "n_type": int((yy == i).sum()),
                         "auc": S.auc_weighted(yy == i, g[f"p_{t}"].to_numpy(float))})
    return rows


def neg_job(args):
    r, fold, label, fixed_all = args
    D = T4.load_data()
    pop = D["pop"]
    M = D["masks"][fold]
    (y0, y1), yt = S.FOLDS[fold]
    yr = pop["year"].to_numpy()
    stage = {(fold, "final"): (M["train"], (yr >= y0) & (yr <= yt))}
    times = S.TIMES if label == "whole" else S.TIMES[1:]
    rows, gc_whole, lab_whole = [], None, None
    for ti, t in enumerate(times):
        true = S.labels_at(pop, label, t)
        if label == "whole" and lab_whole is not None:
            lab, gc = lab_whole, gc_whole
        else:
            lab = true.copy()
            idx = np.flatnonzero(M["train"] & (S.y_codes(true) >= 0))
            seed = [S.SEED, r, fold] if label == "whole" else [S.SEED, r, fold, 1, S.TIMES.index(t)]
            lab[idx] = lab[idx][np.random.default_rng(seed).permutation(idx.size)]
            ck = D["ck"] if label == "whole" else D["ck"][D["ck"]["time"] == t]
            gc, _ = T2.group_c(pop, D["P"], ck, pd.Series(lab), stage)
            if label == "whole":
                lab_whole, gc_whole = lab, gc
        res = T4.run_job(fold, t, label=label, labels=lab, gc=gc, fixed=fixed_all[(label, fold, t)], models=("M1", "M2", "M3", "M4"))
        rows += primary_auc(res, true, {"label": label, "shuffle": r, "fold": fold, "time": t})
    return rows


def pos_job(args):
    leak, label, fold, t, fixed = args
    D = T4.load_data()
    res = T4.run_job(fold, t, label=label, fixed=fixed, extra=LEAKS[leak], models=("M2", "M3"))
    return primary_auc(res, S.labels_at(D["pop"], label, t), {"leak": leak, "label": label, "fold": fold, "time": t})


def copy_tau(df: pd.DataFrame) -> pd.DataFrame:
    """At tau the remaining label is the whole label (A1.3): its rows are the whole-label rows."""
    return pd.concat([df, df[(df["label"] == "whole") & (df["time"] == "tau")].assign(label="remaining")], ignore_index=True)


def main() -> int:
    t_start = time.perf_counter()
    fixed = chosen_settings()
    # ---------------- positive
    jobs = [(lk, lab, f, t, fixed[(lab, f, t)]) for lab in S.LABELS for lk in LEAKS for t in S.TIMES for f in S.FOLDS
            if not (lab == "remaining" and t == "tau")]
    pos = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for rows in ex.map(pos_job, jobs):
            pos += rows
    pos = copy_tau(pd.DataFrame(pos))
    pos["config_hash"] = S.cfg_hash()
    pos.to_parquet(S.art("t5_positive.parquet"), index=False)
    gated = pos[(pos["leak"] == "rules") & pos["model"].isin(GATED_MODELS)]
    row3 = gated[gated["auc"] < 0.95]
    m2 = pos[(pos["leak"] == "rules") & (pos["model"] == "M2")]
    print(f"positive done {time.perf_counter() - t_start:,.0f}s; row 3 (M3) cells below 0.95: {len(row3)}; M2 (ungated) below: {int((m2['auc'] < 0.95).sum())}", flush=True)
    # ---------------- negative
    jobs = [(r, f, lab, fixed) for lab in S.LABELS for r in range(SHUFFLES) for f in S.FOLDS]
    neg = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for n, rows in enumerate(ex.map(neg_job, jobs)):
            neg += rows
            print(f"  negative {n + 1}/{len(jobs)}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    neg = copy_tau(pd.DataFrame(neg))
    neg["config_hash"] = S.cfg_hash()
    neg.to_parquet(S.art("t5_negative.parquet"), index=False)
    gate = neg.groupby(["label", "model", "cw", "time", "type"]).agg(mean_auc=("auc", "mean"), sd_auc=("auc", "std"), draws=("auc", "size"),
                                                                     min_auc=("auc", "min"), max_auc=("auc", "max"),
                                                                     single_outside=("auc", lambda s: int(((s < 0.45) | (s > 0.55)).sum()))).reset_index()
    gate["outside"] = (gate["mean_auc"] < 0.45) | (gate["mean_auc"] > 0.55)
    gate.to_parquet(S.art("t5_negative_gate.parquet"), index=False)
    row2 = gate[gate["outside"]]

    # ---------------- baseline (T4 scores)
    auc = pd.read_parquet(S.art("t4_auc.parquet"))
    ll = pd.read_parquet(S.art("t4_logloss.parquet"))
    b = auc[(auc["label"] == "whole") & (auc["time"] == "tau") & (auc["label_N"] == 100) & auc["model"].isin(["M0", "M1"])]
    base = b.groupby(["model", "read", "type"])["auc"].mean().unstack("type").reindex(columns=S.TYPES)
    llb = ll[(ll["label"] == "whole") & (ll["time"] == "tau") & ll["model"].isin(["M0", "M1"])].groupby(["model", "read"])[["log_loss", "skill"]].mean()

    per_label = {}
    for lab in S.LABELS:
        g2, g3, gm2 = gate[gate["label"] == lab], gated[gated["label"] == lab], m2[m2["label"] == lab]
        per_label[lab] = {
            "row2": {"cells": int(len(g2)), "outside": int(g2["outside"].sum()), "mean_auc_range": [float(g2["mean_auc"].min()), float(g2["mean_auc"].max())],
                     "single_shuffle_cells_outside_band": int(g2["single_outside"].sum()), "single_shuffle_cells": int((neg["label"] == lab).sum())},
            "row3_m3": {"cells": int(len(g3)), "below": int((g3["auc"] < 0.95).sum()), "min_auc": float(g3["auc"].min())},
            "m2_ungated": {"cells": int(len(gm2)), "below": int((gm2["auc"] < 0.95).sum()), "min_auc": float(gm2["auc"].min()),
                           "below_cells": gm2[gm2["auc"] < 0.95].to_dict("records")},
            "terminal_log_by_type_mean": pos[(pos["leak"] == "terminal_log") & (pos["label"] == lab)].groupby("type")["auc"].mean().reindex(S.TYPES).to_dict(),
        }
    S.write_json("t5_summary.json", {
        "config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1),
        "row2_negative": {"rule": "mean per-fold primary AUC over 3 folds x 10 shuffles in [0.45, 0.55], per label x type x model x decision time",
                          "cells": int(len(gate)), "outside": int(len(row2)), "fires": bool(len(row2) > 0), "outside_cells": row2.to_dict("records"),
                          "mean_auc_range": [float(gate["mean_auc"].min()), float(gate["mean_auc"].max())],
                          "single_shuffle_cells_outside_band": int(gate["single_outside"].sum()), "single_shuffle_cells": int(len(neg))},
        "row3_positive": {"rule": "A1.1: rules leak, M3 (both class weights): every per-fold primary AUC >= 0.95, every type and decision time, each label; M2 reported, ungated",
                          "cells": int(len(gated)), "below": int(len(row3)), "fires": bool(len(row3) > 0), "below_cells": row3.to_dict("records"),
                          "min_auc": float(gated["auc"].min())},
        "per_label": per_label,
        "baseline_tau": {"auc_mean_over_folds": {f"{m}|{r}": v for (m, r), v in base.to_dict("index").items()},
                         "log_loss_mean_over_folds": {f"{m}|{r}": v for (m, r), v in llb.to_dict("index").items()}},
    })
    print(f"row 2: {len(row2)} of {len(gate)} cells outside; row 3 (M3): {len(row3)} of {len(gated)} cells below 0.95")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
