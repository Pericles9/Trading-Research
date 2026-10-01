"""
Chop regime C1 -- the per-moment measures (T1-T4) and the hindsight columns (section 5), one code path.

Every measure function takes the arrays it may see -- the tape and the quote book sliced to <= t by
c1common.Tape.view / QuoteBook.view -- and asserts that none of them reaches past t (c1common.assert_causal) and
that its window lies inside t's own clock segment, free of both auction minutes (c1common.assert_window). The
section 6 causality and segment tests (`causality_test`, `segment_test`) feed each function a print and a quote
1 ns after t, and windows that cross a boundary; each must raise.

    rate ladder     b2's R1 ladder (b2common.a2_ladder_r1, Brief 1's a2_count_ladder) with t in tau's place
    presence        trade_rate, dollar_flow, turnover_rate per valid rate rung; quote state at t; spread_tw
    relative        n_eff, top3_share, move_per_trade per valid rate rung
    scale-free      32 equal-volume buckets per valid rung (>= 64 collapsed trades), both prices: VWAP and the
                    D16 midpoint at each bucket's last print; er, er_0, er_rel. Amendment 1: the variance ratio is not
                    built (A1.1); the midpoint is primary, VWAP where a window has no midpoint path (A1.2)
    context         rung 0 (segment start -> t) bucketed to 32: the leg, giveback, time and volume since its high
    hindsight       forward return, MFE and MAE per horizon, entry = the first non-spike print after t; these read
                    the future by design and are never inputs to anything above

The bucket construction is Brief 1's split-at-edges rule (instruments.bucketize) on prefix sums; `bucket_equality_test`
checks the two agree.
"""
from __future__ import annotations

import math

import numpy as np

import c1common as C

B1, I, B2 = C.B1, C.I, C.B2
NS, MIN_NS = C.NS, C.MIN_NS
SQ2PI = math.sqrt(2.0 / math.pi)


# ====================================================================== quote state

def quote_state(qv: dict | None, t: int, size_mult: float | None) -> dict:
    """The D16 quote at t (the last D17-valid quote at or before t in t's Phase 11 segment), its spread in both units,
    the age of the best bid / offer, and displayed depth at the touch."""
    if qv is None:
        return {"quote_at_t": False}
    C.assert_causal(t, qv["ts"], qv["vts"], qv["cts"])
    if qv["vts"].size == 0:
        return {"quote_at_t": False}
    bid, ask = float(qv["vbid"][-1]), float(qv["vask"][-1])
    mid = (bid + ask) / 2.0
    out = {"quote_at_t": True, "bid_t": bid, "ask_t": ask, "mid_t": mid, "spread_bp_t": 1e4 * (ask - bid) / mid, "spread_c_t": 100.0 * (ask - bid),
           "quote_age_s": (t - int(qv["cts"][-1])) / NS if qv["cts"].size else np.nan}
    if size_mult is not None:
        out["depth_ask_usd"] = float(qv["vasz"][-1]) * size_mult * ask
        out["depth_bid_usd"] = float(qv["vbsz"][-1]) * size_mult * bid
    return out


def tw_spread(qv: dict | None, a: int, t: int) -> tuple[float, float, float]:
    """Time-weighted quoted spread over [a, t] (bp, cents) and the share of the window covered by a valid quote --
    Phase 11's rule: each row lasts until the next row; excluded rows' time is dropped."""
    if qv is None or qv["ts"].size == 0:
        return np.nan, np.nan, 0.0
    C.assert_causal(t, qv["ts"])
    ts, val, sbp, spr = qv["ts"], qv["valid"], qv["sbp"], qv["spr"]

    def integ(x):
        r = int(np.searchsorted(ts, x, "right")) - 1
        if r < 0:
            return 0.0, 0.0, 0.0
        dx = float(x - ts[r]) if val[r] else 0.0
        return qv["C_bp"][r] + sbp[r] * dx, qv["C_c"][r] + 100.0 * spr[r] * dx, qv["C_d"][r] + dx

    b1, c1, d1 = integ(t)
    b0, c0, d0 = integ(a)
    dur = d1 - d0
    if dur <= 0:
        return np.nan, np.nan, 0.0
    return (b1 - b0) / dur, (c1 - c0) / dur, dur / max(t - a, 1)


# ====================================================================== the rate ladder (presence and relative)

