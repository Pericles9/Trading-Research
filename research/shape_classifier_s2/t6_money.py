"""
Shape classifier S2, T6 -- money relevance, without designing a strategy (brief section 5). Long side only (D5).

For each model variant, type and decision time: the primary test events in that fold's top decile of the type's
predicted probability (score >= its 90th percentile, ties included), pooled over the three folds. Their forward
return from the decision time to +10, +30, +60 minutes and to 20:00 -- entry at the first print after the decision
time (zero latency, the upper bound; entries at d + 1 s and d + 5 s beside it), exit at the last print at or before
the horizon (T2) -- net of 70.98 bp flat and, separately, 2.512 cents per share (D19). Against the same figure
for all primary test events that reached the decision time.

Writes artifacts/t6_forward.parquet (summary statistics and 21 quantiles per cell), t6_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t6_money.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

CFG = S.load_cfg()
RT_BP, RT_C = CFG["money"]["cost"]["rt_bp"], CFG["money"]["cost"]["rt_cents"]
LATS = ["lat0", "lat1s", "lat5s"]
HORS = ["h10", "h30", "h60", "to2000"]
QS = np.linspace(0, 1, 21)


def stats(v: np.ndarray, state: np.ndarray) -> dict:
    ok = state == "ok"
    x = v[ok & np.isfinite(v)]
    d = {"n_rows": int(len(v)), "n_ok": int(x.size), "n_no_entry": int((state == "no_entry").sum()),
         "n_past_2000": int((state == "horizon_past_2000").sum()), "n_no_print": int((state == "no_print_in_horizon").sum())}
    if x.size:
        d.update({"median": float(np.median(x)), "mean": float(x.mean()), "share_gt0": float((x > 0).mean()),
                  "q": [float(z) for z in np.quantile(x, QS)]})
    return d


def main() -> int:
    pred = pd.read_parquet(S.art("t4_predictions.parquet"))
    pred = pred[pred["primary"]]
    ck = pd.read_parquet(S.art("t2_checkpoints.parquet"))
    ck = ck[ck["state"] == "reached"]
    cols = ["event_id", "time"] + [c for c in ck.columns if c.startswith("fr_")]
    ck = ck[cols]
    for ln in LATS:
        for h in HORS:
            ck[f"net_{ln}_{h}_bp"] = ck[f"fr_{ln}_{h}_gross_bp"] - RT_BP
            ck[f"net_{ln}_{h}_cents"] = ck[f"fr_{ln}_{h}_gross_cents"] - RT_C
    rows = []
    for tkey in S.TIMES:
        pt = pred[pred["time"] == tkey]
        allid = pt[pt["model"] == "M0"][["event_id", "fold"]]
        base = allid.merge(ck[ck["time"] == tkey], on="event_id", how="left")
        for ln in LATS:
            for h in HORS:
                st = base[f"fr_{ln}_{h}_state"].fillna("no_entry").to_numpy()
                for unit in ("bp", "cents"):
                    rows.append({"time": tkey, "model": "all", "cw": "-", "type": "all", "latency": ln, "horizon": h, "unit": unit, "set": "all",
                                 **stats(base[f"net_{ln}_{h}_{unit}"].to_numpy(float), st)})
        for (mdl, cw), g in pt.groupby(["model", "cw"]):
            if mdl == "M0":
                continue
            for t in S.TYPES:
                top = []
                for f, gf in g.groupby("fold"):
                    s = gf[f"p_{t}"].to_numpy(float)
                    top.append(gf.loc[s >= np.quantile(s, 0.9), "event_id"])
                ids = pd.concat(top)
                sub = base[base["event_id"].isin(set(ids))]
                for ln in LATS:
                    for h in HORS:
                        st = sub[f"fr_{ln}_{h}_state"].fillna("no_entry").to_numpy()
                        for unit in ("bp", "cents"):
                            rows.append({"time": tkey, "model": mdl, "cw": cw, "type": t, "latency": ln, "horizon": h, "unit": unit, "set": "top_decile",
                                         **stats(sub[f"net_{ln}_{h}_{unit}"].to_numpy(float), st)})
    out = pd.DataFrame(rows)
    out["q"] = out["q"].apply(lambda v: v if isinstance(v, list) else None)
    out["config_hash"] = S.cfg_hash()
    out.to_parquet(S.art("t6_forward.parquet"), index=False)
    m = out[(out["latency"] == "lat0") & (out["unit"] == "bp") & (out["horizon"] == "h30")]
    allm = m[m["set"] == "all"].set_index("time")["median"]
    top = m[(m["set"] == "top_decile") & (m["model"] == "M3") & (m["cw"] == "none")].pivot(index="type", columns="time", values="median")
    S.write_json("t6_summary.json", {"config_hash": S.cfg_hash(), "cost": {"rt_bp": RT_BP, "rt_cents": RT_C},
                                     "all_primary_median_net_bp_h30_lat0": allm.to_dict(),
                                     "m3_top_decile_median_net_bp_h30_lat0": top.to_dict("index")})
    print(allm.round(1).to_string())
    print(top.reindex(S.TYPES)[S.TIMES].round(1).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
