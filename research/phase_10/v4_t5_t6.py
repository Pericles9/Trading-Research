"""
Phase 10 v4 T5-T6 -- the Arm A test, stability, causal audit, failure rows.

Usage: .venv/Scripts/python.exe research/phase_10/v4_t5_t6.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import COHORT_KEY, POOLED, quantiles, rel, write_json  # noqa: E402
from v4_pipeline import cfg_hash, load_cfg  # noqa: E402

OUT = "v4_t5_t6_summary.json"

CAUSAL_AUDIT = [
    ("inter_trade_interval", "non_causal", "the interval joining print i to i+1 is only known once print i+1 has arrived; usable online with a one-print lag"),
    ("local_median_log_interval", "non_causal", "CENTRED moving median -- reads forward in time by half a window (D9, T2b). Phase 17 needs a trailing estimator, which is a different estimator, not a re-parameterization"),
    ("normalized_log_interval", "non_causal", "inherits the centred window from local_median_log_interval"),
    ("interval_histogram", "non_causal", "built over the completed session"),
    ("histogram_peaks", "non_causal", "derived from the completed-session histogram"),
    ("void_parameter", "non_causal", "derived from the completed-session histogram"),
    ("threshold_decades", "non_causal", "the trough of the completed-session histogram; the single most non-causal quantity in the phase"),
    ("no_threshold_label", "non_causal", "an outcome of the completed-session void gate"),
    ("subburst_intervals", "non_causal", "runs below a completed-session threshold"),
    ("subburst_count", "non_causal", "aggregate of subburst_intervals"),
    ("subburst_duration_spacing", "non_causal", "aggregate of subburst_intervals"),
    ("session_move_denominator", "non_causal", "uses the last in-window T=0 print"),
    ("move_share", "non_causal", "inherits the session-move denominator"),
    ("detection_anchor_ns", "CAUSAL", "D7: first poll boundary at or after the running max of T=0 price reaches threshold x the T-1 RTH close. Every input is known at or before that instant. JUSTIFIED EXPLICITLY per T6c -- this is the only causal field in the phase, and it is causal by construction because D7 was written to be an operating-time anchor"),
    ("detection_segment", "CAUSAL", "a function of detection_anchor_ns and the pinned session calendar, both known at detection time"),
    ("event_peak_ns", "non_causal", "the intensity maximum over the completed session (v2, retrospective by construction)"),
    ("seconds_from_detection", "non_causal", "the sub-burst start is non-causal even though the detection anchor is causal"),
    ("seconds_from_peak", "non_causal", "both endpoints non-causal"),
]


def loglog_slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if m.sum() < 5:
        return None
    return float(np.polyfit(np.log10(x[m]), np.log10(y[m]), 1)[0])


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    fc = cfg["failure_criteria"]
    tie_ref = cfg["ties"]["reference_variant"]
    wref = cfg["normalization"]["window_fraction_reference"]
    mref = cfg["subbursts"]["min_prints_reference"]
    cut = cfg["threshold"]["void_parameter"]["cutoff"]

    ev = pd.read_parquet(os.path.join(art, "v4_event_metrics.parquet"))
    sb = pd.read_parquet(os.path.join(art, "v4_subbursts.parquet"))
    for d in (ev, sb):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)

    ref = ev[(ev["tie_variant"] == tie_ref) & (ev["window_fraction"] == wref)
             & (ev["min_prints"].fillna(mref) == mref)]
    pool = ref[ref["cohort_group"].isin(POOLED)]
    ok = pool[pool["status"] == "ok"]
    psb = sb[sb["cohort_group"].isin(POOLED)]

    # ------------------------------------------------------- T3d no_threshold
    def share_block(df):
        n = len(df)
        return {"n_events": n,
                "n_ok": int((df["status"] == "ok").sum()),
                "n_no_threshold": int((df["status"] == "no_threshold").sum()),
                "n_too_few_prints": int((df["status"] == "too_few_prints").sum()),
                "share_no_threshold": float((df["status"] == "no_threshold").sum() / n) if n else None,
                "reasons": df.loc[df["status"] == "no_threshold", "no_threshold_reason"]
                             .value_counts().to_dict()}

    no_thr = {"pooled": share_block(pool),
              "by_segment": {str(g): share_block(gg) for g, gg in pool.groupby("segment")},
              "by_group": {str(g): share_block(gg) for g, gg in ref.groupby("cohort_group")},
              "zaliapin_reasoning": (
                  "D9 predicts, on the seismology prior art, that the bimodality separating clustered "
                  "from background events breaks in the vicinity of the dominant event -- and the "
                  "whole T=0 session is that vicinity. A no_threshold event is one where the method "
                  "declines to declare sub-bursts rather than inventing them. No fallback threshold "
                  "is ever applied.")}

    # ------------------------------------------------------- T6b void
    void = {"pooled": quantiles(pool["void"].dropna()),
            "cutoff": cut,
            "n_with_void": int(pool["void"].notna().sum()),
            "by_segment": {str(g): quantiles(gg["void"].dropna()) for g, gg in pool.groupby("segment")},
            "best_void_of_no_threshold_events": quantiles(
                pool.loc[pool["status"] == "no_threshold", "best_void"].dropna())}
    okv = ok["void"].dropna()
    margin = fc["row_3"]["margin"]
    void["share_within_margin_above_cutoff"] = (
        float(((okv >= cut) & (okv < cut + margin)).mean()) if len(okv) else None)

    thr = {"pooled": quantiles(ok["threshold_decades"]),
           "by_segment": {str(g): quantiles(gg["threshold_decades"])
                          for g, gg in ok.groupby("segment")}}

    # ------------------------------------------------------- T5 Arm A test
    def arm_a(df):
        out = {}
        for var, col in (("t0_print_count", "n_prints_raw"),
                         ("session_duration_seconds", "print_span_seconds"),
                         ("absolute_activity_prints_per_sec", None)):
            if col is None:
                x = df["n_prints_raw"] / df["print_span_seconds"].replace(0, np.nan)
            else:
                x = df[col]
            y = df["n_subbursts"]
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() < 5:
                out[var] = {"n": int(m.sum()), "spearman": None, "loglog_slope": None}
                continue
            s = sps.spearmanr(x[m], y[m])
            out[var] = {"n": int(m.sum()), "spearman": float(s.statistic),
                        "spearman_pvalue": float(s.pvalue),
                        "loglog_slope": loglog_slope(x[m], y[m])}
        return out

    t5 = {"pooled": {**arm_a(ok), "n_events": int(len(ok)),
                     "subbursts_per_1000_prints": quantiles(
                         ok["n_subbursts"] / (ok["n_prints_raw"] / 1000.0)),
                     "subbursts_per_hour": quantiles(
                         ok["n_subbursts"] / (ok["print_span_seconds"] / 3600.0))},
          "by_segment": {str(g): {**arm_a(gg), "n_events": int(len(gg))}
                         for g, gg in ok.groupby("segment") if len(gg) >= 5}}

    # ------------------------------------------------------- T6a stability
    def rel_change(pivot):
        v = pivot.dropna()
        if not len(v):
            return None
        rng = v.max(axis=1) - v.min(axis=1)
        med = v.median(axis=1).replace(0, np.nan)
        return quantiles((rng / med).dropna())

    wpv = ev[(ev["tie_variant"] == tie_ref) & (ev["status"] == "ok")
             & (ev["min_prints"].fillna(mref) == mref)
             & ev["cohort_group"].isin(POOLED)].pivot_table(
        index=COHORT_KEY, columns="window_fraction", values="n_subbursts")
    win_stab = {"relative_change_across_10_30pct": rel_change(wpv),
                "n_events": int(len(wpv.dropna())),
                "published_comparison": fc["row_4"]["published_comparison"],
                "median_count_by_window": {str(c): float(wpv[c].median())
                                           for c in wpv.columns if wpv[c].notna().any()}}

    tpv = ev[(ev["window_fraction"] == wref) & (ev["status"] == "ok")
             & (ev["min_prints"].fillna(mref) == mref)
             & ev["cohort_group"].isin(POOLED)].pivot_table(
        index=COHORT_KEY, columns="tie_variant", values="n_subbursts")
    tie_stab = {"relative_change_across_variants": rel_change(tpv),
                "n_events": int(len(tpv.dropna())),
                "median_count_by_variant": {str(c): float(tpv[c].median())
                                            for c in tpv.columns if tpv[c].notna().any()},
                "n_no_threshold_by_variant": {
                    str(v): int(((ev["tie_variant"] == v) & (ev["window_fraction"] == wref)
                                 & (ev["status"] == "no_threshold")
                                 & ev["cohort_group"].isin(POOLED)).sum())
                    for v in cfg["ties"]["variants"]}}

    mpv = ev[(ev["tie_variant"] == tie_ref) & (ev["window_fraction"] == wref)
             & (ev["status"] == "ok") & ev["cohort_group"].isin(POOLED)].pivot_table(
        index=COHORT_KEY, columns="min_prints", values="n_subbursts")
    minp_stab = {"relative_change_across_min_prints": rel_change(mpv),
                 "median_count_by_min_prints": {str(c): float(mpv[c].median())
                                                for c in mpv.columns if mpv[c].notna().any()}}

    # ------------------------------------------------------- T6c causal audit
    ca = pd.DataFrame(CAUSAL_AUDIT, columns=["field", "causality", "reason"])
    ca["config_hash"] = chash
    ca.to_parquet(os.path.join(art, "v4_causal_audit.parquet"), index=False)
    causal = {"n_fields": int(len(ca)),
              "n_causal": int((ca["causality"] == "CAUSAL").sum()),
              "n_non_causal": int((ca["causality"] == "non_causal").sum()),
              "causal_fields": ca.loc[ca["causality"] == "CAUSAL", ["field", "reason"]].to_dict("records"),
              "phase_17_must_rederive": ca.loc[ca["causality"] == "non_causal", "field"].tolist(),
              "headline": ("Every field in this phase is non-causal except the D7 detection anchor and "
                           "the segment label derived from it. The threshold itself is the most "
                           "non-causal quantity here -- it is the trough of the completed session's "
                           "histogram. Phase 17 must re-derive the normalization, the histogram, the "
                           "void gate and the threshold under causality; none of them is a "
                           "re-parameterization of what is here.")}

    # ------------------------------------------------------- T6d failure rows
    rows = []
    a = t5["pooled"]["t0_print_count"]
    rows.append({"row": 1, "observable": "sub-burst count vs T=0 print count",
                 "observed": {"spearman": a["spearman"], "loglog_slope": a["loglog_slope"]},
                 "threshold": f"spearman <= {fc['row_1']['threshold_max_spearman']} and slope <= {fc['row_1']['threshold_max_slope']}",
                 "pass": bool(a["spearman"] is not None and a["loglog_slope"] is not None
                              and a["spearman"] <= fc["row_1"]["threshold_max_spearman"]
                              and a["loglog_slope"] <= fc["row_1"]["threshold_max_slope"]),
                 "detail": {"n": a["n"], "arm_a_reference": {"spearman": 0.96, "slope": 0.85}}})

    s2 = no_thr["pooled"]["share_no_threshold"]
    rows.append({"row": 2, "observable": "share no_threshold", "observed": s2,
                 "threshold": f"<= {fc['row_2']['threshold_max_share']}",
                 "pass": bool(s2 is not None and s2 <= fc["row_2"]["threshold_max_share"]),
                 "detail": {"n": no_thr["pooled"]["n_events"]}})

    s3 = void["share_within_margin_above_cutoff"]
    rows.append({"row": 3, "observable": f"share of void within {margin} above cutoff {cut}",
                 "observed": s3, "threshold": f"<= {fc['row_3']['threshold_max_share']}",
                 "pass": bool(s3 is not None and s3 <= fc["row_3"]["threshold_max_share"]),
                 "detail": {"n": int(len(okv))}})

    s4 = (win_stab["relative_change_across_10_30pct"] or {}).get("q50")
    rows.append({"row": 4, "observable": "median relative change in count across 10-30% window grid",
                 "observed": s4, "threshold": f"<= {fc['row_4']['threshold_max_relative_change']}",
                 "pass": bool(s4 is not None and s4 <= fc["row_4"]["threshold_max_relative_change"]),
                 "detail": {"n": win_stab["n_events"], "published_comparison": 0.003}})

    s5 = (tie_stab["relative_change_across_variants"] or {}).get("q50")
    rows.append({"row": 5, "observable": "median relative change in count across tie variants",
                 "observed": s5, "threshold": f"<= {fc['row_5']['threshold_max_relative_change']}",
                 "pass": bool(s5 is not None and s5 <= fc["row_5"]["threshold_max_relative_change"]),
                 "detail": {"n": tie_stab["n_events"]}})

    degen = float(((ok["n_subbursts"] == 1)
                   & (ok["largest_subburst_span_share"].fillna(0) >= 0.5)).mean()) if len(ok) else None
    med_dur = float(psb["duration_seconds"].median()) if len(psb) else None
    res_floor_s = float(pool["resolution_floor_ns"].median()) / 1e9
    dur_mult = (med_dur / res_floor_s) if (med_dur and res_floor_s) else None
    rows.append({"row": 6, "observable": "degenerate share / median duration over resolution floor",
                 "observed": {"degenerate_share": degen, "median_duration_s": med_dur,
                              "resolution_floor_s": res_floor_s, "duration_over_floor": dur_mult},
                 "threshold": f"share <= {fc['row_6']['threshold_max_share']} and duration/floor > {fc['row_6']['threshold_min_duration_multiple']}",
                 "pass": bool(degen is not None and dur_mult is not None
                              and degen <= fc["row_6"]["threshold_max_share"]
                              and dur_mult > fc["row_6"]["threshold_min_duration_multiple"])})

    tp = thr["by_segment"].get("premarket", {}).get("q50")
    tr = thr["by_segment"].get("rth", {}).get("q50")
    s7 = abs(tp - tr) if (tp is not None and tr is not None) else None
    rows.append({"row": 7, "observable": "premarket vs rth median threshold separation, decades",
                 "observed": s7, "threshold": f"<= {fc['row_7']['threshold_max_decades']}",
                 "pass": bool(s7 is not None and s7 <= fc["row_7"]["threshold_max_decades"]),
                 "detail": {"premarket_median": tp, "rth_median": tr}})

    any_fail = any(r["pass"] is False for r in rows)

    # ------------------------------------------------------- T4 descriptive
    def block(e, s):
        return {"n_events": int(len(e)), "n_subbursts": int(len(s)),
                "subburst_count": quantiles(e["n_subbursts"]),
                "duration_seconds": quantiles(s["duration_seconds"]),
                "spacing_seconds": quantiles(s["spacing_seconds"]),
                "move_share": quantiles(s["move_share"]),
                "n_move_share_undefined": int(s["move_share"].isna().sum()),
                "n_events_session_move_undefined": int((~e["session_move_defined"].fillna(False)).sum()),
                "share_session_prints_in_subbursts": quantiles(e["share_session_prints_in_subbursts"]),
                "seconds_from_detection": quantiles(s["seconds_from_detection"]),
                "seconds_from_peak": quantiles(s["seconds_from_peak"]),
                "move_share_by_rank": {
                    f"rank_{k}": quantiles(s.assign(ab=s["subburst_move"].abs())
                                           .sort_values("ab", ascending=False)
                                           .groupby(COHORT_KEY).nth(k - 1)["move_share"])
                    for k in (1, 2, 3)}}

    desc = {"pooled": block(ok, psb),
            "by_segment": {str(g): block(gg, psb[psb["segment"] == g])
                           for g, gg in ok.groupby("segment")}}
    for g in ("row_cap_census", "dev_v4_sidecar"):
        ge = ref[(ref["cohort_group"] == g) & (ref["status"] == "ok")]
        gs = sb[sb["cohort_group"] == g]
        if len(ge):
            desc[g] = block(ge, gs)

    ties = {"pooled_share_tied": quantiles(pool["share_tied"]),
            "resolution_floor_ns": quantiles(pool["resolution_floor_ns"]),
            "by_segment": {str(g): {"share_tied": quantiles(gg["share_tied"]),
                                    "resolution_floor_ns": quantiles(gg["resolution_floor_ns"])}
                           for g, gg in pool.groupby("segment")}}

    summary = {"phase": "10", "version": "v4", "task": "T5-T6", "config_hash": chash,
               "population": "pooled analysis cohort n=100 at the reference cell "
                             f"(tie={tie_ref}, window={wref}, min_prints={mref}); "
                             "row_cap_census and dev_v4_sidecar carried, never pooled",
               "t1_ties": ties,
               "t3_no_threshold": no_thr,
               "t3_void": void,
               "t3_threshold": thr,
               "t4_descriptive": desc,
               "t5_arm_a_test": t5,
               "t6a_stability": {"normalization_window": win_stab, "tie_variant": tie_stab,
                                 "min_prints": minp_stab},
               "t6c_causal_audit": causal,
               "t6d_failure_criteria": {
                   "row_0": {"mode": fc["row_0"]["mode"], "observed": None, "pass": None,
                             "note": fc["row_0"]["note"]},
                   "rows": rows, "any_failed": bool(any_fail)},
               "phase_13_boundary": cfg["phase_13_boundary"],
               "standing_lesson": fc["standing_lesson"],
               "source": "research/phase_10/v4_t5_t6.py:main"}
    write_json(os.path.join(art, OUT), summary)

    p = no_thr["pooled"]
    print(f"no_threshold: {p['n_no_threshold']}/{p['n_events']} = {p['share_no_threshold']:.3f} pooled")
    for g, v in no_thr["by_segment"].items():
        print(f"   {g}: {v['n_no_threshold']}/{v['n_events']} = {v['share_no_threshold']:.3f}")
    print(f"void: median {void['pooled']['q50']:.4f} (n={void['n_with_void']}), "
          f"share within {margin} of cutoff {cut}: {s3}")
    print(f"sub-burst count median {desc['pooled']['subburst_count']['q50']:.0f}, "
          f"duration median {desc['pooled']['duration_seconds']['q50']:.4f}s")
    print("\n=== FAILURE ROWS ===")
    for r in rows:
        o = r["observed"]
        os_ = (f"{o:+.4f}" if isinstance(o, float) else
               json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o.items()})
               if isinstance(o, dict) else str(o))
        print(f"  row {r['row']} {str(r['observable'])[:44]:46s} {os_[:56]:56s} -> "
              f"{'PASS' if r['pass'] else 'FAIL'}")
    print(f"\n  ANY FAILED: {any_fail}")
    return 0 if not any_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
