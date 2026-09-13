"""
Build F1, F1-PF5: assemble t0_spine.parquet per D33's tiered t0 construction.

No spine or view column is named t0, and no single existing detection artifact covers the
20,951-event in-scope universe at one precision (docs/Universe-Decisions.md D33). This script
builds the tiered fallback, finest anchor available first:

  1. nanosecond_poll1     -- det_ns_poll1 from results/phase_10/artifacts/v2_r13_detection.parquet,
     threshold=1.3 (matching config/phase_10_v4.json's own pin for this artifact -- not re-decided
     here). 114 events carry a threshold=1.3 row; 4 are never_crosses=True (the price never
     reaches 1.3x the T-1 RTH close, so there is no crossing to timestamp) and correctly fall
     through to tier 2/3 below. 110 events get a genuine nanosecond anchor.

  2. minute_a102          -- a102_detection_anchors.parquet's det_minute (session_offset=0),
     resolved back to its SOURCE bar's first_trade_ts in event_minute_bars_v2, rather than
     reconstructing wall-clock time from the minute-index grid independently via a session
     calendar. event_minute_bars_v2 already carries the exact nanosecond timestamp for that bar
     (it is the table a102_detection.py itself joined to produce det_minute), so re-deriving it
     through calendar arithmetic would only add DST/early-close risk for no benefit. a102 has
     15,763 rows total, but only 15,369 carry det_undefined=False (a defined det_minute) -- the
     other 394 never crossed the threshold in a102's own scan, the same defect class as tier 1's
     4 never_crosses rows, just at a larger scale. 15,369 matches Universe-Decisions.md D15's own,
     independently recorded "detection-universe" population exactly. Of those 15,369, 110 are
     already claimed by tier 1 (a subset relationship, confirmed by 110 + 15,259 = 15,369 in the
     actual run), leaving 15,259 for this tier to fill.

  3. first_trade_fallback -- for every event neither tier above reaches (confirmed 5,582 in the
     actual run), the first regular-session (09:30-16:00 ET) trade of event_date_canonical, read
     directly from that event's own data/filtered/{TICKER}_{DATE}_{MOM:.2f}/trades.parquet
     (+ any *_repair_1c.parquet sibling), per the established per-event read pattern
     (research/phase_10/common.py) -- NOT a scan of the 4.9B-row filtered_trades table, which the
     standing DuckDB-over-pandas rule reserves for aggregate work, not a per-event targeted read
     this small.

  unavailable             -- no folder, or no RTH print, for that event. Confirmed zero in the
     actual run: every one of the 20,951 in-scope events resolves at some tier.

Confirmed tier counts (results/fundamentals_f1/artifacts/t0_assemble_summary.json):
nanosecond_poll1=110, minute_a102=15,259, first_trade_fallback=5,582, unavailable=0. Sum=20,951.

**Path-resolution bug, caught 2026-09-12 while writing F1-T6's context prep script, fixed
here retroactively:** FILTERED_ROOT was a cwd-relative literal ("data/filtered"), not routed
through src/data/paths.py's resolve_data_root() the way CLAUDE.md's data-root convention
requires. This build runs inside a git worktree (E:\Trading-Research-f1) that has no
data/filtered/ of its own -- /data/ is wholly gitignored and a worktree gets its own empty
working directory for anything git doesn't track. The relative path happened to resolve
correctly on the original 2026-09-11 run only because the process's cwd was the main
checkout at that moment; it would silently return zero fallback events (first_trade_fallback_one
returns None on a missing folder, not an error) if re-run with cwd set to the worktree.
Fixed to `str(C.data_root() / "filtered")`, which resolves correctly regardless of cwd or
which worktree the process runs in. Re-ran after the fix: identical 5,582 fallback events,
confirming the original count was correct, not an artifact of the fragile path.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t0_assemble.py
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

OUT_PATH = f"{C.ART}/t0_spine.parquet"
SUMMARY_PATH = f"{C.ART}/t0_assemble_summary.json"
THRESHOLD = 1.3  # config/fundamentals_f1.json: t0_spine.tiers.1_nanosecond_poll1.threshold

FILTERED_ROOT = str(C.data_root() / "filtered")
RTH_OPEN = "09:30:00"
RTH_CLOSE = "16:00:00"


def load_universe() -> pd.DataFrame:
    df = pd.read_parquet(
        C.UNIVERSE_MATERIALIZATION_PATH, columns=["ticker", "event_date_canonical", "momentum_pct"]
    )
    df["event_date_canonical"] = df["event_date_canonical"].astype(str)
    df["mp"] = df["momentum_pct"].round(2)
    assert len(df) == C.TARGET_ROW_COUNT, (
        f"universe materialization has {len(df)} rows, expected {C.TARGET_ROW_COUNT}"
    )
    assert not df.duplicated(subset=["ticker", "event_date_canonical", "mp"]).any()
    return df[["ticker", "event_date_canonical", "mp"]]


def load_nanosecond_tier() -> pd.DataFrame:
    df = pd.read_parquet(
        C.NANOSECOND_ANCHOR_PATH,
        columns=["ticker", "event_date_canonical", "momentum_pct", "threshold", "det_ns_poll1"],
    )
    df = df[np.isclose(df["threshold"], THRESHOLD)].copy()
    df["event_date_canonical"] = df["event_date_canonical"].astype(str)
    df["mp"] = df["momentum_pct"].round(2)
    df = df.dropna(subset=["det_ns_poll1"])
    # det_ns_poll1 is stored float64. At ~1.6e18 ns (2020-2024 epoch nanoseconds), float64's
    # 52-bit mantissa cannot represent every integer exactly -- round to nearest rather than
    # truncate, the least-biased cast available; sub-microsecond drift here does not matter for
    # this build's purpose (filing proximity, share-count lag), only for the retracted
    # sub-second research line this anchor was originally built for.
    df["t0_ns"] = df["det_ns_poll1"].round().astype("int64")
    df["t0_source"] = "nanosecond_poll1"
    out = df[["ticker", "event_date_canonical", "mp", "t0_ns", "t0_source"]]
    out = out.drop_duplicates(subset=["ticker", "event_date_canonical", "mp"])
    # 114 rows carry a threshold=1.3 entry in the source file; 4 are never_crosses=True (the
    # price never reaches 1.3x the T-1 RTH close, so no crossing timestamp exists to record --
    # confirmed directly against the source file, not assumed). 110 have a genuine nanosecond
    # anchor. The 4 never_crosses events fall through to tier 2/3 below, exactly as intended.
    assert len(out) == 110, f"expected 110 nanosecond_poll1 events (114 rows minus 4 never_crosses), got {len(out)}"
    return out


def load_minute_tier(con) -> pd.DataFrame:
    a102 = pd.read_parquet(
        C.MINUTE_ANCHOR_PATH, columns=["ticker", "event_date_canonical", "mp", "det_minute", "det_undefined"]
    )
    a102 = a102[~a102["det_undefined"]].copy()
    a102["event_date_canonical"] = a102["event_date_canonical"].astype(str)
    a102["mp"] = a102["mp"].round(2)

    con.register("a102_det", a102)
    out = con.execute("""
        SELECT a.ticker, a.event_date_canonical, a.mp,
               b.first_trade_ts AS t0_ns,
               'minute_a102' AS t0_source
        FROM a102_det a
        JOIN event_minute_bars_v2 b
          ON a.ticker = b.ticker
         AND a.event_date_canonical = b.event_date_canonical
         AND ROUND(b.momentum_pct, 2) = a.mp
         AND b.session_offset = 0
         AND b.minute_index = a.det_minute
    """).fetchdf()
    con.unregister("a102_det")
    out = out.drop_duplicates(subset=["ticker", "event_date_canonical", "mp"])
    return out


def _event_folder(ticker: str, event_date: str, mp: float) -> str:
    return os.path.join(FILTERED_ROOT, f"{ticker}_{event_date}_{mp:.2f}")


def _trade_files(ticker: str, event_date: str, mp: float) -> list[str]:
    """Base trades.parquet plus every *_repair_1c.parquet sibling (CLAUDE.md repair provenance)."""
    folder = _event_folder(ticker, event_date, mp)
    if not os.path.isdir(folder):
        return []
    out = []
    base = os.path.join(folder, "trades.parquet")
    if os.path.exists(base):
        out.append(base)
    out.extend(sorted(glob.glob(os.path.join(folder, "trades*_repair_1c.parquet"))))
    return out


def first_trade_fallback_one(ticker: str, event_date: str, mp: float) -> int | None:
    files = _trade_files(ticker, event_date, mp)
    if not files:
        return None
    frames = [pd.read_parquet(f, columns=["sip_timestamp"]) for f in files]
    ts = pd.concat(frames, ignore_index=True)["sip_timestamp"] if len(frames) > 1 else frames[0]["sip_timestamp"]
    lo = pd.Timestamp(f"{event_date} {RTH_OPEN}", tz="America/New_York").value
    hi = pd.Timestamp(f"{event_date} {RTH_CLOSE}", tz="America/New_York").value
    in_rth = ts[(ts >= lo) & (ts < hi)]
    if in_rth.empty:
        return None
    return int(in_rth.min())


def load_fallback_tier(remaining: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in remaining.itertuples(index=False):
        t0 = first_trade_fallback_one(r.ticker, r.event_date_canonical, r.mp)
        if t0 is not None:
            rows.append((r.ticker, r.event_date_canonical, r.mp, t0, "first_trade_fallback"))
    return pd.DataFrame(rows, columns=["ticker", "event_date_canonical", "mp", "t0_ns", "t0_source"])


def main():
    key = ["ticker", "event_date_canonical", "mp"]
    universe = load_universe()
    nanosecond = load_nanosecond_tier()

    con = C.connect(read_only=True)
    minute = load_minute_tier(con)
    con.close()

    spine = universe.merge(nanosecond, on=key, how="left")

    missing = spine["t0_ns"].isna()
    spine = spine.merge(minute, on=key, how="left", suffixes=("", "_m"))
    fill = missing & spine["t0_ns_m"].notna()
    spine.loc[fill, ["t0_ns", "t0_source"]] = spine.loc[fill, ["t0_ns_m", "t0_source_m"]].values
    spine = spine.drop(columns=["t0_ns_m", "t0_source_m"])

    still_missing = spine[spine["t0_ns"].isna()][key]
    print(f"resolving first_trade_fallback for {len(still_missing)} events "
          f"(per-event file reads, not a filtered_trades scan)...")
    fallback = load_fallback_tier(still_missing)

    spine = spine.merge(fallback, on=key, how="left", suffixes=("", "_f"))
    missing2 = spine["t0_ns"].isna()
    fill2 = missing2 & spine["t0_ns_f"].notna()
    spine.loc[fill2, ["t0_ns", "t0_source"]] = spine.loc[fill2, ["t0_ns_f", "t0_source_f"]].values
    spine = spine.drop(columns=["t0_ns_f", "t0_source_f"])

    spine["t0_source"] = spine["t0_source"].fillna("unavailable")
    spine["t0_ns"] = spine["t0_ns"].astype("Int64")  # nullable -- 'unavailable' rows stay NULL

    spine["event_id"] = [
        C.event_id({"ticker": t, "event_date_canonical": d, "momentum_pct": m})
        for t, d, m in zip(spine["ticker"], spine["event_date_canonical"], spine["mp"])
    ]
    spine = spine.rename(columns={"mp": "momentum_pct"})
    spine = spine[["event_id", "ticker", "event_date_canonical", "momentum_pct", "t0_ns", "t0_source"]]

    assert len(spine) == C.TARGET_ROW_COUNT, len(spine)
    assert spine["event_id"].is_unique

    tier_counts = spine["t0_source"].value_counts().to_dict()
    assert tier_counts.get("nanosecond_poll1", 0) == 110, tier_counts
    assert sum(tier_counts.values()) == C.TARGET_ROW_COUNT

    os.makedirs(C.ART, exist_ok=True)
    spine.to_parquet(OUT_PATH, index=False)

    summary = {
        "rows": len(spine),
        "tier_counts": {str(k): int(v) for k, v in tier_counts.items()},
        "config_hash": C.cfg_hash(),
        "nanosecond_threshold": THRESHOLD,
    }
    C.write_json(SUMMARY_PATH, summary)
    print(summary)


if __name__ == "__main__":
    main()
