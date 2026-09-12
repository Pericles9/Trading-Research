#!/usr/bin/env python
"""Identify fragmentation from the trade record, not from a time tolerance (review s3).

THE OBJECTION THIS ANSWERS, and it is correct. The excess goes 4.06 -> 2.63 -> 1.29 ->
below 1 at collapse tolerances of 0/1/10/100 ms. Choosing 100 ms because that is where
the signal disappears is parameter tuning in the negative direction, and a null feels
conservative when it is merely an answer.

WHAT THE RECORD CARRIES. data/filtered/*/trades.parquet has, beyond the four columns the
committed reader takes: `exchange`, `conditions` (list of SIP condition codes),
`id`, `tape`, `trf_id`, `participant_timestamp`. So prints from one marketable order
sweeping the book are separable from independent arrivals by their JOINT signature
rather than by proximity alone:

    monotone price      a marketable order walks the book one way and does not reverse
    multiple exchanges  a sweep takes liquidity at several venues at once
    contiguous sequence the SIP numbers them consecutively

THE CONDITION CODES ARE NOT DECODED HERE AND THAT IS DELIBERATE. data/filtered/
METADATA.md documents the column as "Trade conditions" and gives no code table; the
environment is offline (D14) so no reference can be fetched. Asserting that code 14 is
an intermarket sweep would be a fabrication dressed as a finding. What IS reported is
the EMPIRICAL association: which condition tuples are enriched inside sub-millisecond
runs relative to outside them. That is a measurement and needs no code table. Any
reading of what the codes MEAN is marked [verify] and is not used by the collapse.

THE NULL, so "monotone and multi-venue" is not scored against intuition. Run structure
is held fixed and the per-print attributes (price, exchange) are permuted across the
session. If sub-millisecond runs are genuinely one order, monotonicity and venue count
inside them sit far above that null; if they are coincidental collisions of independent
arrivals, they sit on it.

OUTPUT. A per-event collapsed tape written to the cache, built on identity rather than
on a tolerance, for the Allan recomputation and the interval channel to consume.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10"))
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                     # noqa: E402
from common import session_window, trade_files                     # noqa: E402
from instrument_gates import CACHE, cohort, jdump                  # noqa: E402

COLS = ["sip_timestamp", "price", "size", "sequence_number", "exchange", "conditions"]
TAUS_NS = (100_000, 1_000_000, 10_000_000)          # 0.1, 1, 10 ms
TAU_COLLAPSE = 1_000_000                            # the run definition used to collapse


def read_full(eid, segment=None):
    """Targeted per-event read with the extra columns. Reuses the committed
    trade_files() and session_window(); no second read path for the standard ones."""
    cfg = adapter.load_config()
    ticker, date, mp = adapter.parse_event_id(eid)
    files = trade_files(cfg, ticker, date, mp)
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f, columns=COLS) for f in files],
                   ignore_index=True) if len(files) > 1 else pd.read_parquet(
        files[0], columns=COLS)
    df = df.sort_values(["sip_timestamp", "sequence_number"], kind="mergesort")
    b = adapter.segment_bounds_ns(date)
    lo, hi = b[segment] if segment else (b["premarket"][0], b["post"][1])
    ts = df["sip_timestamp"].to_numpy()
    return df.loc[(ts >= lo) & (ts < hi)].reset_index(drop=True)


def runs_at(ts, tau):
    """Maximal groups of consecutive prints separated by < tau. -> group id per print."""
    if ts.size == 0:
        return np.zeros(0, dtype=np.int64)
    brk = np.diff(ts) >= tau
    return np.concatenate([[0], np.cumsum(brk)]).astype(np.int64)


def run_stats(df, gid):
    """Per multi-print run: monotone price? distinct exchanges? contiguous sequence?"""
    p = df["price"].to_numpy(float)
    x = df["exchange"].to_numpy()
    q = df["sequence_number"].to_numpy(np.int64)
    order = np.argsort(gid, kind="mergesort")
    gid_s, p, x, q = gid[order], p[order], x[order], q[order]
    edges = np.flatnonzero(np.diff(gid_s)) + 1
    starts = np.concatenate([[0], edges])
    ends = np.concatenate([edges, [gid_s.size]])
    out = {"n_runs": 0, "n_multi": 0, "mono": 0, "multi_venue": 0, "contig": 0,
           "prints_in_multi": 0, "len_hist": Counter()}
    for a, b in zip(starts, ends):
        n = b - a
        out["n_runs"] += 1
        out["len_hist"][min(int(n), 20)] += 1
        if n < 2:
            continue
        out["n_multi"] += 1
        out["prints_in_multi"] += int(n)
        pp = p[a:b]
        d = np.diff(pp)
        if np.all(d >= 0) or np.all(d <= 0):
            out["mono"] += 1
        if np.unique(x[a:b]).size > 1:
            out["multi_venue"] += 1
        if int(q[b - 1] - q[a]) == n - 1:
            out["contig"] += 1
    return out


def permuted_null(df, gid, seed=0, n_perm=3):
    """Same run structure, attributes shuffled across the session."""
    rng = np.random.default_rng(seed)
    acc = {"mono": [], "multi_venue": [], "contig": []}
    for _ in range(n_perm):
        d2 = df.copy()
        idx = rng.permutation(len(df))
        d2["price"] = df["price"].to_numpy()[idx]
        d2["exchange"] = df["exchange"].to_numpy()[idx]
        d2["sequence_number"] = df["sequence_number"].to_numpy()[idx]
        st = run_stats(d2, gid)
        m = max(st["n_multi"], 1)
        for k in acc:
            acc[k].append(st[k] / m)
    return {k: float(np.mean(v)) for k, v in acc.items()}


def condition_enrichment(df, gid):
    """Which condition tuples are enriched INSIDE multi-print runs? Empirical only --
    no code table is asserted, because the repo has none and the environment is offline."""
    cnt = np.bincount(gid)
    inside = cnt[gid] > 1
    def tup(v):
        return "none" if v is None or (hasattr(v, "__len__") and len(v) == 0) \
            else ",".join(str(int(z)) for z in sorted(v))
    keys = [tup(v) for v in df["conditions"]]
    ci = Counter(k for k, m in zip(keys, inside) if m)
    co = Counter(k for k, m in zip(keys, inside) if not m)
    ni, no = max(sum(ci.values()), 1), max(sum(co.values()), 1)
    rows = []
    for k in set(list(ci) + list(co)):
        pi, po = ci[k] / ni, co[k] / no
        if ci[k] + co[k] < 50:
            continue
        rows.append({"conditions": k, "n_inside": ci[k], "n_outside": co[k],
                     "share_inside": pi, "share_outside": po,
                     "enrichment": pi / po if po > 0 else float("inf")})
    return sorted(rows, key=lambda r: -r["enrichment"])[:10]


def collapse_identity(df, tau=TAU_COLLAPSE):
    """One arrival per SWEEP RUN, where a run qualifies as one order if it is
    price-monotone AND (multi-venue OR sequence-contiguous). Runs that fail the
    signature are left alone -- their prints stay as separate arrivals."""
    ts = df["sip_timestamp"].to_numpy(np.int64)
    gid = runs_at(ts, tau)
    p = df["price"].to_numpy(float)
    x = df["exchange"].to_numpy()
    q = df["sequence_number"].to_numpy(np.int64)
    keep = np.ones(ts.size, bool)
    edges = np.flatnonzero(np.diff(gid)) + 1
    starts = np.concatenate([[0], edges])
    ends = np.concatenate([edges, [ts.size]])
    n_collapsed = 0
    for a, b in zip(starts, ends):
        if b - a < 2:
            continue
        d = np.diff(p[a:b])
        mono = np.all(d >= 0) or np.all(d <= 0)
        if not mono:
            continue
        if np.unique(x[a:b]).size > 1 or int(q[b - 1] - q[a]) == (b - a - 1):
            keep[a + 1:b] = False
            n_collapsed += int(b - a - 1)
    return ts[keep], n_collapsed


def main() -> int:
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    events = list(cohort()["event_id"])[:n_ev]
    res = {"taus_ns": list(TAUS_NS), "tau_collapse_ns": TAU_COLLAPSE,
           "note": __doc__, "events": {}}
    CACHE.mkdir(parents=True, exist_ok=True)

    for eid in events:
        df = read_full(eid, "rth")
        if df is None or len(df) < 5000:
            continue
        ts = df["sip_timestamp"].to_numpy(np.int64)
        e = {"prints": int(len(df)), "by_tau": {}}
        for tau in TAUS_NS:
            gid = runs_at(ts, tau)
            st = run_stats(df, gid)
            m = max(st["n_multi"], 1)
            null = permuted_null(df, gid, seed=3)
            e["by_tau"][str(tau)] = {
                "n_runs": st["n_runs"], "n_multi_print_runs": st["n_multi"],
                "prints_in_multi_runs": st["prints_in_multi"],
                "share_prints_in_multi": st["prints_in_multi"] / len(df),
                "mono_share": st["mono"] / m, "mono_null": null["mono"],
                "multi_venue_share": st["multi_venue"] / m,
                "multi_venue_null": null["multi_venue"],
                "contig_share": st["contig"] / m, "contig_null": null["contig"],
                "len_hist": {str(k): v for k, v in sorted(st["len_hist"].items())}}
        gid1 = runs_at(ts, TAU_COLLAPSE)
        e["condition_enrichment"] = condition_enrichment(df, gid1)
        keep_ts, n_col = collapse_identity(df)
        e["identity_collapse"] = {
            "prints_before": int(len(df)), "prints_after": int(keep_ts.size),
            "removed": int(n_col), "retained_share": float(keep_ts.size / len(df))}
        np.save(CACHE / f"identity_collapsed_{eid}.npy", keep_ts)
        res["events"][eid] = e
        t1 = e["by_tau"]["1000000"]
        print(f"  {eid.split('_')[0]:6s} prints {len(df):7,d}  "
              f"in sub-ms runs {t1['share_prints_in_multi']:.3f}  "
              f"mono {t1['mono_share']:.3f} (null {t1['mono_null']:.3f})  "
              f"multivenue {t1['multi_venue_share']:.3f} (null {t1['multi_venue_null']:.3f})  "
              f"-> identity collapse keeps {e['identity_collapse']['retained_share']:.3f}",
              flush=True)

    jdump(res, "fragmentation_identity.json")

    print("\n" + "=" * 96)
    print("SUB-MILLISECOND RUNS: SIGNATURE vs A PERMUTED NULL (run structure held fixed)")
    print("=" * 96)
    for tau in TAUS_NS:
        g = [res["events"][e]["by_tau"][str(tau)] for e in res["events"]]
        print(f"\ntau = {tau/1e6:g} ms   prints in multi-print runs: "
              f"{np.median([x['share_prints_in_multi'] for x in g]):.3f}")
        for k, lab in (("mono", "price-monotone"), ("multi_venue", "multi-venue"),
                       ("contig", "sequence-contiguous")):
            obs = np.median([x[f"{k}_share"] for x in g])
            nul = np.median([x[f"{k}_null"] for x in g])
            print(f"    {lab:22s} observed {obs:.3f}   permuted null {nul:.3f}   "
                  f"lift {obs/nul if nul > 0 else float('inf'):5.2f}x")

    print("\nCONDITION TUPLES ENRICHED INSIDE SUB-MS RUNS (empirical; no code table is "
          "asserted -- [verify] any reading of what a code MEANS)")
    pool = {}
    for e in res["events"]:
        for r in res["events"][e]["condition_enrichment"]:
            pool.setdefault(r["conditions"], []).append(r["enrichment"])
    for k, v in sorted(pool.items(), key=lambda kv: -np.median(kv[1]))[:8]:
        print(f"    conditions=({k:14s})  median enrichment {np.median(v):6.2f}x  "
              f"(n events {len(v)})")

    print("\nIDENTITY COLLAPSE (price-monotone AND (multi-venue OR contiguous), tau = 1 ms)")
    g = [res["events"][e]["identity_collapse"] for e in res["events"]]
    print(f"    retained share of prints: median {np.median([x['retained_share'] for x in g]):.3f}"
          f"  range {min(x['retained_share'] for x in g):.3f}"
          f"-{max(x['retained_share'] for x in g):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
