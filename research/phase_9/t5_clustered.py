"""
Phase 9 T5 - ticker-clustered inference.

D1's events are not independent draws: they concentrate in a few thousand
tickers, so nominal n overstates the number of independent observations and
any CI computed as if events were iid is too narrow.

T5a events-per-ticker distribution.
T5b ticker-block bootstrap: resample TICKERS with replacement (all events of
    each drawn ticker come along), bootstrap_reps=2000, bootstrap_seed=42,
    percentile 95% CI. Applied to every headline median in this phase and to
    the Phase 8 headline medians being restated.
T5c median of per-ticker medians, and share of tickers with a negative
    median, alongside every pooled median. These are the cluster-robust
    location statistics: one ticker with 57 events cannot outvote 57 tickers.

A naive event-level (iid) bootstrap is run with the same reps and seed so the
two intervals are directly comparable on chart 08 - the width ratio is the
cost of clustering.

Escalation row 10: block-bootstrap 95% CI on the pooled t0_close->t1_close
median contains 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_9 import common as C

FLAGS = f"{C.ART}/t1_cross_session_flags.parquet"
RETRACE = f"{C.ART}/t3_retracement.parquet"
GRID = f"{C.ART}/t4_axis_grid.parquet"
OUT_JSON = f"{C.ART}/t5_clustered_inference.json"

QUINTILES = [1, 2, 3, 4, 5]
DET_BINS = ["premarket", "0930-1000", "1000-1100", "1100-1300", "after_1300"]


def _prep(values: np.ndarray, tickers: np.ndarray):
    m = np.isfinite(values)
    v, t = values[m], tickers[m]
    order = np.argsort(t, kind="stable")
    v, t = v[order], t[order]
    _, starts, counts = np.unique(t, return_index=True, return_counts=True)
    return v, starts, counts


def block_bootstrap_median(values, tickers, reps, seed, ci=0.95):
    """Percentile CI on the median, resampling whole tickers with replacement."""
    v, starts, counts = _prep(np.asarray(values, float), np.asarray(tickers))
    T = len(starts)
    if T == 0 or len(v) == 0:
        return {"n": 0, "n_tickers": 0, "point": None, "lo": None, "hi": None}
    rng = np.random.default_rng(seed)
    out = np.empty(reps)
    cs = np.cumsum(counts) - counts
    for r in range(reps):
        idx = rng.integers(0, T, T)
        c = counts[idx]
        tot = int(c.sum())
        pos = np.repeat(starts[idx], c) + (np.arange(tot) - np.repeat(np.cumsum(c) - c, c))
        out[r] = np.median(v[pos])
    a = (1 - ci) / 2
    return {"n": int(len(v)), "n_tickers": int(T), "point": float(np.median(v)),
            "lo": float(np.quantile(out, a)), "hi": float(np.quantile(out, 1 - a))}


def naive_bootstrap_median(values, reps, seed, ci=0.95):
    """Event-level iid bootstrap - the interval clustering makes too narrow."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0, "point": None, "lo": None, "hi": None}
    rng = np.random.default_rng(seed)
    n = len(v)
    out = np.empty(reps)
    for r in range(reps):
        out[r] = np.median(v[rng.integers(0, n, n)])
    a = (1 - ci) / 2
    return {"n": int(n), "point": float(np.median(v)),
            "lo": float(np.quantile(out, a)), "hi": float(np.quantile(out, 1 - a))}


def per_ticker(values, tickers):
    """T5c - median of per-ticker medians, share of tickers negative."""
    df = pd.DataFrame({"v": np.asarray(values, float), "t": np.asarray(tickers)}).dropna()
    if not len(df):
        return {"n_tickers": 0, "median_of_ticker_medians": None, "share_tickers_negative": None}
    g = df.groupby("t")["v"].median()
    return {"n_tickers": int(len(g)),
            "median_of_ticker_medians": float(g.median()),
            "share_tickers_negative": float((g < 0).mean()),
            "n_tickers_negative": int((g < 0).sum())}


