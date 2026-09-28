"""
Brief 1, T0a + T0b -- population, dev sample, slice membership. Written, not read: nothing here
touches a price or an outcome.

T0a  D1 asserted at 15,763 against Phase 5a's sampling frame; the 50 dev events and the 6 sidecar
     events asserted inside D1 and disjoint.
T0b  results/attention_excursion/b1/slices.parquet -- one row per D1 event, slice by
     event_date_canonical (D38), dev + sidecar -> dev_quarantine regardless of date, with
     first_seen_slice and is_first_seen_ticker.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t0_population.py
"""
from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import common as C  # noqa: E402

ORDER = ["development", "selection", "final"]


def date_slice(d: str, cfg: dict) -> str:
    for s in ORDER:
        lo, hi = cfg["slices"][s]
        if lo <= d <= hi:
            return s
    return "outside"


def main() -> int:
    cfg = C.load_cfg()
    d1 = C.load_d1()

    # ---- T0a
    n = len(d1)
    assert n == cfg["population"]["d1_n_expected"], f"D1 = {n}, expected 15,763"
    assert (d1["source_file"] == "file1").all(), "non-file1 row in the D1 frame"
    assert not d1.duplicated(["ticker", "event_date_canonical"]).any(), "duplicate (ticker, date) in D1"
    assert d1["event_id"].notna().all(), f"{d1['event_id'].isna().sum()} D1 events have no folder"
    assert d1["event_id"].is_unique

    dev = C.load_dev()
    side = C.load_sidecar()
    assert len(dev) == cfg["population"]["dev_n_expected"]
    assert len(side) == cfg["population"]["sidecar_n_expected"]
    key = ["ticker", "event_date_canonical"]
    dev_in = dev.merge(d1[key], on=key, how="inner")
    side_in = side.merge(d1[key], on=key, how="inner")
    assert len(dev_in) == 50, f"{50 - len(dev_in)} dev events outside D1"
    assert len(side_in) == 6, f"{6 - len(side_in)} sidecar events outside D1"
    assert dev.merge(side, on=key).empty, "dev and sidecar overlap"

    # ---- T0b
    s = d1[["event_id", "ticker", "event_date_canonical"]].copy()
    s["date_slice"] = s["event_date_canonical"].map(lambda d: date_slice(d, cfg))
    assert (s["date_slice"] != "outside").all(), s[s["date_slice"] == "outside"].head()
    dev_k = set(map(tuple, dev[key].values))
    side_k = set(map(tuple, side[key].values))
    kk = list(zip(s["ticker"], s["event_date_canonical"]))
    s["dev_group"] = ["dev_v3" if k in dev_k else ("dev_v4_sidecar" if k in side_k else None) for k in kk]
    s["slice"] = s["date_slice"].where(s["dev_group"].isna(), "dev_quarantine")

    rank = {v: i for i, v in enumerate(ORDER)}
    first = s.assign(r=s["date_slice"].map(rank)).groupby("ticker")["r"].min().map(dict(enumerate(ORDER)))
    s["first_seen_slice"] = s["ticker"].map(first)
    s["is_first_seen_ticker"] = (s["slice"] == s["first_seen_slice"])

    # assertions: partition exact, quarantine exact
    assert len(s) == n and s["event_id"].is_unique
    assert s["slice"].isin(ORDER + ["dev_quarantine"]).all()
    assert (s.loc[s["dev_group"].notna(), "slice"] == "dev_quarantine").all()
    assert (s["slice"] == "dev_quarantine").sum() == 56
    assert not s.loc[s["slice"] == "dev_quarantine", "is_first_seen_ticker"].any()

    s = s[["event_id", "ticker", "event_date_canonical", "slice", "date_slice", "dev_group",
           "first_seen_slice", "is_first_seen_ticker"]]
    s.to_parquet(C.REPO / C.OUT / "slices.parquet", index=False)

    before = s["date_slice"].value_counts().reindex(ORDER).to_dict()
    after = s["slice"].value_counts().reindex(ORDER + ["dev_quarantine"]).to_dict()
    fs = s[s["slice"].isin(ORDER)].groupby("slice")["is_first_seen_ticker"].agg(["sum", "size"]).reindex(ORDER)
    q_by_date = s[s["slice"] == "dev_quarantine"].groupby(["date_slice", "dev_group"]).size().unstack(fill_value=0)
    summary = {
        "config_hash": C.cfg_hash(),
        "d1_n": n,
        "dev_n": 50, "sidecar_n": 6,
        "slice_counts_before_quarantine": before,
        "expected_before_quarantine_approx": cfg["slices"]["expected_before_quarantine_approx"],
        "slice_counts_after_quarantine": after,
        "first_seen_events_per_slice": {k: int(v) for k, v in fs["sum"].items()},
        "events_per_slice": {k: int(v) for k, v in fs["size"].items()},
        "first_seen_share": {k: round(float(a) / float(b), 4) for k, a, b in zip(fs.index, fs["sum"], fs["size"])},
        "distinct_tickers_per_slice": s[s["slice"].isin(ORDER)].groupby("slice")["ticker"].nunique().reindex(ORDER).to_dict(),
        "quarantine_by_date_slice": {str(i): {str(c): int(v) for c, v in r.items()} for i, r in q_by_date.iterrows()},
        "sidecar_events": side.assign(event_id=[s.set_index(["ticker", "event_date_canonical"]).loc[tuple(x), "event_id"] for x in side[key].values]).to_dict("records"),
        "assertions_passed": ["D1 = 15,763", "all source_file = file1", "(ticker, date) unique", "every D1 event resolves to one folder",
                              "50 dev + 6 sidecar all inside D1, disjoint", "slices partition D1 exactly",
                              "every dev/sidecar event in dev_quarantine, none elsewhere"],
    }
    C.write_json(f"{C.ART}/t0_population.json", summary)
    print(pd.Series(before), "\n", pd.Series(after), "\n", fs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
