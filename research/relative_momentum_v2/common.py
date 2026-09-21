"""
v2 shared plumbing: the absolute floor, its build-time assertion, and the tick/quote readers.

The architecture, and the reason for it. v0 and v1 both gated on a RATIO -- relative volume, then
a percentile of relative volume -- and both degraded the median trade. A percentile of ratios is
still a ratio: it fails on a dead tape exactly like the thing it was meant to catch. v2 runs an
ABSOLUTE, unit-bearing floor first and demotes the ratio to a tie-break among survivors, which also
gives the system a NO_TRADE outcome that ranking alone structurally cannot produce.

Everything the floor reads is a raw measured quantity with a unit attached. Nothing is divided by a
baseline, a rolling mean, another candidate's value, or a percentile. That is not a convention here,
it is asserted in code -- see assert_floor_inputs_absolute.

D17 governs the quote side: crossed quotes, null/non-positive prices, one-sided quotes and zero-size
quotes are excluded; LOCKED quotes (bid == ask) are carried, because dropping a genuine zero-spread
state biases measured spread upward.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

CFG = "config/relative_momentum_v2.json"
ART = "results/relative_momentum/v2/artifacts"
CHARTS = "results/relative_momentum/v2/charts"

REPO = pathlib.Path(__file__).resolve().parents[2]

POPULATION = "results/relative_momentum/v1/artifacts/t0_candidates.parquet"
D1_CONCURRENCY = "results/relative_momentum/v1/artifacts/t5_d1_concurrency.json"
BASELINE = "results/fundamental_exploration/e2/artifacts/e2_t2a_baseline.parquet"
DETECTION_PRICE = "results/fundamental_exploration/artifacts/detection_price.parquet"
XS_FLAGS = "results/phase_9/artifacts/t1_cross_session_flags.parquet"
V0_DIAGNOSTIC = "results/relative_momentum/v0/artifacts/t4_diagnostic.parquet"

NS = 1_000_000_000


# ------------------------------------------------------------------ config

def load_cfg() -> dict:
    with open(REPO / CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def write_json(path: str, obj: dict) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


# ------------------------------------------------------- the floor contract

# The exact raw measured quantities the floor may read. Every one carries a unit.
FLOOR_INPUTS = (
    "print_count",      # prints
    "notional_usd",     # dollars
    "venue_count",      # venues
    "quote_count",      # messages
    "spread_bp",        # basis points
    "depth_usd",        # dollars
    "depth_available",  # bool guard, not a measurement
)

# The price filter's input, kept separate because the filter itself is separate.
PRICE_INPUT = "last_price"   # dollars

# Anything whose name implies it was produced by dividing through something else. The floor may
# never see one of these; the ranker may see all of them.
FORBIDDEN_TOKENS = (
    "b_e", "score", "baseline", "percentile", "pctl", "quantile", "rank", "ratio",
    "relative", "rel_", "zscore", "z_score", "norm", "pct", "share_of", "vs_",
)


class FloorContractViolation(AssertionError):
    """Raised when a non-absolute quantity reaches the absolute floor."""


def assert_floor_inputs_absolute(columns) -> None:
    """The pseudocode's build-time ASSERT, implemented.

    'no input to ABSOLUTE_FLOOR is divided by a prior-session baseline, a rolling mean of its own
    series, another candidate's value, or a percentile of any distribution.'

    Enforced structurally rather than by convention: the floor is only ever handed a projection of
    FLOOR_INPUTS, and this raises if that projection is incomplete or if any column name carries a
    token implying a normalised quantity. Relative volume, B_e and every percentile therefore cannot
    reach the floor -- they are not in the whitelist and they trip the token check.
    """
    cols = list(columns)
    missing = [c for c in FLOOR_INPUTS if c not in cols]
    if missing:
        raise FloorContractViolation(
            f"floor inputs missing from the projection: {missing}")
    extra = [c for c in cols if c not in FLOOR_INPUTS]
    if extra:
        raise FloorContractViolation(
            f"floor was handed columns outside the whitelist: {extra}")
    for c in cols:
        low = c.lower()
        for tok in FORBIDDEN_TOKENS:
            if tok in low:
                raise FloorContractViolation(
                    f"column {c!r} contains forbidden token {tok!r} -- a floor input may not be "
                    f"a ratio, a percentile, or normalised by a baseline")


# ------------------------------------------------------------- thresholds

def derive_thresholds(cfg: dict, overrides: dict | None = None) -> dict:
    """Resolve the six floor thresholds plus the separate price threshold.

    overrides maps a laddered constant name to the rung to use; anything absent takes its declared
    reference rung. MIN_NOTIONAL_USD and MIN_PRICE_USD are DERIVED, never declared directly.
    """
    lad = cfg["ladders"]
    k = cfg["constants"]
    o = overrides or {}

    def rung(name: str):
        if name in o:
            v = o[name]
            assert v in lad[name]["rungs"], f"{name}={v} is not a declared rung"
            return v
        return lad[name]["reference"]

    S = rung("INTENDED_SIZE_USD")
    X = rung("MAX_PER_SHARE_COST_BP")
    return {
        "MIN_PRINTS": rung("MIN_PRINTS"),
        "MIN_NOTIONAL_USD": S / k["PARTICIPATION_CAP"],
        "MIN_VENUES": k["MIN_VENUES"],
        "MIN_QUOTES": rung("MIN_QUOTES"),
        "MAX_SPREAD_BP": rung("MAX_SPREAD_BP"),
        "MIN_DEPTH_USD": rung("MIN_DEPTH_USD"),
        "MIN_PRICE_USD": k["PER_SHARE_COST_USD"] * 10000.0 / X,
        "_INTENDED_SIZE_USD": S,
        "_MAX_PER_SHARE_COST_BP": X,
    }


def ladder_configurations(cfg: dict) -> list[dict]:
    """The reference rung plus each laddered constant swept one at a time -- 13 configurations.

    A full cross would be 3^6 = 729. One-at-a-time keeps the surface readable while still reading
    ACROSS each ladder, which is the discipline the plan committed to: no rung privileged.
    """
    lad = cfg["ladders"]
    names = [n for n in lad if not n.startswith("_")]
    out = [{"label": "reference", "swept": None, "overrides": {}}]
    for n in names:
        for r in lad[n]["rungs"]:
            if r == lad[n]["reference"]:
                continue
            out.append({"label": f"{n}={r}", "swept": n, "overrides": {n: r}})
    return out


def absolute_floor(m: dict, thr: dict) -> tuple[bool, list[str]]:
    """ABSOLUTE_FLOOR, verbatim from the pseudocode, minus price_too_low.

    price_too_low is applied separately (price_filter) per Correction 1 section 4: it rejects more
    than everything else combined and it is a COST decision, not an attention one. Left inside this
    AND it masks every other condition's contribution to the fail-reason histogram.
    """
    fails: list[str] = []
    if m["print_count"] < thr["MIN_PRINTS"]:
        fails.append("too_few_prints")
    if m["notional_usd"] < thr["MIN_NOTIONAL_USD"]:
        fails.append("thin_notional")
    if m["venue_count"] < thr["MIN_VENUES"]:
        fails.append("single_venue")
    if m["quote_count"] < thr["MIN_QUOTES"]:
        fails.append("dead_book")
    if m["spread_bp"] is not None and np.isfinite(m["spread_bp"]) \
            and m["spread_bp"] > thr["MAX_SPREAD_BP"]:
        fails.append("spread_too_wide")
    if m["depth_available"] and m["depth_usd"] < thr["MIN_DEPTH_USD"]:
        fails.append("no_depth")
    return (len(fails) == 0), fails


def price_filter(last_price: float, thr: dict) -> bool:
    """TRUE = passes (price is high enough). Separate from the floor, reported on its own."""
    return bool(np.isfinite(last_price) and last_price >= thr["MIN_PRICE_USD"])


# ------------------------------------------------------------- data access

def load_population() -> pd.DataFrame:
    """v1's gap-gated candidates: 903 events, one per event, tick-exact gap-gate reconstruction
    including queued entries and the runner's next-tick fill convention. Reused, not rebuilt."""
    d = pd.read_parquet(REPO / POPULATION)
    ok = d[d["ok"].fillna(False)].copy().reset_index(drop=True)
    return ok


