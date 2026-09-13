#!/usr/bin/env python
"""T2 -- construct the ISO-share variable, dev tier only (50 primary events).

Definition, stated before computing (prompt T2):

    iso_share(event) = SUM(size WHERE 14 IN conditions, t in [W_lo, W_hi])
                      / SUM(size,                        t in [W_lo, W_hi])

W_lo = session_window(event_date, 0)['start_ns']  -- T=0 extended-day session start (04:00 ET, D3)
W_hi = last_trade_ts of event_minute_bars_v2 at minute_index = det_minute + 5

Both bounds come from already-committed machinery (T0): session_window() (D3 clock) and the
minute cache's own trade timestamps, not an assumed fixed-seconds offset. det_undefined events
(no anchor) are excluded, matching research/phase_10e/t1_candidate_entries.py.

Read path: trade_files() for file discovery (base + Phase 1c repair siblings), then a direct
per-event parquet read requesting `conditions` explicitly -- read_event_trades() in the same
module does not carry that column, so it is not reused for the read itself, only for file
discovery (T0's finding).

The print's own size counts in both its own numerator (if ISO-flagged) and the denominator --
stated here so the boundary convention is explicit rather than incidental (same rule T2 of
impact_by_participation.md applied to its own denominator).

Usage: .venv/Scripts/python.exe research/iso_share_hold_length/t2_iso_share.py
"""
from __future__ import annotations

import json
import os
import sys

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
OUT_JSON = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t2_iso_share.json")
OUT_PARQUET = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t2_iso_share.parquet")
LATENCY_MIN = 5
ISO_CODE = 14

sys.path.insert(0, os.path.join(REPO, "research", "phase_10"))
import common  # noqa: E402


def read_conditions(cfg, ticker, event_date, mp):
    """Per-event trades with `conditions`, base + repair siblings. Not read_event_trades()
    (T0: that function doesn't request `conditions`)."""
    files = common.trade_files(cfg, ticker, event_date, mp)
    if not files:
        return None
    cols = ["sip_timestamp", "size", "conditions"]
    frames = [pd.read_parquet(f, columns=cols) for f in files]
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


