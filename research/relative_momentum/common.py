"""
R0 shared plumbing: config load, the identity key, the D1 population, and a
read-only re-implementation of the participation gate's own event-selection rule.

Nothing under scanner-epg-momentum/ is executed or imported from here. Section I.6
of the brief makes that repository read-only to this work, so its selection rule is
re-implemented over the shared archive rather than called.

Universe: NOT a live SELECT against momentum_events_canonical. That view joins
filtered_trades (4.9B rows) and filtered_quotes (3.8B rows) for its coverage flags
unconditionally, so any query against it scans both. Reused from
research/fundamental_exploration/common.py and config/fundamentals_f1.json
(reuse-before-build / D30).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pandas as pd

CFG = "config/relative_momentum_r0.json"
ART = "results/relative_momentum/r0/artifacts"
CHARTS = "charts/relative_momentum/r0"

REPO = pathlib.Path(__file__).resolve().parents[2]


def load_cfg() -> dict:
    with open(REPO / CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    """sha256[:12] of the committed config, newline-normalised so the hash is identical
    on LF and CRLF checkouts. Matches research/phase_9/common.py's convention."""
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def event_id(row) -> str:
    """Verbatim from research/phase_10/common.py:215 -- do not modify independently."""
    return f"{row['ticker']}_{row['event_date_canonical']}_{row['momentum_pct']:.2f}"


def load_universe() -> pd.DataFrame:
    """in_scope = TRUE, all source files (20,951 rows). Adds event_id and a
    string event_date_canonical."""
    cfg = load_cfg()
    u = pd.read_parquet(REPO / cfg["universe"]["materialization_path"]).copy()
    if pd.api.types.is_datetime64_any_dtype(u["event_date_canonical"]):
        u["event_date_canonical"] = u["event_date_canonical"].dt.strftime("%Y-%m-%d")
    u = u[["ticker", "event_date_canonical", "momentum_pct", "source_file"]].copy()
    u["event_id"] = u.apply(event_id, axis=1)
    u["year"] = u["event_date_canonical"].str[:4]
    return u


def load_d1() -> pd.DataFrame:
    """D1 = in_scope AND source_file = 'file1'."""
    u = load_universe()
    return u[u["source_file"] == "file1"].reset_index(drop=True)


# ---------------------------------------------------------------- gate side

_EVENT_RE = re.compile(
    r"^(?P<ticker>[A-Z0-9.p]+)_(?P<date>\d{4}-\d{2}-\d{2}|None)_(?P<mom>[\d.]+)$"
)


def parse_event_dir(name: str) -> dict | None:
    """Re-implemented from scanner-epg-momentum/backtest/data/loaders/trades.py
    ::parse_event_dir. Same regex, same semantics; the source is read-only to this
    brief so it is copied by value, not imported."""
    m = _EVENT_RE.match(name)
    if m is None:
        return None
    return {
        "ticker": m.group("ticker"),
        "date": m.group("date") if m.group("date") != "None" else None,
        "mom_pct": float(m.group("mom")),
        "dir_name": name,
    }


def gate_listable_events(min_mom: float = 50.0, require_date: bool = True) -> pd.DataFrame:
    """The participation gate's own admissible universe, re-implemented read-only.

    Mirrors scanner-epg-momentum/backtest/data/loaders/trades.py::list_events:
      folder-name parse, optional date requirement, mom_pct floor, trades.parquet present.
    Returns one row per admissible event folder, plus the rows the rule REJECTS and why,
    so the exclusion is a reported number rather than an absence.
    """
    cfg = load_cfg()
    filtered = REPO / cfg["gate"]["event_lister_rule"]["filtered_dir"]
    rows = []
    for d in sorted(filtered.iterdir()):
        if not d.is_dir():
            continue
        info = parse_event_dir(d.name)
        if info is None:
            rows.append({"dir_name": d.name, "ticker": None, "date": None, "mom_pct": None,
                         "admitted": False, "reject_reason": "folder_name_unparseable",
                         "has_trades": None, "has_quotes": None})
            continue
        has_trades = (d / "trades.parquet").exists()
        has_quotes = (d / "quotes.parquet").exists()
        reason = None
        if require_date and info["date"] is None:
            reason = "no_date_in_folder_name"
        elif info["mom_pct"] < min_mom:
            reason = f"mom_pct_below_{min_mom:g}"
        elif not has_trades:
            reason = "no_trades_parquet"
        rows.append({"dir_name": d.name, "ticker": info["ticker"], "date": info["date"],
                     "mom_pct": info["mom_pct"], "admitted": reason is None,
                     "reject_reason": reason, "has_trades": has_trades,
                     "has_quotes": has_quotes})
    df = pd.DataFrame(rows)
    df["event_id"] = [
        f"{t}_{d}_{m:.2f}" if t is not None and d is not None and m == m else None
        for t, d, m in zip(df["ticker"], df["date"], df["mom_pct"])
    ]
    return df


def gate_run_events() -> pd.DataFrame:
    """Every (ticker, date) the participation gate was actually RUN on, from every
    per_event_summary.json under the backtest results tree, with the gate-fire
    columns each run recorded. One row per (run_path, ticker, date)."""
    cfg = load_cfg()
    root = REPO / cfg["gate"]["run_result_roots"][0]
    keep = ["ticker", "date", "status", "n_pass_edges", "n_pass_windows",
            "n_trades_in_event", "n_event_trades", "mean_pass_window_sec",
            "median_pass_window_sec", "prev_close", "max_intraday_pct_session"]
    frames = []
    for p in sorted(root.rglob("per_event_summary.json")):
        try:
            d = json.load(open(p))
        except Exception as exc:  # corrupt/partial run output is reported, not skipped silently
            frames.append(pd.DataFrame([{"ticker": None, "date": None,
                                         "run_path": str(p.relative_to(REPO)),
                                         "load_error": str(exc)}]))
            continue
        if isinstance(d, dict):
            d = list(d.values())
        if not d:
            continue
        f = pd.DataFrame(d)
        for c in keep:
            if c not in f.columns:
                f[c] = pd.NA
        f = f[keep].copy()
        f["run_path"] = str(p.relative_to(REPO))
        frames.append(f)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=keep)
    out = out[out["ticker"].notna() & out["date"].notna()].copy()
    return out


def write_json(path: str, obj: dict) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
