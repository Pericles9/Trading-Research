"""
Brief 2, T4 -- step zero: the unconditional excursion vector, all of D1 with tau and a vector.

The first read of the outcome, and the only one in this brief. No attention, catalyst or
cross-sectional quantity is read here: the only inputs are T1's excursion rows, T0's facet table and
the no-drift reference (T4a) -- no T2 or T3 artifact is opened.

For each rung N separately (nothing is pooled across rungs), overall and by every level of each facet --
slice, year, tau_anchor_segment, price_tier (R4), tau_close_sensitive, flag_cross_session_extreme,
jump_share band (R4, from the rung's own jump_share) and edge class (each class its own row, plus
none_of_these):
  u_peak    counts in absolute 0.05 bins with the simulated free walk's share in the same bins
  rise_s, fall_s, dip_before_peak_s, terminal_s   n, quantiles, mean, and the reference's
  cost      share with rise_bp > 70.98 bp and with rise_cents > 2.512 cents (Brief 1 cost_reference)
Gallery: 72 events, seeded, stratified by year x segment (config brief2.t4_step_zero.gallery); their
bucketed paths are rebuilt with Brief 1's excursion_vector and checked against T1's components.

Writes artifacts/t4_facets.parquet, t4_u_peak_bins.parquet, t4_cost.parquet, t4_gallery.parquet,
t4_gallery_buckets.parquet, t4_step_zero.json.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/t4_step_zero.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402
import t1_excursion as T1  # noqa: E402

COMPS = ["rise_s", "fall_s", "dip_before_peak_s", "terminal_s"]
EDGES = ["rise_censored", "no_rise", "peak_tied", "halt_in_path", "thin_path"]
BINS = np.linspace(0.0, 1.0, 21)


def u_bins(u: np.ndarray) -> np.ndarray:
    """Counts in [0, .05), [.05, .10), ..., [.95, 1.0] (the last bin closed)."""
    return np.histogram(np.asarray(u, dtype=float), bins=BINS)[0]


def facet_frames(df: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame]]:
    out = [("all", "all", df)]
    for f in ["slice", "year", "tau_anchor_segment", "price_tier", "tau_close_sensitive", "flag_cross_session_extreme", "jump_share_band"]:
        col = df[f].astype("string").fillna("missing")
        for lev in sorted(col.unique()):
            out.append((f, str(lev), df[col == lev]))
    for e in EDGES:
        out.append(("edge_class", e, df[df[e].fillna(False).astype(bool)]))
    none = ~np.any(np.column_stack([df[e].fillna(False).astype(bool).to_numpy() for e in EDGES]), axis=1)
    out.append(("edge_class", "none_of_these", df[none]))
    return out


def main() -> int:
    cfg = B.load_cfg()
    s4 = cfg["brief2"]["t4_step_zero"]
    cost = cfg["cost_reference"]
    ex = pd.read_parquet(B.art("t1_excursion.parquet"))
    pop = pd.read_parquet(B.art("t0_population.parquet"))
    ref = pd.read_parquet(B.art("t4a_reference_free_walk.parquet"))
    va = ex[ex["vector_available"] == True].copy()  # noqa: E712
    va = va.drop(columns=[c for c in ("slice", "tau_anchor_segment", "price_tier", "tau_ns") if c in va])
    fac = pop[["event_id", "tau_ns", "slice", "year", "tau_anchor_segment", "price_tier"]]
    va = va.merge(fac, on="event_id", how="left", suffixes=("_t1", ""))
    va["year"] = va["year"].astype(int)
    va["jump_share_band"] = B.jump_band(va["jump_share"].to_numpy(), cfg)
    assert va["slice"].notna().all() and va["price_tier"].notna().all()
    B.assert_int64(va)
    n_tau = int(pop["tau_available"].sum())

    frows, urows, crows = [], [], []
    for N in cfg["t4_excursion"]["bucket_ladder"]:
        rN = ref[ref["N"] == N]
        ref_u = u_bins(rN["u_peak"]) / len(rN)
        ref_q = {c: {"median": float(rN[c].median()), "mean": float(rN[c].mean()), "p25": float(rN[c].quantile(.25)),
                     "p75": float(rN[c].quantile(.75))} for c in COMPS + ["u_peak"]}
        dN = va[va["N"] == N]
        for facet, lev, g in facet_frames(dN):
            n = int(len(g))
            row = {"N": int(N), "facet": facet, "level": lev, "n": n, "events": int(g["event_id"].nunique())}
            if n:
                cnt = u_bins(g["u_peak"])
                for b in range(20):
                    urows.append({"N": int(N), "facet": facet, "level": lev, "bin_lo": BINS[b], "bin_hi": BINS[b + 1],
                                  "count": int(cnt[b]), "share": cnt[b] / n, "reference_share": float(ref_u[b])})
                u = g["u_peak"].astype(float)
                row.update({"u_peak_median": float(u.median()), "u_peak_mean": float(u.mean()),
                            "u_peak_share_le_0.05": float((u < 0.05).mean()), "u_peak_share_ge_0.95": float((u >= 0.95).mean()),
                            "u_peak_share_interior_0.1_0.9": float(((u >= 0.1) & (u < 0.9)).mean()),
                            "ref_u_peak_median": ref_q["u_peak"]["median"],
                            "ref_u_peak_share_interior_0.1_0.9": float(ref_u[2:18].sum())})
                for c in COMPS:
                    v = g[c].astype(float).dropna()
                    row.update({f"{c}_n": int(v.size), f"{c}_median": float(v.median()) if v.size else None,
                                f"{c}_p25": float(v.quantile(.25)) if v.size else None, f"{c}_p75": float(v.quantile(.75)) if v.size else None,
                                f"{c}_mean": float(v.mean()) if v.size else None,
                                f"ref_{c}_median": ref_q[c]["median"], f"ref_{c}_mean": ref_q[c]["mean"]})
                row.update({"rise_bp_median": float(g["rise_bp"].median()), "rise_cents_median": float(g["rise_cents"].median()),
                            "share_rise_bp_gt_rt": float((g["rise_bp"] > cost["rt_bp"]).mean()),
                            "share_rise_cents_gt_rt": float((g["rise_cents"] > cost["rt_cents"]).mean())})
            frows.append(row)
            if facet in ("all", "price_tier", "edge_class"):
                crows.append({"N": int(N), "facet": facet, "level": lev, "n": n,
                              "n_rise_bp_gt_rt": int((g["rise_bp"] > cost["rt_bp"]).sum()),
                              "n_rise_cents_gt_rt": int((g["rise_cents"] > cost["rt_cents"]).sum()),
                              "share_rise_bp_gt_rt": float((g["rise_bp"] > cost["rt_bp"]).mean()) if n else None,
                              "share_rise_cents_gt_rt": float((g["rise_cents"] > cost["rt_cents"]).mean()) if n else None,
                              "share_both": float(((g["rise_bp"] > cost["rt_bp"]) & (g["rise_cents"] > cost["rt_cents"])).mean()) if n else None})
    fr, ur, cr = pd.DataFrame(frows), pd.DataFrame(urows), pd.DataFrame(crows)
    for df, name in [(fr, "t4_facets"), (ur, "t4_u_peak_bins"), (cr, "t4_cost")]:
        df["config_hash"] = B.cfg_hash()
        df.to_parquet(B.art(f"{name}.parquet"), index=False)

    # ------------------------------------------------ gallery (72, seeded, year x segment)
    gcfg = s4["gallery"]
    full = va.groupby("event_id")["N"].nunique()
    elig = va[va["event_id"].isin(full[full == 3].index)].drop_duplicates("event_id")[["event_id", "year", "tau_anchor_segment"]]
    strata = elig.groupby(["year", "tau_anchor_segment"]).size().sort_index()
    k = len(strata)
    rest = gcfg["n"] - k
    assert rest >= 0, "more strata than gallery slots"
    quota = strata / strata.sum() * rest
    alloc = np.floor(quota).astype(int)
    left = rest - int(alloc.sum())
    for idx in (quota - alloc).sort_values(ascending=False, kind="stable").index[:left]:
        alloc[idx] += 1
    alloc = (alloc + 1).clip(upper=strata)
    rng = np.random.default_rng(gcfg["seed"])
    picks = []
    for (y, sg), a in alloc.items():
        pool = sorted(elig[(elig["year"] == y) & (elig["tau_anchor_segment"] == sg)]["event_id"])
        for e in rng.choice(pool, size=int(a), replace=False):
            picks.append({"event_id": str(e), "year": int(y), "tau_anchor_segment": sg, "stratum_size": int(strata[(y, sg)])})
    gal = pd.DataFrame(picks)
    gal["config_hash"] = B.cfg_hash()
    gal.to_parquet(B.art("t4_gallery.parquet"), index=False)
    tp = pop.set_index("event_id")
    bks, worst = [], 0.0
    for e in gal["event_id"]:
        r = tp.loc[e]
        ts, px, sz = T1.path_arrays(e, int(r["tau_ns"]), r["event_date_canonical"])
        for N in cfg["t4_excursion"]["bucket_ladder"]:
            v = B.I.excursion_vector(int(r["tau_ns"]), float(r["tau_price"]), ts, px, sz, N)
            row = va[(va["event_id"] == e) & (va["N"] == N)].iloc[0]
            worst = max(worst, max(abs(float(v[c]) - float(row[c])) for c in ["u_peak"] + COMPS))
            bks.append(pd.DataFrame({"event_id": e, "N": N, "i": np.arange(1, N + 1), "u": np.arange(1, N + 1) / N,
                                     "vwap": v["_bucket_price"], "t_end_ns": v["_bucket_t_end"]}))
    assert worst == 0.0, f"gallery rebuild differs from T1 by {worst}"
    bk = pd.concat(bks, ignore_index=True)
    bk["config_hash"] = B.cfg_hash()
    bk.to_parquet(B.art("t4_gallery_buckets.parquet"), index=False)

    allr = fr[fr["facet"] == "all"].set_index("N")
    tiers = cr[cr["facet"] == "price_tier"]
    B.write_json("t4_step_zero.json", {
        "config_hash": B.cfg_hash(), "events_with_tau": n_tau,
        "events_with_vector_by_N": {int(N): int(allr.loc[N, "n"]) for N in allr.index},
        "reads_no_attention": "inputs: t1_excursion, t0_population, t4a_reference_free_walk only",
        "headline_by_N": {int(N): {"n": int(allr.loc[N, "n"]), "u_peak_median": allr.loc[N, "u_peak_median"],
                                   "ref_u_peak_median": allr.loc[N, "ref_u_peak_median"],
                                   "u_peak_share_interior_0.1_0.9": allr.loc[N, "u_peak_share_interior_0.1_0.9"],
                                   "ref_u_peak_share_interior_0.1_0.9": allr.loc[N, "ref_u_peak_share_interior_0.1_0.9"],
                                   "u_peak_share_le_0.05": allr.loc[N, "u_peak_share_le_0.05"],
                                   "u_peak_share_ge_0.95": allr.loc[N, "u_peak_share_ge_0.95"],
                                   "rise_s_median": allr.loc[N, "rise_s_median"], "ref_rise_s_median": allr.loc[N, "ref_rise_s_median"],
                                   "rise_s_mean": allr.loc[N, "rise_s_mean"], "ref_rise_s_mean": allr.loc[N, "ref_rise_s_mean"],
                                   "fall_s_median": allr.loc[N, "fall_s_median"], "ref_fall_s_median": allr.loc[N, "ref_fall_s_median"],
                                   "share_rise_bp_gt_rt": allr.loc[N, "share_rise_bp_gt_rt"],
                                   "share_rise_cents_gt_rt": allr.loc[N, "share_rise_cents_gt_rt"]}
                         for N in allr.index},
        "cost_clearing_by_price_tier": {f"N={int(r.N)}|{r.level}": {"n": int(r.n), "share_rise_bp_gt_rt": r.share_rise_bp_gt_rt,
                                                                    "share_rise_cents_gt_rt": r.share_rise_cents_gt_rt, "share_both": r.share_both}
                                        for r in tiers.itertuples()},
        "cost_reference": cost,
        "gallery": {"n": int(len(gal)), "strata": int(k), "allocation": {f"{y}|{sg}": int(a) for (y, sg), a in alloc.items()},
                    "seed": gcfg["seed"], "rebuild_matches_t1": True},
    })
    print(allr[["n", "u_peak_median", "ref_u_peak_median", "u_peak_share_interior_0.1_0.9", "ref_u_peak_share_interior_0.1_0.9",
                "rise_s_median", "ref_rise_s_median", "share_rise_bp_gt_rt", "share_rise_cents_gt_rt"]].to_string())
    print(tiers[["N", "level", "n", "share_rise_bp_gt_rt", "share_rise_cents_gt_rt"]].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
