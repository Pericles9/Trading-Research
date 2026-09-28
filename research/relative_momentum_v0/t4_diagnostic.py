"""
v0-T4: the diagnostic panel. Gates nothing.

1. Collinearity: Spearman between the attention score and move_at at each candidate moment.
   This is the question the old brief reserved for a separate task, answered in the same pass.

2. Two things that fall out of having built move_at and that the report needs in order not to
   overstate what the evaluation covers:

   a. The gate's own intraday_pct_at_entry against the tick-derived move_at. The gate resolves
      its previous close from a three-source chain (DuckDB daily_bars, a daily parquet, or the
      last trade of the prior event-day folder -- scanner-epg-momentum/backtest/scripts/
      build_scanner_hit_catalog.py). Only the third of those is tick-derived. If the two
      measures disagree materially, the gate's own 30% entry condition is not the same
      condition D4 would write.

   b. Candidate density against D1 density over the SAME dates. The concurrency distribution
      T2 measures is a property of a 6.3%-of-D1 population, not of the universe, and that
      bounds how far the gate-2 result can be read.

A12: move_at is a cross-session ratio, so flag_cross_session_extreme is carried and the
headline correlation is reported with and without the flagged set, untrimmed first.

Usage: .venv/Scripts/python.exe research/relative_momentum_v0/t4_diagnostic.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v0 import common as C  # noqa: E402

IN = f"{C.ART}/t3_evaluated.parquet"
OUT_JSON = f"{C.ART}/t4_diagnostic.json"
OUT_PARQUET = f"{C.ART}/t4_diagnostic.parquet"


def spear(a: np.ndarray, b: np.ndarray) -> dict:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return {"n": int(m.sum()), "rho": None, "p": None}
    r = stats.spearmanr(a[m], b[m])
    return {"n": int(m.sum()), "rho": round(float(r.statistic), 4),
            "p": float(r.pvalue)}


def main() -> int:
    d = pd.read_parquet(C.REPO / IN)

    xs_path = C.REPO / C.XS_FLAGS
    if xs_path.exists():
        xs = pd.read_parquet(xs_path)
        cols = {c.lower(): c for c in xs.columns}
        tcol, dcol = cols.get("ticker"), cols.get("event_date_canonical")
        fcol = cols.get("flag_cross_session_extreme")
        if tcol and dcol and fcol:
            xs = xs.copy()
            xs[dcol] = xs[dcol].astype(str).str.slice(0, 10)
            g = xs.groupby([tcol, dcol])[fcol].max().reset_index()
            g["key"] = g[tcol] + "|" + g[dcol]
            d = d.merge(g[["key", fcol]].rename(
                columns={fcol: "flag_cross_session_extreme"}), on="key", how="left")
    if "flag_cross_session_extreme" not in d.columns:
        d["flag_cross_session_extreme"] = pd.NA
    d["xs_flag"] = d["flag_cross_session_extreme"].fillna(False).astype(bool)

    s = d[d["score_available"] & d["move_at"].notna()].copy()
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    score = s["score"].to_numpy(dtype=float)
    move = s["move_at"].to_numpy(dtype=float)

    collin = {
        "all_candidate_moments": spear(score, move),
        "flag_clear": spear(score[~s["xs_flag"].to_numpy()], move[~s["xs_flag"].to_numpy()]),
        "FLAGGED": spear(score[s["xs_flag"].to_numpy()], move[s["xs_flag"].to_numpy()]),
        "by_session_bucket": {
            str(k): spear(g["score"].to_numpy(dtype=float), g["move_at"].to_numpy(dtype=float))
            for k, g in s.groupby("session_bucket")},
        "contested_moments_only": spear(
            s.loc[s["n_live_at_tau"] >= 2, "score"].to_numpy(dtype=float),
            s.loc[s["n_live_at_tau"] >= 2, "move_at"].to_numpy(dtype=float)),
        "reading": "rho is the diagnostic, not a verdict. It says how much the attention score "
                   "restates the move rather than adding to it.",
    }

    # score decile -> move_at, so the relationship is a distribution not just a coefficient
    s["score_decile"] = pd.qcut(s["score"], 10, labels=False, duplicates="drop")
    by_dec = []
    for k, g in s.groupby("score_decile"):
        by_dec.append({
            "score_decile": int(k), "n": int(len(g)),
            "score_median": round(float(g["score"].median()), 4),
            "move_at_p25": round(float(g["move_at"].quantile(.25)), 4),
            "move_at_median": round(float(g["move_at"].median()), 4),
            "move_at_p75": round(float(g["move_at"].quantile(.75)), 4),
            "gross_bp_median": round(float(g["natural_exit_pnl_pct"].median() * 100), 1),
            "gross_bp_mean": round(float(g["natural_exit_pnl_pct"].mean() * 100), 1),
        })

    # (a) the gate's own move measure against the tick-derived one
    gate_move = s["intraday_pct_at_entry"].to_numpy(dtype=float)
    diff = move - gate_move
    gate_vs_tick = {
        "spearman": spear(gate_move, move),
        "difference_quantiles": {f"p{int(q * 100)}": round(float(np.nanquantile(diff, q)), 4)
                                 for q in (.01, .05, .25, .5, .75, .95, .99)},
        "share_gate_ge_30pct": round(float((gate_move >= 0.30).mean()), 4),
        "share_tick_move_ge_30pct": round(float((move >= 0.30).mean()), 4),
        "reading": "the gate's entry condition is gap >= 30% on ITS previous close. Where the "
                   "two disagree, the gate's 30% is not the 30% a tick-derived measure would "
                   "have applied. Only one of the gate's three prev-close sources is "
                   "tick-derived.",
    }

    # (b) how far the concurrency result can be read
    d1 = C.load_d1()
    lo, hi = d["date"].min(), d["date"].max()
    d1w = d1[(d1["event_date_canonical"] >= lo) & (d1["event_date_canonical"] <= hi)]
    n_dates_cand = int(d["date"].nunique())
    n_dates_d1 = int(d1w["event_date_canonical"].nunique())
    density = {
        "date_range": {"min": lo, "max": hi},
        "candidates": {"n": int(len(d)), "n_session_dates": n_dates_cand,
                       "per_date": round(len(d) / n_dates_cand, 2)},
        "D1_same_dates": {"n": int(len(d1w)), "n_session_dates": n_dates_d1,
                          "per_date": round(len(d1w) / n_dates_d1, 2)},
        "density_ratio": round((len(d1w) / n_dates_d1) / (len(d) / n_dates_cand), 2),
        "reading": "if the gate ran on every D1 event over these same dates rather than on the "
                   "mom >= 50 slice it was run on, per-date candidate density would rise by "
                   "about this ratio. The concurrency distribution in T2 is therefore a "
                   "LOWER BOUND on what a full-D1 deployment would see, and gate 2's near "
                   "inertness here is a property of this population, not a measured property "
                   "of the universe.",
    }

    summary = {
        "task": "v0-T4 diagnostic panel (gates nothing)",
        "config_hash": C.cfg_hash(),
        "collinearity_score_vs_move_at": collin,
        "score_decile_panel": by_dec,
        "gate_move_vs_tick_move": gate_vs_tick,
        "candidate_density_vs_D1": density,
        "a12": "move_at is a cross-session ratio; the correlation is reported untrimmed first "
               "and split on flag_cross_session_extreme, flagged rows never dropped.",
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "score_decile_panel"},
                     indent=2, default=str))
    print("\nSCORE DECILE PANEL")
    print(pd.DataFrame(by_dec).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
