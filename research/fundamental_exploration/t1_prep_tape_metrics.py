"""
E1-T1 prep: tape-side event characteristics -- event volume (shares, notional), print
count at t0, median inter-trade interval, and t0's own session bucket.

DuckDB SQL over pandas throughout (CLAUDE.md: never materialize filtered_trades' 4.9B
rows into a dataframe). One bulk join: the events frame is registered and DuckDB
hash-joins it against filtered_trades in a single scan -- not a per-event point query
loop, per phase/13's own T1 lesson.

**Revision, 2026-09-15, after a first attempt failed.** 20,951 of the ~24,726 total
event-folders on disk are in-scope -- this join matches ~85% of filtered_trades' 4.9B
rows, not a small slice. The first version ran one query computing session aggregates
AND the median-inter-trade-interval window function (LAG OVER PARTITION BY event_id
ORDER BY sip_timestamp) together; it ran 141.5 minutes and then hit DuckDB's OOM
(memory_limit 25GB = 80% of this machine's 32GB, DuckDB's own default -- not something
this repo configures) inside the window operator's per-partition sort. The plain
aggregates (COUNT/SUM, bounded state = 20,951 groups) were never the problem -- split
out here into their own single-pass query, run once over the full table. The
window-function query is the one that needs a sort per partition (some events run to
hundreds of thousands of RTH trades) and is now batched by event year (6 batches
instead of 1), each written to its own checkpoint parquet immediately, with
SET threads=4 / SET preserve_insertion_order=false to bound per-thread sort-buffer
memory -- both DuckDB's own suggested mitigations for this exact OOM message. A crash
partway through now loses at most one year's batch, not the whole run.

Declared window (config.tape_side.event_volume_window): the regular session
(09:30-16:00 America/New_York, XNYS calendar) of the event's own event_date_canonical.
RTH bounds computed per-event in Python via pandas.Timestamp(tz=...).value (nanosecond
epoch), matching research/fundamentals_f1/t6_prep_context.py's own idiom.

"Print count at t0": trades within the same 60-second UTC-epoch-ns bucket as t0_ns,
regardless of session -- timezone-invariant to floor (America/New_York's UTC offset is
always a whole number of hours).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t1_prep_tape_metrics.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

RTH_OPEN, RTH_CLOSE = "09:30:00", "16:00:00"
MINUTE_NS = 60_000_000_000
OUT_PATH = f"{C.ART}/tape_metrics.parquet"
GAP_CHECKPOINT_DIR = f"{C.ART}/_t1_gap_checkpoints"


def rth_bounds(event_date: str) -> tuple[int, int]:
    lo = pd.Timestamp(f"{event_date} {RTH_OPEN}", tz="America/New_York").value
    hi = pd.Timestamp(f"{event_date} {RTH_CLOSE}", tz="America/New_York").value
    return lo, hi


def build_events() -> pd.DataFrame:
    joined = pd.read_parquet(f"{C.ART}/e1_joined.parquet", columns=["event_id", "ticker", "t0_ns"])
    event_id_re = re.compile(r"_(\d{4}-\d{2}-\d{2})_(-?\d+\.\d{2})$")
    parsed = joined["event_id"].apply(lambda eid: event_id_re.search(eid).groups())
    joined["event_date"] = parsed.apply(lambda p: p[0])
    joined["momentum_pct"] = parsed.apply(lambda p: float(p[1]))
    joined["year"] = joined["event_date"].str[:4]

    bounds = joined["event_date"].apply(rth_bounds)
    joined["rth_lo_ns"] = bounds.apply(lambda b: b[0])
    joined["rth_hi_ns"] = bounds.apply(lambda b: b[1])
    joined["t0_min_lo_ns"] = (joined["t0_ns"] // MINUTE_NS) * MINUTE_NS
    joined["t0_min_hi_ns"] = joined["t0_min_lo_ns"] + MINUTE_NS
    joined["t0_session"] = np.select(
        [joined["t0_ns"] < joined["rth_lo_ns"], joined["t0_ns"] >= joined["rth_hi_ns"]],
        ["pre_market", "after_hours"], default="regular",
    )
    return joined


def run_cheap_aggregates(con, events: pd.DataFrame) -> pd.DataFrame:
    """Single pass, no window function: session volume/print-count and t0-minute
    print-count. Bounded aggregation state (20,951 groups) -- this was never the part
    that ran out of memory."""
    con.register("events", events)

    session_sql = """
        SELECT e.event_id, COUNT(*) AS print_count_session,
               SUM(t.size) AS volume_shares, SUM(t.price * t.size) AS volume_notional
        FROM events e
        JOIN filtered_trades t
          ON t.ticker = e.ticker AND t.event_date = e.event_date AND t.momentum_pct = e.momentum_pct
        WHERE t.sip_timestamp >= e.rth_lo_ns AND t.sip_timestamp < e.rth_hi_ns
        GROUP BY e.event_id
    """
    session_df = con.execute(session_sql).df()

    t0_sql = """
        SELECT e.event_id, COUNT(*) AS print_count_at_t0
        FROM events e
        JOIN filtered_trades t
          ON t.ticker = e.ticker AND t.event_date = e.event_date AND t.momentum_pct = e.momentum_pct
        WHERE t.sip_timestamp >= e.t0_min_lo_ns AND t.sip_timestamp < e.t0_min_hi_ns
        GROUP BY e.event_id
    """
    t0_df = con.execute(t0_sql).df()

    out = events[["event_id"]].merge(session_df, on="event_id", how="left")
    out = out.merge(t0_df, on="event_id", how="left")
    for col in ["print_count_session", "volume_shares", "volume_notional", "print_count_at_t0"]:
        out[col] = out[col].fillna(0)
    return out


GAP_SQL = """
    WITH rth AS (
        SELECT e.event_id, t.sip_timestamp
        FROM batch_events e
        JOIN filtered_trades t
          ON t.ticker = e.ticker AND t.event_date = e.event_date AND t.momentum_pct = e.momentum_pct
        WHERE t.sip_timestamp >= e.rth_lo_ns AND t.sip_timestamp < e.rth_hi_ns
    ),
    gaps AS (
        SELECT event_id,
               sip_timestamp - LAG(sip_timestamp) OVER (PARTITION BY event_id ORDER BY sip_timestamp) AS gap_ns
        FROM rth
    )
    SELECT event_id, MEDIAN(gap_ns) AS median_intertrade_ns
    FROM gaps WHERE gap_ns IS NOT NULL GROUP BY event_id
