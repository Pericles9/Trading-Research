#!/usr/bin/env python
"""Gate A, resolved. The brief: 'If the zero-sum test fails, that is the single most
important finding available and the rest of this brief is void until it is resolved.'

TWO CORRECTIONS TO MY OWN FIRST PASS, both stated rather than quietly applied.

(1) THE WEIGHT. The identity is  int F(t,s) * lam_hat_s(t) dt = s^2 int lam_hat_s'' dt
    = 0, where lam_hat_s is the intensity SMOOTHED AT THAT SAME SCALE s. The first
    pass weighted by the k=20 kNN rate that sets s_min -- a different, scale-free
    estimator of a different quantity. Weighting an identity by the wrong lambda does
    not test the identity. The field's own `lograte` output is lam_hat_s and is what
    is used here.

(2) THE SIGN FIXTURE. My first pass built a bump of width sigma = 4 s on a background
    of 20/s with a peak of 220/s, then read at 2*s_min = 0.021 s -- two decades below
    the feature. Depth at the centre of a Gaussian bump of width sigma read at scale s
    is -s^2/(sigma^2+s^2), which at s = 0.021 and sigma = 4 is -0.00003. The fixture
    measured noise and I recorded it as a sign failure. It is not a defect in
    burst_on(); it is the resolution arithmetic this brief exists to characterise. The
    sign is asserted here at s comparable to the feature, which is where a sign
    convention can be read at all, and the committed suite is run beside it.

THE CONTROL THAT DECIDES THE ZERO-SUM. Run the same pyramid path, the same ladder, the
same edge and n_eff masks, on a synthetic INHOMOGENEOUS POISSON tape of the same
duration and rate path. A tape with no burst structure whatsoever must show the same
residual-versus-scale profile if the residual is the finite domain and the masks. If
the real tape's residual is larger, it is not the domain.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                    # noqa: E402
import event_panels as ep                                         # noqa: E402
from scale_field import (burst_on, collapse_same_timestamp, field,  # noqa: E402
                         intervals, s_min_for_rate, seconds_since)

OUT = os.path.join(REPO_ROOT, "results", "scale_field", "artifacts",
                   "instrument_gates")
PROBE_SCALES = (0.25, 1.0, 4.0, 16.0, 64.0, 256.0, 1024.0)


def weighted_residual(ts_s, ev_s, x, t_grid, scales, **kw):
    """int F*lam_s dt / int lam_s dt, per scale, weighted by the field's OWN lam_s."""
    f = field(ts_s, ev_s, x, t_grid, np.asarray(scales, float), **kw)
    dt = np.gradient(t_grid)
    out = []
    for j, s in enumerate(scales):
        F, L = f["dlograte"][:, j], f["lograte"][:, j]
        ok = np.isfinite(F) & np.isfinite(L)
        if ok.sum() < 100:
            out.append({"s": float(s), "n": int(ok.sum()), "rel": float("nan"),
                        "defined_share": float(ok.mean())})
            continue
        w = np.exp(L[ok]) * dt[ok]
        out.append({"s": float(s), "n": int(ok.sum()),
                    "rel": float((F[ok] * w).sum() / w.sum()),
                    "defined_share": float(ok.mean())})
    return out


def poisson_surrogate(ts_ns, lo_ns, hi_ns, seed=0, bw_s=30.0):
    """Inhomogeneous Poisson with the real tape's rate path and NOTHING ELSE.

    lam(t) is a Gaussian-smoothed count at bandwidth bw_s -- coarse enough that no
    burst structure survives into it, fine enough that the diurnal shape does. Thinned
    from a homogeneous draw at the running maximum, so the realisation is exact.
    """
    from scipy.ndimage import gaussian_filter1d
    rng = np.random.default_rng(seed)
    T = (hi_ns - lo_ns) / 1e9
    dt = 1.0
    n = int(T / dt) + 1
    c = np.bincount(np.clip(((ts_ns - lo_ns) / 1e9 / dt).astype(np.int64), 0, n - 1),
                    minlength=n).astype(float)
    lam = gaussian_filter1d(c, bw_s / dt, mode="nearest") / dt
    lmax = float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    return (lo_ns + (u[keep] * 1e9)).astype(np.int64)


