"""
Brief 1, Amendment 2 A2.2 -- the control references, simulated at each rung's N with the same statistic
(realised-variance scale, A2.3 tie rule) the controls use. Computed and committed BEFORE the re-run.

For N in {50, 100, 200}, M seeded Gaussian paths each:
  bridge      demeaned iid N(0,1) steps, shuffled -- what the negative bridge control produces with no
              drift and no fat tails. u_peak should be discrete-uniform.
  free_walk   iid N(0,1) steps, sum free -- the negative free-walk control's no-drift reference and the
              step-zero reference line (A2.2): a discrete arcsine.
  positive    the bridge construction plus the injected rise 2.0 to u = 0.3 and fall 1.5, injected in the
              ORIGINAL (pre-demeaning) path's sigma_path units -- the same injection as the positive control.

Writes artifacts/t6_references.json (means, medians, and the full u_peak distribution per atom i/N).
No data is read. Recovered-versus-injected bias is recorded as an instrument property, never corrected.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t6a_references.py
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import instruments as I  # noqa: E402


def main() -> int:
    cfg = C.load_cfg()
    a2 = cfg["amendment_2"]["references"]
    M, seed = a2["paths_per_N"], a2["seed"]
    inj = a2["injection"]
    rng = np.random.default_rng(seed)
    out = {"config_hash": C.cfg_hash(), "paths_per_N": M, "seed": seed, "scale": "rv", "tie_tol": 1e-9, "by_N": {}}
    for N in cfg["t4_excursion"]["bucket_ladder"]:
        u = np.arange(N + 1) / N
        d_inc = np.diff(I.drift_curve(u, inj["peak_u"], inj["rise"], inj["fall"]))
        res = {"bridge": [], "free_walk": [], "positive": []}
        for _ in range(M):
            z = rng.standard_normal(N)
            sp0 = math.sqrt(float(np.sum(z * z)))
            dm = rng.permutation(z - z.mean())
            fw = rng.standard_normal(N)
            for key, steps in (("bridge", dm), ("free_walk", fw), ("positive", dm + d_inc * sp0)):
                c = I.components(np.r_[0.0, np.cumsum(steps)])
                res[key].append((c["i_peak"], c["rise_s"], c["fall_s"], c["u_peak"]))
        rN = {}
        for key, rows in res.items():
            a = np.array(rows, dtype=float)
            ip = a[:, 0].astype(int)
            rN[key] = {"n": int(len(a)), "mean_rise_s": float(a[:, 1].mean()), "median_rise_s": float(np.median(a[:, 1])),
                       "mean_fall_s": float(a[:, 2].mean()), "median_fall_s": float(np.median(a[:, 2])),
                       "median_u_peak": float(np.median(a[:, 3])), "mean_u_peak": float(a[:, 3].mean()),
                       "u_peak_counts": np.bincount(ip, minlength=N + 1).tolist()}
        out["by_N"][str(N)] = rN
        print(N, {k: (round(v["mean_rise_s"], 3), round(v["median_rise_s"], 3), round(v["median_fall_s"], 3), round(v["median_u_peak"], 3))
                  for k, v in rN.items()})
    C.write_json(f"{C.ART}/t6_references.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
