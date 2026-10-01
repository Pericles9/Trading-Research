"""
Chop regime C1 -- Amendment 1 A1.3: the efficiency ratio's noise reference, simulated through the pipeline.

Per window (one valid scale-free rung of one moment, as measures.build_event hands it to `on_window`):

  VWAP      the window's print-to-print log returns, demeaned, drawn with replacement; re-integrated from the first
            print's log price with every print's own time and size kept; bucketed exactly as real data (the owners of the
            32 volume edges depend on the sizes only; the value sums run on each synthetic print's deviation from the
            synthetic first print with volume, measures.vwap_log_path's construction)
  midpoint  the D17-valid quotes from the one prevailing at the window's first print through t: log midpoint changes,
            demeaned, drawn with replacement; re-integrated from the prevailing midpoint with the quote times kept; sampled
            at the first print and each bucket's last print (measures.bucket_path's sample points)

er is then measures.scale_free on the 32 returns, as on real data. An injected drift (the A1.4 positive control) adds
d x sd(demeaned steps) / sqrt(n steps) to every step of the same draws: d own-noise units of the null walk across the
window. An identity check (no demeaning, the identity draw) must reproduce the build's own returns.

Reads only the window's prints and quotes at or before t (the sliced views); no outcome is touched.
"""
from __future__ import annotations

import numpy as np

import c1common as C
import measures as M

BASIS_CODE = {"mid": 0, "vwap": 1}
CHUNK = 4_000_000                       # elements per (draws x steps) block, to bound memory on the busiest windows


def _er_rows(R: np.ndarray) -> np.ndarray:
    return M.scale_free(R)["er"]


def vwap_steps(info: dict) -> dict:
    bp, v = info["bp"], info["v"]
    lo, hi = bp["lo"], bp["hi"]
    ts, px, sz = v["ts"][lo:hi], v["px"][lo:hi], v["sz"][lo:hi]
    cv_end = np.cumsum(sz)
    b = M.buckets_core(ts, px, cv_end, np.cumsum(px * sz), len(bp["t_end"]))
    nb = len(bp["t_end"])
    E = np.arange(1, nb + 1, dtype=np.float64) * (b["V"] / nb)
    E[-1] = b["V"]
    return {"steps": np.diff(np.log(px)), "sz": sz, "cv_end": cv_end, "own": b["own"], "first": b["first"], "E": E, "B": b["V"] / nb}


def vwap_paths(ws: dict, S: np.ndarray) -> np.ndarray:
    """(D, 32) bucket returns for D step sequences S (D, n - 1)."""
    syn = np.c_[np.zeros(S.shape[0]), np.cumsum(S, axis=1)]
    dev = np.expm1(syn - syn[:, [ws["first"]]])
    cd = np.cumsum(dev * ws["sz"][None, :], axis=1)
    own = ws["own"]
    F = cd[:, own] - (ws["cv_end"][own] - ws["E"])[None, :] * dev[:, own]
    u = np.diff(np.c_[np.zeros(S.shape[0]), F], axis=1) / ws["B"]
    return np.diff(np.log1p(np.c_[dev[:, ws["first"]], u]), axis=1)


def mid_steps(info: dict) -> dict | None:
    bp, qv = info["bp"], info["qv"]
    if qv is None or not bp["mid_ok"]:
        return None
    vts, vlm = qv["vts"], qv["vlogmid"]
    i0 = int(np.searchsorted(vts, bp["t_first"], "right")) - 1
    if i0 < 0:
        return None
    idx = np.searchsorted(vts, np.r_[bp["t_first"], bp["t_end"]], "right") - 1 - i0
    return {"steps": np.diff(vlm[i0:]), "lm0": float(vlm[i0]), "idx": idx}


def mid_paths(ms: dict, S: np.ndarray) -> np.ndarray:
    path = np.c_[np.zeros(S.shape[0]), np.cumsum(S, axis=1)]
    return np.diff(path[:, ms["idx"]], axis=1)


def null_er(info: dict, basis: str, draws: int, seed: int, drifts=(0.0,), identity_check: bool = False) -> dict | None:
    """{d: (draws,) er} for the A1.3 null with drift d (d = 0 is the null itself). None when the basis has no path."""
    if basis == "vwap":
        ws = vwap_steps(info)
        paths = lambda S: vwap_paths(ws, S)  # noqa: E731
        real = info["r_vwap"]
    else:
        ws = mid_steps(info)
        if ws is None:
            return None
        paths = lambda S: mid_paths(ws, S)  # noqa: E731
        real = info["r_mid"]
    x = ws["steps"]
    if identity_check:
        R0 = paths(x[None, :])
        assert np.allclose(R0[0], real, rtol=1e-7, atol=1e-10), f"A1.3 null wiring: identity path differs from the build's {basis} returns"
    n = x.size
    out = {d: np.full(draws, np.nan) for d in drifts}
    if n == 0:
        return out
    d0 = x - x.mean()
    sd = float(np.sqrt((d0 * d0).mean()))
    rng = np.random.default_rng([seed, int(info["event_index"]), int(info["j"]), int(info["k"]), BASIS_CODE[basis], 31])
    I = rng.integers(0, n, size=(draws, n))
    step = max(1, CHUNK // max(n, 1))
    for a in range(0, draws, step):
        S = d0[I[a:a + step]]
        for d in drifts:
            out[d][a:a + step] = _er_rows(paths(S + d * sd / np.sqrt(n)))
    return out


def cell_key(seg: str, k: int, tier: str, basis: str) -> str:
    return f"{seg}|{int(k)}|{tier}|{basis}"


def band(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    if not x.size:
        return {"draws": 0, "median": np.nan, "p05": np.nan, "p95": np.nan}
    return {"draws": int(x.size), "median": float(np.median(x)), "p05": float(np.quantile(x, 0.05)), "p95": float(np.quantile(x, 0.95))}
