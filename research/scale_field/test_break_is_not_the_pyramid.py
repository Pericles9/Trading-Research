"""
Is the ~200 s break in the rate channel's dispersion a property of the DATA, or an
artefact of the Gaussian pyramid's decimation schedule?

This is run before the number is written down as a finding, because it is the most
interesting number in the run and therefore the one most worth trying to break.

THE SUGGESTED TEST DOES NOT WORK, and the algebra says so before any run. The
verification note proposed re-running with `sigma_lo=12` on the grounds that it "moves
every octave boundary without changing the estimator". It does not move them at all.
In `field()`, the base grid is `dt = scales.min() / sigma_lo` and decimation fires while
`s / dt > 4 * sigma_lo`, so the first boundary sits at

    s > 4 * sigma_lo * scales.min() / sigma_lo  =  4 * scales.min()

and every later one at 8x, 16x, ... the band minimum. sigma_lo cancels. Measured over
sigma_lo in {5, 8, 12}: the boundaries are identical to the digit (4.362, 8.724, 17.448,
32.0, 69.792 s for a band starting at 1 s). Raising sigma_lo refines the base grid --
which is worth doing on its own account, and is reported -- but it is not the
sensitivity test it was intended to be.

Two tests that DO move or remove the thing under suspicion:

  A. SHIFT THE BAND MINIMUM by sqrt(2). Boundaries move multiplicatively with it
     (4.362 -> 5.657, 69.792 -> 98.701 s). Same estimator, same event, same scales per
     octave; only the decimation schedule moves. If the break tracks the schedule it
     moves by sqrt(2); if it is in the data it stays put.

  B. REMOVE THE PYRAMID. `field_exact` evaluates the kernel pairwise with no binning,
     no decimation and no interpolation. It is the definitive answer. Cost is
     O(|t_grid| x n_prints x n_scales), so it runs on a subsampled time grid and a
     scale window bracketing the break -- which is all that is needed, since the
     question is local to the break.

Usage: .venv/Scripts/python.exe research/scale_field/test_break_is_not_the_pyramid.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))

import adapter  # noqa: E402
from adapter import load_detection, load_event_prints_meta, rel  # noqa: E402
from scale_field import (collapse_same_timestamp, field, field_exact,  # noqa: E402
                         intervals, seconds_since)
from v3_t1_gate import broken_stick  # noqa: E402  -- v3's own fit, reused

OUT = "results/scale_field/artifacts/break_pyramid_sensitivity.json"
EVENTS = ["AEHL_2021-02-19_37.50", "CREX_2022-02-01_41.48"]

# Bracket the break generously: the reported location is ~215 s, so span 8 s .. 2048 s.
EXACT_SCALE_LO, EXACT_SCALE_HI, EXACT_N_SCALES = 8.0, 2048.0, 25
EXACT_GRID_POINTS = 150


def decimation_boundaries(band_min: float, sigma_lo: float, band_max: float) -> list[float]:
    scales = np.geomspace(band_min, band_max, 89)
    dt, out = band_min / sigma_lo, []
    for s in scales:
        while s / dt > 4 * sigma_lo:
            dt *= 2
            out.append(float(s))
    return out


def iqr_knee(scales, Z) -> dict:
    """Break location of the dispersion-across-time curve, via v3's broken_stick."""
    iqr = np.nanpercentile(Z, 75, axis=0) - np.nanpercentile(Z, 25, axis=0)
    ok = np.isfinite(iqr) & (iqr > 0)
    if ok.sum() < 6:
        return {"ok": False, "n_scales_used": int(ok.sum())}
    f = broken_stick(np.log10(np.asarray(scales)[ok]), np.log10(iqr[ok]))
    return {"ok": bool(f.get("ok")), "knee_seconds": round(float(f["knee_seconds"]), 2),
            "delta_bic": round(float(f["delta_bic"]), 1),
            "slope_before": round(float(f["slope_before"]), 3),
            "slope_after": round(float(f["slope_after"]), 3),
            "n_scales_used": int(ok.sum())}


