"""
T1: build participation onset and end.

E2's baseline B_e is reused verbatim. E2's WINDOW artifact is rebuilt -- see common.py's module
docstring and the config's e2_reuse.rebuild_rationale for why it cannot serve as an exit.

Both marks come from event_minute_bars_v2 restricted to session_offset = 0, which is what enforces
censoring at the event-day extended session end structurally rather than as an afterthought.

  participation_end   first minute after t0 where trailing-10-min dollar volume <= 3 x B_e
                      and stays there for C consecutive minutes
  participation_onset the mirror: first minute after t0 where it is >= 3 x B_e and stays for C

C is DECLARED here at 10 minutes with a {5, 10, 20} sensitivity ladder. The brief says to carry
E2's declared value; that value is unrecoverable because E2's brief and code were never committed.

Usage: .venv/Scripts/python.exe research/participation_exit_overlay/t1_participation.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.participation_exit_overlay import common as C  # noqa: E402
from src.data.db import get_connection  # noqa: E402

OUT_JSON = f"{C.ART}/t1_participation.json"
OUT_PARQUET = f"{C.ART}/t1_participation.parquet"

SQL = """
SELECT b.ticker,
       CAST(b.event_date_canonical AS VARCHAR) AS date,
       b.minute_index,
       b.segment,
       b.volume,
       b.vwap,
       b.last_price,
       b.first_trade_ts
