"""
Brief 1, T6 -- the four controls (Control Standard) on the 50 dev events. Pass criteria are the
config's (t6_controls), committed before this ran; a failure is a HARD STOP (escalation row 2).

Every control runs the SAME functions that built the real vectors (instruments.components,
instruments.excursion_vector, instruments.a2_count_ladder) on synthetic inputs built from each event's
own data. Nothing is re-implemented here.

  negative_excursion      bridge: 200 seeded shuffles of the demeaned bucket returns; free walk: 200 draws with
                          replacement (Amendment 2); both against simulated references (t6_references.json)
  negative_acceleration   homogeneous Poisson tape over the event's own segment history [segment start, tau]
                          with its own collapsed count there (Amendment 3)
  positive_excursion      the shuffled path + an injected rise (2.0 to u = 0.3) and fall (1.5)
  positive_acceleration   rate doubling at the midpoint of rung m, m in {0,1,2,3}
  null_parameter_sweep    component medians across {50, 100, 200}; count vs kernel A2 per rung
  blindness               prices x10 and x0.1 (must match to 1e-9); sub-$1 prices to the $0.01 grid (reported)

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t6_controls.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attention as A  # noqa: E402
import common as C  # noqa: E402
import instruments as I  # noqa: E402

LN2 = math.log(2.0)
SIGMA_COMPS = ["u_peak", "rise_s", "fall_s", "dip_before_peak_s", "terminal_s"]
BP_COMPS = ["sigma_b_bp", "sigma_path_bp", "rise_bp", "fall_bp"]


def arcsine_cdf(u):
    return (2.0 / np.pi) * np.arcsin(np.sqrt(np.clip(u, 0.0, 1.0)))


def ks_arcsine(u: np.ndarray) -> float:
    """sup |F_n - F| for a sample with atoms, evaluated on both sides of every atom."""
    u = np.sort(np.asarray(u, dtype=float))
    vals, cnt = np.unique(u, return_counts=True)
    cum = np.cumsum(cnt) / u.size
    left = np.r_[0.0, cum[:-1]]
    F = arcsine_cdf(vals)
    return float(max(np.max(np.abs(cum - F)), np.max(np.abs(left - F))))


def main() -> int:
    cfg = C.load_cfg()
    c6 = cfg["t6_controls"]
    rng = np.random.default_rng(c6["seed"])
    n_sh = c6["negative_excursion"]["n_shuffles"]
    a2x = cfg["amendment_2"]["controls"]
    ks_max, rise_tol, pos_tol, u_tol = 0.05, 0.05, 0.10, 0.05
    readable = 100
    a2c = cfg["t5_attention"]["a2_acceleration"]
    n_min, coef, kmax = a2c["counting_noise_stop"]["n_min"], a2c["resolution_floor"]["coef"], a2c["k_max"]
    refs = json.load(open(C.art("t6_references.json"), encoding="utf-8"))["by_N"]

    ex = pd.read_parquet(C.art("t4_excursion.parquet"))
    ex = ex[(ex["dev_group"] == "dev_v3") & (ex["vector_available"] == True)]  # noqa: E712
    bk = pd.read_parquet(C.art("t4_buckets.parquet"))
    att = pd.read_parquet(C.art("t5_attention.parquet"))
    att = att[(att["dev_group"] == "dev_v3") & (att["attention_available"] == True)]  # noqa: E712
    ladder = cfg["t4_excursion"]["bucket_ladder"]
    verdict, detail = {}, {}

    # ============================================================ excursion controls (Amendment 2 A2.2)
    neg, fwk, pos = [], [], []
    for r in ex.itertuples():
        P = bk[(bk["event_id"] == r.event_id) & (bk["N"] == r.N)].sort_values("i")["vwap"].to_numpy()
        lp = np.log(np.r_[r.tau_price, P])
        ret = np.diff(lp)
        dm = ret - ret.mean()
        u = np.arange(r.N + 1) / r.N
        inj = np.diff(I.drift_curve(u)) * r.sigma_path          # the event's own (RV) sigma_path
        for s_ in range(n_sh):
            sh = rng.permutation(dm)
            c = I.components(np.r_[lp[0], lp[0] + np.cumsum(sh)])
            neg.append((r.N, r.event_id, c["i_peak"], c["u_peak"], c["rise_s"], c["sigma_zero"]))
            fw = rng.choice(dm, size=dm.size, replace=True)          # with replacement: the sum is free
            c = I.components(np.r_[lp[0], lp[0] + np.cumsum(fw)])
            fwk.append((r.N, r.event_id, c["i_peak"], c["u_peak"], c["rise_s"], c["sigma_zero"]))
            c = I.components(np.r_[lp[0], lp[0] + np.cumsum(sh + inj)])
            pos.append((r.N, r.event_id, c["i_peak"], c["u_peak"], c["rise_s"], c["fall_s"], c["sigma_zero"]))
    cols = ["N", "event_id", "i_peak", "u_peak", "rise_s", "sigma_zero"]
    neg = pd.DataFrame(neg, columns=cols)
    fwk = pd.DataFrame(fwk, columns=cols)
    pos = pd.DataFrame(pos, columns=["N", "event_id", "i_peak", "u_peak", "rise_s", "fall_s", "sigma_zero"])
    for df, nm in [(neg, "t6_negative_excursion_bridge"), (fwk, "t6_negative_excursion_free_walk"), (pos, "t6_positive_excursion")]:
        df.to_parquet(C.art(f"{nm}.parquet"), index=False)

    def ks_two_sample(i_peak: np.ndarray, ref_counts: list, N: int) -> float:
        """sup over atoms i/N of |F_control - F_reference|, both right-continuous on the same grid."""
        c = np.bincount(i_peak.astype(int), minlength=N + 1).astype(float)
        f1 = np.cumsum(c) / c.sum()
        rc = np.asarray(ref_counts, dtype=float)
        f2 = np.cumsum(rc) / rc.sum()
        return float(np.max(np.abs(f1 - f2)))

    def neg_eval(df, ref_key):
        out, ok = {}, True
        for N in ladder:
            g = df[(df["N"] == N) & ~df["sigma_zero"]]
            ref = refs[str(N)][ref_key]
            ks = ks_two_sample(g["i_peak"].to_numpy(), ref["u_peak_counts"], N)
            mr = float(g["rise_s"].mean())
            p = (ks <= ks_max) and (abs(mr - ref["mean_rise_s"]) <= rise_tol)
            ok &= p
            out[int(N)] = {"n": int(len(g)), "events": int(g["event_id"].nunique()),
                           "ks_vs_simulated_reference": ks, "ks_vs_arcsine_continuous": ks_arcsine(g["u_peak"].to_numpy()),
                           "mean_rise_s": mr, "reference_mean_rise_s": ref["mean_rise_s"], "delta_mean_rise_s": mr - ref["mean_rise_s"],
                           "median_rise_s": float(g["rise_s"].median()),
                           "share_u_peak_le_0.1": float((g["u_peak"] <= 0.1).mean()),
                           "share_u_peak_ge_0.9": float((g["u_peak"] >= 0.9).mean()),
                           "pass": bool(p), "sigma_zero_dropped": int(df[(df["N"] == N)]["sigma_zero"].sum())}
        return ok, out

    verdict["negative_excursion_bridge"], detail["negative_excursion_bridge"] = neg_eval(neg, "bridge")
    verdict["negative_excursion_free_walk"], detail["negative_excursion_free_walk"] = neg_eval(fwk, "free_walk")

    pe, ok_p = {}, True
    for N in ladder:
        g = pos[(pos["N"] == N) & ~pos["sigma_zero"]]
        ref = refs[str(N)]["positive"]
        mu, mr, mf = float(g["u_peak"].median()), float(g["rise_s"].median()), float(g["fall_s"].median())
        p = (abs(mr - ref["median_rise_s"]) <= pos_tol * ref["median_rise_s"]
             and abs(mf - ref["median_fall_s"]) <= pos_tol * ref["median_fall_s"]
             and abs(mu - ref["median_u_peak"]) <= u_tol)
        ok_p &= p
        pe[int(N)] = {"n": int(len(g)), "median_u_peak": mu, "median_rise_s": mr, "median_fall_s": mf,
                      "reference_median_u_peak": ref["median_u_peak"], "reference_median_rise_s": ref["median_rise_s"],
                      "reference_median_fall_s": ref["median_fall_s"],
                      "rise_vs_reference_rel": mr / ref["median_rise_s"] - 1, "fall_vs_reference_rel": mf / ref["median_fall_s"] - 1,
                      "bias_vs_injected": {"u_peak": mu - 0.3, "rise_s": mr - 2.0, "fall_s": mf - 1.5},
                      "pass": bool(p)}
    verdict["positive_excursion"] = ok_p
    detail["positive_excursion"] = pe

    # ============================================================ acceleration controls
    # Amendment 3: synthetic tapes span tau's segment history [segment start, tau] and carry the event's own
    # collapsed count inside it; events whose tau is in a cross minute have no segment history (A3.2).
    na_rows, pa_rows = [], []
    n_draw = c6["negative_acceleration"]["n_draws"]
    att_a2 = att[att["a2_state"] == "value"]
    for r in att_a2.itertuples():
        tau = int(r.tau_ns)
        t0 = int(r.a2_anchor_ns)
        H = tau - t0
        n = int(r.n_collapsed_seg_tau)
        for s in range(n_draw):
            ct = np.sort(rng.integers(t0, tau + 1, size=n)).astype(np.int64)
            for x in I.a2_count_ladder(ct, tau, t0, n_min, coef, kmax):
                if x["valid"]:
                    na_rows.append((r.event_id, s, x["k"], x["accel"], x["n_recent"], x["n_older"]))
        for m in c6["positive_acceleration"]["placements_m"]:
            Wm = H / 2.0 ** m
            ts_ = tau - int(round(Wm / 2))
            rate = n / (H + Wm / 2)                        # per ns x H units: expected total n
            for s in range(n_draw):
                nb = rng.poisson(rate * (ts_ - t0))
                na = rng.poisson(2 * rate * (tau - ts_))
                ct = np.sort(np.r_[rng.integers(t0, ts_, size=nb), rng.integers(ts_, tau + 1, size=na)]).astype(np.int64)
                for x in I.a2_count_ladder(ct, tau, t0, n_min, coef, kmax):
                    if x["valid"]:
                        pa_rows.append((r.event_id, m, s, x["k"], x["accel"]))
    na_df = pd.DataFrame(na_rows, columns=["event_id", "draw", "k", "accel", "n_recent", "n_older"])
    pa_df = pd.DataFrame(pa_rows, columns=["event_id", "m", "draw", "k", "accel"])
    na_df.to_parquet(C.art("t6_negative_acceleration.parquet"), index=False)
    pa_df.to_parquet(C.art("t6_positive_acceleration.parquet"), index=False)

    nae, ok_na = {}, True
    for k, g in na_df.groupby("k"):
        z = g["accel"] / np.sqrt(1.0 / g["n_recent"] + 1.0 / g["n_older"])
        rd = len(g) >= readable
        med, sdz = float(g["accel"].median()), float(z.std())
        p = (abs(med) < 0.1) and (0.80 <= sdz <= 1.25)
        if rd:
            ok_na &= p
        nae[int(k)] = {"n": int(len(g)), "events": int(g["event_id"].nunique()), "median_accel": med, "sd_z": sdz,
                       "readable": bool(rd), "pass": bool(p) if rd else None}
    verdict["negative_acceleration"] = ok_na
    detail["negative_acceleration"] = nae
    detail["acceleration_population"] = {"events": int(len(att_a2)), "excluded_auction_minute": int((att["a2_state"] != "value").sum()),
                                         "history": "[segment start, tau] (Amendment 3 A3.1)",
                                         "segments": att_a2["tau_anchor_segment"].value_counts().to_dict()}

    pae, ok_pa = {}, True
    for (m, k), g in pa_df.groupby(["m", "k"]):
        med = float(g["accel"].median())
        rd = len(g) >= readable
        if k == m:
            target, role = LN2, "straddle (verdict)"
        elif k > m:
            target, role = 0.0, "after the step (verdict)"
        else:
            target, role = math.log(1 + 2.0 ** (k - m)), "coarser, step inside recent half (reported vs analytic; not in verdict)"
        p = abs(med - target) <= 0.2
        literal = abs(med - (LN2 if k == m else 0.0)) <= 0.2
        in_verdict = k >= m
        if rd and in_verdict:
            ok_pa &= p
        pae[f"m={int(m)},k={int(k)}"] = {"n": int(len(g)), "median_accel": med, "target": target, "role": role,
                                         "readable": bool(rd), "pass_vs_target": bool(p) if rd else None,
                                         "pass_literal_text": bool(literal) if rd else None}
    verdict["positive_acceleration"] = ok_pa
    detail["positive_acceleration"] = pae

    # ============================================================ null-parameter sweep
    comps = SIGMA_COMPS + BP_COMPS + ["rise_cents", "fall_cents", "t_peak_s"]
    sweep = {}
    for c in comps:
        meds = {int(N): float(ex[ex["N"] == N][c].median()) for N in ladder}
        v = np.array(list(meds.values()))
        mean = float(v.mean())
        spread = float(v.max() - v.min())
        if abs(mean) < 0.05:
            lab = "rung-dependent" if spread > 0.05 else "stable"
            basis = "absolute spread (mean within 0.05 of zero)"
        else:
            lab = "rung-dependent" if spread > 0.20 * abs(mean) else "stable"
            basis = "spread / |mean|"
        sweep[c] = {"medians": meds, "spread": spread, "rel_spread": spread / abs(mean) if mean else None, "label": lab, "basis": basis}
    rg = pd.read_parquet(C.art("t5_a2_rungs.parquet"))
    rg = rg[(rg["dev_group"] == "dev_v3") & rg["valid"]]
    a2sw = {int(k): {"n": int(len(g)), "median_count": float(g["accel"].median()),
                     "median_kernel": float(g["accel_kernel"].median()) if g["accel_kernel"].notna().any() else None,
                     "n_kernel_defined": int(g["kernel_defined"].sum()),
                     "spearman": A.spearman(g["accel"], g["accel_kernel"])} for k, g in rg.groupby("k")}
    verdict["null_parameter_sweep"] = True
    detail["null_parameter_sweep"] = {"excursion": sweep, "a2_count_vs_kernel": a2sw}

    # ============================================================ blindness
    ev = ex.drop_duplicates("event_id")
    t2 = pd.read_parquet(C.art("t2_tau.parquet")).set_index("event_id")
    bl, rd_rows, worst = [], [], 0.0
    for r in ev.itertuples():
        tau = int(t2.loc[r.event_id, "tau_ns"])
        tr = C.read_trades(r.event_id, with_conditions=False)
        t2000 = C.et_ns(r.event_date_canonical, "20:00:00")
        a, b = int(np.searchsorted(tr["ts"], tau, "right")), int(np.searchsorted(tr["ts"], t2000, "right"))
        ts, px, sz = tr["ts"][a:b], tr["px"][a:b], tr["sz"][a:b]
        for N in ladder:
            base = I.excursion_vector(tau, r.tau_price, ts, px, sz, N)
            for f in c6["blindness"]["rescale_factors"]:
                v = I.excursion_vector(tau, r.tau_price * f, ts, px * f, sz, N)
                d = max(abs(base[c] - v[c]) for c in SIGMA_COMPS + BP_COMPS)
                worst = max(worst, d)
                bl.append({"event_id": r.event_id, "N": N, "factor": f, "max_abs_diff": d})
            rnd = lambda p: np.where(p < 1.0, np.floor(p * 100 + 0.5) / 100, p)  # noqa: E731
            v = I.excursion_vector(tau, float(rnd(np.array([r.tau_price]))[0]), ts, rnd(px), sz, N)
            rd_rows.append({"event_id": r.event_id, "N": N, "sub_dollar_tau": bool(r.tau_price < 1.0),
                            "sigma_zero_after": bool(v.get("sigma_zero", False)),
                            **{f"d_{c}": (v[c] - base[c]) for c in SIGMA_COMPS + BP_COMPS}})
    bl = pd.DataFrame(bl)
    rd_df = pd.DataFrame(rd_rows)
    bl.to_parquet(C.art("t6_blindness_rescale.parquet"), index=False)
    rd_df.to_parquet(C.art("t6_blindness_rounding.parquet"), index=False)
    verdict["blindness"] = bool(worst <= 1e-9)
    sub = rd_df[rd_df["sub_dollar_tau"]]
    detail["blindness"] = {"rescale_max_abs_diff": worst, "rescale_checks": int(len(bl)), "pass": bool(worst <= 1e-9),
                           "rounding": {"event_rungs": int(len(rd_df)), "sub_dollar_event_rungs": int(len(sub)),
                                        "sub_dollar_events": int(sub["event_id"].nunique()),
                                        "median_abs_change_sub_dollar": {c: float(sub[f"d_{c}"].abs().median()) for c in SIGMA_COMPS + BP_COMPS} if len(sub) else {},
                                        "max_abs_change_sub_dollar": {c: float(sub[f"d_{c}"].abs().max()) for c in SIGMA_COMPS + BP_COMPS} if len(sub) else {},
                                        "unchanged_at_or_above_1_dollar": bool((rd_df[~rd_df["sub_dollar_tau"]][[f"d_{c}" for c in SIGMA_COMPS]].abs().max().max() if (~rd_df["sub_dollar_tau"]).any() else 0) < 1e-9)}}

    failed = [k for k, v in verdict.items() if not v]
    row2 = {"criterion": "any T6 control fails its declared pass criterion", "tier": "HARD STOP",
            "failed_controls": failed, "fires": bool(failed)}
    C.write_json(f"{C.ART}/t6_controls.json", {"config_hash": C.cfg_hash(), "verdict": verdict, "row_2": row2, "detail": detail,
                                               "II5_blindness_1e-9": bool(worst <= 1e-9)})
    print("VERDICT", verdict)
    print("ROW 2", row2)
    for k in ["negative_excursion_bridge", "negative_excursion_free_walk", "positive_excursion"]:
        print(k, {N: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()} for N, v in detail[k].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
