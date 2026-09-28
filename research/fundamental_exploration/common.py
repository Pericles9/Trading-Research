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
import numpy as np
import pandas as pd

from src.data.db import get_connection
from src.data.paths import resolve_data_root, resolve_duckdb_path

CFG = "config/fundamental_exploration.json"
ART = "results/fundamental_exploration/artifacts"
CHARTS = "results/fundamental_exploration/charts"

# E2 nests under the same results/fundamental_exploration/ umbrella as E1 (per the brief's own
# "results/fundamental_exploration/e2/" path) -- "charts/fundamental_exploration/e2/" read literally
# would be a new top-level charts/ dir, which no phase or task in this repo has (same correction as
# E1's own SS7/SS8). Nested under e2/charts/ instead.
CFG_E2 = "config/fundamental_exploration_e2.json"
ART_E2 = "results/fundamental_exploration/e2/artifacts"
CHARTS_E2 = "results/fundamental_exploration/e2/charts"

# Part III (prompts/attention_excursion_b1.md; 2026-09-23) -- which participation-window artifact the E2
# duration pipeline reads. "" is the as-run window (the committed E2 results); "_units_fixed" is the
# corrected-units rebuild (e2_t2_window_units_fix.py). Every artifact, JSON and chart the duration
# pipeline writes carries the same suffix, so the as-run outputs are never overwritten.
import os as _os  # noqa: E402
E2_WINDOW_VARIANT = _os.environ.get("E2_WINDOW_VARIANT", "")


def ev(name: str) -> str:
    """Insert the window-variant suffix before a name's extension (or at its end if it has none)."""
    if not E2_WINDOW_VARIANT:
        return name
    stem, dot, ext = name.rpartition(".")
    if dot and "/" not in ext:
        return f"{stem}{E2_WINDOW_VARIANT}.{ext}"
    return f"{name}{E2_WINDOW_VARIANT}"


def e2_t3_summary() -> dict:
    """The T3 summary for the active window variant -- the source of every zero-share and censored
    figure a duration chart states, so no as-run number is hard-coded into a re-rendered chart."""
    with open(ev(f"{ART_E2}/e2_t3_describe_responses_summary.json")) as f:
        return json.load(f)


def zero_share_text(d: int = 0) -> str:
    s = e2_t3_summary()
    return f"{100 * s['n_zero_duration'] / s['n_with_window']:.{d}f}%"


def censored_text() -> str:
    s = e2_t3_summary()
    return (f"censored_share = {s['censored_share']:.2%} ({s['n_censored']:,} of {s['n_with_window']:,}); "
            "censored events have no duration and are excluded from duration statistics")
# Routed through resolve_data_root(), NOT a cwd-relative literal -- same bug class Build F1 found
# and fixed in its own common.py (2026-09-13, commit 369daab): a cwd-relative "data/..." literal
# silently resolves to the WRONG location if this code ever runs from a worktree other than the
# primary checkout (exactly what happened to F1's entire raw archive). CFG/ART/CHARTS above stay
# repo-relative on purpose -- they're tracked repo paths, not data-root paths.
EVENT_FUNDAMENTALS_PATH = str(pathlib.Path(resolve_data_root()) / "fundamentals" / "event_fundamentals.parquet").replace("\\", "/")

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

SHARE_COUNT_SUSPECT_THRESHOLD = 100_000  # descriptive diagnostic only, never a filter -- see
# add_corrected_shares_outstanding's docstring below


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


def load_cfg(path: str = CFG) -> dict:
    with open(path) as f:
        return json.load(f)


def cfg_hash(path: str = CFG) -> str:
    """sha256[:12] of the committed config, newline-normalised so the hash is identical
    on LF and CRLF checkouts. Matches research/phase_9/common.py's convention."""
    b = pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")
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


def add_corrected_shares_outstanding(df: pd.DataFrame) -> pd.DataFrame:
    """shs_shares_outstanding is as-filed, on whatever basis was in effect when the SEC
    filing itself was made (shs_asof_ns) -- if the nearest split strictly before t0
    (spl_last_split_ratio/spl_last_split_ns, research/fundamentals_f1/t5_assemble.py:
    165-169, ASOF, unbounded lookback) happened AFTER that filing's as-of date, the raw
    count is on the pre-split basis and needs multiplying by spl_last_split_ratio (ratio
    = new/old shares, ratio<1 = reverse per the same script's line 173) to read on the
    same basis as t0. If the filing came after the split (or no split is on record),
    the raw count is already correct as filed. Adds shs_shares_outstanding_corrected;
    never overwrites the raw column. Per the brief's own caveat (SS1): every task using
    the share count carries both columns, or states the cohort has no reverse split.

    Also flags shs_zero_artifact: 54 events (found while building E1-T4) carry
    shs_shares_outstanding == 0.0 exactly, all shs_quality=='filed_stale' -- a
    nonsensical value for any of these (real, operating) companies, and not caught by
    shs_quality's own enum (same class of gap as E1-T2's spl_quality finding: the
    quality label doesn't fully cover what "the data is unusable" means). Corrected
    value is set to NaN for these rows so a downstream ratio (E1-T4's turnover) divides
    by NaN, not 0 -- dividing by a literal 0 produced +inf and corrupted every summary
    statistic (mean, quantiles) in any cell that happened to contain one of them."""
    df = df.copy()
    df["shs_zero_artifact"] = df["shs_shares_outstanding"] == 0
    needs_correction = (
        df["spl_last_split_ns"].notna()
        & df["shs_asof_ns"].notna()
        & (df["shs_asof_ns"] < df["spl_last_split_ns"])
        & ~df["shs_zero_artifact"]
    )
    df["shs_shares_outstanding_corrected"] = df["shs_shares_outstanding"]
    df.loc[needs_correction, "shs_shares_outstanding_corrected"] = (
        df.loc[needs_correction, "shs_shares_outstanding"] * df.loc[needs_correction, "spl_last_split_ratio"]
    )
    df.loc[df["shs_zero_artifact"], "shs_shares_outstanding_corrected"] = np.nan
    df["shs_correction_applied"] = needs_correction

    # A second, broader problem (found in E1-T6): sorting the corrected column's
    # smallest nonzero values turns up 1, 1, 1, 12, 12, 17, 100 (x9), 1000 (x6),
    # 1440 (x9) -- implausible for real, actively-traded companies (one, LAES, trades
    # ~79M shares against a filed count of 100). Unlike the exact-zero case there is no
    # clean gap separating these from legitimate small microcap counts, so this is a
    # DIAGNOSTIC flag only (a stated round threshold, not a data-driven boundary) --
    # never used to exclude or correct anything. It exists so every consumer of this
    # column reports it consistently instead of each script picking its own cutoff.
    df["shs_share_count_suspect"] = (
        df["shs_shares_outstanding_corrected"].notna()
        & (df["shs_shares_outstanding_corrected"] < SHARE_COUNT_SUSPECT_THRESHOLD)
    )
    return df


def write_json(path: str, obj: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
