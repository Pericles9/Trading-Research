"""
Phase 8 T1 - decompose realized(09:30) (6b median 0.173) into three
log-space components against the tick anchor tick_close_t_minus_1_rth.

Scan-free (event_minute_bars_v2 + frozen 6b tick-anchor parquet). D4-clean:
every price is a tick-derived last/first trade from v2; the anchor and
day_high_ext are reused from opportunity_decay_primary.parquet (a61/6b,
tick-only). No spine numeric on any path.

Per event, prices:
  anchor         = tick_close_t_minus_1_rth (last T-1 premarket/rth print)
  p_last_tm1_ext = last extended print on T-1  (arg_max last_price by minute_index, offset -1)
  p_first_t0_ext = first extended print on T0   (arg_min first_price by minute_index, offset 0)
  p_0930         = last T0 print at/before minute_index 330 (RTH open)

Components (additive in log space; they sum to the numerator log(p_0930/anchor)):
  seg_t1_post  = log(p_last_tm1_ext / anchor)       T-1 16:00->20:00 observable path
  seg_overnight= log(p_first_t0_ext / p_last_tm1_ext) T-1 last -> T0 first ext (jump)
  seg_t0_pre   = log(p_0930 / p_first_t0_ext)        T0 first ext -> 09:30

Reported per component:
  - share of realized(09:30) = seg_i / numerator   (denom of realized cancels)
  - absolute log move        = seg_i

Definedness (flag, never impute):
  decomp_undefined = anchor missing OR any of the three prices missing (chiefly:
                     no T-1 extended-day bars). Own row.
  share_undefined  = numerator <= 0 (09:30 price at/below anchor; no positive
                     realized move to take a share of). Own row; still enters the
                     absolute-log-move panel.
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
ANCHOR_PATH = "results/phase_6b/artifacts/opportunity_decay_primary.parquet"
OUT_JSON = "results/phase_8/artifacts/t1_decomposition.json"
OUT_PARQUET = "results/phase_8/artifacts/t1_decomposition.parquet"
RTH_OPEN_MI = 330


def _iqr(s: pd.Series) -> list:
    s = s.dropna()
    if len(s) == 0:
        return [None, None]
    return [float(s.quantile(0.25)), float(s.quantile(0.75))]


def _dist(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0, "median": None, "iqr": [None, None], "min": None, "max": None}
    return {
        "n": int(len(s)),
        "median": float(s.median()),
        "iqr": _iqr(s),
        "min": float(s.min()),
        "max": float(s.max()),
    }


def main():
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")

    d1 = pd.read_parquet(D1_PATH)
    con.register("d1", d1)
    con.execute(
        "CREATE TEMP TABLE d1k AS "
        "SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp FROM d1"
    )

    prices = con.execute(f"""
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp,
               arg_max(b.last_price, b.minute_index) FILTER (b.session_offset = -1) AS p_last_tm1_ext,
               arg_min(b.first_price, b.minute_index) FILTER (b.session_offset = 0)  AS p_first_t0_ext,
               arg_max(b.last_price, b.minute_index)
                   FILTER (b.session_offset = 0 AND b.minute_index <= {RTH_OPEN_MI}) AS p_0930,
               COUNT(*) FILTER (b.session_offset = -1) AS n_bars_tm1
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical
                AND ROUND(b.momentum_pct,2)=d1k.mp
        GROUP BY 1,2,3
    """).fetchdf()

    anchor = pd.read_parquet(ANCHOR_PATH)
    anchor = anchor.assign(mp=anchor["momentum_pct"].round(2))[
        ["ticker", "event_date_canonical", "mp", "tick_close_t_minus_1_rth",
         "day_high_ext", "has_t_minus_1_rth", "denom_nonpositive"]
    ]

    df = prices.merge(anchor, on=["ticker", "event_date_canonical", "mp"], how="left")
    assert len(df) == len(d1), f"row mismatch after merge: {len(df)} vs D1 {len(d1)}"

    anc = df["tick_close_t_minus_1_rth"]
    defined = (
        anc.notna() & (anc > 0)
        & df["p_last_tm1_ext"].notna() & (df["p_last_tm1_ext"] > 0)
        & df["p_first_t0_ext"].notna() & (df["p_first_t0_ext"] > 0)
        & df["p_0930"].notna() & (df["p_0930"] > 0)
    )
    df["decomp_undefined"] = ~defined

    df["seg_t1_post"] = np.where(defined, np.log(df["p_last_tm1_ext"] / anc), np.nan)
    df["seg_overnight"] = np.where(defined, np.log(df["p_first_t0_ext"] / df["p_last_tm1_ext"]), np.nan)
    df["seg_t0_pre"] = np.where(defined, np.log(df["p_0930"] / df["p_first_t0_ext"]), np.nan)
    df["numerator"] = df["seg_t1_post"] + df["seg_overnight"] + df["seg_t0_pre"]

    df["share_undefined"] = defined & (df["numerator"] <= 0)
    share_ok = defined & (df["numerator"] > 0)
    for seg in ["seg_t1_post", "seg_overnight", "seg_t0_pre"]:
        df[f"share_{seg}"] = np.where(share_ok, df[seg] / df["numerator"], np.nan)

    # Cross-check against 6b realized_at_rth_open = numerator / log(day_high_ext/anchor)
    denom = np.where(defined & (df["day_high_ext"] > 0), np.log(df["day_high_ext"] / anc), np.nan)
    df["realized_at_rth_open_recomputed"] = df["numerator"] / denom

    df.to_parquet(OUT_PARQUET, index=False)

    n_total = len(df)
    n_decomp_undef = int(df["decomp_undefined"].sum())
    n_share_undef = int(df["share_undefined"].sum())
    n_share_ok = int(share_ok.sum())

    summary = {
        "phase": "8", "task": "T1",
        "source": "research/phase_8/t1_decomposition.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "n_d1": n_total,
        "n_decomp_undefined": n_decomp_undef,
        "n_decomp_undefined_reason": "no T-1 extended-day bars or missing anchor/prices (chiefly the 36 has_t_minus_1_rth=FALSE)",
        "n_share_undefined": n_share_undef,
        "n_share_undefined_reason": "numerator log(p_0930/anchor) <= 0 (09:30 price at/below the T-1 RTH close); no positive realized move to share. Carried; enters the absolute-move panel, not the share violins.",
        "n_share_defined": n_share_ok,
        "absolute_log_move": {
            "seg_t1_post": _dist(df.loc[defined, "seg_t1_post"]),
            "seg_overnight": _dist(df.loc[defined, "seg_overnight"]),
            "seg_t0_pre": _dist(df.loc[defined, "seg_t0_pre"]),
            "numerator_total": _dist(df.loc[defined, "numerator"]),
        },
        "share_of_realized_0930": {
            "seg_t1_post": _dist(df.loc[share_ok, "share_seg_t1_post"]),
            "seg_overnight": _dist(df.loc[share_ok, "share_seg_overnight"]),
            "seg_t0_pre": _dist(df.loc[share_ok, "share_seg_t0_pre"]),
        },
        "crosscheck_6b_realized_at_rth_open_median_recomputed": float(
            df.loc[defined, "realized_at_rth_open_recomputed"].median()
        ),
        "crosscheck_6b_note": "6b reported median realized_at_rth_open = 0.173; recomputed here from the same tick anchor as a consistency check.",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
