"""
Shape atlas S1, T5 -- the atlas: everything that goes with each type (section 6), and the type share by
date. Exploratory, hindsight used by design; nothing here is a tested result. F1-layer columns are
described per type under D39.

For every (view, typing, k, type) -- theory types (post view), declared run-up classes (run-up view),
and every cluster of both methods at every k in every view:
  centroid     members' mean resampled path, pointwise IQR band, and the null centroid (members' null
               draw 0 through the identical pipeline)
  gallery      the 12 members nearest the centroid and 12 drawn at random (seeded), each with its actual
               N = 100 bucketed path, tau, peak and end
  money        post-tau vector at N = 100 (u_peak, rise_s, fall_s, dip, terminal), rise_bp, rise_cents,
               fall_bp, minutes to peak, excess_rise_bp (= rise_bp - the event's own null median rise)
  descriptors  attention, catalyst, fundamentals, tape, run-up (config atlas.descriptors): continuous as
               41 quantiles with n, categorical as shares with n
Type by date: chi-square of the date x type table against 200 seeded label permutations.

Writes artifacts/t5_descriptors.parquet (one row per event: every descriptor), t5_atlas.json (the
atlas.html data), t5_type_by_date.parquet, t5_summary.json.

Usage: .venv/Scripts/python.exe research/shape_atlas_s1/t5_atlas.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1common as S  # noqa: E402

CFG = S.load_cfg()
G = CFG["views"]["resample"]["G"]
QS = np.linspace(0, 1, 41)
MONEY = ["post100_u_peak", "post100_rise_s", "post100_fall_s", "post100_dip_before_peak_s", "post100_terminal_s", "post100_rise_bp",
         "rise_cents", "post100_fall_bp", "minutes_to_peak", "excess_rise_bp"]
CONT = {"attention": ["turnover", *[f"accel_k{k}" for k in range(13)], "trades_per_min_k0", "trades_per_min_finest", "dollars_per_min_k0",
                      "dollars_per_min_finest", "flow_share_rest_finest", "live_n_15", "live_n_60", "live_n_rest", "competition_excess_j"],
        "fundamentals": ["shs_shares_outstanding_corrected", "si_shares_short", "short_interest_share"],
        "tape": ["jump_share", "hours_after_0400"],
        "runup": ["gap_share", "runup_u_launch", "runup_height_s", "runup_max_drawdown_s", "runup_pushes", "runup_minutes", "runup_shares"]}
CAT = {"attention": ["a2_ignition"], "catalyst": ["filing_24h", "last_form_before_tau", "flg_dilution_form_before_t0"],
       "fundamentals": ["spl_reverse_split_365d"],
       "tape": ["halt_in_path", "tau_close_sensitive", "flag_cross_session_extreme", "tau_anchor_segment", "year", "price_tier"],
       "runup": ["runup_class"]}


def descriptors() -> pd.DataFrame:
    ev = pd.read_parquet(S.art("s1_events.parquet"))
    d = ev[["event_id", "ticker", "event_date_canonical", "year", "tau_anchor_segment", "price_tier", "tau_close_sensitive",
            "flag_cross_session_extreme", "sec_from_0400", "gap_share", "whole_u_tau", "post100_u_peak", "post100_rise_s", "post100_fall_s",
            "post100_dip_before_peak_s", "post100_terminal_s", "post100_rise_bp", "post100_fall_bp", "post100_null_median_rise_bp",
            "runup_u_launch", "runup_height_s", "runup_max_drawdown_s", "runup_pushes", "runup_minutes", "runup_shares", "runup_u_peak",
            "whole_u_peak"]].copy()
    d["excess_rise_bp"] = d["post100_rise_bp"] - d["post100_null_median_rise_bp"]
    d["hours_after_0400"] = d["sec_from_0400"] / 3600.0
    x = pd.read_parquet(S.src("excursion"), columns=["event_id", "N", "rise_cents", "t_peak_s", "jump_share", "halt_in_path"])
    x = x[x["N"] == 100].drop(columns="N")
    x["minutes_to_peak"] = x.pop("t_peak_s") / 60.0
    d = d.merge(x, on="event_id", how="left")
    at = pd.read_parquet(S.src("attention"), columns=["event_id", "turnover", "a2_ignition", "filing_24h", "last_form_before_tau",
                                                      "flg_dilution_form_before_t0", "shs_shares_outstanding_corrected"])
    d = d.merge(at, on="event_id", how="left")
    rg = pd.read_parquet(S.src("a2_rungs"), columns=["event_id", "k", "valid", "accel", "trades_per_min", "dollars_per_min"])
    v = rg[rg["valid"]]
    acc = v[v["k"] <= 12].pivot(index="event_id", columns="k", values="accel")
    acc.columns = [f"accel_k{int(c)}" for c in acc.columns]
    d = d.merge(acc, left_on="event_id", right_index=True, how="left")
    k0 = v[v["k"] == 0].set_index("event_id")[["trades_per_min", "dollars_per_min"]].add_suffix("_k0")
    fin = v.sort_values("k").groupby("event_id").tail(1).set_index("event_id")[["trades_per_min", "dollars_per_min"]].add_suffix("_finest")
    d = d.merge(k0, left_on="event_id", right_index=True, how="left").merge(fin, left_on="event_id", right_index=True, how="left")
    xs = pd.read_parquet(S.src("cross_section"), columns=["event_id", "liveness", "k", "live_n", "flow_share"])
    ln = xs.drop_duplicates(["event_id", "liveness"]).pivot(index="event_id", columns="liveness", values="live_n")
    ln.columns = [f"live_n_{'rest' if c == 'rest_of_session' else c}" for c in ln.columns]
    fs = xs[(xs["liveness"] == "rest_of_session") & xs["k"].notna()].sort_values("k").groupby("event_id").tail(1).set_index("event_id")[["flow_share"]]
    fs.columns = ["flow_share_rest_finest"]
    d = d.merge(ln, left_on="event_id", right_index=True, how="left").merge(fs, left_on="event_id", right_index=True, how="left")
    cp = pd.read_parquet(S.src("competition"), columns=["j", "liveness", "W_min", "status", "baseline_thin", "excess"])
    cp = cp[(cp["liveness"].astype(str) == "rest_of_session") & (cp["W_min"] == 15) & (cp["status"].astype(str) == "ok") & ~cp["baseline_thin"]]
    d = d.merge(cp.groupby("j")["excess"].median().rename("competition_excess_j"), left_on="event_id", right_index=True, how="left")
    fu = S.C1.load_fundamentals_corrected()[["event_id", "si_shares_short", "spl_reverse_split_365d"]]
    d = d.merge(fu, on="event_id", how="left")
    d["short_interest_share"] = d["si_shares_short"] / d["shs_shares_outstanding_corrected"]
    rc = pd.read_parquet(S.art("s1_runup_classes.parquet"), columns=["event_id", "runup_class"])
    d = d.merge(rc, on="event_id", how="left")
    assert len(d) == len(ev) and d["event_id"].is_unique
    return d


def qvec(v) -> dict:
    v = pd.to_numeric(pd.Series(v), errors="coerce").dropna().to_numpy(float)
    return {"n": int(v.size), "q": [round(float(x), 6) for x in np.quantile(v, QS)] if v.size else []}


def cvec(v) -> dict:
    s = pd.Series(v).astype("string").fillna("missing")
    vc = s.value_counts()
    return {"n": int(s.size), "levels": {str(k): int(x) for k, x in vc.items()}}


def view_data(view: str, ev: pd.DataFrame):
    P = pd.read_parquet(S.art(f"s1_paths_{view}.parquet"))
    lp = P[[f"b{i:03d}" for i in range(101)]].to_numpy()
    c = S.comps_batch(lp)
    X = S.resample(lp, c["sigma_path"], G)
    eidx = ev.set_index("event_id").loc[P["event_id"], "event_index"].to_numpy()
    XN = np.full_like(X, np.nan)
    for i in range(len(P)):
        if not c["sigma_zero"][i]:
            XN[i] = S.null_pipeline(lp[i], S.null_index(CFG, int(eidx[i]), view, 100, 1), G)[2][0]
    return P["event_id"].to_numpy(), lp, X, XN, c


def main() -> int:
    ev = pd.read_parquet(S.art("s1_events.parquet"))
    d = descriptors()
    d["config_hash"] = S.cfg_hash()
    d.to_parquet(S.art("t5_descriptors.parquet"), index=False)
    dd = d.set_index("event_id")
    tt = pd.read_parquet(S.art("s1_theory_types.parquet"))
    tt = tt[(tt["N"] == 100) & (tt["type_state"] == "typed")].set_index("event_id")["theory_type"]
    rc = dd["runup_class"]
    gcfg = CFG["atlas"]["gallery"]
    entries, allref = [], {}
    for grp, cols in CONT.items():
        for c in cols:
            allref[c] = qvec(dd[c])
    for grp, cols in CAT.items():
        for c in cols:
            allref[c] = cvec(dd[c])
    for c in MONEY:
        allref[c] = qvec(dd[c])
    combo = 0
    for view in ("post", "whole_day", "runup"):
        ids, lp, X, XN, comp = view_data(view, ev)
        okv = np.isfinite(X).all(axis=1)
        pos = {e: i for i, e in enumerate(ids)}
        typings = []
        if view == "post":
            typings.append(("theory", None, tt))
        if view == "runup":
            typings.append(("declared", None, rc[rc.index.isin(ids)]))
        asg = pd.read_parquet(S.art(f"t3_{view}_assignments.parquet"))
        for (method, k), g in asg.groupby(["method", "k"]):
            typings.append((method, int(k), g.set_index("event_id")["label"].astype(int).astype(str)))
        for typing, k, lab in typings:
            for t in sorted(lab.dropna().unique(), key=str):
                mem = [e for e in lab.index[lab == t] if e in pos]
                rows = np.array([pos[e] for e in mem], dtype=int)
                rows = rows[okv[rows]] if rows.size else rows
                entry = {"view": view, "typing": typing, "k": k, "type": str(t), "n": int(len(mem)), "n_with_path": int(rows.size)}
                if rows.size:
                    Xm = X[rows]
                    mean = Xm.mean(axis=0)
                    q = np.percentile(Xm, [25, 75], axis=0)
                    entry["centroid"] = {"mean": np.round(mean, 4).tolist(), "p25": np.round(q[0], 4).tolist(), "p75": np.round(q[1], 4).tolist(),
                                         "null": np.round(np.nanmean(XN[rows], axis=0), 4).tolist()}
                    dist = np.sqrt(((Xm - mean) ** 2).sum(axis=1))
                    near = rows[np.argsort(dist, kind="stable")[: gcfg["closest"]]]
                    rest = np.setdiff1d(rows, near)
                    rng = np.random.default_rng([gcfg["seed"], combo])
                    rnd = rng.choice(rest, size=min(gcfg["random"], rest.size), replace=False) if rest.size else rest
                    gal = []
                    for kind, sel in (("nearest", near), ("random", rnd)):
                        for i in sel:
                            e = ids[i]
                            r = dd.loc[e]
                            tau_u = 0.0 if view == "post" else (1.0 if view == "runup" else float(r["whole_u_tau"]))
                            gal.append({"event_id": e, "ticker": r["ticker"], "date": r["event_date_canonical"], "kind": kind,
                                        "y_bp": np.round(lp[i] * 1e4, 2).tolist(), "u_peak": float(comp["u_peak"][i]), "tau_u": tau_u})
                    entry["gallery"] = gal
                sub = dd.loc[[e for e in mem if e in dd.index]]
                entry["money"] = {c: qvec(sub[c]) for c in MONEY}
                entry["desc"] = {c: qvec(sub[c]) for cols in CONT.values() for c in cols}
                entry["cat"] = {c: cvec(sub[c]) for cols in CAT.values() for c in cols}
                entries.append(entry)
                combo += 1
        print(view, "entries so far", len(entries), flush=True)

    # ------------------------------------------------ type share by date
    tcfg = CFG["type_by_date"]
    rng = np.random.default_rng(tcfg["seed"])
    date_of = dd["event_date_canonical"]
    tbd = []
    typings = [("post", "theory", None, tt)]
    for view in ("post", "whole_day", "runup"):
        asg = pd.read_parquet(S.art(f"t3_{view}_assignments.parquet"))
        for (method, k), g in asg.groupby(["method", "k"]):
            typings.append((view, method, int(k), g.set_index("event_id")["label"]))
    typings.append(("runup", "declared", None, rc))
    for view, typing, k, lab in typings:
        lab = lab.dropna()
        dates = date_of.loc[lab.index].to_numpy()
        di = pd.factorize(dates)[0]
        li = pd.factorize(lab.to_numpy())[0]
        nd, nt = di.max() + 1, li.max() + 1

        def chi2(labels):
            tab = np.bincount(di * nt + labels, minlength=nd * nt).reshape(nd, nt).astype(float)
            exp = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
            m = exp > 0
            return float((((tab - exp) ** 2)[m] / exp[m]).sum())
        obs = chi2(li)
        perm = np.array([chi2(rng.permutation(li)) for _ in range(tcfg["permutations"])])
        tbd.append({"view": view, "typing": typing, "k": k, "events": int(lab.size), "dates": int(nd), "types": int(nt),
                    "chi2_observed": obs, "chi2_perm_mean": float(perm.mean()), "chi2_perm_p95": float(np.quantile(perm, 0.95)),
                    "ratio_obs_to_perm_mean": obs / float(perm.mean()), "share_perm_ge_observed": float((perm >= obs).mean())})
    tbd = pd.DataFrame(tbd)
    tbd["config_hash"] = S.cfg_hash()
    tbd.to_parquet(S.art("t5_type_by_date.parquet"), index=False)
    perday = pd.DataFrame({"date": date_of.loc[tt.index].to_numpy(), "type": tt.to_numpy()}).groupby(["date", "type"]).size().unstack(fill_value=0)
    perday.to_parquet(S.art("t5_theory_types_per_date.parquet"))

    with open(S.art("t5_atlas.json"), "w", encoding="utf-8") as f:
        json.dump({"config_hash": S.cfg_hash(), "G": G, "quantiles": QS.round(4).tolist(), "groups": {**{g: c for g, c in CONT.items()}},
                   "cat_groups": CAT, "money": MONEY, "all_events": allref, "entries": entries}, f, separators=(",", ":"))
    S.write_json("t5_summary.json", {"config_hash": S.cfg_hash(), "atlas_entries": len(entries),
                                     "descriptor_coverage": {c: int(dd[c].notna().sum()) for cols in list(CONT.values()) + list(CAT.values()) for c in cols},
                                     "type_by_date": tbd.drop(columns="config_hash").to_dict("records")})
    print(len(entries), "atlas entries")
    print(tbd.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
