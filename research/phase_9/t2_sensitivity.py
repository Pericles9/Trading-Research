"""
Phase 9 T2 - Phase 8 cross-session sensitivity restatement.

Recomputes the Phase 8 cross-session statistics - t0_close -> t1_close and
t0_close -> t3_close, pooled and by pq_rth_open quintile and era - in four
variants:

  (i)   untrimmed all          <- the PRIMARY. No exclusion.
  (ii)  flagged carried but reported separately (flagged / unflagged rows)
  (iii) flagged excluded       (flag_cross_session_extreme = TRUE removed)
  (iv)  trimmed to trim_ratio_bounds (default 0.55-1.80)

Note on (iii) vs (iv): the flag threshold ln(1.8) corresponds to a ratio band
[0.5556, 1.8], and the configured trim bounds are [0.55, 1.80]. The two sets
differ only on the sliver 0.55 <= ratio < 0.5556. They are near-duplicate
views by construction, not independent checks. Reported as measured.

Base population is Phase 8's own a102_contamination.parquet - the artifact
being restated - which already excludes the Phase 8 flagged union (no_baseline,
has_t_minus_1_rth FALSE, denom_nonpositive, dup-prints, row-cap). A full-D1
supplementary population is reported alongside so the effect of that prior
exclusion is visible.

Cross-check: markouts are recomputed independently from Phase 9 session closes
and compared against Phase 8's stored markout, to prove the two price paths
agree before any variant is read.

Escalation row 6: flagged share in any single quintile > 2x the pooled share.
Escalation row 7: median sign flip between variant (i) and variant (iii) on
any headline cell.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_9 import common as C

FLAGS = f"{C.ART}/t1_cross_session_flags.parquet"
OUT_JSON = f"{C.ART}/t2_cross_session_sensitivity.json"

HORIZON_PAIR = {"t1_close": "t0_t1", "t3_close": "t0_t3"}
QUINTILES = [1, 2, 3, 4, 5]


def main():
    cfg = C.load_cfg()
    lo, hi = cfg["trim_ratio_bounds"]

    con = C.connect()
    d1 = C.d1_frame()
    wide = C.closes_wide(con, d1)

    flags = pd.read_parquet(FLAGS)
    flags["event_date_canonical"] = pd.to_datetime(flags["event_date_canonical"])

    # ---------- base: Phase 8's own cross-session artifact ----------
    base = pd.read_parquet(C.CONTAM_PATH)
    base["event_date_canonical"] = pd.to_datetime(base["event_date_canonical"])
    base = base[base.anchor_name == "t0_close"].copy()

    # ---------- cross-check Phase 9 closes vs Phase 8 markouts ----------
    chk = base.merge(wide[C.KEY + ["close_t0", "close_t1", "close_t3"]], on=C.KEY, how="left")
    chk["p9_markout"] = np.where(
        chk.horizon_name == "t1_close",
        np.log(chk["close_t1"] / chk["close_t0"]),
        np.log(chk["close_t3"] / chk["close_t0"]))
    d = (chk["p9_markout"] - chk["markout"]).abs()
    crosscheck = {
        "n_compared": int(d.notna().sum()),
        "max_abs_diff": (float(d.max()) if d.notna().any() else None),
        "n_diff_gt_1e_9": int((d > 1e-9).sum()),
        "note": "Phase 9 session closes vs Phase 8 t4_anchors ASOF prices; same convention, expected identical",
    }
    print(f"cross-check vs Phase 8 markouts: n={crosscheck['n_compared']:,} "
          f"max|diff|={crosscheck['max_abs_diff']:.3e} n(diff>1e-9)={crosscheck['n_diff_gt_1e_9']}")

    # ---------- attach the T1 flag per (event, session pair) ----------
    def attach(df):
        out = []
        for h, pair in HORIZON_PAIR.items():
            s = df[df.horizon_name == h].copy()
            f = flags[flags.session_pair == pair][C.KEY + ["flag_cross_session_extreme", "ratio"]]
            s = s.merge(f, on=C.KEY, how="left")
            s["flag_cross_session_extreme"] = s["flag_cross_session_extreme"].fillna(False).astype(bool)
            out.append(s)
        return pd.concat(out, ignore_index=True)

    B = attach(base)
    B = B[B.markout.notna()].copy()
    B["ratio"] = B["ratio"].fillna(np.exp(B["markout"]))

    # full-D1 supplementary population (no Phase 8 flagged-union exclusion)
    full = []
    for h, pair in HORIZON_PAIR.items():
        col = "close_t1" if h == "t1_close" else "close_t3"
        s = wide[C.KEY + ["era", "close_t0", col]].copy()
        s = s[s["close_t0"].gt(0) & s[col].gt(0)]
        s["horizon_name"] = h
        s["markout"] = np.log(s[col] / s["close_t0"])
        s["ratio"] = np.exp(s["markout"])
        f = flags[flags.session_pair == pair][C.KEY + ["flag_cross_session_extreme"]]
        s = s.merge(f, on=C.KEY, how="left")
        s["flag_cross_session_extreme"] = s["flag_cross_session_extreme"].fillna(False).astype(bool)
        full.append(s[C.KEY + ["era", "horizon_name", "markout", "ratio", "flag_cross_session_extreme"]])
    F = pd.concat(full, ignore_index=True)

    # ---------- variant slicers ----------
    def variants(df):
        return {
            "i_untrimmed_all": df,
            "ii_flagged_only": df[df.flag_cross_session_extreme],
            "ii_unflagged_only": df[~df.flag_cross_session_extreme],
            "iii_flagged_excluded": df[~df.flag_cross_session_extreme],
            "iv_trimmed": df[df.ratio.between(lo, hi)],
        }

    def grid(df, bucket_col, bucket_vals):
        out = {}
        for h in HORIZON_PAIR:
            hs = df[df.horizon_name == h]
            for vname, vdf in variants(hs).items():
                cells = {"pooled": C.cell_stats(vdf["markout"])}
                for b in bucket_vals:
                    cells[str(b)] = C.cell_stats(vdf.loc[vdf[bucket_col] == b, "markout"])
                out[f"t0_close->{h}|{vname}"] = cells
        return out

    results = {
        "by_quintile_pq_rth_open": grid(B, "pq_rth_open", QUINTILES),
        "by_era": grid(B, "era", C.ERAS),
        "full_d1_by_era": grid(F, "era", C.ERAS),
    }

    # ---------- T2a: flagged share per quintile ----------
    flagged_share = {}
    row6_rows = []
    for h in HORIZON_PAIR:
        hs = B[B.horizon_name == h]
        pooled = float(hs["flag_cross_session_extreme"].mean())
        per_q = {}
        for qv in QUINTILES:
            s = hs[hs.pq_rth_open == qv]
            sh = float(s["flag_cross_session_extreme"].mean()) if len(s) else None
            per_q[f"Q{qv}"] = {"n": int(len(s)),
                               "n_flagged": int(s["flag_cross_session_extreme"].sum()),
                               "flagged_share": sh,
                               "exceeds_2x_pooled": bool(sh is not None and pooled > 0 and sh > 2 * pooled)}
            if per_q[f"Q{qv}"]["exceeds_2x_pooled"]:
                row6_rows.append({"horizon": h, "quintile": f"Q{qv}",
                                  "quintile_share": sh, "pooled_share": pooled})
        flagged_share[f"t0_close->{h}"] = {"pooled_share": pooled, "n_pooled": int(len(hs)),
                                           "per_quintile": per_q}

    # ---------- escalation row 7: median sign flip (i) vs (iii) ----------
    row7_rows = []
    for gname, g in results.items():
        for key, cells in g.items():
            if "|i_untrimmed_all" not in key:
                continue
            k3 = key.replace("|i_untrimmed_all", "|iii_flagged_excluded")
            for cell, v1 in cells.items():
                v3 = g.get(k3, {}).get(cell)
                if not v3 or v1["median"] is None or v3["median"] is None:
                    continue
                if np.sign(v1["median"]) != np.sign(v3["median"]) and v1["median"] != 0 and v3["median"] != 0:
                    row7_rows.append({"grid": gname, "cell_key": key, "cell": cell,
                                      "median_untrimmed": v1["median"], "n_untrimmed": v1["n"],
                                      "median_flag_excluded": v3["median"], "n_flag_excluded": v3["n"]})

    # ---------- headline pooled table (the sign-flip statistic) ----------
    headline = {}
    for h in HORIZON_PAIR:
        hs = B[B.horizon_name == h]
        for vname, vdf in variants(hs).items():
            headline[f"t0_close->{h}|{vname}"] = C.cell_stats(vdf["markout"])

    waterfall = [
        {"step": "Phase 8 a102_contamination.parquet, anchor t0_close",
         "rows_in": int(len(base)), "rows_out": int(len(base)),
         "dropped": 0, "why": "base population as Phase 8 left it (flagged union already excluded there)"},
        {"step": "markout non-null", "rows_in": int(len(base)), "rows_out": int(len(B)),
         "dropped": int(len(base) - len(B)), "why": "horizon session absent in v2 or non-positive price"},
        {"step": "full-D1 supplementary, both closes present and > 0",
         "rows_in": int(len(wide) * 2), "rows_out": int(len(F)),
         "dropped": int(len(wide) * 2 - len(F)), "why": "T+1/T+3 session absent in v2 (offsets -3..+3 only)"},
    ]

    summary = {
        "phase": "9", "task": "T2",
        "source": "research/phase_9/t2_sensitivity.py:main",
        "repro": "python -m research.phase_9.t2_sensitivity",
        "config_hash": C.cfg_hash(),
        "scan_free": True, "tables_touched": ["event_minute_bars_v2"],
        "spine_numeric_reads": 0,
        "primary_variant": "i_untrimmed_all",
        "variant_overlap_note": ("(iii) and (iv) are near-duplicates by construction: the flag band is "
                                 f"[{np.exp(-cfg['ca_flag_log_threshold']):.4f}, {np.exp(cfg['ca_flag_log_threshold']):.4f}] "
                                 f"and the trim bounds are [{lo}, {hi}]; they differ only on 0.55 <= ratio < 0.5556"),
        "trim_ratio_bounds": [lo, hi],
        "base_population": "results/phase_8/artifacts/a102_contamination.parquet (Phase 8 flagged union already excluded)",
        "crosscheck_phase8_markouts": crosscheck,
        "headline_pooled": headline,
        "grids": results,
        "flagged_share_per_quintile": flagged_share,
        "filter_waterfall": waterfall,
        "escalation_row_6": {
            "condition": "flagged share in any single quintile > 2x pooled share",
            "triggered": len(row6_rows) > 0, "rows": row6_rows},
        "escalation_row_7": {
            "condition": "median flips sign between variant (i) untrimmed and variant (iii) flag-excluded on any headline cell",
            "triggered": len(row7_rows) > 0, "rows": row7_rows},
    }
    C.write_json(summary, OUT_JSON)

    # ---------------- console ----------------
    print("\nHEADLINE pooled, by variant:")
    print(f"{'cell':52s} {'n':>7s} {'median':>10s} {'mean_log':>10s} {'mean_simple':>12s}")
    for k, v in headline.items():
        ms = "n/a" if v["mean_simple"] is None else f"{v['mean_simple']:+.4%}"
        md = "n/a" if v["median"] is None else f"{v['median']:+.5f}"
        ml = "n/a" if v["mean_log"] is None else f"{v['mean_log']:+.5f}"
        print(f"{k:52s} {v['n']:7,d} {md:>10s} {ml:>10s} {ms:>12s}")

    print("\nT2a flagged share per pq_rth_open quintile (escalation row 6):")
    for k, v in flagged_share.items():
        print(f"  {k}  pooled {v['pooled_share']:.3%} (n={v['n_pooled']:,})")
        for qk, qv in v["per_quintile"].items():
            mark = "  <-- >2x pooled" if qv["exceeds_2x_pooled"] else ""
            print(f"     {qk}: {qv['n_flagged']:3d}/{qv['n']:5,d} = {(qv['flagged_share'] or 0):.3%}{mark}")

    print(f"\nESCALATION ROW 6: {'*** TRIGGERED ***' if row6_rows else 'pass'}")
    print(f"ESCALATION ROW 7: {'*** TRIGGERED ***' if row7_rows else 'pass'}")
    for r in row7_rows:
        print(f"   {r['cell_key']} [{r['cell']}]: untrimmed {r['median']:+.5f} (n={r['n_untrimmed']:,}) "
              f"-> flag-excluded {r['median_flag_excluded']:+.5f} (n={r['n_flag_excluded']:,})"
              if False else
              f"   {r['cell_key']} [{r['cell']}]: untrimmed {r['median_untrimmed']:+.5f} "
              f"(n={r['n_untrimmed']:,}) -> flag-excluded {r['median_flag_excluded']:+.5f} (n={r['n_flag_excluded']:,})")


if __name__ == "__main__":
    main()
