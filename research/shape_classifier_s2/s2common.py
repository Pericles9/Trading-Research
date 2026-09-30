"""
Shape classifier S2 -- shared plumbing. Exploratory modelling build; the test is ticker-blocked and
time-ordered (brief section 5), everything else is exploratory.

Brief: prompts/shape_classifier_s2.md. Config: config/shape_classifier_s2.json (committed before the run).

Measurement reuses the programme's instrument unchanged: tick reading, session clock, segments, the D26
collapse and the spike guard's rule from Brief 1 (research/attention_excursion_b1/common.py) through S1's
s1common (which wraps b2's b2common). The label is S1's theory type, read from S1's committed artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

import numpy as np
import pandas as pd

_S1 = pathlib.Path(__file__).resolve().parents[1] / "shape_atlas_s1"
if str(_S1) not in sys.path:
    sys.path.insert(0, str(_S1))
import s1common as S1  # noqa: E402

C1, I, B2 = S1.C1, S1.I, S1.B2
REPO = S1.REPO
CFG = "config/shape_classifier_s2.json"
OUT = "results/shape_classifier/s2"
ART = f"{OUT}/artifacts"
CHARTS = f"{OUT}/charts"
CACHE = f"{OUT}/cache"
NS = C1.NS
MIN_NS = C1.MIN_NS
TYPES = ["runaway", "burst", "slow_climb", "exhausted", "fade", "chop"]
TYPE_LABEL = {"runaway": "runaway", "burst": "burst", "slow_climb": "slow climb", "exhausted": "exhausted", "fade": "fade", "chop": "chop"}
TIMES = ["tau", "w1", "w2", "w5", "w10", "w20", "v025", "v05", "v1", "v2"]
TIME_LABEL = {"tau": "τ", "w1": "τ+1m", "w2": "τ+2m", "w5": "τ+5m", "w10": "τ+10m", "w20": "τ+20m",
              "v025": "vol 0.25×", "v05": "vol 0.5×", "v1": "vol 1×", "v2": "vol 2×"}
WALL = {"w1": 1, "w2": 2, "w5": 5, "w10": 10, "w20": 20}
VOL = {"v025": 0.25, "v05": 0.5, "v1": 1.0, "v2": 2.0}
FOLDS = {1: ((2020, 2021), 2022), 2: ((2020, 2022), 2023), 3: ((2020, 2023), 2024)}
SEED = 20260928


def load_cfg() -> dict:
    with open(REPO / CFG, encoding="utf-8") as f:
        return json.load(f)


def cfg_hash() -> str:
    return hashlib.sha256((REPO / CFG).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def art(name: str) -> pathlib.Path:
    p = REPO / ART / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def cache(name: str) -> pathlib.Path:
    d = REPO / CACHE
    d.mkdir(parents=True, exist_ok=True)
    gi = d / ".gitignore"
    if not gi.exists():
        gi.write_text("# rebuildable cache (T2); never committed\n*\n", encoding="utf-8")
    return d / name


def chart_path(task: str, name: str) -> pathlib.Path:
    p = REPO / CHARTS / task / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def src(key: str) -> pathlib.Path:
    return REPO / load_cfg()["sources"][key]


def write_json(name: str, obj) -> None:
    C1.write_json(f"{ART}/{name}", obj)


def read_json(name: str) -> dict:
    return json.load(open(art(name), encoding="utf-8"))


# ------------------------------------------------------------------ population and labels

def load_population() -> pd.DataFrame:
    """S1's 15,519 events with tau, sorted by event_id, with the N = 50 / 100 / 200 labels and the dev flag."""
    ev = pd.read_parquet(src("s1_events"), columns=["event_id", "ticker", "event_date_canonical", "year", "tau_ns", "tau_price",
                                                     "prior_close_exact", "dev_group", "tau_anchor_segment", "price_tier", "sec_from_0400",
                                                     "first_print_ns"])
    tt = pd.read_parquet(src("s1_theory_types"))
    for N in (50, 100, 200):
        t = tt[(tt["N"] == N)].set_index("event_id")
        ev[f"type{N}"] = ev["event_id"].map(t["theory_type"].where(t["type_state"] == "typed"))
    ev["excluded_dev"] = ev["dev_group"].notna()
    ev = ev.sort_values("event_id").reset_index(drop=True)
    B2.assert_int64(ev)
    assert len(ev) == 15519
    return ev