def sign_check() -> dict:
    """The sign, asserted where a sign can be read: s comparable to the feature.

    Reported at three read scales so the resolution arithmetic is visible rather than
    hidden inside a pass/fail.
    """
    rng = np.random.default_rng(11)
    bg, T, sig, amp = 20.0, 400.0, 4.0, 200.0
    base = np.sort(rng.uniform(0, T, rng.poisson(bg * T)))
    bump = np.sort(rng.normal(T / 2, sig, rng.poisson(amp * sig * np.sqrt(2 * np.pi))))
    ts = np.sort(np.concatenate([base, bump[(bump > 0) & (bump < T)]]))
    ev, x = ts[1:], np.log10(np.diff(ts))
    tg = np.linspace(60, T - 60, 6000)
    scales = np.geomspace(0.25, 64, 73)
    f = field(ts, ev, x, tg, scales)
    inb = np.abs(tg - T / 2) < sig
    out = {"sigma_s": sig, "peak_rate": bg + amp, "background_rate": bg,
           "s_min_at_peak": float(s_min_for_rate(np.array([bg + amp]))[0]),
           "by_scale": [], "burst_on_by_factor": {}}
    for s_t in (0.25, 1.0, 4.0, 16.0):
        j = int(np.argmin(np.abs(scales - s_t)))
        v = f["dlograte"][:, j]
        out["by_scale"].append({
            "s": float(scales[j]),
            "s_over_sigma": float(scales[j] / sig),
            "F_median_in_bump": float(np.nanmedian(v[inb])),
            "F_median_outside": float(np.nanmedian(v[np.abs(tg - T / 2) > 8 * sig])),
            "analytic_depth_no_background": float(-scales[j] ** 2
                                                  / (sig ** 2 + scales[j] ** 2)),
            "share_negative_in_bump": float(np.nanmean(v[inb] < 0))})
    lam = bg + amp * np.exp(-0.5 * ((tg - T / 2) / sig) ** 2)
    for fac in (1.0, 2.0):
        on, sstar, jj = burst_on(f, scales, s_min_for_rate(lam), factor=fac)
        out["burst_on_by_factor"][str(fac)] = {
            "read_scale_in_bump_median": float(np.nanmedian(sstar[inb])),
            "read_scale_over_sigma": float(np.nanmedian(sstar[inb]) / sig),
            "on_share_in_bump": float(on[inb].mean()),
            "on_share_far_outside": float(on[np.abs(tg - T / 2) > 8 * sig].mean())}
    # the helper returns True where F is negative -- asserted directly, no fixture
    Zt = np.array([[-0.7, 0.3], [0.4, -0.2]])
    on_t, _, _ = burst_on({"dlograte": Zt}, np.array([1.0, 2.0]),
                          np.array([1.0, 1.0]), factor=1.0)
    out["helper_returns_true_on_negative"] = [bool(on_t[0]), bool(on_t[1])]
    out["helper_sign_correct"] = bool(on_t[0] and not on_t[1])
    return out


def main() -> int:
    cfg = ep.load_config()
    eid = sys.argv[1] if len(sys.argv) > 1 else "JFIN_2020-06-15_60.44"
    res = {"event_id": eid, "sign_check": sign_check(), "zero_sum": {}}

    ts_ns, meta = adapter.load_event_prints_meta(eid, None)
    arr = collapse_same_timestamp(ts_ns)
    origin = int(arr[0])
    lo, hi = int(meta["window_start_ns"]), int(meta["window_end_ns"])
    ts_s = seconds_since(arr, origin)
    ev_s, x = intervals(arr, origin=origin)
    tg = np.linspace(ts_s.min(), ts_s.max(), 240001)     # UNIFORM, so dt is constant

    variants = {
        "as_rendered_edge4_neff8": dict(edge_scales=4.0, neff_min=8.0),
        "no_edge_mask_neff8": dict(edge_scales=0.0, neff_min=8.0),
        "no_edge_mask_no_neff_mask": dict(edge_scales=0.0, neff_min=0.0),
    }
    for name, kw in variants.items():
        res["zero_sum"][name] = weighted_residual(ts_s, ev_s, x, tg, PROBE_SCALES, **kw)
        print(name)
        for q in res["zero_sum"][name]:
            print(f"    s={q['s']:8.2f}  rel={q['rel']:+.3e}  defined={q['defined_share']:.3f}")

    # THE CONTROL: same duration, same rate path, no burst structure.
    sur = poisson_surrogate(arr, lo, hi, seed=5)
    sur = collapse_same_timestamp(sur)
    print(f"\nsurrogate prints {sur.size:,} vs real {arr.size:,}")
    o2 = int(sur[0])
    st, se = seconds_since(sur, o2), intervals(sur, origin=o2)
    tg2 = np.linspace(st.min(), st.max(), 240001)
    res["zero_sum"]["SURROGATE_no_burst_structure_edge4_neff8"] = weighted_residual(
        st, se[0], se[1], tg2, PROBE_SCALES, edge_scales=4.0, neff_min=8.0)
    res["surrogate_prints"] = int(sur.size)
    res["real_prints"] = int(arr.size)
    print("SURROGATE (inhomogeneous Poisson, same rate path, no clustering)")
    for q in res["zero_sum"]["SURROGATE_no_burst_structure_edge4_neff8"]:
        print(f"    s={q['s']:8.2f}  rel={q['rel']:+.3e}  defined={q['defined_share']:.3f}")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "gateA_resolve.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=float)
    print("\nwrote", os.path.join(OUT, "gateA_resolve.json"))
    print("\nsign check:", json.dumps(res["sign_check"]["burst_on_by_factor"]))
    print("helper sign correct:", res["sign_check"]["helper_sign_correct"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
