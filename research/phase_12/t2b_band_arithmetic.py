#!/usr/bin/env python
"""Phase 12 T2b -- route 3: band arithmetic, dev tier.

Every parameter cites its config key (Escalation row 4). D4 stands: previous close is computed
from tick data (the last T-1 RTH trade), never read from any spine numeric column -- Escalation
row 6.

Evaluated at MINUTE BAR granularity (config.route_3_band_arithmetic.evaluate_at's explicit
fallback: "every minute bar if quote-level proves out of budget"), using event_minute_bars_v2's
per-minute VWAP as the eligible-transactions input to the reference-price rolling window. This is
a disclosed approximation to config.luld_bands.reference_price_rule's true tick-level definition,
not the definition itself -- stated here, not smoothed over.

Reference price (docs/data/luld_plan_reference.md Sec 2): the mean of eligible trades over the
prior 5 minutes, recomputed periodically, updated only if the new candidate differs from the
current reference price by >= 1%. Implemented here as a per-minute sequential loop: at each minute
m, the candidate is the volume-weighted mean vwap of minutes [m-4, m] (5 one-minute bars); the
reference price updates to the candidate only if it differs from the current reference price by
>= 1%; otherwise the current reference price persists (matches the hysteresis rule, approximated
at minute rather than 30-second cadence).

Tier: this cohort is Tier 2 by exclusion (micro-cap, not S&P 500/Russell 1000/a listed ETP) per
config.luld_bands.universe_tier_expected -- NOT individually confirmed against an index
membership list for each event, which is not available in this checkout. Stated as an assumption,
not verified per event, matching the config's own "CONFIRM per event rather than assuming" note
that this task cannot fully satisfy without external index-membership data.

Usage: .venv/Scripts/python.exe research/phase_12/t2b_band_arithmetic.py
"""
from __future__ import annotations

import json
import os

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
OUT_JSON = os.path.join(REPO, "results", "phase_12", "artifacts", "t2b_band_arithmetic.json")
OUT_PARQUET = os.path.join(REPO, "results", "phase_12", "artifacts", "t2_band_arithmetic.parquet")

AMENDMENT_18_DATE = pd.Timestamp("2020-02-24")
HYSTERESIS_PCT = 0.01          # luld_bands.reference_price_rule
ROLLING_WINDOW_MIN = 5         # luld_bands.reference_price_rule
TIER2_BRACKETS = [             # luld_bands.band_table_tier_2.brackets
    {"lo": 3.0, "hi": None, "pct": 0.10},
    {"lo": 0.75, "hi": 3.0, "pct": 0.20},
    {"lo": 0.0, "hi": 0.75, "pct": None, "dollar_alt": 0.15, "pct_alt": 0.75},
]
DOUBLING_START_MIN_OF_DAY = 15 * 60 + 35   # 15:35 ET -- luld_bands.doubling_windows[0].start_local
DOUBLING_END_MIN_OF_DAY = 16 * 60          # 16:00 ET


def bracket_for(prev_close: float) -> dict:
    for b in TIER2_BRACKETS:
        lo_ok = prev_close >= b["lo"]
        hi_ok = (b["hi"] is None) or (prev_close < b["hi"])
        if lo_ok and hi_ok:
            return b
    return TIER2_BRACKETS[-1]


def band_width(ref_price: float, bracket: dict, doubled: bool) -> tuple:
    """Returns (lower_band, upper_band). D19: caller reports both bp and cents."""
    mult = 2.0 if doubled else 1.0
    if bracket["pct"] is not None:
        w = ref_price * bracket["pct"] * mult
        return ref_price - w, ref_price + w
    # sub-$0.75 bracket: lesser of $dollar_alt or pct_alt%, doubled upper-band only per
    # luld_plan_reference.md Sec 4 (moderate confidence -- floor-consequence, not a distinct rule)
    dollar = bracket["dollar_alt"] * mult
    pct = ref_price * bracket["pct_alt"] * mult
    w_upper = min(dollar, pct)
    w_lower = min(bracket["dollar_alt"], ref_price * bracket["pct_alt"])  # not doubled, per Sec 4
    return max(ref_price - w_lower, 0.0), ref_price + w_upper


