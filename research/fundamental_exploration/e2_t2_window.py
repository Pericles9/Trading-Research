"""
E2-T2: build the high-participation window. Per event: B_e (from e2_t2a_baseline.py),
n_baseline_sessions, the trailing 10-minute dollar-volume series from t0, the window
end under DE-2, duration_min, and censored.

**Mechanics, confirmed directly with Cooper (2026-09-15):**
- Volume basis: DOLLAR volume (volume x vwap per minute bar) throughout, not shares.
- Baseline B_e: mean of T-3..T-1's regular-hours dollar volume (already built).
- Window end: the first minute at/after t0 where the trailing 10-minute average dollar
  volume is <= 3x B_e, AND stays <= that threshold for the next 10 consecutive minutes
  (C=10, Cooper-confirmed) -- the window end is the START of that qualifying run, not
  its end; the 10-minute lookahead is a confirmation check against measuring the first
  dip in a noisy series.
- Censoring horizon: "end of tick data" (Cooper's choice, NOT the brief's suggested
  "end of extended session") -- the event's OWN last available minute bar in
  event_minute_bars_v2. An event with no qualifying run before that point is censored
  there, not dropped.
- baseline_thin: DEFERRED (Cooper). Not computed here -- left absent from the output,
  not defaulted to False. See config cooper_pending.de2_baseline_floor.

**minute_index <-> clock time**, confirmed directly (first_trade_ts inspection):
minute_index 0 = 04:00:00 America/New_York; minute_index 330 = 09:30:00 (rth start);
minute_index 959 = 19:59:00 (last minute before the 20:00 extended-session close).
i.e. minute_index = floor(minutes elapsed since that day's 04:00 ET). Used to place t0
on the session_offset=0 grid without a lookup table.

**Two window conventions, decided here and documented rather than left implicit:**
1. The rolling 10-minute average is computed over the SEQUENCE of trading minutes
   (session_offset*960 + minute_index, gap-filled to 0 for any minute with no bar --
   "no bar" means no trades that minute, a real zero), NOT padded across the overnight
   closed-market gap between one day's post session and the next day's premarket. A
   wall-clock rolling window spanning that gap would register 8+ hours of "zero volume"
   right at every session reopen and falsely end the window there every time.
2. `duration_min` is real WALL-CLOCK elapsed minutes (window end's timestamp minus t0,
   from actual epoch-ns), not a count of the synthetic trading-minute sequence -- so a
   window that closes on session_offset=+1 correctly reports the overnight hours as
   part of its duration, only the threshold-detection logic (point 1) skips them.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t2_window.py [--dev-n N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

MINUTES_PER_DAY = 960
CONFIRM_MINUTES = 10  # C, Cooper-confirmed
THRESHOLD_MULTIPLE = 3.0
RTH_OPEN_ET_MINUTE_OF_DAY = 4 * 60  # minute_index 0 == 04:00:00 America/New_York


def t0_minute_index(t0_ns: int, event_date_canonical: str) -> int:
    """minute_index on session_offset=0's own grid, per the confirmed 04:00 ET anchor."""
    ts = pd.Timestamp(t0_ns, unit="ns", tz="UTC").tz_convert("America/New_York")
    day_start = pd.Timestamp(f"{event_date_canonical} 04:00:00", tz="America/New_York")
    minutes = int((ts - day_start).total_seconds() // 60)
    return minutes


def build_event_series(bars: pd.DataFrame, t0_mi: int, b_e: float, t0_ns: int) -> dict:
    """bars: this event's rows (session_offset in 0..3), columns session_offset,
    minute_index, dollar_volume. Returns duration_min, censored, window_end_global_minute.

    t0_ns is needed (not just t0_mi) for one boundary case: when the qualifying window
    ends in t0's OWN minute, that minute's bar carries its first trade's timestamp, which
    can be a few seconds BEFORE t0_ns itself (t0 is a nanosecond-precision anchor that can
    fall anywhere inside its own 60-second bucket, not necessarily at the bucket's start) --
    using the bar's timestamp there would produce a spurious few-second negative duration.
    Clamped to t0_ns in that one case; every later minute already sits strictly after t0's
    entire 60-second bucket, so no clamping is needed there."""
    bars = bars.copy()
    bars["global_minute"] = bars["session_offset"] * MINUTES_PER_DAY + bars["minute_index"]
    t0_global = 0 * MINUTES_PER_DAY + t0_mi

    lo, hi = bars["global_minute"].min(), bars["global_minute"].max()
    if hi < t0_global:
        return {"duration_min": None, "censored": True, "window_end_global_minute": None,
                "window_end_ts": None, "reason": "no data at/after t0"}

    full = pd.DataFrame({"global_minute": np.arange(lo, hi + 1)})
    full = full.merge(bars[["global_minute", "dollar_volume", "first_trade_ts", "last_trade_ts"]],
                       on="global_minute", how="left")
    full["dollar_volume"] = full["dollar_volume"].fillna(0.0)
    # gap-filled minutes (no real trade, hence no real first_trade_ts) still need SOME
    # timestamp for duration reporting -- nearest real bar's timestamp is a fine
    # approximation for a minute where nothing traded anyway.
    full["first_trade_ts"] = full["first_trade_ts"].ffill().bfill()
    full["last_trade_ts"] = full["last_trade_ts"].ffill().bfill()

    roll = full["dollar_volume"].rolling(window=CONFIRM_MINUTES, min_periods=1).mean()
    qualifies = (roll <= THRESHOLD_MULTIPLE * b_e).to_numpy()

    # gaps-and-islands: find runs of consecutive True, length >= CONFIRM_MINUTES, whose
    # start position is >= t0_global (DE-2: "the first minute AFTER t0").
    n = len(qualifies)
    run_start = None
    i = 0
    start_search = np.searchsorted(full["global_minute"].to_numpy(), t0_global, side="left")
    while i < n:
        if not qualifies[i]:
            i += 1
            continue
        j = i
        while j < n and qualifies[j]:
            j += 1
        run_len = j - i
        run_pos = max(i, start_search)
        if run_pos < j and (j - run_pos) >= CONFIRM_MINUTES and run_pos >= start_search:
            run_start = run_pos
            break
        i = j

    if run_start is None:
        last_row = full.iloc[-1]
        return {"duration_min": None, "censored": True,
                "window_end_global_minute": int(full["global_minute"].iloc[-1]),
                "window_end_ts": int(last_row["last_trade_ts"]) if pd.notna(last_row["last_trade_ts"]) else None,
                "reason": "no qualifying 10-min run before end of tick data"}

    end_row = full.iloc[run_start]
    if int(end_row["global_minute"]) == t0_global:
        window_end_ts = t0_ns
    else:
        window_end_ts = int(end_row["first_trade_ts"]) if pd.notna(end_row["first_trade_ts"]) else None
    return {"duration_min": None, "censored": False,
            "window_end_global_minute": int(end_row["global_minute"]),
            "window_end_ts": window_end_ts,
            "reason": None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev-n", type=int, default=0, help="if >0, run on only this many events (dev/debug tier)")
    args = ap.parse_args()

    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)

    ef = C.load_event_fundamentals()[["event_id", "ticker", "t0_ns"]]
    baseline = pd.read_parquet(f"{C.ART_E2}/e2_t2a_baseline.parquet")[["event_id", "B_e", "n_baseline_sessions"]]

    events = frame[["event_id", "event_date_canonical", "momentum_pct"]].merge(ef, on="event_id", how="left")
    events = events.merge(baseline, on="event_id", how="left")
    events = events.dropna(subset=["B_e"])  # n_baseline_sessions==0 -> B_e NaN -> cannot build a window
    events["t0_mi"] = events.apply(lambda r: t0_minute_index(int(r["t0_ns"]), r["event_date_canonical"]), axis=1)

    if args.dev_n:
        events = events.sample(args.dev_n, random_state=42).reset_index(drop=True)
        print(f"DEV TIER: running on {len(events)} events")

    key = events[["event_id", "ticker", "event_date_canonical", "momentum_pct"]]

    con = C.connect(read_only=True)
    con.register("ev_key", key)
    sql = """
        SELECT k.event_id, b.session_offset, b.minute_index,
               b.volume * b.vwap AS dollar_volume, b.first_trade_ts, b.last_trade_ts
        FROM ev_key k
        JOIN event_minute_bars_v2 b
          ON b.ticker = k.ticker AND b.event_date_canonical = k.event_date_canonical
         AND b.momentum_pct = k.momentum_pct
        WHERE b.session_offset BETWEEN 0 AND 3
    """
    all_bars = con.execute(sql).df()
    con.close()

    results = []
    for _, ev in events.iterrows():
        bars = all_bars[all_bars["event_id"] == ev["event_id"]]
        r = build_event_series(bars, ev["t0_mi"], ev["B_e"], int(ev["t0_ns"]))
        if r["window_end_ts"] is not None:
            r["duration_min"] = (r["window_end_ts"] - int(ev["t0_ns"])) / 60e9
        r["event_id"] = ev["event_id"]
        r["n_baseline_sessions"] = ev["n_baseline_sessions"]
        r["B_e"] = ev["B_e"]
        results.append(r)

    out = pd.DataFrame(results)

    # brief's own explicit ask: assert, don't just structurally imply. Baseline bars are
    # never touched here at all (T2a's own SQL is session_offset IN (-3,-2,-1) only), and
    # every window_end_ts this script itself produced must sit at/after t0_ns -- a pre-t0
    # window_end would mean a bar from before detection got counted into the duration.
    with_end = out.dropna(subset=["window_end_ts"]).merge(
        events[["event_id", "t0_ns"]], on="event_id", how="left"
    )
    bad = with_end[with_end["window_end_ts"] < with_end["t0_ns"]]
    assert len(bad) == 0, f"{len(bad)} events have a window_end_ts before their own t0_ns: {bad['event_id'].tolist()[:5]}"

    out_path = f"{C.ART_E2}/e2_t2_window_dev.parquet" if args.dev_n else f"{C.ART_E2}/e2_t2_window.parquet"
    out.to_parquet(out_path, index=False)

    n_censored = int(out["censored"].sum())
    summary = {
        "task": "E2-T2 window build" + (" (DEV TIER)" if args.dev_n else ""),
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_events_processed": len(out),
        "n_events_skipped_no_baseline": int(len(frame) - len(events)) if not args.dev_n else None,
        "n_censored": n_censored,
        "censored_share": n_censored / len(out) if len(out) else None,
        "duration_min_summary": (
            {"n": int(out["duration_min"].notna().sum()),
             "median": float(out["duration_min"].median()) if out["duration_min"].notna().any() else None,
             "p25": float(out["duration_min"].quantile(0.25)) if out["duration_min"].notna().any() else None,
             "p75": float(out["duration_min"].quantile(0.75)) if out["duration_min"].notna().any() else None}
        ),
    }
    out_summary_path = (f"{C.ART_E2}/e2_t2_window_dev_summary.json" if args.dev_n
                         else f"{C.ART_E2}/e2_t2_window_summary.json")
    C.write_json(out_summary_path, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
