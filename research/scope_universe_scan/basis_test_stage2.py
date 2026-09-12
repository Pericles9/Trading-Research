#!/usr/bin/env python
"""
Stage 2 of the basis test: does `momentum_pct` track the RTH-only high or the
extended-session high?

THE CLAIM UNDER TEST. CLAUDE.md asserts, as a standing qualifier on every
premarket/extended-hours finding in the programme, that `momentum_pct`

    "inherits the vendor's RTH-scoped, adjusted-basis high forever, so every
     premarket/extended-hours finding is conditional on that selection boundary"

Asserted since 2026-07-24. Never verified against tick data. Stage 1 measured how much
that boundary would cost if the claim is true (31.9% of T=0 session highs sit outside
RTH). This stage tests whether it IS true.

THE TEST. momentum_pct = (H - P)/P * 100, so H = P * (1 + momentum_pct/100). With a
tick-derived previous close P, the implied H can be compared against two tick-derived
candidates from the T=0 tape:

    H_rth   the RTH-only high
    H_sess  the extended-session high (premarket, RTH and post)

Whichever the implied H sits closer to, in log distance, is what the vendor's high was
scoped to. On events where H_sess == H_rth the test is uninformative by construction and
those are excluded from the discriminating set and reported separately.

REUSE, NOT REBUILD. P comes from `results/phase_9/artifacts/t1_cross_session_flags.parquet`
-- `price_earlier` on the `tm1_t0` pair, already tick-derived and already committed. That
artifact also carries `flag_cross_session_extreme`, which is exactly what A12 requires here.

A12 APPLIES AND IS HONOURED. P is a T-1 price and H is a T=0 price, so implied_H/H_* is a
ratio spanning a session boundary -- A12 covers it, "denominators count". Every statistic is
reported WITH and WITHOUT the flagged set, untrimmed primary, flagged events reported as
their own row and never dropped.

D4. Every measured quantity is tick-derived. `momentum_pct` is read and is D4's sole
exception. The spine's `prev_close` is NOT read -- P is tick-derived.

Usage: .venv/Scripts/python.exe research/scope_universe_scan/basis_test_stage2.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

STAGE1 = "results/scope_universe_scan/basis_test.parquet"
FLAGS = "results/phase_9/artifacts/t1_cross_session_flags.parquet"
OUT = "results/scope_universe_scan/basis_test_stage2.json"


def summarise(d: pd.DataFrame, label: str) -> dict:
    """Which candidate does the implied high sit closer to, in log distance?"""
    if not len(d):
        return {"label": label, "n": 0}
    closer_rth = int((d["dist_rth"] < d["dist_sess"]).sum())
    closer_sess = int((d["dist_sess"] < d["dist_rth"]).sum())
    tie = int(len(d) - closer_rth - closer_sess)
    return {
        "label": label, "n": int(len(d)),
        "closer_to_RTH_high": closer_rth,
        "closer_to_EXTENDED_high": closer_sess,
        "tie": tie,
        "share_closer_to_RTH": closer_rth / len(d),
        "median_log_dist_to_rth": float(d["dist_rth"].median()),
        "median_log_dist_to_sess": float(d["dist_sess"].median()),
        "median_implied_over_rth": float((d["implied_H"] / d["high_rth"]).median()),
        "median_implied_over_sess": float((d["implied_H"] / d["session_high"]).median()),
    }


def main() -> int:
    s1 = pd.read_parquet(os.path.join(REPO, STAGE1))
    fl = pd.read_parquet(os.path.join(REPO, FLAGS))
    fl = fl[fl["session_pair"] == "tm1_t0"].copy()
    fl["event_date"] = fl["event_date_canonical"].astype(str)

    d = s1.merge(
        fl[["ticker", "event_date", "mp", "price_earlier",
            "flag_cross_session_extreme"]],
        left_on=["ticker", "event_date", "momentum_pct"],
        right_on=["ticker", "event_date", "mp"], how="inner")

    d = d[d["price_earlier"].notna() & (d["price_earlier"] > 0)
          & d["high_rth"].notna() & (d["high_rth"] > 0)
          & d["session_high"].notna() & (d["session_high"] > 0)].copy()

    d["implied_H"] = d["price_earlier"] * (1.0 + d["momentum_pct"] / 100.0)
    d["dist_rth"] = np.abs(np.log(d["implied_H"] / d["high_rth"]))
    d["dist_sess"] = np.abs(np.log(d["implied_H"] / d["session_high"]))
    d["discriminating"] = d["session_high"] > d["high_rth"] * 1.001

    disc = d[d["discriminating"]]
    out = {
        "task": ("Stage 2 -- does momentum_pct track the RTH-only high or the "
                 "extended-session high?"),
        "claim_under_test": ("CLAUDE.md: momentum_pct 'inherits the vendor's RTH-scoped, "
                             "adjusted-basis high forever'. Asserted 2026-07-24, never "
                             "verified against ticks."),
        "method": ("implied_H = P * (1 + momentum_pct/100) with P = tick-derived T-1 close "
                   "(price_earlier on the tm1_t0 pair, committed Phase 9 artifact). "
                   "Compared in log distance against the tick RTH high and the tick "
                   "extended-session high."),
        "a12": ("P is T-1 and H is T=0, so every ratio here spans a session boundary. A12 "
                "applies -- denominators count. Reported WITH and WITHOUT "
                "flag_cross_session_extreme; untrimmed is primary and flagged events are "
                "their own row, never dropped."),
        "d4": ("all measured quantities tick-derived; momentum_pct is D4's sole exception; "
               "the spine's prev_close is NOT read"),
        "n_stage1": int(len(s1)),
        "n_joined_to_flags": int(len(d)),
        "n_discriminating": int(len(disc)),
        "n_non_discriminating": int(len(d) - len(disc)),
        "non_discriminating_note": ("events whose extended high equals their RTH high "
                                    "within 0.1%. The test cannot separate the two "
                                    "candidates there, by construction."),
        "PRIMARY_untrimmed": summarise(disc, "discriminating, untrimmed (PRIMARY)"),
        "excluding_a12_flagged": summarise(
            disc[~disc["flag_cross_session_extreme"].astype(bool)],
            "discriminating, A12-flagged removed"),
        "a12_flagged_only": summarise(
            disc[disc["flag_cross_session_extreme"].astype(bool)],
            "discriminating, A12-flagged only"),
        "n_a12_flagged_in_discriminating": int(
            disc["flag_cross_session_extreme"].astype(bool).sum()),
        "source": "research/scope_universe_scan/basis_test_stage2.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scope_universe_scan/basis_test_stage2.py",
    }
    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    print(f"stage 1 events {out['n_stage1']}, joined to A12 flags {out['n_joined_to_flags']}")
    print(f"discriminating (extended high > rth high by >0.1%): {out['n_discriminating']}"
          f"   non-discriminating: {out['n_non_discriminating']}")
    print(f"A12-flagged within the discriminating set: "
          f"{out['n_a12_flagged_in_discriminating']}\n")
    for k in ("PRIMARY_untrimmed", "excluding_a12_flagged", "a12_flagged_only"):
        s = out[k]
        if not s.get("n"):
            print(f"{s['label']}: n=0"); continue
        print(f"{s['label']}  (n={s['n']})")
        print(f"   closer to RTH high      {s['closer_to_RTH_high']:4d}  "
              f"{s['share_closer_to_RTH']:6.1%}")
        print(f"   closer to EXTENDED high {s['closer_to_EXTENDED_high']:4d}  "
              f"{1 - s['share_closer_to_RTH']:6.1%}")
        print(f"   median implied/rth {s['median_implied_over_rth']:.4f}   "
              f"median implied/extended {s['median_implied_over_sess']:.4f}\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