def fold_masks(ev: pd.DataFrame, fold: int) -> dict:
    """Boolean masks over `ev` rows for one fold: train, test (secondary), primary, and the tuning split
    inside the training window (sub-train = training years before the last; validation = the last
    training year's events whose ticker is not in the sub-train years). Dev events and unlabelled events
    are in none of them."""
    (y0, y1), yt = FOLDS[fold]
    ok = (~ev["excluded_dev"]) & ev["type100"].notna()
    yr = ev["year"]
    train = ok & yr.between(y0, y1)
    test = ok & (yr == yt)
    primary = test & ~ev["ticker"].isin(set(ev.loc[train, "ticker"]))
    sub = ok & yr.between(y0, y1 - 1)
    val = ok & (yr == y1) & ~ev["ticker"].isin(set(ev.loc[sub, "ticker"]))
    return {"train": train.to_numpy(), "test": test.to_numpy(), "primary": primary.to_numpy(), "sub": sub.to_numpy(), "val": val.to_numpy()}


def ns_frame(rows: list[dict], ns_cols: list[str]) -> pd.DataFrame:
    """DataFrame from row dicts with the nanosecond columns built as exact Int64 (a column mixing ints and None
    is otherwise inferred as float64, which rounds epoch nanoseconds to 256 ns -- the upstream tau defect)."""
    df = pd.DataFrame([{k: v for k, v in r.items() if k not in ns_cols} for r in rows])
    for c in ns_cols:
        df[c] = pd.array([None if r.get(c) is None or (isinstance(r.get(c), float) and np.isnan(r.get(c))) else int(r.get(c)) for r in rows],
                         dtype="Int64")
    return df


def as_int64(s: pd.Series) -> pd.Series:
    """A timestamp column as Int64; float input must hold exact integers (asserted)."""
    if str(s.dtype) in ("Int64", "int64"):
        return s.astype("Int64")
    v = pd.to_numeric(s, errors="coerce")
    ok = v.notna()
    assert (v[ok] == np.round(v[ok])).all(), "non-integer timestamp"
    return v.astype("Int64")


LABELS = ["remaining", "whole"]          # Amendment 1 A1.3: primary = the remaining-path type, secondary = the whole-path type
LABEL_NAME = {"remaining": "remaining-path type (primary, A1.3)", "whole": "whole-path type (secondary, as run)"}
_REM = None


def remaining_table() -> pd.DataFrame:
    """T3a's per-(event, decision time) remaining-path labels and their leak inputs."""
    global _REM
    if _REM is None:
        _REM = pd.read_parquet(art("t3a_remaining_labels.parquet"),
                               columns=["event_id", "time", "rem_state", "rem_type", "rem_rise_pct", "rem_fall_pct", "rem_u_peak", "rem_terminal_log"])
    return _REM


def labels_at(pop: pd.DataFrame, label: str, time_key: str) -> np.ndarray:
    """Each population event's label at a decision time (object array, None where there is none)."""
    if label == "whole":
        return pop["type100"].to_numpy()
    r = remaining_table()
    m = r[r["time"] == time_key].set_index("event_id")["rem_type"]
    return pop["event_id"].map(m).to_numpy()


def y_codes(labels) -> np.ndarray:
    m = {t: i for i, t in enumerate(TYPES)}
    return np.array([m.get(x, -1) if isinstance(x, str) else -1 for x in labels], dtype=int)


# ------------------------------------------------------------------ tick helpers

