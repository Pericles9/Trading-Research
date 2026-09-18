"""
v1-T4: the diagnostic panel, plus Fix 4 -- the price-level effect separated from the gate effect.

1. Collinearity: Spearman(score, move_at) at candidate moments. Carried from v0 unchanged,
   gating nothing. A12 split reported (move_at is a cross-session ratio).

2. Fix 4: net markout by DETECTION-PRICE decile, independent of the gate policy table. Phase 11
   established net edge as a function of detection-price level, so a price-driven effect must be
   separable from a gate effect. Two things are reported:
     - net markout by detection-price decile, all candidates, no policy applied
     - the detection-price composition of each policy, so it is visible whether the gate simply
       re-sorted the population onto a different part of the price axis

   Detection price is reused from E1's artifact (F1-T6's D4-compliant tick-derived construction),
   never re-derived.

3. The score decile panel, carried from v0, because it is where the mechanism shows.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/t4_diagnostic.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import common as C  # noqa: E402

IN = f"{C.ART}/t3_evaluated.parquet"
OUT_JSON = f"{C.ART}/t4_diagnostic.json"
OUT_PARQUET = f"{C.ART}/t4_diagnostic.parquet"
FLOOR = 20


def spear(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return {"n": int(m.sum()), "rho": None}
    r = stats.spearmanr(a[m], b[m])
    return {"n": int(m.sum()), "rho": round(float(r.statistic), 4), "p": float(r.pvalue)}


def cell(g: pd.DataFrame, cost_bp: float) -> dict:
    gross = g["gross_pnl_pct"].to_numpy(float) * 100
    net = gross - cost_bp
    ps = g["net_bp_per_share"].to_numpy(float)
    if len(g) < FLOOR:
        return {"n": int(len(g)), "below_display_floor": True}
    return {
        "n": int(len(g)),
        "detection_price_median": round(float(g["detection_price"].median()), 3),
        "gross_bp_median": round(float(np.median(gross)), 1),
        "gross_bp_mean": round(float(gross.mean()), 1),
        "net_bp_median_flat": round(float(np.median(net)), 1),
        "net_bp_median_per_share": round(float(np.nanmedian(ps)), 1),
        "win_rate_gross": round(float((gross > 0).mean()), 4),
    }


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["evaluation"]["cost"]["round_trip_bp"]

    d = pd.read_parquet(C.REPO / IN)
    dp = pd.read_parquet(C.REPO / C.DETECTION_PRICE)
    d = d.merge(dp, on="event_id", how="left")

    # A12 flag
    xs_path = C.REPO / C.XS_FLAGS
    if xs_path.exists():
        xs = pd.read_parquet(xs_path)
        cl = {c.lower(): c for c in xs.columns}
        t, dt_, f = cl.get("ticker"), cl.get("event_date_canonical"), \
            cl.get("flag_cross_session_extreme")
        if t and dt_ and f:
            xs = xs.copy()
            xs[dt_] = xs[dt_].astype(str).str.slice(0, 10)
            g = xs.groupby([t, dt_])[f].max().reset_index()
            g["key"] = g[t] + "|" + g[dt_]
            d = d.merge(g[["key", f]].rename(columns={f: "xs"}), on="key", how="left")
    d["xs_flag"] = d["xs"].fillna(False).astype(bool) if "xs" in d.columns else False
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    post = d[~d["gate1_warmup"]]

    collin = {
        "all_candidate_moments": spear(d["score"], d["move_at_entry"]),
        "post_warmup": spear(post["score"], post["move_at_entry"]),
        "flag_clear": spear(d.loc[~d["xs_flag"], "score"],
                            d.loc[~d["xs_flag"], "move_at_entry"]),
        "FLAGGED": spear(d.loc[d["xs_flag"], "score"], d.loc[d["xs_flag"], "move_at_entry"]),
        "contested_only": spear(d.loc[d["n_live_at_tau"] >= 2, "score"],
                                d.loc[d["n_live_at_tau"] >= 2, "move_at_entry"]),
        "v0_reference_rho": 0.6915,
        "reading": "rho is the diagnostic, not the verdict. On the gap-gated population move_at "
                   "is compressed by construction (every entry is at or near +30%), which "
                   "mechanically reduces the correlation -- so a lower rho here is NOT evidence "
                   "the score became more independent.",
    }

    # ---- Fix 4: the price axis, with no policy applied --------------------
    by_price = []
    for k, g in d.groupby("detection_price_decile"):
        by_price.append({"detection_price_decile": int(k), **cell(g, cost_bp)})

    # the same axis, post-warmup only
    by_price_post = []
    for k, g in post.groupby("detection_price_decile"):
        by_price_post.append({"detection_price_decile": int(k), **cell(g, cost_bp)})

    # did the gate just re-sort the population along the price axis?
    comp = {}
    for label, sub in [("A all", d), ("A post-warmup", post),
                       ("B post-warmup", post[post["policy_b"]]),
                       ("B1 post-warmup", post[post["gate1_level"]])]:
        comp[label] = {
            "n": int(len(sub)),
            "detection_price_median": round(float(sub["detection_price"].median()), 3),
            "detection_price_decile_median": float(sub["detection_price_decile"].median()),
            "decile_share": {str(int(k)): round(float(v), 4) for k, v in
                             sub["detection_price_decile"].value_counts(normalize=True)
                             .sort_index().items()},
        }

    # ---- the score decile panel, carried from v0 -------------------------
    sd = d.copy()
    sd["score_decile"] = pd.qcut(sd["score"], 10, labels=False, duplicates="drop")
    by_score = []
    for k, g in sd.groupby("score_decile"):
        gross = g["gross_pnl_pct"].to_numpy(float) * 100
        by_score.append({
            "score_decile": int(k), "n": int(len(g)),
            "score_median": round(float(g["score"].median()), 3),
            "move_at_median": round(float(g["move_at_entry"].median()), 4),
            "detection_price_median": round(float(g["detection_price"].median()), 3),
            "gross_bp_median": round(float(np.median(gross)), 1),
            "gross_bp_mean": round(float(gross.mean()), 1),
            "net_bp_median_flat": round(float(np.median(gross - cost_bp)), 1),
        })

    summary = {
        "task": "v1-T4 diagnostic panel and Fix 4 (price level separated from gate effect)",
        "config_hash": C.cfg_hash(),
        "collinearity_score_vs_move_at": collin,
        "fix4_net_markout_by_detection_price_decile": by_price,
        "fix4_post_warmup": by_price_post,
        "fix4_policy_price_composition": comp,
        "fix4_reading": "if the gate's damage were purely a price-level effect, the policies "
                        "would differ from the baseline mainly by sitting on a different part of "
                        "the price axis. The composition block is what shows whether they do.",
        "score_decile_panel": by_score,
        "display_floor": FLOOR,
        "a12": "move_at is a cross-session ratio; the correlation is reported untrimmed first "
               "and split on flag_cross_session_extreme, flagged rows never dropped.",
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("fix4_net_markout_by_detection_price_decile",
                                   "fix4_post_warmup", "score_decile_panel")},
                     indent=2, default=str))
    print("\nFIX 4 — net markout by detection-price decile (no policy applied)")
    print(pd.DataFrame(by_price).to_string(index=False))
    print("\nFIX 4 — same, post-warmup only")
    print(pd.DataFrame(by_price_post).to_string(index=False))
    print("\nSCORE DECILE PANEL")
    print(pd.DataFrame(by_score).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
