#!/usr/bin/env python
"""Are the detection requirement and the duration-readout requirement ever satisfied
at the same time on this cohort?

THE TWO REQUIREMENTS, both derived rather than asserted.

  DETECTION.  Depth at the centre of a Gaussian bump of width sigma read at scale s
  is -s^2/(sigma^2+s^2) (exact: convolving a Gaussian of width sigma with one of
  width s gives width sqrt(sigma^2+s^2), and F = s^2*lam''/lam at the centre is
  -s^2/(sigma^2+s^2)). A 2-sd detection needs that depth below -2*sd(n_eff), so

        s^2/(sigma^2+s^2) > 2*sd     =>     sigma < s * sqrt(1/(2*sd) - 1)

  and it is available at all only while 2*sd < 1, because F >= -1 always.

  DURATION READOUT.  Reading a duration needs scales down to sigma itself: the depth
  curve is flat in sigma once s >> sigma, so a field evaluated only at s >> sigma
  carries the feature's presence and not its width. And s >= s_min is a data limit,
  so sigma >= s_min is required for the width to be readable at all.

Both are stated against s_min, which makes the answer scale-free: it holds at every
rate on every event, and needs no tape to evaluate. Background dilution is IGNORED
here and that makes the detection condition OPTIMISTIC -- a bump sitting on a
background is shallower than -s^2/(sigma^2+s^2), so the real satisfiable band is
narrower than the one printed. Verified against the measured fixture in
gateA_resolve.json: at s = sigma the analytic depth is -0.500 and the measured value
on a bump of 200/s over a background of 20/s is -0.385.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ART = os.path.join(REPO_ROOT, "results", "scale_field", "artifacts",
                   "instrument_gates")


def main() -> int:
    with open(os.path.join(ART, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    tab = {q["n_eff"]: q["sd"] for q in rows
           if q["kernel"] == "centred" and q["conditioning"] == "unconditional"}
    ks = sorted(tab)
    sd_at = lambda ne: float(np.exp(np.interp(np.log(ne), np.log(ks),
                                              np.log([tab[k] for k in ks]))))

    out = {"note": __doc__, "read_factors": {}}
    print(f"{'rf':>4s} {'n_eff':>6s} {'2·sd':>7s} {'detect?':>8s} "
          f"{'sigma_max/s_min':>16s} {'sigma_min/s_min':>16s} {'band (decades)':>15s}")
    for f_ in (1.0, 2.0, 3.0, 4.0, 6.0, 8.0):
        ne = 8.0 * f_
        two = 2 * sd_at(ne)
        s_over_smin = f_                       # s* = read_factor * s_min, exactly
        if two >= 1.0:
            row = {"n_eff": ne, "two_sd": two, "detectable": False,
                   "sigma_max_over_s_min": 0.0, "band_decades": 0.0}
            print(f"{f_:4.0f} {ne:6.0f} {two:7.3f} {'NO':>8s} "
                  f"{'--':>16s} {'--':>16s} {'0':>15s}")
        else:
            # detection ceiling on the feature width, in units of s_min
            sig_max = s_over_smin * np.sqrt(1.0 / two - 1.0)
            sig_min = 1.0                      # width readable only at s >= s_min
            band = np.log10(sig_max / sig_min) if sig_max > sig_min else 0.0
            row = {"n_eff": ne, "two_sd": two, "detectable": True,
                   "sigma_max_over_s_min": sig_max,
                   "sigma_min_over_s_min": sig_min, "band_decades": band}
            print(f"{f_:4.0f} {ne:6.0f} {two:7.3f} {'yes':>8s} "
                  f"{sig_max:16.3f} {sig_min:16.3f} {band:15.3f}")
        out["read_factors"][f"{f_:g}"] = row

    # where does 2*sd cross 1.0 -- below this n_eff a 2-sd negative mark is impossible
    lo, hi = 3.0, 64.0
    for _ in range(80):
        mid = np.sqrt(lo * hi)
        if 2 * sd_at(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    out["n_eff_where_2sd_equals_1"] = float(np.sqrt(lo * hi))
    out["mask_floor_n_eff"] = 8.0
    print(f"\n2·sd = 1 at n_eff = {out['n_eff_where_2sd_equals_1']:.2f}. Below that a "
          f"2-sd negative detection is impossible for ANY feature, because F >= -1.")
    print(f"The field's own mask floor is n_eff >= 8, so the primary read sits "
          f"{8.0/out['n_eff_where_2sd_equals_1']:.2f}x above the impossibility line.")

    with open(os.path.join(ART, "satisfiability.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    print("\nwrote", os.path.join(ART, "satisfiability.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