def rate_ladder(v: dict, t: int, cfg: dict) -> list[dict]:
    """b2 R1 (b2common.a2_ladder_r1) on the collapsed trades of t's segment up to t, anchored at the segment start."""
    C.assert_causal(t, v["ts"], v["ct"])
    r = cfg["measures"]["rate_ladder"]
    lad, _ = B2.a2_ladder_r1(v["ct"], t, v["lo"], r["n_min_per_half_window"], r["d22_floor_coef"], r["k_max"],
                             min_half_window_ns=int(r["min_half_window_ms"] * 1e6))
    return lad


def rate_measures(v: dict, a: int, t: int, n_collapsed: int, shs: float, geo: tuple) -> dict:
    """Presence and relative measures over the window [a, t] of t's segment (a rate-ladder rung)."""
    C.assert_causal(t, v["ts"], v["ct"])
    C.assert_window(a, t, v["seg"], v["lo"], *geo)
    ts, px, sz = v["ts"], v["px"], v["sz"]
    lo, hi = int(np.searchsorted(ts, a, "left")), ts.size
    W_min = (t - a) / MIN_NS
    shares = float(v["CS"][hi] - v["CS"][lo])
    dollars = float(v["CD"][hi] - v["CD"][lo])
    out = {"n_raw": hi - lo, "n_collapsed": n_collapsed, "W_min": W_min, "shares": shares,
           "trade_rate": n_collapsed / W_min, "raw_rate": (hi - lo) / W_min, "dollar_flow": dollars / W_min,
           "turnover_rate": (shares / shs / W_min) if (shs is not None and np.isfinite(shs) and shs > 0) else np.nan}
    if hi > lo and shares > 0:
        cid = v["cid"][lo:hi]
        vol = np.bincount(cid - cid[0], weights=sz[lo:hi])
        s = vol / shares
        out["n_eff"] = float(1.0 / np.sum(s * s))
        top = np.partition(vol, -3)[-3:] if vol.size > 3 else vol
        out["top3_share"] = float(top.sum() / shares)
        out["n_orders"] = int((vol > 0).sum())
    else:
        out.update({"n_eff": np.nan, "top3_share": np.nan, "n_orders": 0})
    out["move_per_trade"] = (abs(math.log(px[hi - 1] / px[lo])) * 1e4 / n_collapsed) if (hi > lo and n_collapsed > 0 and px[lo] > 0 and px[hi - 1] > 0) else np.nan
    return out


# ====================================================================== buckets

def buckets_core(ts: np.ndarray, px: np.ndarray, cv_end: np.ndarray, cd_end: np.ndarray, nb: int) -> dict | None:
    """Brief 1's equal-share-volume buckets (instruments.bucketize: prints split across edges at their own price, bucket
    VWAP, bucket time = last contributing print) on the window's cumulative volume and value (both through each print,
    inclusive). Returns None when the window has no volume."""
    V = float(cv_end[-1]) if cv_end.size else 0.0
    if V <= 0:
        return None
    E = np.arange(nb + 1, dtype=np.float64) * (V / nb)
    E[-1] = V
    own = np.searchsorted(cv_end, E[1:], "left")
    own = np.minimum(own, cv_end.size - 1)
    F = cd_end[own] - (cv_end[own] - E[1:]) * px[own]
    tot = float(cd_end[-1])
    assert abs(F[-1] - tot) <= 1e-9 * abs(tot) + 1e-9, "bucket value not conserved"
    assert abs(np.diff(E).sum() - V) <= 1e-9 * V, "bucket volumes do not sum to the window volume"
    B = V / nb
    vwap = np.diff(np.r_[0.0, F]) / B
    first = int(np.searchsorted(cv_end, 0.0, "right"))            # the first print with volume
    return {"vwap": vwap, "own": own, "first": first, "V": V, "t_end": ts[own], "t_first": int(ts[first]), "p_first": float(px[first])}


def mid_at(times: np.ndarray, qv: dict | None) -> np.ndarray:
    """The D16 midpoint prevailing at each time (NaN where no valid quote yet in the segment)."""
    if qv is None or qv["vts"].size == 0:
        return np.full(len(times), np.nan)
    i = np.searchsorted(qv["vts"], times, "right") - 1
    out = qv["vmid"][np.maximum(i, 0)].astype(np.float64)
    out[i < 0] = np.nan
    return out


