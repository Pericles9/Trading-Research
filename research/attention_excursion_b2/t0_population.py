"""
Brief 2, T0 -- freeze and population.

Asserts D1 = 15,763 (Phase 5a frame), tau available = 15,519 (Brief 1's t2_tau.parquet, not recomputed),
Brief 1's committed slices partition D1, and the dev sample (50) and sidecar (6) sit in dev_quarantine.
Builds the facet table every later task joins to: slice, year, the clock segment of tau (Amendment 3,
XNYS calendar), the cross-minute class, the R4 price tier, tau_close_sensitive, the A12 flag. Runs the
section 7 tests: the causality assertion (Brief 1's II.5 test, which also exercises the A2 segment
assertion) and the R3 competition-window assertion, each fed an input that must raise.

Writes artifacts/t0_population.parquet and artifacts/t0_population.json.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/t0_population.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402

C1, A = B.C1, B.A


def main() -> int:
    cfg = B.load_cfg()
    pop = cfg["brief2"]["population"]
    d1 = C1.load_d1()
    assert len(d1) == pop["d1_n"] == 15763, f"D1 = {len(d1)}"
    assert d1["event_id"].notna().all() and d1["event_id"].is_unique, "D1 event_id not resolved or not unique"

    t2 = pd.read_parquet(B.b1_art("t2_tau.parquet"))
    assert set(t2["event_id"]) == set(d1["event_id"]) and len(t2) == len(d1), "Brief 1 t2_tau does not cover D1 exactly"
    B.assert_int64(t2)
    n_tau = int(t2["tau_available"].sum())
    assert n_tau == pop["tau_available_n"] == 15519, f"tau available = {n_tau}"
    assert t2.loc[t2["tau_available"], "tau_ns"].notna().all()

    sl = pd.read_parquet(B.REPO / pop["slices"])
    assert set(sl["event_id"]) == set(d1["event_id"]) and sl["event_id"].is_unique, "slices do not partition D1"
    assert sl["slice"].isin(["development", "selection", "final", "dev_quarantine"]).all()
    q = sl[sl["slice"] == "dev_quarantine"]
    assert len(q) == 56 and (q["dev_group"] == "dev_v3").sum() == 50 and (q["dev_group"] == "dev_v4_sidecar").sum() == 6, \
        "dev_quarantine is not exactly the 50 dev + 6 sidecar events"
    assert sl.loc[sl["dev_group"].notna(), "slice"].eq("dev_quarantine").all(), "a dev or sidecar event sits in a slice"

    keep = ["event_id", "ticker", "event_date_canonical", "tau_available", "tau_reason", "tau_ns", "tau_price", "prior_close_exact",
            "prior_close_source", "tau_session_segment", "sec_from_0400", "sec_from_0930", "tau_close_sensitive",
            "flag_cross_session_extreme"]
    df = t2[keep].merge(sl[["event_id", "slice", "dev_group", "first_seen_slice", "is_first_seen_ticker"]], on="event_id", how="left")
    df["year"] = df["event_date_canonical"].str[:4].astype(int)
    bounds = {d: C1.rth_bounds_ns(d) for d in df["event_date_canonical"].unique()}
    seg = []
    for t, d, ok in zip(df["tau_ns"], df["event_date_canonical"], df["tau_available"]):
        seg.append(C1.clock_segment(int(t), *bounds[d]) if ok else None)
    df["tau_anchor_segment"] = seg
    df["tau_in_auction_minute"] = df["tau_anchor_segment"].isin(C1.AUCTION).where(df["tau_available"]).astype("boolean")
    df["early_close_day"] = [(bounds[d][1] - bounds[d][0]) < 390 * B.MIN_NS for d in df["event_date_canonical"]]
    df["price_tier"] = B.price_tier(df["tau_price"].to_numpy(), cfg)
    df["tau_ns"] = df["tau_ns"].astype("Int64")
    B.assert_int64(df)
    df["config_hash"] = B.cfg_hash()
    df.to_parquet(B.art("t0_population.parquet"), index=False)

    ctest = A.causality_test(C1.scale_field().field_exact)
    wtest = B.window_test()
    assert ctest["passes"], f"causality / A2 segment test failed: {ctest}"
    assert wtest["passes"], f"competition-window test failed: {wtest}"
    ta = df[df["tau_available"]]
    out = {
        "config_hash": B.cfg_hash(),
        "d1_n": int(len(d1)), "tau_available": n_tau, "tau_unavailable_reasons": t2.loc[~t2["tau_available"], "tau_reason"].value_counts().to_dict(),
        "slices": sl["slice"].value_counts().to_dict(),
        "slices_with_tau": ta["slice"].value_counts().to_dict(),
        "dev_quarantine": {"dev_v3": 50, "dev_v4_sidecar": 6},
        "years_with_tau": ta["year"].value_counts().sort_index().to_dict(),
        "tau_anchor_segment": ta["tau_anchor_segment"].value_counts().to_dict(),
        "tau_in_auction_minute": int(ta["tau_in_auction_minute"].sum()),
        "early_close_events_with_tau": int(ta["early_close_day"].sum()),
        "price_tier_with_tau": ta["price_tier"].value_counts().to_dict(),
        "tau_close_sensitive": ta["tau_close_sensitive"].astype("string").fillna("NULL").value_counts().to_dict(),
        "flag_cross_session_extreme": ta["flag_cross_session_extreme"].astype("string").fillna("missing").value_counts().to_dict(),
        "dates_with_tau": int(ta["event_date_canonical"].nunique()),
        "II5_causality_and_a2_segment_test": ctest,
        "II5_competition_window_test": wtest,
        "assertions_passed": ["D1 = 15,763, event_id resolved and unique", "t2_tau covers D1 exactly; tau_ns int64",
                              "tau available = 15,519", "slices partition D1", "dev_quarantine = 50 dev + 6 sidecar, none elsewhere",
                              "causality test raises on every attention function", "A2 segment test raises",
                              "competition-window test raises on a straddling window"],
    }
    B.write_json("t0_population.json", out)
    print({k: out[k] for k in ("d1_n", "tau_available", "slices", "tau_anchor_segment", "tau_in_auction_minute", "price_tier_with_tau")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
