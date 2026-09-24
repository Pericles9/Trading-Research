"""
Attention and the excursion -- Brief 1 shared plumbing.

Brief: prompts/attention_excursion_b1.md (Part II). Config: config/attention_excursion_b1.json.

Everything here is instrument plumbing -- population, folder resolution, tick reading, the session
clock, the spike guard. No outcome is read by anything in this package.

Reuse, not re-derivation, wherever the repo already holds the construction:
  * segment assignment with the Amendment 6 {8, 15} override -- research/phase_10c/common.py
  * the D26 identity collapse                               -- research/scale_field/subsecond_origin.py
  * the one-sided (D23) kernel rate and the D22 coefficient  -- research/scale_field/scale_field.py
  * the split-corrected share count                         -- research/fundamental_exploration/common.py
  * halt labels                                              -- research/participation_exit_overlay/common.py
"""
from __future__ import annotations

import hashlib
import importlib.util as ilu
import json
import os
import pathlib
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

REPO = pathlib.Path(__file__).resolve().parents[2]
CFG = "config/attention_excursion_b1.json"
OUT = "results/attention_excursion/b1"
ART = f"{OUT}/artifacts"
CHARTS = "results/attention_excursion/b1/charts"

FILTERED = REPO / "data" / "filtered"
ET = "America/New_York"
NS = 1_000_000_000
MIN_NS = 60 * NS

D1_FRAME = "results/phase_5a/artifacts/sampling_frame.parquet"
SIDECAR = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
DEV = "config/dev_sample_v3.json"
PROXY = "results/relative_momentum/v1/artifacts/t5_d1_candidate_moments.parquet"
MB_CLOSE = "results/relative_momentum/r0/artifacts/t0a2_prior_close.parquet"
A12 = "results/phase_9/artifacts/t1_cross_session_flags.parquet"
FUNDAMENTALS = "data/fundamentals/event_fundamentals.parquet"

TRADE_COLS = ["sip_timestamp", "sequence_number", "price", "size", "exchange", "conditions"]


def load_cfg() -> dict:
    with open(REPO / CFG, encoding="utf-8") as f:
        return json.load(f)


def cfg_hash() -> str:
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def write_json(path: str, obj) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def art(name: str) -> pathlib.Path:
    p = REPO / ART / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def chart_path(task: str, name: str) -> pathlib.Path:
    p = REPO / CHARTS / task / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ------------------------------------------------------------------ population

def _folder_index() -> dict[str, str]:
    """(ticker_date) -> folder name. Checked before use: no D1 event has two folders."""
    out: dict[str, str] = {}
    for name in os.listdir(FILTERED):
        parts = name.split("_")
        if len(parts) < 3:
            continue
        out.setdefault(f"{parts[0]}_{parts[1]}", name)
    return out