def vwap_log_path(ts: np.ndarray, px: np.ndarray, sz: np.ndarray, nb: int) -> tuple[np.ndarray, dict] | tuple[None, None]:
    """[ln p0, ln VWAP_1 .. ln VWAP_nb] for a window's prints, p0 = the first print with volume.

    The buckets are buckets_core's (Brief 1's rule); the value sums run on each print's deviation from p0
    (px / p0 - 1), so a bucket whose prints all sit at one price gets exactly that price and two such buckets an exact
    zero return. On raw dollar prefix sums a flat stretch returns rounding noise (~1e-12), which is not scale-invariant
    (the section 6 blindness control would see it)."""
    cv_end = np.cumsum(sz)
    if not cv_end.size or cv_end[-1] <= 0:
        return None, None
    f = int(np.searchsorted(cv_end, 0.0, "right"))
    p0 = float(px[f])
    dev = px / p0 - 1.0
    b = buckets_core(ts, dev, cv_end, np.cumsum(dev * sz), nb)
    return math.log(p0) + np.log1p(np.r_[dev[f], b["vwap"]]), b


def bucket_path(v: dict, qv: dict | None, a: int, t: int, nb: int, geo: tuple) -> dict | None:
    """Both bucket paths over [a, t]: log prices [p0, P_1 .. P_nb], p0 the window's opening price on the same basis."""
    C.assert_causal(t, v["ts"], v["ct"], None if qv is None else qv["vts"])
    C.assert_window(a, t, v["seg"], v["lo"], *geo)
    ts, px = v["ts"], v["px"]
    lo, hi = int(np.searchsorted(ts, a, "left")), ts.size
    if hi <= lo:
        return None
    lp_v, b = vwap_log_path(ts[lo:hi], px[lo:hi], v["sz"][lo:hi], nb)
    if b is None:
        return None
    tot = float(v["CD"][hi] - v["CD"][lo])
    assert abs(float(np.exp(lp_v[1:]).sum()) * (b["V"] / nb) - tot) <= 1e-9 * abs(tot) + 1e-6, "bucket dollar value not conserved"
    m = mid_at(np.r_[b["t_first"], b["t_end"]], qv)
    ok = bool(np.isfinite(m).all() and (m > 0).all())
    return {"lp_vwap": lp_v, "lp_mid": np.log(m) if ok else None, "mid_ok": ok, "V": b["V"], "W_min": (t - a) / MIN_NS,
            "t_end": b["t_end"], "t_first": b["t_first"], "lo": lo, "hi": hi, "own": b["own"]}


# ====================================================================== scale-free statistics

def scale_free(R: np.ndarray) -> dict:
    """er, the closed-form reference er_0 = sqrt(2 / (pi n)) s / mean|r - rbar|, er_rel and sum r^2 for each row of R
    (M, n). The variance ratio is not built (Amendment 1 A1.1); er_rel and er_0 are columns, not conditions (A1.3)."""
    R = np.atleast_2d(np.asarray(R, dtype=np.float64))
    n = R.shape[1]
    path = np.abs(R).sum(axis=1)
    d = R - R.mean(axis=1, keepdims=True)
    s = np.sqrt((d * d).mean(axis=1))
    mad = np.abs(d).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        er = np.abs(R.sum(axis=1)) / path
        er0 = SQ2PI / math.sqrt(n) * s / mad
        er_rel = er / er0
    er[~(path > 0)] = np.nan
    er0[~(mad > 0)] = np.nan
    er_rel[~(path > 0) | ~(mad > 0)] = np.nan
    return {"er": er, "er0": er0, "er_rel": er_rel, "sum_r2": (R * R).sum(axis=1)}


# ====================================================================== context (rung 0)

def leg(lp: np.ndarray) -> dict:
    """The largest rise from a point to a later point on the path (earliest high within the A2.3 tie tolerance, the
    earliest low before it within the same tolerance), in own-noise units across the returns it spans."""
    n = lp.size
    if n < 2:
        return {"leg_state": "no_path"}
    runmin = np.minimum.accumulate(lp)
    rise = lp[1:] - runmin[:-1]
    R = float(rise.max())
    if not R > C.TIE_TOL:
        return {"leg_state": "no_leg", "leg_s": 0.0, "leg_log": 0.0}
    j = int(np.flatnonzero(rise >= R - C.TIE_TOL)[0]) + 1
    lo_val = float(lp[:j].min())
    i = int(np.flatnonzero(lp[:j] <= lo_val + C.TIE_TOL)[0])
    r = np.diff(lp)[i:j]
    noise = float(np.sqrt((r * r).sum()))
    rr = float(lp[j] - lp[i])
    return {"leg_state": "leg", "leg_i": i, "leg_j": j, "leg_log": rr, "leg_s": rr / noise if noise > 0 else np.nan}


