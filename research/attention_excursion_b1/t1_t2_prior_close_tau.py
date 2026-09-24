"""
Brief 1, T1 + T2 -- exact prior close and exact decision instant tau, all of D1, one tick pass.

T1  prior close = the Amendment 6 {8, 15} auction print on the prior XNYS session (largest size;
    ties -> code 8, then latest), else the last regular-hours print by timestamp. Compared with the
    minute-bar close the earlier move_at build used.
T2  tau = the first print at or after 04:00 ET on the event day with price >= 1.30 x prior close,
    skipping spike-guard failures. int64 throughout. Compared with the v1 crossing proxy.

Diagnostics computed in the same pass (cheap once the prints are in memory; none changes tau):
    tau_noguard      -- no spike guard, to count what the guard moved
    tau_guard15      -- the overlay's own 1.5% neighbour agreement, the discrepancy the config records
    tau_mb           -- against the minute-bar prior close, to split tau_exact - tau_proxy into its
                        prior-close part and its print-vs-minute-stamp part

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

_CFG = None


def _cfg():
    global _CFG
    if _CFG is None:
        _CFG = C.load_cfg()
    return _CFG


def prior_close_exact(tr: dict, ps_date: str) -> dict:
    ts, px, sz = tr["ts"], tr["px"], tr["sz"]
    lo, hi = C.day_bounds_ns(ps_date)
    i0, i1 = np.searchsorted(ts, lo, "left"), np.searchsorted(ts, hi, "left")
    out = {"prior_session_date": ps_date, "n_prior_session_prints": int(i1 - i0)}
    if i1 <= i0:
        out.update(prior_close_available=False, prior_close_source="unavailable_no_prior_session_prints",
                   prior_close_exact=np.nan)
        return out
    idx = np.arange(i0, i1)
    m815 = C.rows_with_codes(tr["cond"], {8, 15}, idx)
    m8 = C.rows_with_codes(tr["cond"], {8}, idx)
    a = idx[m815]
    out["n_auction_8"] = int(m8.sum())
    out["n_auction_15"] = int(C.rows_with_codes(tr["cond"], {15}, idx).sum())
    out["n_auction_8_15"] = int(m815.sum())
    op, cl = C.rth_bounds_ns(ps_date)
    out["prior_open_ns"], out["prior_close_bound_ns"] = op, cl
    if a.size:
        is8 = m8[m815]
        # largest size; ties -> code 8 first; then latest timestamp
        key = np.lexsort((ts[a], is8.astype(int), sz[a]))
        j = int(a[key[-1]])
        p = float(px[j])
        ap = px[a]
        out.update(prior_close_available=True, prior_close_source="auction_8_15", prior_close_exact=p,
                   prior_close_ts=int(ts[j]), prior_close_exchange=int(tr["ex"][j]) if "ex" in tr else -1,
                   prior_close_size=float(sz[j]), prior_close_codes=str(C.codes_at(tr["cond"], j)),
                   auction_n_distinct_prices=int(np.unique(ap).size),
                   auction_price_spread_bp=float((ap.max() - ap.min()) / p * 1e4),
                   auction_after_close_s=float((ts[j] - cl) / C.NS))
        if is8.any():
            p8 = px[a[is8]]
            out["auction_code8_price"] = float(p8[np.argmax(sz[a[is8]])])
            out["chosen_differs_from_code8"] = bool(abs(out["auction_code8_price"] - p) > 1e-12)
        # fallback value alongside, for the census of how much the auction rule moves the close
        r = np.flatnonzero((ts[idx] >= op) & (ts[idx] <= cl))
        out["last_rth_print_price"] = float(px[idx[r[-1]]]) if r.size else np.nan
        return out
    r = np.flatnonzero((ts[idx] >= op) & (ts[idx] <= cl))
    if r.size == 0:
        out.update(prior_close_available=False, prior_close_source="unavailable_no_rth_print",
                   prior_close_exact=np.nan)
        return out
    j = int(idx[r[-1]])
    out.update(prior_close_available=True, prior_close_source="fallback_last_rth_print",
               prior_close_exact=float(px[j]), prior_close_ts=int(ts[j]),
               prior_close_exchange=int(tr["ex"][j]) if "ex" in tr else -1,
               prior_close_size=float(sz[j]), prior_close_codes=str(C.codes_at(tr["cond"], j)),
               last_rth_print_price=float(px[j]))
    return out


def tau_rows(tr: dict, date: str, pc: float, mb_close: float) -> dict:
    cfg = _cfg()["t2_tau"]
    mult = cfg["crossing_multiple"]
    dev = cfg["spike_guard"]["deviation_threshold"]
    agree = cfg["spike_guard"]["neighbour_agreement"]
    ts, px, sz = tr["ts"], tr["px"], tr["sz"]
    t0400, t0930, t2000 = C.et_ns(date, "04:00:00"), C.et_ns(date, "09:30:00"), C.et_ns(date, "20:00:00")
    lo = int(np.searchsorted(ts, t0400, "left"))
    hi = int(np.searchsorted(ts, t2000, "right"))
    out = {"n_eventday_prints_0400_2000": int(hi - lo)}
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
    if np.isfinite(mb_close) and mb_close > 0:
        i_mb, _ = C.first_crossing(px, lo, hi, mult * mb_close, dev, agree)
        out["tau_ns_mb"] = int(ts[i_mb]) if i_mb is not None else None
    if i is None:
        out.update(tau_available=False, tau_reason="never_crosses")
        return out
    tau = int(ts[i])
    codes = C.codes_at(tr["cond"], i)
    op, cl = C.rth_bounds_ns(date)
    k = int(np.searchsorted(ts, tau, "right"))       # prints with ts <= tau
    out.update(tau_available=True, tau_reason="ok", tau_ns=tau, tau_price=float(px[i]),
               tau_idx_in_day=int(i - lo), tau_codes=str(codes),
               tau_session_segment=C.assign_segment(tau, codes, op, cl),
               sec_from_0400=(tau - t0400) / C.NS, sec_from_0930=(tau - t0930) / C.NS,
               shares_0400_to_tau=float(sz[lo:k].sum()), n_prints_0400_to_tau=int(k - lo),
               tau_move_at=float(px[i]) / pc - 1.0)
    return out


def one(args) -> dict:
    event_id, ticker, date, mb_close = args
    row = {"event_id": event_id, "ticker": ticker, "event_date_canonical": date}
    try:
        tr = C.read_trades(event_id, with_conditions=True)
        if tr is None:
            row.update(prior_close_available=False, prior_close_source="unavailable_no_trades_file",
                       tau_available=False, tau_reason="no_trades_file")
            return row
        row["n_repair_rows"] = tr["n_repair_rows"]
        row.update(prior_close_exact(tr, C.prior_session(date)))
        row.update(tau_rows(tr, date, row.get("prior_close_exact", np.nan), mb_close))
    except Exception as e:  # carried, never dropped
        row.update(error=f"{type(e).__name__}: {e}", tau_available=False, tau_reason="error")
    return row


def main() -> int:
    t_start = time.perf_counter()
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    d1 = C.load_d1()
    mb = pd.read_parquet(C.REPO / C.MB_CLOSE, columns=["event_id", "prior_close", "prior_close_available"])
    d1 = d1.merge(mb.rename(columns={"prior_close": "prior_close_mb", "prior_close_available": "prior_close_mb_available"}),
                  on="event_id", how="left")
    if lim:
        d1 = d1.sample(lim, random_state=0)
    jobs = [(r.event_id, r.ticker, r.event_date_canonical,
             float(r.prior_close_mb) if r.prior_close_mb_available else np.nan) for r in d1.itertuples()]
    rows = []
    with ProcessPoolExecutor(max_workers=10) as ex:
        for k, r in enumerate(ex.map(one, jobs, chunksize=40)):
            rows.append(r)
            if (k + 1) % 1000 == 0:
                print(f"  {k + 1:,}/{len(jobs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    out = pd.DataFrame(rows).merge(d1[["event_id", "prior_close_mb", "prior_close_mb_available"]], on="event_id", how="left")
    for c in ["tau_ns", "tau_ns_noguard", "tau_ns_guard15", "tau_ns_mb", "prior_close_ts"]:
        if c in out:
            out[c] = out[c].astype("Int64")
    tag = f"_sample{lim}" if lim else ""
    out.to_parquet(C.art(f"t1_t2_pass{tag}.parquet"), index=False)
    print(f"done {len(out):,} events in {time.perf_counter() - t_start:,.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
