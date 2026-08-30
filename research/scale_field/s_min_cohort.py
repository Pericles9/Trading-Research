"""
Step 1 of Cooper's recommended order: the resolution floor across all 100 events.

    n_eff = 2*sqrt(pi) * s * lambda >= 8   =>   s >= 2.2568 / lambda

That is not adopted from anywhere. It is the effective-sample-size definition already
in the estimator, rearranged. Below s_min(t) nothing is measurable at any output
resolution, on any chart, by this method.

WHY THIS RUN IS CHEAP. It needs a print count and a session span, and both are already
in committed artifacts: `t0_print_count` on the frozen cohort manifest and the D3
extended-day span from the pinned XNYS calendar. **No field computation. No tick pass.
No new dependency.** It answers, for all 100 events at once, which band each event can
support.

THREE RATES, AND THEY ARE NOT INTERCHANGEABLE. A single lambda per event hides the
thing that matters, so all three are reported side by side and every table says which
one it is on:

  lambda_session   t0_print_count / extended-day span (57,600 s, or less on an early
                   close). ARTIFACT-ONLY -- this is the figure Cooper's step 1 asks
                   for. Conservative: it counts the dead premarket hours, so it
                   understates lambda and overstates s_min.
  lambda_active    t0_print_count / (last print - first print). Needs the timestamps.
  s_min quantiles  from a k-NN local rate (k=20) evaluated on a uniform grid across
                   the session. This is the honest object -- s_min is a FUNCTION of
                   time, not a scalar, and an event can support a band over part of
                   its session and not the rest.

The last two need a targeted per-event read (`--tick-detail`), which is the same read
the reconciliation gate already does: zero passes over filtered_trades / filtered_quotes,
measured at ~20 s for all 114 events. It is off by default so the artifact-only figure
Cooper specified stands on its own.

ADMISSIBILITY, stated as an arithmetic consequence and not a decision. An event can
support a band only where s_min(t) clears the band's floor. The shares below are
descriptive. Whether a share becomes a pre-registered gate is Cooper's call, not this
script's.

Usage:
    .venv/Scripts/python.exe research/scale_field/s_min_cohort.py
    .venv/Scripts/python.exe research/scale_field/s_min_cohort.py --tick-detail
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
from adapter import (load_cohort, load_detection, load_event_prints_meta,  # noqa: E402
                     load_event_prints, rel, segment_bounds_ns)
from scale_field import NEFF_S_MIN_COEF, s_min_for_rate  # noqa: E402

OUT_JSON = "results/scale_field/artifacts/s_min_cohort.json"
OUT_PARQUET = "results/scale_field/artifacts/s_min_cohort.parquet"

# The floors each band would have to clear, from config/scale_field.json.
BANDS = {"coarse": 1.0, "fine": 0.015625}

# WINDOWS. The D3 extended session is the WRONG denominator for admissibility and the
# first version of this script used it anyway. "The median event supports the coarse
# band over 2.8% of its session" is dominated by the dead premarket hours; what a
# strategy needs to know is whether the band is supported WHEN IT WOULD BE TRADING,
# which is at and after the D7 detection anchor. D5 fixes that as intraday
# post-trigger, long-only, burst-scale horizons -- so the post-anchor windows are the
# operative ones and the symmetric one is carried for comparison with the fine band's
# read window. Offsets are seconds relative to the anchor; None means the session.
WINDOWS = {
    "session":        None,
    "anchor_pm15min": (-900.0, 900.0),
    "anchor_post15min": (0.0, 900.0),
    "anchor_post300s": (0.0, 300.0),
    "anchor_post60s": (0.0, 60.0),
    "anchor_post10s": (0.0, 10.0),
}
# A window bounds the scale axis from ABOVE as well as improving it from below. The
# estimator masks within edge_scales = 4 kernel widths of each end, so a window of length
# W admits only s < W / 8. That upper bound is what turns "s_min improved six-fold" into
# a USABLE RANGE, which is the quantity that decides whether a continuum buys anything
# over a handful of fixed kernels.
EDGE_SCALES = 4.0
WINDOW_WHY = {
    "session": "the D3 extended day. Conservative and mostly dead time; kept as the "
               "artifact-only baseline, NOT as the admissibility denominator.",
    "anchor_pm15min": "the brief's fine-band read window, symmetric about the anchor.",
    "anchor_post15min": "post-trigger, D5's actual surface.",
    "anchor_post300s": "five minutes -- included because it was tabulated, though it "
                       "does not fit inside a tradeable window at this horizon class.",
    "anchor_post60s": "burst-scale, the horizon class D5 names.",
    "anchor_post10s": "the momentum system's own holding period, order ten seconds.",
}
# Reference marks for the report: the committed sub-burst duration medians (step 2).
SUBBURST_MARKS = {"v4 median": 3.48e-7, "10c s1 median": 1.2941e-3, "10d T4 median": 2.755e-3}


def knn_rate(ts_ns: np.ndarray, grid_ns: np.ndarray, k: int = 20) -> np.ndarray:
    """Local print rate by k-nearest-neighbour spacing. Same estimator the charts use:
    a fixed-width count on a sparse tape swings between zero and a large number, and
    lambda here feeds n_eff, which needs about 8 effective prints."""
    if ts_ns.size < k + 1:
        return np.full(grid_ns.size, np.nan)
    i = np.searchsorted(ts_ns, grid_ns)
    lo = np.clip(i - k // 2, 0, ts_ns.size - 1 - k)
    span = (ts_ns[lo + k] - ts_ns[lo]).astype(np.float64) / 1e9
    return np.where(span > 0, k / span, np.nan)


def _usable(df, wname, off) -> dict:
    """s_min .. s_max for the window, and how many decades that leaves.

    s_max = W / (2 * edge_scales): the estimator blanks within edge_scales kernel widths
    of each end, so a kernel wider than W/8 has no interior left to report. Reported two
    ways because they differ and the difference is not noise:
      * from the MEDIAN EVENT's s_min (the typical event's range)
      * from s_min at the MEDIAN lambda (2.2568 / median lambda) -- Jensen's inequality
        makes these disagree, and quoting one as if it were the other overstates the range.
    """
    W = float(off[1] - off[0])
    s_max = W / (2.0 * EDGE_SCALES)
    col = f"{wname}__s_min_median"
    lam = f"{wname}__lambda"
    if col not in df.columns or not df[col].notna().any():
        return {"n": 0}
    s_min_med_event = float(np.nanmedian(df[col]))
    lam_med = float(np.nanmedian(df[lam]))
    s_min_at_med_lam = float(s_min_for_rate(lam_med))
    out = {"window_seconds": W, "s_max_seconds": s_max,
           "s_max_rule": "W / (2 * edge_scales) = W/8",
           "lambda_median": lam_med,
           "s_min_at_median_lambda": s_min_at_med_lam,
           "s_min_median_across_events": s_min_med_event}
    for tag, smn in (("at_median_lambda", s_min_at_med_lam),
                     ("median_event", s_min_med_event)):
        if smn > 0 and s_max > smn:
            out[f"usable_decades__{tag}"] = float(np.log10(s_max / smn))
            out[f"usable_octaves__{tag}"] = float(np.log2(s_max / smn))
        else:
            out[f"usable_decades__{tag}"] = 0.0
            out[f"usable_octaves__{tag}"] = 0.0
    return out


def q(a, qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> dict:
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), "min": float(a.min()), "max": float(a.max()),
            **{f"q{int(x*100):02d}": float(np.quantile(a, x)) for x in qs}}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tick-detail", action="store_true",
                   help="also compute lambda_active and the within-session s_min(t) "
                        "distribution. Targeted per-event read, zero full-table passes.")
    p.add_argument("--grid-points", type=int, default=2000)
    args = p.parse_args()

    cfg = adapter.load_config()
    cohort = load_cohort(cfg)                  # asserts the frozen hash
    det = load_detection(cfg)
    anchors = {r.event_id: r.anchor_ns for r in det.itertuples(index=False)
               if np.isfinite(r.anchor_ns)}
    c = cohort.merge(det[["event_id", "segment"]], on="event_id", how="left")
    pooled = c[c["pooled"]].copy()
    print(f"cohort {len(cohort)} events, {len(pooled)} pooled, hash asserted OK")

    rows, t0 = [], time.perf_counter()
    for r in pooled.itertuples(index=False):
        b = segment_bounds_ns(r.event_date_canonical)
        span_s = (b["post"][1] - b["premarket"][0]) / 1e9
        n_prints = int(r.t0_print_count)
        lam_session = n_prints / span_s if span_s > 0 else np.nan
        row = {
            "event_id": r.event_id, "ticker": r.ticker,
            "event_date_canonical": r.event_date_canonical,
            "cohort_group": r.cohort_group,
            "segment": r.segment if isinstance(r.segment, str) else "no_detection",
            "t0_print_count": n_prints,
            "session_span_seconds": span_s,
            "lambda_session": lam_session,
            "s_min_session": float(s_min_for_rate(lam_session)),
        }
        if args.tick_detail:
            ts, meta = load_event_prints_meta(r.event_id, None, cfg)
            anchor = anchors.get(r.event_id)
            for wname, off in WINDOWS.items():
                if off is None or anchor is None or ts.size <= 25:
                    continue
                lo = int(anchor + off[0] * 1e9)
                hi = int(anchor + off[1] * 1e9)
                w = ts[(ts >= lo) & (ts < hi)]
                if w.size <= 25:
                    row[f"{wname}__lambda"] = np.nan
                    row[f"{wname}__s_min_median"] = np.nan
                    for b in BANDS:
                        row[f"{wname}__share_{b}"] = np.nan
                    row[f"{wname}__n_prints"] = int(w.size)
                    continue
                grid = np.linspace(lo, hi, args.grid_points).astype(np.int64)
                smw = s_min_for_rate(knn_rate(ts, grid))     # kNN over the FULL tape,
                # evaluated on the window: a window edge must not manufacture a rate drop.
                row[f"{wname}__n_prints"] = int(w.size)
                row[f"{wname}__lambda"] = float(w.size / ((hi - lo) / 1e9))
                row[f"{wname}__s_min_median"] = float(np.nanmedian(smw))
                row[f"{wname}__s_min_q05"] = float(np.nanquantile(smw, 0.05))
                for b, fl in BANDS.items():
                    row[f"{wname}__share_{b}"] = float(np.nanmean(smw <= fl))
            if ts.size > 25:
                active = (ts[-1] - ts[0]) / 1e9
                lam_active = ts.size / active if active > 0 else np.nan
                grid = np.linspace(int(ts[0]), int(ts[-1]), args.grid_points).astype(np.int64)
                sm = s_min_for_rate(knn_rate(ts, grid))
                row.update(
                    n_prints_measured=int(ts.size),
                    active_span_seconds=float(active),
                    lambda_active=float(lam_active),
                    s_min_active=float(s_min_for_rate(lam_active)),
                    s_min_q05=float(np.nanquantile(sm, 0.05)),
                    s_min_q25=float(np.nanquantile(sm, 0.25)),
                    s_min_median=float(np.nanmedian(sm)),
                    s_min_q75=float(np.nanquantile(sm, 0.75)),
                    s_min_q95=float(np.nanquantile(sm, 0.95)),
                    **{f"share_session_below_{k}": float(np.nanmean(sm <= v))
                       for k, v in BANDS.items()},
                )
        rows.append(row)
    df = pd.DataFrame(rows)
    elapsed = time.perf_counter() - t0
    print(f"{len(df)} events in {elapsed:.1f}s")

    # ---------------- summaries
    def by_segment(col):
        return {str(s): q(g[col]) for s, g in df.groupby("segment") if g[col].notna().any()}

    summary = {
        "task": "step 1 -- resolution floor s_min across the analysis cohort",
        "config_hash": adapter.config_hash(),
        "cohort_content_hash": cfg["cohort"]["content_hash"],
        "cohort_hash_asserted": True,
        "n_events": int(len(df)),
        "rule": "n_eff = 2*sqrt(pi)*s*lambda >= 8  =>  s >= 2.2568/lambda. Derived from "
                "the estimator's own effective sample size, not adopted from anywhere.",
        "neff_min": cfg["field"]["neff_min"],
        "coefficient": float(NEFF_S_MIN_COEF),
        "inputs": "t0_print_count (frozen cohort manifest) + D3 extended-day span "
                  "(pinned XNYS calendar). No field computation, no tick pass.",
        "seconds_elapsed": round(elapsed, 1),
        "segment_counts": {str(k): int(v) for k, v in df["segment"].value_counts().items()},
        "lambda_session_prints_per_s": {"pooled": q(df["lambda_session"]),
                                        "by_segment": by_segment("lambda_session")},
        "s_min_session_seconds": {"pooled": q(df["s_min_session"]),
                                  "by_segment": by_segment("s_min_session")},
        "band_floors_seconds": BANDS,
        "admissibility_on_lambda_session": {
            band: {
                "rule": f"s_min_session <= {floor} s, i.e. the event's session-mean rate "
                        f"supports the band's own floor",
                "n_admissible": int((df["s_min_session"] <= floor).sum()),
                "share": round(float((df["s_min_session"] <= floor).mean()), 4),
                "by_segment": {str(s): {"n": int(len(g)),
                                        "n_admissible": int((g["s_min_session"] <= floor).sum()),
                                        "share": round(float((g["s_min_session"] <= floor).mean()), 4)}
                               for s, g in df.groupby("segment")},
            } for band, floor in BANDS.items()},
        "caveat": "lambda_session counts the whole extended day including its dead hours, "
                  "so it UNDERSTATES lambda and OVERSTATES s_min. It is the conservative "
                  "bound and the artifact-only one. Run --tick-detail for lambda_active "
                  "and the within-session distribution.",
        "subburst_reference_marks_seconds": SUBBURST_MARKS,
        "source": "research/scale_field/s_min_cohort.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scale_field/s_min_cohort.py"
                     + (" --tick-detail" if args.tick_detail else ""),
    }
    if args.tick_detail and "lambda_active" in df.columns:
        summary["tick_detail"] = {
            "read": "targeted per-event parquet read, zero passes over filtered_trades",
            "lambda_active_prints_per_s": {"pooled": q(df["lambda_active"]),
                                           "by_segment": by_segment("lambda_active")},
            "s_min_active_seconds": {"pooled": q(df["s_min_active"]),
                                     "by_segment": by_segment("s_min_active")},
            "s_min_within_session_median_seconds": {
                "pooled": q(df["s_min_median"]), "by_segment": by_segment("s_min_median")},
            "s_min_within_session_q05_seconds": {
                "note": "the event's BEST 5% of the session -- its most favourable moment",
                "pooled": q(df["s_min_q05"]), "by_segment": by_segment("s_min_q05")},
            "share_of_session_supporting_band": {
                band: {"pooled": q(df[f"share_session_below_{band}"]),
                       "by_segment": by_segment(f"share_session_below_{band}")}
                for band in BANDS},
            "by_window": {
                wname: {
                    "why": WINDOW_WHY[wname],
                    "offsets_seconds_from_anchor": off,
                    "n_events_with_window": int(df[f"{wname}__lambda"].notna().sum())
                    if f"{wname}__lambda" in df.columns else 0,
                    "lambda_prints_per_s": q(df[f"{wname}__lambda"])
                    if f"{wname}__lambda" in df.columns else {"n": 0},
                    "s_min_median_seconds": q(df[f"{wname}__s_min_median"])
                    if f"{wname}__s_min_median" in df.columns else {"n": 0},
                    "share_of_window_supporting_band": {
                        b: q(df[f"{wname}__share_{b}"])
                        for b in BANDS if f"{wname}__share_{b}" in df.columns},
                    "n_events_median_moment_supports_band": {
                        b: int((df[f"{wname}__s_min_median"] <= fl).sum())
                        for b, fl in BANDS.items()
                        if f"{wname}__s_min_median" in df.columns},
                    "usable_range": _usable(df, wname, off),
                } for wname, off in WINDOWS.items() if off is not None},
            "usable_range_note": "A window bounds the scale axis from ABOVE as well: "
                                 "s < W/8 after the 4-kernel-width edge mask. Inside the "
                                 "operational window the field has roughly ONE DECADE of "
                                 "usable scale range, and in the first ten seconds about "
                                 "two-thirds of a decade -- two octaves. That is the number "
                                 "that decides whether a continuum buys anything over three "
                                 "or four fixed kernels, and it is a challenge to the "
                                 "premise this build started from. See REPORT section 11.",
            "window_note": "The D3 session is NOT the admissibility denominator. It is "
                           "mostly dead time and understates admissibility for the only "
                           "period a strategy would act in. The post-anchor windows are "
                           "the operative ones under D5.",
        }

    os.makedirs(os.path.dirname(rel(OUT_JSON)), exist_ok=True)
    with open(rel(OUT_JSON), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    df.to_parquet(rel(OUT_PARQUET), index=False)

    # ---------------- console
    s = summary["s_min_session_seconds"]
    print(f"\ns_min on lambda_session (artifact-only), seconds:")
    print(f"  pooled n={s['pooled']['n']}  q05={s['pooled']['q05']:.3g}  "
          f"median={s['pooled']['q50']:.3g}  q95={s['pooled']['q95']:.3g}  "
          f"max={s['pooled']['max']:.3g}")
    for seg, v in s["by_segment"].items():
        print(f"  {seg:12s} n={v['n']:3d}  q25={v['q25']:.3g}  median={v['q50']:.3g}  "
              f"q75={v['q75']:.3g}")
    print("\nadmissible on lambda_session:")
    for band, a in summary["admissibility_on_lambda_session"].items():
        print(f"  {band:7s} floor {BANDS[band]:g} s: {a['n_admissible']}/{len(df)} "
              f"({a['share']:.0%})   " +
              "  ".join(f"{k} {vv['n_admissible']}/{vv['n']}" for k, vv in a["by_segment"].items()))
    if args.tick_detail:
        t = summary["tick_detail"]["s_min_within_session_median_seconds"]["pooled"]
        print(f"\nwithin-session median s_min: q05={t['q05']:.3g}  median={t['q50']:.3g}  "
              f"q95={t['q95']:.3g}")
        for band in BANDS:
            sh = summary["tick_detail"]["share_of_session_supporting_band"][band]["pooled"]
            print(f"  share of session supporting {band:7s}: median {sh['q50']:.1%}")
        print("\nBY WINDOW -- the session is the wrong denominator:")
        print(f"  {'window':18s} {'n':>4s} {'lam med':>8s} {'s_min':>8s} "
              f"{'s_max':>8s} {'decades':>8s} {'octaves':>8s} {'coarse ok':>10s}")
        for wname, w in summary["tick_detail"]["by_window"].items():
            lam = w["lambda_prints_per_s"]
            nb = w["n_events_median_moment_supports_band"]
            u = w.get("usable_range", {})
            if not lam.get("n") or not u.get("window_seconds"):
                continue
            print(f"  {wname:18s} {lam['n']:4d} {lam['q50']:8.2f} "
                  f"{u['s_min_at_median_lambda']:8.3g} {u['s_max_seconds']:8.3g} "
                  f"{u['usable_decades__at_median_lambda']:8.2f} "
                  f"{u['usable_octaves__at_median_lambda']:8.1f} "
                  f"{nb['coarse']:6d}/{lam['n']:<3d}")
        print("  (s_min quoted at the MEDIAN lambda; s_max = W/8 after the edge mask)")
    print(f"\nwrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
