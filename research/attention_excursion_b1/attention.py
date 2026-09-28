"""
Brief 1 -- the attention quantities that are not the A2 ladders (those live in instruments.py).

Every function takes the prints it is allowed to see and asserts that none is after tau. The II.5
verification test (`causality_test`) feeds each function -- and both A2 ladders -- a print one
nanosecond after tau and requires the assertion to raise.
"""
from __future__ import annotations

import glob
import json
import math
import os

import numpy as np
import pandas as pd

import common as C
import instruments as I

POST_TAU_MSG = "post-tau print reached an attention quantity"
SEGMENT_MSG = "A2 rung half-window leaves tau's clock segment"


def assert_segment_windows(lad: list[dict], tau_ns: int, seg_start_ns: int, open_ns: int, close_ns: int) -> None:
    """Amendment 3 II.5: every rung's half-windows [lo, mid) and [mid, tau] lie inside [segment start,
    tau], meet neither cross minute [open, open + 60 s) / [close, close + 60 s), and do not span a
    segment boundary. A violation raises."""
    seg = C.clock_segment(tau_ns, open_ns, close_ns)
    if seg in C.AUCTION:
        raise AssertionError(f"{SEGMENT_MSG}: tau is in a cross minute ({seg}); A2 is unavailable there")
    for x in lad:
        lo, mid = int(x["win_lo_ns"]), int(x["win_mid_ns"])
        if not (seg_start_ns <= lo <= mid <= tau_ns):
            raise AssertionError(f"{SEGMENT_MSG}: rung {x['k']} [{lo}, {tau_ns}] starts before the segment start {seg_start_ns}")
        for a, b in ((open_ns, open_ns + C.MIN_NS), (close_ns, close_ns + C.MIN_NS)):
            if lo < b and tau_ns >= a:
                raise AssertionError(f"{SEGMENT_MSG}: rung {x['k']} [{lo}, {tau_ns}] meets the cross minute [{a}, {b})")
        if {C.clock_segment(lo, open_ns, close_ns), C.clock_segment(mid, open_ns, close_ns)} != {seg}:
            raise AssertionError(f"{SEGMENT_MSG}: rung {x['k']} spans a segment boundary")


def assert_causal(ts: np.ndarray, tau_ns: int) -> None:
    if ts.size and int(np.max(ts)) > tau_ns:
        raise AssertionError(POST_TAU_MSG)


def a1_shares(ts: np.ndarray, sz: np.ndarray, tau_ns: int, t0400_ns: int) -> float:
    """Shares traded from 04:00 ET to tau inclusive."""
    assert_causal(ts, tau_ns)
    m = ts >= t0400_ns
    return float(sz[m].sum())


def dollar_volume(ts: np.ndarray, px: np.ndarray, sz: np.ndarray, lo_ns: int, tau_ns: int) -> float:
    """Dollar volume over (lo, tau]."""
    assert_causal(ts, tau_ns)
    m = ts > lo_ns
    return float((px[m] * sz[m]).sum())


def window_counts(ct: np.ndarray, tau_ns: int, win_lo_ns: int, win_mid_ns: int) -> tuple[int, int]:
    """Collapsed counts in [mid, tau] and [lo, mid) -- the A2 half-windows, on any name's prints."""
    assert_causal(ct, tau_ns)
    hi = int(np.searchsorted(ct, tau_ns, "right"))
    im = int(np.searchsorted(ct, win_mid_ns, "left"))
    ia = int(np.searchsorted(ct, win_lo_ns, "left"))
    return hi - im, im - ia


def last_price(ts: np.ndarray, px: np.ndarray, tau_ns: int) -> float:
    assert_causal(ts, tau_ns)
    return float(px[-1]) if ts.size else float("nan")


def a3_filings(accepted_ns: np.ndarray, forms: np.ndarray, tau_ns: int) -> dict:
    """Filings strictly before tau. The caller passes only those; the assertion enforces it."""
    if accepted_ns.size and int(np.max(accepted_ns)) >= tau_ns:
        raise AssertionError(POST_TAU_MSG)
    day = 24 * 3600 * 10**9
    if accepted_ns.size == 0:
        return {"filing_24h": False, "n_filings_24h": 0, "hours_since_last_filing": float("nan"),
                "last_form_before_tau": None}
    j = int(np.argmax(accepted_ns))
    n24 = int((accepted_ns >= tau_ns - day).sum())
    return {"filing_24h": n24 > 0, "n_filings_24h": n24,
            "hours_since_last_filing": (tau_ns - int(accepted_ns[j])) / 3.6e12,
            "last_form_before_tau": str(forms[j])}


# ------------------------------------------------------------------ SEC raw archive (F1's source)

