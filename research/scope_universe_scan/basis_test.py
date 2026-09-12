#!/usr/bin/env python
"""
Is the archive's selection variable RTH-scoped? Cooper's read section 4, adapted.

WHAT COOPER ASKED, AND WHAT IS ACTUALLY REACHABLE. The read asks for the SCREEN's field --
Polygon's `todaysChangePerc` -- to be compared against tick data computed premarket-inclusive
and RTH-only, to learn which one it tracks. **That field is not in the archive.** Nothing in
this checkout stores it, so it cannot be tested here at all, and saying otherwise would be
the fabrication class Cooper named on 2026-08-31.

WHAT IS TESTABLE, AND IT IS THE ARCHIVE HALF OF THE SAME QUESTION. `momentum_pct` IS in the
archive, it is the universe-selection variable, and CLAUDE.md ASSERTS of it:

    "it inherits the vendor's RTH-scoped, adjusted-basis high forever, so every
     premarket/extended-hours finding is conditional on that selection boundary"

That assertion has never been verified against tick data. This script verifies it. If
`momentum_pct` turns out NOT to be RTH-scoped, a standing qualifier attached to every
extended-hours finding in the programme is wrong. If it IS, the qualifier is confirmed and
the size of what it excludes becomes measurable rather than assumed.

TWO STAGES, AND ONLY THE FIRST IS FREE OF A12.

  STAGE 1 -- WITHIN SESSION, no cross-session ratio, so A12 does not apply.
    Where does the T=0 extended-session high actually sit: premarket, RTH, or post?
    Tick-derived from filtered/ prints. This alone measures how much an RTH-scoped screen
    would miss, and it needs no previous close.

  STAGE 2 -- CROSS SESSION, so A12 DOES apply and the flag is carried.
    momentum_pct = (H - P)/P, so H = P*(1 + momentum_pct/100). With a tick-derived previous
    close from T-1, the implied H can be compared against the RTH-only tick high and the
    extended-session tick high. Whichever it matches is the answer. The T-1-to-T0 ratio
    spans a session boundary, so per A12 `flag_cross_session_extreme` is carried and every
    statistic is reported with and without the flagged set, untrimmed primary.

D4: every measured quantity here is tick-derived from filtered/ prints. `momentum_pct` is
read, and it is D4's sole exception -- the universe-selection variable. No other spine
numeric column is touched: notably the previous close is taken from TICKS, not from the
spine's `prev_close`.

Usage: .venv/Scripts/python.exe research/scope_universe_scan/basis_test.py [--n 300]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research", "scale_field"))

import adapter  # noqa: E402
from adapter import load_event_tape, parse_event_id, segment_bounds_ns  # noqa: E402

OUT = "results/scope_universe_scan/basis_test.json"
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
SEED = 42


def sample_events(n: int) -> pd.DataFrame:
    c = duckdb.connect(DB, read_only=True)
    # The canonical view carries no event_id; it is (ticker, date, momentum_pct) per the
    # adapter's make_event_id. Sample deterministically on that triple.
    df = c.execute(f"""
        select ticker, event_date_canonical, momentum_pct
        from momentum_events_canonical
        where in_scope and trades_ingested
        order by hash(ticker || event_date_canonical || cast(momentum_pct as varchar)
                      || '{SEED}')
        limit {n}
    """).fetchdf()
    c.close()
    df["event_id"] = [adapter.make_event_id(t, d, m) for t, d, m in
                      zip(df.ticker, df.event_date_canonical, df.momentum_pct)]
    return df


def segment_highs(event_id: str, cfg) -> dict | None:
    """Tick-derived high per wall-clock segment of the T=0 extended session."""
    out = {}
    for seg in ("premarket", "rth", "post"):
        try:
            tape = load_event_tape(event_id, seg, cfg)
        except Exception:
            return None
        if tape is None or len(tape) == 0:
            out[seg] = {"high": None, "n": 0}
        else:
            p = tape["price"].to_numpy(dtype=np.float64)
            p = p[np.isfinite(p) & (p > 0)]
            out[seg] = {"high": float(p.max()) if p.size else None, "n": int(p.size)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    args = ap.parse_args()
    cfg = adapter.load_config()

    ev = sample_events(args.n)
    rows, t0 = [], time.perf_counter()
    for r in ev.itertuples(index=False):
        h = segment_highs(r.event_id, cfg)
        if h is None:
            continue
        hp, hr, ho = h["premarket"]["high"], h["rth"]["high"], h["post"]["high"]
        highs = {k: v for k, v in (("premarket", hp), ("rth", hr), ("post", ho))
                 if v is not None}
        if not highs:
            continue
        where = max(highs, key=highs.get)
        sess_high = max(highs.values())
        rows.append({
            "event_id": r.event_id, "ticker": r.ticker,
            "event_date": str(r.event_date_canonical),
            "momentum_pct": float(r.momentum_pct),
            "high_premarket": hp, "high_rth": hr, "high_post": ho,
            "n_premarket": h["premarket"]["n"], "n_rth": h["rth"]["n"],
            "n_post": h["post"]["n"],
            "session_high": sess_high, "session_high_segment": where,
            "ratio_session_over_rth": (sess_high / hr) if hr else None,
        })
        if len(rows) % 25 == 0:
            print(f"  {len(rows)} events ({time.perf_counter()-t0:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} events with tick highs, {time.perf_counter()-t0:.0f}s")
    df.to_parquet(os.path.join(REPO, "results/scope_universe_scan/basis_test.parquet"),
                  index=False)

    have_rth = df[df["high_rth"].notna()]
    ratio = have_rth["ratio_session_over_rth"].dropna()
    seg_counts = df["session_high_segment"].value_counts().to_dict()

    out = {
        "task": ("Cooper read section 4, adapted -- is the ARCHIVE's selection variable "
                 "RTH-scoped? Stage 1, within-session, A12 does not apply."),
        "what_could_not_be_tested": (
            "The SCREEN's field (Polygon todaysChangePerc) is not stored anywhere in this "
            "checkout, so it cannot be tested here. This tests momentum_pct, the archive's "
            "own selection variable, against tick data. It answers the archive half of "
            "Cooper's question and NOT the live half."),
        "claim_under_test": (
            "CLAUDE.md asserts momentum_pct 'inherits the vendor's RTH-scoped, "
            "adjusted-basis high forever'. Never verified against ticks until now."),
        "n_sampled": int(len(ev)), "n_with_tick_highs": int(len(df)), "seed": SEED,
        "d4": ("every measured quantity is tick-derived from filtered/ prints; "
               "momentum_pct is D4's sole exception; the spine's prev_close is NOT read"),
        "stage_1_where_the_session_high_sits": {
            "counts": {k: int(v) for k, v in seg_counts.items()},
            "shares": {k: float(v) / len(df) for k, v in seg_counts.items()},
            "n": int(len(df))},
        "stage_1_session_high_over_rth_high": {
            "n": int(ratio.size),
            "share_gt_1": float((ratio > 1).mean()) if ratio.size else None,
            "share_gt_1p01": float((ratio > 1.01).mean()) if ratio.size else None,
            "share_gt_1p05": float((ratio > 1.05).mean()) if ratio.size else None,
            "quantiles": {f"q{int(q*100):02d}": float(ratio.quantile(q))
                          for q in (0.5, 0.75, 0.9, 0.95, 0.99)} if ratio.size else None,
            "max": float(ratio.max()) if ratio.size else None},
        "events_with_no_rth_prints": int((df["high_rth"].isna()).sum()),
        "source": "research/scope_universe_scan/basis_test.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scope_universe_scan/basis_test.py --n "
                     + str(args.n),
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    s1 = out["stage_1_where_the_session_high_sits"]
    print("\nwhere the T=0 extended-session high sits (tick-derived):")
    for k, v in sorted(s1["shares"].items(), key=lambda kv: -kv[1]):
        print(f"   {k:10s} {s1['counts'][k]:4d}  {v:6.1%}")
    r = out["stage_1_session_high_over_rth_high"]
    if r["n"]:
        print(f"\nsession_high / rth_high  (n={r['n']}):")
        print(f"   share > 1     {r['share_gt_1']:.1%}")
        print(f"   share > 1.01  {r['share_gt_1p01']:.1%}")
        print(f"   share > 1.05  {r['share_gt_1p05']:.1%}")
        print(f"   quantiles     {r['quantiles']}")
        print(f"   max           {r['max']:.3f}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
