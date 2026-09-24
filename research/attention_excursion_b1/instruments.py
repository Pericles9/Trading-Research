"""
Brief 1 -- the two instruments, as pure functions shared by T4 (build), T5 (build) and T6 (controls).

The controls must exercise exactly the code that builds the real vectors, so nothing here is
re-implemented in the control script: T6 feeds synthetic paths and tapes through these same
functions.

Excursion (Part I I.2, Part II T4)
    bucketize()         equal-share-volume buckets, prints split across bucket edges at their own
                        price, VWAP per bucket, bucket time = last contributing print
    components()        the vector from a log-price path [ln tau_price, ln P_1 .. ln P_N]

Acceleration (Part I A2, Part II T5)
    a2_count_ladder()   top-anchored halving ladder, counting-noise stop and D22 floor
    a2_kernel()         the scale field's one-sided (D23) kernel rate ratio, as a check
"""
from __future__ import annotations

import math

import numpy as np

PI_2 = math.pi / 2.0


# ====================================================================== excursion

def bucketize(ts: np.ndarray, px: np.ndarray, sz: np.ndarray, n_buckets: int) -> dict:
    """Cut a path into n_buckets of equal share volume.

    A print straddling a bucket edge is split across the buckets at its own price. Returns bucket
    VWAP, bucket volume, bucket end time and assignment diagnostics. Zero-size prints carry no
    volume and so cannot sit in a volume bucket; they are counted, not assigned."""
    sz = np.asarray(sz, dtype=np.float64)
    pos = sz > 0
    n_zero = int((~pos).sum())
    ts, px, sz = ts[pos], px[pos], sz[pos]
    V = float(sz.sum())
    if V <= 0 or ts.size == 0:
        return {"ok": False, "reason": "no_volume", "n_zero_size": n_zero}
    B = V / n_buckets
    cum_end = np.cumsum(sz)
    cum_start = cum_end - sz
    edges = np.arange(n_buckets + 1, dtype=np.float64) * B
    edges[-1] = cum_end[-1]
    brk = np.unique(np.concatenate([cum_start, cum_end, edges]))
    seg_lo, seg_hi = brk[:-1], brk[1:]
    seg_v = seg_hi - seg_lo
    keep = seg_v > 0
    seg_lo, seg_hi, seg_v = seg_lo[keep], seg_hi[keep], seg_v[keep]
    mid = (seg_lo + seg_hi) / 2.0
    pr = np.searchsorted(cum_end, mid, side="right")          # print owning the segment
    bk = np.minimum((mid / B).astype(np.int64), n_buckets - 1)  # bucket owning the segment
    bvol = np.bincount(bk, weights=seg_v, minlength=n_buckets)
    bval = np.bincount(bk, weights=seg_v * px[pr], minlength=n_buckets)
    # every print's volume fully allocated; every bucket filled to B
    per_print = np.bincount(pr, weights=seg_v, minlength=ts.size)
    assert np.allclose(per_print, sz, rtol=1e-9, atol=1e-6), "print volume not fully assigned"
    assert abs(bvol.sum() - V) <= 1e-9 * V + 1e-6, "bucket volumes do not sum to the path volume"
    assert (bvol > 0).all(), "empty bucket"
    last_seg = np.flatnonzero(np.r_[bk[1:] != bk[:-1], True])
    bt = ts[pr[last_seg]]
    assert bt.size == n_buckets
    return {"ok": True, "vwap": bval / bvol, "vol": bvol, "t_end": bt.astype(np.int64),
            "V": V, "B": B, "n_prints": int(ts.size), "n_zero_size": n_zero,
            "max_bucket_vol_rel_err": float(np.max(np.abs(bvol - B)) / B)}


def bipower_sigma(r: np.ndarray) -> float:
    """sqrt((pi/2) * mean |r_i| |r_{i-1}|) -- Barndorff-Nielsen & Shephard (2004)."""
    if r.size < 2:
        return float("nan")
    return float(math.sqrt(PI_2 * float(np.mean(np.abs(r[1:]) * np.abs(r[:-1])))))


def components(logp: np.ndarray) -> dict:
    """The sigma-unit components from a log path of length N+1 whose element 0 is ln(tau_price).

    Position i sits at u = i/N. sigma_b is re-estimated from this path's own returns every time --
    the controls depend on that."""
    N = logp.size - 1
    r = np.diff(logp)
    sb = bipower_sigma(r)
    sp = sb * math.sqrt(N)
    i_pk = int(np.argmax(logp))
    run_max = np.maximum.accumulate(logp[: i_pk + 1])
    dip = float(np.max(run_max - logp[: i_pk + 1]))
    rise = float(logp[i_pk] - logp[0])
    fall = float(logp[i_pk] - logp[N])
    term = float(logp[N] - logp[0])
    ok = np.isfinite(sp) and sp > 0
    div = sp if ok else np.nan
    return {"N": N, "i_peak": i_pk, "u_peak": i_pk / N, "sigma_b": sb, "sigma_path": sp,
            "rise_s": rise / div, "fall_s": fall / div, "dip_before_peak_s": dip / div,
            "terminal_s": term / div, "rise_log": rise, "fall_log": fall, "dip_log": dip,
            "terminal_log": term, "sigma_zero": not ok,
            "rise_censored": i_pk == N, "peak_at_tau": i_pk == 0, "no_rise": i_pk <= 1}