def main() -> int:
    con = duckdb.connect(DB, read_only=True)
    events = con.execute("""
        select distinct ticker, event_date, momentum_pct
        from filtered_trades_dev_v4
        order by 1, 2
    """).df()

    rows = []
    event_summaries = []

    for r in events.itertuples(index=False):
        date_str = pd.Timestamp(r.event_date).strftime("%Y-%m-%d")
        is_pre_amendment_18 = pd.Timestamp(r.event_date) < AMENDMENT_18_DATE

        # T-1 previous close: last RTH minute bar's last_price, session_offset = -1. Tick-derived
        # (event_minute_bars_v2.last_price is built from filtered_trades, not the spine) -- D4-safe.
        pc = con.execute("""
            select last_price from event_minute_bars_v2
            where ticker = ? and event_date_canonical = ? and momentum_pct = ?
              and session_offset = -1 and segment = 'rth' and last_price is not null
            order by minute_index desc limit 1
        """, [r.ticker, date_str, r.momentum_pct]).fetchone()
        if pc is None or pc[0] is None:
            event_summaries.append({"ticker": r.ticker, "event_date": date_str,
                                     "momentum_pct": r.momentum_pct, "status": "no_prev_close"})
            continue
        prev_close = float(pc[0])
        bracket = bracket_for(prev_close)

        bars = con.execute("""
            select minute_index, vwap, high, low, n_trades, first_trade_ts
            from event_minute_bars_v2
            where ticker = ? and event_date_canonical = ? and momentum_pct = ?
              and session_offset = 0 and segment = 'rth'
            order by minute_index
        """, [r.ticker, date_str, r.momentum_pct]).df()
        if len(bars) == 0:
            event_summaries.append({"ticker": r.ticker, "event_date": date_str,
                                     "momentum_pct": r.momentum_pct, "status": "no_rth_bars"})
            continue

        bars = bars[bars.n_trades > 0].reset_index(drop=True)
        if len(bars) == 0:
            event_summaries.append({"ticker": r.ticker, "event_date": date_str,
                                     "momentum_pct": r.momentum_pct, "status": "no_traded_bars"})
            continue

        ref_price = prev_close  # seed: no eligible trades yet, prior value persists
        n_touches = 0
        n_bracket_crossings = 0
        cur_bracket_lo = bracket["lo"]
        first_ts = pd.to_datetime(bars["first_trade_ts"], unit="ns", utc=True) \
                     .dt.tz_convert("America/New_York")
        for i, row_b in bars.iterrows():
            window = bars.iloc[max(0, i - ROLLING_WINDOW_MIN + 1): i + 1]
            candidate = float((window["vwap"] * window["n_trades"]).sum() / window["n_trades"].sum())
            if ref_price == 0 or abs(candidate - ref_price) / ref_price >= HYSTERESIS_PCT:
                ref_price = candidate

            live_bracket = bracket_for(ref_price)
            if live_bracket["lo"] != cur_bracket_lo:
                n_bracket_crossings += 1
                cur_bracket_lo = live_bracket["lo"]

            minute_of_day = first_ts.iloc[i].hour * 60 + first_ts.iloc[i].minute
            if is_pre_amendment_18:
                doubled = (DOUBLING_START_MIN_OF_DAY <= minute_of_day < DOUBLING_END_MIN_OF_DAY) or \
                          (9 * 60 + 30 <= minute_of_day < 9 * 60 + 45)
            else:
                doubled = (DOUBLING_START_MIN_OF_DAY <= minute_of_day < DOUBLING_END_MIN_OF_DAY) and \
                          (ref_price <= 3.00)

            lo_band, hi_band = band_width(ref_price, live_bracket, doubled)
            touched = (row_b["high"] >= hi_band) or (row_b["low"] <= lo_band)
            if touched:
                n_touches += 1

            dist_bp = min(abs(row_b["high"] - hi_band), abs(row_b["low"] - lo_band)) / ref_price * 10000
            rows.append({
                "ticker": r.ticker, "event_date": date_str, "momentum_pct": r.momentum_pct,
                "minute_index": int(row_b["minute_index"]), "reference_price": ref_price,
                "tier": 2, "price_bracket_lo": live_bracket["lo"],
                "doubling_window_active": bool(doubled),
                "is_pre_amendment_18": bool(is_pre_amendment_18),
                "lower_band": lo_band, "upper_band": hi_band,
                "distance_to_band_edge_bp": float(dist_bp),
                "distance_to_band_edge_cents": float(min(abs(row_b["high"] - hi_band),
                                                          abs(row_b["low"] - lo_band)) * 100),
                "touched_band": bool(touched),
            })

        event_summaries.append({
            "ticker": r.ticker, "event_date": date_str, "momentum_pct": r.momentum_pct,
            "status": "ok", "prev_close": prev_close, "initial_bracket_lo": bracket["lo"],
            "is_pre_amendment_18": bool(is_pre_amendment_18),
            "n_minutes": len(bars), "n_band_touches": n_touches,
            "n_bracket_crossings": n_bracket_crossings,
        })

    band_df = pd.DataFrame(rows)
    band_df.to_parquet(OUT_PARQUET, index=False)

    ok = [e for e in event_summaries if e["status"] == "ok"]
    n_events_crossed_bracket = sum(1 for e in ok if e["n_bracket_crossings"] > 0)
    n_events_touched_band = sum(1 for e in ok if e["n_band_touches"] > 0)

    out = {
        "task": "T2b -- route 3 band arithmetic, dev tier, minute-bar granularity",
        "config_keys_used": ["luld_bands.band_table_tier_2", "luld_bands.doubling_windows",
                              "luld_bands.pre_amendment_18_regime", "luld_bands.reference_price_rule"],
        "evaluate_at": "minute bar (config's explicit fallback, not tick/quote level)",
        "tier_assumption": ("Tier 2 for all events, NOT individually confirmed against an index "
                             "membership list (unavailable in this checkout) -- "
                             "config.luld_bands.universe_tier_expected, disclosed limitation."),
        "n_events": len(events),
        "status_counts": pd.Series([e["status"] for e in event_summaries]).value_counts().to_dict(),
        "n_events_ok": len(ok),
        "n_events_crossed_bracket_during_session": n_events_crossed_bracket,
        "share_events_crossed_bracket": (n_events_crossed_bracket / len(ok)) if ok else None,
        "n_events_touched_a_band": n_events_touched_band,
        "share_events_touched_a_band": (n_events_touched_band / len(ok)) if ok else None,
        "n_events_pre_amendment_18": sum(1 for e in ok if e["is_pre_amendment_18"]),
        "event_summaries": event_summaries,
        "source": "research/phase_12/t2b_band_arithmetic.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_12/t2b_band_arithmetic.py",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"n_events={len(events)}  n_ok={len(ok)}")
    print("status counts:", out["status_counts"])
    print(f"events that crossed a bracket mid-session: {n_events_crossed_bracket}/{len(ok)} "
          f"({out['share_events_crossed_bracket']:.3f})")
    print(f"events that touched a band edge (minute high/low): {n_events_touched_band}/{len(ok)} "
          f"({out['share_events_touched_a_band']:.3f})")
    print(f"pre-Amendment-18 events: {out['n_events_pre_amendment_18']}")
    print(f"\nwrote {OUT_JSON}\nwrote {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
