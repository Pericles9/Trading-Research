"""
Build F1, F1-T6 prep: per-event detection price (for the price-decile cross-cut) and
per-company exchange/delisted status (for the exchange/delisted cross-cuts), neither of
which exists as a single ready-made column anywhere in this build. Offline, no network call.

**Detection price is tick-derived, not a spine numeric -- not D4-restricted.** D4 quarantines
`momentum_events_canonical`'s own OHLC/volume columns; the price used here is the actual
traded price at the t0 anchor, read from the same tick sources t0_assemble.py already used
to derive t0_ns itself (v2_r13_detection's `cross_price` for the nanosecond_poll1 tier,
a102_detection_anchors' `det_price_lat0` for minute_a102, and a direct re-read of each
first_trade_fallback event's own trades.parquet for the rest -- t0_assemble.py only kept the
timestamp from that read, not the price, so this script re-reads those 5,582 files). Used
here only to bucket events into deciles for a coverage cross-cut (F1-T6a) -- never stored in
`event_fundamentals`, never related to a market outcome (D32).

Exchange/delisted status: reused from F1-T2's already-pulled `ticker_details` archive
(`active`, `primary_exchange`), not a fresh API call -- distinct from the universe
CS/ADRC classification CLAUDE.md pins to `ticker_reference_snapshot.parquet` (a different
question: this is a coverage-report diagnostic, not universe membership).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t6_prep_context.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

FILTERED_ROOT = str(C.data_root() / "filtered")  # resolve_data_root()-based, not cwd-relative --
# see t0_assemble.py's docstring for why a bare "data/filtered" literal is wrong in a worktree
RTH_OPEN, RTH_CLOSE = "09:30:00", "16:00:00"
TICKER_DETAILS_ROOT = "data/raw/fundamentals/massive/2026-09-12/ticker_details"
OUT_PATH = f"{C.ART}/t6_context.parquet"


def _event_folder(ticker: str, event_date: str, mp: float) -> str:
    return os.path.join(FILTERED_ROOT, f"{ticker}_{event_date}_{mp:.2f}")


def first_trade_price(ticker: str, event_date: str, mp: float) -> float | None:
    folder = _event_folder(ticker, event_date, mp)
    files = [os.path.join(folder, "trades.parquet")] if os.path.exists(os.path.join(folder, "trades.parquet")) else []
    files += sorted(glob.glob(os.path.join(folder, "trades*_repair_1c.parquet")))
    if not files:
        return None
    frames = [pd.read_parquet(f, columns=["sip_timestamp", "price"]) for f in files]
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    lo = pd.Timestamp(f"{event_date} {RTH_OPEN}", tz="America/New_York").value
    hi = pd.Timestamp(f"{event_date} {RTH_CLOSE}", tz="America/New_York").value
    in_rth = df[(df["sip_timestamp"] >= lo) & (df["sip_timestamp"] < hi)]
    if in_rth.empty:
        return None
    return float(in_rth.loc[in_rth["sip_timestamp"].idxmin(), "price"])


def main():
    t0_spine = pd.read_parquet(f"{C.ART}/t0_spine.parquet")
    identity = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")[["event_id", "cik"]]
    base = t0_spine.merge(identity, on="event_id", how="left")

    # nanosecond_poll1: cross_price from v2_r13_detection.parquet, threshold 1.3
    v2 = pd.read_parquet(C.NANOSECOND_ANCHOR_PATH)
    v2 = v2[v2["threshold"] == 1.3][["ticker", "event_date_canonical", "momentum_pct", "cross_price"]]
    v2 = v2.rename(columns={"momentum_pct": "mp", "cross_price": "detection_price"})

    # minute_a102: det_price_lat0 from a102_detection_anchors.parquet
    a102 = pd.read_parquet(C.MINUTE_ANCHOR_PATH)
    a102 = a102[["ticker", "event_date_canonical", "mp", "det_price_lat0"]].rename(
        columns={"det_price_lat0": "detection_price"}
    )
    # both source artifacts carry event_date_canonical as datetime64, unlike t0_spine's plain
    # date string -- normalize before merging (same class of dtype mismatch t0_assemble.py's
    # verification script hit against quotes_bitmaps_all.parquet, caught 2026-09-12).
    for _df in (v2, a102):
        if pd.api.types.is_datetime64_any_dtype(_df["event_date_canonical"]):
            _df["event_date_canonical"] = _df["event_date_canonical"].dt.strftime("%Y-%m-%d")

    base["mp"] = base["momentum_pct"]
    ns_tier = base[base["t0_source"] == "nanosecond_poll1"].merge(
        v2, on=["ticker", "event_date_canonical", "mp"], how="left"
    )[["event_id", "detection_price"]]
    min_tier = base[base["t0_source"] == "minute_a102"].merge(
        a102, on=["ticker", "event_date_canonical", "mp"], how="left"
    )[["event_id", "detection_price"]]

    fallback = base[base["t0_source"] == "first_trade_fallback"]
    print(f"re-reading trades.parquet for {len(fallback)} first_trade_fallback events (detection price)")
    prices = []
    for i, r in enumerate(fallback.itertuples(index=False)):
        p = first_trade_price(r.ticker, r.event_date_canonical, r.mp)
        prices.append(p)
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(fallback)}")
    fb_tier = pd.DataFrame({"event_id": fallback["event_id"].values, "detection_price": prices})

    price = pd.concat([ns_tier, min_tier, fb_tier], ignore_index=True)
    base = base.merge(price, on="event_id", how="left")
    n_missing_price = int(base["detection_price"].isna().sum())
    base["detection_price_decile"] = pd.qcut(base["detection_price"], 10, labels=False, duplicates="drop")

    # exchange / delisted status from F1-T2's ticker_details archive
    rows = []
    for path in glob.glob(f"{TICKER_DETAILS_ROOT}/*.json"):
        cik = os.path.basename(path).replace(".json", "")
        with open(path) as f:
            records = json.load(f)
        if records:
            r = records[0]
            rows.append({"cik": cik, "primary_exchange": r.get("primary_exchange"), "active": r.get("active")})
    td = pd.DataFrame(rows)
    base = base.merge(td, on="cik", how="left")
    base["delisted_status"] = base["active"].map({True: "active", False: "delisted"}).fillna("unknown")

    out = base[["event_id", "cik", "detection_price", "detection_price_decile",
                "primary_exchange", "delisted_status"]]
    out.to_parquet(OUT_PATH, index=False)

    summary = {
        "rows": len(out),
        "n_missing_detection_price": n_missing_price,
        "n_missing_exchange_info": int(out["primary_exchange"].isna().sum()),
        "delisted_status_counts": out["delisted_status"].value_counts().to_dict(),
        "config_hash": C.cfg_hash(),
    }
    C.write_json(f"{C.ART}/t6_context_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
