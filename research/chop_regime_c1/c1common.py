"""
Chop regime C1 -- shared plumbing. A build, an instrument check and an interactive suite; nothing here fits,
tunes or selects (Cooper sets the filter by eye after the stop).

Brief: prompts/chop_regime_c1.md. Config: config/chop_regime_c1.json (committed before any run).

Measurement reuses the programme's instrument unchanged wherever it exists: tick reading, the session clock and
segments, the D26 collapse and the spike rule from Brief 1 (research/attention_excursion_b1/common.py), b2's R1 rate
ladder (research/attention_excursion_b2/b2common.py::a2_ladder_r1), S1's tie tolerance, and S2's tau_d, V_pre,
tau-anchored share count and causal tau_close_sensitive state (research/shape_classifier_s2/). This module adds the
event's tape and quote book, sliced per moment so that nothing after t can reach a measure.

Naming: B1 = Brief 1's common module (S2 and S1 call it C1; here C1 is this brief).
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

_S2 = pathlib.Path(__file__).resolve().parents[1] / "shape_classifier_s2"
if str(_S2) not in sys.path:
    sys.path.insert(0, str(_S2))
import s2common as S2  # noqa: E402

B1, I, B2, S1 = S2.C1, S2.I, S2.B2, S2.S1
REPO = S2.REPO
CFG = "config/chop_regime_c1.json"
OUT = "results/chop_regime/c1"
ART = f"{OUT}/artifacts"
CHARTS = f"{OUT}/charts"
SUITE = f"{OUT}/suite"
NS = B1.NS
MIN_NS = B1.MIN_NS
SEGS = ("premarket", "regular", "after_hours")
SEG_CODE = {"premarket": 0, "regular": 1, "after_hours": 2, "auction_open": 3, "auction_close": 4}
P11_SEGS = ("premarket", "rth", "post")
HORIZONS = ["w5", "w15", "w60", "v025", "v05", "v1"]
WALL = {"w5": 5, "w15": 15, "w60": 60}
VOL = {"v025": 0.25, "v05": 0.5, "v1": 1.0}
BASES = ("mid", "vwap")
TIE_TOL = math.log1p(1e-9)
CAUSAL_MSG = "data after t reached a C1 measure"
SEGMENT_MSG = "C1 window leaves t's clock segment"
TOL_MS = 10.0
HALT_GAP_NS = 300 * NS
REM_TIMES = {"tau": 0, "w1": 1, "w2": 2, "w5": 5, "w10": 10, "w20": 20}


def load_cfg() -> dict:
    with open(REPO / CFG, encoding="utf-8") as f:
        return json.load(f)


def cfg_hash() -> str:
    return hashlib.sha256((REPO / CFG).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def art(name: str) -> pathlib.Path:
    p = REPO / ART / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def chart_path(task: str, name: str) -> pathlib.Path:
    p = REPO / CHARTS / task / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def src(key: str) -> pathlib.Path:
    return REPO / load_cfg()["sources"][key]


def write_json(name: str, obj) -> None:
    B1.write_json(f"{ART}/{name}", obj)


def read_json(name: str) -> dict:
    return json.load(open(art(name), encoding="utf-8"))


def as_int64(s: pd.Series) -> pd.Series:
    return S2.as_int64(s)


# ------------------------------------------------------------------ population

def load_population() -> pd.DataFrame:
    """Every event C1 builds: the development slice and the 56 quarantined events, with tau available.

    tau = S2's tau_d (c__tau_d_ns in t1_group_a): max(stored tau, the crossing print), the decision time S2 used for
    its entries. V_pre = S2's ref_shares. The share count is S2's tau-anchored, split-corrected count."""
    cfg = load_cfg()
    sl = pd.read_parquet(src("slices"))
    ga = pd.read_parquet(src("s2_group_a"), columns=[
        "event_id", "segment", "price_tier", "c__tau_ns", "c__tau_exact_ns", "c__tau_d_ns", "c__tau_price", "c__ticker", "c__year",
        "c__event_date_canonical", "c__ref_shares", "c__shs_tau_corrected", "c__shs_tau_asof_ns", "c__shs_tau_accepted_ns",
        "c__dilution_tau", "c__cik"])
    for c in ("c__tau_ns", "c__tau_exact_ns", "c__tau_d_ns"):
        assert str(ga[c].dtype) in ("int64", "Int64"), f"{c} is {ga[c].dtype}, not int64"
    meta = pd.read_parquet(src("s2_event_meta"), columns=["event_id", "tau_mb_exact_ns", "n_day_prints", "last_print_ns"])
    s1 = pd.read_parquet(src("s1_events"), columns=["event_id", "event_index"])
    fu = pd.read_parquet(src("fundamentals"), columns=["event_id", "shs_quality"])
    d = sl.merge(ga, on="event_id", how="inner").merge(meta, on="event_id", how="left").merge(s1, on="event_id", how="left") \
        .merge(fu, on="event_id", how="left")
    d = d[d["slice"].isin(["development", "dev_quarantine"])].copy()
    d = d.rename(columns={"c__tau_d_ns": "tau_ns", "c__tau_exact_ns": "tau_exact_ns", "c__tau_ns": "tau_stored_ns", "c__tau_price": "tau_price",
                          "c__year": "year", "c__ref_shares": "v_pre", "c__shs_tau_corrected": "shs", "c__shs_tau_asof_ns": "shs_asof_ns",
                          "c__shs_tau_accepted_ns": "shs_accepted_ns", "c__dilution_tau": "dilution", "c__cik": "cik", "segment": "tau_segment"})
    d["event_date_canonical"] = pd.to_datetime(d["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    assert (d["event_date_canonical"] == pd.to_datetime(d["c__event_date_canonical"]).dt.strftime("%Y-%m-%d")).all()
    assert (d["ticker"] == d["c__ticker"]).all()
    d = d.drop(columns=["c__event_date_canonical", "c__ticker"])
    for c in ("tau_ns", "tau_exact_ns", "tau_stored_ns"):
        d[c] = d[c].astype("int64")
    for c in ("shs_asof_ns", "shs_accepted_ns", "tau_mb_exact_ns", "last_print_ns"):
        d[c] = as_int64(d[c])
    # D15: Phase 11's quotes_ingested join (ticker, event_date_canonical, round(momentum_pct, 2)); momentum_pct is read
    # from the folder name as a join key only (D4)
    qs = pd.read_parquet(src("quotes_coverage_d15"))
    qs["event_date_canonical"] = pd.to_datetime(qs["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    qs["session_date"] = pd.to_datetime(qs["session_date"]).dt.strftime("%Y-%m-%d")
    key = qs["ticker"] + "|" + qs["event_date_canonical"] + "|" + qs["mom_2dp"].round(2).map(lambda v: f"{v:.2f}")
    mp = d["event_id"].str.rsplit("_", n=1).str[1].astype(float).round(2).map(lambda v: f"{v:.2f}")
    dkey = d["ticker"] + "|" + d["event_date_canonical"] + "|" + mp
    d["quotes_ingested"] = dkey.isin(set(key))
    d["quotes_event_day"] = dkey.isin(set(key[qs["session_date"] == qs["event_date_canonical"]]))
    d = d.sort_values("event_id").reset_index(drop=True)
    assert d["tau_ns"].dtype == np.int64
    return d


def dev_slice(pop: pd.DataFrame) -> pd.DataFrame:
    return pop[pop["slice"] == "development"].reset_index(drop=True)


def quarantine(pop: pd.DataFrame) -> pd.DataFrame:
    return pop[pop["slice"] == "dev_quarantine"].reset_index(drop=True)


# ------------------------------------------------------------------ quotes

QUOTE_COLS = ["sip_timestamp", "sequence_number", "bid_price", "ask_price", "bid_size", "ask_size"]


def read_quotes(event_id: str) -> dict | None:
    """quotes.parquet + quotes_repair_1c.parquet, sorted by (sip_timestamp, sequence_number) -- D16's order."""
    folder = B1.folder_path(event_id)
    tabs = []
    for f in (folder / "quotes.parquet", folder / "quotes_repair_1c.parquet"):
        if not f.exists():
            continue
        names = pq.read_schema(f).names
        t = pq.read_table(f, columns=[c for c in QUOTE_COLS if c in names])
        want = {"sip_timestamp": pa.int64(), "sequence_number": pa.int64(), "bid_price": pa.float64(), "ask_price": pa.float64(),
                "bid_size": pa.float64(), "ask_size": pa.float64()}
        if "sequence_number" not in t.column_names:
            t = t.append_column("sequence_number", pa.array(np.zeros(t.num_rows, dtype=np.int64)))
        t = t.select(QUOTE_COLS)
        for c in t.column_names:
            if t.schema.field(c).type != want[c]:
                t = t.set_column(t.column_names.index(c), c, t.column(c).cast(want[c]))
        tabs.append(t)
    if not tabs:
        return None
    t = pa.concat_tables(tabs) if len(tabs) > 1 else tabs[0]
    if t.num_rows == 0:
        return None
    ts = t.column("sip_timestamp").to_numpy().astype(np.int64)
    seq = np.nan_to_num(t.column("sequence_number").to_numpy(zero_copy_only=False).astype(np.float64), nan=0).astype(np.int64)
    o = np.lexsort((seq, ts))
    g = lambda c: t.column(c).to_numpy(zero_copy_only=False).astype(np.float64)[o]  # noqa: E731
    return {"ts": ts[o], "seq": seq[o], "bid": g("bid_price"), "ask": g("ask_price"), "bsz": g("bid_size"), "asz": g("ask_size")}