"""


def run_gap_batch(batch_events: pd.DataFrame, label: str) -> pd.DataFrame:
    """One isolated connection per batch -- a prior run OOM'd on the 6th (largest,
    2025) year batch despite 5 smaller years succeeding on a shared connection;
    reusing one DuckDB connection across many execute() calls appears to accumulate
    state (query plan cache / relation objects) across iterations. A fresh connection
    per batch guarantees no such carryover, at the cost of DB-open overhead (cheap
    relative to the query itself)."""
    con = C.connect(read_only=True)
    con.execute("SET threads=4")
    con.execute("SET preserve_insertion_order=false")
    con.register("batch_events", batch_events)
    print(f"  {label}: {len(batch_events):,} events, running median-gap query...")
    result = con.execute(GAP_SQL).df()
    con.close()
    return result


def run_gap_medians_batched(events: pd.DataFrame) -> pd.DataFrame:
    """The window-function part (LAG needs a per-partition sort), batched by event
    year and checkpointed to disk per batch -- see module docstring for why. A batch
    that still OOMs on a fresh connection is halved by a stable ticker-hash split and
    retried (recursively, if needed) rather than failing the whole run."""
    os.makedirs(GAP_CHECKPOINT_DIR, exist_ok=True)

    years = sorted(events["year"].unique())
    results = []
    for year in years:
        ckpt_path = f"{GAP_CHECKPOINT_DIR}/{year}.parquet"
        if os.path.exists(ckpt_path):
            print(f"  year {year}: checkpoint already exists, skipping")
            results.append(pd.read_parquet(ckpt_path))
            continue

        year_events = events[events["year"] == year][
            ["event_id", "ticker", "event_date", "momentum_pct", "rth_lo_ns", "rth_hi_ns"]
        ]
        year_result = run_batch_with_fallback(year_events, f"year {year}")
        year_result.to_parquet(ckpt_path, index=False)
        print(f"  year {year}: done, {len(year_result):,} events with a defined median gap")
        results.append(year_result)

    return pd.concat(results, ignore_index=True)


def run_batch_with_fallback(batch_events: pd.DataFrame, label: str, depth: int = 0) -> pd.DataFrame:
    try:
        return run_gap_batch(batch_events, label)
    except Exception as e:
        if depth >= 3 or len(batch_events) < 200:
            raise
        print(f"  {label}: failed ({e.__class__.__name__}: {e}); splitting in half and retrying")
        split_key = pd.util.hash_pandas_object(batch_events["ticker"], index=False) % 2
        half_a = run_batch_with_fallback(batch_events[split_key == 0], f"{label}.a", depth + 1)
        half_b = run_batch_with_fallback(batch_events[split_key == 1], f"{label}.b", depth + 1)
        return pd.concat([half_a, half_b], ignore_index=True)


AGG_CHECKPOINT_PATH = f"{C.ART}/_t1_agg_checkpoint.parquet"


def main() -> int:
    events = build_events()

    if os.path.exists(AGG_CHECKPOINT_PATH):
        print("cheap aggregates: checkpoint already exists, skipping")
        agg_df = pd.read_parquet(AGG_CHECKPOINT_PATH)
    else:
        print("running cheap aggregates (single pass, no window function)...")
        con = C.connect(read_only=True)
        agg_df = run_cheap_aggregates(con, events)
        con.close()
        agg_df.to_parquet(AGG_CHECKPOINT_PATH, index=False)

    print("running median-inter-trade-interval, batched by year...")
    gap_df = run_gap_medians_batched(events)

    out = events[["event_id", "t0_session"]].merge(agg_df, on="event_id", how="left")
    out = out.merge(gap_df, on="event_id", how="left")

    out.to_parquet(OUT_PATH, index=False)

    summary = {
        "task": "E1-T1 prep: tape-side metrics",
        "rows": len(out),
        "n_zero_session_prints": int((out["print_count_session"] == 0).sum()),
        "n_zero_t0_prints": int((out["print_count_at_t0"] == 0).sum()),
        "n_null_median_intertrade": int(out["median_intertrade_ns"].isna().sum()),
        "t0_session_counts": out["t0_session"].value_counts().to_dict(),
        "config_hash": C.cfg_hash(),
    }
    C.write_json(f"{C.ART}/t1_prep_tape_metrics_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
