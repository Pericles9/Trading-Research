"""
Brief 1, T3 -- the open-adjacent boundary, measured (DA-4). No outcome enters.

From event_minute_bars_v2, all D1 events, event day only: per event and clock minute, n_trades divided
by that event's own median per-minute n_trades over the event day's existing bars, so no single loud
name dominates. Each event contributes only minutes that END at or before its own tau (the crossing
burst is excluded). Cross-event median and IQR per clock minute, 03:55 -> 10:30.

Proposal rule (config t3_open_boundary.proposal_rule): for each open O, L(m) = median of the
per-minute medians over [m+10, m+20]; the proposed boundary is the first minute m >= O with
p25(m) <= L(m) <= p75(m). The profile is computed out to 11:00 so that L is defined through 10:30;
only 03:55-10:30 is charted. Cooper confirms or replaces the boundary at T7.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t3_open_boundary.py
"""
from __future__ import annotations

import os
import sys

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

M_LO, M_HI = -5, 420          # clock minutes from 04:00: 03:55 .. 11:00 (exclusive)
M_CHART_HI = 390              # 10:30
OPENS = {"04:00": 0, "09:30": 330}


def main() -> int:
    cfg = C.load_cfg()
    t2 = pd.read_parquet(C.art("t2_tau.parquet"),
                         columns=["event_id", "ticker", "event_date_canonical", "tau_available", "tau_reason",
                                  "tau_ns", "prior_close_available"])
    t2["t0400_ns"] = [C.et_ns(d, "04:00:00") for d in t2["event_date_canonical"]]
    use = t2[t2["prior_close_available"]].copy()          # tau placeable
    excluded_no_prior_close = int((~t2["prior_close_available"]).sum())
    use["tau_ns_f"] = use["tau_ns"].astype("float64")      # NaN for never-crosses
    ev = use[["event_id", "ticker", "event_date_canonical", "t0400_ns"]].copy()
    ev["event_date_canonical"] = pd.to_datetime(ev["event_date_canonical"]).dt.date

    con = duckdb.connect(str(C.REPO / "data" / "duckdb" / "main.duckdb"), read_only=True)
    con.register("ev", ev)
    bars = con.execute("""
        SELECT e.event_id,
               CAST(floor((b.first_trade_ts - e.t0400_ns) / 60e9) AS INTEGER) AS clock_min,
               b.minute_index, b.n_trades
        FROM event_minute_bars_v2 b
        JOIN ev e ON b.ticker = e.ticker AND b.event_date_canonical = e.event_date_canonical
        WHERE b.session_offset = 0
    """).df()
    con.close()
    bars = bars[(bars["clock_min"] >= 0) & (bars["clock_min"] < 960)]
    idx_mismatch = bars[bars["clock_min"] < 390]
    n_mismatch = int((idx_mismatch["clock_min"] != idx_mismatch["minute_index"]).sum())

    med = bars.groupby("event_id")["n_trades"].median()
    ev_ids = use["event_id"].tolist()
    pos = {e: i for i, e in enumerate(ev_ids)}
    n_ev, n_m = len(ev_ids), M_HI - M_LO
    grid = np.zeros((n_ev, n_m))
    w = bars[(bars["clock_min"] >= M_LO) & (bars["clock_min"] < M_HI)]
    ri = w["event_id"].map(pos).to_numpy()
    ci = (w["clock_min"] - M_LO).to_numpy()
    denom = w["event_id"].map(med).to_numpy()
    grid[ri, ci] = w["n_trades"].to_numpy() / denom

    # inclusion: minute ends at or before tau; never-crosses -> every minute; before 04:00 -> no data
    t0400 = use["t0400_ns"].to_numpy(dtype=np.float64)
    tau = use["tau_ns_f"].to_numpy()
    mins = np.arange(M_LO, M_HI)
    end_ns = t0400[:, None] + (mins[None, :] + 1) * 60e9
    incl = np.where(np.isnan(tau)[:, None], True, end_ns <= tau[:, None])
    incl &= (mins[None, :] >= 0)
    no_bars = ~use["event_id"].isin(med.index).to_numpy()
    incl[no_bars, :] = False
    g = np.where(incl, grid, np.nan)

    prof = pd.DataFrame({
        "clock_min": mins,
        "clock_et": [f"{(4 * 60 + m) // 60:02d}:{(4 * 60 + m) % 60:02d}" for m in mins],
        "n_events": incl.sum(0),
        "median": np.nanmedian(np.where(incl.any(0)[None, :], g, 0.0), axis=0),
        "p25": np.nanpercentile(np.where(incl.any(0)[None, :], g, 0.0), 25, axis=0),
        "p75": np.nanpercentile(np.where(incl.any(0)[None, :], g, 0.0), 75, axis=0),
        "mean": np.nanmean(np.where(incl.any(0)[None, :], g, 0.0), axis=0),
    })
    prof.loc[prof["n_events"] == 0, ["median", "p25", "p75", "mean"]] = np.nan
    prof["share_zero"] = [float(np.mean(g[incl[:, j], j] == 0)) if incl[:, j].any() else np.nan for j in range(n_m)]

    medv = prof["median"].to_numpy()
    prof["L_ref_10_20"] = [np.nanmedian(medv[j + 10:j + 21]) if j + 21 <= n_m else np.nan for j in range(n_m)]
    prof["within_iqr"] = (prof["p25"] <= prof["L_ref_10_20"]) & (prof["L_ref_10_20"] <= prof["p75"])
    prof.to_parquet(C.art("t3_open_profile.parquet"), index=False)

    proposals = {}
    for name, o in OPENS.items():
        sub = prof[(prof["clock_min"] >= o) & prof["L_ref_10_20"].notna()]
        first = sub[sub["within_iqr"]]
        f1 = first.iloc[0] if len(first) else None
        run = None
        wi = sub["within_iqr"].to_numpy()
        for k in range(len(wi) - 4):
            if wi[k:k + 5].all():
                run = sub.iloc[k]
                break
        proposals[name] = {
            "open_clock_min": o,
            "proposed_boundary_first_minute": None if f1 is None else {"clock_et": f1["clock_et"], "minutes_after_open": int(f1["clock_min"] - o),
                                                                       "n_events": int(f1["n_events"])},
            "proposed_boundary_5_consecutive": None if run is None else {"clock_et": run["clock_et"], "minutes_after_open": int(run["clock_min"] - o),
                                                                         "n_events": int(run["n_events"])},
            "profile_at_open": prof[prof["clock_min"].between(o, o + 25)][["clock_et", "n_events", "median", "p25", "p75", "L_ref_10_20", "within_iqr"]].to_dict("records"),
        }

    summary = {
        "config_hash": C.cfg_hash(),
        "rule": cfg["t3_open_boundary"]["proposal_rule"],
        "events_used": int(n_ev - no_bars.sum()),
        "events_excluded_prior_close_unavailable": excluded_no_prior_close,
        "events_without_bars": int(no_bars.sum()),
        "events_never_crossing_all_minutes_included": int(np.isnan(tau).sum()),
        "minute_index_vs_clock_minute_mismatch_before_1030": n_mismatch,
        "bars_before_1030": int(len(idx_mismatch)),
        "pre_0400": "event_minute_bars_v2 holds no bars before 04:00 -- 03:55-03:59 carry n = 0",
        "proposals": proposals,
        "outcome_used": "none",
    }
    C.write_json(f"{C.ART}/t3_open_boundary.json", summary)
    for k, v in proposals.items():
        print(k, v["proposed_boundary_first_minute"], v["proposed_boundary_5_consecutive"])
    print("mismatch", n_mismatch, "of", len(idx_mismatch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