def d17_excluded(bid, ask, bsz, asz) -> np.ndarray:
    """D17: crossed, null or non-positive price, a side missing, or a null or zero size. Locked (bid = ask) is carried."""
    with np.errstate(invalid="ignore"):
        return (~np.isfinite(bid) | ~np.isfinite(ask) | (bid <= 0) | (ask <= 0) | ~np.isfinite(bsz) | ~np.isfinite(asz)
                | (bsz <= 0) | (asz <= 0) | (bid > ask))


class QuoteBook:
    """The event day's quotes per Phase 11 segment (premarket [04:00, open), rth [open, close), post [close, 20:00)).

    Per segment: all rows (for Phase 11's time weighting, where every row lasts until the next row and excluded rows'
    time is dropped) and the D17-valid rows (for the D16 ASOF quote and the BBO-change marker). Prefix integrals are
    causal: the integral up to row r uses only timestamps <= ts[r]. `view(t)` returns the rows at or before t."""

    def __init__(self, q: dict | None, date: str, size_mult: float | None):
        op, cl = B1.rth_bounds_ns(date)
        self.bounds = [B1.et_ns(date, "04:00:00"), op, cl, B1.et_ns(date, "20:00:00")]
        self.size_mult = size_mult
        self.seg = []
        for g in range(3):
            lo, hi = self.bounds[g], self.bounds[g + 1]
            if q is None:
                self.seg.append(None)
                continue
            a, b = int(np.searchsorted(q["ts"], lo, "left")), int(np.searchsorted(q["ts"], hi, "left"))
            ts, bid, ask, bsz, asz = (q[k][a:b] for k in ("ts", "bid", "ask", "bsz", "asz"))
            exc = d17_excluded(bid, ask, bsz, asz)
            val = ~exc
            mid = np.where(val, (bid + ask) / 2.0, np.nan)
            spr = np.where(val, ask - bid, 0.0)
            sbp = np.where(val, 1e4 * spr / np.where(val, mid, 1.0), 0.0)
            nxt = np.r_[ts[1:], hi] if ts.size else ts
            dur = (np.minimum(nxt, hi) - ts).astype(np.float64)
            vd = np.where(val, dur, 0.0)
            vi = np.flatnonzero(val)
            vts, vb, va = ts[vi], bid[vi], ask[vi]
            chg = np.r_[True, (vb[1:] != vb[:-1]) | (va[1:] != va[:-1])] if vi.size else np.zeros(0, dtype=bool)
            self.seg.append({
                "ts": ts, "valid": val, "C_bp": np.r_[0.0, np.cumsum(sbp * vd)], "C_c": np.r_[0.0, np.cumsum(100.0 * spr * vd)],
                "C_d": np.r_[0.0, np.cumsum(vd)], "sbp": sbp, "spr": spr,
                "vts": vts, "vbid": vb, "vask": va, "vbsz": bsz[vi], "vasz": asz[vi], "vmid": (vb + va) / 2.0,
                "cts": vts[chg], "vlogmid": np.log((vb + va) / 2.0) if vi.size else np.zeros(0)})

    def p11_segment(self, t: int) -> int:
        """0 premarket, 1 rth, 2 post; -1 outside 04:00-20:00."""
        b = self.bounds
        if t < b[0] or t >= b[3]:
            return -1
        return 0 if t < b[1] else (1 if t < b[2] else 2)

    def view(self, t: int) -> dict | None:
        """The segment's rows at or before t (views, no copy)."""
        g = self.p11_segment(t)
        if g < 0 or self.seg[g] is None:
            return None
        s = self.seg[g]
        r = int(np.searchsorted(s["ts"], t, "right"))
        v = int(np.searchsorted(s["vts"], t, "right"))
        c = int(np.searchsorted(s["cts"], t, "right"))
        return {"g": g, "t": t, "seg_lo": self.bounds[g], "ts": s["ts"][:r], "valid": s["valid"][:r], "C_bp": s["C_bp"][:r + 1], "C_c": s["C_c"][:r + 1],
                "C_d": s["C_d"][:r + 1], "sbp": s["sbp"][:r], "spr": s["spr"][:r], "vts": s["vts"][:v], "vbid": s["vbid"][:v], "vask": s["vask"][:v],
                "vbsz": s["vbsz"][:v], "vasz": s["vasz"][:v], "vmid": s["vmid"][:v], "vlogmid": s["vlogmid"][:v], "cts": s["cts"][:c]}


