"""
Shape classifier S2, T6 -- money relevance, without designing a strategy (brief section 5; Amendment 1 A1.4). Long
side only (D5).

Per label (A1.3: remaining-path type, primary; whole-path type, secondary), model variant, type and decision time:
the primary test events in each fold's top decile of the type's predicted probability (score >= its 90th percentile,
ties included) and bottom decile (score <= its 10th percentile), pooled over the three folds, against all labelled
primary test events that reached the decision time. Forward return from the decision time to +10, +30, +60 minutes
and to 20:00 -- entry at the first print after the decision time (zero latency, the upper bound), at d + 1 s and at
d + 5 s; exit at the last print at or before the horizon (T2) -- net of 70.98 bp flat and, separately, 2.512 cents
per share (D19).

A1.4 intervals: 500 ticker bootstrap resamples of the pooled primary test set at each decision time (the folds'
primary tickers are disjoint); each resample weights a row by its ticker's draw count; the median of the decile, of
all events, and their paired difference are recomputed per resample (weighted lower median); 95% percentile
intervals. Point estimates are the plain medians.

Writes artifacts/t6_forward.parquet, t6_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t6_money.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

CFG = S.load_cfg()
RT_BP, RT_C = CFG["money"]["cost"]["rt_bp"], CFG["money"]["cost"]["rt_cents"]
A14 = CFG["amendment_1"]["A1_4_money_intervals"]
LATS = ["lat0", "lat1s", "lat5s"]
HORS = ["h10", "h30", "h60", "to2000"]
QS = np.linspace(0, 1, 21)
B = 500


def wmedian_boot(x_sorted: np.ndarray, W_sorted: np.ndarray) -> np.ndarray:
    """Weighted lower median of x for every row of W (columns aligned with the sorted x). NaN where a resample
    gives the set zero weight."""
    if x_sorted.size == 0:
        return np.full(W_sorted.shape[0], np.nan)
    cw = np.cumsum(W_sorted, axis=1)
    tot = cw[:, -1]
    idx = (cw < (tot / 2.0)[:, None]).sum(axis=1)
    out = x_sorted[np.minimum(idx, x_sorted.size - 1)].astype(float)
    out[tot <= 0] = np.nan
    return out


def ci(v: np.ndarray) -> tuple[float, float, int]:
    v = v[np.isfinite(v)]
    return (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975)), int(v.size)) if v.size else (np.nan, np.nan, 0)


def stats(v: np.ndarray, state: np.ndarray) -> dict:
    ok = (state == "ok") & np.isfinite(v)
    x = v[ok]
    d = {"n_rows": int(len(v)), "n_ok": int(x.size), "n_no_entry": int((state == "no_entry").sum()),
         "n_past_2000": int((state == "horizon_past_2000").sum()), "n_no_print": int((state == "no_print_in_horizon").sum())}
    if x.size:
        d.update({"median": float(np.median(x)), "mean": float(x.mean()), "share_gt0": float((x > 0).mean()),
                  "q": [float(z) for z in np.quantile(x, QS)]})
    return d


def main() -> int:
    t_start = time.perf_counter()
    pop = S.load_population()
    tick = pop.set_index("event_id")["ticker"]
    pred = pd.read_parquet(S.art("t4_predictions.parquet"))
    pred = pred[pred["primary"]]
    st = pd.read_parquet(S.art("t2_checkpoints.parquet"), columns=["event_id", "time", "state"])
    fw = pd.read_parquet(S.art("t2_forward.parquet")).merge(st, on=["event_id", "time"])
    fw = fw[fw["state"] == "reached"]
    for ln in LATS:
        for h in HORS:
            fw[f"net_{ln}_{h}_bp"] = fw[f"fr_{ln}_{h}_gross_bp"] - RT_BP
            fw[f"net_{ln}_{h}_cents"] = fw[f"fr_{ln}_{h}_gross_cents"] - RT_C
    rows = []
    for li, label in enumerate(S.LABELS):
        for ti, tkey in enumerate(S.TIMES):
            pt = pred[(pred["label"] == label) & (pred["time"] == tkey)]
            base = pt[pt["model"] == "M0"][["event_id", "fold"]].merge(fw[fw["time"] == tkey], on="event_id", how="left").reset_index(drop=True)
            if base.empty:
                continue
            W = S.ticker_boot_weights(tick.loc[base["event_id"]].to_numpy(), B, A14["seed"] + 100 * li + ti)
            pos = pd.Series(np.arange(len(base)), index=base["event_id"])
            members = {}
            for (mdl, cw), g in pt.groupby(["model", "cw"]):
                if mdl == "M0":
                    continue
                for t in S.TYPES:
                    top, bot = [], []
                    for _, gf in g.groupby("fold"):
                        s = gf[f"p_{t}"].to_numpy(float)
                        top.append(gf.loc[s >= np.quantile(s, 0.9), "event_id"])
                        bot.append(gf.loc[s <= np.quantile(s, 0.1), "event_id"])
                    members[(mdl, cw, t, "top_decile")] = pos.loc[pd.concat(top)].to_numpy()
                    members[(mdl, cw, t, "bottom_decile")] = pos.loc[pd.concat(bot)].to_numpy()
            for ln in LATS:
                for h in HORS:
                    state = base[f"fr_{ln}_{h}_state"].fillna("no_entry").to_numpy()
                    for unit in ("bp", "cents"):
                        v = base[f"net_{ln}_{h}_{unit}"].to_numpy(float)
                        ok = (state == "ok") & np.isfinite(v)
                        oki = np.flatnonzero(ok)
                        order = oki[np.argsort(v[oki], kind="mergesort")]
                        Ws = W[:, order]
                        all_b = wmedian_boot(v[order], Ws)
                        key = {"label": label, "time": tkey, "latency": ln, "horizon": h, "unit": unit}
                        lo, hi, nb = ci(all_b)
                        rows.append({**key, "model": "all", "cw": "-", "type": "all", "set": "all", **stats(v, state),
                                     "median_ci_lo": lo, "median_ci_hi": hi, "n_boot": nb})
                        rank = np.full(len(base), -1)
                        rank[order] = np.arange(order.size)
                        for (mdl, cw, t, which), mem in members.items():
                            r = rank[mem]
                            r = np.sort(r[r >= 0])
                            sub_b = wmedian_boot(v[order][r], Ws[:, r])
                            d = stats(v[mem], state[mem])
                            lo, hi, nb = ci(sub_b)
                            dlo, dhi, dnb = ci(sub_b - all_b)
                            rows.append({**key, "model": mdl, "cw": cw, "type": t, "set": which, **d, "median_ci_lo": lo, "median_ci_hi": hi, "n_boot": nb,
                                         "diff_vs_all": (d["median"] - float(np.median(v[ok]))) if d.get("median") is not None and ok.any() else np.nan,
                                         "diff_ci_lo": dlo, "diff_ci_hi": dhi, "diff_n_boot": dnb})
            print(f"  {label} {tkey}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    out = pd.DataFrame(rows)
    out["q"] = out["q"].apply(lambda v: v if isinstance(v, list) else None)
    out["config_hash"] = S.cfg_hash()
    out.to_parquet(S.art("t6_forward.parquet"), index=False, compression="zstd")
    m = out[(out["latency"] == "lat0") & (out["unit"] == "bp") & (out["model"] == "M3") & (out["cw"] == "none")]
    summ = {}
    for lab in S.LABELS:
        for h in ("h30", "to2000"):
            for which in ("top_decile", "bottom_decile"):
                x = m[(m["label"] == lab) & (m["horizon"] == h) & (m["set"] == which)]
                summ[f"{lab}|{h}|{which}"] = {f"{r.type}|{r.time}": {"diff": r.diff_vs_all, "lo": r.diff_ci_lo, "hi": r.diff_ci_hi, "n_ok": r.n_ok}
                                              for r in x.itertuples()}
    S.write_json("t6_summary.json", {"config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "cost": {"rt_bp": RT_BP, "rt_cents": RT_C},
                                     "bootstrap": {"B": B, "unit": "ticker", "seed": f"{A14['seed']} + 100 x label index + decision-time index"},
                                     "m3_none_lat0_bp_diff_vs_all": summ})
    x = m[(m["label"] == "remaining") & (m["horizon"] == "h30") & (m["set"] == "top_decile")].pivot(index="type", columns="time", values="diff_vs_all")
    print(x.reindex(S.TYPES)[S.TIMES].round(0).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