def event_folder(ticker: str, date: str) -> str | None:
    hits = sorted(glob.glob(str(REPO / "data" / "filtered" / f"{ticker}_{date}_*")))
    return hits[0] if hits else None


def snap_tau_to_tick(folder: str, tau_float: float, tol_ns: int = 10_000) -> dict:
    """Recover tau's exact int64 value by snapping it to the nearest real tick.

    WHY THIS IS NEEDED. v1-T0 wrote entry_ts as float64. At 1.7e18 the float64 grid spacing is
    256 ns, so every stored tau is rounded by up to ~128 ns. tau IS a tick timestamp by
    construction -- v1 set it to ts[i] -- so the nearest tick recovers the true value rather than
    inventing one. Two of the 903 candidates were rounded UPWARD past their own trigger print
    (BENF 2024-07-05 by 115 ns, JL 2024-01-29 by 58 ns), and because their previous print was
    601 s and 4,639 s earlier the `ts <= tau` window came up completely empty -- they would have
    been rejected by the floor for a floating-point reason.

    Asserts the snap is under tol_ns, which is what makes this a precision recovery and not a
    shift: a genuine mismatch would be orders of magnitude larger.
    """
    tp = os.path.join(folder, "trades.parquet")
    if not os.path.exists(tp):
        return {"tau_ns": int(tau_float), "snap_ns": None, "snapped": False}
    ts = np.sort(pq.read_table(tp, columns=["sip_timestamp"]).column("sip_timestamp").to_numpy())
    if ts.size == 0:
        return {"tau_ns": int(tau_float), "snap_ns": None, "snapped": False}
    approx = int(tau_float)
    j = int(np.searchsorted(ts, approx))
    cands = [ts[k] for k in (j - 1, j, j + 1) if 0 <= k < ts.size]
    best = min(cands, key=lambda v: abs(int(v) - approx))
    snap = int(best) - approx
    assert abs(snap) <= tol_ns, (
        f"tau snap of {snap} ns exceeds {tol_ns} ns -- this is a real mismatch, not float "
        f"precision recovery")
    return {"tau_ns": int(best), "snap_ns": snap, "snapped": True}