def assert_causal(t: int, *ts_arrays) -> None:
    """Section 4: no print or quote with sip_timestamp > t reaches a measure."""
    for a in ts_arrays:
        if a is not None and len(a) and int(a[-1]) > t:
            raise AssertionError(CAUSAL_MSG)
        if a is not None and len(a) and int(np.max(a)) > t:
            raise AssertionError(CAUSAL_MSG)


# ------------------------------------------------------------------ the tape

class Tape:
    """One event's prints 04:00-20:00, the clock segments, and per C1 segment the D26 collapse and prefix sums."""

    def __init__(self, event_id: str, date: str, tr: dict | None = None):
        tr = tr if tr is not None else B1.read_trades(event_id, with_conditions=False)
        self.date = date
        self.t0400, self.t2000 = B1.et_ns(date, "04:00:00"), B1.et_ns(date, "20:00:00")
        a, b = int(np.searchsorted(tr["ts"], self.t0400, "left")), int(np.searchsorted(tr["ts"], self.t2000, "right"))
        self.ts, self.px, self.sz = tr["ts"][a:b].copy(), tr["px"][a:b].copy(), tr["sz"][a:b].copy()
        self.op, self.cl = B1.rth_bounds_ns(date)
        self.CS = np.r_[0.0, np.cumsum(self.sz)]                  # shares 04:00 -> print i (exclusive)
        self.seg = {}
        for name in SEGS:
            lo = B1.segment_start_ns(name, date, self.op, self.cl)
            hi = {"premarket": self.op, "regular": self.cl, "after_hours": self.t2000}[name]
            i0, i1 = int(np.searchsorted(self.ts, lo, "left")), int(np.searchsorted(self.ts, hi, "left"))
            ts, px, sz = self.ts[i0:i1], self.px[i0:i1], self.sz[i0:i1]
            ct = B1.collapse_tol(ts, TOL_MS) if ts.size else np.zeros(0, dtype=np.int64)
            cid = (np.searchsorted(ct, ts, "right") - 1).astype(np.int64) if ts.size else np.zeros(0, dtype=np.int64)
            self.seg[name] = {"lo": lo, "hi": hi, "i0": i0, "ts": ts, "px": px, "sz": sz, "ct": ct, "cid": cid,
                              "CS": np.r_[0.0, np.cumsum(sz)], "CD": np.r_[0.0, np.cumsum(px * sz)]}

    def segment(self, t: int) -> str:
        return B1.clock_segment(t, self.op, self.cl)

    def seg_end(self, name: str) -> int:
        """Where t's segment ends for the hindsight censoring rule: open, close, 20:00."""
        return {"premarket": self.op, "regular": self.cl, "after_hours": self.t2000}[name]

    def view(self, t: int, name: str) -> dict:
        """t's segment's prints at or before t (views): ts, px, sz, collapsed times, order ids, prefix sums."""
        s = self.seg[name]
        hi = int(np.searchsorted(s["ts"], t, "right"))
        c = int(np.searchsorted(s["ct"], t, "right"))
        return {"t": t, "seg": name, "lo": s["lo"], "ts": s["ts"][:hi], "px": s["px"][:hi], "sz": s["sz"][:hi], "ct": s["ct"][:c],
                "cid": s["cid"][:hi], "CS": s["CS"][:hi + 1], "CD": s["CD"][:hi + 1]}