def context(bp: dict, basis: str, p_t: float, t: int, nb: int) -> dict:
    lp = bp["lp_mid"] if basis == "mid" else bp["lp_vwap"]
    if lp is None:
        return {"leg_state": "no_path"}
    g = leg(lp)
    out = {"leg_state": g["leg_state"], "leg_s": g.get("leg_s", np.nan)}
    if g["leg_state"] != "leg":
        out.update({"leg_bp": 0.0 if g["leg_state"] == "no_leg" else np.nan, "leg_c": 0.0 if g["leg_state"] == "no_leg" else np.nan})
        return out
    i, j = g["leg_i"], g["leg_j"]
    p_lo, p_hi = math.exp(lp[i]), math.exp(lp[j])
    t_hi = bp["t_first"] if j == 0 else int(bp["t_end"][j - 1])
    t_lo = bp["t_first"] if i == 0 else int(bp["t_end"][i - 1])
    out.update({"leg_bp": (p_hi / p_lo - 1.0) * 1e4, "leg_c": (p_hi - p_lo) * 100.0, "leg_low_px": p_lo, "leg_high_px": p_hi,
                "leg_low_ns": t_lo, "leg_high_ns": t_hi, "since_high_min": (t - t_hi) / MIN_NS, "since_high_vol": 1.0 - j / nb,
                "giveback": (lp[j] - math.log(p_t)) / (lp[j] - lp[i]) if (p_t > 0 and np.isfinite(p_t)) else np.nan})
    return out


# ====================================================================== hindsight (reads the future by design)

class Forward:
    """Section 5: forward windows from each moment on the event day's non-spike prints (hindsight)."""

    def __init__(self, tape: C.Tape):
        spk = C.S2.spike_flags(tape.px)
        self.fts, self.fpx = tape.ts[~spk], tape.px[~spk]
        self.ts, self.CS = tape.ts, tape.CS
        self.tape = tape
        self.n_spikes = int(spk.sum())

    def one(self, t: int, seg: str, key: str, v_pre: float) -> dict:
        tp = self.tape
        limit = tp.t2000 if seg == "after_hours" else tp.seg_end(seg) - 1          # prints at the open / close are auction prints
        limit = min(limit, tp.t2000)
        if key in C.WALL:
            want = t + C.WALL[key] * MIN_NS
            censored = want > limit
            end = min(want, limit)
        else:
            if not (np.isfinite(v_pre) and v_pre > 0):
                return {"state": "v_pre_undefined"}
            i_t = int(np.searchsorted(self.ts, t, "right"))
            k = int(np.searchsorted(self.CS, self.CS[i_t] + C.VOL[key] * v_pre, "left"))
            if k <= self.ts.size and k > i_t:
                tv = int(self.ts[k - 1])
                censored = tv > limit
                end = min(tv, limit)
            else:
                censored, end = True, limit
        e = int(np.searchsorted(self.fts, t, "right"))
        je = int(np.searchsorted(self.fts, end, "right"))
        if e >= je:
            return {"state": "no_print_in_h", "censored": bool(censored)}
        pe, pl = float(self.fpx[e]), float(self.fpx[je - 1])
        seg_px = self.fpx[e:je]
        mx, mn = float(seg_px.max()), float(seg_px.min())
        return {"state": "ok", "censored": bool(censored), "entry_px": pe, "entry_ns": int(self.fts[e]),
                "ret_bp": (pl / pe - 1.0) * 1e4, "ret_c": (pl - pe) * 100.0, "mfe_bp": (mx / pe - 1.0) * 1e4, "mfe_c": (mx - pe) * 100.0,
                "mae_bp": (mn / pe - 1.0) * 1e4, "mae_c": (mn - pe) * 100.0}

    def max_in(self, t: int, minutes: int) -> float:
        """Highest non-spike print in (t, t + minutes], cut at 20:00 (G3's hindsight clause)."""
        end = min(t + minutes * MIN_NS, self.tape.t2000)
        e, je = int(np.searchsorted(self.fts, t, "right")), int(np.searchsorted(self.fts, end, "right"))
        return float(self.fpx[e:je].max()) if je > e else np.nan


# ====================================================================== one event