def measure(folder: str, tau_ns: int, window_seconds: int) -> dict:
    """MEASURE(c, tau) from the pseudocode. Causal: the window is [tau - W, tau], upper bound
    inclusive, and the assertion below fires if anything after tau reaches a returned quantity."""
    lo = tau_ns - window_seconds * NS
    out = {"print_count": 0, "notional_usd": 0.0, "venue_count": 0, "quote_count": 0,
           "last_price": np.nan, "spread_bp": np.nan, "spread_cents": np.nan,
           "depth_usd": np.nan, "depth_available": False,
           "n_quote_rows_raw": 0, "n_quote_rows_excluded_d17": 0, "share_volume": 0,
           "trades_read": False, "quotes_read": False}

    tp = os.path.join(folder, "trades.parquet")
    if os.path.exists(tp):
        t = pq.read_table(tp, columns=["sip_timestamp", "price", "size", "exchange"])
        ts = t.column("sip_timestamp").to_numpy()
        m = (ts >= lo) & (ts <= tau_ns)
        assert not (ts[m] > tau_ns).any(), "causality violated: a print after tau entered the window"
        out["trades_read"] = True
        if m.any():
            px = t.column("price").to_numpy()[m]
            sz = t.column("size").to_numpy()[m].astype(np.float64)
            ex = t.column("exchange").to_numpy()[m]
            order = np.argsort(ts[m], kind="stable")
            out["print_count"] = int(m.sum())
            out["notional_usd"] = float((px * sz).sum())
            out["share_volume"] = int(sz.sum())
            out["venue_count"] = int(np.unique(ex).size)
            out["last_price"] = float(px[order][-1])

    qp = os.path.join(folder, "quotes.parquet")
    if os.path.exists(qp):
        q = pq.read_table(qp, columns=["sip_timestamp", "bid_price", "ask_price",
                                       "bid_size", "ask_size"])
        qts = q.column("sip_timestamp").to_numpy()
        qm = (qts >= lo) & (qts <= tau_ns)
        assert not (qts[qm] > tau_ns).any(), "causality violated: a quote after tau entered"
        out["quotes_read"] = True
        out["n_quote_rows_raw"] = int(qm.sum())
        if qm.any():
            b = q.column("bid_price").to_numpy()[qm].astype(np.float64)
            a = q.column("ask_price").to_numpy()[qm].astype(np.float64)
            bs = q.column("bid_size").to_numpy()[qm].astype(np.float64)
            asz = q.column("ask_size").to_numpy()[qm].astype(np.float64)
            # D17: exclude crossed, null/non-positive, one-sided, zero-size. CARRY locked (b == a).
            keep = (np.isfinite(b) & np.isfinite(a) & (b > 0) & (a > 0)
                    & (b <= a) & np.isfinite(bs) & np.isfinite(asz) & (bs > 0) & (asz > 0))
            out["n_quote_rows_excluded_d17"] = int(qm.sum() - keep.sum())
            out["quote_count"] = int(keep.sum())
            if keep.any():
                bb, aa, bbs, aas = b[keep], a[keep], bs[keep], asz[keep]
                mid = (bb + aa) / 2.0
                out["spread_bp"] = float(np.median((aa - bb) / mid * 1e4))
                out["spread_cents"] = float(np.median((aa - bb) * 100.0))
                # pseudocode: MEDIAN(bid_size * bid + ask_size * ask) -- BOTH sides summed
                out["depth_usd"] = float(np.median(bbs * bb + aas * aa))
                out["depth_available"] = True
    return out
