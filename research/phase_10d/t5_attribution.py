"""
Phase 10d T5 -- ATTRIBUTION. The deliverable is not a duration number; it is which
mechanism moved it.

T5a  floor-only / merge-only / joint, full distribution, pooled + per segment + per kernel
T5b  n_prints composition per cell -- promotion versus deletion
T5c  separator sensitivity, hard_break vs bridgeable_count_only
T5d  parameter dominance                                            [10d-R3]
T5e  count vs print count, descriptive only, no gate
T5f  degeneracy check                                               [10d-R5]
T5g  kernel and variant consistency                                 [10d-R6]
plus the 10d-R4 separability evaluation.

Prior-version figures are READ FROM COMMITTED ARTIFACTS, with attribution recorded,
never transcribed from a prompt.

Usage: .venv/Scripts/python.exe research/phase_10d/t5_attribution.py
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ART = os.path.join(ROOT, "results", "phase_10d", "artifacts")
KEY = ["ticker", "event_date_canonical"]
SEGS = ["premarket", "rth", "evening", "unlabelled"]


def conf():
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        return json.load(f)


def dstat(a):
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return dict(n=0, q25=np.nan, median=np.nan, q75=np.nan, max=np.nan)
    return dict(n=int(a.size), q25=float(np.quantile(a, .25)),
                median=float(np.median(a)), q75=float(np.quantile(a, .75)),
                max=float(a.max()))


def dec(x, ref):
    """Shift in decades of duration, relative to the reference median."""
    if not (np.isfinite(x) and np.isfinite(ref)) or x <= 0 or ref <= 0:
        return np.nan
    return float(np.log10(x / ref))


def prior_figures():
    """Every prior-version number this phase quotes, read from its committed artifact."""
    p10a = os.path.join(ROOT, "results", "phase_10", "artifacts")
    with open(os.path.join(p10a, "v4_t5_t6_summary.json"), encoding="utf-8") as f:
        v4 = json.load(f)
    with open(os.path.join(p10a, "v3_t2_t4_summary.json"), encoding="utf-8") as f:
        v3 = json.load(f)
    c10 = pd.read_parquet(os.path.join(
        ROOT, "results", "phase_10c", "artifacts", "s1_t1_subbursts.parquet"))

    v4d = v4["t4_descriptive"]["pooled"]["duration_seconds"]
    v4a = v4["t5_arm_a_test"]["pooled"]
    v3p = v3["t4_arm_a_test"]["pooled"]
    return {
        "v4_duration_pooled": {
            "n": v4d["n"], "q25": v4d["q25"], "median": v4d["q50"], "q75": v4d["q75"],
            "max": v4d["q100"],
            "_source": "results/phase_10/artifacts/v4_t5_t6_summary.json "
                       "/t4_descriptive/pooled/duration_seconds",
            "_cohort": "v4's 100-event analysis cohort (50 dev_v4_primary + 50 "
                       "activity_extension), NOT 10c/10d's 56-event dev sample. The "
                       "populations differ and the comparison is between different "
                       "cohorts, which is stated wherever the figure appears.",
            "_prompt_says": "349 ns -- confirmed: q50 = 3.49e-07 s"},
        "v4_no_threshold": {
            "pooled": v4["t3_no_threshold"]["pooled"],
            "premarket": v4["t3_no_threshold"]["by_segment"]["premarket"],
            "rth": v4["t3_no_threshold"]["by_segment"]["rth"],
            "_source": "results/phase_10/artifacts/v4_t5_t6_summary.json /t3_no_threshold",
            "_prompt_says": "10/100, premarket 3/28, rth 7/70 -- confirmed",
            "_reason": "v4's own artifact records the reason as 'no trough clears void "
                       "cutoff 0.7' for all 10. That rule is retired; 10c does not use it."},
        "v4_count_vs_prints": {
            "n": v4a["t0_print_count"]["n"],
            "spearman_t0_print_count": v4a["t0_print_count"]["spearman"],
            "loglog_slope_t0_print_count": v4a["t0_print_count"]["loglog_slope"],
            "spearman_absolute_activity": v4a["absolute_activity_prints_per_sec"]["spearman"],
            "loglog_slope_absolute_activity":
                v4a["absolute_activity_prints_per_sec"]["loglog_slope"],
            "_source": "results/phase_10/artifacts/v4_t5_t6_summary.json /t5_arm_a_test/pooled",
            "_prompt_says": "0.87/0.92 -- confirmed (0.8748 / 0.9224)"},
        "v3_count_vs_prints": {
            "print_rate_n": v3p["print_rate"]["t0_print_count"]["n"],
            "print_rate_spearman": v3p["print_rate"]["t0_print_count"]["spearman"],
            "print_rate_slope": v3p["print_rate"]["t0_print_count"]["loglog_slope"],
            "volume_rate_n": v3p["volume_rate"]["t0_print_count"]["n"],
            "volume_rate_spearman": v3p["volume_rate"]["t0_print_count"]["spearman"],
            "volume_rate_slope": v3p["volume_rate"]["t0_print_count"]["loglog_slope"],
            "_source": "results/phase_10/artifacts/v3_t2_t4_summary.json "
                       "/t4_arm_a_test/pooled",
            "_prompt_says": "0.28-0.35 / 0.19-0.26 -- confirmed (0.2772/0.3531 spearman, "
                            "0.2605/0.1849 slope)"},
        "v1_count_vs_prints": {
            "spearman": 0.96, "loglog_slope": 0.85,
            "_source": "results/phase_10/REPORT.md line 127, table row "
                       "'*Arm A, for reference* | *+0.96* | *+0.85*'",
            "_attribution_caveat": "ATTRIBUTION GAP, recorded rather than papered over: "
                                   "unlike v3 and v4, v1's Arm A pair exists only in "
                                   "REPORT.md prose. No committed JSON artifact under "
                                   "results/phase_10/artifacts/ carries a Spearman in "
                                   "[0.9, 1.0]. The figure is quoted with that provenance "
                                   "and is not re-derived here."},
        "c10c_duration_pooled": {
            **dstat(c10.duration_s),
            "_source": "results/phase_10c/artifacts/s1_t1_subbursts.parquet, all 130 ok "
                       "(event, kernel) cells pooled",
            "_note": "This is 10c's OWN pooled figure across all three kernels. 10d's "
                     "reference cell reproduces it bit-exactly (verified: identical "
                     "start_ns, end_ns, n_prints and duration_s over all 170,722 objects). "
                     "MAJORITY OF THIS POPULATION IS SINGLE-INTERVAL: 10c applies no "
                     "run-length floor.",
            "share_2print": float((c10.n_prints == 2).mean()),
            "n_2print": int((c10.n_prints == 2).sum())},
    }


def main() -> int:
    C10D = conf()
    chash = hashlib.sha256(json.dumps(C10D, sort_keys=True).encode()).hexdigest()[:8]
    sb = pd.read_parquet(os.path.join(ART, "t4_subbursts.parquet"))
    cells = pd.read_parquet(os.path.join(ART, "t4_cell_summary.parquet"))
    ctx = pd.read_parquet(os.path.join(ART, "t4_variant_context.parquet"))
    KERNELS = C10D["upstream_10c"]["kernels_min"]
    KP = C10D["upstream_10c"]["kernel_primary_min"]
    MPS = C10D["min_prints_grid"]["values"]
    NONDEG = sorted({(int(K), float(d)) for K, d in
                     zip(sb.K, sb.d)} - {(0, 0.0)})
    assert len(NONDEG) == 12, NONDEG

    hb = sb[sb.sep == "hard_break"]
    seg125 = ctx[ctx.variant == 1.25][KEY + ["segment"]].copy()
    seg125["segment"] = seg125.segment.fillna("unlabelled")

    # ============================================================== T5a
    def read(df, tag, **meta):
        return {"read": tag, **meta, **dstat(df.duration_s),
                "n_objects": int(len(df)),
                "prints_in_bursts": int(df.n_prints.sum()) if len(df) else 0,
                "share_2print": float((df.n_prints == 2).mean()) if len(df) else np.nan}

    t5a = []
    for k in KERNELS:
        kk = hb[hb.kernel_min == k]
        base = kk[(kk.K == 0) & (kk.d == 0.0) & (kk.min_prints == 2)]
        ref_med = float(base.duration_s.median())
        t5a.append({**read(base, "identity", kernel_min=k, K=0, d=0.0, min_prints=2),
                    "shift_decades": 0.0})
        for mp in MPS:
            if mp == 2:
                continue
            g = kk[(kk.K == 0) & (kk.d == 0.0) & (kk.min_prints == mp)]
            t5a.append({**read(g, "floor_only", kernel_min=k, K=0, d=0.0, min_prints=mp),
                        "shift_decades": dec(g.duration_s.median(), ref_med)})
        for K, dd in NONDEG:
            g = kk[(kk.K == K) & (kk.d == dd) & (kk.min_prints == 2)]
            t5a.append({**read(g, "merge_only", kernel_min=k, K=K, d=dd, min_prints=2),
                        "shift_decades": dec(g.duration_s.median(), ref_med)})
        for K, dd in NONDEG:
            for mp in MPS:
                if mp == 2:
                    continue
                g = kk[(kk.K == K) & (kk.d == dd) & (kk.min_prints == mp)]
                t5a.append({**read(g, "joint", kernel_min=k, K=K, d=dd, min_prints=mp),
                            "shift_decades": dec(g.duration_s.median(), ref_med)})
    t5a = pd.DataFrame(t5a)

    # per segment, at the primary kernel
    t5a_seg = []
    kk = hb[hb.kernel_min == KP].merge(seg125, on=KEY, how="left")
    kk["segment"] = kk.segment.fillna("unlabelled")
    for s in SEGS:
        ks = kk[kk.segment == s]
        if not len(ks):
            continue
        base = ks[(ks.K == 0) & (ks.d == 0.0) & (ks.min_prints == 2)]
        ref_med = float(base.duration_s.median()) if len(base) else np.nan
        cellsets = ([("identity", 0, 0.0, 2)]
                    + [("floor_only", 0, 0.0, mp) for mp in MPS if mp != 2]
                    + [("merge_only", K, dd, 2) for K, dd in NONDEG]
                    + [("joint", K, dd, mp) for K, dd in NONDEG for mp in MPS if mp != 2])
        for tag, K, dd, mp in cellsets:
            g = ks[(ks.K == K) & (ks.d == dd) & (ks.min_prints == mp)]
            t5a_seg.append({**read(g, tag, kernel_min=KP, segment=s, K=K, d=dd,
                                   min_prints=mp),
                            "shift_decades": dec(g.duration_s.median(), ref_med)})
    t5a_seg = pd.DataFrame(t5a_seg)

    # ---- headline attribution at the primary kernel
    kp = t5a[t5a.kernel_min == KP]
    floor_only = kp[kp.read == "floor_only"]
    merge_only = kp[kp.read == "merge_only"]
    joint = kp[kp.read == "joint"]
    att = {
        "kernel_min": KP, "sep": "hard_break",
        "identity_median_s": float(kp[kp.read == "identity"].iloc[0]["median"]),
        "identity_n": int(kp[kp.read == "identity"].iloc[0]["n_objects"]),
        "floor_only_max_shift_decades": float(floor_only.shift_decades.abs().max()),
        "floor_only_at_mp3_decades": float(
            floor_only[floor_only.min_prints == 3].iloc[0].shift_decades),
        "floor_only_at_mp5_decades": float(
            floor_only[floor_only.min_prints == 5].iloc[0].shift_decades),
        "merge_only_max_shift_decades": float(merge_only.shift_decades.abs().max()),
        "merge_only_median_shift_decades": float(merge_only.shift_decades.median()),
        "joint_max_shift_decades": float(joint.shift_decades.abs().max()),
    }
    att["additive_prediction_decades"] = (att["floor_only_at_mp3_decades"]
                                          + att["merge_only_max_shift_decades"])
    jc = joint[(joint.min_prints == 3)]
    att["joint_max_at_mp3_decades"] = float(jc.shift_decades.max())
    att["interaction_decades"] = att["joint_max_at_mp3_decades"] - att["additive_prediction_decades"]
    att["dominant_mechanism"] = ("floor" if att["floor_only_max_shift_decades"]
                                 > att["merge_only_max_shift_decades"] else "merge")
    att["ratio_floor_over_merge"] = (att["floor_only_max_shift_decades"]
                                     / max(att["merge_only_max_shift_decades"], 1e-12))

    # ============================================================== 10d-R4
    r4c = C10D["escalation"]["R4_attribution_not_separable"]
    sep_min = float(r4c["separability_min_decades"])
    neg_max = float(r4c["negligible_max_decades"])
    f_abs = att["floor_only_at_mp3_decades"]
    m_abs = att["merge_only_max_shift_decades"]
    r4 = {"floor_only_shift_decades": f_abs, "merge_only_shift_decades": m_abs,
          "abs_difference_decades": abs(abs(f_abs) - abs(m_abs)),
          "separability_min_decades": sep_min, "negligible_max_decades": neg_max,
          "both_non_negligible": bool(abs(f_abs) > neg_max and abs(m_abs) > neg_max),
          "fires": bool(abs(f_abs) > neg_max and abs(m_abs) > neg_max
                        and abs(abs(f_abs) - abs(m_abs)) < sep_min)}

    # ============================================================== T5b
    t5b = []
    for k in KERNELS:
        kk2 = hb[hb.kernel_min == k]
        base = kk2[(kk2.K == 0) & (kk2.d == 0.0) & (kk2.min_prints == 2)]
        base_prints = int(base.n_prints.sum())
        for (K, dd, mp), g in kk2.groupby(["K", "d", "min_prints"]):
            npr = g.n_prints
            t5b.append({
                "kernel_min": float(k), "K": int(K), "d": float(dd), "min_prints": int(mp),
                "read": ("identity" if (K, dd, mp) == (0, 0.0, 2)
                         else "floor_only" if (K, dd) == (0, 0.0)
                         else "merge_only" if mp == 2 else "joint"),
                "n_objects": int(len(g)),
                "share_2print": float((npr == 2).mean()),
                "n_2print": int((npr == 2).sum()),
                "prints_in_bursts": int(npr.sum()),
                "prints_delta_vs_identity": int(npr.sum()) - base_prints,
                "prints_retained_share": float(npr.sum() / base_prints),
                "median_n_prints": float(npr.median())})
    t5b = pd.DataFrame(t5b)

    # ============================================================== T5c
    t5c = []
    for k in KERNELS:
        for (K, dd, mp) in [(0, 0.0, 2)] + [(K, d_, mp_) for K, d_ in NONDEG
                                            for mp_ in MPS]:
            a = sb[(sb.kernel_min == k) & (sb.K == K) & (sb.d == dd)
                   & (sb.min_prints == mp) & (sb.sep == "hard_break")]
            b = sb[(sb.kernel_min == k) & (sb.K == K) & (sb.d == dd)
                   & (sb.min_prints == mp) & (sb.sep == "bridgeable_count_only")]
            t5c.append({"kernel_min": float(k), "K": int(K), "d": float(dd),
                        "min_prints": int(mp),
                        "n_hard_break": int(len(a)), "n_bridgeable": int(len(b)),
                        "n_delta": int(len(b) - len(a)),
                        "count_rel_change": float((len(b) - len(a)) / max(len(a), 1)),
                        "median_hard_break_s": float(a.duration_s.median()) if len(a) else np.nan,
                        "median_bridgeable_s": float(b.duration_s.median()) if len(b) else np.nan,
                        "identical": bool(len(a) == len(b)
                                          and np.array_equal(np.sort(a.start_ns.to_numpy()),
                                                             np.sort(b.start_ns.to_numpy())))})
    t5c = pd.DataFrame(t5c)

    # ============================================================== T5d / 10d-R3
    ec = cells[(cells.label == "ok") & (cells.kernel_min == KP)
               & (cells.sep == "hard_break") & (cells.min_prints == 2)].copy()
    ec["kd_rank"] = ec.apply(
        lambda r_: (sorted(NONDEG).index((int(r_.K), float(r_.d))) + 1
                    if (int(r_.K), float(r_.d)) in NONDEG else 0), axis=1)
    nd = ec[ec.kd_rank > 0]
    tol_rho_dur = abs(spearmanr(nd.kd_rank, nd.dur_median).statistic)
    tol_rho_cnt = abs(spearmanr(nd.kd_rank, nd.n_objects).statistic)
    ident = ec[ec.kd_rank == 0]
    ev_chars = C10D["escalation"]["R3_merge_tolerance_dominance"]["event_characteristics"]
    char_rho = {}
    for c in ev_chars:
        if c == "t0_print_count":
            col = ident.n_prints_session
        elif c == "session_duration_s":
            col = ident.n_intervals * 0 + np.nan
        else:
            col = ident[c] if c in ident.columns else None
        if col is None or not np.isfinite(np.asarray(col, dtype=float)).any():
            char_rho[c] = {"duration": np.nan, "count": np.nan,
                           "_note": "not carried on the cell summary"}
            continue
        char_rho[c] = {
            "duration": float(abs(spearmanr(col, ident.dur_median, nan_policy="omit").statistic)),
            "count": float(abs(spearmanr(col, ident.n_objects, nan_policy="omit").statistic))}
    max_char_dur = np.nanmax([v["duration"] for v in char_rho.values()])
    max_char_cnt = np.nanmax([v["count"] for v in char_rho.values()])
    r3 = {"n_events_at_identity": int(len(ident)), "n_nondegenerate_rows": int(len(nd)),
          "tolerance_rho_duration": float(tol_rho_dur),
          "tolerance_rho_count": float(tol_rho_cnt),
          "max_event_characteristic_rho_duration": float(max_char_dur),
          "max_event_characteristic_rho_count": float(max_char_cnt),
          "event_characteristic_rho": char_rho,
          "fires": bool(tol_rho_dur > max_char_dur or tol_rho_cnt > max_char_cnt),
          "_computed_over": "the twelve non-degenerate (K,d) cells only, kernel 8, "
                            "min_prints=2, sep=hard_break"}

    # ============================================================== T5e
    ident_ev = ident.copy()
    t5e = {}
    for name, col in [("t0_print_count", ident_ev.n_prints_session),
                      ("n_intervals", ident_ev.n_intervals)]:
        sp = spearmanr(col, ident_ev.n_objects, nan_policy="omit")
        m = (col > 0) & (ident_ev.n_objects > 0)
        slope = float(np.polyfit(np.log10(col[m]), np.log10(ident_ev.n_objects[m]), 1)[0])
        t5e[name] = {"n": int(m.sum()), "spearman": float(sp.statistic),
                     "spearman_pvalue": float(sp.pvalue), "loglog_slope": slope}
    t5e["_note"] = ("DESCRIPTIVE ONLY. No pass/fail, no gate. Retired as a hard stop at "
                    "10c on Cooper's call. A positive relation is expected -- a bigger, "
                    "longer, more active event mechanically produces more sub-bursts under "
                    "any definition.")

    # ============================================================== T5f / 10d-R5
    r5c = C10D["escalation"]["R5_degenerate_decomposition"]
    floor_s = float(r5c["resolution_floor_s"])
    t5f_rows = []
    for k in KERNELS:
        for (K, dd, mp) in [(0, 0.0, 2), (5, 1.0, 2), (0, 0.0, 3), (5, 1.0, 3)]:
            g = hb[(hb.kernel_min == k) & (hb.K == K) & (hb.d == dd) & (hb.min_prints == mp)]
            if not len(g):
                continue
            per_ev = g.groupby(KEY).size()
            one_only = int((per_ev == 1).sum())
            t5f_rows.append({
                "kernel_min": float(k), "K": int(K), "d": float(dd), "min_prints": int(mp),
                "n_events": int(len(per_ev)),
                "events_single_subburst": one_only,
                "single_subburst_share": one_only / len(per_ev),
                "n_objects": int(len(g)),
                "at_resolution_floor": int((g.duration_s <= floor_s * 1.0001).sum()),
                "resolution_floor_share": float((g.duration_s <= floor_s * 1.0001).mean())})
    t5f = pd.DataFrame(t5f_rows)
    r5 = {"resolution_floor_s": floor_s,
          "max_single_subburst_share": float(t5f.single_subburst_share.max()),
          "threshold_single_subburst_share": r5c["session_spanning_share_max"],
          "max_resolution_floor_share": float(t5f.resolution_floor_share.max()),
          "threshold_resolution_floor_share": r5c["resolution_floor_share_max"],
          "fires": bool(t5f.single_subburst_share.max() > r5c["session_spanning_share_max"]
                        or t5f.resolution_floor_share.max() > r5c["resolution_floor_share_max"])}

    # ============================================================== T5g / 10d-R6
    per_k = {}
    for k in KERNELS:
        kp_ = t5a[t5a.kernel_min == k]
        per_k[f"{k:g}min"] = {
            "identity_median_s": float(kp_[kp_.read == "identity"].iloc[0]["median"]),
            "floor_only_mp3_decades": float(
                kp_[(kp_.read == "floor_only") & (kp_.min_prints == 3)].iloc[0].shift_decades),
            "merge_only_max_decades": float(
                kp_[kp_.read == "merge_only"].shift_decades.max()),
            "dominant": ("floor" if abs(float(kp_[(kp_.read == "floor_only")
                                                  & (kp_.min_prints == 3)].iloc[0].shift_decades))
                         > abs(float(kp_[kp_.read == "merge_only"].shift_decades.max()))
                         else "merge")}
    f_signs = [np.sign(v["floor_only_mp3_decades"]) for v in per_k.values()]
    m_signs = [np.sign(v["merge_only_max_decades"]) for v in per_k.values()]
    coherent = (max(f_signs.count(1), f_signs.count(-1)) >= 2
                or max(m_signs.count(1), m_signs.count(-1)) >= 2)
    any_material = any(abs(v["floor_only_mp3_decades"]) >= 0.05
                       or abs(v["merge_only_max_decades"]) >= 0.05 for v in per_k.values())
    r6 = {"per_kernel": per_k, "coherent_sign_at_2_of_3": bool(coherent),
          "any_kernel_material": bool(any_material),
          "dominant_agrees_across_kernels": len({v["dominant"] for v in per_k.values()}) == 1,
          "fires": bool(not coherent and not any_material)}

    # variant consistency: objects are variant-independent, so only segment mix moves
    var_rows = []
    for v in C10D["upstream_10c"]["variants"]:
        cv = ctx[ctx.variant == v][KEY + ["segment"]].copy()
        cv["segment"] = cv.segment.fillna("unlabelled")
        j = hb[(hb.kernel_min == KP) & (hb.min_prints == 2)].merge(cv, on=KEY, how="left")
        base = j[(j.K == 0) & (j.d == 0.0)]
        for s in SEGS:
            bs = base[base.segment == s]
            ms = j[(j.K == 5) & (j.d == 1.0) & (j.segment == s)]
            if not len(bs):
                continue
            var_rows.append({"variant": float(v), "segment": s,
                             "n_identity": int(len(bs)),
                             "identity_median_s": float(bs.duration_s.median()),
                             "merge_max_median_s": float(ms.duration_s.median()) if len(ms) else np.nan,
                             "merge_shift_decades": dec(ms.duration_s.median(),
                                                        bs.duration_s.median()) if len(ms) else np.nan})
    var = pd.DataFrame(var_rows)

    # ---------------------------------------------------------------- write
    t5a.to_parquet(os.path.join(ART, "t5_attribution_by_kernel.parquet"), index=False)
    t5a_seg.to_parquet(os.path.join(ART, "t5_attribution_by_segment.parquet"), index=False)
    t5b.to_parquet(os.path.join(ART, "t5_nprints_composition.parquet"), index=False)
    t5c.to_parquet(os.path.join(ART, "t5_separator_sensitivity.parquet"), index=False)
    t5f.to_parquet(os.path.join(ART, "t5_degeneracy.parquet"), index=False)
    var.to_parquet(os.path.join(ART, "t5_variant_consistency.parquet"), index=False)

    out = {"phase": "10d", "task": "T5", "config_hash": chash,
           "prior_version_figures": prior_figures(),
           "T5a_attribution": att,
           "T5b_composition_headline": {
               "identity": t5b[(t5b.kernel_min == KP) & (t5b.read == "identity")]
               .to_dict("records"),
               "floor_only": t5b[(t5b.kernel_min == KP) & (t5b.read == "floor_only")]
               .to_dict("records"),
               "merge_only_extremes": t5b[(t5b.kernel_min == KP) & (t5b.read == "merge_only")]
               .sort_values("prints_delta_vs_identity").iloc[[0, -1]].to_dict("records")},
           "T5c_separator": {
               "n_cells_compared": int(len(t5c)),
               "n_cells_identical": int(t5c.identical.sum()),
               "max_abs_count_rel_change": float(t5c.count_rel_change.abs().max()),
               "by_kernel_max": t5c.groupby("kernel_min").count_rel_change.max().to_dict()},
           "T5d_R3_parameter_dominance": r3,
           "T5e_count_vs_print_count": t5e,
           "T5f_R5_degeneracy": r5,
           "T5g_R6_kernel_variant": r6,
           "R4_separability": r4,
           "artifacts": {
               "by_kernel": "results/phase_10d/artifacts/t5_attribution_by_kernel.parquet",
               "by_segment": "results/phase_10d/artifacts/t5_attribution_by_segment.parquet",
               "composition": "results/phase_10d/artifacts/t5_nprints_composition.parquet",
               "separator": "results/phase_10d/artifacts/t5_separator_sensitivity.parquet",
               "degeneracy": "results/phase_10d/artifacts/t5_degeneracy.parquet",
               "variant": "results/phase_10d/artifacts/t5_variant_consistency.parquet"}}
    with open(os.path.join(ART, "t5_attribution.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print(f"=== ATTRIBUTION, kernel {KP:g} min, sep=hard_break ===")
    print(f"  identity median      {att['identity_median_s']*1e3:.4f} ms "
          f"(n={att['identity_n']:,})")
    print(f"  floor-only  mp=3     {att['floor_only_at_mp3_decades']:+.4f} decades")
    print(f"  floor-only  mp=5     {att['floor_only_at_mp5_decades']:+.4f} decades")
    print(f"  merge-only  max      {att['merge_only_max_shift_decades']:+.4f} decades")
    print(f"  merge-only  median   {att['merge_only_median_shift_decades']:+.4f} decades")
    print(f"  joint       max      {att['joint_max_shift_decades']:+.4f} decades")
    print(f"  interaction          {att['interaction_decades']:+.4f} decades")
    print(f"  DOMINANT MECHANISM   {att['dominant_mechanism'].upper()} "
          f"(ratio {att['ratio_floor_over_merge']:.2f}x)")
    print(f"\n  R3 fires={r3['fires']}  tol_rho dur={r3['tolerance_rho_duration']:.3f} "
          f"cnt={r3['tolerance_rho_count']:.3f} vs max event char "
          f"dur={r3['max_event_characteristic_rho_duration']:.3f} "
          f"cnt={r3['max_event_characteristic_rho_count']:.3f}")
    print(f"  R4 fires={r4['fires']}  |floor|={abs(f_abs):.4f} |merge|={abs(m_abs):.4f} "
          f"diff={r4['abs_difference_decades']:.4f} (min {sep_min})")
    print(f"  R5 fires={r5['fires']}  single-subburst max share "
          f"{r5['max_single_subburst_share']:.4f}, floor share "
          f"{r5['max_resolution_floor_share']:.4f}")
    print(f"  R6 fires={r6['fires']}  dominant per kernel: "
          f"{ {k: v['dominant'] for k, v in per_k.items()} }")
    print(f"\n  T5c separator: {int(t5c.identical.sum())}/{len(t5c)} cells identical, "
          f"max |count change| {t5c.count_rel_change.abs().max():.4%}")
    print(f"  T5e count vs prints: spearman {t5e['t0_print_count']['spearman']:.4f}, "
          f"slope {t5e['t0_print_count']['loglog_slope']:.4f} "
          f"(n={t5e['t0_print_count']['n']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
