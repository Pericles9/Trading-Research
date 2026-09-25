"""
Brief 1, T4 -- the excursion vector on the dev sample (50) and the sidecar (6, own row).

Path: every print strictly after tau and at or before 20:00 ET on the event day (DA-1). Bucket ladder
{50, 100, 200} (DA-2), equal share volume, prints split across bucket edges at their own price, VWAP per
bucket. Components per Part II T4, all from research/attention_excursion_b1/instruments.py -- the same
functions T6's controls exercise. No attention quantity is read here; nothing is conditioned on
anything. This is the unconditional build.

Edge classes are flags, never drops: rise_censored, no_rise (peak at tau or in the first bucket, with
peak_at_tau carried separately), halt_in_path (A2.6: a gap of >= 300 s inside regular hours, plus LULD-V3c labels),
thin_path (< 250 prints after tau).

Writes artifacts/t4_excursion.parquet (event x rung), artifacts/t4_buckets.parquet (the bucketed paths,
for the strip charts), artifacts/t4_summary.json (incl. escalation row 6 and the II.5 conservation check).

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t4_excursion.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import instruments as I  # noqa: E402


def dev_population() -> pd.DataFrame:
    s = pd.read_parquet(C.REPO / C.OUT / "slices.parquet", columns=["event_id", "dev_group"])
    s = s[s["dev_group"].notna()]
    t2 = pd.read_parquet(C.art("t2_tau.parquet"))
    d = s.merge(t2, on="event_id", how="left")
    assert (d["dev_group"] == "dev_v3").sum() == 50 and (d["dev_group"] == "dev_v4_sidecar").sum() == 6
    return d


def path_arrays(event_id: str, tau_ns: int, date: str):
    tr = C.read_trades(event_id, with_conditions=False)
    t2000 = C.et_ns(date, "20:00:00")
    ts, px, sz = tr["ts"], tr["px"], tr["sz"]
    a = int(np.searchsorted(ts, tau_ns, "right"))      # strictly after tau
    b = int(np.searchsorted(ts, t2000, "right"))
    return ts[a:b], px[a:b], sz[a:b]


def main() -> int:
    cfg = C.load_cfg()["t4_excursion"]
    ladder = cfg["bucket_ladder"]
    thin_n = cfg["thin_path_min_prints"]
    gap_s = C.load_cfg()["amendment_2"]["halt_rule"]["gap_seconds"]
    halts = C.load_halt_labels()
    d = dev_population()
    rows, buckets = [], []
    for r in d.itertuples():
        base = {"event_id": r.event_id, "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                "dev_group": r.dev_group, "tau_session_segment": r.tau_session_segment,
                "flag_cross_session_extreme": r.flag_cross_session_extreme,
                "tau_close_sensitive": r.tau_close_sensitive, "year": r.event_date_canonical[:4],
                "sec_from_0930": r.sec_from_0930, "open_adjacent_0930": None}
        if not r.tau_available:
            for N in ladder:
                rows.append({**base, "N": N, "vector_available": False, "reason": f"tau_unavailable:{r.tau_reason}"})
            continue
        tau = int(r.tau_ns)
        ts, px, sz = path_arrays(r.event_id, tau, r.event_date_canonical)
        # A2.6: a gap counts toward a halt only for the part of it that lies inside regular hours
        # (LULD pauses are >= 5 minutes and apply in regular hours only); the calendar close governs
        # early-close days. The part outside regular hours is a descriptor, not a halt.
        g_lo = np.r_[tau, ts[:-1]] if ts.size else np.array([], dtype=np.int64)
        g_hi = ts
        op, cl = C.rth_bounds_ns(r.event_date_canonical)
        in_rth = np.clip(np.minimum(g_hi, cl) - np.maximum(g_lo, op), 0, None) / 1e9 if ts.size else np.array([])
        outside = (g_hi - g_lo) / 1e9 - in_rth if ts.size else np.array([])
        lab = halts.get(f"{r.ticker}|{r.event_date_canonical}", [])
        end = int(ts[-1]) if ts.size else tau
        lab_in = [h for h in lab if h[1] > tau and h[0] <= end]
        flags = {"n_path_prints_all": int(ts.size), "thin_path": bool(ts.size < thin_n),
                 "max_gap_s": float(((g_hi - g_lo) / 1e9).max()) if ts.size else np.nan,
                 "max_gap_in_rth_s": float(in_rth.max()) if ts.size else np.nan,
                 "max_gap_outside_rth_s": float(outside.max()) if ts.size else np.nan,
                 "halt_gap_rth": bool(ts.size and in_rth.max() >= gap_s),
                 "halt_label_available": bool(f"{r.ticker}|{r.event_date_canonical}" in halts),
                 "halt_label_in_path": bool(lab_in), "tau_price": float(r.tau_price)}
        flags["halt_in_path"] = bool(flags["halt_gap_rth"] or flags["halt_label_in_path"])
        for N in ladder:
            if ts.size < 2:
                rows.append({**base, **flags, "N": N, "vector_available": False, "reason": "path_too_short"})
                continue
            v = I.excursion_vector(tau, float(r.tau_price), ts, px, sz, N)
            P, T = v.pop("_bucket_price", None), v.pop("_bucket_t_end", None)
            rows.append({**base, **flags, **v})
            if P is not None:
                buckets.append(pd.DataFrame({"event_id": r.event_id, "N": N, "i": np.arange(1, N + 1),
                                             "u": np.arange(1, N + 1) / N, "vwap": P, "t_end_ns": T}))
    out = pd.DataFrame(rows)
    out["config_hash"] = C.cfg_hash()
    out.to_parquet(C.art("t4_excursion.parquet"), index=False)
    bk = pd.concat(buckets, ignore_index=True)
    bk.to_parquet(C.art("t4_buckets.parquet"), index=False)

    dev = out[out["dev_group"] == "dev_v3"]
    per_ev = dev.drop_duplicates("event_id")
    thin_share = float(per_ev["thin_path"].fillna(False).mean())
    va = out[out["vector_available"] == True]  # noqa: E712
    comps = ["u_peak", "rise_s", "fall_s", "dip_before_peak_s", "terminal_s", "sigma_b_bp", "sigma_path_bp",
             "sigma_bv_path_bp", "jump_share", "peak_tie_span_u", "rise_bp", "fall_bp", "rise_cents", "fall_cents",
             "t_peak_s", "t_end_s"]
    med = {g: {int(N): {c: float(x[c].median()) for c in comps} | {"n": int(len(x))}
               for N, x in gg.groupby("N")} for g, gg in va.groupby("dev_group")}
    classes = {g: {int(N): {k: int(x[k].fillna(False).astype(bool).sum()) for k in
                            ["rise_censored", "no_rise", "peak_at_tau", "peak_tied", "halt_in_path", "halt_gap_rth",
                             "halt_label_in_path", "thin_path", "sigma_zero"]} | {"n": int(len(x))}
                   for N, x in gg.groupby("N")} for g, gg in va.groupby("dev_group")}
    summary = {
        "config_hash": C.cfg_hash(),
        "events": {"dev_v3": int(per_ev.shape[0]), "sidecar": int(out[out["dev_group"] == "dev_v4_sidecar"]["event_id"].nunique())},
        "vector_available_rows": out.groupby(["dev_group", "N"])["vector_available"].sum().astype(int).unstack().to_dict("index"),
        "unavailable_reasons": out.loc[out["vector_available"] != True, "reason"].value_counts().to_dict(),  # noqa: E712
        "component_medians": med,
        "edge_classes": classes,
        "path_prints": {"dev_median": float(per_ev["n_path_prints_all"].median()), "dev_min": int(per_ev["n_path_prints_all"].min())},
        "gaps_dev": {"max_gap_outside_rth_s_median": float(per_ev["max_gap_outside_rth_s"].median()),
                     "max_gap_in_rth_s_median": float(per_ev["max_gap_in_rth_s"].median()),
                     "halt_in_path_events": int(per_ev["halt_in_path"].fillna(False).astype(bool).sum()),
                     "halt_label_available_events": int(per_ev["halt_label_available"].fillna(False).astype(bool).sum())},
        "scale": "rv (Amendment 2 A2.1)",
        "open_adjacent_0930": "PENDING -- boundary not set by Cooper (A2.7); sec_from_0930 carried",
        "row_6": {"criterion": "thin paths above 20% of the dev sample", "tier": "LOG",
                  "thin_events": int(per_ev["thin_path"].fillna(False).sum()), "of": int(per_ev.shape[0]),
                  "observed_share": thin_share, "fires": bool(thin_share > 0.20)},
        "II5_bucket_volume_conservation": {"asserted_in": "instruments.bucketize (print volume fully assigned; buckets sum to path volume; no empty bucket)",
                                           "event_rungs_checked": int(len(va)),
                                           "max_bucket_vol_rel_err": float(va["max_bucket_vol_rel_err"].max()),
                                           "passes": True},
    }
    C.write_json(f"{C.ART}/t4_summary.json", summary)
    print(summary["events"], summary["row_6"], summary["unavailable_reasons"])
    for N, v in med.get("dev_v3", {}).items():
        print(N, {k: round(x, 3) for k, x in v.items() if k in ("u_peak", "rise_s", "fall_s", "terminal_s", "n")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
