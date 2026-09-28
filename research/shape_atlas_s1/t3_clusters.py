"""
Shape atlas S1, T3 -- data-driven types and whether they beat noise (section 4), for one view.
Exploratory, hindsight used by design; nothing here is a tested result.

Input: the view's N = 100 bucket log paths (T1), resampled to G = 100 sigma-normalised points. The
null: null draws 0..4 of every event (the same row-stable draws as T1's), each a replicate dataset of
one draw per event, through the identical pipeline (s1common.null_pipeline).

4a  PCA of the resampled curves (uniform grid: functional PCA); spectrum real vs null; first five
    components as shapes.
4b  GMM on the first d FPC scores (d = the real view's 90% count; the null uses its own PCA with the same
    d), k = 1..8, BIC gain = BIC(1) - BIC(k); k-means on the paths, k = 2..8; silhouette (paths,
    Euclidean, 5,000 seeded) for both; ARI between the two; the same on every null replicate.
    Assignments carried for every k (labels ordered by size, 0 = largest).
4c  Across time: fit on 2020-22, assign 2023-24, fit 2023-24, match clusters (Hungarian on the
    correlation of member-mean paths), and the reverse; as written (tickers repeat) and ticker-blocked
    (tickers seen in the fit period removed from the assigned period). Across resamples: 50 ticker
    bootstrap refits; each event's co-assignment rate.
Structure label per cluster (config stability.structure_label): beats the null at its k, and matched
centroid correlation >= 0.9 in both directions.
4d  Cross-tab against the theory types (T2, N = 100).

Writes artifacts/t3_{view}_*.parquet and t3_{view}_summary.json.

Usage: .venv/Scripts/python.exe research/shape_atlas_s1/t3_clusters.py <post|whole_day|runup>
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1common as S  # noqa: E402

CFG = S.load_cfg()
CC = CFG["clustering"]
ST = CFG["stability"]
G = CFG["views"]["resample"]["G"]
SEED = CC["kmeans"]["seed"]
KS = CC["k"]
R = CC["null_replicates"]["n"]


def relabel(lab: np.ndarray, k: int) -> np.ndarray:
    counts = np.bincount(lab, minlength=k)
    order = np.argsort(-counts, kind="stable")
    m = np.empty(k, dtype=int)
    m[order] = np.arange(k)
    return m[lab]


def fit_model(X, method, k, d, n_init):
    if method == "kmeans":
        return ("kmeans", KMeans(n_clusters=k, n_init=n_init, random_state=SEED).fit(X))
    pca = PCA(n_components=d, random_state=SEED).fit(X)
    gm = GaussianMixture(n_components=k, covariance_type=CC["gmm"]["covariance"], n_init=n_init, random_state=SEED).fit(pca.transform(X))
    return ("gmm", pca, gm)


def predict(model, X):
    if model[0] == "kmeans":
        return model[1].predict(X)
    return model[2].predict(model[1].transform(X))


def member_means(X, lab, k):
    return np.vstack([X[lab == c].mean(axis=0) if (lab == c).any() else np.full(X.shape[1], np.nan) for c in range(k)])


def match(MA, MB):
    k = MA.shape[0]
    corr = np.array([[np.corrcoef(MA[i], MB[j])[0, 1] if np.isfinite(MA[i]).all() and np.isfinite(MB[j]).all() else -1.0
                      for j in range(k)] for i in range(k)])
    r, c = linear_sum_assignment(-corr)
    return c, corr[r, c]


def load_view(view: str, ev: pd.DataFrame):
    P = pd.read_parquet(S.art(f"s1_paths_{view}.parquet"))
    lp = P[[f"b{i:03d}" for i in range(101)]].to_numpy()
    c = S.comps_batch(lp)
    X = S.resample(lp, c["sigma_path"], G)
    ok = ~c["sigma_zero"] & np.isfinite(X).all(axis=1)
    meta = ev.set_index("event_id").loc[P["event_id"].to_numpy()].reset_index()
    return meta[ok].reset_index(drop=True), lp[ok], X[ok], int((~ok).sum())


def null_sets(view: str, lp: np.ndarray, eidx: np.ndarray):
    out = np.full((R, lp.shape[0], G), np.nan)
    for i in range(lp.shape[0]):
        _, _, Xn = S.null_pipeline(lp[i], S.null_index(CFG, int(eidx[i]), view, 100, R), G)
        out[:, i, :] = Xn
    return out


def main() -> int:
    view = sys.argv[1]
    t0 = time.perf_counter()
    ev = pd.read_parquet(S.art("s1_events.parquet"))
    meta, lp, X, n_dropped = load_view(view, ev)
    ids = meta["event_id"].to_numpy()
    n = len(ids)
    XN = null_sets(view, lp, meta["event_index"].to_numpy())
    print(view, n, "events;", n_dropped, "sigma-zero rows not clustered;", round(time.perf_counter() - t0), "s", flush=True)

    # ------------------------------------------------ 4a, 4b on real and every null replicate
    full = PCA(random_state=SEED).fit(X)
    d = int(np.searchsorted(np.cumsum(full.explained_variance_ratio_), 0.90) + 1)
    stats, spectrum, shapes, labels_real, probs_real = [], [], [], {}, {}
    datasets = [("real", X, np.ones(n, dtype=bool))] + [(f"null{r}", XN[r], np.isfinite(XN[r]).all(axis=1)) for r in range(R)]
    for name, D, okr in datasets:
        Dm = D[okr]
        p = PCA(random_state=SEED).fit(Dm)
        for j, v in enumerate(p.explained_variance_ratio_[:20]):
            spectrum.append({"view": view, "dataset": name, "component": j + 1, "var_share": float(v)})
        if name in ("real", "null0"):
            for j in range(5):
                for g in range(G):
                    shapes.append({"view": view, "dataset": name, "component": j + 1, "g": g, "value": float(p.components_[j, g])})
        Z = p.transform(Dm)[:, :d]
        bic1 = GaussianMixture(1, covariance_type="full", random_state=SEED).fit(Z).bic(Z)
        for k in KS:
            gm = GaussianMixture(k, covariance_type=CC["gmm"]["covariance"], n_init=CC["gmm"]["n_init"], random_state=SEED).fit(Z)
            lg = gm.predict(Z)
            km = KMeans(n_clusters=k, n_init=CC["kmeans"]["n_init"], random_state=SEED).fit(Dm)
            lk = km.labels_
            sil_g = silhouette_score(Dm, lg, sample_size=min(CC["silhouette"]["sample_size"], len(Dm)), random_state=SEED) if len(set(lg)) > 1 else np.nan
            sil_k = silhouette_score(Dm, lk, sample_size=min(CC["silhouette"]["sample_size"], len(Dm)), random_state=SEED)
            stats.append({"view": view, "dataset": name, "k": k, "d": d, "n": int(len(Dm)), "gmm_bic": float(gm.bic(Z)), "gmm_bic1": float(bic1),
                          "gmm_bic_improvement": float(bic1 - gm.bic(Z)), "gmm_silhouette": float(sil_g), "kmeans_silhouette": float(sil_k),
                          "kmeans_inertia": float(km.inertia_), "ari_gmm_kmeans": float(adjusted_rand_score(lg, lk))})
            if name == "real":
                labels_real[("gmm", k)] = relabel(lg, k)
                probs_real[("gmm", k)] = gm.predict_proba(Z).max(axis=1)
                labels_real[("kmeans", k)] = relabel(lk, k)
        print(" ", view, name, "done", round(time.perf_counter() - t0), "s", flush=True)
    st = pd.DataFrame(stats)
    real = st[st["dataset"] == "real"].set_index("k")
    nul = st[st["dataset"] != "real"].groupby("k")
    rmn = pd.DataFrame({
        "k": KS,
        "gmm_bic_improvement_real": real.loc[KS, "gmm_bic_improvement"].to_numpy(),
        "gmm_bic_improvement_null_mean": nul["gmm_bic_improvement"].mean().loc[KS].to_numpy(),
        "gmm_bic_improvement_null_max": nul["gmm_bic_improvement"].max().loc[KS].to_numpy(),
        "gmm_silhouette_real": real.loc[KS, "gmm_silhouette"].to_numpy(),
        "gmm_silhouette_null_mean": nul["gmm_silhouette"].mean().loc[KS].to_numpy(),
        "gmm_silhouette_null_max": nul["gmm_silhouette"].max().loc[KS].to_numpy(),
        "kmeans_silhouette_real": real.loc[KS, "kmeans_silhouette"].to_numpy(),
        "kmeans_silhouette_null_mean": nul["kmeans_silhouette"].mean().loc[KS].to_numpy(),
        "kmeans_silhouette_null_max": nul["kmeans_silhouette"].max().loc[KS].to_numpy(),
        "ari_real": real.loc[KS, "ari_gmm_kmeans"].to_numpy(), "ari_null_mean": nul["ari_gmm_kmeans"].mean().loc[KS].to_numpy()})
    rmn["gmm_beats_null"] = (rmn["gmm_silhouette_real"] > rmn["gmm_silhouette_null_max"]) & (rmn["gmm_bic_improvement_real"] > rmn["gmm_bic_improvement_null_max"])
    rmn["kmeans_beats_null"] = rmn["kmeans_silhouette_real"] > rmn["kmeans_silhouette_null_max"]
    rmn.insert(0, "view", view)

    asg = []
    for (method, k), lab in labels_real.items():
        asg.append(pd.DataFrame({"event_id": ids, "view": view, "method": method, "k": k, "label": lab,
                                 "gmm_max_prob": probs_real.get((method, k), np.full(n, np.nan))}))
    asg = pd.concat(asg, ignore_index=True)
    cen = []
    for (method, k), lab in labels_real.items():
        for c in range(k):
            m = lab == c
            q = np.nanpercentile(X[m], [25, 50, 75], axis=0)
            mean, nmean = X[m].mean(axis=0), np.nanmean(XN[0][m], axis=0)
            cen.append(pd.DataFrame({"view": view, "method": method, "k": k, "label": c, "n": int(m.sum()), "g": np.arange(G),
                                     "mean": mean, "p25": q[0], "median": q[1], "p75": q[2], "null_mean": nmean}))
    cen = pd.concat(cen, ignore_index=True)

    # ------------------------------------------------ 4c across time, both directions, two variants
    yr = meta["year"].to_numpy().astype(int)
    tick = meta["ticker"].to_numpy()
    A = (yr >= ST["periods"]["A"][0]) & (yr <= ST["periods"]["A"][1])
    Bm = (yr >= ST["periods"]["B"][0]) & (yr <= ST["periods"]["B"][1])
    stab, mcorr = [], {}
    for method in ("gmm", "kmeans"):
        n_init = CC["gmm"]["n_init"] if method == "gmm" else CC["kmeans"]["n_init"]
        for k in KS:
            fits = {}
            for variant in ("tickers_repeat", "ticker_blocked"):
                for direction, fit_m, other_m in (("A->B", A, Bm), ("B->A", Bm, A)):
                    if variant == "ticker_blocked":
                        other_m = other_m & ~np.isin(tick, np.unique(tick[fit_m]))
                    key_fit = ("fit", direction[0])
                    if key_fit not in fits:
                        fits[key_fit] = fit_model(X[fit_m], method, k, d, n_init)
                    mf = fits[key_fit]
                    lab_fit = predict(mf, X[fit_m])
                    mo = fit_model(X[other_m], method, k, d, n_init)
                    lab_other_fit = predict(mo, X[other_m])
                    lab_other_asg = predict(mf, X[other_m])
                    MA, MB = member_means(X[fit_m], lab_fit, k), member_means(X[other_m], lab_other_fit, k)
                    col, corr = match(MA, MB)
                    for c in range(k):
                        stab.append({"view": view, "method": method, "k": k, "variant": variant, "direction": direction, "fit_label": c,
                                     "matched_label": int(col[c]), "centroid_corr": float(corr[c]),
                                     "share_assigned": float(np.mean(lab_other_asg == c)), "share_refit_matched": float(np.mean(lab_other_fit == col[c])),
                                     "share_in_fit": float(np.mean(lab_fit == c)), "n_fit": int(fit_m.sum()), "n_other": int(other_m.sum()),
                                     "ari_assigned_vs_refit": float(adjusted_rand_score(lab_other_asg, lab_other_fit))})
        print(" ", view, method, "stability done", round(time.perf_counter() - t0), "s", flush=True)
    stab = pd.DataFrame(stab)

    # the full-data cluster ids <-> the period-A fit's ids, for the structure label: match the full fit to each period fit
    lab_rows = []
    for method in ("gmm", "kmeans"):
        for k in KS:
            full_lab = labels_real[(method, k)]
            MF = member_means(X, full_lab, k)
            s = stab[(stab["method"] == method) & (stab["k"] == k) & (stab["variant"] == "tickers_repeat")]
            beats = bool(rmn.set_index("k").loc[k, f"{method}_beats_null"])
            # rebuild the A-fit and B-fit member means from the stability rows' own fits by refitting deterministically
            fa = fit_model(X[A], method, k, d, CC["gmm"]["n_init"] if method == "gmm" else CC["kmeans"]["n_init"])
            fb = fit_model(X[Bm], method, k, d, CC["gmm"]["n_init"] if method == "gmm" else CC["kmeans"]["n_init"])
            MA = member_means(X[A], predict(fa, X[A]), k)
            MB = member_means(X[Bm], predict(fb, X[Bm]), k)
            ca, corr_a = match(MF, MA)
            cb, corr_b = match(MF, MB)
            for c in range(k):
                rep = min(corr_a[c], corr_b[c])
                lab_rows.append({"view": view, "method": method, "k": k, "label": c, "n": int((full_lab == c).sum()),
                                 "beats_null_at_k": beats, "corr_full_vs_A": float(corr_a[c]), "corr_full_vs_B": float(corr_b[c]),
                                 "min_period_corr": float(rep),
                                 "structure_label": ("structure" if beats and rep >= 0.9 else
                                                     "not distinguishable from noise" if not beats else "not stable")})
    labels_tbl = pd.DataFrame(lab_rows)

    # ------------------------------------------------ bootstrap co-assignment
    rng = np.random.default_rng(ST["bootstrap"]["seed"])
    utick = np.unique(tick)
    boots = [rng.choice(utick, size=utick.size, replace=True) for _ in range(ST["bootstrap"]["n"])]
    pos = {t: np.flatnonzero(tick == t) for t in utick}
    co = []
    for method in ("gmm", "kmeans"):
        n_init = ST["bootstrap"]["gmm_n_init"] if method == "gmm" else ST["bootstrap"]["kmeans_n_init"]
        for k in KS:
            full_lab = labels_real[(method, k)]
            acc = np.zeros(n)
            sizes = np.bincount(full_lab, minlength=k)
            for bt in boots:
                rows = np.concatenate([pos[t] for t in bt])
                lb = predict(fit_model(X[rows], method, k, d, n_init), X)
                for c in range(k):
                    mem = np.flatnonzero(full_lab == c)
                    if mem.size < 2:
                        continue
                    h = np.bincount(lb[mem], minlength=k)
                    acc[mem] += (h[lb[mem]] - 1) / (mem.size - 1)
            co.append(pd.DataFrame({"event_id": ids, "view": view, "method": method, "k": k, "label": full_lab,
                                    "co_assignment_rate": acc / len(boots)}))
        print(" ", view, method, "bootstrap done", round(time.perf_counter() - t0), "s", flush=True)
    co = pd.concat(co, ignore_index=True)

    # ------------------------------------------------ 4d theory x cluster
    tt = pd.read_parquet(S.art("s1_theory_types.parquet"))
    tt = tt[tt["N"] == 100][["event_id", "theory_type", "type_state"]]
    x = asg.merge(tt, on="event_id", how="left")
    x["theory_type"] = x["theory_type"].fillna(x["type_state"]).fillna("untyped")
    xt = x.groupby(["view", "method", "k", "label", "theory_type"]).size().rename("n").reset_index()

    for df, name in [(st, "stats"), (rmn, "real_minus_null"), (pd.DataFrame(spectrum), "spectrum"), (pd.DataFrame(shapes), "fpc_shapes"),
                     (asg, "assignments"), (cen, "centroids"), (stab, "stability"), (labels_tbl, "structure"), (co, "coassign"),
                     (xt, "theory_x_cluster")]:
        df["config_hash"] = S.cfg_hash()
        df.to_parquet(S.art(f"t3_{view}_{name}.parquet"), index=False)
    S.write_json(f"t3_{view}_summary.json", {
        "config_hash": S.cfg_hash(), "view": view, "events_clustered": n, "not_clustered_sigma_zero": n_dropped, "d_90pct": d,
        "null_replicates": R, "seconds": round(time.perf_counter() - t0, 1),
        "real_minus_null": rmn.drop(columns=["view"]).to_dict("records"),
        "stability_min_corr": stab.groupby(["method", "k", "variant", "direction"])["centroid_corr"].min().reset_index().to_dict("records"),
        "structure_labels": labels_tbl.groupby(["method", "k"])["structure_label"].value_counts().rename("n").reset_index().to_dict("records"),
        "coassign_median": co.groupby(["method", "k"])["co_assignment_rate"].median().reset_index().to_dict("records")})
    print(view, "all done", round(time.perf_counter() - t0), "s")
    print(rmn.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
