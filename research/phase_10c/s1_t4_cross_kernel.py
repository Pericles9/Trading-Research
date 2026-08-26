"""
Phase 10c Stage 1, T4 -- cross-kernel interpretation. No combining rule, no single
per-event number -- kernels are read side by side throughout.

T4a  threshold location vs. kernel window size, per event
T4b  void parameter strength by kernel, per event
T4c  heterogeneity: does the best-separated kernel covary with event size, segment,
     or detection price decile

threshold_seconds_median and void are variant-independent for label=='ok' cells (the
sub-burst math never reads the variant -- see s1_t1_subbursts.py's design note), so
this script works from a single deduped per-(event, kernel) view rather than
re-showing the same value three times under three variant labels. Verified below,
not assumed.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t4_cross_kernel.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
KERNELS = [2.0, 8.0, 32.0]
VARIANTS = [1.25, 1.30, 1.35]


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))

    # -------- verify variant-independence of threshold/void for label=='ok' cells
    ok = cells[cells.label == "ok"]
    piv_thr = ok.pivot_table(index=["ticker", "event_date_canonical", "kernel_min"],
                             columns="threshold", values="threshold_seconds_median")
    piv_void = ok.pivot_table(index=["ticker", "event_date_canonical", "kernel_min"],
                              columns="threshold", values="void")
    max_thr_spread = (piv_thr.max(axis=1) - piv_thr.min(axis=1)).max()
    max_void_spread = (piv_void.max(axis=1) - piv_void.min(axis=1)).max()
    assert max_thr_spread < 1e-9, f"threshold_seconds_median varies by variant: {max_thr_spread}"
    assert max_void_spread < 1e-9, f"void varies by variant: {max_void_spread}"

    # -------- dedup to one row per (event, kernel); coalesce segment across variants
    # (prefer 1.25's label, else 1.30's, else 1.35's -- an event unlabelled at the
    # lower threshold may still be labelled at a higher one, per the population table)
    seg_pref = (cells.pivot_table(index=["ticker", "event_date_canonical", "kernel_min"],
                                  columns="threshold", values="segment", aggfunc="first"))
    def coalesce(row):
        for v in VARIANTS:
            if v in row.index and pd.notna(row[v]):
                return row[v]
        return None
    seg_coalesced = seg_pref.apply(coalesce, axis=1).rename("segment")

    per_event_kernel = (cells.drop_duplicates(["ticker", "event_date_canonical", "kernel_min"])
                       [["ticker", "event_date_canonical", "kernel_min", "label",
                         "threshold_seconds_median", "void", "n_intervals"]]
                       .set_index(["ticker", "event_date_canonical", "kernel_min"]))
    # take the label/threshold/void from whichever variant is 'ok' if any is (dedup
    # above may have kept a non-'ok' row first for an event that's 'ok' under another
    # variant's cell -- rebuild properly from the ok-priority view)
    ok_priority = (cells.sort_values("label", key=lambda s: s.eq("ok"), ascending=False)
                  .drop_duplicates(["ticker", "event_date_canonical", "kernel_min"])
                  [["ticker", "event_date_canonical", "kernel_min", "label",
                    "threshold_seconds_median", "void", "n_intervals"]]
                  .set_index(["ticker", "event_date_canonical", "kernel_min"]))
    pek = ok_priority.join(seg_coalesced).reset_index()

    # -------- T4c covariates: event size (n_intervals, kernel-invariant per event) and
    # detection price (nearest tick price to the 1.25 anchor, tick-derived -> not D4-quarantined)
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    price_rows = []
    for r in dev.itertuples(index=False):
        row = det[(det.ticker == r.ticker) & (det.event_date_canonical == r.event_date_canonical)
                 & (np.isclose(det.threshold, 1.25))]
        if not len(row) or pd.isna(row.iloc[0].det_ns_poll0):
            price_rows.append({"ticker": r.ticker, "event_date_canonical":
                               r.event_date_canonical, "price_at_detection": np.nan})
            continue
        det_ns = int(row.iloc[0].det_ns_poll0)
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            price_rows.append({"ticker": r.ticker, "event_date_canonical":
                               r.event_date_canonical, "price_at_detection": np.nan})
            continue
        ts = s0["sip_timestamp"].to_numpy()
        idx = np.argmin(np.abs(ts.astype(np.int64) - det_ns))
        price_rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                          "price_at_detection": float(s0["price"].to_numpy()[idx])})
    price_df = pd.DataFrame(price_rows)
    price_df["price_decile"] = pd.qcut(price_df.price_at_detection.rank(method="first"),
                                       10, labels=False, duplicates="drop")

    pek = pek.merge(price_df, on=["ticker", "event_date_canonical"], how="left")
    pek.to_parquet(rel(f"{ART}/s1_t4_per_event_kernel.parquet"), index=False)

    # -------- T4b: best-separated kernel per event (highest void among 'ok' kernels)
    ok_pek = pek[pek.label == "ok"]
    best = (ok_pek.loc[ok_pek.groupby(["ticker", "event_date_canonical"]).void.idxmax()]
           [["ticker", "event_date_canonical", "kernel_min", "void", "segment",
             "n_intervals", "price_decile"]]
           .rename(columns={"kernel_min": "best_kernel_min"}))
    n_kernels_ok = ok_pek.groupby(["ticker", "event_date_canonical"]).kernel_min.nunique()
    best = best.merge(n_kernels_ok.rename("n_kernels_ok"), on=["ticker", "event_date_canonical"])
    best.to_parquet(rel(f"{ART}/s1_t4b_best_kernel.parquet"), index=False)

    # -------- T4a: flat vs ~1:1 scaling -- per-event correlation of log(threshold) vs log(kernel)
    slopes = []
    for (tk, ed), g in ok_pek.groupby(["ticker", "event_date_canonical"]):
        g = g.dropna(subset=["threshold_seconds_median"])
        if len(g) < 2:
            continue
        x = np.log(g.kernel_min.to_numpy())
        y = np.log(g.threshold_seconds_median.to_numpy())
        if np.ptp(x) == 0:
            continue
        slope = np.polyfit(x, y, 1)[0]
        slopes.append({"ticker": tk, "event_date_canonical": ed, "n_kernels": len(g),
                       "log_log_slope": float(slope)})
    slopes_df = pd.DataFrame(slopes)
    slopes_df.to_parquet(rel(f"{ART}/s1_t4a_slopes.parquet"), index=False)

    # -------- T4c heterogeneity: does best_kernel covary with size/segment/price decile
    best["best_kernel_ordinal"] = best.best_kernel_min.map({2.0: 0, 8.0: 1, 32.0: 2})
    rho_size, p_size = spearmanr(best.best_kernel_ordinal, best.n_intervals)
    valid_pd = best.dropna(subset=["price_decile"])
    rho_price, p_price = spearmanr(valid_pd.best_kernel_ordinal, valid_pd.price_decile)
    by_segment = (best.groupby("segment", dropna=False).best_kernel_min
                 .value_counts(dropna=False).unstack(fill_value=0))

    out = {
        "phase": "10c", "stage": "1", "task": "T4_cross_kernel", "config_hash": chash,
        "variant_independence_verified": {
            "max_threshold_spread_across_variants": float(max_thr_spread),
            "max_void_spread_across_variants": float(max_void_spread),
            "note": "both < 1e-9 -- confirms threshold_seconds_median and void never depend on "
                   "the threshold variant, only on (event, kernel), as designed.",
        },
        "T4a_slope_distribution": {
            "n_events": int(len(slopes_df)),
            "median_slope": float(slopes_df.log_log_slope.median()),
            "p25_slope": float(slopes_df.log_log_slope.quantile(0.25)),
            "p75_slope": float(slopes_df.log_log_slope.quantile(0.75)),
            "share_near_zero_lt_0.2": float((slopes_df.log_log_slope.abs() < 0.2).mean()),
            "share_near_one_gt_0.8": float((slopes_df.log_log_slope.abs() > 0.8).mean()),
            "reading": ("A slope near 0 means threshold location is FLAT across kernel widths "
                       "(a real structural interval). A slope near 1 means the threshold scales "
                       "with the kernel (the local-median window is setting the threshold, the "
                       "multi-kernel form of the free-parameter problem). Reported as a "
                       "distribution below; not characterized further -- the read is Cooper's."),
        },
        "T4b_best_kernel_distribution": {
            "n_events_with_at_least_one_ok_kernel": int(len(best)),
            "counts": best.best_kernel_min.value_counts().to_dict(),
            "n_kernels_ok_distribution": best.n_kernels_ok.value_counts().sort_index().to_dict(),
        },
        "T4c_heterogeneity": {
            "best_kernel_vs_event_size_n_intervals": {"spearman_rho": float(rho_size),
                                                       "p_value": float(p_size), "n": int(len(best))},
            "best_kernel_vs_detection_price_decile": {"spearman_rho": float(rho_price),
                                                      "p_value": float(p_price),
                                                      "n": int(len(valid_pd))},
            "best_kernel_by_segment": by_segment.to_dict(),
            "note": ("price_at_detection is the nearest TICK price to the 1.25-variant anchor "
                     "(not a spine numeric -- D4 quarantine does not apply). Descriptive only, no "
                     "threshold, no characterization beyond the correlation figures themselves."),
        },
        "source": "research/phase_10c/s1_t4_cross_kernel.py:main",
    }
    c10c.write_json(rel(f"{ART}/s1_t4_summary.json"), out)

    print(f"variant-independence check: max thr spread {max_thr_spread:.2e}, "
          f"max void spread {max_void_spread:.2e}")
    print(f"\nT4a log-log slope: median {out['T4a_slope_distribution']['median_slope']:.3f} "
          f"(p25 {out['T4a_slope_distribution']['p25_slope']:.3f}, "
          f"p75 {out['T4a_slope_distribution']['p75_slope']:.3f})  n={len(slopes_df)}")
    print(f"\nT4b best kernel counts: {out['T4b_best_kernel_distribution']['counts']}")
    print(f"\nT4c best_kernel vs n_intervals: rho={rho_size:.3f} p={p_size:.3f}")
    print(f"T4c best_kernel vs price_decile: rho={rho_price:.3f} p={p_price:.3f} n={len(valid_pd)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
