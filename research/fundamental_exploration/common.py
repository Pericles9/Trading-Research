"""
E1 shared plumbing: config load, DuckDB connection, the identity key.

Identity key: reused verbatim from research/phase_10/common.py:215, not re-derived --
the same string is already the de facto key across phase_10, phase_10e, phase_11,
scale_field and fundamentals_f1 (D30/reuse-before-build).

Detection price: NOT re-derived here. F1-T6 (research/fundamentals_f1/t6_prep_context.py)
already built a D4-compliant, tick-derived detection_price/detection_price_decile for all
20,951 events -- this package reads that artifact (t6_context.parquet) rather than
re-reading v2_r13_detection / a102_detection_anchors / first-trade fallback files itself.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import duckdb
import pandas as pd

from src.data.db import get_connection
from src.data.paths import resolve_data_root, resolve_duckdb_path

CFG = "config/fundamental_exploration.json"
ART = "results/fundamental_exploration/artifacts"
CHARTS = "results/fundamental_exploration/charts"
EVENT_FUNDAMENTALS_PATH = "data/fundamentals/event_fundamentals.parquet"

# D30/reuse-before-build: this universe's event key, matching research/phase_10/common.py
# and phase_10e/phase_11/scale_field/fundamentals_f1 exactly. Do not invent a second one.
COHORT_KEY = ["ticker", "event_date_canonical", "momentum_pct"]

# Reused verbatim from research/fundamentals_f1/common.py -- D15's own 20,951-row
# materialization of momentum_events_canonical WHERE in_scope=TRUE. A live SELECT against
# the view is pathologically slow regardless of projected columns (its staged construction
# joins filtered_trades/filtered_quotes for coverage flags unconditionally).
UNIVERSE_MATERIALIZATION_PATH = "results/phase_5/artifacts/quotes_bitmaps_all.parquet"
TARGET_ROW_COUNT = 20_951  # confirmed via UNIVERSE_MATERIALIZATION_PATH, not a live view scan

DETECTION_PRICE_PATH = "results/fundamentals_f1/artifacts/t6_context.parquet"
DETECTION_PRICE_FALLBACK_PATH = f"{ART}/detection_price.parquet"


def event_id(row) -> str:
    """Verbatim from research/phase_10/common.py:215 -- do not modify independently."""
    return f"{row['ticker']}_{row['event_date_canonical']}_{row['momentum_pct']:.2f}"


_EVENT_ID_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_(-?\d+\.\d{2})$")


def add_identity_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Adds event_date_canonical, momentum_pct, and year, parsed back out of event_id
    (the exact inverse of event_id() above) -- event_fundamentals.parquet carries
    ticker/t0_ns/t0_source directly but not the other two cohort-key fields. Used by
    every task from E1-T1 on; do not re-derive this regex per script."""
    df = df.copy()
    parsed = df["event_id"].apply(lambda eid: _EVENT_ID_RE.search(eid).groups())
    df["event_date_canonical"] = parsed.apply(lambda p: p[0])
    df["momentum_pct"] = parsed.apply(lambda p: float(p[1]))
    df["year"] = df["event_date_canonical"].str[:4]
    return df


def load_cfg() -> dict:
    with open(CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    """sha256[:12] of the committed config, newline-normalised so the hash is identical
    on LF and CRLF checkouts. Matches research/phase_9/common.py's convention."""
    b = pathlib.Path(CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """DuckDB connection via the shared src/data helpers -- resolve_duckdb_path's env
    override precedence (MOM_DB_DUCKDB_PATH > MOM_DB_DATABASE_ROOT > default) applies."""
    return get_connection(read_only=read_only)


def data_root() -> pathlib.Path:
    return pathlib.Path(resolve_data_root())


def duckdb_path() -> pathlib.Path:
    return pathlib.Path(resolve_duckdb_path())


def load_event_fundamentals() -> pd.DataFrame:
    return pd.read_parquet(EVENT_FUNDAMENTALS_PATH)


def load_detection_price() -> pd.DataFrame:
    """Prefers F1's own t6_context.parquet (a gitignored, regenerable F1 intermediate --
    present when Build F1's pipeline has been run end-to-end on this checkout). Falls back
    to this package's own detection_price.parquet (t0b_detection_price.py), which reuses
    F1-T6's tiering logic and its first_trade_price() function verbatim rather than
    re-deriving it -- see that script's docstring."""
    path = DETECTION_PRICE_PATH if pathlib.Path(DETECTION_PRICE_PATH).exists() else DETECTION_PRICE_FALLBACK_PATH
    return pd.read_parquet(path)[["event_id", "detection_price", "detection_price_decile"]]


def write_json(path: str, obj: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