def build_event(rec: dict, cfg: dict, size_mult: float | None, halts: list, on_window=None, tape: C.Tape | None = None,
                quotes: dict | None | str = "read", with_hindsight: bool = True) -> dict:
    """Every moment of one event: T1 grid and flags, T2 presence and cost, T3 relative, T4 scale-free and context, and
    the section 5 hindsight columns. `on_window(info)` is called for every valid scale-free window (T5's controls
    read the same windows the build does)."""
    eid, date = rec["event_id"], rec["event_date_canonical"]
    tape = tape if tape is not None else C.Tape(eid, date)
    q = C.read_quotes(eid) if quotes == "read" else quotes
    book = C.QuoteBook(q, date, size_mult)
    geo = (tape.op, tape.cl)
    nb = cfg["measures"]["scale_free_ladder"]["buckets"]
    stop = cfg["measures"]["scale_free_ladder"]["count_stop_collapsed_trades"]
    kmax = cfg["measures"]["scale_free_ladder"]["k_max"]
    tau = int(rec["tau_ns"])
    shs = rec.get("shs")
    shs = float(shs) if shs is not None and np.isfinite(shs) and shs > 0 else None
    v_pre = float(rec["v_pre"]) if rec.get("v_pre") is not None and np.isfinite(rec["v_pre"]) else np.nan
    js, tms, ws = C.moment_grid(tau, tape.t2000, cfg)
    fwd = Forward(tape) if with_hindsight else None
    rows, rrows, srows = [], [], []
    prev_t = None
    for j, t, w in zip(js.tolist(), tms.tolist(), ws.tolist()):
        seg = tape.segment(t)
        n_before = int(np.searchsorted(tape.ts, t, "right"))
        row = {"event_id": eid, "j": j, "t_ns": t, "weight": w, "minutes_since_tau": (t - tau) / MIN_NS, "segment": seg,
               "in_auction_minute": seg in B1.AUCTION,
               "no_print_since_last_moment": False if prev_t is None else bool(n_before == int(np.searchsorted(tape.ts, prev_t, "right"))),
               "tcs_state": C.S2.tcs_state(int(rec["tau_exact_ns"]), tau, rec.get("tau_mb_exact_ns"), t)}
        last_print = int(tape.ts[n_before - 1]) if n_before else tape.t0400
        in_label = any(s <= t < e for s, e in halts)
        row["halt_state"] = "label" if in_label else ("gap_proxy" if (seg == "regular" and t - last_print >= C.HALT_GAP_NS) else "none")
        row["shares_0400_t"] = float(tape.CS[n_before])
        if shs is not None:
            assert rec["shs_asof_ns"] is not None and int(rec["shs_asof_ns"]) < t and int(rec["shs_accepted_ns"]) < t, "share count not known at t"
            row["turnover_t"] = row["shares_0400_t"] / shs
        prev_t = t
        qv = book.view(t)
        row.update(quote_state(qv, t, size_mult))
        if with_hindsight:
            for key in C.HORIZONS:
                f = fwd.one(t, seg if seg in C.SEGS else "regular", key, v_pre) if seg in C.SEGS else {"state": "auction_moment"}
                for kk, vv in f.items():
                    row[f"{key}_{kk}"] = vv
            row["g3_fwd_max_px"] = fwd.max_in(t, 60)
        if seg not in C.SEGS:
            row["measure_state"] = "auction_minute"
            rows.append(row)
            continue
        v = tape.view(t, seg)
        H = t - v["lo"]
        if H <= 0:
            row["measure_state"] = "at_segment_start"
            rows.append(row)
            continue
        row["measure_state"] = "ok"
        row["H_min"] = H / MIN_NS
        # ---------------- T2 / T3: the rate ladder
        lad = rate_ladder(v, t, cfg)
        valid_k = []
        for x in lad:
            rr = {"event_id": eid, "j": j, "k": x["k"], "W_s": x["W_s"], "valid": x["valid"], "cls": x["class"], "n_recent": x["n_recent"], "n_older": x["n_older"]}
            if x["valid"]:
                rr.update(rate_measures(v, int(x["win_lo_ns"]), t, x["n_recent"] + x["n_older"], shs, geo))
                valid_k.append(x["k"])
            rrows.append(rr)
        row["n_rate_rungs_valid"] = len(valid_k)
        rate0 = v["ct"].size / (H / MIN_NS)
        row["rate_rung0"] = rate0
        if valid_k:
            kf = max(valid_k)
            fr = [r for r in rrows[-len(lad):] if r["k"] == kf][0]
            row["finest_rate_rung"] = kf
            for c in ("trade_rate", "raw_rate", "dollar_flow", "turnover_rate", "n_eff", "top3_share", "move_per_trade", "n_orders"):
                row[c] = fr[c]
            a_f = t - int(round(H / 2.0 ** kf))
            row["spread_tw_bp"], row["spread_tw_c"], row["spread_tw_cover"] = tw_spread(qv, a_f, t)
            row["act_ratio"] = fr["trade_rate"] / rate0 if rate0 > 0 else np.nan
        # ---------------- T4: the scale-free ladder
        k_valid, R_mid, R_vwap, meta = [], [], [], []
        cutoff = None
        for k in range(kmax + 1):
            W = H / (2.0 ** k)
            if W / 2.0 < 10_000_000:                               # the 10 ms half-window floor (the D26 tolerance)
                break
            a = t - int(round(W))
            ncol = v["ct"].size - int(np.searchsorted(v["ct"], a, "left"))
            if ncol < stop:
                cutoff = k
                break
            bp = bucket_path(v, qv, a, t, nb, geo)
            if bp is None:
                cutoff = k
                break
            k_valid.append(k)
            meta.append((k, a, W / 1e9, ncol, bp))
            R_vwap.append(np.diff(bp["lp_vwap"]))
            R_mid.append(np.diff(bp["lp_mid"]) if bp["mid_ok"] else np.full(nb, np.nan))
        row["n_valid_rungs"] = len(k_valid)
        row["scale_free_cutoff_k"] = cutoff
        if k_valid:
            st = {"vwap": scale_free(np.array(R_vwap)), "mid": scale_free(np.array(R_mid))}
            prim = ["mid" if m[4]["mid_ok"] else "vwap" for m in meta]      # A1.2: the midpoint, VWAP where the window has no midpoint path
            for ii, (k, a, W_s, ncol, bp) in enumerate(meta):
                sr = {"event_id": eid, "j": j, "k": k, "W_s": W_s, "n_collapsed": ncol, "shares": bp["V"], "mid_ok": bp["mid_ok"],
                      "price_basis": "mid" if prim[ii] == "mid" else "vwap_fallback"}
                for bs in C.BASES:
                    for c, arr in st[bs].items():
                        sr[f"{c}_{bs}"] = float(arr[ii])
                sr["er"] = sr[f"er_{prim[ii]}"]
                srows.append(sr)
                if on_window is not None:
                    on_window({"event_id": eid, "j": j, "k": k, "t": t, "a": a, "seg": seg, "v": v, "qv": qv, "bp": bp, "W_s": W_s,
                               "r_vwap": R_vwap[ii], "r_mid": R_mid[ii] if bp["mid_ok"] else None, "spread_bp_t": row.get("spread_bp_t", np.nan),
                               "v_pre": v_pre, "geo": geo, "event_index": rec.get("event_index")})
            kf = k_valid[-1]
            ii = len(k_valid) - 1
            row["finest_rung"] = kf
            fb = meta[ii][4]
            row["finest_mid_ok"] = fb["mid_ok"]
            row["price_basis"] = "mid" if prim[ii] == "mid" else "vwap_fallback"
            sp = row.get("spread_bp_t", np.nan)
            for bs in C.BASES:
                for c in ("er", "er0", "er_rel"):
                    row[f"{c}_{bs}"] = float(st[bs][c][ii])
                s2 = float(st[bs]["sum_r2"][ii])
                for key in C.HORIZONS:
                    if key in C.WALL:
                        sig = math.sqrt(s2 / fb["W_min"] * C.WALL[key]) if np.isfinite(s2) else np.nan
                    else:
                        sig = math.sqrt(s2 / fb["V"] * C.VOL[key] * v_pre) if (np.isfinite(s2) and np.isfinite(v_pre)) else np.nan
                    row[f"sigma_{key}_{bs}"] = sig
                    if not (np.isfinite(sp) and np.isfinite(sig)):
                        row[f"cost_noise_{key}_{bs}"] = np.nan
                    else:                                          # a flat window has zero own noise: any cost is infinite against it
                        row[f"cost_noise_{key}_{bs}"] = sp / (1e4 * sig) if sig > 0 else np.inf
            pb = prim[ii]
            for c in ("er", "er0", "er_rel"):
                row[c] = row[f"{c}_{pb}"]
            for key in C.HORIZONS:
                row[f"sigma_{key}"] = row[f"sigma_{key}_{pb}"]
                row[f"cost_noise_{key}"] = row[f"cost_noise_{key}_{pb}"]
            # every valid rung k >= 1 (the "at every valid rung" option): the largest er over those rungs, each on its own primary
            # basis; unavailable when a rung's er is undefined (a flat window)
            sel = [ii2 for ii2, m in enumerate(meta) if m[0] >= 1]
            vals = np.array([st[prim[ii2]]["er"][ii2] for ii2 in sel]) if sel else np.array([])
            row["er_allmax"] = float(vals.max()) if (sel and np.isfinite(vals).all()) else np.nan
            row["n_valid_rungs_k1"] = len(sel)
            # ---------------- T4: context on rung 0
            if meta[0][0] == 0:
                bp0 = meta[0][4]
                for bs in C.BASES:
                    p_t = row.get("mid_t", np.nan) if bs == "mid" else float(v["px"][-1])
                    cx = context(bp0, bs, p_t, t, nb) if (bs == "vwap" or bp0["mid_ok"]) else {"leg_state": "no_path"}
                    for c, val in cx.items():
                        row[f"{c}_{bs}"] = val
                cb = prim[0]
                row["context_basis"] = "mid" if cb == "mid" else "vwap_fallback"
                for c in ("leg_state", "leg_s", "leg_bp", "leg_c", "leg_low_px", "leg_high_px", "leg_low_ns", "leg_high_ns", "since_high_min",
                          "since_high_vol", "giveback"):
                    row[c] = row.get(f"{c}_{cb}", np.nan)
        rows.append(row)
    return {"rows": rows, "rate_rungs": rrows, "sf_rungs": srows, "n_prints": int(tape.ts.size), "n_quotes": 0 if q is None else int(q["ts"].size),
            "n_spikes": fwd.n_spikes if fwd is not None else None}


