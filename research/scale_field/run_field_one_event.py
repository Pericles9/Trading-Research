"""
Order-of-work step 3: one event, both bands, both channels. Compute it, write it,
chart it, STOP.

Two bands, because the cost is not symmetric (measured, 2M prints, one session):

    coarse  1 s .. 2048 s   whole session      89 scales    1.7 s / event
    fine    15.6 ms .. 1 s  +/- 15 s anchor    49 scales    7.0 s / event
    fine, same band, whole session                        > 110 s / event -- not run

The fine band is CHARTED over +/- 15 s inside a +/- 15 min READ, not over +/- 15 min
as the brief states. The deviation and its reason are recorded in
config/scale_field.json scale_axis.fine.window_deviation_from_brief and carried into
every run manifest: a heatmap column cannot be narrower than its kernel, and at
+/- 15 min a chart-width grid gives 1.3 s per column against a 15.6 ms smallest
kernel. Cost is unchanged -- it is set by the pyramid bin count over the READ window,
which is still +/- 15 min.

So the coarse band runs session-wide and the fine band runs only around the D7
detection anchor (threshold 1.3, poll 1 s, REUSED from
results/phase_10/artifacts/v2_r13_detection.parquet). The fine end is where the
fragmentation scale lives and it does not need session-wide coverage; the coarse end
is cheap and does.

BOUNDED AT BOTH ENDS, and both bounds are stated rather than assumed:

  * FINE end is bounded by the data. Below the local inter-trade interval the
    effective sample size collapses. `field()` returns NaN under n_eff >= 8 and is
    NEVER given a fallback -- same treatment as insufficient_context. The hard floor
    is 2^-20 s = 0.954 us, ~12x the 80.5 ns median timestamp resolution; below that
    you are measuring quantization. This run's fine band stops at 2^-6 s, far above it.
  * COARSE end is bounded by session length: cap ~ session_span / 8. At s = 4,096 s
    a regular-hours session (~23,400 s) holds ~2 independent windows, which is
    exactly where v3's headline A = 1,245 sits. The 2,048 s ceiling is under the cap
    for the extended session (57,600/8 = 7,200 s) and under it for RTH alone
    (23,400/8 = 2,925 s). The cap is recorded in the manifest, not left implicit.

NO THRESHOLD IS APPLIED AND NONE IS AVAILABLE YET. The Poisson constant
SIGMA_POISSON_DECADES is a unit-test fixture, not a standard against this tape: v3
measured the Allan factor at 5.99 at T = 15.6 ms rising monotonically to 1,245 at
T = 4,096 s, so a z-score against Poisson would be inflated by roughly sqrt(A(T)) --
about 2.4x at milliseconds and ~35x at the hour scale. Matched-null thresholds are
step 5, after Cooper reads this, and they REUSE research/phase_10b/pipeline.py.

Usage:
    .venv/Scripts/python.exe research/scale_field/run_field_one_event.py
    .venv/Scripts/python.exe research/scale_field/run_field_one_event.py --event TKR_YYYY-MM-DD_MM.MM
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import load_cohort, load_detection, load_event_prints_meta, rel  # noqa: E402
from scale_field import (allan_factor, collapse_same_timestamp, field,  # noqa: E402
                         intervals, to_seconds)

DEFAULT_EVENT = "AEHL_2021-02-19_37.50"
DEFAULT_EVENT_WHY = (
    "rth segment, 17,365 T=0 prints against an rth-segment median of 17,425 -- the "
    "median event, not the loudest one. Carries no cohort flag (row cap, dup prints, "
    "ETH-dominant, 1c repair all False) so nothing in the picture is a known artifact. "
    "Already in the Diag1 animation set, so the tape has been read before under the "
    "previous grammar."
)


def band_scales(spec: dict) -> np.ndarray:
    return np.geomspace(spec["min_seconds"], spec["max_seconds"], spec["n_scales"])


def run_band(ts_ns, name, spec, cfg, window_ns=None):
    """One band of the field. Returns (long-form DataFrame, provenance dict).

    `window_ns` restricts the REPORTED time grid; the tape is still read with a
    margin on each side so the estimator's own edge mask (edge_scales x s) never
    bites inside the reported window. Without the margin the fine band would return
    NaN over its first and last seconds and the picture would show a data boundary as
    if it were a feature. The margin is the band's `context_seconds` where it has one
    -- for the fine band that is the brief's +/- 15 min, read in full so the estimator
    sees the surrounding tape even though the chart shows the resolvable centre.
    """
    fcfg = cfg["field"]
    scales = band_scales(spec)
    margin_ns = int(max(spec.get("context_seconds", 0.0),
                        8 * spec["max_seconds"]) * 1e9)

    if window_ns is None:
        keep_ns = (int(ts_ns[0]), int(ts_ns[-1]) + 1)
        grid_ns = keep_ns
    else:
        grid_ns = (int(window_ns[0]), int(window_ns[1]))
        keep_ns = (grid_ns[0] - margin_ns, grid_ns[1] + margin_ns)

    sel = ts_ns[(ts_ns >= keep_ns[0]) & (ts_ns < keep_ns[1])]
    n_raw = int(sel.size)
    arr = collapse_same_timestamp(sel)             # reference tie variant
    if arr.size < 3:
        raise SystemExit(f"band {name}: only {arr.size} arrivals in window -- nothing to do")

    # One int64 origin shared by both channels. Rebasing BEFORE the float divide is
    # not cosmetic: at epoch magnitude float64 seconds have a 238 ns ULP against a
    # 49 ns minimum gap, and scale_field._assert_resolved raises rather than let that
    # through silently.
    origin = int(arr[0])
    ts_s, _ = to_seconds(arr, origin)
    ev_s, x = intervals(arr, origin_ns=origin)

    n_grid = fcfg["t_grid_points_fine"] if window_ns is not None else fcfg["t_grid_points_coarse"]
    t_grid = np.linspace((grid_ns[0] - origin) / 1e9, (grid_ns[1] - origin) / 1e9, n_grid)

    t0 = time.perf_counter()
    f = field(ts_s, ev_s, x, t_grid, scales,
              neff_min=fcfg["neff_min"], sigma_lo=fcfg["sigma_lo"],
              edge_scales=fcfg["edge_scales"])
    elapsed = time.perf_counter() - t0

    T, S = np.meshgrid(t_grid, scales, indexing="ij")
    df = pd.DataFrame({
        "band": name,
        "t_ns": (origin + (T.ravel() * 1e9)).astype(np.int64),
        "t_s_rel": T.ravel(),
        "scale_s": S.ravel(),
        "log2_scale": np.log2(S.ravel()),
        "m": f["m"].ravel(),
        "dm": f["dm"].ravel(),
        "lograte": f["lograte"].ravel(),
        "dlograte": f["dlograte"].ravel(),
        "n_eff": f["n_eff"].ravel(),
    })

    prov = {
        "band": name,
        "scale_min_seconds": float(scales[0]),
        "scale_max_seconds": float(scales[-1]),
        "n_scales": int(scales.size),
        "scales_per_octave": float((scales.size - 1) / np.log2(scales[-1] / scales[0])),
        "coverage": spec["coverage"],
        "t_grid_points": int(n_grid),
        "t_grid_start_ns": int(grid_ns[0]),
        "t_grid_end_ns": int(grid_ns[1]),
        "t_grid_span_seconds": float((grid_ns[1] - grid_ns[0]) / 1e9),
        "tape_margin_seconds": float(margin_ns / 1e9),
        "n_prints_in_read_window": n_raw,
        "read_window_start_ns": int(keep_ns[0]),
        "read_window_end_ns": int(keep_ns[1]),
        "context_seconds": spec.get("context_seconds"),
        "window_deviation_from_brief": spec.get("window_deviation_from_brief"),
        "n_arrivals_after_tie_collapse": int(arr.size),
        "n_ties_collapsed": int(n_raw - arr.size),
        "n_intervals": int(ev_s.size),
        "origin_ns": origin,
        "seconds_elapsed": round(elapsed, 2),
        "seconds_per_event_budgeted": spec.get("measured_cost_seconds_per_event"),
        "nan_share": {k: float(np.isnan(f[k]).mean()) for k in ("m", "dm", "lograte", "dlograte")},
        "n_eff_below_floor_share": float((f["n_eff"] < fcfg["neff_min"]).mean()),
        "neff_rule": fcfg["neff_rule"],
    }
    return df, prov


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--event", default=DEFAULT_EVENT)
    p.add_argument("--out", default="results/scale_field/artifacts")
    args = p.parse_args()

    cfg = adapter.load_config()
    chash = adapter.config_hash()
    cohort = load_cohort(cfg)                 # asserts the frozen hash
    det = load_detection(cfg)

    row = cohort[cohort["event_id"] == args.event]
    if row.empty:
        raise SystemExit(f"{args.event} is not in the frozen cohort manifest")
    row = row.iloc[0]
    d = det[det["event_id"] == args.event]
    if d.empty or not np.isfinite(d["anchor_ns"].iloc[0]):
        raise SystemExit(f"{args.event} has no D7 detection anchor at threshold "
                         f"{cfg['detection_anchor']['threshold']}; the fine band has "
                         f"no centre. Pick an event that crosses.")
    anchor_ns = int(d["anchor_ns"].iloc[0])
    ev_segment = str(d["segment"].iloc[0])

    ts, meta = load_event_prints_meta(args.event, None, cfg)
    print(f"{args.event}  segment {ev_segment}  {meta['n_prints']} prints  "
          f"{meta['n_tied_prints']} tied  min gap {meta['min_nonzero_gap_ns']} ns")

    sa = cfg["scale_axis"]
    session_span = (meta["window_end_ns"] - meta["window_start_ns"]) / 1e9
    half = cfg["scale_axis"]["fine"]["coverage_seconds"]

    frames, prov = [], []
    df_c, pv_c = run_band(ts, "coarse", sa["coarse"], cfg, None)
    frames.append(df_c); prov.append(pv_c)
    print(f"  coarse {pv_c['n_scales']} scales  {pv_c['seconds_elapsed']}s  "
          f"NaN share dlograte {pv_c['nan_share']['dlograte']:.2f} / dm {pv_c['nan_share']['dm']:.2f}")

    df_f, pv_f = run_band(ts, "fine", sa["fine"], cfg,
                          (anchor_ns - int(half * 1e9), anchor_ns + int(half * 1e9)))
    frames.append(df_f); prov.append(pv_f)
    print(f"  fine   {pv_f['n_scales']} scales  {pv_f['seconds_elapsed']}s  "
          f"NaN share dlograte {pv_f['nan_share']['dlograte']:.2f} / dm {pv_f['nan_share']['dm']:.2f}")

    out_dir = rel(args.out)
    os.makedirs(out_dir, exist_ok=True)
    field_df = pd.concat(frames, ignore_index=True)
    field_df.to_parquet(os.path.join(out_dir, f"field_{args.event}.parquet"), index=False)
    adapter.load_event_tape(args.event, None, cfg).to_parquet(
        os.path.join(out_dir, f"tape_{args.event}.parquet"), index=False)

    # v3's own curve for this event, on this event -- the prediction the scale axis is
    # read against. Recomputed here rather than joined so the chart is self-contained;
    # it is the same call the reconciliation gate proved bit-exact against v3.
    lo, hi = meta["window_start_ns"], meta["window_end_ns"]
    ts_rel = (ts - lo).astype(np.float64) / 1e9
    lad = cfg["reconciliation"]["ladder"]
    allan_rows = []
    for e in range(lad["min_exponent"], lad["max_exponent"] + 1):
        T = lad["base_seconds"] * 2.0 ** e
        A, n_pairs = allan_factor(ts_rel, T, t_start=0.0, t_end=(hi - lo) / 1e9,
                                  min_windows=cfg["reconciliation"]["min_windows_for_a_rung"])
        allan_rows.append({"T": T, "log2_T": float(e), "allan": A, "n_pairs": n_pairs})
    pd.DataFrame(allan_rows).to_parquet(
        os.path.join(out_dir, f"allan_{args.event}.parquet"), index=False)

    manifest = {
        "task": "one event, both bands, both channels (order of work step 3)",
        "config_hash": chash,
        "event_id": args.event,
        "event_chosen_because": DEFAULT_EVENT_WHY if args.event == DEFAULT_EVENT else "operator choice",
        "cohort_group": str(row["cohort_group"]),
        "pooled": bool(row["pooled"]),
        "cohort_content_hash": cfg["cohort"]["content_hash"],
        "cohort_hash_asserted": True,
        "detection_anchor": {
            "artifact": cfg["detection_anchor"]["artifact"],
            "threshold": cfg["detection_anchor"]["threshold"],
            "poll_interval_seconds": cfg["detection_anchor"]["poll_interval_seconds"],
            "anchor_ns": anchor_ns,
            "event_segment": ev_segment,
            "rule": "REUSED, NOT RE-DERIVED (D7)",
        },
        "tape": {k: meta[k] for k in
                 ("n_prints", "n_unique_timestamps", "n_tied_prints",
                  "min_nonzero_gap_ns", "span_seconds", "n_files",
                  "has_repair_sibling", "window_start_ns", "window_end_ns")},
        "session_span_seconds": session_span,
        "coarse_cap_seconds": session_span / 8.0,
        "coarse_cap_rule": sa["coarse_cap_rule"],
        "coarse_ceiling_under_cap": bool(sa["coarse"]["max_seconds"] <= session_span / 8.0),
        "hard_floor_seconds": sa["hard_floor_seconds"],
        "bands": prov,
        "tie_variant": cfg["field"]["tie_variant"],
        "thresholds_applied": "NONE. No standardisation against the Poisson null on "
                              "this data -- see poisson_null in config/scale_field.json. "
                              "Matched-null thresholds are step 5.",
        "v3_prediction": cfg["reconciliation"]["v3_knees_seconds"],
        "v3_prediction_role": cfg["reconciliation"]["v3_knees_role"],
        "reconciliation_gate": "results/scale_field/artifacts/reconcile_allan.json",
        "source": "research/scale_field/run_field_one_event.py:main",
        "reproduce": f".venv/Scripts/python.exe research/scale_field/run_field_one_event.py --event {args.event}",
    }
    with open(os.path.join(out_dir, f"field_{args.event}_manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nsession span {session_span:.0f} s   coarse cap (span/8) "
          f"{session_span/8:.0f} s   ceiling {sa['coarse']['max_seconds']:.0f} s "
          f"{'under' if manifest['coarse_ceiling_under_cap'] else 'OVER'} the cap")
    print(f"wrote {out_dir}/field_{args.event}.parquet  ({len(field_df)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