def load_d1() -> pd.DataFrame:
    """D1 = in_scope AND file1, from Phase 5a's materialised frame (never a live SELECT on the
    canonical view, which joins the 4.9B/3.8B-row tables). event_id = the event's folder name, the
    same key Build F1's event_fundamentals uses."""
    d = pd.read_parquet(REPO / D1_FRAME, columns=["ticker", "event_date_canonical", "momentum_pct", "source_file"])
    d["event_date_canonical"] = pd.to_datetime(d["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    idx = _folder_index()
    d["event_id"] = (d["ticker"] + "_" + d["event_date_canonical"]).map(idx)
    return d


def load_dev() -> pd.DataFrame:
    ev = json.load(open(REPO / DEV))["events"]
    d = pd.DataFrame(ev).rename(columns={"date": "event_date_canonical"})
    d["event_date_canonical"] = pd.to_datetime(d["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    return d[["ticker", "event_date_canonical"]]


def load_sidecar() -> pd.DataFrame:
    d = pd.read_parquet(REPO / SIDECAR, columns=["ticker", "event_date_canonical"])
    d["event_date_canonical"] = pd.to_datetime(d["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    return d


def folder_path(event_id: str) -> pathlib.Path:
    return FILTERED / event_id


# ------------------------------------------------------------------ session clock

def et_ns(date_str: str, hhmmss: str) -> int:
    """Wall-clock ET on a date, in epoch ns, DST resolved by the tz database."""
    return int(pd.Timestamp(f"{date_str} {hhmmss}", tz=ET).tz_convert("UTC").value)


def day_bounds_ns(date_str: str) -> tuple[int, int]:
    """[00:00 ET, next 00:00 ET) for the calendar date."""
    lo = et_ns(date_str, "00:00:00")
    hi = int((pd.Timestamp(date_str, tz=ET) + pd.Timedelta(days=1)).tz_convert("UTC").value)
    return lo, hi


_CAL = None


def xnys():
    global _CAL
    if _CAL is None:
        import exchange_calendars as xcals
        _CAL = xcals.get_calendar("XNYS")
    return _CAL


def prior_session(date_str: str) -> str:
    return str(xnys().previous_session(pd.Timestamp(date_str)).date())


def rth_bounds_ns(date_str: str) -> tuple[int, int]:
    cal = xnys()
    s = pd.Timestamp(date_str)
    return int(cal.session_open(s).value), int(cal.session_close(s).value)


# ------------------------------------------------------------------ tick reading

def read_trades(event_id: str, with_conditions: bool = True) -> dict | None:
    """All prints in an event folder (trades.parquet + trades_repair_1c.parquet when present),
    sorted by (sip_timestamp, sequence_number). Timestamps stay int64 throughout.

    Returns dict of numpy arrays; 'conditions' is kept as a pyarrow ListArray aligned to the sorted
    order so code membership can be tested without materialising Python lists."""
    folder = folder_path(event_id)
    files = [folder / "trades.parquet", folder / "trades_repair_1c.parquet"]
    tables = []
    for f in files:
        if not f.exists():
            continue
        schema_names = pq.read_schema(f).names
        cols = [c for c in TRADE_COLS if c in schema_names and (with_conditions or c != "conditions")]
        t = pq.read_table(f, columns=cols)
        if "sequence_number" not in t.column_names:
            t = t.append_column("sequence_number", pa.array(np.zeros(t.num_rows, dtype=np.int64)))
        if with_conditions and "conditions" not in t.column_names:
            t = t.append_column("conditions", pa.nulls(t.num_rows, pa.list_(pa.int64())))
        t = t.select([c for c in TRADE_COLS if c in t.column_names])
        # one schema across trades.parquet and its repair sibling (size is int64 in some files and
        # double in others; concat refuses to merge them)
        want = {"sip_timestamp": pa.int64(), "sequence_number": pa.int64(), "price": pa.float64(),
                "size": pa.float64(), "exchange": pa.int64(), "conditions": pa.list_(pa.int64())}
        for c in t.column_names:
            if t.schema.field(c).type != want[c]:
                t = t.set_column(t.column_names.index(c), c, t.column(c).cast(want[c]))
        tables.append(t)
    if not tables:
        return None
    t = pa.concat_tables(tables, promote_options="default") if len(tables) > 1 else tables[0]
    if t.num_rows == 0:
        return None
    ts = t.column("sip_timestamp").to_numpy().astype(np.int64)
    seq = t.column("sequence_number").to_numpy(zero_copy_only=False)
    seq = np.nan_to_num(seq.astype(np.float64), nan=0).astype(np.int64)
    order = np.lexsort((seq, ts))
    out = {
        "ts": ts[order],
        "seq": seq[order],
        "px": t.column("price").to_numpy(zero_copy_only=False).astype(np.float64)[order],
        "sz": np.nan_to_num(t.column("size").to_numpy(zero_copy_only=False).astype(np.float64))[order],
        "n_repair_rows": int(tables[1].num_rows) if len(tables) > 1 else 0,
    }
    if "exchange" in t.column_names:
        out["ex"] = np.nan_to_num(t.column("exchange").to_numpy(zero_copy_only=False).astype(np.float64), nan=-1).astype(np.int64)[order]
    if with_conditions:
        cond = t.column("conditions").combine_chunks()
        out["cond"] = cond.take(pa.array(order))
    return out


def rows_with_codes(cond: pa.ListArray, codes: set[int], idx: np.ndarray | None = None) -> np.ndarray:
    """Boolean mask over rows (or over `idx`) whose condition list contains any of `codes`."""
    sub = cond if idx is None else cond.take(pa.array(idx))
    n = len(sub)
    if n == 0:
        return np.zeros(0, dtype=bool)
    flat = pc.list_flatten(sub)
    parents = pc.list_parent_indices(sub).to_numpy()
    hit = np.isin(flat.to_numpy(zero_copy_only=False), list(codes))
    mask = np.zeros(n, dtype=bool)
    mask[parents[hit]] = True
    return mask


def codes_at(cond: pa.ListArray, i: int) -> list[int]:
    v = cond[i].as_py()
    return [int(x) for x in v] if v else []


# ------------------------------------------------------------------ spike guard

def is_spike(px: np.ndarray, i: int, dev: float, agree: float) -> bool:
    """A print deviating by more than `dev` from BOTH immediate neighbours, whose neighbours agree
    with each other within `agree`. A print with no successor (or predecessor) is not a spike."""
    n = px.size
    if i <= 0 or i >= n - 1:
        return False
    prev, cur, nxt = px[i - 1], px[i], px[i + 1]
    if prev <= 0 or nxt <= 0:
        return False
    return bool(abs(cur - prev) / prev > dev and abs(cur - nxt) / nxt > dev
                and abs(prev - nxt) / max(prev, nxt) <= agree)


def first_crossing(px: np.ndarray, lo_idx: int, hi_idx: int, level: float,
                   dev: float | None, agree: float | None) -> tuple[int | None, int]:
    """First index in [lo_idx, hi_idx) with px >= level that is not a spike. Returns
    (index or None, number of spikes skipped). dev=None disables the guard."""
    cand = lo_idx + np.flatnonzero(px[lo_idx:hi_idx] >= level)
    skipped = 0
    for i in cand:
        if dev is not None and is_spike(px, int(i), dev, agree):
            skipped += 1
            continue
        return int(i), skipped
    return None, skipped


# ------------------------------------------------------------------ reused constructions

def _load_module(name: str, rel_path: str):
    spec = ilu.spec_from_file_location(name, str(REPO / rel_path))
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_P10C = None


def _extract(rel_path: str, names: set[str], seed: dict | None = None) -> dict:
    """Execute only the named top-level definitions of a repo file, verbatim from its own source.
    Used where importing the whole module would drag in an unrelated module-level import chain
    (phase_10c/common.py does `from common import ...` against phase_10's package, which collides
    with this package's own `common`)."""
    import ast
    src = (REPO / rel_path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = [n for n in tree.body
            if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    missing = names - {getattr(n, "name", None) or n.targets[0].id for n in keep}
    assert not missing, f"{rel_path}: {missing} not found"
    ns: dict = {"np": np, **(seed or {})}
    exec(compile(ast.Module(body=keep, type_ignores=[]), rel_path, "exec"), ns)
    return ns


def assign_segment(ts: int, codes, open_ns: int, close_ns: int) -> str:
    """research/phase_10c/common.py::assign_segment (Amendment 6 {8,15} override), executed from
    that file's own source. Its labels are evening / premarket / rth; 'evening' after the close is
    reported here as 'post'."""
    global _P10C
    if _P10C is None:
        _P10C = _extract("research/phase_10c/common.py", {"CLOSING_PRINT_CODES", "assign_segment"})
    seg = _P10C["assign_segment"](ts, codes, open_ns, close_ns)
    return "post" if seg == "evening" else seg


_SO = None
_SF = None


def collapse_tol(ts_ns: np.ndarray, tol_ms: float) -> np.ndarray:
    """research/scale_field/subsecond_origin.py::collapse_tol -- the D26 identity collapse -- executed
    from that file's own source together with scale_field.py::collapse_same_timestamp, which it calls.
    Importing subsecond_origin as a module drags in scale_field/adapter.py's `from common import ...`,
    which collides with this package's own `common`."""
    global _SO
    if _SO is None:
        ns = _extract("research/scale_field/scale_field.py", {"collapse_same_timestamp"})
        so = _extract("research/scale_field/subsecond_origin.py", {"collapse_tol"},
                      {"collapse_same_timestamp": ns["collapse_same_timestamp"]})
        _SO = so
    return _SO["collapse_tol"](np.asarray(ts_ns, dtype=np.int64), tol_ms)


def scale_field():
    global _SF
    if _SF is None:
        sys.path.insert(0, str(REPO / "research" / "scale_field"))
        import scale_field as sf  # noqa: E402
        _SF = sf
    return _SF


def load_fundamentals_corrected() -> pd.DataFrame:
    """event_fundamentals with E1's split-corrected share count and suspect flag added."""
    sys.path.insert(0, str(REPO))
    from research.fundamental_exploration.common import add_corrected_shares_outstanding  # noqa: E402
    ef = pd.read_parquet(REPO / FUNDAMENTALS)
    return add_corrected_shares_outstanding(ef)


def load_halt_labels() -> dict:
    sys.path.insert(0, str(REPO))
    from research.participation_exit_overlay.common import load_halt_labels as lhl  # noqa: E402
    return lhl()
