"""
Build F1 shared plumbing: config load, DuckDB connection, the identity key, and the
tiered t0 anchor.

Identity key: reused verbatim from research/phase_10/common.py:event_id, not
re-derived -- the same string is already the de facto key across phase_10, phase_10e,
phase_11 and scale_field (D30/reuse-before-build).

t0: per docs/Universe-Decisions.md D33, no spine or view column named t0 exists, and no
single existing detection artifact covers the ~20,951-event universe at one precision.
t0_spine.parquet (built by t0_assemble.py, not this module) is the tiered construction;
every other script in this package reads it rather than re-deriving t0.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import duckdb
import pandas as pd

from src.data.db import get_connection
from src.data.paths import resolve_data_root, resolve_duckdb_path

CFG = "config/fundamentals_f1.json"
ART = "results/fundamentals_f1/artifacts"
CHARTS = "results/fundamentals_f1/charts"
# Routed through resolve_data_root(), NOT a cwd-relative literal -- CLAUDE.md's data root is a
# single shared location (E:\Trading Research\data) regardless of which worktree code runs from.
# Fixed 2026-09-13 after discovering the entire Build F1 raw archive and event_fundamentals.parquet
# had been silently written to this worktree's own local data/ folder instead (same bug class as
# t0_assemble.py's FILTERED_ROOT, fixed 2026-09-12) -- migrated the data to the canonical root and
# fixed every script that had its own hardcoded "data/..." literal, not just these two constants.
RAW_ROOT = str(pathlib.Path(resolve_data_root()) / "raw" / "fundamentals").replace("\\", "/")
NORMALIZED_ROOT = str(pathlib.Path(resolve_data_root()) / "fundamentals").replace("\\", "/")

# D33 tier artifacts, read-only inputs to t0_assemble.py -- never re-derived elsewhere.
NANOSECOND_ANCHOR_PATH = "results/phase_10/artifacts/v2_r13_detection.parquet"
MINUTE_ANCHOR_PATH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
UNIVERSE_MATERIALIZATION_PATH = "results/phase_5/artifacts/quotes_bitmaps_all.parquet"

# D30/reuse-before-build: this universe's event key, matching research/phase_10/common.py
# and phase_10e/phase_11/scale_field exactly. Do not invent a second convention.
COHORT_KEY = ["ticker", "event_date_canonical", "momentum_pct"]

TARGET_ROW_COUNT = 20_951  # confirmed via UNIVERSE_MATERIALIZATION_PATH, not a live view scan


def event_id(row) -> str:
    """Verbatim from research/phase_10/common.py:215 -- do not modify independently."""
    return f"{row['ticker']}_{row['event_date_canonical']}_{row['momentum_pct']:.2f}"


def load_cfg() -> dict:
    with open(CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    """sha256[:12] of the committed config, newline-normalised so the hash is
    identical on LF and CRLF checkouts. Matches research/phase_9/common.py's convention."""
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


def load_massive_api_key() -> str:
    """Read from .secrets/polygon_api_key.txt, exactly as research/phase_1b's
    fetch_ticker_reference.py does. Never print, log, or write this into any artifact."""
    with open(".secrets/polygon_api_key.txt") as f:
        return f.read().strip()


def build_cik_identity_map() -> pd.DataFrame:
    """One row per resolved CIK, with a representative ticker -- the most frequent ticker
    string F1-T1 mapped to it. Shared by every F1-Tn script that pulls per-CIK (F1-T2,
    F1-T3, F1-T4); do not re-derive independently per script."""
    spine = pd.read_parquet(f"{ART}/ticker_identity.parquet")
    resolved = spine.dropna(subset=["cik"])
    rep = (resolved.groupby(["cik", "ticker"]).size().reset_index(name="n")
           .sort_values("n", ascending=False).drop_duplicates(subset="cik"))
    return rep[["cik", "ticker"]].reset_index(drop=True)


def write_json(path: str, obj: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