def main() -> int:
    cfg = adapter.load_config()
    fcfg, sa = cfg["field"], cfg["scale_axis"]
    results = {
        "question": "Is the ~200 s break in the rate channel's dispersion in the data "
                    "or in the pyramid's decimation schedule?",
        "sigma_lo_is_not_the_knob": {
            "claim": "sigma_lo does NOT move the decimation boundaries; they sit at "
                     "4 * scales.min() * 2^k. sigma_lo cancels in s/dt > 4*sigma_lo "
                     "with dt = scales.min()/sigma_lo.",
            "boundaries_by_sigma_lo": {
                str(sl): [round(b, 3) for b in decimation_boundaries(1.0, sl, 2048.0)[:5]]
                for sl in (5.0, 8.0, 12.0)},
            "boundaries_by_band_min": {
                str(bm): [round(b, 3) for b in decimation_boundaries(bm, 8.0, 2048.0 * bm)[:5]]
                for bm in (1.0, 2 ** 0.5)},
        },
        "events": {},
    }

    det = load_detection(cfg)
    for ev in EVENTS:
        ts, meta = load_event_prints_meta(ev, None, cfg)
        arr = collapse_same_timestamp(ts)
        origin = int(arr[0])
        ts_s = seconds_since(arr, origin)
        ev_s, x = intervals(arr, origin=origin)
        t_grid = np.linspace(ts_s[0], ts_s[-1], fcfg["t_grid_points_coarse"])
        row = {"segment": str(det.loc[det["event_id"] == ev, "segment"].iloc[0]),
               "n_arrivals": int(arr.size)}

        # --- A. shift the band minimum, which DOES move the schedule -----------
        for tag, bmin in (("band_min_1.0", 1.0), ("band_min_sqrt2", float(np.sqrt(2)))):
            scales = np.geomspace(bmin, bmin * 2048.0, sa["coarse"]["n_scales"])
            f = field(ts_s, ev_s, x, t_grid, scales, neff_min=fcfg["neff_min"],
                      sigma_lo=fcfg["sigma_lo"], edge_scales=fcfg["edge_scales"])
            row[tag] = {
                "scales": [round(float(scales[0]), 4), round(float(scales[-1]), 1)],
                "first_decimations": [round(b, 3) for b in
                                      decimation_boundaries(bmin, fcfg["sigma_lo"], bmin * 2048.0)[:4]],
                "dlograte": iqr_knee(scales, f["dlograte"]),
                "dm": iqr_knee(scales, f["dm"]),
            }

        # --- B. remove the pyramid entirely ------------------------------------
        sc_x = np.geomspace(EXACT_SCALE_LO, EXACT_SCALE_HI, EXACT_N_SCALES)
        tg_x = np.linspace(ts_s[0], ts_s[-1], EXACT_GRID_POINTS)
        fe = field_exact(ts_s, ev_s, x, tg_x, sc_x, neff_min=fcfg["neff_min"])
        fp = field(ts_s, ev_s, x, tg_x, sc_x, neff_min=fcfg["neff_min"],
                   sigma_lo=fcfg["sigma_lo"], edge_scales=fcfg["edge_scales"])
        row["exact_no_pyramid"] = {
            "scale_range": [EXACT_SCALE_LO, EXACT_SCALE_HI],
            "n_scales": EXACT_N_SCALES, "t_grid_points": EXACT_GRID_POINTS,
            "dlograte": iqr_knee(sc_x, fe["dlograte"]),
            "dm": iqr_knee(sc_x, fe["dm"]),
        }
        row["pyramid_same_grid"] = {
            "dlograte": iqr_knee(sc_x, fp["dlograte"]),
            "dm": iqr_knee(sc_x, fp["dm"]),
        }
        results["events"][ev] = row
        print(f"{ev}  ({row['segment']})")
        print(f"  band_min 1.0     dlograte knee {row['band_min_1.0']['dlograte'].get('knee_seconds')} s")
        print(f"  band_min sqrt2   dlograte knee {row['band_min_sqrt2']['dlograte'].get('knee_seconds')} s"
              f"   (schedule moved by 1.414x)")
        print(f"  EXACT, no pyramid dlograte knee {row['exact_no_pyramid']['dlograte'].get('knee_seconds')} s")
        print(f"  pyramid, same grid dlograte knee {row['pyramid_same_grid']['dlograte'].get('knee_seconds')} s")

    # ---- verdict
    verdicts = {}
    for ev, r in results["events"].items():
        a = r["band_min_1.0"]["dlograte"].get("knee_seconds")
        b = r["band_min_sqrt2"]["dlograte"].get("knee_seconds")
        e = r["exact_no_pyramid"]["dlograte"].get("knee_seconds")
        moved = None if not (a and b) else round(b / a, 3)
        verdicts[ev] = {
            "shift_ratio_band_min": moved,
            "tracks_the_schedule_would_be": 1.414,
            "exact_vs_pyramid_ratio": None if not (a and e) else round(e / a, 3),
            "verdict": ("data" if moved is not None and abs(moved - 1.0) < 0.25
                        else "pyramid or inconclusive"),
        }
    results["verdicts"] = verdicts
    results["source"] = "research/scale_field/test_break_is_not_the_pyramid.py:main"
    results["reproduce"] = (".venv/Scripts/python.exe research/scale_field/"
                            "test_break_is_not_the_pyramid.py")
    with open(rel(OUT), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {OUT}")
    for ev, v in verdicts.items():
        print(f"  {ev}: shift {v['shift_ratio_band_min']} (schedule would give 1.414) "
              f"-> {v['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
