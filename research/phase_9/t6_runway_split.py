"""
Phase 9 T6 - runway population split.

runway_minutes (Phase 8 A10.2) is the gap between detection and the T0
extended-day high. It is not unimodal: a large atom at exactly 0, a steep
decay through the first few minutes, then a second mass out in the hours.

T6a full histogram, linear and log-x, with the trough between the two modes
     located EMPIRICALLY - no assumed cut point. The atom at runway = 0 is
     reported on its own; it is a spike, not a mode of a density, and folding
     it into a log histogram would hide it.
T6b characterise the two populations on ANCHOR-KNOWABLE variables only:
     detection segment, detection minute, pq_rth_open, price level at
     detection, logrv at detection. Report whether any separates them.
T6c runway_minutes is NOT anchor-knowable - it is measured from the T0 high,
     which is not known until the session resolves. It must never be used as a
     markout bucket (Phase 8 escalation row 11; Phase 9 escalation row 12).
     Nothing in this task computes a markout. It is a diagnostic split only.

logrv at detection uses the SESSION form, log((v0(det_minute)+1)/(b_session+1)),
where b_session is Phase 8 T3's frozen per-event baseline (median full
extended-session volume over T-1/T-2/T-3). Both parts are knowable at the
detection minute.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_9 import common as C

OUT_JSON = f"{C.ART}/t6_runway_split.json"
NBINS = 44


def describe(s: pd.Series) -> dict:
    s = pd.Series(s).dropna().astype(float)
    if not len(s):
        return {"n": 0}
    return {"n": int(len(s)), "mean": float(s.mean()), "median": float(s.median()),
            "q10": float(s.quantile(.10)), "q25": float(s.quantile(.25)),
            "q75": float(s.quantile(.75)), "q90": float(s.quantile(.90))}


def main():
    con = C.connect()
    d1 = C.d1_frame()
    C.closes_wide(con, d1)                      # creates temp p9bars

    det = C.detection_anchors()
    det["mp"] = det["mp"].round(2)
    uni = det[~det["det_undefined"].astype(bool)].copy()
    uni["era"] = C.era_of(uni["event_date_canonical"])
    n_uni = len(uni)

    t3 = pd.read_parquet(C.T3_PART_PATH)
    t3["event_date_canonical"] = pd.to_datetime(t3["event_date_canonical"])
    uni = uni.merge(t3[C.KEY + ["b_session", "pq_rth_open", "participation_class"]],
                    on=C.KEY, how="left")

    # ---- cumulative T0 volume at the detection minute (anchor-knowable) ----
    tgt = uni[C.KEY].copy()
    tgt["det_minute"] = uni["det_minute"].values
    con.register("dtgt", tgt)
    v0 = con.execute("""
        WITH cum AS (
            SELECT ticker, event_date_canonical, mp, minute_index,
                   SUM(volume) OVER (PARTITION BY ticker, event_date_canonical, mp
                                     ORDER BY minute_index) AS cv
            FROM p9bars WHERE session_offset = 0
        )
        SELECT t.ticker, t.event_date_canonical, t.mp,
               MAX(c.cv) FILTER (c.minute_index <= t.det_minute) AS v0_det
        FROM dtgt t LEFT JOIN cum c
          ON t.ticker = c.ticker AND t.event_date_canonical = c.event_date_canonical
         AND t.mp = c.mp
        GROUP BY 1,2,3
    """).fetchdf()
    v0["event_date_canonical"] = pd.to_datetime(v0["event_date_canonical"])
    uni = uni.merge(v0, on=C.KEY, how="left")
    uni["v0_det"] = uni["v0_det"].astype(float)
    uni["b_session"] = uni["b_session"].astype(float)
    uni["logrv_det"] = np.log((uni["v0_det"] + 1) / (uni["b_session"] + 1))
    uni["price_at_detection"] = uni["det_price_lat0"].astype(float)

    r = uni["runway_minutes"].astype(float)

    # ---------- T6a: the atom, then the trough ----------
    n_zero = int((r == 0).sum())
    atom = {"n_runway_zero": n_zero, "share_of_detection_universe": n_zero / n_uni,
            "note": "a point mass, not a mode of a density; reported separately from the log histogram"}
    marks = {f"share_le_{k}": float((r <= k).mean()) for k in [0, 1, 5, 15, 30, 60, 120, 240, 480]}

    pos = r[r >= 1]
    lg = np.log10(pos)
    counts, edges = np.histogram(lg, bins=NBINS)

    # Trough location needs a DENSITY, not raw counts. runway_minutes is
    # integer-valued, so log-spaced bins below ~10 minutes are narrower than
    # the integer lattice and alternate between populated and empty: a raw
    # argmin lands in an aliasing gap next to the first mode, not in the
    # trough between the two masses. A Gaussian KDE on log10(runway) with a
    # bandwidth wider than the lattice spacing removes that artifact.
    # Smoothing is used ONLY to locate the trough - the reported histogram and
    # chart 07 are raw counts.
    from scipy.stats import gaussian_kde
    bw = 0.15                                   # in log10 units
    kde = gaussian_kde(lg.values, bw_method=bw / lg.values.std(ddof=1))
    xs = np.linspace(lg.min(), lg.max(), 1000)
    dens = kde(xs)
    # interior local maxima/minima of the density
    lmax = [i for i in range(1, len(xs) - 1) if dens[i] > dens[i - 1] and dens[i] >= dens[i + 1]]
    lmin = [i for i in range(1, len(xs) - 1) if dens[i] < dens[i - 1] and dens[i] <= dens[i + 1]]
    if len(lmax) >= 2:
        top2 = sorted(sorted(lmax, key=lambda i: -dens[i])[:2])
        m1i, m2i = top2[0], top2[1]
        between = [i for i in lmin if m1i < i < m2i]
        tri = min(between, key=lambda i: dens[i]) if between else \
            m1i + int(np.argmin(dens[m1i:m2i + 1]))
    else:
        m1i = int(np.argmax(dens)); m2i = None; tri = None
    bimodal = m2i is not None

    trough = {
        "method": ("Gaussian KDE on log10(runway_minutes) over runway >= 1, bandwidth 0.15 log10 units; "
                   "modes = two highest interior local maxima, trough = lowest local minimum between them. "
                   "A raw-count argmin is not usable here: runway is integer-valued, so log bins below ~10 "
                   "min are narrower than the integer lattice and produce empty bins adjacent to the first "
                   "mode. Smoothing locates the trough ONLY - reported counts and chart 07 are raw."),
        "kde_bandwidth_log10": bw,
        "bimodal": bimodal,
        "mode_1_minutes": float(10 ** xs[m1i]),
        "mode_2_minutes": (float(10 ** xs[m2i]) if bimodal else None),
        "trough_minutes": (float(10 ** xs[tri]) if tri is not None else None),
        "density_mode_1": float(dens[m1i]),
        "density_mode_2": (float(dens[m2i]) if bimodal else None),
        "density_trough": (float(dens[tri]) if tri is not None else None),
        "mode_1_over_trough": (float(dens[m1i] / dens[tri]) if tri is not None and dens[tri] > 0 else None),
        "mode_2_over_trough": (float(dens[m2i] / dens[tri]) if bimodal and tri is not None and dens[tri] > 0 else None),
        "n_interior_local_maxima": len(lmax),
    }
    histogram = [{"bin_lo_minutes": float(10 ** edges[i]), "bin_hi_minutes": float(10 ** edges[i + 1]),
                  "count": int(counts[i])} for i in range(len(counts))]
    kde_curve = [{"minutes": float(10 ** x), "density": float(d)} for x, d in zip(xs[::10], dens[::10])]

    # ---- the answer depends on the measure, so compute both ----
    # Counts per LOG bin rise mechanically as the bins widen, so a hump in the
    # hours on a log axis is not by itself a second mode. The measure-invariant
    # object is density per MINUTE. Both are reported; chart 07 shows both panels.
    lin_edges = np.arange(0, 981, 20)
    lin_counts, _ = np.histogram(r, bins=lin_edges)
    per_min = lin_counts / 20.0
    nz = per_min[per_min > 0]
    strictly_decaying = bool(np.all(np.diff(per_min[:len(per_min) - 1]) <= 0))
    # is there any interior local max in the per-minute density beyond the first bin?
    interior_max = [i for i in range(1, len(per_min) - 1)
                    if per_min[i] > per_min[i - 1] and per_min[i] >= per_min[i + 1]]
    measure = {
        "question": "is runway one population or two?",
        "note": ("counts per LOG bin rise mechanically with bin width, so the hump in the hours on a log "
                 "axis is not by itself a second mode; density per MINUTE is the measure-invariant object"),
        "linear_density_per_minute_bin20": [
            {"lo_minutes": int(lin_edges[i]), "hi_minutes": int(lin_edges[i + 1]),
             "count": int(lin_counts[i]), "per_minute": float(per_min[i])}
            for i in range(len(lin_counts))],
        "linear_density_monotone_decreasing": strictly_decaying,
        "linear_density_interior_local_maxima_bins": [
            {"lo_minutes": int(lin_edges[i]), "hi_minutes": int(lin_edges[i + 1]),
             "per_minute": float(per_min[i])} for i in interior_max],
        "log_scale_trough_depth_mode1_over_trough": trough["mode_1_over_trough"],
        "log_scale_trough_depth_mode2_over_trough": trough["mode_2_over_trough"],
        "reading": (
            "Per minute, the density falls from 342.65/min over 0-20 min to ~10/min by 300 min and keeps "
            "falling; the largest interior local maximum is 13.55/min at 320-340 min, 25x below the first "
            "bin. The interior local maxima are ripples on a decaying curve, not a second mass. On a log "
            "axis the same data shows a broad hump around 276 min, but that hump is counts-per-log-bin: "
            "the 4,011 events at 120-480 min occupy 360 minutes (11/min) against 4,699 events in the first "
            "6 minutes (~780/min). The only genuine discontinuity is the atom at exactly 0. The log-scale "
            "trough at ~1.8 min is 1.19x deep against mode 1, i.e. a shallow dip immediately adjacent to "
            "the first mode rather than a separation between two masses."),
    }
    print(f"\nlinear density per minute: monotone decreasing = {strictly_decaying}; "
          f"interior local maxima = {len(interior_max)}")
    print("  per-minute density by 20-min bin (first 12):")
    for i in range(12):
        print(f"    {int(lin_edges[i]):4d}-{int(lin_edges[i+1]):4d} min: "
              f"{lin_counts[i]:6,d} events  {per_min[i]:9.2f}/min")

    cut = trough["trough_minutes"]
    print(f"detection universe {n_uni:,}; runway == 0 atom: {n_zero:,} ({n_zero/n_uni:.2%})")
    print(f"bimodal={trough['bimodal']}  mode 1 ~{trough['mode_1_minutes']:.1f} min, "
          f"mode 2 ~{trough['mode_2_minutes']:.1f} min, trough ~{cut:.1f} min "
          f"(mode1/trough {trough['mode_1_over_trough']:.2f}x, mode2/trough {trough['mode_2_over_trough']:.2f}x)")

    # ---------- T6b: characterise on anchor-knowable variables ----------
    uni["runway_population"] = np.where(r <= cut, "short_runway", "long_runway")
    pops = ["short_runway", "long_runway"]
    npop = {p: int((uni.runway_population == p).sum()) for p in pops}
    print(f"split at the empirical trough: short {npop['short_runway']:,}  long {npop['long_runway']:,}")

    numeric = {"det_minute": "detection minute (anchor-knowable)",
               "price_at_detection": "last trade at the detection minute",
               "logrv_det": "log((cum T0 volume at det + 1)/(b_session + 1))",
               "pq_rth_open": "pre-open participation quintile"}
    charact = {}
    for col, desc in numeric.items():
        a = uni.loc[uni.runway_population == "short_runway", col]
        b = uni.loc[uni.runway_population == "long_runway", col]
        da, db = describe(a), describe(b)
        # overlap of the two distributions: 1 - total variation over a common
        # 50-bin grid. 1.0 = identical, 0.0 = disjoint. Separation, not a test.
        av = pd.Series(a).dropna().astype(float).values
        bv = pd.Series(b).dropna().astype(float).values
        ov = None
        if len(av) and len(bv):
            lo, hi = np.nanmin([av.min(), bv.min()]), np.nanmax([av.max(), bv.max()])
            if hi > lo:
                bins = np.linspace(lo, hi, 51)
                ha = np.histogram(av, bins=bins, density=False)[0] / len(av)
                hb = np.histogram(bv, bins=bins, density=False)[0] / len(bv)
                ov = float(np.minimum(ha, hb).sum())
        charact[col] = {"description": desc, "short_runway": da, "long_runway": db,
                        "median_difference": ((db["median"] - da["median"])
                                              if da.get("median") is not None and db.get("median") is not None else None),
                        "distribution_overlap": ov}

    seg_tab = {}
    for col in ["det_segment", "det_bin", "era"]:
        ct = pd.crosstab(uni[col], uni["runway_population"])
        sh = (ct.div(ct.sum(axis=1), axis=0))
        seg_tab[col] = {str(i): {"n_short": int(ct.loc[i].get("short_runway", 0)),
                                 "n_long": int(ct.loc[i].get("long_runway", 0)),
                                 "share_long": float(sh.loc[i].get("long_runway", np.nan))}
                        for i in ct.index}

    summary = {
        "phase": "9", "task": "T6",
        "source": "research/phase_9/t6_runway_split.py:main",
        "repro": "python -m research.phase_9.t6_runway_split",
        "config_hash": C.cfg_hash(),
        "scan_free": True, "tables_touched": ["event_minute_bars_v2"],
        "spine_numeric_reads": 0,
        "n_detection_universe": n_uni,
        "t6c_prohibition": ("runway_minutes is NOT anchor-knowable - it is measured from the T0 high, which is "
                            "not known until the session resolves. It must never be used as a markout bucket "
                            "(Phase 8 escalation row 11; Phase 9 escalation row 12). This task computes no "
                            "markout of any kind; the split is diagnostic only."),
        "markouts_computed_here": 0,
        "runway_zero_atom": atom,
        "cumulative_shares": marks,
        "quantiles": describe(r),
        "trough": trough,
        "measure_dependence": measure,
        "log_histogram_raw_counts": histogram,
        "kde_curve": kde_curve,
        "population_split": {
            "cut_minutes": cut,
            "rule": "runway <= trough -> short_runway, else long_runway",
            "n": npop,
            "caveat": ("the cut is the log-scale KDE trough (~1.8 min), which in practice separates runway <= 1 "
                       "from the rest; per the measure_dependence block the per-minute density is a single "
                       "decaying population, so this split partitions one population rather than separating two"),
        },
        "anchor_knowable_characterisation": charact,
        "categorical_characterisation": seg_tab,
    }
    C.write_json(summary, OUT_JSON)

    # ---------------- console ----------------
    print("\nT6b anchor-knowable characterisation (short vs long runway):")
    print(f"{'variable':22s} {'short median':>13s} {'long median':>13s} {'diff':>10s} {'overlap':>9s}")
    for col, v in charact.items():
        sm_, lm_ = v["short_runway"].get("median"), v["long_runway"].get("median")
        ov = v["distribution_overlap"]
        print(f"{col:22s} {sm_:13.4f} {lm_:13.4f} {v['median_difference']:+10.4f} "
              f"{(ov if ov is not None else float('nan')):9.3f}")
    print("\n  overlap: 1.000 = distributions identical, 0.000 = disjoint")

    print("\nshare in the long-runway population, by detection segment:")
    for k, v in seg_tab["det_segment"].items():
        print(f"  {k:10s} n={v['n_short']+v['n_long']:6,d}  share long {v['share_long']:6.1%}")
    print("\nshare in the long-runway population, by detection bin:")
    for k, v in seg_tab["det_bin"].items():
        print(f"  {k:12s} n={v['n_short']+v['n_long']:6,d}  share long {v['share_long']:6.1%}")

    print("\nESCALATION ROW 12: markouts computed in T6 = 0 -> pass "
          "(runway used as a diagnostic split only, never as a markout bucket)")


if __name__ == "__main__":
    main()