def stat(name, values, tickers, reps, seed):
    b = block_bootstrap_median(values, tickers, reps, seed)
    nv = naive_bootstrap_median(values, reps, seed)
    pt = per_ticker(values, tickers)
    bw = (b["hi"] - b["lo"]) if b["lo"] is not None else None
    nw = (nv["hi"] - nv["lo"]) if nv["lo"] is not None else None
    return {"name": name, "n": b["n"], "n_tickers": b["n_tickers"], "median": b["point"],
            "block_ci95": [b["lo"], b["hi"]], "naive_ci95": [nv["lo"], nv["hi"]],
            "block_ci_width": bw, "naive_ci_width": nw,
            "width_ratio_block_over_naive": (bw / nw if (bw and nw) else None),
            "block_ci_contains_zero": (bool(b["lo"] is not None and b["lo"] <= 0 <= b["hi"])),
            **{k: v for k, v in pt.items() if k != "n_tickers"}}


def main():
    cfg = C.load_cfg()
    reps, seed = cfg["bootstrap_reps"], cfg["bootstrap_seed"]
    print(f"ticker-block bootstrap: reps={reps} seed={seed}")

    d1 = C.d1_frame()

    # ---------- T5a events-per-ticker ----------
    vc = d1.groupby("ticker").size().sort_values(ascending=False)
    n_ev, n_tk = int(len(d1)), int(len(vc))
    dist = {
        "n_events": n_ev, "n_tickers": n_tk,
        "events_per_ticker_median": float(vc.median()),
        "events_per_ticker_mean": float(vc.mean()),
        "events_per_ticker_max": int(vc.max()),
        "events_per_ticker_min": int(vc.min()),
        "share_events_in_tickers_ge_5": float(vc[vc >= 5].sum() / n_ev),
        "share_events_in_tickers_ge_10": float(vc[vc >= 10].sum() / n_ev),
        "n_tickers_ge_5": int((vc >= 5).sum()), "n_tickers_ge_10": int((vc >= 10).sum()),
        "top_20_tickers": [{"ticker": t, "n_events": int(c)} for t, c in vc.head(20).items()],
        "histogram": {str(k): int(v) for k, v in vc.value_counts().sort_index().items()},
    }
    print(f"T5a: {n_ev:,} events / {n_tk:,} tickers  median {vc.median():.0f}  mean {vc.mean():.2f}  max {vc.max()}")
    print(f"     share of events in tickers with >=5: {dist['share_events_in_tickers_ge_5']:.1%}"
          f"  >=10: {dist['share_events_in_tickers_ge_10']:.1%}")

    stats = []

    # ---------- Phase 8 headline: t0_close -> t1_close ----------
    flags = pd.read_parquet(FLAGS)
    flags["event_date_canonical"] = pd.to_datetime(flags["event_date_canonical"])
    base = pd.read_parquet(C.CONTAM_PATH)
    base["event_date_canonical"] = pd.to_datetime(base["event_date_canonical"])
    base = base[(base.anchor_name == "t0_close") & (base.horizon_name == "t1_close")
                & base.markout.notna()].copy()
    f01 = flags[flags.session_pair == "t0_t1"][C.KEY + ["flag_cross_session_extreme"]]
    base = base.merge(f01, on=C.KEY, how="left")
    base["flag_cross_session_extreme"] = base["flag_cross_session_extreme"].fillna(False).astype(bool)

    stats.append(stat("t0_close->t1_close | pooled | untrimmed (PRIMARY)",
                      base["markout"].values, base["ticker"].values, reps, seed))
    row10_primary = stats[-1]
    stats.append(stat("t0_close->t1_close | pooled | flag-excluded",
                      base.loc[~base.flag_cross_session_extreme, "markout"].values,
                      base.loc[~base.flag_cross_session_extreme, "ticker"].values, reps, seed))
    for qv in QUINTILES:
        s = base[base.pq_rth_open == qv]
        stats.append(stat(f"t0_close->t1_close | pq_rth_open Q{qv} | untrimmed",
                          s["markout"].values, s["ticker"].values, reps, seed))

    # ---------- det+5 -> t0_close ----------
    G = pd.read_parquet(GRID)
    fe = G[(G.grid == "fixed_exit") & (G.latency == 5) & G.markout.notna()]
    stats.append(stat("det+5->t0_close | pooled",
                      fe["markout"].values, fe["ticker"].values, reps, seed))
    for db in DET_BINS:
        s = fe[fe.det_bin == db]
        stats.append(stat(f"det+5->t0_close | det_bin {db}",
                          s["markout"].values, s["ticker"].values, reps, seed))

    # ---------- retracement medians ----------
    R = pd.read_parquet(RETRACE)
    for h in ["t0_close", "t1_close", "t2_close", "t3_close"]:
        s = R[R.horizon == h]
        stats.append(stat(f"retrace_excursion | {h}",
                          s["retrace_excursion"].values, s["ticker"].values, reps, seed))
    for h in ["t0_close", "t1_close", "t2_close", "t3_close"]:
        s = R[R.horizon == h]
        stats.append(stat(f"retrace_detection | {h}",
                          s["retrace_detection"].values, s["ticker"].values, reps, seed))

    # ---------- escalation row 10 ----------
    row10 = {
        "condition": "ticker-block bootstrap 95% CI on pooled t0_close->t1_close median contains 0",
        "statistic": row10_primary["name"],
        "median": row10_primary["median"],
        "block_ci95": row10_primary["block_ci95"],
        "naive_ci95": row10_primary["naive_ci95"],
        "n": row10_primary["n"], "n_tickers": row10_primary["n_tickers"],
        "triggered": row10_primary["block_ci_contains_zero"],
    }

    widths = [s["width_ratio_block_over_naive"] for s in stats
              if s["width_ratio_block_over_naive"] is not None]
    summary = {
        "phase": "9", "task": "T5",
        "source": "research/phase_9/t5_clustered.py:main",
        "repro": "python -m research.phase_9.t5_clustered",
        "config_hash": C.cfg_hash(),
        "scan_free": True, "tables_touched": ["event_minute_bars_v2"],
        "spine_numeric_reads": 0,
        "bootstrap": {"method": "ticker-block, resample tickers with replacement, percentile CI",
                      "reps": reps, "seed": seed, "ci_level": 0.95,
                      "naive_comparison": "event-level iid bootstrap, same reps and seed"},
        "events_per_ticker": dist,
        "headline_medians": stats,
        "ci_width_ratio_summary": {
            "median_block_over_naive": float(np.median(widths)) if widths else None,
            "min": float(np.min(widths)) if widths else None,
            "max": float(np.max(widths)) if widths else None,
            "n_statistics": len(widths)},
        "escalation_row_10": row10,
    }
    C.write_json(summary, OUT_JSON)

    # ---------------- console ----------------
    print(f"\n{'statistic':52s} {'n':>7s} {'med':>9s} {'block 95% CI':>22s} {'naive 95% CI':>22s} {'w':>5s}")
    for s in stats:
        b = f"[{s['block_ci95'][0]:+.4f},{s['block_ci95'][1]:+.4f}]" if s["block_ci95"][0] is not None else "n/a"
        nv = f"[{s['naive_ci95'][0]:+.4f},{s['naive_ci95'][1]:+.4f}]" if s["naive_ci95"][0] is not None else "n/a"
        w = f"{s['width_ratio_block_over_naive']:.2f}" if s["width_ratio_block_over_naive"] else "n/a"
        z = " <-0" if s["block_ci_contains_zero"] else ""
        print(f"{s['name']:52s} {s['n']:7,d} {s['median']:+9.4f} {b:>22s} {nv:>22s} {w:>5s}{z}")

    print(f"\nT5c median-of-per-ticker-medians / share of tickers negative:")
    for s in stats:
        print(f"  {s['name']:52s} {s['median_of_ticker_medians']:+9.4f}  "
              f"{s['share_tickers_negative']:6.1%} of {s['n_tickers']:,} tickers")

    print(f"\nCI width ratio block/naive: median {summary['ci_width_ratio_summary']['median_block_over_naive']:.2f}x "
          f"(range {summary['ci_width_ratio_summary']['min']:.2f}-{summary['ci_width_ratio_summary']['max']:.2f}x)")
    print(f"\nESCALATION ROW 10: pooled t0_close->t1_close block CI "
          f"[{row10['block_ci95'][0]:+.5f}, {row10['block_ci95'][1]:+.5f}] -> "
          + ("*** TRIGGERED (contains 0) ***" if row10["triggered"] else "pass (excludes 0)"))


if __name__ == "__main__":
    main()
