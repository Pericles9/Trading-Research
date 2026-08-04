"""
Phase 9 T3 - retracement measurement.

The Phase 8 grid measures markouts from anchors. It never measures how much of
the excursion comes back. This does.

Detection universe (n = 15,369 = D1 minus the 394 det_undefined), with
  A = tick_close_t_minus_1_rth   (D4-clean, frozen from 6b)
  H = day_high_ext               (D4-clean, frozen from 6b)
  p_det = det_price_lat0         (frozen from Phase 8 A10.2)

T3a  retrace_excursion(h)  = (H - p_h) / (H - A),     where H - A > 0
T3b  retrace_detection(h)  = (H - p_h) / (H - p_det), where H - p_det > 0
     0 = still at the high.  1.0 = back to the T-1 RTH close.  >1.0 = below it.
T3c  level-crossing census: share p_h < A, share p_h < p_det, by era and
     detection segment.
T3d  same, with flag_cross_session_extreme carried separately.

T3d note - which flag applies where. The denominator H - A spans the (T-1,T0)
boundary because A is a T-1 price and H is a T0 price. So the (T-1,T0) flag
bears on EVERY horizon including t0_close, not just T+1..T+3. The numerator
p_h additionally spans (T0,T+k) for the three forward horizons. Both
components are reported, and their union:
  flag_cs_denominator  - (T-1,T0) extreme; contaminates H - A at all horizons
  flag_cs_numerator    - (T0,T+k) extreme; contaminates p_h at t1/t2/t3 only
  flag_cs_any          - union, the carry-set for the sensitivity variant

HORIZON CEILING: event_minute_bars_v2 carries offsets -3..+3 only. T+3 is the
hard ceiling. Nothing here extrapolates past it.

Escalation row 8: retrace_excursion denominator undefined > 2% of the
detection universe.
Escalation row 9: retrace_det_undefined share > 25%.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_9 import common as C

FLAGS = f"{C.ART}/t1_cross_session_flags.parquet"
OUT_PARQUET = f"{C.ART}/t3_retracement.parquet"
OUT_JSON = f"{C.ART}/t3_retracement_summary.json"

HORIZONS = ["t0_close", "t1_close", "t2_close", "t3_close"]
HZ_PAIR = {"t0_close": None, "t1_close": "t0_t1", "t2_close": "t0_t2", "t3_close": "t0_t3"}
QS = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def quantiles(s: pd.Series) -> dict:
    s = pd.Series(s).dropna()
    if not len(s):
        return {"n": 0, **{f"q{int(p*100):02d}": None for p in QS}, "mean": None}
    return {"n": int(len(s)), **{f"q{int(p*100):02d}": float(s.quantile(p)) for p in QS},
            "mean": float(s.mean())}


def main():
    con = C.connect()
    d1 = C.d1_frame()
    wide = C.closes_wide(con, d1)

    anc = C.anchor6b()
    det = C.detection_anchors()
    det["mp"] = det["mp"].round(2)

    base = (d1.merge(anc, on=C.KEY, how="left")
              .merge(det[C.KEY + ["det_undefined", "det_segment", "det_bin", "det_minute",
                                  "det_price_lat0", "runway_minutes"]], on=C.KEY, how="left")
              .merge(wide[C.KEY + [f"close_{k}" for k in ["t0", "t1", "t2", "t3"]]],
                     on=C.KEY, how="left"))

    n_d1 = len(base)
    uni = base[~base["det_undefined"].astype(bool)].copy()
    n_uni = len(uni)
    print(f"D1 {n_d1:,} -> detection universe {n_uni:,} (det_undefined dropped: {n_d1 - n_uni:,})")

    uni["A"] = uni["tick_close_t_minus_1_rth"]
    uni["H"] = uni["day_high_ext"]
    uni["p_det"] = uni["det_price_lat0"]
    uni["den_exc"] = uni["H"] - uni["A"]
    uni["den_det"] = uni["H"] - uni["p_det"]
    uni["exc_undefined"] = ~uni["den_exc"].gt(0)
    uni["retrace_det_undefined"] = ~uni["den_det"].gt(0)

    # escalation rows 8 / 9
    n_exc_undef = int(uni["exc_undefined"].sum())
    n_det_undef = int(uni["retrace_det_undefined"].sum())
    row8 = {"condition": "retrace_excursion denominator undefined > 2% of detection universe",
            "n": n_exc_undef, "share": n_exc_undef / n_uni, "threshold": 0.02,
            "triggered": bool(n_exc_undef / n_uni > 0.02),
            "note": "6b denom_nonpositive carried; never imputed",
            "agrees_with_6b_denom_nonpositive": int(
                (uni["exc_undefined"] & uni["denom_nonpositive"].astype(bool)).sum())}
    row9 = {"condition": "retrace_det_undefined share > 25%",
            "n": n_det_undef, "share": n_det_undef / n_uni, "threshold": 0.25,
            "triggered": bool(n_det_undef / n_uni > 0.25)}
    print(f"row 8: exc denominator undefined {n_exc_undef} ({n_exc_undef/n_uni:.4%})")
    print(f"row 9: retrace_det_undefined      {n_det_undef} ({n_det_undef/n_uni:.4%})")

    # ---------- flags ----------
    flags = pd.read_parquet(FLAGS)
    flags["event_date_canonical"] = pd.to_datetime(flags["event_date_canonical"])
    fden = flags[flags.session_pair == "tm1_t0"][C.KEY + ["flag_cross_session_extreme"]].rename(
        columns={"flag_cross_session_extreme": "flag_cs_denominator"})
    uni = uni.merge(fden, on=C.KEY, how="left")
    uni["flag_cs_denominator"] = uni["flag_cs_denominator"].fillna(False).astype(bool)

    # ---------- long per (event, horizon) ----------
    rows = []
    for h in HORIZONS:
        s = uni.copy()
        s["horizon"] = h
        s["p_h"] = s[f"close_{h.split('_')[0]}"]
        pair = HZ_PAIR[h]
        if pair:
            fn = flags[flags.session_pair == pair][C.KEY + ["flag_cross_session_extreme"]].rename(
                columns={"flag_cross_session_extreme": "flag_cs_numerator"})
            s = s.merge(fn, on=C.KEY, how="left")
        else:
            s["flag_cs_numerator"] = False
        s["flag_cs_numerator"] = s["flag_cs_numerator"].fillna(False).astype(bool)
        s["flag_cs_any"] = s["flag_cs_denominator"] | s["flag_cs_numerator"]
        s["horizon_undefined"] = s["p_h"].isna() | ~s["p_h"].gt(0)

        ok = s["p_h"].gt(0)
        s["retrace_excursion"] = np.where(ok & ~s["exc_undefined"],
                                          (s["H"] - s["p_h"]) / s["den_exc"], np.nan)
        s["retrace_detection"] = np.where(ok & ~s["retrace_det_undefined"],
                                          (s["H"] - s["p_h"]) / s["den_det"], np.nan)
        s["below_A"] = np.where(ok, s["p_h"] < s["A"], np.nan)
        s["below_det"] = np.where(ok, s["p_h"] < s["p_det"], np.nan)
        rows.append(s[C.KEY + ["era", "horizon", "det_segment", "det_bin", "det_minute",
                               "runway_minutes", "A", "H", "p_det", "p_h",
                               "den_exc", "den_det", "exc_undefined", "retrace_det_undefined",
                               "horizon_undefined", "retrace_excursion", "retrace_detection",
                               "below_A", "below_det", "flag_cs_denominator",
                               "flag_cs_numerator", "flag_cs_any"]])
    R = pd.concat(rows, ignore_index=True)
    R.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {OUT_PARQUET}  ({len(R):,} rows)")

    # ---------- summaries ----------
    def block(df, label):
        out = {}
        for h in HORIZONS:
            s = df[df.horizon == h]
            out[h] = {
                "n_events": int(len(s)),
                "n_horizon_undefined": int(s["horizon_undefined"].sum()),
                "retrace_excursion": quantiles(s["retrace_excursion"]),
                "retrace_detection": quantiles(s["retrace_detection"]),
                "level_crossing": {
                    "n_defined": int(s["below_A"].notna().sum()),
                    "n_below_A": int(np.nansum(s["below_A"].values)),
                    "share_below_A": (float(np.nanmean(s["below_A"].values))
                                      if s["below_A"].notna().any() else None),
                    "n_below_det": int(np.nansum(s["below_det"].values)),
                    "share_below_det": (float(np.nanmean(s["below_det"].values))
                                        if s["below_det"].notna().any() else None),
                },
            }
        return {"label": label, "horizons": out}

    variants = {
        "all_carried": block(R, "all events, untrimmed - PRIMARY"),
        "cs_flagged_excluded": block(R[~R.flag_cs_any], "flag_cross_session_extreme (either side) excluded"),
        "cs_flagged_only": block(R[R.flag_cs_any], "flag_cross_session_extreme (either side) only"),
    }

    by_era = {e: block(R[R.era == e], f"era {e}") for e in C.ERAS}
    segs = [s for s in R["det_segment"].dropna().unique().tolist()]
    by_seg = {sg: block(R[R.det_segment == sg], f"segment {sg}") for sg in segs}

    # flag composition per horizon
    flag_counts = {h: {
        "n": int((R.horizon == h).sum()),
        "n_flag_denominator": int(R.loc[R.horizon == h, "flag_cs_denominator"].sum()),
        "n_flag_numerator": int(R.loc[R.horizon == h, "flag_cs_numerator"].sum()),
        "n_flag_any": int(R.loc[R.horizon == h, "flag_cs_any"].sum()),
        "share_flag_any": float(R.loc[R.horizon == h, "flag_cs_any"].mean()),
    } for h in HORIZONS}

    waterfall = [
        {"step": "D1 -> detection universe", "rows_in": n_d1, "rows_out": n_uni,
         "dropped": n_d1 - n_uni,
         "why": "det_undefined: tick T0 extended max never reaches 1.30x anchor (Phase 8 A10.3, the 394)"},
        {"step": "detection universe -> retrace_excursion defined", "rows_in": n_uni,
         "rows_out": n_uni - n_exc_undef, "dropped": n_exc_undef,
         "why": "H - A <= 0 (6b denom_nonpositive); carried, own row, never imputed"},
        {"step": "detection universe -> retrace_detection defined", "rows_in": n_uni,
         "rows_out": n_uni - n_det_undef, "dropped": n_det_undef,
         "why": "H - p_det <= 0 (detection print already at the extended-day high); carried as retrace_det_undefined"},
    ]

    summary = {
        "phase": "9", "task": "T3",
        "source": "research/phase_9/t3_retracement.py:main",
        "repro": "python -m research.phase_9.t3_retracement",
        "config_hash": C.cfg_hash(),
        "scan_free": True, "tables_touched": ["event_minute_bars_v2"],
        "spine_numeric_reads": 0,
        "horizon_ceiling": "T+3 - event_minute_bars_v2 carries offsets -3..+3 only; no figure extrapolates past it",
        "n_d1": n_d1, "n_detection_universe": n_uni,
        "definitions": {
            "retrace_excursion": "(H - p_h) / (H - A), H=day_high_ext, A=tick_close_t_minus_1_rth",
            "retrace_detection": "(H - p_h) / (H - p_det), p_det=det_price_lat0",
            "reading": "0 = still at the high; 1.0 = back to the T-1 RTH close; >1.0 = below it",
        },
        "t3d_flag_scope_note": ("H - A spans the (T-1,T0) boundary, so the denominator flag applies at "
                                "EVERY horizon including t0_close; the numerator flag applies at t1/t2/t3"),
        "flag_composition": flag_counts,
        "variants": variants,
        "by_era": by_era,
        "by_detection_segment": by_seg,
        "filter_waterfall": waterfall,
        "escalation_row_8": row8,
        "escalation_row_9": row9,
        "artifacts": [OUT_PARQUET],
    }
    C.write_json(summary, OUT_JSON)

    # ---------------- console ----------------
    print("\nretrace_excursion quantiles (PRIMARY, all carried)   [T+3 ceiling]")
    print(f"{'horizon':10s} {'n':>7s} {'q05':>8s} {'q25':>8s} {'median':>8s} {'q75':>8s} {'q95':>8s}")
    for h in HORIZONS:
        v = variants["all_carried"]["horizons"][h]["retrace_excursion"]
        print(f"{h:10s} {v['n']:7,d} {v['q05']:8.3f} {v['q25']:8.3f} {v['q50']:8.3f} {v['q75']:8.3f} {v['q95']:8.3f}")

    print("\nretrace_detection quantiles (PRIMARY, all carried)")
    for h in HORIZONS:
        v = variants["all_carried"]["horizons"][h]["retrace_detection"]
        print(f"{h:10s} {v['n']:7,d} {v['q05']:8.3f} {v['q25']:8.3f} {v['q50']:8.3f} {v['q75']:8.3f} {v['q95']:8.3f}")

    print("\nlevel-crossing census (PRIMARY)")
    print(f"{'horizon':10s} {'n':>7s} {'below A':>9s} {'share':>8s} {'below det':>10s} {'share':>8s}")
    for h in HORIZONS:
        lc = variants["all_carried"]["horizons"][h]["level_crossing"]
        print(f"{h:10s} {lc['n_defined']:7,d} {lc['n_below_A']:9,d} {lc['share_below_A']:7.2%} "
              f"{lc['n_below_det']:10,d} {lc['share_below_det']:7.2%}")

    print("\nby detection segment - median retrace_excursion (n)")
    for sg in segs:
        line = []
        for h in HORIZONS:
            v = by_seg[sg]["horizons"][h]["retrace_excursion"]
            line.append(f"{h}:{v['q50']:+.3f}(n={v['n']:,})")
        print(f"  {sg:10s} " + "  ".join(line))

    print(f"\nESCALATION ROW 8: {row8['share']:.4%} vs 2% -> "
          + ("*** TRIGGERED ***" if row8["triggered"] else "pass"))
    print(f"ESCALATION ROW 9: {row9['share']:.4%} vs 25% -> "
          + ("*** TRIGGERED ***" if row9["triggered"] else "pass"))


if __name__ == "__main__":
    main()