# ====================================================================== section 6 tests

def causality_test() -> dict:
    """A print and a quote 1 ns after t fed into every measure function; each must raise with CAUSAL_MSG."""
    d = "2021-03-15"
    op, cl = B1.rth_bounds_ns(d)
    t = op + 120 * MIN_NS
    lo = op + MIN_NS
    ts = np.linspace(lo, t, 2000).astype(np.int64)
    px = 1.0 + 0.01 * np.sin(np.arange(ts.size))
    sz = np.full(ts.size, 100.0)

    def view(ts_, px_, sz_):
        return {"t": t, "seg": "regular", "lo": lo, "ts": ts_, "px": px_, "sz": sz_, "ct": ts_, "cid": np.arange(ts_.size),
                "CS": np.r_[0.0, np.cumsum(sz_)], "CD": np.r_[0.0, np.cumsum(px_ * sz_)]}

    def qview(qts):
        n = qts.size
        return {"g": 1, "t": t, "seg_lo": op, "ts": qts, "valid": np.ones(n, dtype=bool), "C_bp": np.zeros(n + 1), "C_c": np.zeros(n + 1),
                "C_d": np.zeros(n + 1), "sbp": np.zeros(n), "spr": np.zeros(n), "vts": qts, "vbid": np.full(n, 0.99), "vask": np.full(n, 1.01),
                "vbsz": np.full(n, 100.0), "vasz": np.full(n, 100.0), "vmid": np.ones(n), "vlogmid": np.zeros(n), "cts": qts}

    good, bad = view(ts, px, sz), view(np.r_[ts, t + 1], np.r_[px, 1.0], np.r_[sz, 100.0])
    qgood, qbad = qview(ts[::10]), qview(np.r_[ts[::10], t + 1])
    a = t - 30 * MIN_NS
    cfg = C.load_cfg()
    cases = {
        "quote_state/quote": lambda: quote_state(qbad, t, 1.0),
        "tw_spread/quote": lambda: tw_spread(qbad, a, t),
        "rate_ladder/print": lambda: rate_ladder(bad, t, cfg),
        "rate_measures/print": lambda: rate_measures(bad, a, t, 100, 1e6, (op, cl)),
        "bucket_path/print": lambda: bucket_path(bad, qgood, a, t, 32, (op, cl)),
        "bucket_path/quote": lambda: bucket_path(good, qbad, a, t, 32, (op, cl)),
    }
    out = {}
    for name, fn in cases.items():
        try:
            fn()
            out[name] = "DID NOT RAISE"
        except AssertionError as e:
            out[name] = "raised" if (C.CAUSAL_MSG in str(e) or "after tau" in str(e)) else f"raised other: {e}"
    quote_state(qgood, t, 1.0), tw_spread(qgood, a, t), rate_ladder(good, t, cfg), rate_measures(good, a, t, 100, 1e6, (op, cl))
    bucket_path(good, qgood, a, t, 32, (op, cl))
    out["clean_inputs_do_not_raise"] = "ok"
    out["passes"] = all(x in ("raised", "ok") for x in out.values())
    return out