# ------------------------------------------------------------------ the segment rule

def assert_window(a: int, t: int, seg: str, lo: int, op: int, cl: int) -> None:
    """Section 4 / b2 R3: [a, t] inside t's own clock segment [lo, t] and free of both auction minutes."""
    if seg not in SEGS:
        raise AssertionError(f"{SEGMENT_MSG}: t is in {seg}")
    if not (lo <= a <= t):
        raise AssertionError(f"{SEGMENT_MSG}: window start {a} before the segment start {lo}")
    for x, y in ((op, op + MIN_NS), (cl, cl + MIN_NS)):
        if a < y and t >= x:
            raise AssertionError(f"{SEGMENT_MSG}: [{a}, {t}] meets the auction minute [{x}, {y})")
    if B1.clock_segment(a, op, cl) != seg or B1.clock_segment(t, op, cl) != seg:
        raise AssertionError(f"{SEGMENT_MSG}: [{a}, {t}] spans a segment boundary")


# ------------------------------------------------------------------ misc

def moment_grid(tau: int, t2000: int, cfg: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(j, t, weight): tau + j min for j = 0..60, then every 5 min; strictly before 20:00."""
    m = cfg["moments"]
    n1, step = m["wall_minutes_every_1"], m["late_step_minutes"]
    js, ts, ws = [], [], []
    for j in range(n1 + 1):
        t = tau + j * MIN_NS
        if t >= t2000:
            break
        js.append(j), ts.append(t), ws.append(m["weights"]["tau_and_first_60_min"])
    i = 1
    while True:
        t = tau + (n1 + step * i) * MIN_NS
        if t >= t2000:
            break
        js.append(n1 + i), ts.append(t), ws.append(m["weights"]["after_60_min"])
        i += 1
    js, ts, ws = np.array(js, dtype=np.int64), np.array(ts, dtype=np.int64), np.array(ws, dtype=np.int64)
    if ts.size:
        assert ws.sum() == (ts[-1] - tau) // MIN_NS + 1, "weights do not sum to the minutes covered"
    return js, ts, ws


def minutes_since_tau(j: np.ndarray) -> np.ndarray:
    j = np.asarray(j)
    return np.where(j <= 60, j, 60 + 5 * (j - 60))


def moment_uid(event_index, j):
    return np.asarray(event_index, dtype=np.int64) * 512 + np.asarray(j, dtype=np.int64)