def main() -> int:
    cfg = json.load(open(os.path.join(REPO, "config", "phase_10.json"), encoding="utf-8"))

    con = duckdb.connect(DB, read_only=True)
    dev = con.execute("""
        select ticker, event_date, momentum_pct
        from filtered_trades_dev_v4
        where dev_cohort = 'primary'
        group by 1, 2, 3
        order by 1, 2
    """).df()

    anch = pd.read_parquet(os.path.join(
        REPO, "results", "phase_8", "artifacts", "a102_detection_anchors.parquet"))
    anch = anch.rename(columns={"mp": "momentum_pct"})

    dev["event_date"] = pd.to_datetime(dev["event_date"])
    anch["event_date_canonical"] = pd.to_datetime(anch["event_date_canonical"])
    dev = dev.merge(
        anch[["ticker", "event_date_canonical", "momentum_pct", "det_minute", "det_undefined"]],
        left_on=["ticker", "event_date", "momentum_pct"],
        right_on=["ticker", "event_date_canonical", "momentum_pct"],
        how="left",
    )

    n_no_anchor_row = int(dev["det_minute"].isna().sum())
    n_det_undefined = int(dev["det_undefined"].fillna(True).sum())

    con.execute(f"ATTACH '{DB}' AS m (READ_ONLY)")

    rows = []
    for r in dev.itertuples(index=False):
        rec = {
            "ticker": r.ticker, "event_date": str(r.event_date.date()),
            "momentum_pct": r.momentum_pct,
        }
        if pd.isna(r.det_minute) or bool(r.det_undefined):
            rec.update(status="no_anchor", n_prints=0, n_iso_prints=0,
                       size_total=0, size_iso=0, iso_share=np.nan)
            rows.append(rec)
            continue

        det_minute = int(r.det_minute)
        entry_minute = det_minute + LATENCY_MIN

        sw = common.session_window(str(r.event_date.date()), 0)
        if sw is None:
            rec.update(status="no_session_window", n_prints=0, n_iso_prints=0,
                       size_total=0, size_iso=0, iso_share=np.nan)
            rows.append(rec)
            continue
        w_lo = sw["start_ns"]

        mb = con.execute("""
            select last_trade_ts from m.event_minute_bars_v2
            where ticker = ? and event_date_canonical = ? and momentum_pct = ?
              and session_offset = 0 and minute_index = ?
        """, [r.ticker, str(r.event_date.date()), r.momentum_pct, entry_minute]).fetchone()
        if mb is None or mb[0] is None:
            # entry_minute bar has no trades (n_trades=0) or doesn't exist; fall back to the
            # last available minute at or before entry_minute so the window is never empty
            mb = con.execute("""
                select last_trade_ts from m.event_minute_bars_v2
                where ticker = ? and event_date_canonical = ? and momentum_pct = ?
                  and session_offset = 0 and minute_index <= ? and last_trade_ts is not null
                order by minute_index desc limit 1
            """, [r.ticker, str(r.event_date.date()), r.momentum_pct, entry_minute]).fetchone()
        if mb is None or mb[0] is None:
            rec.update(status="no_upper_bound", n_prints=0, n_iso_prints=0,
                       size_total=0, size_iso=0, iso_share=np.nan)
            rows.append(rec)
            continue
        w_hi = int(mb[0])

        df = read_conditions(cfg, r.ticker, str(r.event_date.date()), r.momentum_pct)
        if df is None or len(df) == 0:
            rec.update(status="no_trade_files", n_prints=0, n_iso_prints=0,
                       size_total=0, size_iso=0, iso_share=np.nan)
            rows.append(rec)
            continue

        win = df[(df["sip_timestamp"] >= w_lo) & (df["sip_timestamp"] <= w_hi)]
        n_prints = int(len(win))
        if n_prints == 0:
            rec.update(status="empty_window", n_prints=0, n_iso_prints=0,
                       size_total=0, size_iso=0, iso_share=np.nan)
            rows.append(rec)
            continue

        is_iso = win["conditions"].apply(
            lambda c: (c is not None) and (ISO_CODE in list(c)))
        size_total = float(win["size"].sum())
        size_iso = float(win.loc[is_iso, "size"].sum())
        rec.update(
            status="ok", det_minute=det_minute, entry_minute=entry_minute,
            window_start_ns=int(w_lo), window_end_ns=int(w_hi),
            n_prints=n_prints, n_iso_prints=int(is_iso.sum()),
            size_total=size_total, size_iso=size_iso,
            iso_share=(size_iso / size_total if size_total > 0 else np.nan),
        )
        rows.append(rec)

    out = pd.DataFrame(rows)
    out.to_parquet(OUT_PARQUET, index=False)

    ok = out[out.status == "ok"]
    coverage = len(ok) / len(out)
    summary = {
        "task": "T2 -- per-event ISO share, dev tier, latency=5min entry anchor",
        "n_events": int(len(out)),
        "n_ok": int(len(ok)),
        "coverage": coverage,
        "status_counts": out["status"].value_counts().to_dict(),
        "n_no_anchor_row": n_no_anchor_row,
        "n_det_undefined": n_det_undefined,
        "iso_share_summary": {
            "n": int(ok["iso_share"].notna().sum()),
            "mean": float(ok["iso_share"].mean()),
            "median": float(ok["iso_share"].median()),
            "q25": float(ok["iso_share"].quantile(.25)),
            "q75": float(ok["iso_share"].quantile(.75)),
            "share_exactly_zero": float((ok["iso_share"] == 0).mean()),
            "max": float(ok["iso_share"].max()),
        },
        "window_definition": ("[session_window(event_date,0).start_ns, "
                               "last_trade_ts @ minute_index=det_minute+5 "
                               "(or nearest prior non-empty bar)]"),
        "iso_code": ISO_CODE,
        "latency_minutes": LATENCY_MIN,
        "source": "research/iso_share_hold_length/t2_iso_share.py:main",
        "reproduce": ".venv/Scripts/python.exe research/iso_share_hold_length/t2_iso_share.py",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"n_events={summary['n_events']}  n_ok={summary['n_ok']}  coverage={coverage:.3f}")
    print("status counts:", summary["status_counts"])
    print("iso_share summary:", json.dumps(summary["iso_share_summary"], indent=2))
    print(f"\nwrote {OUT_JSON}\nwrote {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
