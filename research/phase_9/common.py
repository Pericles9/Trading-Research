"""
Phase 9 shared loaders and guards.

Read-only phase (escalation row 2): the ONLY table touched is
event_minute_bars_v2. Everything else comes from frozen Phase 6b / Phase 8
artifacts. No spine numeric column (momentum_events OHLC/volume) enters any
computation path (escalation row 3) - `momentum_pct` appears here solely as
part of the composite join key, rounded to 2dp, exactly as Phase 6b/8 keyed
their artifacts. It is never an operand.

Session-close convention, inherited verbatim from Phase 8 T4: the close of
session offset k is `last_price` of the bar with the greatest minute_index on
that session (extended day, any segment) - i.e. last trade at/before
minute_index 959. Sessions absent from v2 are `has_t{k}` FALSE and carry a
NULL close; never imputed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

CFG = "config/phase_9.json"
ART = "results/phase_9/artifacts"
CHARTS = "results/phase_9/charts"

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
ANCHOR6B = "results/phase_6b/artifacts/opportunity_decay_primary.parquet"
DET_PATH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
CONTAM_PATH = "results/phase_8/artifacts/a102_contamination.parquet"
T3_PART_PATH = "results/phase_8/artifacts/t3_participation.parquet"

KEY = ["ticker", "event_date_canonical", "mp"]
ERA_BOUNDARY = pd.Timestamp("2022-01-01")
ERAS = ["era_2020_2021", "era_2022_2024"]
OFFSETS = [-1, 0, 1, 2, 3]
V2_ROW_PIN = 45_925_350

# session-pair label -> (earlier offset, later offset)
PAIRS = {"tm1_t0": (-1, 0), "t0_t1": (0, 1), "t0_t2": (0, 2), "t0_t3": (0, 3)}
HORIZON_OFFSET = {"t0_close": 0, "t1_close": 1, "t2_close": 2, "t3_close": 3}


def load_cfg() -> dict:
    with open(CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    """sha256[:12] of the committed config, newline-normalised so the hash is
    identical on LF and CRLF checkouts."""
    b = pathlib.Path(CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def caption(sample: str, filters: str) -> str:
    return f"sample: {sample} · filters: {filters} · config {cfg_hash()} · Phase 9"


def connect():
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    n = con.execute("SELECT COUNT(*) FROM event_minute_bars_v2").fetchone()[0]
    if n != V2_ROW_PIN:
        raise SystemExit(
            f"ESCALATION ROW 4 - event_minute_bars_v2 row count {n:,} != {V2_ROW_PIN:,}. HARD STOP."
        )
    return con


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    df["event_date_canonical"] = pd.to_datetime(df["event_date_canonical"])
    return df


def era_of(dates: pd.Series) -> pd.Series:
    return pd.Series(
        np.where(pd.to_datetime(dates) < ERA_BOUNDARY, ERAS[0], ERAS[1]), index=dates.index
    )


def d1_frame() -> pd.DataFrame:
    """Frozen D1 (n=15,763): identity columns + era only. Not re-derived."""
    d1 = _norm(pd.read_parquet(D1_PATH))
    d1["mp"] = d1["momentum_pct"].round(2)
    d1 = d1[KEY].drop_duplicates().reset_index(drop=True)
    d1["era"] = era_of(d1["event_date_canonical"])
    return d1


def anchor6b() -> pd.DataFrame:
    """Frozen 6b tick anchor: A = tick_close_t_minus_1_rth, H = day_high_ext.
    Both tick-derived and D4-clean (a62_d4_sweep: 0 measurement-path spine hits)."""
    a = _norm(pd.read_parquet(ANCHOR6B))
    a["mp"] = a["momentum_pct"].round(2)
    return a[KEY + ["tick_close_t_minus_1_rth", "day_high_ext",
                    "has_t_minus_1_rth", "denom_nonpositive"]]


def detection_anchors() -> pd.DataFrame:
    """Frozen Phase 8 A10.2 detection anchors (det_undefined marks the 394)."""
    d = _norm(pd.read_parquet(DET_PATH))
    return d


def session_closes(con, d1: pd.DataFrame) -> pd.DataFrame:
    """Per (event, session_offset in -1..3): close price, last minute_index,
    n bars. Long format. Missing sessions simply have no row."""
    con.register("d1k", d1[KEY])
    con.execute("DROP TABLE IF EXISTS p9bars")
    con.execute(
        f"""
        CREATE TEMP TABLE p9bars AS
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp,
               b.session_offset, b.minute_index, b.last_price, b.high, b.volume
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker = d1k.ticker
                AND b.event_date_canonical = d1k.event_date_canonical
                AND ROUND(b.momentum_pct,2) = d1k.mp
        WHERE b.session_offset IN ({','.join(str(o) for o in OFFSETS)})
        """
    )
    cl = con.execute(
        """
        SELECT ticker, event_date_canonical, mp, session_offset,
               MAX(minute_index) AS last_mi,
               COUNT(*) AS n_bars,
               ARG_MAX(last_price, minute_index) AS close_price
        FROM p9bars
        GROUP BY 1,2,3,4
        """
    ).fetchdf()
    return _norm(cl)


def closes_wide(con, d1: pd.DataFrame) -> pd.DataFrame:
    """One row per event, columns close_tm1/close_t0/close_t1/close_t2/close_t3
    (+ last_mi_t0). NaN = session absent from v2, carried, never imputed."""
    cl = session_closes(con, d1)
    lab = {-1: "tm1", 0: "t0", 1: "t1", 2: "t2", 3: "t3"}
    cl["lab"] = cl["session_offset"].map(lab)
    px = cl.pivot_table(index=KEY, columns="lab", values="close_price", aggfunc="first")
    px.columns = [f"close_{c}" for c in px.columns]
    mi = cl.pivot_table(index=KEY, columns="lab", values="last_mi", aggfunc="first")
    mi.columns = [f"last_mi_{c}" for c in mi.columns]
    out = d1.merge(px.reset_index(), on=KEY, how="left").merge(mi.reset_index(), on=KEY, how="left")
    for c in ["close_tm1", "close_t0", "close_t1", "close_t2", "close_t3"]:
        if c not in out:
            out[c] = np.nan
    return out


def q(s: pd.Series, p: float):
    s = s.dropna()
    return float(s.quantile(p)) if len(s) else None


def cell_stats(markout: pd.Series) -> dict:
    """Full statistic set for a T2/T4 cell. `markout` is a signed LOG return;
    mean_simple is the mean of exp(r)-1 (the statistic that sign-flipped in
    the Phase 8 inspection)."""
    s = pd.Series(markout).dropna()
    n = int(len(s))
    if n == 0:
        return {"n": 0, "median": None, "mean_log": None, "mean_simple": None,
                "iqr": [None, None], "q01": None, "q05": None, "q95": None,
                "q99": None, "share_gt_0": None}
    return {
        "n": n,
        "median": float(s.median()),
        "mean_log": float(s.mean()),
        "mean_simple": float(np.expm1(s).mean()),
        "iqr": [q(s, 0.25), q(s, 0.75)],
        "q01": q(s, 0.01), "q05": q(s, 0.05),
        "q95": q(s, 0.95), "q99": q(s, 0.99),
        "share_gt_0": float((s > 0).mean()),
    }


def trimmed_mean_simple(markout: pd.Series, lo: float, hi: float):
    """Mean simple return over pairs whose price ratio exp(r) is inside
    [lo, hi]. Returns (value, n_kept)."""
    s = pd.Series(markout).dropna()
    ratio = np.exp(s)
    keep = s[(ratio >= lo) & (ratio <= hi)]
    return (float(np.expm1(keep).mean()) if len(keep) else None), int(len(keep))


def write_json(obj, path: str):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    print(f"wrote {path}")