def load_cik_filings(raw_root: str, cik: str) -> pd.DataFrame:
    """accession, form, accepted_ns for one CIK from F1's own raw submissions archive (primary file +
    older-history files). Parsing follows research/fundamentals_f1/t3_filing_index.py: acceptanceDateTime
    is genuine UTC, empty values dropped, dedup on accession."""
    frames = []
    for p in [os.path.join(raw_root, f"{cik}.json")] + sorted(glob.glob(os.path.join(raw_root, f"{cik}__*.json"))):
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        rec = d.get("filings", {}).get("recent", d)
        frames.append(pd.DataFrame({"accession": rec.get("accessionNumber", []), "form": rec.get("form", []),
                                    "acceptance": rec.get("acceptanceDateTime", [])}))
    if not frames:
        return pd.DataFrame(columns=["accession", "form", "accepted_ns"])
    f = pd.concat(frames, ignore_index=True)
    f = f[f["acceptance"].astype(str) != ""]
    f["accepted_ns"] = pd.to_datetime(f["acceptance"], utc=True, errors="coerce").astype("int64")
    return f.dropna(subset=["accepted_ns"]).drop_duplicates("accession")[["accession", "form", "accepted_ns"]]


# ------------------------------------------------------------------ II.5 test

def causality_test(field_exact) -> dict:
    """Feed each attention function a print 1 ns after tau; each must raise."""
    tau = 10**15
    t0400 = tau - 6 * 3600 * 10**9
    ts_ok = np.linspace(t0400, tau, 500).astype(np.int64)
    ts_bad = np.r_[ts_ok, tau + 1]
    px = np.ones(ts_bad.size)
    sz = np.ones(ts_bad.size)
    cases = {
        "a1_shares": lambda: a1_shares(ts_bad, sz, tau, t0400),
        "dollar_volume": lambda: dollar_volume(ts_bad, px, sz, t0400, tau),
        "window_counts": lambda: window_counts(ts_bad, tau, t0400, tau - 10**9),
        "last_price": lambda: last_price(ts_bad, px, tau),
        "a3_filings": lambda: a3_filings(np.array([tau - 5, tau]), np.array(["8-K", "8-K"]), tau),
        "a2_count_ladder": lambda: I.a2_count_ladder(ts_bad, tau, t0400),
        "a2_kernel": lambda: I.a2_kernel(ts_bad, tau, t0400, [2], field_exact),
    }
    out = {}
    for name, fn in cases.items():
        try:
            fn()
            out[name] = "DID NOT RAISE"
        except AssertionError as e:
            out[name] = "raised" if (POST_TAU_MSG in str(e) or "after tau" in str(e)) else f"raised other: {e}"
    # and the clean inputs must not raise
    a1_shares(ts_ok, np.ones(ts_ok.size), tau, t0400)
    I.a2_count_ladder(ts_ok, tau, t0400)
    out["clean_inputs_do_not_raise"] = "ok"
    out.update(segment_test())
    out["passes"] = all(v in ("raised", "ok") for v in out.values())
    return out


def segment_test() -> dict:
    """Amendment 3 II.5: a regular-hours tau with a 04:00-anchored ladder (runs 1-3) must raise; a tau
    in the opening-cross minute must raise; the segment-anchored ladder (09:31) must not."""
    d = "2024-03-15"
    op, cl = C.rth_bounds_ns(d)
    t0400 = C.et_ns(d, "04:00:00")
    tau = C.et_ns(d, "11:00:00")
    ts = np.linspace(t0400, tau, 5000).astype(np.int64)
    out = {}
    for name, (lad, t, start) in {
            "segment_rth_tau_anchored_0400": (I.a2_count_ladder(ts, tau, t0400), tau, t0400),
            "segment_tau_in_open_cross_minute": ([], op + 30 * C.NS, op + C.MIN_NS)}.items():
        try:
            assert_segment_windows(lad, t, start, op, cl)
            out[name] = "DID NOT RAISE"
        except AssertionError as e:
            out[name] = "raised" if SEGMENT_MSG in str(e) else f"raised other: {e}"
    start = C.segment_start_ns("regular", d, op, cl)
    assert_segment_windows(I.a2_count_ladder(ts[ts >= start], tau, start), tau, start, op, cl)
    out["segment_anchored_ladder_does_not_raise"] = "ok"
    return out


def spearman(a, b) -> float:
    a, b = pd.Series(a), pd.Series(b)
    m = a.notna() & b.notna()
    if m.sum() < 3:
        return float("nan")
    return float(a[m].rank().corr(b[m].rank()))


def safe_log(x: float) -> float:
    return math.log(x) if x > 0 else float("nan")
