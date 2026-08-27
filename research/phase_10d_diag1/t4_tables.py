"""
10d Diagnostic 1, T4a/T4c -- the tables behind every chart, and the
stationary-or-shifting verdict.

DESCRIPTION ONLY. No boundary rule is adopted, no parameter tuned, no cutoff applied.

Usage: .venv/Scripts/python.exe research/phase_10d_diag1/t4_tables.py
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ART = os.path.join(ROOT, "results", "phase_10d_diag1", "artifacts")
KEY = ["ticker", "event_date_canonical"]
KP = 8.0


def q(a, ks=(0, .25, .5, .75, 1)):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), **{f"q{int(k*100)}": float(np.quantile(a, k)) for k in ks}}


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d_diag1.json"), encoding="utf-8") as f:
        Cc = json.load(f)
    chash = hashlib.sha256(json.dumps(Cc, sort_keys=True).encode()).hexdigest()[:8]
    fr = pd.read_parquet(os.path.join(ART, "t1_frames.parquet"))
    tr = pd.read_parquet(os.path.join(ART, "t1_troughs.parquet"))
    st = pd.read_parquet(os.path.join(ART, "t1_frame_steps.parquet"))
    refs = list(zip(Cc["reference_lines_s"], ["1ms", "10ms", "100ms", "1s", "10s"]))

    frt = fr[fr.frame_index >= 0]
    trt = tr[tr.frame_index >= 0]
    ok8 = frt[(frt.kernel_min == KP) & (frt.label == "ok")].copy()
    tr8 = trt[trt.kernel_min == KP]

    # ---------------------------------------------------- T4a: boundary tracks
    per_event = []
    for (t, d), g in ok8.groupby(KEY):
        gg = g.sort_values("frame_index")
        hop = np.abs(np.diff(gg.winner_norm.to_numpy()))
        per_event.append({
            "ticker": t, "event_date_canonical": d, "kernel_min": KP,
            "n_ok_frames": int(len(g)),
            "abs_s": q(g.winner_abs_s), "norm_dec": q(g.winner_norm),
            "local_median_s": q(g.local_median_s),
            "sd_log10_abs": float(np.log10(g.winner_abs_s).std()),
            "sd_log10_local_median": float(np.log10(g.local_median_s).std()),
            "sd_norm": float(g.winner_norm.std()),
            "frame_to_frame_hop_median_dec": float(np.median(hop)) if hop.size else np.nan,
            "share_hops_over_0p5_dec": float((hop > 0.5).mean()) if hop.size else np.nan,
            "share_hops_over_1p0_dec": float((hop > 1.0).mean()) if hop.size else np.nan})

    # ---------------------------------------------------- T4c: variance decomposition
    def decomp(g):
        la = np.log10(g.winner_abs_s.to_numpy())
        lm = np.log10(g.local_median_s.to_numpy())
        nm = g.winner_norm.to_numpy()
        v = la.var()
        if v == 0 or not np.isfinite(v):
            return {"var_log10_abs": float(v), "share_local_median": np.nan,
                    "share_normalized": np.nan, "share_2cov": np.nan}
        return {"var_log10_abs": float(v),
                "share_local_median": float(lm.var() / v),
                "share_normalized": float(nm.var() / v),
                "share_2cov": float(2 * np.cov(lm, nm)[0, 1] / v)}

    dec_pooled = decomp(ok8)
    dec_event = [{"ticker": t, "event_date_canonical": d, "n": int(len(g)), **decomp(g)}
                 for (t, d), g in ok8.groupby(KEY)]
    hop_all = np.concatenate([np.abs(np.diff(g.sort_values("frame_index")
                                             .winner_norm.to_numpy()))
                              for _, g in ok8.groupby(KEY) if len(g) > 1])
    verdict = {
        "question": "is the histogram's shape stationary or shifting, and does the boundary "
                    "track the shape or jump between modes?",
        "pooled_sd_log10_absolute_boundary_dec": float(np.log10(ok8.winner_abs_s).std()),
        "pooled_sd_log10_local_median_dec": float(np.log10(ok8.local_median_s).std()),
        "pooled_sd_normalized_boundary_dec": float(ok8.winner_norm.std()),
        "variance_decomposition_pooled": dec_pooled,
        "variance_decomposition_per_event": dec_event,
        "frame_to_frame_hop_median_dec": float(np.median(hop_all)),
        "share_hops_over_0p5_dec": float((hop_all > 0.5).mean()),
        "share_hops_over_1p0_dec": float((hop_all > 1.0).mean()),
        "n_consecutive_frame_pairs": int(hop_all.size),
        "statement": (
            "NOT STATIONARY AND NOT STABLE, and the movement is not the denominator's. "
            "Pooled over 8-min frames the winner's NORMALIZED position has sd "
            f"{float(ok8.winner_norm.std()):.3f} decades against sd "
            f"{float(np.log10(ok8.local_median_s).std()):.3f} decades for the local median, "
            "so the position on the shape moves about twice as much as the normalization "
            "denominator does. The normalized term accounts for "
            f"{dec_pooled['share_normalized']:.0%} of the variance of the absolute boundary "
            f"and the cross term is {dec_pooled['share_2cov']:.0%} — the two partly cancel, "
            "which is why the absolute track looks calmer than either component. "
            f"Consecutive frames overlap by 7/8 of their window, yet the winner moves by "
            f"more than 0.5 decades between "
            f"{float((hop_all > 0.5).mean()):.1%} of adjacent frame pairs and by more than "
            f"1.0 decade between {float((hop_all > 1.0).mean()):.1%}. A boundary that "
            "relocates by a factor of ten between two windows sharing 87.5% of their data "
            "is not tracking a slowly-moving shape; it is switching between candidates. "
            "Chart 03 shows why there are candidates to switch between."),
        "_caveat": ("USEG contributes 9 ok frames of 961 and its sd is ~0 by having almost "
                    "no frames; it is included in the pooled figure and reported "
                    "separately so it cannot be mistaken for stability."),
    }

    # ---------------------------------------------------- ladder / reach tables
    reach = []
    for v, lab in refs:
        row = {"threshold": lab, "threshold_s": v,
               "any_candidate_share": float((trt.loc_abs_s >= v).mean()),
               "any_candidate_n": int((trt.loc_abs_s >= v).sum()),
               "winner_share": float((trt[trt["rank"] == 0].loc_abs_s >= v).mean()),
               "winner_n": int((trt[trt["rank"] == 0].loc_abs_s >= v).sum())}
        for k in Cc["upstream"]["kernels_min"]:
            g = trt[trt.kernel_min == k]
            row[f"any_k{k:g}"] = float((g.loc_abs_s >= v).mean())
            row[f"winner_k{k:g}"] = float((g[g["rank"] == 0].loc_abs_s >= v).mean())
        reach.append(row)

    by_rank = []
    for r_ in sorted(tr8["rank"].unique())[:12]:
        g = tr8[tr8["rank"] == r_]
        by_rank.append({"rank": int(r_), "n": int(len(g)),
                        "median_abs_s": float(g.loc_abs_s.median()),
                        "q25_abs_s": float(g.loc_abs_s.quantile(.25)),
                        "q75_abs_s": float(g.loc_abs_s.quantile(.75)),
                        "median_void": float(g.void.median()),
                        "median_norm_dec": float(g.loc_norm.median()),
                        **{f"share_ge_{lab}": float((g.loc_abs_s >= v).mean())
                           for v, lab in refs}})

    piv = tr8.pivot_table(index=KEY + ["frame_index"], columns="rank",
                          values=["loc_abs_s", "void"])
    both = piv.dropna(subset=[("void", 0), ("void", 1)])
    gap = (both[("void", 0)] - both[("void", 1)]).to_numpy()
    r0, r1 = both[("loc_abs_s", 0)].to_numpy(), both[("loc_abs_s", 1)].to_numpy()
    runner = {"n_frames_with_two_or_more": int(len(both)),
              "void_gap": q(gap), "median_void_gap": float(np.median(gap)),
              "share_gap_below_0p05": float((gap < 0.05).mean()),
              "share_gap_below_0p10": float((gap < 0.10).mean()),
              "median_winner_s": float(np.median(r0)),
              "median_runnerup_s": float(np.median(r1)),
              "share_runnerup_coarser": float((r1 > r0).mean()),
              "statement": (
                  "The runner-up is NOT systematically the coarse candidate: it is coarser "
                  f"than the winner in {float((r1 > r0).mean()):.1%} of frames, close to a "
                  "coin flip, and its median location "
                  f"({float(np.median(r1))*1e3:.3f} ms) is within a few percent of the "
                  f"winner's ({float(np.median(r0))*1e3:.3f} ms). The coarse candidates sit "
                  "further down the ladder — see by_rank, where median absolute location "
                  "rises monotonically with rank.")}

    modes = {"n_ok_frames": int(len(ok8)),
             "peaks": q(ok8.n_peaks), "troughs": q(ok8.n_troughs),
             "share_exactly_two_peaks": float((ok8.n_peaks == 2).mean()),
             "share_three_or_more_peaks": float((ok8.n_peaks >= 3).mean()),
             "n_exactly_two_peaks": int((ok8.n_peaks == 2).sum()),
             "median_peaks": float(ok8.n_peaks.median()),
             "label_shares": (frt[frt.kernel_min == KP].label.value_counts(normalize=True)
                              .to_dict()),
             "label_counts": frt[frt.kernel_min == KP].label.value_counts().to_dict(),
             "statement": (
                 "The void parameter grades a trough against two flanking peaks, a "
                 "construction that presumes two modes. At 8-min frame resolution "
                 f"{float((ok8.n_peaks >= 3).mean()):.1%} of frames carrying a boundary hold "
                 f"three or more surviving peaks (median {int(ok8.n_peaks.median())}, range "
                 f"{int(ok8.n_peaks.min())}-{int(ok8.n_peaks.max())}); only "
                 f"{int((ok8.n_peaks == 2).sum())} of {len(ok8):,} are the two-peak case.")}

    cross = []
    for k in Cc["upstream"]["kernels_min"]:
        g = frt[(frt.kernel_min == k) & (frt.label == "ok")]
        gl = trt[trt.kernel_min == k]
        cross.append({"kernel_min": k, "n_ok_frames": int(len(g)),
                      "winner_abs_s": q(g.winner_abs_s),
                      "local_median_s": q(g.local_median_s),
                      "winner_norm_dec": q(g.winner_norm),
                      "median_peaks": float(g.n_peaks.median()) if len(g) else np.nan,
                      "n_candidates": int(len(gl)),
                      "share_any_candidate_ge_100ms": float((gl.loc_abs_s >= 0.1).mean())})

    frames_tbl = st.to_dict("records")
    thin = frt.groupby("kernel_min").apply(
        lambda g: pd.Series({"n_frames": len(g),
                             "thin_share": float((g.label == "thin").mean()),
                             "ok_share": float((g.label == "ok").mean())}),
        include_groups=False).reset_index().to_dict("records")

    out = {"diagnostic": "10d-diag1", "task": "T4a/T4c", "config_hash": chash,
           "_config_hash_note": ("computed with an EXPLICIT UTF-8 read. This config contains "
                                 "non-ASCII characters in its _why strings, so reading it "
                                 "under the Windows default cp1252 gives a different parsed "
                                 "object and the different hash 2e15b95e. config/phase_10d.json "
                                 "is pure ASCII and is unaffected. Third hash-reproducibility "
                                 "defect found in this lineage, after 10c's raw-byte "
                                 "line-ending sensitivity and its stale recorded value."),
           "causal_status": ("NON-CAUSAL throughout. Centered window; every frame reads "
                             "forward by half a kernel. Nothing here is a detector, a signal "
                             "or an operating point. No causal debt is retired."),
           "T4c_verdict": verdict,
           "T4a_per_event_boundary_track": per_event,
           "T4a_reach_by_reference_line": reach,
           "T4a_by_ladder_rank_kernel8": by_rank,
           "T4a_winner_vs_runnerup": runner,
           "T4a_mode_counts_kernel8": modes,
           "T4a_cross_kernel": cross,
           "T4a_frame_steps": frames_tbl,
           "T4a_frame_labels_by_kernel": thin}
    with open(os.path.join(ART, "t4_tables.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print("=== T4c VERDICT ===")
    print(verdict["statement"])
    print()
    print("=== reach: share of candidates at or above each line (all kernels) ===")
    for r_ in reach:
        print(f"  >= {r_['threshold']:>5}: any {r_['any_candidate_share']:6.2%} "
              f"({r_['any_candidate_n']:,})   winner {r_['winner_share']:6.2%} "
              f"({r_['winner_n']:,})")
    print()
    print("=== by ladder rank, kernel 8 ===")
    for b in by_rank[:9]:
        print(f"  rank {b['rank']}: n={b['n']:>5,}  median {b['median_abs_s']*1e3:9.3f} ms  "
              f"void {b['median_void']:.3f}  >=100ms {b['share_ge_100ms']:6.1%}  "
              f">=1s {b['share_ge_1s']:5.1%}")
    print()
    print(f"=== modes: {modes['share_three_or_more_peaks']:.1%} of ok frames have 3+ peaks; "
          f"median {modes['median_peaks']:.0f} ===")
    print(f"=== runner-up coarser in {runner['share_runnerup_coarser']:.1%} of frames; "
          f"median void gap {runner['median_void_gap']:.4f} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
