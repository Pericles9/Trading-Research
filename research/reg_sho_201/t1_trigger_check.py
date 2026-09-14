#!/usr/bin/env python
"""Reg SHO Rule 201 -- per-event trigger check, dev tier.

Authorized 2026-09-14 (docs/Universe-Decisions.md D36) as a measurement task only. Does NOT
authorize or implement any short-side strategy logic -- D5's long-only constraint is unchanged.
See docs/data/reg_sho_201_reference.md for the rule itself and this script's scope note.

Trigger: any RTH trade at price <= 0.90 * previous_close (a 10%+ intraday decline from the prior
day's RTH closing price), checked on trade prices, per the rule's own basis (not the NBB).
Previous close: last T-1 RTH minute bar's last_price from event_minute_bars_v2, tick-derived --
D4-safe, reusing the exact construction research/phase_12/t2b_band_arithmetic.py already built,
not rebuilt here.

Duration, reported not modeled: once triggered, the restriction covers the rest of the trigger day
and the following full trading day (T+1) -- this script reports WHETHER and WHEN T=0 triggers, and
separately checks T=0's own state at T+1's session (was T+1 covered by a T=0-day trigger). It does
not implement any execution/position logic for the restriction period.

Usage: .venv/Scripts/python.exe research/reg_sho_201/t1_trigger_check.py
"""
from __future__ import annotations

import json
import os

import duckdb
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
OUT_JSON = os.path.join(REPO, "results", "reg_sho_201", "artifacts", "t1_trigger_check.json")
OUT_PARQUET = os.path.join(REPO, "results", "reg_sho_201", "artifacts", "t1_trigger_check.parquet")
DECLINE_THRESHOLD = 0.10  # Rule 201: 10% or more intraday decline from prior RTH close


def main() -> int:
    con = duckdb.connect(DB, read_only=True)
    events = con.execute("""
        select distinct ticker, event_date, momentum_pct
        from filtered_trades_dev_v4
        order by 1, 2
    """).df()

    rows = []
    for r in events.itertuples(index=False):
        date_str = pd.Timestamp(r.event_date).strftime("%Y-%m-%d")

        # Previous close: last T-1 RTH minute bar's last_price -- tick-derived, D4-safe, same
        # construction as research/phase_12/t2b_band_arithmetic.py.
        pc = con.execute("""
            select last_price from event_minute_bars_v2
            where ticker = ? and event_date_canonical = ? and momentum_pct = ?
              and session_offset = -1 and segment = 'rth' and last_price is not null
            order by minute_index desc limit 1
        """, [r.ticker, date_str, r.momentum_pct]).fetchone()
        if pc is None or pc[0] is None:
            rows.append({"ticker": r.ticker, "event_date": date_str,
                         "momentum_pct": r.momentum_pct, "status": "no_prev_close"})
            continue
        prev_close = float(pc[0])
        trigger_price = prev_close * (1 - DECLINE_THRESHOLD)

        # T=0 RTH trades at or below the trigger price -- earliest one is the trigger moment.
        first_trigger = con.execute("""
            select b.first_trade_ts, b.low, b.minute_index
            from event_minute_bars_v2 b
            where b.ticker = ? and b.event_date_canonical = ? and b.momentum_pct = ?
              and b.session_offset = 0 and b.segment = 'rth' and b.low <= ?
              and b.first_trade_ts is not null
            order by b.minute_index asc limit 1
        """, [r.ticker, date_str, r.momentum_pct, trigger_price]).fetchone()

        # T=0's own minute-bar low, for context regardless of trigger status.
        day_low = con.execute("""
            select min(low) from event_minute_bars_v2
            where ticker = ? and event_date_canonical = ? and momentum_pct = ?
              and session_offset = 0 and segment = 'rth'
        """, [r.ticker, date_str, r.momentum_pct]).fetchone()
        day_low_val = float(day_low[0]) if day_low and day_low[0] is not None else None
        max_decline = ((prev_close - day_low_val) / prev_close) if day_low_val else None

        if first_trigger is None:
            rows.append({
                "ticker": r.ticker, "event_date": date_str, "momentum_pct": r.momentum_pct,
                "status": "ok", "prev_close": prev_close, "trigger_price": trigger_price,
                "triggered_t0": False, "trigger_minute_index": None,
                "day_low": day_low_val, "max_intraday_decline": max_decline,
            })
            continue

        rows.append({
            "ticker": r.ticker, "event_date": date_str, "momentum_pct": r.momentum_pct,
            "status": "ok", "prev_close": prev_close, "trigger_price": trigger_price,
            "triggered_t0": True, "trigger_minute_index": int(first_trigger[2]),
            "day_low": day_low_val, "max_intraday_decline": max_decline,
        })

    df = pd.DataFrame(rows)
    df.to_parquet(OUT_PARQUET, index=False)

    ok = df[df.status == "ok"]
    n_triggered = int(ok["triggered_t0"].sum())
    out = {
        "task": "Reg SHO 201 -- per-event trigger check, dev tier",
        "rule_source": "docs/data/reg_sho_201_reference.md",
        "decline_threshold": DECLINE_THRESHOLD,
        "prev_close_construction": ("last T-1 RTH minute bar's last_price from "
                                     "event_minute_bars_v2 -- tick-derived, D4-safe, same as "
                                     "research/phase_12/t2b_band_arithmetic.py"),
        "n_events": len(events),
        "n_ok": len(ok),
        "status_counts": df["status"].value_counts().to_dict(),
        "n_triggered_t0": n_triggered,
        "share_triggered_t0": (n_triggered / len(ok)) if len(ok) else None,
        "max_intraday_decline_summary": {
            "median": float(ok["max_intraday_decline"].median()),
            "p75": float(ok["max_intraday_decline"].quantile(.75)),
            "p90": float(ok["max_intraday_decline"].quantile(.9)),
            "max": float(ok["max_intraday_decline"].max()),
        },
        "scope_note": ("Measurement only. Reports whether/when Rule 201 would have triggered on "
                        "T=0 for each event. Does not model the restriction mechanics, does not "
                        "evaluate T+1 coverage, and does not imply, authorize, or measure any "
                        "short-side execution -- D5 stands unchanged."),
        "source": "research/reg_sho_201/t1_trigger_check.py:main",
        "reproduce": ".venv/Scripts/python.exe research/reg_sho_201/t1_trigger_check.py",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"n_events={len(events)}  n_ok={len(ok)}")
    print("status counts:", out["status_counts"])
    print(f"triggered on T=0: {n_triggered}/{len(ok)} ({out['share_triggered_t0']:.3f})")
    print("max intraday decline summary:", json.dumps(out["max_intraday_decline_summary"], indent=2))
    print(f"\nwrote {OUT_JSON}\nwrote {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