def segment_test() -> dict:
    """Windows that cross a segment boundary or hold an auction minute must raise with SEGMENT_MSG."""
    d = "2021-03-15"
    op, cl = B1.rth_bounds_ns(d)
    t0400 = B1.et_ns(d, "04:00:00")
    cases = {
        "regular_window_reaching_into_open_auction": (op + 30 * NS, op + 5 * MIN_NS, "regular", op + MIN_NS),
        "regular_window_reaching_premarket": (op - 5 * MIN_NS, op + 10 * MIN_NS, "regular", op + MIN_NS),
        "after_hours_window_holding_close_auction": (cl + 10 * NS, cl + 10 * MIN_NS, "after_hours", cl + MIN_NS),
        "premarket_window_before_0400": (t0400 - MIN_NS, t0400 + 10 * MIN_NS, "premarket", t0400),
        "t_in_auction_minute": (op + 5 * NS, op + 30 * NS, "auction_open", op),
    }
    out = {}
    for name, (a, t, seg, lo) in cases.items():
        try:
            C.assert_window(a, t, seg, lo, op, cl)
            out[name] = "DID NOT RAISE"
        except AssertionError as e:
            out[name] = "raised" if C.SEGMENT_MSG in str(e) else f"raised other: {e}"
    # and through a measure function: rate_measures and bucket_path on a window reaching into the open auction
    ts = np.linspace(op, op + 20 * MIN_NS, 500).astype(np.int64)
    v = {"t": int(ts[-1]), "seg": "regular", "lo": op + MIN_NS, "ts": ts, "px": np.ones(ts.size), "sz": np.full(ts.size, 100.0), "ct": ts,
         "cid": np.arange(ts.size), "CS": np.r_[0.0, np.cumsum(np.full(ts.size, 100.0))], "CD": np.r_[0.0, np.cumsum(np.full(ts.size, 100.0))]}
    for name, fn in {"rate_measures_window_in_auction": lambda: rate_measures(v, op + 10 * NS, int(ts[-1]), 100, 1e6, (op, cl)),
                     "bucket_path_window_in_auction": lambda: bucket_path(v, None, op + 10 * NS, int(ts[-1]), 32, (op, cl))}.items():
        try:
            fn()
            out[name] = "DID NOT RAISE"
        except AssertionError as e:
            out[name] = "raised" if C.SEGMENT_MSG in str(e) else f"raised other: {e}"
    C.assert_window(op + 2 * MIN_NS, op + 30 * MIN_NS, "regular", op + MIN_NS, op, cl)
    out["inside_regular_does_not_raise"] = "ok"
    out["passes"] = all(x in ("raised", "ok") for x in out.values())
    return out


