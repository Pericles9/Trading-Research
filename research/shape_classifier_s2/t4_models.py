"""
Shape classifier S2, T4 -- fit M0-M4 per fold and decision time, tuned inside the training window only.

  M0  training type shares (among training events that reached the decision time)
  M1  cell rule at tau: turnover band (training quartiles + missing) x ignition x segment, one pseudo-event at M0
  M2  multinomial logistic regression: numeric inputs median-filled + missing indicators, categoricals one-hot,
      standardised; C in {0.1, 1, 10}
  M3  HistGradientBoostingClassifier, native missing values and categoricals, early stopping off;
      learning rate {0.03, 0.1} x leaf count {15, 31} x iterations {200, 500}
  M4  atlas analogs after tau: k nearest training events by the Group C path distance (RMS over the query event's
      own 20-point elapsed grid), type shares among them, one pseudo-event at M0; k in {25, 50, 100}
  class weight none and balanced are separate variants of M2, M3 and M4, each tuned on its own.

Tuning: fit on the sub-train years, score validation log loss on the last training year's events whose ticker is
not in the sub-train years (Group C from the 'tune' typical paths); the chosen setting is refitted on the whole
training window (Group C 'final') and predicts the test year. The test year is never read before that.

The same `run_job` serves T5: permuted training labels (typical paths rebuilt from them by the caller), fixed
settings, extra (leak) inputs.

Amendment 1: every job runs for both labels -- the remaining-path type at the decision time (primary, A1.3) and the
whole-path type (secondary); at tau the remaining label is the whole label, so its results are copied.

Writes artifacts/t4_predictions.parquet (label x test events x fold x time x model: six probabilities),
t4_tuning.parquet, t4_group_c_remaining.parquet, t4_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t4_models.py
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "3")

import itertools  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.exceptions import ConvergenceWarning  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

K = len(S.TYPES)
A_NUM = ["tod_h", "gap_share", "runup_u_launch", "runup_height_s", "runup_max_drawdown_s", "runup_pushes", "log10_runup_minutes",
         "log10_runup_shares", "log10_turnover", "accel_k0", "accel_k1", "accel_k2", "accel_k3", "accel_k4", "log10_pre_trades_per_min",
         "log10_pre_dollars_per_min", "live_n_15", "live_n_60", "live_n_rest", "flow_share_15_k0", "flow_share_60_k0", "flow_share_rest_k0",
         "short_interest_share", "log10_shares_outstanding"]
A_BOOL = ["auction_minute", "tau_is_first_print", "accel_valid_k0", "accel_valid_k1", "accel_valid_k2", "accel_valid_k3", "accel_valid_k4",
          "a2_ignition", "filing_24h", "dilution_tau", "reverse_split_365d"]
A_CAT = ["segment", "last_form", "price_tier"]
T_CAT = ["tcs_state"]
B_NUM = ["elapsed_min", "ret_log", "high_log", "dd_log", "u_high", "log10_post_trades_per_min", "log10_post_dollars_per_min", "lr_trade_rate",
         "lr_dollar_rate", "accel_post", "rv_post", "log1p_max_gap_s", "log1p_since_last_print_s", "vol_progress", "asinh_z_ret",
         "asinh_z_high", "asinh_z_dd", "asinh_rv_ratio"]
B_BOOL = ["gap_halt_proxy"]
C_NUM = [f"dist_{t}" for t in S.TYPES]
M2_GRID = [{"C": c} for c in (0.1, 1.0, 10.0)]
M3_GRID = [{"learning_rate": lr, "max_leaf_nodes": ml, "max_iter": it} for lr, ml, it in itertools.product((0.03, 0.1), (15, 31), (200, 500))]
M4_GRID = [{"k": k} for k in (25, 50, 100)]
CWS = ("none", "balanced")
LEAK_COLS = ["leak_rise_pct", "leak_fall_pct", "leak_u_peak", "leak_terminal_log"]


def inputs_for(time_key: str, extra: tuple = ()) -> tuple[list, list, list]:
    """(numeric, boolean, categorical) input columns at a decision time."""
    num, boo, cat = list(A_NUM), list(A_BOOL), list(A_CAT) + list(T_CAT)
    if time_key != "tau":
        num += B_NUM + C_NUM
        boo += B_BOOL
    return num + list(extra), boo, cat


# ------------------------------------------------------------------ data

_DATA: dict = {}


def load_data() -> dict:
    """Everything a job needs, loaded once per process."""
    if _DATA:
        return _DATA
    pop = S.load_population()
    A = pd.read_parquet(S.art("t1_group_a.parquet"))
    ck = pd.read_parquet(S.art("t2_checkpoints.parquet"))
    ck = ck[ck["state"] == "reached"].copy()
    ck["log1p_max_gap_s"] = np.log1p(ck["max_gap_s"])
    ck["log1p_since_last_print_s"] = np.log1p(ck["since_last_print_s"])
    for c in ("z_ret", "z_high", "z_dd", "rv_ratio"):
        ck[f"asinh_{c}"] = np.arcsinh(ck[c])
    gc = pd.read_parquet(S.art("t2_group_c.parquet"))
    gcr = pd.read_parquet(S.art("t4_group_c_remaining.parquet")) if S.art("t4_group_c_remaining.parquet").exists() else None
    s1 = pd.read_parquet(S.src("s1_events"), columns=["event_id", "post100_rise_pct", "post100_fall_pct", "post100_u_peak"])
    ex = pd.read_parquet(S.src("b2_excursion"), columns=["event_id", "N", "terminal_log"])
    leak = s1.merge(ex[ex["N"] == 100][["event_id", "terminal_log"]], on="event_id", how="left")
    # the positive control's leak inputs, per label (A1.3): whole = S1's post-tau rule inputs and b2's terminal_log;
    # remaining = T3a's remaining-path rule inputs at the decision time
    leak = leak.rename(columns={"post100_rise_pct": "wleak_rise_pct", "post100_fall_pct": "wleak_fall_pct", "post100_u_peak": "wleak_u_peak",
                                "terminal_log": "wleak_terminal_log"})
    rem = S.remaining_table().rename(columns={"rem_rise_pct": "leak_rise_pct", "rem_fall_pct": "leak_fall_pct", "rem_u_peak": "leak_u_peak",
                                              "rem_terminal_log": "leak_terminal_log"})[["event_id", "time"] + LEAK_COLS]
    P = np.load(S.cache("master_paths.npy"), mmap_mode="r")
    pe = pd.read_parquet(S.cache("master_paths_events.parquet"))["event_id"]
    assert (pe.to_numpy() == pop["event_id"].to_numpy()).all()
    base = pop[["event_id", "ticker", "year", "type100", "excluded_dev"]].merge(A, on="event_id", how="left").merge(leak, on="event_id", how="left")
    for c in A_BOOL:                                   # booleans with nulls can come back from parquet as object
        base[c] = base[c].map({True: 1.0, False: 0.0}).astype(float)
    ck["gap_halt_proxy"] = ck["gap_halt_proxy"].map({True: 1.0, False: 0.0}).astype(float)
    _DATA.update({"pop": pop, "base": base, "ck": ck, "gc": gc, "gc_remaining": gcr, "rem_leak": rem, "P": P, "pos": pd.Series(np.arange(len(pop)), index=pop["event_id"]),
                  "masks": {f: S.fold_masks(pop, f) for f in S.FOLDS}})
    return _DATA


def frame(time_key: str, fold: int, stage: str, gc: pd.DataFrame | None = None, label: str = "whole") -> pd.DataFrame:
    """One row per event that reached `time_key`, with every input (Group C from the fold's `stage`, built from
    `label`'s typical paths) and the label's leak columns (used only by T5's positive control)."""
    D = load_data()
    ck = D["ck"][D["ck"]["time"] == time_key]
    f = D["base"].merge(ck, on="event_id", how="inner")
    if label == "whole":
        for c in LEAK_COLS:
            f[c] = f["w" + c]
    else:
        f = f.merge(D["rem_leak"][D["rem_leak"]["time"] == time_key].drop(columns="time"), on="event_id", how="left")
    if time_key != "tau":
        g = gc if gc is not None else (D["gc"] if label == "whole" else D["gc_remaining"])
        g = g[(g["time"] == time_key) & (g["fold"] == fold) & (g["stage"] == stage)][["event_id"] + C_NUM]
        f = f.merge(g, on="event_id", how="left")
    f["row"] = f["event_id"].map(D["pos"]).to_numpy()
    return f


# ------------------------------------------------------------------ encoders

class Prep:
    """M2's encoding, fitted on training rows only."""

    def __init__(self, num, boo, cat):
        self.num, self.boo, self.cat = num, boo, cat

    def fit(self, df):
        X = self._raw(df)
        self.med = np.nanmedian(X, axis=0)
        self.med = np.where(np.isfinite(self.med), self.med, 0.0)
        self.ind = np.flatnonzero(np.isnan(X).any(axis=0))
        self.levels = {c: sorted(df[c].astype("string").fillna("missing").unique()) for c in self.cat}
        Z = self._assemble(df, X)
        self.mu, self.sd = Z.mean(axis=0), Z.std(axis=0)
        self.sd[self.sd == 0] = 1.0
        return self

    def _raw(self, df):
        cols = [df[c].astype(float).to_numpy() for c in self.num] + [df[c].astype("float64").to_numpy() for c in self.boo]
        return np.column_stack(cols) if cols else np.zeros((len(df), 0))

    def _assemble(self, df, X):
        Xf = np.where(np.isnan(X), self.med[None, :], X)
        parts = [Xf, np.isnan(X[:, self.ind]).astype(float)]
        for c in self.cat:
            v = df[c].astype("string").fillna("missing").to_numpy()
            parts.append(np.column_stack([(v == lv).astype(float) for lv in self.levels[c]]))
        return np.column_stack(parts)

    def transform(self, df):
        return (self._assemble(df, self._raw(df)) - self.mu) / self.sd


class HGBPrep:
    """M3's encoding: numeric and booleans as float with NaN; categoricals as training-level codes (unseen = NaN)."""

    def __init__(self, num, boo, cat):
        self.num, self.boo, self.cat = num, boo, cat

    def fit(self, df):
        self.levels = {c: sorted(df[c].astype("string").fillna("missing").unique()) for c in self.cat}
        return self

    def transform(self, df):
        cols = [df[c].astype(float).to_numpy() for c in self.num] + [df[c].astype("float64").to_numpy() for c in self.boo]
        for c in self.cat:
            m = {lv: i for i, lv in enumerate(self.levels[c])}
            cols.append(df[c].astype("string").fillna("missing").map(m).astype(float).to_numpy())
        return np.column_stack(cols)

    def cat_mask(self):
        return np.r_[np.zeros(len(self.num) + len(self.boo), dtype=bool), np.ones(len(self.cat), dtype=bool)]

    def names(self):
        return self.num + self.boo + self.cat


def full_proba(model, X) -> np.ndarray:
    p = model.predict_proba(X)
    out = np.zeros((X.shape[0], K))
    out[:, model.classes_] = p
    return out


# ------------------------------------------------------------------ the models

def m0(y_fit) -> np.ndarray:
    c = np.bincount(y_fit, minlength=K).astype(float)
    return c / c.sum()


def m1_cells(df) -> pd.Series:
    return df["segment"].astype(str) + "|" + df["a2_ignition"].astype("string").fillna("missing").astype(str) + "|" + df["_tband"].astype(str)


def m1_fit_predict(fit, y_fit, pred) -> np.ndarray:
    p0 = m0(y_fit)
    lt = fit["log10_turnover"].to_numpy(float)
    q = np.nanquantile(lt, [0.25, 0.5, 0.75]) if np.isfinite(lt).any() else np.array([0, 0, 0.0])

    def band(df):
        x = df["log10_turnover"].to_numpy(float)
        b = np.searchsorted(q, x, side="right").astype(object)
        b[~np.isfinite(x)] = "missing"
        return b
    f, p = fit.copy(), pred.copy()
    f["_tband"], p["_tband"] = band(f), band(p)
    cf, cp = m1_cells(f), m1_cells(p)
    tab = pd.crosstab(cf, pd.Series(y_fit, index=f.index)).reindex(columns=range(K), fill_value=0)
    n = tab.sum(axis=1)
    probs = (tab.to_numpy() + p0[None, :]) / (n.to_numpy()[:, None] + 1.0)
    lut = dict(zip(tab.index, probs))
    return np.vstack([lut.get(c, p0) for c in cp])


def m2_fit(fit, y_fit, num, boo, cat, C, cw):
    prep = Prep(num, boo, cat).fit(fit)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        mdl = LogisticRegression(C=C, max_iter=3000, class_weight=None if cw == "none" else "balanced").fit(prep.transform(fit), y_fit)
    return prep, mdl


def m3_fit(fit, y_fit, num, boo, cat, st, cw, seed):
    prep = HGBPrep(num, boo, cat).fit(fit)
    mdl = HistGradientBoostingClassifier(learning_rate=st["learning_rate"], max_leaf_nodes=st["max_leaf_nodes"], max_iter=st["max_iter"],
                                         early_stopping=False, random_state=seed, categorical_features=prep.cat_mask(),
                                         class_weight=None if cw == "none" else "balanced").fit(prep.transform(fit), y_fit)
    return prep, mdl


def m4_predict(P, fit_rows, y_fit, q_rows, q_E_s, ks, cw) -> dict:
    """Type shares among the k nearest fit events by RMS path distance over each query's own 20-point grid."""
    grid = S.master_grid_s()
    idx = S.query_index(q_E_s, grid)
    Pf = np.asarray(P[np.asarray(fit_rows)], dtype=np.float32)
    Pq = np.asarray(P[np.asarray(q_rows)], dtype=np.float32)
    p0 = m0(y_fit)
    w = 1.0 / np.where(p0 > 0, p0, np.nan)
    w = np.nan_to_num(w)
    out = {k: np.zeros((len(q_rows), K)) for k in ks}
    kmax = max(ks)
    uq, inv = np.unique(idx, axis=0, return_inverse=True)
    inv = np.asarray(inv).reshape(-1)
    for u in range(uq.shape[0]):
        cols = uq[u]
        F = Pf[:, cols]
        ok = np.isfinite(F).all(axis=1)
        F, yy = F[ok], y_fit[ok]
        qi_all = np.flatnonzero(inv == u)
        kk = min(kmax, len(F))
        for c0 in range(0, len(qi_all), 256):                      # chunks keep the distance block small
            qi = qi_all[c0:c0 + 256]
            Q = Pq[qi][:, cols]
            dist = np.sqrt(((Q[:, None, :] - F[None, :, :]) ** 2).mean(axis=2))
            part = np.argpartition(dist, kk - 1, axis=1)[:, :kk] if kk < len(F) else np.tile(np.arange(len(F)), (len(qi), 1))
            for j, i in enumerate(qi):
                cand = part[j]
                order = cand[np.lexsort((cand, dist[j, cand]))]     # nearest first; ties by training-row order
                for k in ks:
                    nb = yy[order[:k]]
                    if cw == "none":
                        c = np.bincount(nb, minlength=K).astype(float)
                        out[k][i] = (c + p0) / (c.sum() + 1.0)
                    else:
                        c = np.bincount(nb, weights=w[nb], minlength=K)
                        c = c / c.sum() * len(nb) if c.sum() > 0 else c
                        out[k][i] = (c + 1.0 / K) / (len(nb) + 1.0)
    return out


# ------------------------------------------------------------------ one fold x decision time

def run_job(fold: int, time_key: str, *, label: str = "whole", labels: np.ndarray | None = None, gc: pd.DataFrame | None = None,
            fixed: dict | None = None, extra: tuple = (), models: tuple = ("M0", "M1", "M2", "M3", "M4"), seed: int = S.SEED) -> dict:
    """Fit and predict one label x fold x decision time. The label is the whole-path type or the remaining-path type
    at `time_key` (Amendment 1); rows without it are neither fitted nor scored. `labels` (aligned to the population)
    replaces it (T5 negative control); `gc` replaces the Group C table (typical paths from those labels); `fixed`
    {(model, cw): setting} skips tuning; `extra` adds input columns (T5 positive control)."""
    D = load_data()
    M = D["masks"][fold]
    num, boo, cat = inputs_for(time_key, extra)
    lab = S.labels_at(D["pop"], label, time_key) if labels is None else labels
    ycode = S.y_codes(lab)

    def has(df):
        return df[ycode[df["row"].to_numpy()] >= 0]
    fin = frame(time_key, fold, "final", gc, label)
    tr, te = has(fin[M["train"][fin["row"]]]), has(fin[M["test"][fin["row"]]])
    y_tr = ycode[tr["row"]]
    preds, tuning = {}, []
    if fixed is None:
        tun = frame(time_key, fold, "tune", gc, label)
        sub, val = has(tun[M["sub"][tun["row"]]]), has(tun[M["val"][tun["row"]]])
        y_sub, y_val = ycode[sub["row"]], ycode[val["row"]]
    chosen = {}

    def choose(name, cw, grid, score_fn):
        if fixed is not None:
            chosen[(name, cw)] = fixed[(name, cw)]
            return
        best = None
        for st in grid:
            ll = score_fn(st)
            tuning.append({"label": label, "fold": fold, "time": time_key, "model": name, "cw": cw, "setting": str(st), "val_log_loss": ll,
                           "n_sub": int(len(sub)), "n_val": int(len(val))})
            if best is None or ll < best[0]:
                best = (ll, st)
        chosen[(name, cw)] = best[1]
        tuning[-1 - (len(grid) - 1 - grid.index(best[1]))]["chosen"] = True

    if "M0" in models:
        preds[("M0", "none")] = np.tile(m0(y_tr), (len(te), 1))
    if "M1" in models and time_key == "tau":
        preds[("M1", "none")] = m1_fit_predict(tr, y_tr, te)
    if "M2" in models:
        for cw in CWS:
            choose("M2", cw, M2_GRID, lambda st: S.log_loss(y_val, (lambda pm: full_proba(pm[1], pm[0].transform(val)))(
                m2_fit(sub, y_sub, num, boo, cat, st["C"], cw))))
            prep, mdl = m2_fit(tr, y_tr, num, boo, cat, chosen[("M2", cw)]["C"], cw)
            preds[("M2", cw)] = full_proba(mdl, prep.transform(te))
    if "M3" in models:
        for cw in CWS:
            choose("M3", cw, M3_GRID, lambda st: S.log_loss(y_val, (lambda pm: full_proba(pm[1], pm[0].transform(val)))(
                m3_fit(sub, y_sub, num, boo, cat, st, cw, seed))))
            prep, mdl = m3_fit(tr, y_tr, num, boo, cat, chosen[("M3", cw)], cw, seed)
            preds[("M3", cw)] = full_proba(mdl, prep.transform(te))
    if "M4" in models and time_key != "tau":
        ks = [g["k"] for g in M4_GRID]
        for cw in CWS:
            if fixed is None:
                pv = m4_predict(D["P"], sub["row"].to_numpy(), y_sub, val["row"].to_numpy(), val["elapsed_min"].to_numpy() * 60.0, ks, cw)
                choose("M4", cw, M4_GRID, lambda st: S.log_loss(y_val, pv[st["k"]]))
            else:
                chosen[("M4", cw)] = fixed[("M4", cw)]
            k = chosen[("M4", cw)]["k"]
            preds[("M4", cw)] = m4_predict(D["P"], tr["row"].to_numpy(), y_tr, te["row"].to_numpy(), te["elapsed_min"].to_numpy() * 60.0, [k], cw)[k]
    rows = []
    prim = M["primary"][te["row"].to_numpy()]
    for (name, cw), p in preds.items():
        df = pd.DataFrame(p.astype(np.float32), columns=[f"p_{t}" for t in S.TYPES])
        df.insert(0, "event_id", te["event_id"].to_numpy())
        df.insert(1, "label", label)
        df.insert(2, "fold", fold)
        df.insert(3, "time", time_key)
        df.insert(4, "model", name)
        df.insert(5, "cw", cw)
        df.insert(6, "primary", prim)
        rows.append(df)
    return {"pred": pd.concat(rows, ignore_index=True), "tuning": pd.DataFrame(tuning), "chosen": {f"{k[0]}|{k[1]}": v for k, v in chosen.items()},
            "n": {"train": int(len(tr)), "test": int(len(te)), "primary": int(prim.sum())}}


def _job(args):
    label, fold, time_key = args
    t0 = time.perf_counter()
    r = run_job(fold, time_key, label=label)
    r["seconds"] = round(time.perf_counter() - t0, 1)
    r["label"], r["fold"], r["time"] = label, fold, time_key
    return r


def group_c_remaining() -> pd.DataFrame:
    """Group C for the remaining label (A1.3): per decision time after tau, the typical paths of each fold's
    training events grouped by their remaining-path type at that time (tune and final stages), and every event's
    six distances -- T2's group_c, unchanged, given that time's labels."""
    import t2_checkpoints as T2
    D = load_data()
    pop, out = D["pop"], []
    masks = T2.stage_masks(pop)
    for t in S.TIMES[1:]:
        g, _ = T2.group_c(pop, D["P"], D["ck"][D["ck"]["time"] == t], pd.Series(S.labels_at(pop, "remaining", t)), masks)
        out.append(g)
    gc = pd.concat(out, ignore_index=True)
    gc["config_hash"] = S.cfg_hash()
    return gc


def main() -> int:
    t_start = time.perf_counter()
    gcr = group_c_remaining()
    gcr.to_parquet(S.art("t4_group_c_remaining.parquet"), index=False, compression="zstd")
    print(f"remaining-label Group C {time.perf_counter() - t_start:,.0f}s", flush=True)
    _DATA.clear()
    jobs = [("whole", f, t) for t in S.TIMES for f in S.FOLDS] + [("remaining", f, t) for t in S.TIMES[1:] for f in S.FOLDS]
    preds, tun, chosen = [], [], []
    with ProcessPoolExecutor(max_workers=4) as ex:
        for r in ex.map(_job, jobs):
            preds.append(r["pred"])
            tun.append(r["tuning"])
            chosen.append({"label": r["label"], "fold": r["fold"], "time": r["time"], "seconds": r["seconds"], **r["n"], "chosen": r["chosen"]})
            print(f"  {r['label']:>9} fold {r['fold']} {r['time']:>5}  n={r['n']}  {r['seconds']}s  total {time.perf_counter() - t_start:,.0f}s", flush=True)
    # tau: the remaining label is the whole label by construction (A1.3); its results are the whole-label results
    for lst in (preds, tun):
        lst.extend([x[(x["label"] == "whole") & (x["time"] == "tau")].assign(label="remaining") for x in list(lst) if len(x)])
    chosen += [{**c, "label": "remaining", "copied_from": "whole"} for c in list(chosen) if c["label"] == "whole" and c["time"] == "tau"]
    pr = pd.concat(preds, ignore_index=True)
    pr["config_hash"] = S.cfg_hash()
    pr.to_parquet(S.art("t4_predictions.parquet"), index=False, compression="zstd")
    tu = pd.concat(tun, ignore_index=True)
    tu["chosen"] = tu["chosen"].fillna(False).astype(bool) if "chosen" in tu else False
    tu.to_parquet(S.art("t4_tuning.parquet"), index=False)
    S.write_json("t4_summary.json", {"config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "jobs": chosen,
                                     "inputs": {t: dict(zip(("numeric", "boolean", "categorical"), inputs_for(t))) for t in ("tau", "w1")}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
