"""
Brief 1, Amendment 3 -- the weight of the anchoring change, measured (A3.7 report additions). Reads
the Amendment 2 run's T5 artifacts (artifacts/run3/, 04:00-anchored) against the re-run's
(segment-anchored), and counts the cross-minute class on all of D1 from T2's tau. Reads no outcome.

  valid rungs per event, by clock segment of tau, before and after
  how many previously valid rungs straddled the open (window [tau - W_k, tau] meets [open, open + 60 s))
  -- and the close, the same way
  from_nothing rungs before and after; rung 0 from_nothing events before and after
  the cross-minute class on D1 and on the dev sample
  check: premarket crossers' ladders are unchanged (their anchor is 04:00 in both runs)

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t5_a3_before_after.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

RUN3 = "run3"


def main() -> int:
    b_ev = pd.read_parquet(C.art(f"{RUN3}/t5_attention.parquet"))
    b_rg = pd.read_parquet(C.art(f"{RUN3}/t5_a2_rungs.parquet"))
    a_ev = pd.read_parquet(C.art("t5_attention.parquet"))
    a_rg = pd.read_parquet(C.art("t5_a2_rungs.parquet"))
    keep = lambda d: d[(d["dev_group"] == "dev_v3") & (d["attention_available"] == True)]  # noqa: E731,E712
    b_ev, a_ev = keep(b_ev), keep(a_ev)
    assert set(b_ev["event_id"]) == set(a_ev["event_id"]), "the before and after runs cover different events"
    seg = a_ev.set_index("event_id")["tau_anchor_segment"]

    # ---------------------------------------------------------------- per event
    ev = a_ev[["event_id", "event_date_canonical", "tau_ns", "tau_anchor_segment", "tau_in_auction_minute", "a2_state",
               "H_s", "H_0400_s", "a2_valid_rungs", "a2_rungs_computed", "a2_invalid_from_nothing", "a2_rung0_from_nothing"]].merge(
        b_ev[["event_id", "a2_valid_rungs", "a2_rungs_computed", "a2_invalid_from_nothing", "a2_rung0_from_nothing"]]
        .rename(columns=lambda c: c if c == "event_id" else f"{c}_before"), on="event_id")
    ev = ev.rename(columns={"a2_valid_rungs": "a2_valid_rungs_after", "a2_rungs_computed": "a2_rungs_computed_after",
                            "a2_invalid_from_nothing": "a2_invalid_from_nothing_after", "a2_rung0_from_nothing": "a2_rung0_from_nothing_after"})

    # ---------------------------------------------------------------- the before windows, reconstructed exactly
    b_rg = b_rg[b_rg["dev_group"] == "dev_v3"].merge(b_ev[["event_id", "tau_ns"]], on="event_id")
    lo, op_, cl_ = [], [], []
    for r in b_rg.itertuples():
        tau = int(r.tau_ns)
        t0400 = C.et_ns(r.event_date_canonical, "04:00:00")
        W = (tau - t0400) / (2.0 ** int(r.k))                  # instruments.a2_count_ladder, runs 1-3
        o, c = C.rth_bounds_ns(r.event_date_canonical)
        lo.append(tau - int(round(W)))
        op_.append(o)
        cl_.append(c)
    b_rg["win_lo_ns"], b_rg["open_ns"], b_rg["close_ns"] = lo, op_, cl_
    b_rg["straddles_open"] = (b_rg["win_lo_ns"] < b_rg["open_ns"] + C.MIN_NS) & (b_rg["tau_ns"].astype("int64") >= b_rg["open_ns"])
    b_rg["straddles_close"] = (b_rg["win_lo_ns"] < b_rg["close_ns"] + C.MIN_NS) & (b_rg["tau_ns"].astype("int64") >= b_rg["close_ns"])
    b_rg["tau_anchor_segment"] = b_rg["event_id"].map(seg)
    b_rg[["event_id", "k", "valid", "class", "W_s", "win_lo_ns", "straddles_open", "straddles_close", "tau_anchor_segment"]].to_parquet(
        C.art("t5_a3_before_windows.parquet"), index=False)
    ev["valid_rungs_straddling_open_before"] = ev["event_id"].map(
        b_rg[b_rg["valid"] & b_rg["straddles_open"]].groupby("event_id").size()).fillna(0).astype(int)
    ev["config_hash"] = C.cfg_hash()
    ev.to_parquet(C.art("t5_a3_before_after_events.parquet"), index=False)

    a_rg = a_rg[a_rg["dev_group"] == "dev_v3"]
    by_seg = {}
    for sg, g in ev.groupby("tau_anchor_segment"):
        gv = g[g["a2_state"] == "value"]
        bv = b_rg[b_rg["tau_anchor_segment"] == sg]
        by_seg[sg] = {"events": int(len(g)),
                      "before": {"valid_rungs_median": float(g["a2_valid_rungs_before"].median()),
                                 "valid_rungs_total": int(g["a2_valid_rungs_before"].sum()),
                                 "zero_valid_events": int((g["a2_valid_rungs_before"] == 0).sum()),
                                 "rungs_computed_total": int(g["a2_rungs_computed_before"].sum()),
                                 "valid_rungs_straddling_open": int((bv["valid"] & bv["straddles_open"]).sum()),
                                 "valid_rungs_straddling_close": int((bv["valid"] & bv["straddles_close"]).sum()),
                                 "H_median_s": float(g["H_0400_s"].median())},
                      "after": {"events_with_a2": int(len(gv)),
                                "valid_rungs_median": float(gv["a2_valid_rungs_after"].median()) if len(gv) else None,
                                "valid_rungs_total": int(gv["a2_valid_rungs_after"].sum()) if len(gv) else 0,
                                "zero_valid_events": int((gv["a2_valid_rungs_after"] == 0).sum()),
                                "rungs_computed_total": int(gv["a2_rungs_computed_after"].sum()) if len(gv) else 0,
                                "H_median_s": float(gv["H_s"].median()) if len(gv) else None}}
    pm = ev[ev["tau_anchor_segment"] == "premarket"]
    pm_b = b_rg[b_rg["event_id"].isin(pm["event_id"])].sort_values(["event_id", "k"])[["event_id", "k", "n_recent", "n_older", "valid"]]
    pm_a = a_rg[a_rg["event_id"].isin(pm["event_id"])].sort_values(["event_id", "k"])[["event_id", "k", "n_recent", "n_older", "valid"]]
    premarket_identical = bool(len(pm_b) == len(pm_a) and (pm_b.reset_index(drop=True) == pm_a.reset_index(drop=True)).all().all())

    classes = lambda d: d["class"].value_counts().to_dict()  # noqa: E731
    bstr = b_rg[b_rg["valid"]]
    out = {
        "config_hash": C.cfg_hash(),
        "before": "artifacts/run3/ (Amendment 2 run, commit 99b7e51): every ladder anchored at 04:00",
        "after": "artifacts/ (Amendment 3): anchored at the start of tau's clock segment; cross-minute taus carry no A2",
        "events": int(len(ev)),
        "valid_rungs_by_segment": by_seg,
        "valid_rungs_all": {"before_total": int(ev["a2_valid_rungs_before"].sum()),
                            "after_total": int(ev["a2_valid_rungs_after"].fillna(0).sum()),
                            "before_median": float(ev["a2_valid_rungs_before"].median()),
                            "after_median_events_with_a2": float(ev.loc[ev["a2_state"] == "value", "a2_valid_rungs_after"].median()),
                            "before_zero_valid_events": int((ev["a2_valid_rungs_before"] == 0).sum()),
                            "after_zero_valid_events": int((ev["a2_valid_rungs_after"] == 0).sum())},
        "previously_valid_rungs_straddling_open": {"rungs": int(bstr["straddles_open"].sum()), "of_valid_rungs": int(len(bstr)),
                                                   "events": int(bstr[bstr["straddles_open"]]["event_id"].nunique()),
                                                   "rule": "window [tau - W_k, tau] meets the opening-cross minute [open, open + 60 s)"},
        "previously_valid_rungs_straddling_close": {"rungs": int(bstr["straddles_close"].sum()),
                                                    "events": int(bstr[bstr["straddles_close"]]["event_id"].nunique())},
        "previously_invalid_rungs_straddling_open": {"rungs": int((~b_rg["valid"] & b_rg["straddles_open"]).sum()),
                                                     "by_class": classes(b_rg[~b_rg["valid"] & b_rg["straddles_open"]])},
        "from_nothing": {"before_rungs": int((b_rg["class"] == "from_nothing").sum()),
                         "after_rungs": int((a_rg["class"] == "from_nothing").sum()),
                         "before_rung0_events": int(ev["a2_rung0_from_nothing_before"].sum()),
                         "after_rung0_events": int(ev["a2_rung0_from_nothing_after"].fillna(False).sum()),
                         "before_by_segment": b_rg[b_rg["class"] == "from_nothing"]["tau_anchor_segment"].value_counts().to_dict(),
                         "after_by_segment": a_rg[a_rg["class"] == "from_nothing"]["tau_anchor_segment"].value_counts().to_dict(),
                         "before_by_k": {str(k): int(v) for k, v in b_rg[b_rg["class"] == "from_nothing"]["k"].value_counts().sort_index().items()},
                         "after_by_k": {str(k): int(v) for k, v in a_rg[a_rg["class"] == "from_nothing"]["k"].value_counts().sort_index().items()},
                         "before_half_window_s_median": float(b_rg.loc[b_rg["class"] == "from_nothing", "W_s"].median() / 2),
                         "after_half_window_s_median": float(a_rg.loc[a_rg["class"] == "from_nothing", "W_s"].median() / 2),
                         "before_straddling_open": int(((b_rg["class"] == "from_nothing") & b_rg["straddles_open"]).sum())},
        "invalid_classes": {"before": classes(b_rg[~b_rg["valid"]]), "after": classes(a_rg[~a_rg["valid"]])},
        "premarket_ladders_identical": {"value": premarket_identical, "events": int(len(pm)),
                                        "why": "a premarket tau's segment start is 04:00, the anchor of runs 1-3"},
    }

    # ---------------------------------------------------------------- the cross-minute class on D1
    t2 = pd.read_parquet(C.art("t2_tau.parquet"), columns=["event_id", "event_date_canonical", "tau_available", "tau_ns"])
    t2 = t2[t2["tau_available"]].copy()
    bounds = {d: C.rth_bounds_ns(d) for d in t2["event_date_canonical"].unique()}
    t2["tau_anchor_segment"] = [C.clock_segment(int(t), *bounds[d]) for t, d in zip(t2["tau_ns"], t2["event_date_canonical"])]
    early = sum(1 for d, (o, c) in bounds.items() if (c - o) < 390 * C.MIN_NS)
    out["auction_minute_class"] = {
        "d1_tau_available": int(len(t2)),
        "d1_by_segment": t2["tau_anchor_segment"].value_counts().to_dict(),
        "d1_auction_open": int((t2["tau_anchor_segment"] == "auction_open").sum()),
        "d1_auction_close": int((t2["tau_anchor_segment"] == "auction_close").sum()),
        "dev_v3": int(ev["tau_in_auction_minute"].sum()),
        "dev_v3_ids": sorted(ev.loc[ev["tau_in_auction_minute"] == True, "event_id"].tolist()),  # noqa: E712
        "early_close_dates_in_d1": int(early),
        "brief_figure": "148 of 15,519 in 09:30:00-09:31:00 (A3.2)"}
    C.write_json(f"{C.ART}/t5_a3_before_after.json", out)
    print({k: out[k] for k in ("valid_rungs_all", "previously_valid_rungs_straddling_open", "from_nothing", "premarket_ladders_identical")})
    print(out["auction_minute_class"])
    for sg, v in by_seg.items():
        print(sg, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
