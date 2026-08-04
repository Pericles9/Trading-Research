"""
Phase 9 T1 - cross-session corporate-action detector.

D4 quarantined spine numerics because of adjustment-basis mismatch. The same
mismatch exists in raw tick prices ACROSS a session boundary. Phase 8 applied
the within-day guard and then computed cross-day ratios anyway (§18/§19). This
closes that gap.

For every ordered session pair used anywhere in Phase 8 or Phase 9 -
(T-1,T0), (T0,T+1), (T0,T+2), (T0,T+3) - compute

    r = log(p_later_close / p_earlier_close)

from event_minute_bars_v2 last-trade prices only, and set

    flag_cross_session_extreme = |r| >= ca_flag_log_threshold   (default ln 1.8)

T1a: the flag is MAGNITUDE ONLY. It encodes no corporate-action judgment - a
real 80% overnight move is flagged exactly as a 2:1 reverse split is.

T1b: the integer-clustering share is a DIAGNOSTIC about what the flagged set
turns out to be. It is computed after the fact and is not part of the flag.

T1d: the flag is homed in results/phase_9/artifacts/t1_cross_session_flags.parquet,
parallel to flag_possible_row_cap. It is NOT added to src/data/canonical.py -
that needs Cooper's instruction, and nothing in src/ changes mid-phase.

Escalation row 5: flagged share of (T0,T+1) pairs > 5% -> hard stop.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_9 import common as C

OUT_PARQUET = f"{C.ART}/t1_cross_session_flags.parquet"
OUT_JSON = f"{C.ART}/t1_ca_detector.json"


def nearest_integer_ratio(x: float, kmin: int, kmax: int):
    """Nearest candidate in {k} u {1/k}, k in [kmin,kmax], by RELATIVE
    deviation. Returns (label, value, abs_dev, rel_dev)."""
    if not np.isfinite(x) or x <= 0:
        return None, None, None, None
    cands = [(f"{k}", float(k)) for k in range(kmin, kmax + 1)]
    cands += [(f"1/{k}", 1.0 / k) for k in range(kmin, kmax + 1)]
    lab, val = min(cands, key=lambda c: abs(x - c[1]) / c[1])
    return lab, val, abs(x - val), abs(x - val) / val


def band_null_coverage(log_abs: pd.Series, thr: float, tol: float, kmin: int, kmax: int):
    """Chance baseline for the integer-band diagnostic.

    A band [k(1-tol), k(1+tol)] has CONSTANT width in log space,
    ln((1+tol)/(1-tol)), for every k. So the share of flagged pairs that would
    land in a band *by chance* is just the fraction of the flagged log-range
    that the bands cover. Without this, "23% sit within 3% of an integer" is
    unreadable - the bands are not measure-zero, and they get denser relative
    to the spacing as k grows.

    Computed on |log ratio| (bands at ln k are symmetric with 1/k). Returns the
    covered log-measure share over the observed flagged support.
    """
    s = pd.Series(log_abs).dropna()
    if not len(s):
        return None
    lo, hi = float(thr), float(s.max())
    if hi <= lo:
        return None
    w = np.log((1 + tol) / (1 - tol))  # band width in log space, same for all k
    covered = 0.0
    for k in range(kmin, kmax + 1):
        b0, b1 = np.log(k) - w / 2, np.log(k) + w / 2
        covered += max(0.0, min(b1, hi) - max(b0, lo))
    return float(covered / (hi - lo))


def band_resolution_limit(tol: float, kmax: int) -> dict:
    """The k above which the integer bands stop being distinguishable.

    Band half-width in log space is w/2 with w = ln((1+tol)/(1-tol)); adjacent
    integers are ln(1+1/k) apart, which SHRINKS with k. Once ln(1+1/k) < w the
    bands touch and then tile the axis, so "within tol of some integer" becomes
    automatically true and the diagnostic carries no information up there. This
    is a property of the test, not of the data.
    """
    w = np.log((1 + tol) / (1 - tol))
    k_star = None
    for k in range(2, kmax + 1):
        if np.log(1 + 1 / k) < w:
            k_star = k
            break
    return {"band_log_width": float(w),
            "first_k_where_bands_touch": k_star,
            "informative_k_range": [2, (k_star - 1) if k_star else kmax],
            "note": "at k >= first_k_where_bands_touch the bands tile the axis; membership there is uninformative by construction"}


def per_k_local_null(log_abs: pd.Series, tol: float, kmin: int, kmax: int,
                     k_informative_max: int, window: float = 0.18) -> list:
    """Observed vs LOCAL-background count in each integer band.

    The flagged |log r| distribution decays steeply, so a log-uniform null
    over the whole support is the wrong comparison (it is what makes the
    aggregate share read as 'at chance'). Instead, for each k, estimate the
    background density from the off-band part of a local window around ln k
    and scale it to the band width. Restricted to k where the bands are still
    resolvable.
    """
    u = pd.Series(log_abs).dropna().values
    w = np.log((1 + tol) / (1 - tol))
    bands = [(np.log(k) - w / 2, np.log(k) + w / 2) for k in range(kmin, kmax + 1)]

    def in_any_band(x):
        return np.any([(x >= b0) & (x <= b1) for b0, b1 in bands], axis=0)

    out = []
    for k in range(kmin, min(kmax, k_informative_max) + 1):
        c = np.log(k)
        b0, b1 = c - w / 2, c + w / 2
        lo, hi = c - window, c + window
        obs = int(((u >= b0) & (u <= b1)).sum())
        inwin = u[(u >= lo) & (u <= hi)]
        off = inwin[~in_any_band(inwin)]
        # off-band log-measure inside the window
        grid = np.linspace(lo, hi, 4001)
        off_measure = float((~in_any_band(grid)).mean() * (hi - lo))
        exp = (len(off) / off_measure * w) if off_measure > 0 else None
        out.append({
            "k": k,
            "observed": obs,
            "expected_local_background": (None if exp is None else round(float(exp), 2)),
            "excess": (None if exp is None else obs - round(float(exp), 2)),
            "ratio_obs_to_exp": (None if not exp else round(float(obs / exp), 2)),
            "n_offband_in_window": int(len(off)),
        })
    return out


def main():
    cfg = C.load_cfg()
    thr = cfg["ca_flag_log_threshold"]
    tol = cfg["ca_integer_tolerance"]
    kmin, kmax = cfg["integer_ratio_range"]

    con = C.connect()
    d1 = C.d1_frame()
    wide = C.closes_wide(con, d1)
    print(f"D1 events: {len(d1):,}   (v2 row pin verified)")

    rows = []
    for pair, (a, b) in C.PAIRS.items():
        la = {-1: "tm1", 0: "t0", 1: "t1", 2: "t2", 3: "t3"}
        pe, pl = wide[f"close_{la[a]}"], wide[f"close_{la[b]}"]
        ok = pe.notna() & pl.notna() & pe.gt(0) & pl.gt(0)
        df = wide.loc[ok, C.KEY + ["era"]].copy()
        df["session_pair"] = pair
        df["earlier_offset"], df["later_offset"] = a, b
        df["price_earlier"] = pe[ok].values
        df["price_later"] = pl[ok].values
        df["r"] = np.log(df["price_later"] / df["price_earlier"])
        df["ratio"] = np.exp(df["r"])
        df["n_pairs_possible"] = int(len(wide))
        rows.append(df)
    P = pd.concat(rows, ignore_index=True)

    P["flag_cross_session_extreme"] = P["r"].abs() >= thr

    nr = P.loc[P["flag_cross_session_extreme"], "ratio"].map(
        lambda x: nearest_integer_ratio(x, kmin, kmax))
    P["nearest_integer_ratio_label"] = pd.Series([None] * len(P), dtype=object)
    P["nearest_integer_ratio_value"] = np.nan
    P["abs_dev_from_integer_ratio"] = np.nan
    P["rel_dev_from_integer_ratio"] = np.nan
    if len(nr):
        idx = nr.index
        P.loc[idx, "nearest_integer_ratio_label"] = [t[0] for t in nr]
        P.loc[idx, "nearest_integer_ratio_value"] = [t[1] for t in nr]
        P.loc[idx, "abs_dev_from_integer_ratio"] = [t[2] for t in nr]
        P.loc[idx, "rel_dev_from_integer_ratio"] = [t[3] for t in nr]
    P["within_integer_tolerance"] = (
        P["flag_cross_session_extreme"] & P["rel_dev_from_integer_ratio"].le(tol))

    P.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {OUT_PARQUET}  ({len(P):,} rows)")

    # ---------------- per-pair summary ----------------
    per_pair, waterfall, null_cov = {}, [], {}
    for pair in C.PAIRS:
        s = P[P.session_pair == pair]
        nf = int(s["flag_cross_session_extreme"].sum())
        nint = int(s["within_integer_tolerance"].sum())
        fl_p = s[s["flag_cross_session_extreme"]]
        cov = band_null_coverage(fl_p["r"].abs(), thr, tol, kmin, kmax)
        obs = (nint / nf) if nf else None
        null_cov[pair] = {
            "expected_share_by_chance": cov,
            "observed_share": obs,
            "excess": (None if (cov is None or obs is None) else obs - cov),
            "ratio_observed_to_chance": (None if not cov or obs is None else obs / cov),
        }
        per_pair[pair] = {
            "n_events_d1": int(len(wide)),
            "n_pairs_defined": int(len(s)),
            "n_pairs_undefined": int(len(wide) - len(s)),
            "n_flagged": nf,
            "flagged_share_of_defined": (nf / len(s)) if len(s) else None,
            "n_flagged_within_integer_tolerance": nint,
            "integer_band_share_of_flagged": (nint / nf) if nf else None,
            "ratio_q01": C.q(s["ratio"], 0.01), "ratio_q99": C.q(s["ratio"], 0.99),
            "ratio_min": (float(s["ratio"].min()) if len(s) else None),
            "ratio_max": (float(s["ratio"].max()) if len(s) else None),
        }
        waterfall.append({
            "step": f"{pair}: D1 events -> pairs with both closes present and > 0",
            "rows_in": int(len(wide)), "rows_out": int(len(s)),
            "dropped": int(len(wide) - len(s)),
            "why": "session absent from event_minute_bars_v2 (offsets -3..+3 only) or non-positive close; carried as undefined, never imputed",
        })

    reslim = band_resolution_limit(tol, kmax)
    k_inf = reslim["informative_k_range"][1]
    per_k = {pair: per_k_local_null(
        P[(P.session_pair == pair) & P["flag_cross_session_extreme"]]["r"].abs(),
        tol, kmin, kmax, k_inf) for pair in C.PAIRS}
    per_k["ALL_PAIRS"] = per_k_local_null(
        P[P["flag_cross_session_extreme"]]["r"].abs(), tol, kmin, kmax, k_inf)

    # integer-band histogram of the flagged set (which k the mass sits on)
    fl = P[P["flag_cross_session_extreme"]]
    band_counts = (fl.loc[fl["within_integer_tolerance"], "nearest_integer_ratio_label"]
                   .value_counts().to_dict())

    # top 50 by |r| across all pairs
    top = fl.reindex(fl["r"].abs().sort_values(ascending=False).index).head(50)
    top50 = [{
        "ticker": t.ticker,
        "event_date": str(pd.Timestamp(t.event_date_canonical).date()),
        "session_pair": t.session_pair,
        "price_earlier": round(float(t.price_earlier), 6),
        "price_later": round(float(t.price_later), 6),
        "ratio": round(float(t.ratio), 6),
        "log_r": round(float(t.r), 6),
        "nearest_integer_ratio": t.nearest_integer_ratio_label,
        "abs_dev_from_integer_ratio": (None if pd.isna(t.abs_dev_from_integer_ratio)
                                       else round(float(t.abs_dev_from_integer_ratio), 6)),
        "rel_dev_from_integer_ratio": (None if pd.isna(t.rel_dev_from_integer_ratio)
                                       else round(float(t.rel_dev_from_integer_ratio), 6)),
        "within_integer_tolerance": bool(t.within_integer_tolerance),
    } for t in top.itertuples(index=False)]

    # events flagged on ANY pair (the carry-set used by T2/T3)
    any_flag = P[P["flag_cross_session_extreme"]][C.KEY].drop_duplicates()

    row5 = per_pair["t0_t1"]["flagged_share_of_defined"]
    triggered = bool(row5 is not None and row5 > 0.05)

    summary = {
        "phase": "9", "task": "T1",
        "source": "research/phase_9/t1_ca_detector.py:main",
        "repro": "python -m research.phase_9.t1_ca_detector",
        "config_hash": C.cfg_hash(),
        "scan_free": True, "tables_touched": ["event_minute_bars_v2"],
        "spine_numeric_reads": 0,
        "detector": {
            "definition": "r = log(p_later_close / p_earlier_close), event_minute_bars_v2 last-trade prices only",
            "close_convention": "last_price of the max-minute_index bar on that session offset (extended day, any segment)",
            "flag": "flag_cross_session_extreme = |r| >= ca_flag_log_threshold",
            "ca_flag_log_threshold": thr,
            "ca_flag_ratio_threshold": [round(float(np.exp(-thr)), 6), round(float(np.exp(thr)), 6)],
            "magnitude_only": "T1a - the flag encodes no corporate-action judgment",
            "flag_home": OUT_PARQUET,
            "flag_home_note": "T1d - parallel to flag_possible_row_cap; NOT added to src/data/canonical.py",
        },
        "integer_diagnostic": {
            "note": "T1b - evidence about what the flagged set is, NOT part of the flag",
            "ca_integer_tolerance": tol,
            "integer_ratio_range": [kmin, kmax],
            "band_counts_within_tolerance": band_counts,
            "null_coverage": {
                "definition": "share of the flagged log-ratio support covered by the integer bands; the rate the diagnostic would report by chance",
                "why": "a band [k(1-tol), k(1+tol)] has constant log-width ln((1+tol)/(1-tol)) for every k, so the bands are not measure-zero and the raw share is unreadable without this",
                "per_pair": null_cov,
            },
            "band_resolution_limit": reslim,
            "per_k_local_null": {
                "definition": "observed count in each integer band vs the count implied by the off-band density in a local window around ln k",
                "why": "the flagged |log r| distribution decays steeply, so the flat null above understates the background at low k and overstates it at high k; the per-k local comparison is the one that can see a reverse-split spike",
                "window_log_halfwidth": 0.18,
                "per_pair": per_k,
            },
        },
        "per_pair": per_pair,
        "n_events_flagged_on_any_pair": int(len(any_flag)),
        "share_of_d1_flagged_on_any_pair": float(len(any_flag) / len(wide)),
        "filter_waterfall": waterfall,
        "escalation_row_5": {
            "condition": "flag_cross_session_extreme share of (T0,T+1) pairs > 5%",
            "observed": row5, "threshold": 0.05, "triggered": triggered,
        },
        "top_50_by_abs_r": top50,
        "artifacts": [OUT_PARQUET],
    }
    C.write_json(summary, OUT_JSON)

    print("\nper-pair flag counts:")
    for k, v in per_pair.items():
        print(f"  {k:8s} defined={v['n_pairs_defined']:6,d}  flagged={v['n_flagged']:5,d}"
              f"  ({(v['flagged_share_of_defined'] or 0)*100:5.2f}%)"
              f"  integer-band {v['n_flagged_within_integer_tolerance']:4,d}"
              f"  ({(v['integer_band_share_of_flagged'] or 0)*100:5.1f}% of flagged)")
    print(f"\nevents flagged on any pair: {len(any_flag):,} "
          f"({len(any_flag)/len(wide)*100:.2f}% of D1)")
    print(f"\ninteger bands (within {tol:.0%}): "
          + ", ".join(f"{k}x:{v}" for k, v in sorted(band_counts.items(), key=lambda kv: -kv[1])[:15]))
    print("\ninteger-band share vs chance (bands are not measure-zero):")
    for k, v in null_cov.items():
        if v["observed_share"] is None or v["expected_share_by_chance"] is None:
            continue
        print(f"  {k:8s} observed {v['observed_share']:6.2%}   by chance {v['expected_share_by_chance']:6.2%}"
              f"   excess {v['excess']:+6.2%}   x{v['ratio_observed_to_chance']:.2f}")
    print(f"\nband resolution limit: bands touch at k={reslim['first_k_where_bands_touch']} "
          f"(log width {reslim['band_log_width']:.4f}); informative k range {reslim['informative_k_range']}")
    print("\nper-k observed vs LOCAL background, all pairs pooled:")
    print("   k   observed   expected   excess   obs/exp")
    for r in per_k["ALL_PAIRS"]:
        e, x, xs = r["expected_local_background"], r["excess"], r["ratio_obs_to_exp"]
        e_s = "     n/a" if e is None else f"{e:8.2f}"
        x_s = "    n/a" if x is None else f"{x:+7.2f}"
        r_s = "  n/a" if xs is None else f"x{xs:.2f}"
        print(f"  {r['k']:2d}   {r['observed']:8d}   {e_s}   {x_s}   {r_s}")
    print(f"\nESCALATION ROW 5: (T0,T+1) flagged share {row5:.4%} vs 5% -> "
          + ("*** TRIGGERED - HARD STOP ***" if triggered else "pass"))


if __name__ == "__main__":
    main()