def excursion_vector(tau_ns: int, tau_price: float, ts: np.ndarray, px: np.ndarray, sz: np.ndarray,
                     n_buckets: int) -> dict:
    """Bucketize the path and compute every component, sigma-unit and money."""
    b = bucketize(ts, px, sz, n_buckets)
    if not b["ok"]:
        return {"N": n_buckets, "vector_available": False, "reason": b["reason"]}
    P = b["vwap"]
    logp = np.log(np.r_[tau_price, P])
    c = components(logp)
    i = c["i_peak"]
    p_pk = tau_price if i == 0 else float(P[i - 1])
    p_end = float(P[-1])
    c.update({
        "vector_available": True,
        "sigma_b_bp": c["sigma_b"] * 1e4, "sigma_path_bp": c["sigma_path"] * 1e4,
        "rise_bp": (p_pk - tau_price) / tau_price * 1e4, "fall_bp": (p_pk - p_end) / tau_price * 1e4,
        "rise_cents": (p_pk - tau_price) * 100.0, "fall_cents": (p_pk - p_end) * 100.0,
        "peak_price": p_pk, "end_bucket_price": p_end,
        "t_peak_s": 0.0 if i == 0 else float(b["t_end"][i - 1] - tau_ns) / 1e9,
        "t_end_s": float(ts[-1] - tau_ns) / 1e9,
        "n_path_prints": b["n_prints"], "n_zero_size_prints": b["n_zero_size"],
        "path_volume": b["V"], "max_bucket_vol_rel_err": b["max_bucket_vol_rel_err"],
    })
    c["_bucket_price"] = P
    c["_bucket_t_end"] = b["t_end"]
    return c


# ====================================================================== acceleration

def a2_count_ladder(ct: np.ndarray, tau_ns: int, t0400_ns: int, n_min: int = 17,
                    floor_coef: float = 2.2568, k_max: int = 40) -> list[dict]:
    """Top-anchored halving ladder on collapsed trade times `ct` (sorted int64, all <= tau).

    Rung k: W_k = H / 2^k; n_recent in [tau - W_k/2, tau], n_older in [tau - W_k, tau - W_k/2).
    Descends while both stops pass; the first failing rung is returned with its reason and is not
    valid. from_nothing (n_older == 0, n_recent > 0) is a class, never +inf."""
    assert ct.size == 0 or int(ct[-1]) <= tau_ns, "print after tau reached A2"
    H = tau_ns - t0400_ns
    out = []
    if H <= 0:
        return out
    hi = int(np.searchsorted(ct, tau_ns, side="right"))
    for k in range(k_max + 1):
        W = H / (2.0 ** k)
        a = tau_ns - int(round(W))
        m = tau_ns - int(round(W / 2.0))
        ia = int(np.searchsorted(ct, a, side="left"))
        im = int(np.searchsorted(ct, m, side="left"))
        n_rec, n_old = hi - im, im - ia
        W_s = W / 1e9
        lam = (n_rec + n_old) / W_s if W_s > 0 else 0.0
        floor_ok = lam > 0 and (W_s / 2.0) >= floor_coef / lam
        noise_ok = n_rec >= n_min and n_old >= n_min
        valid = bool(noise_ok and floor_ok)
        if valid:
            cls = "valid"
        elif n_old == 0 and n_rec > 0:
            cls = "from_nothing"
        elif not noise_ok:
            cls = "counting_noise"
        else:
            cls = "resolution_floor"
        out.append({"k": k, "W_s": W_s, "n_recent": n_rec, "n_older": n_old, "lambda_per_s": lam,
                    "noise_ok": bool(noise_ok), "floor_ok": bool(floor_ok), "valid": valid, "class": cls,
                    "accel": math.log(n_rec / n_old) if valid else float("nan"),
                    "win_lo_ns": a, "win_mid_ns": m})
        if not valid:
            break
    return out


def a2_kernel(ct: np.ndarray, tau_ns: int, t0400_ns: int, ks: list[int], field_exact,
              truncate: float = 4.0) -> dict:
    """ln(lambda_{W_k/2}(tau) / lambda_{W_k}(tau)) under the scale field's one-sided kernel,
    evaluated exactly (field_exact, no binning). Undefined where the history tau - 04:00 is shorter
    than truncate x W_k -- the scale field's own causal edge rule."""
    assert ct.size == 0 or int(ct[-1]) <= tau_ns, "print after tau reached the kernel check"
    H = tau_ns - t0400_ns
    ts_s = (ct - t0400_ns).astype(np.float64) / 1e9
    tg = np.array([(tau_ns - t0400_ns) / 1e9])
    out = {}
    for k in ks:
        W_s = H / (2.0 ** k) / 1e9
        if H / 1e9 < truncate * W_s:
            out[k] = {"defined": False, "accel_kernel": float("nan")}
            continue
        f = field_exact(ts_s, np.empty(0), np.empty(0), tg, np.array([W_s / 2.0, W_s]), kernel="onesided")
        lr = f["lograte"][0]
        out[k] = {"defined": bool(np.isfinite(lr).all()), "accel_kernel": float(lr[0] - lr[1]),
                  "lograte_half": float(lr[0]), "lograte_full": float(lr[1])}
    return out
