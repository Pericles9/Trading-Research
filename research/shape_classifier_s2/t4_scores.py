"""
Shape classifier S2, T4 scores -- per type, model variant, decision time, fold and read (primary / secondary).

  AUC        one type vs the rest; 95% interval from 500 ticker bootstrap resamples of that test set
  lift       share of the type among events at or above the 90th percentile of its score / its test-set share
  calibration predicted probability bins (config edges) against observed frequency, n per bin
  log loss   multiclass, model and M0 on the same test rows; skill = 1 - LL / LL_M0
  confusion  argmax type vs true type, counts
  rungs      the N = 100 models' AUC against the N = 50 and N = 200 labels (secondary labels, never fitted)
  row 5      primary cells with fewer than 20 events of a type (reached events) are marked read = False

Writes artifacts/t4_auc.parquet, t4_lift.parquet, t4_calibration.parquet, t4_logloss.parquet, t4_confusion.parquet,
t4_scores_summary.json (the AUC-by-time table for the primary read).

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t4_scores.py [predictions parquet name] [output prefix]
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

B = 500
EDGES = np.array(S.load_cfg()["scores"]["calibration_edges"])


def score(pred: pd.DataFrame, prefix: str = "t4", boot: bool = True) -> dict:
    pop = S.load_population()
    whole = {N: pop.set_index("event_id")[f"type{N}"] for N in (50, 100, 200)}
    rem = S.remaining_table()
    tick = pop.set_index("event_id")["ticker"]
    r5 = pd.read_parquet(S.art("t3_row5.parquet"))
    r5k = set(zip(r5["label"], r5["fold"], r5["time"], r5["type"]))
    PC = [f"p_{t}" for t in S.TYPES]
    auc, lift, cal, ll, conf = [], [], [], [], []
    for (label, fold, tkey), g in pred.groupby(["label", "fold", "time"], sort=False):
        if label == "whole":
            lab = whole
        else:                                   # the remaining-path type at this decision time (N = 100 only)
            lab = {100: rem[rem["time"] == tkey].set_index("event_id")["rem_type"]}
        m0 = g[(g["model"] == "M0")]
        for read in ("primary", "secondary"):
            rows0 = m0 if read == "secondary" else m0[m0["primary"]]
            ids = rows0["event_id"].to_numpy()
            if len(ids) == 0:
                continue
            W = S.ticker_boot_weights(tick.loc[ids].to_numpy(), B, S.SEED + fold) if boot else None
            y100 = S.y_codes(lab[100].loc[ids].to_numpy())
            ll0 = S.log_loss(y100, rows0[PC].to_numpy())
            for (mdl, cw), gm in g.groupby(["model", "cw"], sort=False):
                gm = gm if read == "secondary" else gm[gm["primary"]]
                gm = gm.set_index("event_id").loc[ids]
                Pm = gm[PC].to_numpy(dtype=float)
                key = {"label": label, "fold": fold, "time": tkey, "model": mdl, "cw": cw, "read": read}
                L = S.log_loss(y100, Pm)
                ll.append({**key, "n": len(ids), "log_loss": L, "log_loss_m0": ll0, "skill": 1.0 - L / ll0})
                am = Pm.argmax(axis=1)
                cm = np.zeros((6, 6), dtype=int)
                np.add.at(cm, (y100, am), 1)
                for i, ti in enumerate(S.TYPES):
                    for j, tj in enumerate(S.TYPES):
                        conf.append({**key, "true": ti, "pred": tj, "n": int(cm[i, j])})
                for i, t in enumerate(S.TYPES):
                    s = Pm[:, i]
                    readable = not (read == "primary" and (label, fold, tkey, t) in r5k)
                    for N in [n for n in (100, 50, 200) if n in lab]:
                        y = S.y_codes(lab[N].loc[ids].to_numpy()) == i
                        ok = S.y_codes(lab[N].loc[ids].to_numpy()) >= 0
                        if N == 100 and boot:
                            a, lo, hi = S.auc_ci(y, s, W)
                        else:
                            a, lo, hi = S.auc_weighted(y[ok], s[ok]), np.nan, np.nan
                        auc.append({**key, "type": t, "label_N": N, "n": int(ok.sum()), "n_type": int(y[ok].sum()), "auc": a,
                                    "ci_lo": lo, "ci_hi": hi, "read_ok": readable})
                    y = y100 == i
                    lf, ntop = S.lift_top10(y, s)
                    lift.append({**key, "type": t, "n": len(ids), "n_type": int(y.sum()), "lift": lf, "n_top": ntop,
                                 "n_type_top": int(y[s >= np.quantile(s, 0.9)].sum()), "read_ok": readable})
                    b = np.clip(np.searchsorted(EDGES, s, side="right") - 1, 0, len(EDGES) - 2)
                    for k in range(len(EDGES) - 1):
                        m = b == k
                        cal.append({**key, "type": t, "bin_lo": EDGES[k], "bin_hi": EDGES[k + 1], "n": int(m.sum()),
                                    "mean_pred": float(s[m].mean()) if m.any() else np.nan,
                                    "obs_freq": float(y[m].mean()) if m.any() else np.nan})
    out = {"auc": pd.DataFrame(auc), "lift": pd.DataFrame(lift), "calibration": pd.DataFrame(cal), "logloss": pd.DataFrame(ll),
           "confusion": pd.DataFrame(conf)}
    for k, v in out.items():
        v["config_hash"] = S.cfg_hash()
        v.to_parquet(S.art(f"{prefix}_{k}.parquet"), index=False)
    return out


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "t4_predictions.parquet"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "t4"
    pred = pd.read_parquet(S.art(name))
    out = score(pred, prefix)
    a = out["auc"]
    p = a[(a["read"] == "primary") & (a["label_N"] == 100) & a["read_ok"]]          # row 5: unread folds left out of the means
    tab = p.groupby(["label", "model", "cw", "type", "time"]).agg(auc_mean=("auc", "mean"), auc_min=("auc", "min"), auc_max=("auc", "max"),
                                                                   n_type=("n_type", "sum"), folds_read=("read_ok", "sum")).reset_index()
    S.write_json(f"{prefix}_scores_summary.json", {
        "config_hash": S.cfg_hash(), "bootstrap": {"B": B, "unit": "ticker", "seed": f"{S.SEED} + fold"},
        "primary_auc_by_time": {f"{r.label}|{r.model}|{r.cw}|{r.type}|{r.time}": {"mean": r.auc_mean, "min": r.auc_min, "max": r.auc_max,
                                                                       "n_type_3folds": int(r.n_type), "folds_read": int(r.folds_read)}
                                for r in tab.itertuples()},
        "logloss_skill_primary": {f"{lb}|{m}|{c}|{t}": v for (lb, m, c, t), v in
                                  out["logloss"][out["logloss"]["read"] == "primary"].groupby(["label", "model", "cw", "time"])["skill"].mean().items()},
    })
    for lb in S.LABELS:
        for mdl in ("M3", "M2"):
            t = tab[(tab["label"] == lb) & (tab["model"] == mdl) & (tab["cw"] == "none")].pivot(index="type", columns="time", values="auc_mean").reindex(S.TYPES)[S.TIMES]
            print(lb, mdl, "none, primary AUC (mean of the readable folds)")
            print(t.round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
