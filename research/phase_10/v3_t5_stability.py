"""
Phase 10 v3 T5 -- stability and all pre-registered failure rows.

  T5a  observable agreement (print rate vs volume rate), per event
  T5b  tie-variant agreement, per the v2 tie handling
  T5c  segment-conditioned reporting of every T3 quantity
  T5d  every failure row, observed vs threshold, pass/fail, nothing further

Standing lesson carried from v1 and recorded in D8: a pass on stability rows is
not evidence of correctness. Rows exist to DISQUALIFY, never to endorse.

Usage: .venv/Scripts/python.exe research/phase_10/v3_t5_stability.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t5_sensitivity import interval_jaccard  # noqa: E402
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, collapse_ties, knn_rate, load_frozen_cohort, quantiles,
    read_event_trades, rel, session_window, write_json,
)
from v3_t1_gate import cfg_hash, load_cfg  # noqa: E402
from v3_t2_t4_subbursts import resolve  # noqa: E402

OUT = "v3_t5_stability.json"
OBS = ("print_rate", "volume_rate")


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    fc = cfg["failure_criteria"]
    exc = cfg["excursion"]
    k_fast = cfg["envelope"]["fast_k"]
    floor_s = 1e-09

    ev = pd.read_parquet(os.path.join(art, "v3_t3_event_metrics.parquet"))
    sub = pd.read_parquet(os.path.join(art, "v3_t3_subbursts.parquet"))
    for d in (ev, sub):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    ev["ok"] = ev["ok"].fillna(False).astype(bool)
    pooled = ev[ev["cohort_group"].isin(POOLED) & ev["ok"]]
    psub = sub[sub["cohort_group"].isin(POOLED)]

    # ---------------------------------------------------------- T5a observables
    a = pooled[pooled["observable"] == "print_rate"].set_index(COHORT_KEY)["n_subbursts"]
    b = pooled[pooled["observable"] == "volume_rate"].set_index(COHORT_KEY)["n_subbursts"]
    j = pd.concat([a.rename("p"), b.rename("v")], axis=1).dropna()
    sp = sps.spearmanr(j["p"], j["v"]) if len(j) > 2 else None
    t5a = {"n_events": int(len(j)),
           "spearman_subburst_count": float(sp.statistic) if sp else None,
           "spearman_pvalue": float(sp.pvalue) if sp else None,
           "count_ratio_volume_over_print": quantiles(j["v"] / j["p"].replace(0, np.nan))}

    # ---------------------------------------------------------- T5b tie variants
    cohort = load_frozen_cohort({"paths": {"cohort_manifest": cfg["paths"]["cohort_manifest"]},
                                 "cohort": {"content_hash": cfg["cohort"]["content_hash"]}})
    keys = set(map(tuple, pooled[COHORT_KEY].drop_duplicates().to_numpy()))
    tie_j = {o: [] for o in OBS}
    tie_cnt = {o: [] for o in OBS}
    meta = pooled.set_index(COHORT_KEY + ["observable"])
    for r in cohort.itertuples(index=False):
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        if key not in keys:
            continue
        w = session_window(r.event_date_canonical, 0)
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts = t0["sip_timestamp"].to_numpy()
        sz = t0["size"].to_numpy(dtype=float)
        cts, csz, _ = collapse_ties(ts, sz)
        sess = w["span_minutes"] * 60.0
        for obs in OBS:
            if (key + (obs,)) not in meta.index:
                continue
            m = meta.loc[key + (obs,)]
            if isinstance(m, pd.DataFrame):
                m = m.iloc[0]
            knee = float(m["knee_seconds"])
            got = []
            for tv, sv in ((ts, sz), (cts, csz)):
                ke = int(np.clip(round(sv.size / max(sess, 1.0) * knee), 5, max(5, sv.size - 1)))
                if sv.size <= ke or sv.size <= k_fast:
                    got.append(None); continue
                f = knn_rate(tv, sv, k_fast, floor_s)[obs]
                e = knn_rate(tv, sv, ke, floor_s)[obs]
                got.append(resolve(tv, f / np.maximum(e, 1e-30), knee, exc))
            if got[0] is None or got[1] is None:
                continue
            A = (np.array([[s["start_ns"] / 1e9, s["end_ns"] / 1e9] for s in got[0]])
                 if got[0] else np.zeros((0, 2)))
            B = (np.array([[s["start_ns"] / 1e9, s["end_ns"] / 1e9] for s in got[1]])
                 if got[1] else np.zeros((0, 2)))
            tie_j[obs].append(interval_jaccard(A, B)[0])
            tie_cnt[obs].append((len(got[0]), len(got[1])))
    t5b = {obs: {"n_events": len(tie_j[obs]), "jaccard": quantiles(tie_j[obs]),
                 "n_count_identical": int(sum(x == y for x, y in tie_cnt[obs]))}
           for obs in OBS}

    # ---------------------------------------------------------- T5c segment tables
    def block(sub_ev, sub_sb):
        return {
            "n_events": int(len(sub_ev)),
            "n_subbursts": int(len(sub_sb)),
            "subburst_count": quantiles(sub_ev["n_subbursts"]),
            "duration_seconds": quantiles(sub_sb["duration_seconds"]),
            "spacing_seconds": quantiles(sub_sb["spacing_seconds"]),
            "move_share": quantiles(sub_sb["move_share"]),
            "n_move_share_undefined": int(sub_sb["move_share"].isna().sum()),
            "n_events_session_move_undefined": int((~sub_ev["session_move_defined"].fillna(False)).sum()),
            "share_session_prints_in_subbursts": quantiles(sub_ev["share_session_prints_in_subbursts"]),
            "share_session_seconds_in_subbursts": quantiles(sub_ev["share_session_seconds_in_subbursts"]),
            "seconds_from_detection": quantiles(sub_sb["seconds_from_detection"]),
            "seconds_from_peak": quantiles(sub_sb["seconds_from_peak"]),
            "move_share_by_rank": {
                f"rank_{k}": quantiles(
                    sub_sb.assign(ab=sub_sb["subburst_move"].abs())
                    .sort_values("ab", ascending=False).groupby(COHORT_KEY).nth(k - 1)["move_share"])
                for k in (1, 2, 3)},
        }

    t5c = {}
    for obs in OBS:
        e_o = pooled[pooled["observable"] == obs]
        s_o = psub[psub["observable"] == obs]
        t5c[obs] = {"pooled": block(e_o, s_o),
                    "by_segment": {str(g): block(gg, s_o[s_o["segment"] == g])
                                   for g, gg in e_o.groupby("segment")}}
        for grp in ("row_cap_census", "dev_v4_sidecar"):
            ge = ev[(ev["cohort_group"] == grp) & (ev["observable"] == obs) & ev["ok"]]
            gs = sub[(sub["cohort_group"] == grp) & (sub["observable"] == obs)]
            if len(ge):
                t5c[obs][grp] = block(ge, gs)

    # ---------------------------------------------------------- T5d failure rows
    t24 = json.load(open(os.path.join(art, "v3_t2_t4_summary.json"), encoding="utf-8"))
    gate = json.load(open(os.path.join(art, "v3_t1_gate.json"), encoding="utf-8"))
    rows = []
    for r in t24["failure_row_1"]["rows"]:
        rows.append({**r, "observed": {"spearman_vs_print_count": r["spearman_vs_print_count"],
                                       "loglog_slope": r["loglog_slope"]},
                     "threshold": f'spearman <= {r["threshold_max_spearman"]} and '
                                  f'slope <= {r["threshold_max_slope"]}'})

    sp2 = t5a["spearman_subburst_count"]
    rows.append({"row": 2, "observable": "print vs volume", "observed": sp2,
                 "threshold": f">= {fc['row_2']['threshold_min_spearman']}",
                 "pass": bool(sp2 is not None and sp2 >= fc["row_2"]["threshold_min_spearman"]),
                 "detail": {"n": t5a["n_events"]}})

    for obs in OBS:
        v = t24["t2b_knee_interval_sensitivity"][obs]["jaccard"]["q50"]
        rows.append({"row": 3, "observable": obs, "observed": v,
                     "threshold": f">= {fc['row_3']['threshold_min_jaccard']}",
                     "pass": bool(v is not None and v >= fc["row_3"]["threshold_min_jaccard"]),
                     "detail": {"n": t24["t2b_knee_interval_sensitivity"][obs]["jaccard"]["n"],
                                "note": "evaluated INSIDE the T1 knee bootstrap interval only"}})

    for obs in OBS:
        e_o = pooled[pooled["observable"] == obs]
        s_o = psub[psub["observable"] == obs]
        degen = float(((e_o["n_subbursts"] == 1)
                       & (e_o["largest_subburst_span_share"] >= 0.5)).mean()) if len(e_o) else None
        med_dur = float(s_o["duration_seconds"].median()) if len(s_o) else None
        floor = exc["min_duration_fraction_of_knee"] * e_o["knee_seconds"].median()
        mult = (med_dur / floor) if (med_dur and floor) else None
        rows.append({"row": 4, "observable": obs,
                     "observed": {"degenerate_share": degen, "median_duration_over_floor": mult,
                                  "median_duration_s": med_dur, "floor_s": floor},
                     "threshold": f"share <= {fc['row_4']['threshold_max_share']} and "
                                  f"duration/floor > {fc['row_4']['threshold_min_duration_multiple']}",
                     "pass": bool(degen is not None and mult is not None
                                  and degen <= fc["row_4"]["threshold_max_share"]
                                  and mult > fc["row_4"]["threshold_min_duration_multiple"])})

    for r in gate["row_5_segment_compatibility"]["rows"]:
        rows.append({"row": 5, "observable": r["observable"],
                     "observed": r["separation_decades"],
                     "threshold": f"<= {fc['row_5']['threshold_max_decades']} decades or "
                                  f"overlapping intervals",
                     "pass": r["pass"],
                     "detail": {"intervals_overlap": r["intervals_overlap"]}})
    for r in gate["gate_row_6"]["rows"]:
        rows.append({"row": 6, "observable": f"{r['observable']}/{r['segment']}",
                     "observed": {"delta_bic": r["delta_bic"], "slope_change": r["slope_change"],
                                  "knee_seconds": r["knee_seconds"]},
                     "threshold": f"dBIC >= {fc['row_6']['threshold_min_delta_bic']} and "
                                  f"|slope change| >= {fc['row_6']['threshold_min_slope_change']}",
                     "pass": r["pass"]})
    for r in gate["gate_row_7"]["rows"]:
        rows.append({"row": 7, "observable": f"{r['observable']}/{r['segment']}",
                     "observed": r["iqr_decades"],
                     "threshold": f"<= {fc['row_7']['threshold_max_iqr_decades']} decades",
                     "pass": r["pass"], "detail": {"n": r["n_events"]}})

    any_fail = any(r["pass"] is False for r in rows)
    summary = {
        "phase": "10", "version": "v3", "task": "T5", "config_hash": chash,
        "population": "pooled analysis cohort n=100; row_cap_census and dev_v4_sidecar carried, "
                      "labeled, never pooled",
        "t5a_observable_agreement": t5a,
        "t5b_tie_variant_agreement": t5b,
        "t5c_segment_conditioned": t5c,
        "t5d_failure_criteria": {
            "row_0": {"mode": fc["row_0"]["mode"], "observed": None, "pass": None,
                      "note": fc["row_0"]["note"]},
            "rows": rows, "any_failed": bool(any_fail)},
        "standing_lesson": fc["standing_lesson"],
        "source": "research/phase_10/v3_t5_stability.py:main",
    }
    write_json(os.path.join(art, OUT), summary)

    print(f"T5a observable Spearman on sub-burst count: {sp2:.4f} (n={t5a['n_events']})")
    for obs in OBS:
        print(f"T5b tie-variant Jaccard {obs}: median "
              f"{t5b[obs]['jaccard']['q50']:.4f} (n={t5b[obs]['n_events']}, "
              f"{t5b[obs]['n_count_identical']} identical counts)")
    print("\n=== T5d ALL FAILURE ROWS ===")
    for r in rows:
        o = r["observed"]
        os_ = f"{o:+.4f}" if isinstance(o, float) else (
            json.dumps({k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in o.items()}) if isinstance(o, dict) else str(o))
        print(f"  row {r['row']} {str(r['observable'])[:24]:26s} {os_[:78]:78s} "
              f"-> {'PASS' if r['pass'] else 'FAIL'}")
    print(f"\n  ANY FAILED: {any_fail}")
    return 0 if not any_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
