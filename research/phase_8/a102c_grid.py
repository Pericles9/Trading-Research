"""
Phase 8 A10.2c - detection-anchored markout grid (the tradeable grid).

Scan-free. Anchor = det+L latency offset (L in {0,1,5,15,30}; det+0 is a
physical upper bound). Horizons: det+{5,15,30,60}, t0_close, t1_close,
t3_close - each a signed log return from each latency anchor (sign kept).
Bucket = detection time-of-day bin (participation NOT used - collinear with
the crossing). Era faceted. Carried flags: the five T5d populations + the 394
det_undefined, own rows, never pooled.

Prices: last trade at/before target minute (ASOF over T0 bars) for the
det-relative points; session closes reused from t4_anchors.parquet. All
figures on the detection universe n=15,369 (A10.3).
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
T4 = "results/phase_8/artifacts/t4_anchors.parquet"
A101 = "results/phase_8/artifacts/a101_labels.parquet"
T3 = "results/phase_8/artifacts/t3_participation.parquet"
ANCHOR6B = "results/phase_6b/artifacts/opportunity_decay_primary.parquet"
DUP6B = "results/phase_6b/artifacts/event_index_v2.parquet"
OUT_GRID = "results/phase_8/artifacts/a102_detection_markout_grid.parquet"
OUT_JSON = "results/phase_8/artifacts/a102_detection_markout_summary.json"
KEY = ["ticker", "event_date_canonical", "mp"]
LAT = [0, 1, 5, 15, 30]
DET_H = [5, 15, 30, 60]
OFFSETS = sorted(set(LAT) | set(DET_H))  # 0,1,5,15,30,60
DET_BINS = ["premarket", "0930-1000", "1000-1100", "1100-1300", "after_1300"]
FLAGSHIP_L, FLAGSHIP_H = 5, "t0_close"


def _norm(df):
    df["event_date_canonical"] = pd.to_datetime(df["event_date_canonical"]); return df


def _cell(s):
    s = s.dropna()
    return {"n": int(len(s)), "median": (float(s.median()) if len(s) else None),
            "iqr": ([float(s.quantile(.25)), float(s.quantile(.75))] if len(s) else [None, None])}


def main():
    ev = _norm(pd.read_parquet(ANCH))
    det = ev[~ev.det_undefined].copy()

    # session-close prices + last_t0_mi from t4 (anchor='t0_close' rows cover all events)
    t4 = _norm(pd.read_parquet(T4))
    t4c = t4[t4.anchor_name == "t0_close"]
    t0p = t4c[KEY + ["anchor_price"]].drop_duplicates(KEY).rename(columns={"anchor_price": "p_t0_close"})
    t1p = t4c[t4c.horizon_name == "t1_close"][KEY + ["horizon_price", "horizon_undefined"]].rename(
        columns={"horizon_price": "p_t1_close", "horizon_undefined": "u_t1_close"})
    t3p = t4c[t4c.horizon_name == "t3_close"][KEY + ["horizon_price", "horizon_undefined"]].rename(
        columns={"horizon_price": "p_t3_close", "horizon_undefined": "u_t3_close"})
    det = det.merge(t0p, on=KEY, how="left").merge(t1p, on=KEY, how="left").merge(t3p, on=KEY, how="left")

    # det-relative prices at det_minute + offset via ASOF over T0 bars
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    con.register("d1k", det[KEY])
    con.execute("""
        CREATE TEMP TABLE p8t0 AS
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp, b.minute_index, b.last_price
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical AND ROUND(b.momentum_pct,2)=d1k.mp
        WHERE b.session_offset = 0
    """)
    lastmi = con.execute("SELECT ticker, event_date_canonical, mp, MAX(minute_index) AS last_t0_mi FROM p8t0 GROUP BY 1,2,3").fetchdf()
    lastmi = _norm(lastmi)
    det = det.merge(lastmi, on=KEY, how="left")
    tr = []
    for off in OFFSETS:
        t = det[KEY + ["det_minute", "last_t0_mi"]].copy()
        t["off"] = off; t["target_minute"] = t["det_minute"] + off
        tr.append(t)
    targets = pd.concat(tr, ignore_index=True)
    con.register("targets", targets)
    priced = con.execute("""
        SELECT t.ticker, t.event_date_canonical, t.mp, t.off, t.target_minute, t.last_t0_mi, b.last_price AS price
        FROM targets t
        ASOF LEFT JOIN p8t0 b
          ON t.ticker=b.ticker AND t.event_date_canonical=b.event_date_canonical AND t.mp=b.mp
         AND t.target_minute >= b.minute_index
    """).fetchdf()
    priced = _norm(priced)
    # undefined if target beyond last T0 print
    priced["price"] = np.where(priced["target_minute"] > priced["last_t0_mi"], np.nan, priced["price"])
    wide = priced.pivot_table(index=KEY, columns="off", values="price", aggfunc="first")
    wide.columns = [f"p_off{int(c)}" for c in wide.columns]
    det = det.merge(wide, on=KEY, how="left")

    # flags: five T5d populations + det_undefined (det already excluded here)
    a101 = _norm(pd.read_parquet(A101))
    t3 = _norm(pd.read_parquet(T3))
    anc6b = _norm(pd.read_parquet(ANCHOR6B)); anc6b["mp"] = anc6b["momentum_pct"].round(2)
    dup6b = _norm(pd.read_parquet(DUP6B)); dup6b["mp"] = dup6b["momentum_pct"].round(2)
    def st(df, col, val=True): return set(map(tuple, df.loc[df[col].astype(bool) == val, KEY].values))
    flagged = (set(map(tuple, t3.loc[t3.participation_class == "no_baseline", KEY].values))
               | set(map(tuple, anc6b.loc[~anc6b.has_t_minus_1_rth.astype(bool), KEY].values))
               | set(map(tuple, anc6b.loc[anc6b.denom_nonpositive.astype(bool), KEY].values))
               | set(map(tuple, dup6b.loc[dup6b.flag_has_dup_prints.astype(bool), KEY].values))
               | set(map(tuple, a101.loc[a101.flag_possible_row_cap.astype(bool), KEY].values)))
    det["in_flagged_union"] = list(map(lambda t: t in flagged, zip(det.ticker, det.event_date_canonical, det.mp)))

    # build long markout table: (L anchor) x (horizon) with H after L
    def hprice(row, h):
        if h in ("t0_close", "t1_close", "t3_close"):
            return row[f"p_{h}"]
        return row[f"p_off{h}"]
    rows = []
    detm = det[~det.in_flagged_union].copy()
    for L in LAT:
        aprice = detm[f"p_off{L}"]
        for h in DET_H + ["t0_close", "t1_close", "t3_close"]:
            if isinstance(h, int) and h <= L:
                continue  # horizon must be after the latency anchor
            hp = detm[f"p_off{h}"] if isinstance(h, int) else detm[f"p_{h}"]
            m = np.where((aprice > 0) & (hp > 0), np.log(hp / aprice), np.nan)
            hn = f"det+{h}" if isinstance(h, int) else h
            part = pd.DataFrame({
                "ticker": detm.ticker, "event_date_canonical": detm.event_date_canonical, "mp": detm.mp,
                "latency": L, "horizon": hn, "det_bin": detm.det_bin, "era": detm.era, "markout": m,
            })
            rows.append(part)
    grid = pd.concat(rows, ignore_index=True)
    grid.to_parquet(OUT_GRID, index=False)

    # summary grid: latency x det_bin x horizon x era
    HORIZ = [f"det+{h}" for h in DET_H] + ["t0_close", "t1_close", "t3_close"]
    gsum = []
    for h in HORIZ:
        for era in ["era_2020_2021", "era_2022_2024"]:
            for L in LAT:
                for b in DET_BINS:
                    s = grid[(grid.horizon == h) & (grid.era == era) & (grid.latency == L)
                             & (grid.det_bin == b)]["markout"]
                    c = _cell(s); c.update({"horizon": h, "era": era, "latency": L, "det_bin": b,
                                            "thin": c["n"] < 100, "zero_latency_upper_bound": (L == 0)})
                    gsum.append(c)

    # flagship det+5 -> t0_close by det_bin (pooled era) and premarket separate
    fs = grid[(grid.latency == FLAGSHIP_L) & (grid.horizon == FLAGSHIP_H)]
    flagship_by_bin = {b: _cell(fs[fs.det_bin == b]["markout"]) for b in DET_BINS}
    premarket_row = {h: _cell(grid[(grid.latency == FLAGSHIP_L) & (grid.horizon == h) & (grid.det_bin == "premarket")]["markout"]) for h in HORIZ}

    summary = {
        "phase": "8", "task": "A10.2c",
        "source": "research/phase_8/a102c_grid.py:main",
        "scan_free": True,
        "detection_universe_n": int((~ev.det_undefined).sum()),
        "flagged_excluded_n": int(det["in_flagged_union"].sum()),
        "latency_offsets": LAT, "det_horizons": DET_H,
        "zero_latency_note": "det+0 is a physical impossibility; upper bound only",
        "flagship": f"det+{FLAGSHIP_L} -> {FLAGSHIP_H}",
        "flagship_by_detection_bin": flagship_by_bin,
        "premarket_detection_row_det5": premarket_row,
        "grid": gsum,
        "artifact": OUT_GRID,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "grid"}, indent=2, default=str))


if __name__ == "__main__":
    main()