FROM event_minute_bars_v2 b
WHERE b.session_offset = 0
"""


def main() -> int:
    cfg = C.load_cfg()
    pr = cfg["participation_rule"]
    trailing = pr["trailing_window_minutes"]
    mult = pr["multiple"]
    c_ref = pr["C_minutes"]["reference"]
    c_ladder = pr["C_minutes"]["ladder"]

    pop = C.load_population()
    be = pd.read_parquet(C.REPO / C.BASELINE)[
        ["event_id", "B_e", "n_baseline_sessions", "total_baseline_dollar_volume"]]
    fun = pd.read_parquet(C.REPO / C.FUNDAMENTALS)[["event_id", "t0_ns", "t0_source"]]
    pop = pop.merge(be, on="event_id", how="left", suffixes=("", "_e2"))
    pop = pop.merge(fun, on="event_id", how="left")

    # E2 DE-2: baseline thin is flagged and carried.
    pop["baseline_thin"] = pop["n_baseline_sessions"].fillna(0) < 3

    t0 = time.time()
    con = get_connection(read_only=True)
    bars = con.execute(SQL).df()
    print(f"minute bars (session_offset=0): {len(bars):,} rows in {time.time()-t0:.0f}s", flush=True)
    bars["key"] = bars["ticker"] + "|" + bars["date"]
    bars["dollar"] = bars["volume"].astype("float64") * bars["vwap"].astype("float64")

    wanted = set(pop["key"])
    bars = bars[bars["key"].isin(wanted)]
    print(f"  of which in the 903: {len(bars):,} rows, "
          f"{bars['key'].nunique()} events", flush=True)

    grids: dict[str, np.ndarray] = {}
    lastpx: dict[str, np.ndarray] = {}
    for key, g in bars.groupby("key"):
        v = np.zeros(C.SESSION_MINUTES, dtype=np.float64)
        lp = np.full(C.SESSION_MINUTES, np.nan)
        mi = g["minute_index"].to_numpy()
        ok = (mi >= 0) & (mi < C.SESSION_MINUTES)
        v[mi[ok]] = g["dollar"].to_numpy()[ok]
        lp[mi[ok]] = g["last_price"].to_numpy()[ok]
        grids[key] = v
        lastpx[key] = lp

    rows = []
    for r in pop.itertuples(index=False):
        base = C.session_base_ns(r.date)
        t0_min = int((int(r.t0_ns) - base) // C.MIN_NS)
        tau_min = int((int(r.tau_ns) - base) // C.MIN_NS)
        rec = {"key": r.key, "t0_minute": t0_min, "tau_minute": tau_min,
               "session_base_ns": base,
               "censor_horizon_ns": base + C.SESSION_MINUTES * C.MIN_NS}
        v = grids.get(r.key)
        if v is None or not np.isfinite(r.B_e) or r.B_e <= 0:
            rec.update({"bars_available": False})
            rows.append(rec)
            continue
        rec["bars_available"] = True
        rec["minutes_with_volume"] = int((v > 0).sum())
        for c in c_ladder:
            m = C.participation_marks(v, float(r.B_e), t0_min, c, mult, trailing)
            suf = "" if c == c_ref else f"_C{c}"
            rec[f"onset_minute{suf}"] = m["onset_minute"]
            rec[f"end_minute{suf}"] = m["end_minute"]
            if c == c_ref:
                rec["trailing_at_t0_usd"] = m["trailing_at_t0"]
                rec["threshold_usd"] = m["threshold_usd"]
                rec["peak_trailing_usd"] = m["peak_trailing_usd"]
            # Exit B anchor: the first decay AT OR AFTER tau. An exit cannot precede its entry.
            k = np.ones(trailing, dtype=np.float64)
            tr = np.convolve(v, k, mode="full")[: v.size]
            eb = C.run_length_first(tr <= mult * float(r.B_e), max(tau_min, 0), c)
            rec[f"exit_b_minute{suf}"] = eb
        rows.append(rec)

    d = pop.merge(pd.DataFrame(rows), on="key", how="left")
    assert len(d) == len(pop), "participation join changed the row count"

    # ---- timestamps, in two flavours, because they are not the same instant ----
    #
    # THE FACT: the minute at which participation actually crossed. This is what the T2 overlay
    # reports, because the overlay is about when participation moved, not when a trader knew.
    #
    # THE CONFIRMATION: the rule requires the crossing to HOLD for C consecutive minutes, so the
    # earliest instant it can be acted on is the END of minute (mark + C - 1). Timestamping an
    # exit at the start of the crossing minute would let the trade use C minutes of information
    # that had not happened yet -- lookahead, and exactly the defect class this programme has
    # spent v0/v1/v2 removing. Exit B therefore uses the CONFIRMED instant.
    c_ref_minutes = c_ref
    for col, fact_out, conf_out in [
            ("onset_minute", "participation_onset_ns", "participation_onset_confirmed_ns"),
            ("end_minute", "participation_end_ns", "participation_end_confirmed_ns"),
            ("exit_b_minute", "exit_b_ns", "exit_b_confirmed_ns")]:
        mi = d[col]
        d[fact_out] = np.where(mi.notna(), d["session_base_ns"] + mi.fillna(0) * C.MIN_NS, np.nan)
        d[conf_out] = np.where(
            mi.notna(),
            d["session_base_ns"] + (mi.fillna(0) + c_ref_minutes) * C.MIN_NS, np.nan)
    d["onset_censored"] = d["bars_available"] & d["onset_minute"].isna()
    d["end_censored"] = d["bars_available"] & d["end_minute"].isna()
    d["exit_b_censored"] = d["bars_available"] & d["exit_b_minute"].isna()
    # a censored Exit B exits at the censoring horizon, labelled, never silently tradeable.
    # Uncensored Exit B uses the CONFIRMED instant, clamped so it can never precede its own entry
    # and never run past the censoring horizon.
    d["exit_b_ns_effective"] = np.where(
        d["exit_b_censored"], d["censor_horizon_ns"],
        np.minimum(np.maximum(d["exit_b_confirmed_ns"], d["tau_ns"]), d["censor_horizon_ns"]))
    d["exit_b_clamped_to_tau"] = (~d["exit_b_censored"]) & (
        d["exit_b_confirmed_ns"] < d["tau_ns"])
    assert int((d["exit_b_ns_effective"] < d["tau_ns"]).sum()) == 0,         "Exit B precedes its own entry after clamping"

    d["t0_to_onset_sec"] = (d["participation_onset_ns"] - d["t0_ns"]) / C.NS
    d["tau_minus_onset_sec"] = (d["tau_ns"] - d["participation_onset_ns"]) / C.NS
    d["windowclose_minus_end_sec"] = (d["natural_exit_ts"] - d["participation_end_ns"]) / C.NS
    d["exitb_minus_windowclose_sec"] = (d["exit_b_ns_effective"] - d["natural_exit_ts"]) / C.NS
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    # divergence from E2's artifact, reported rather than hidden
    e2 = pd.read_parquet(C.REPO / C.E2_WINDOW)[["event_id", "window_end_ts", "duration_min",
                                                "censored"]]
    cmp_ = d[["key", "event_id", "tau_ns", "participation_end_ns", "end_censored"]].merge(
        e2, on="event_id", how="left")
    cmp_["e2_end_before_tau"] = cmp_["window_end_ts"] < cmp_["tau_ns"]

    def qd(x, ps=(.05, .25, .5, .75, .95)):
        x = np.asarray(x, dtype=float); x = x[np.isfinite(x)]
        return {f"p{int(p*100)}": round(float(np.quantile(x, p)), 1) for p in ps} if x.size else {}

    ok = d[d["bars_available"].fillna(False)]
    summary = {
        "task": "T1 participation onset and end",
        "config_hash": C.cfg_hash(),
        "e2_reuse": cfg["e2_reuse"]["status"],
        "e2_rebuild_rationale": cfg["e2_reuse"]["rebuild_rationale"]["why_not_reusable_as_an_exit"],
        "rule": {"trailing_minutes": trailing, "multiple": mult,
                 "C_reference": c_ref, "C_ladder": c_ladder,
                 "C_status": pr["C_minutes"]["status"]},
        "n": int(len(d)), "n_bars_available": int(ok.shape[0]),
        "n_bars_unavailable": int(len(d) - ok.shape[0]),
        "censoring": {
            "horizon": pr["censoring"]["horizon"],
            "n_onset_censored": int(d["onset_censored"].sum()),
            "n_end_censored": int(d["end_censored"].sum()),
            "n_exit_b_censored": int(d["exit_b_censored"].sum()),
            "share_exit_b_censored": round(float(d["exit_b_censored"].mean()), 4),
            "note": "censored events are their own class; no mean is taken across censored and "
                    "uncensored (E2 DE-3).",
        },
        "onset": {
            "n_found": int(d["onset_minute"].notna().sum()),
            "t0_to_onset_sec": qd(ok["t0_to_onset_sec"]),
            "share_onset_at_or_before_tau": round(
                float((ok["participation_onset_ns"] <= ok["tau_ns"]).mean()), 4),
        },
        "end": {
            "n_found": int(d["end_minute"].notna().sum()),
            "share_end_before_tau": round(
                float((ok["participation_end_ns"] < ok["tau_ns"]).mean()), 4),
            "note": "this is why Exit B anchors on the first decay AT OR AFTER tau rather than on "
                    "the t0-anchored end -- an exit cannot precede its entry.",
        },
        "causality": {
            "fact_vs_confirmed": "participation_*_ns is the minute the crossing happened (the "
                                 "fact, used by the T2 overlay). participation_*_confirmed_ns is "
                                 "the end of minute (mark + C - 1), the earliest instant the "
                                 "C-minute run is knowable. Exit B uses the CONFIRMED instant; "
                                 "timestamping it at the start of the crossing minute would use "
                                 "C minutes of information that had not happened yet.",
            "confirmation_lag_sec": c_ref * 60,
            "n_exit_b_clamped_to_tau": int(d["exit_b_clamped_to_tau"].sum()),
            "clamp_note": "events whose confirmed decay still lands before tau exit at tau, i.e. "
                          "a zero-length hold; counted, never negative.",
        },
        "exit_b": {
            "n_found": int(d["exit_b_minute"].notna().sum()),
            "exitb_minus_windowclose_sec": qd(ok["exitb_minus_windowclose_sec"]),
            "share_exit_b_after_window_close": round(
                float((ok["exit_b_ns_effective"] > ok["natural_exit_ts"]).mean()), 4),
        },
        "baseline_thin_de2": {
            "n_thin": int(d["baseline_thin"].sum()),
            "by_n_baseline_sessions": d["n_baseline_sessions"].value_counts().sort_index().to_dict(),
        },
        "divergence_from_e2_artifact": {
            "n_e2_end_before_tau": int(cmp_["e2_end_before_tau"].sum()),
            "share_e2_end_before_tau": round(float(cmp_["e2_end_before_tau"].mean()), 4),
            "e2_duration_min_median": round(float(cmp_["duration_min"].median()), 2),
            "e2_share_duration_zero": round(float((cmp_["duration_min"] == 0).mean()), 4),
            "e2_censored_any": bool(cmp_["censored"].any()),
            "rebuilt_end_censored_share": round(float(d["end_censored"].mean()), 4),
        },
        "output_parquet": OUT_PARQUET,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