def bucket_equality_test(n_windows: int = 200, seed: int = 20260930) -> dict:
    """buckets_core against Brief 1's instruments.bucketize on random tapes (prints straddling edges, zero sizes)."""
    rng = np.random.default_rng(seed)
    worst_p, worst_t = 0.0, 0
    for _ in range(n_windows):
        n = int(rng.integers(64, 3000))
        ts = np.sort(rng.integers(0, 10**12, n)).astype(np.int64)
        px = np.exp(np.cumsum(rng.normal(0, 0.002, n))) * rng.uniform(0.2, 20)
        sz = rng.choice([0, 1, 7, 50, 100, 250, 1000, 5000], size=n).astype(np.float64)
        sz[0] = max(sz[0], 100.0)
        ref = I.bucketize(ts, px, sz, 32)
        cv, cd = np.cumsum(sz), np.cumsum(px * sz)
        b = buckets_core(ts, px, cv, cd, 32)
        worst_p = max(worst_p, float(np.max(np.abs(b["vwap"] / ref["vwap"] - 1.0))))
        worst_t = max(worst_t, int(np.max(np.abs(b["t_end"] - ref["t_end"]))))
    return {"windows": n_windows, "max_rel_vwap_diff": worst_p, "max_t_end_diff_ns": worst_t,
            "passes": bool(worst_p < 1e-9 and worst_t == 0)}
