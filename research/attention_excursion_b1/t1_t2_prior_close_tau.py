"""
Brief 1, T1 + T2 under Amendment 1 -- exact prior close and exact decision instant tau, all of D1,
one tick pass. (Run 1's version of this script, with the superseded largest-size T1 rule, is at
commit a3f6a9c; its artifacts are in artifacts/run1/.)

T1 (A1.2)  prior close, first that exists wins, on the prior XNYS session:
             listing_cross    -- code 8 (Closing Prints) on the listing venue's exchange id
             listing_official -- code 15 (Market Center Official Close) on the listing venue
             last_rth_print   -- last print in [open, min(close, 16:00)], excluding code 8/15 prints
                                 from any other venue
             unavailable
           Listing venue from the Phase 1b snapshot; MIC -> exchange id from config (census-derived).
T2         tau = first print at or after 04:00 ET with price >= 1.30 x prior close, skipping
           spike-guard failures. int64 throughout.

Computed alongside, each a column the amendment names (none changes tau):
    tau_ns_noguard       no spike guard
    tau_ns_guard15       the overlay's 1.5% neighbour agreement (A1.4 sensitivity)
    tau_ns_mb            against the old minute-bar close (A1.3 tau_close_sensitive)
    tau_proxy_prime_ns   the v1 minute-level proxy rebuilt from ticks on the SAME close as tau (A1.1)
    tau_proxy_mb_tick_ns the same construction on the minute-bar close -- must reproduce v1's stored
                         proxy, which validates the construction row 4 now gates on

No outcome is read: the pass stops at tau.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t1_t2_prior_close_tau.py [n_events]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SNAPSHOT = "results/phase_1b/artifacts/ticker_reference_snapshot.parquet"
LISTING_CAPABLE = (1, 10, 12)
_CFG = None


def _cfg():
    global _CFG
    if _CFG is None:
        _CFG = C.load_cfg()
    return _CFG


def prior_close_a1(tr: dict, ps_date: str, listing_ex: int | None) -> dict:
    ts, px, sz, ex = tr["ts"], tr["px"], tr["sz"], tr["ex"]
    cmap = _cfg()["t1_prior_close"]["condition_code_mapping"]
    c_cross, c_off = cmap["closing_cross"]["code"], cmap["official_close"]["code"]
    lo, hi = C.day_bounds_ns(ps_date)
    i0, i1 = int(np.searchsorted(ts, lo, "left")), int(np.searchsorted(ts, hi, "left"))
    out = {"prior_session_date": ps_date, "n_prior_session_prints": i1 - i0, "listing_ex": listing_ex,
           "listing_unknown": listing_ex is None}
    if i1 <= i0:
        out.update(prior_close_available=False, prior_close_source="unavailable", prior_close_exact=np.nan,
                   unavailable_reason="no_prior_session_prints", listing_venue_mismatch=False)
        return out
    idx = np.arange(i0, i1)
    m_cross = C.rows_with_codes(tr["cond"], {c_cross}, idx)
    m_off = C.rows_with_codes(tr["cond"], {c_off}, idx)
    m_38 = C.rows_with_codes(tr["cond"], {38}, idx)
    cross_ex = sorted(set(int(v) for v in ex[idx[m_cross]]))
    out.update(n_cross_prints=int(m_cross.sum()), n_official_prints=int(m_off.sum()), n_code38=int(m_38.sum()),
               cross_venues_seen=str(cross_ex))
    on_listing = (ex[idx] == listing_ex) if listing_ex is not None else np.zeros(idx.size, dtype=bool)
    lc = idx[m_cross & on_listing]
    lo_ = idx[m_off & on_listing]
    out["n_listing_cross"], out["n_listing_official"] = int(lc.size), int(lo_.size)
    out["listing_venue_mismatch"] = bool(lc.size == 0 and any(e in LISTING_CAPABLE and e != listing_ex for e in cross_ex))
    op, cl = C.rth_bounds_ns(ps_date)
    cl_eff = min(cl, C.et_ns(ps_date, "16:00:00"))
    out["prior_close_bound_ns"] = cl_eff

    def take(j, source):
        out.update(prior_close_available=True, prior_close_source=source, prior_close_exact=float(px[j]),
                   prior_close_ts=int(ts[j]), prior_close_exchange=int(ex[j]), prior_close_size=float(sz[j]),
                   prior_close_codes=str(C.codes_at(tr["cond"], j)))

    if lc.size:
        key = np.lexsort((ts[lc], sz[lc]))                 # largest size, then latest
        take(int(lc[key[-1]]), "listing_cross")
    elif lo_.size:
        take(int(lo_[np.argmax(ts[lo_])]), "listing_official")
    else:
        auction_other = (m_cross | m_off) & ~on_listing
        ok = (ts[idx] >= op) & (ts[idx] <= cl_eff) & ~auction_other
        r = np.flatnonzero(ok)
        if r.size:
            take(int(idx[r[-1]]), "last_rth_print")
        else:
            out.update(prior_close_available=False, prior_close_source="unavailable", prior_close_exact=np.nan,
                       unavailable_reason="no_rth_print")
    return out


def proxy_minute(ts: np.ndarray, px: np.ndarray, lo: int, hi: int, level: float, t0400: int) -> int | None:
    """v1's minute-level proxy on ticks: the first clock minute from 04:00 whose high reaches `level`,
    stamped at that minute's first print. The first such minute is the minute of the first print at or
    above the level, so no minute table is needed."""
    i, _ = C.first_crossing(px, lo, hi, level, None, None)
    if i is None:
        return None
    m = (int(ts[i]) - t0400) // C.MIN_NS
    return int(ts[int(np.searchsorted(ts, t0400 + m * C.MIN_NS, "left"))])


def tau_rows(tr: dict, date: str, pc: float, mb_close: float) -> dict:
    cfg = _cfg()["t2_tau"]
    mult = cfg["crossing_multiple"]
    dev = cfg["spike_guard"]["deviation_threshold"]
    agree = cfg["spike_guard"]["neighbour_agreement"]
    ts, px, sz = tr["ts"], tr["px"], tr["sz"]
    t0400, t0930, t2000 = C.et_ns(date, "04:00:00"), C.et_ns(date, "09:30:00"), C.et_ns(date, "20:00:00")
    lo = int(np.searchsorted(ts, t0400, "left"))
    hi = int(np.searchsorted(ts, t2000, "right"))
    out = {"n_eventday_prints_0400_2000": hi - lo}
    if np.isfinite(mb_close) and mb_close > 0:
        i_mb, _ = C.first_crossing(px, lo, hi, mult * mb_close, dev, agree)
        out["tau_ns_mb"] = int(ts[i_mb]) if i_mb is not None else None
        out["tau_proxy_mb_tick_ns"] = proxy_minute(ts, px, lo, hi, mult * mb_close, t0400)
    if not np.isfinite(pc) or pc <= 0:
        out.update(tau_available=False, tau_reason="prior_close_unavailable")
        return out
    level = mult * pc
    i, skipped = C.first_crossing(px, lo, hi, level, dev, agree)
    i_ng, _ = C.first_crossing(px, lo, hi, level, None, None)
    i_15, _ = C.first_crossing(px, lo, hi, level, dev, dev / 2)
    out["tau_level"] = level
    out["n_spikes_skipped"] = skipped
    out["tau_ns_noguard"] = int(ts[i_ng]) if i_ng is not None else None
    out["tau_ns_guard15"] = int(ts[i_15]) if i_15 is not None else None
    out["tau_proxy_prime_ns"] = proxy_minute(ts, px, lo, hi, level, t0400)
    if i is None:
        out.update(tau_available=False, tau_reason="never_crosses")
        return out
    tau = int(ts[i])
    codes = C.codes_at(tr["cond"], i)
    op, cl = C.rth_bounds_ns(date)
    k = int(np.searchsorted(ts, tau, "right"))       # prints with ts <= tau
    out.update(tau_available=True, tau_reason="ok", tau_ns=tau, tau_price=float(px[i]),
               tau_codes=str(codes), tau_session_segment=C.assign_segment(tau, codes, op, cl),
               sec_from_0400=(tau - t0400) / C.NS, sec_from_0930=(tau - t0930) / C.NS,
               shares_0400_to_tau=float(sz[lo:k].sum()), n_prints_0400_to_tau=k - lo,
               tau_move_at=float(px[i]) / pc - 1.0)
    return out


def one(args) -> dict:
    event_id, ticker, date, mb_close, listing_ex = args
    row = {"event_id": event_id, "ticker": ticker, "event_date_canonical": date}
    try:
        tr = C.read_trades(event_id, with_conditions=True)
        if tr is None:
            row.update(prior_close_available=False, prior_close_source="unavailable",
                       unavailable_reason="no_trades_file", tau_available=False, tau_reason="no_trades_file")
            return row
        row["n_repair_rows"] = tr["n_repair_rows"]
        row.update(prior_close_a1(tr, C.prior_session(date), listing_ex))
        row.update(tau_rows(tr, date, row.get("prior_close_exact", np.nan), mb_close))
    except Exception as e:  # carried, never dropped
        row.update(error=f"{type(e).__name__}: {e}", tau_available=False, tau_reason="error")
    return row


def main() -> int:
    t_start = time.perf_counter()
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    cfg = C.load_cfg()
    mic_map = cfg["t1_prior_close"]["listing_venue"]["mic_to_exchange_id"]
    d1 = C.load_d1()
    snap = pd.read_parquet(C.REPO / SNAPSHOT, columns=["ticker", "primary_exchange"]).drop_duplicates("ticker")
    d1 = d1.merge(snap, on="ticker", how="left")
    d1["listing_ex"] = d1["primary_exchange"].map(mic_map)
    mb = pd.read_parquet(C.REPO / C.MB_CLOSE, columns=["event_id", "prior_close", "prior_close_available"])
    d1 = d1.merge(mb.rename(columns={"prior_close": "prior_close_mb", "prior_close_available": "prior_close_mb_available"}),
                  on="event_id", how="left")
    if lim:
        d1 = d1.sample(lim, random_state=0)
    jobs = [(r.event_id, r.ticker, r.event_date_canonical,
             float(r.prior_close_mb) if r.prior_close_mb_available else np.nan,
             int(r.listing_ex) if pd.notna(r.listing_ex) else None) for r in d1.itertuples()]
    rows = []
    with ProcessPoolExecutor(max_workers=10) as ex:
        for k, r in enumerate(ex.map(one, jobs, chunksize=40)):
            rows.append(r)
            if (k + 1) % 1000 == 0:
                print(f"  {k + 1:,}/{len(jobs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    out = pd.DataFrame(rows).merge(d1[["event_id", "primary_exchange", "prior_close_mb", "prior_close_mb_available"]],
                                   on="event_id", how="left")
    for c in ["tau_ns", "tau_ns_noguard", "tau_ns_guard15", "tau_ns_mb", "tau_proxy_prime_ns", "tau_proxy_mb_tick_ns",
              "prior_close_ts", "listing_ex"]:
        if c in out:
            out[c] = out[c].astype("Int64")
    tag = f"_sample{lim}" if lim else ""
    out["config_hash"] = C.cfg_hash()
    out.to_parquet(C.art(f"t1_t2_pass{tag}.parquet"), index=False)
    print(f"done {len(out):,} events in {time.perf_counter() - t_start:,.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
