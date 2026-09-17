"""
E1 support: reconstruct F1-T6's detection_price / detection_price_decile locally.

results/fundamentals_f1/artifacts/t6_context.parquet is a gitignored, regenerable F1
intermediate (results/fundamentals_f1/artifacts/*.parquet, per .gitignore) that is not
present on this checkout. Its own upstream inputs (t0_spine.parquet, ticker_identity.parquet)
are gitignored too and would require re-running most of Build F1's pipeline to reproduce.

Not needed: event_fundamentals.parquet already carries ticker/t0_ns/t0_source directly (the
one thing t0_spine.parquet would have supplied), and event_date_canonical/momentum_pct are
recoverable exactly from event_id's own format (ticker_YYYY-MM-DD_MP, D30's identity key).
This script reproduces only the two columns E1 actually needs (detection_price,
detection_price_decile), reusing research/fundamentals_f1/t6_prep_context.py's own
first_trade_price() function verbatim for the first_trade_fallback tier (reuse-before-build/
D30) rather than re-deriving that tick-level read.

Output is E1's own cache (results/fundamental_exploration/artifacts/detection_price.parquet),
not a rewrite of F1's t6_context.parquet -- if a future checkout regenerates the real F1
artifact, research/fundamental_exploration/common.py's load_detection_price() prefers it.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t0b_detection_price.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402
from research.fundamentals_f1.t6_prep_context import first_trade_price  # noqa: E402

NANOSECOND_ANCHOR_PATH = "results/phase_10/artifacts/v2_r13_detection.parquet"
MINUTE_ANCHOR_PATH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
OUT_PATH = f"{C.ART}/detection_price.parquet"

EVENT_ID_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_(-?\d+\.\d{2})$")


def parse_event_id(event_id: str) -> tuple[str, float]:
    m = EVENT_ID_RE.search(event_id)
    if not m:
        raise ValueError(f"event_id does not match expected format: {event_id}")
    return m.group(1), float(m.group(2))


def main() -> int:
    ef = C.load_event_fundamentals()[["event_id", "ticker", "t0_source"]].copy()
    parsed = ef["event_id"].apply(parse_event_id)
    ef["event_date_canonical"] = parsed.apply(lambda p: p[0])
    ef["mp"] = parsed.apply(lambda p: p[1])

    v2 = pd.read_parquet(NANOSECOND_ANCHOR_PATH)
    v2 = v2[v2["threshold"] == 1.3][["ticker", "event_date_canonical", "momentum_pct", "cross_price"]]
    v2 = v2.rename(columns={"momentum_pct": "mp", "cross_price": "detection_price"})
    if pd.api.types.is_datetime64_any_dtype(v2["event_date_canonical"]):
        v2["event_date_canonical"] = v2["event_date_canonical"].dt.strftime("%Y-%m-%d")

    a102 = pd.read_parquet(MINUTE_ANCHOR_PATH)
    a102 = a102[["ticker", "event_date_canonical", "mp", "det_price_lat0"]].rename(
        columns={"det_price_lat0": "detection_price"}
    )
    if pd.api.types.is_datetime64_any_dtype(a102["event_date_canonical"]):
        a102["event_date_canonical"] = a102["event_date_canonical"].dt.strftime("%Y-%m-%d")

    ns_tier = ef[ef["t0_source"] == "nanosecond_poll1"].merge(
        v2, on=["ticker", "event_date_canonical", "mp"], how="left"
    )[["event_id", "detection_price"]]
    min_tier = ef[ef["t0_source"] == "minute_a102"].merge(
        a102, on=["ticker", "event_date_canonical", "mp"], how="left"
    )[["event_id", "detection_price"]]

    fallback = ef[ef["t0_source"] == "first_trade_fallback"]
    print(f"re-reading trades.parquet for {len(fallback)} first_trade_fallback events (detection price)")
    prices = []
    for i, r in enumerate(fallback.itertuples(index=False)):
        prices.append(first_trade_price(r.ticker, r.event_date_canonical, r.mp))
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{len(fallback)}")
    fb_tier = pd.DataFrame({"event_id": fallback["event_id"].values, "detection_price": prices})

    price = pd.concat([ns_tier, min_tier, fb_tier], ignore_index=True)
    out = ef[["event_id"]].merge(price, on="event_id", how="left")
    n_missing = int(out["detection_price"].isna().sum())
    out["detection_price_decile"] = pd.qcut(out["detection_price"], 10, labels=False, duplicates="drop")
    out.to_parquet(OUT_PATH, index=False)

    summary = {
        "task": "E1-T0b detection price reconstruction (F1-T6 equivalent, local cache)",
        "rows": len(out), "n_missing_detection_price": n_missing,
        "config_hash": C.cfg_hash(),
    }
    C.write_json(f"{C.ART}/t0b_detection_price_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