def spike_flags(px: np.ndarray, dev: float = 0.03, agree: float = 0.03) -> np.ndarray:
    """Brief 1's is_spike, vectorised: print i deviates by more than `dev` from both neighbours, which
    agree within `agree`. The first and last prints of the array are never spikes (no neighbour)."""
    n = px.size
    out = np.zeros(n, dtype=bool)
    if n < 3:
        return out
    prev, cur, nxt = px[:-2], px[1:-1], px[2:]
    good = (prev > 0) & (nxt > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = good & (np.abs(cur - prev) / prev > dev) & (np.abs(cur - nxt) / nxt > dev) & \
            (np.abs(prev - nxt) / np.maximum(prev, nxt) <= agree)
    out[1:-1] = s
    return out


TAU_ROUND_NS = 128   # every stored tau / tau_mb in b1, b2 and S1 is float64-rounded to a multiple of 256 ns (T0)


def tcs_state(tau_x: int, tau_d: int, tau_mb_x, d: int, thr_ns: int = 60 * NS) -> str:
    """R1: tau_close_sensitive as far as it is settled at decision time d, on exact print times: the minute-bar
    crossing print tau_mb_x (recomputed from ticks in T2 with b1's first_crossing) seen by d -> TRUE if
    |tau_x - tau_mb_x| > 60 s else FALSE; not seen by d -> TRUE once d - tau_d > 60 s, else not_settled."""
    if tau_mb_x is not None and not pd.isna(tau_mb_x) and int(tau_mb_x) <= d:
        return "true" if abs(tau_x - int(tau_mb_x)) > thr_ns else "false"
    return "true" if d - tau_d > thr_ns else "not_settled"


def tcs_latest_ts(tau_mb_x, d: int) -> int:
    """The latest data timestamp the R1 state reads: the minute-bar crossing print when seen by d, else d."""
    if tau_mb_x is not None and not pd.isna(tau_mb_x) and int(tau_mb_x) <= d:
        return int(tau_mb_x)
    return d


def master_grid_s() -> np.ndarray:
    g = load_cfg()["inputs"]["group_c"]["master_grid_s"]
    a = np.arange(1, g["step_1s_to"] + 1, 1)
    b = np.arange(g["step_1s_to"] + 10, g["step_10s_to"] + 1, 10)
    c = np.arange(g["step_10s_to"] + 60, g["step_60s_to"] + 1, 60)
    return np.r_[0, a, b, c].astype(np.int64)


def query_index(E_s, grid: np.ndarray) -> np.ndarray:
    """Master-grid indices of the 20 query points t_g = E (g + 1) / 20 (the largest grid time <= t_g)."""
    E_s = np.atleast_1d(np.asarray(E_s, dtype=float))
    t = E_s[:, None] * (np.arange(20) + 1)[None, :] / 20.0
    return np.searchsorted(grid, t, side="right") - 1


# ------------------------------------------------------------------ scoring

def auc_weighted(y: np.ndarray, s: np.ndarray, w: np.ndarray | None = None) -> float:
    """One-vs-rest AUC (Mann-Whitney with ties = 1/2), with optional non-negative row weights (the ticker
    bootstrap draws weights). NaN when either class has zero weight."""
    y = np.asarray(y, dtype=bool)
    s = np.asarray(s, dtype=float)
    w = np.ones(y.size) if w is None else np.asarray(w, dtype=float)
    order = np.argsort(s, kind="mergesort")
    s, y, w = s[order], y[order], w[order]
    wp, wn = w * y, w * ~y
    P, Nn = wp.sum(), wn.sum()
    if P <= 0 or Nn <= 0:
        return float("nan")
    # group ties
    brk = np.r_[True, s[1:] != s[:-1]]
    gid = np.cumsum(brk) - 1
    gp = np.bincount(gid, wp)
    gn = np.bincount(gid, wn)
    neg_below = np.cumsum(gn) - gn
    return float((gp * (neg_below + 0.5 * gn)).sum() / (P * Nn))


def ticker_boot_weights(tickers: np.ndarray, B: int, seed: int) -> np.ndarray:
    """(B, n) row weights: each resample draws tickers with replacement; a row's weight is its ticker's
    draw count."""
    u, inv = np.unique(tickers, return_inverse=True)
    rng = np.random.default_rng(seed)
    cnt = rng.multinomial(len(u), np.full(len(u), 1.0 / len(u)), size=B)
    return cnt[:, inv].astype(float)


def auc_boot(y: np.ndarray, s: np.ndarray, W: np.ndarray) -> np.ndarray:
    """auc_weighted for every row of W at once (the sort and tie groups are shared)."""
    y = np.asarray(y, dtype=bool)
    order = np.argsort(np.asarray(s, dtype=float), kind="mergesort")
    ss, yy, WW = np.asarray(s, dtype=float)[order], y[order], W[:, order]
    brk = np.flatnonzero(np.r_[True, ss[1:] != ss[:-1]])
    gp = np.add.reduceat(WW * yy[None, :], brk, axis=1)
    gn = np.add.reduceat(WW * (~yy)[None, :], brk, axis=1)
    P, Nn = gp.sum(axis=1), gn.sum(axis=1)
    below = np.cumsum(gn, axis=1) - gn
    with np.errstate(divide="ignore", invalid="ignore"):
        a = (gp * (below + 0.5 * gn)).sum(axis=1) / (P * Nn)
    a[(P <= 0) | (Nn <= 0)] = np.nan
    return a


def auc_ci(y: np.ndarray, s: np.ndarray, W: np.ndarray) -> tuple[float, float, float]:
    a = auc_weighted(y, s)
    boots = auc_boot(y, s, W)
    boots = boots[np.isfinite(boots)]
    if boots.size == 0:
        return a, float("nan"), float("nan")
    return a, float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def log_loss(yc: np.ndarray, P: np.ndarray) -> float:
    P = np.clip(np.asarray(P, dtype=float), 1e-15, 1.0)
    P = P / P.sum(axis=1, keepdims=True)
    return float(-np.mean(np.log(P[np.arange(len(yc)), yc])))


def lift_top10(y: np.ndarray, s: np.ndarray) -> tuple[float, int]:
    y = np.asarray(y, dtype=bool)
    if y.size == 0 or y.mean() == 0:
        return float("nan"), 0
    thr = np.quantile(s, 0.9)
    top = s >= thr
    return float(y[top].mean() / y.mean()), int(top.sum())
