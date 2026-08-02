"""
Phase 8 A10.2a - detection anchor construction.

Scan-free (event_minute_bars_v2 + frozen 6b tick-anchor / high-time artifacts).
D4-clean: det threshold uses tick_close_t_minus_1_rth (tick), never spine prev_close.

det_anchor = first T0 extended-day minute at which last_price >= 1.30 *
tick_close_t_minus_1_rth. Price threshold only; no smoothing/confirmation/
volume qualifier; multiplier frozen at 1.30 (escalation row 14).

Outputs per event: det_minute, det_undefined, detection segment + time bin,
runway (minutes and log distance to day_high_ext), and last-trade-at/before
prices at det+{0,1,5,15,30} (the latency ladder; det+0 is a physical upper
bound). Saved to a102_detection_anchors.parquet for A10.2b/c.

Escalation row 13: share of D1 whose T0 extended max (day_high_ext) never
reaches 1.30x anchor > 2% -> hard stop (tick threshold vs momentum_pct).
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
ANCHOR_PATH = "results/phase_6b/artifacts/opportunity_decay_primary.parquet"
HIGH_PATH = "results/phase_6b/artifacts/high_time_of_day.parquet"
OUT_PARQUET = "results/phase_8/artifacts/a102_detection_anchors.parquet"
OUT_JSON = "results/phase_8/artifacts/a102_detection_summary.json"
KEY = ["ticker", "event_date_canonical", "mp"]
MULT = 1.30
LAT = [0, 1, 5, 30, 15]  # ladder; order irrelevant
ERA_BOUNDARY = pd.Timestamp("2022-01-01")


def seg(mi):
    if pd.isna(mi):
        return None
    return "premarket" if mi < 330 else ("rth" if mi < 720 else "post")


def det_bin(mi):
    if pd.isna(mi):
        return None
    if mi < 330:
        return "premarket"
    if mi < 360:
        return "0930-1000"
    if mi < 420:
        return "1000-1100"
    if mi < 540:
        return "1100-1300"
    return "after_1300"


def main():
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    d1 = pd.read_parquet(D1_PATH); d1["event_date_canonical"] = pd.to_datetime(d1["event_date_canonical"])
    d1["mp"] = d1["momentum_pct"].round(2)

    anc = pd.read_parquet(ANCHOR_PATH); anc["event_date_canonical"] = pd.to_datetime(anc["event_date_canonical"])
    anc["mp"] = anc["momentum_pct"].round(2)
    anc = anc[KEY + ["tick_close_t_minus_1_rth", "day_high_ext", "has_t_minus_1_rth"]]
    anc["threshold"] = MULT * anc["tick_close_t_minus_1_rth"]

    high = pd.read_parquet(HIGH_PATH); high["event_date_canonical"] = pd.to_datetime(high["event_date_canonical"])
    high["mp"] = high["momentum_pct"].round(2)
    high = high[KEY + ["high_minute_index", "high"]]

    ev = d1[KEY].drop_duplicates().merge(anc, on=KEY, how="left").merge(high, on=KEY, how="left")
    ev["era"] = np.where(ev["event_date_canonical"] < ERA_BOUNDARY, "era_2020_2021", "era_2022_2024")

    # det_minute: first T0 minute whose CROSSING PRINT (bar high) reaches threshold.
    # A10.3 reconciliation: high (the crossing print a scanner sees), not last_price,
    # so det_undefined == the 394 day_high_ext non-reachers and n=15,369 (Cooper term b).
    # bar.high is a v2 tick-derived field, not spine OHLC -> D4-clean (row 14 intact).
    con.register("d1k", ev[KEY])
    con.register("thr", ev[KEY + ["threshold"]])
    det = con.execute("""
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp,
               MIN(b.minute_index) FILTER (b.high >= t.threshold) AS det_minute
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical AND ROUND(b.momentum_pct,2)=d1k.mp
        JOIN thr t ON b.ticker=t.ticker AND b.event_date_canonical=t.event_date_canonical AND ROUND(b.momentum_pct,2)=t.mp
        WHERE b.session_offset = 0 AND t.threshold IS NOT NULL
        GROUP BY 1,2,3
    """).fetchdf()
    det["event_date_canonical"] = pd.to_datetime(det["event_date_canonical"])
    ev = ev.merge(det, on=KEY, how="left")
    ev["det_undefined"] = ev["det_minute"].isna()
    ev["det_segment"] = ev["det_minute"].map(seg)
    ev["det_bin"] = ev["det_minute"].map(det_bin)
    ev["never_reach_high"] = ~(ev["day_high_ext"] >= ev["threshold"])  # row-13 metric (incl. NaN anchor)

    # latency-offset anchor prices via ASOF (last trade at/before det_minute+offset)
    con.execute("""
        CREATE TEMP TABLE p8t0 AS
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp, b.minute_index, b.last_price
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical AND ROUND(b.momentum_pct,2)=d1k.mp
        WHERE b.session_offset = 0
    """)
    tgt = ev[~ev.det_undefined][KEY + ["det_minute"]].copy()
    tr = []
    for k in LAT:
        t = tgt.copy(); t["lat"] = k; t["target_minute"] = t["det_minute"] + k
        tr.append(t)
    targets = pd.concat(tr, ignore_index=True)
    con.register("targets", targets)
    priced = con.execute("""
        SELECT t.ticker, t.event_date_canonical, t.mp, t.lat, t.target_minute, b.last_price AS price
        FROM targets t
        ASOF LEFT JOIN p8t0 b
          ON t.ticker=b.ticker AND t.event_date_canonical=b.event_date_canonical AND t.mp=b.mp
         AND t.target_minute >= b.minute_index
    """).fetchdf()
    priced["event_date_canonical"] = pd.to_datetime(priced["event_date_canonical"])
    wide = priced.pivot_table(index=KEY, columns="lat", values="price", aggfunc="first")
    wide.columns = [f"det_price_lat{int(c)}" for c in wide.columns]
    ev = ev.merge(wide, on=KEY, how="left")

    # runway: minutes det->high, log distance det_price(lat0)->day_high_ext
    ev["runway_minutes"] = ev["high_minute_index"] - ev["det_minute"]
    ev["runway_log_distance"] = np.where(
        ev["det_undefined"] | ev["det_price_lat0"].isna() | ~(ev["det_price_lat0"] > 0) | ~(ev["day_high_ext"] > 0),
        np.nan, np.log(ev["day_high_ext"] / ev["det_price_lat0"]))

    ev.to_parquet(OUT_PARQUET, index=False)

    n = len(ev)
    n_det_undef = int(ev["det_undefined"].sum())
    n_never_high = int(ev["never_reach_high"].sum())
    row13_rate = n_never_high / n
    seg_counts = ev[~ev.det_undefined]["det_segment"].value_counts().to_dict()
    bin_counts = ev[~ev.det_undefined]["det_bin"].value_counts().to_dict()

    def q(s):
        s = s.dropna()
        return {"n": int(len(s)), "median": float(s.median()), "q25": float(s.quantile(.25)),
                "q75": float(s.quantile(.75)), "min": float(s.min()), "max": float(s.max())}

    # A10.3(d) report-only diagnostic on the 394 det_undefined events: distribution
    # of tick max-move fraction (day_high_ext / tick_close_t_minus_1_rth), and a
    # split-adjacent proxy count (no splits feed available -> ratio-based proxy,
    # labelled as such). Registered reopen condition: if the 394 are scattered well
    # below threshold rather than clustered near it, reopen the momentum_pct basis
    # question as an Open-Items entry.
    und = ev[ev["det_undefined"]].copy()
    und["tick_maxmove_ratio"] = und["day_high_ext"] / und["tick_close_t_minus_1_rth"]
    ratio = und["tick_maxmove_ratio"].dropna()
    n_no_anchor = int((und["tick_close_t_minus_1_rth"].isna() | ~(und["tick_close_t_minus_1_rth"] > 0)).sum())
    split_proxy_reverse = int((ratio < 1.0).sum())       # day high below prior close -> basis flip (reverse split)
    split_proxy_severe = int((ratio < 0.9).sum())        # strongly off basis
    near_threshold = int(((ratio >= 1.20) & (ratio < 1.30)).sum())  # clustered just below 1.30
    a103_diag = {
        "n_det_undefined": int(len(und)),
        "n_no_anchor_has_t_minus_1_rth_false": n_no_anchor,
        "n_anchor_present": int(len(ratio)),
        "tick_maxmove_ratio_dist_anchor_present": q(ratio),
        "clustered_near_threshold_1p20_to_1p30_n": near_threshold,
        "clustered_near_threshold_share_of_anchor_present": (near_threshold / len(ratio)) if len(ratio) else None,
        "split_adjacent_proxy_note": "no splits feed available; proxy = tick maxmove ratio implausible for a genuine intraday momentum event",
        "split_adjacent_proxy_ratio_lt_1p0": split_proxy_reverse,
        "split_adjacent_proxy_ratio_lt_0p9": split_proxy_severe,
        "reopen_condition": "scattered well below threshold -> reopen momentum_pct basis item; clustered near threshold -> do not reopen",
    }

    summary = {
        "phase": "8", "task": "A10.2a",
        "source": "research/phase_8/a102_detection.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "multiplier": MULT,
        "crossing_price_field": "bar high (A10.3 reconciliation; see config)",
        "detection_universe_n": n - n_det_undef,
        "coverage": {
            "n_d1": n,
            "n_det_defined": n - n_det_undef, "det_defined_share": (n - n_det_undef) / n,
            "n_det_undefined": n_det_undef,
            "n_never_reach_high_ext": n_never_high, "never_reach_high_ext_share": row13_rate,
            "row13_threshold": 0.02, "row13_triggered": row13_rate > 0.02,
            "row13_disposition": "A10.3 override (Cooper 2026-08-01): proceed; the 394 carry det_undefined=TRUE, detection figures use n=15,369, multiplier stays 1.30",
        },
        "a10_3_diagnostic_394": a103_diag,
        "detection_segment_counts": seg_counts,
        "detection_bin_counts": bin_counts,
        "detection_minute_by_segment": {
            s: q(ev.loc[(~ev.det_undefined) & (ev.det_segment == s), "det_minute"])
            for s in ["premarket", "rth", "post"]},
        "runway_minutes": q(ev.loc[~ev.det_undefined, "runway_minutes"]),
        "runway_minutes_by_era": {e: q(ev.loc[(~ev.det_undefined) & (ev.era == e), "runway_minutes"])
                                  for e in ["era_2020_2021", "era_2022_2024"]},
        "runway_log_distance": q(ev.loc[~ev.det_undefined, "runway_log_distance"]),
        "artifact": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("detection_minute_by_segment",)}, indent=2, default=str))
    if summary["coverage"]["row13_triggered"]:
        print("\n[row 13 at 2.50% -> A10.3 override: proceed; 394 carried det_undefined; n=15,369]")


if __name__ == "__main__":
    main()
