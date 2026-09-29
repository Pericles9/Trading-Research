"""
Shape classifier S2, T1 -- Group A: everything known at tau, one row per event.

Sources (brief section 3, "from the b2 and S1 artifacts, or recomputed"):
  S1 s1_events           timing, run-up descriptors, price tier, gap_share, first print
  b2 t2_attention        a2_ignition, filing_24h, last_form_before_tau, shares 04:00 -> tau
  b2 t2_a2_rungs         accel_k0..k4 (valid rungs only; windows end at tau)
  b2 t2_cross_sectional  live_n per liveness, flow_share at rung 0 per liveness
  b1 t2_tau              tau_ns_mb, for the R1 causal tau_close_sensitive state (built per decision time in T2)
  pre-tau tick pass      pre-tau trade rate and dollar flow (D26 collapse), ref_shares for the volume checkpoints;
                         ticks are sliced to ts <= tau before anything is computed
  R3 (Cooper)            shares outstanding and the dilution flag re-anchored at tau from F1's raw SEC archive
  R2 (Cooper)            short interest: latest settlement published (assumed 10 XNYS sessions later) before the
                         event date, from the raw vendor files
Every input carries the latest data timestamp it reads (ts__<input>); T1 asserts each <= tau.

Writes artifacts/t1_group_a.parquet (inputs, carried columns c__*, latest timestamps ts__*),
t1_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t1_group_a.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

C1 = S.C1
CFG = S.load_cfg()
TOL_MS = 10.0
SEC_SUB = str(S.src("sec_submissions"))
SEC_CF = str(S.src("sec_companyfacts"))
SI_RAW = str(S.src("short_interest_raw"))
NS72 = 72 * 3600 * S.NS
NS24 = 24 * 3600 * S.NS


# ------------------------------------------------------------------ pre-tau tick pass

def crossing_print(ts: np.ndarray, px: np.ndarray, tau_stored: int, p_tau: float) -> int | None:
    """The crossing print's own timestamp: the earliest print at the tau price within the stored value's float64
    rounding bound (+-128 ns)."""
    lo, hi = np.searchsorted(ts, tau_stored - S.TAU_ROUND_NS, "left"), np.searchsorted(ts, tau_stored + S.TAU_ROUND_NS, "right")
    c = [int(ts[i]) for i in range(lo, hi) if px[i] == p_tau]
    return min(c) if c else None


def pre_tau(rec: dict) -> dict:
    tr = C1.read_trades(rec["event_id"], with_conditions=False)
    date, tau_s = rec["event_date_canonical"], int(rec["tau_ns"])
    t_ex = crossing_print(tr["ts"], tr["px"], tau_s, float(rec["tau_price"]))
    assert t_ex is not None, f"{rec['event_id']}: no print at the tau price within 128 ns of the stored tau"
    tau = max(tau_s, t_ex)                       # tau_d: the decision time at tau (T0: stored tau is float64-rounded)
    t0400 = C1.et_ns(date, "04:00:00")
    n_between = int(((tr["ts"] > t_ex) & (tr["ts"] <= tau_s)).sum())
    a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], tau, "right"))
    ts, px, sz = tr["ts"][a:b].copy(), tr["px"][a:b].copy(), tr["sz"][a:b].copy()     # ts <= tau_d only
    del tr
    assert ts.size and ts[-1] <= tau, "pre-tau slice reaches past tau_d"
    op, cl = C1.rth_bounds_ns(date)
    seg = C1.clock_segment(tau, op, cl)
    s0 = C1.segment_start_ns(seg, date, op, cl)
    lo = t0400 if s0 is None else s0
    m = ts >= lo
    ct = C1.collapse_tol(ts[m], TOL_MS)
    dur_min = max(tau - lo, S.NS) / S.MIN_NS
    out = {"event_id": rec["event_id"], "tau_exact_ns": t_ex, "tau_d_ns": tau, "n_prints_after_crossing_to_stored": n_between,
           "segment_check": seg, "first_print_ns": int(ts[0]),
           "pre_window": "segment" if s0 is not None else "0400_auction_minute", "pre_lo_ns": int(lo),
           "pre_n_collapsed": int(ct.size), "pre_dollars": float((px[m] * sz[m]).sum()), "pre_shares": float(sz[m].sum()),
           "pre_minutes": (tau - lo) / S.MIN_NS, "ts__pre": int(ts[m][-1]) if m.any() else int(lo)}
    out["pre_trades_per_min"] = out["pre_n_collapsed"] / dur_min
    out["pre_dollars_per_min"] = out["pre_dollars"] / dur_min
    out["ref_shares"] = float(sz[m].sum()) if s0 is not None else np.nan          # [segment start, tau]
    return out


# ------------------------------------------------------------------ SEC archive (R3)

def cik_filings(cik: str) -> pd.DataFrame:
    """research/fundamentals_f1/t3_filing_index.py's parse (primary + older-history files, acceptanceDateTime
    as UTC, empty values dropped, dedup on accession), with `items` kept for the 8-K Item 3.02 rule."""
    frames = []
    for p in [os.path.join(SEC_SUB, f"{cik}.json")] + sorted(glob.glob(os.path.join(SEC_SUB, f"{cik}__*.json"))):
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        rec = d.get("filings", {}).get("recent", d)
        n = len(rec.get("accessionNumber", []))
        frames.append(pd.DataFrame({"accession": rec.get("accessionNumber", []), "form": rec.get("form", []),
                                    "acceptance": rec.get("acceptanceDateTime", []), "items": rec.get("items", [""] * n)}))
    if not frames:
        return pd.DataFrame(columns=["accession", "form", "items", "accepted_ns"])
    f = pd.concat(frames, ignore_index=True)
    f = f[f["acceptance"].astype(str) != ""]
    t = pd.to_datetime(f["acceptance"], utc=True, errors="coerce")
    f = f[t.notna()].copy()
    f["accepted_ns"] = t[t.notna()].astype("int64")
    return f.drop_duplicates("accession")[["accession", "form", "items", "accepted_ns"]]


def cik_shares(cik: str) -> pd.DataFrame:
    """research/fundamentals_f1/t4_shares_outstanding.py's extraction: dei:EntityCommonStockSharesOutstanding,
    units shares -> (shares, asof_date = end, form, accession); dropna on shares and asof; dedup."""
    p = os.path.join(SEC_CF, f"{cik}.json")
    if not os.path.exists(p):
        return pd.DataFrame(columns=["shares", "asof_date", "source_form", "accession"])
    d = json.load(open(p))
    try:
        recs = d["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"]
    except KeyError:
        recs = []
    o = pd.DataFrame([{"shares": r.get("val"), "asof_date": r.get("end"), "source_form": r.get("form"), "accession": r.get("accn")} for r in recs])
    if o.empty:
        return pd.DataFrame(columns=["shares", "asof_date", "source_form", "accession"])
    return o.dropna(subset=["shares", "asof_date"]).drop_duplicates(subset=["accession", "asof_date"])


def fundamentals_for_cik(args) -> list[dict]:
    cik, evs, dil_forms = args
    fl = cik_filings(cik)
    obs = cik_shares(cik).merge(fl[["accession", "accepted_ns"]], on="accession", how="left").dropna(subset=["accepted_ns"])
    t = pd.to_datetime(obs["asof_date"], utc=True, errors="coerce")
    obs = obs[t.notna()].copy()
    obs["asof_ns"] = t[t.notna()].astype("int64")
    fl = fl.sort_values("accepted_ns")
    acc = fl["accepted_ns"].to_numpy(np.int64)
    is_dil = np.array([(f in dil_forms) or (f == "8-K" and isinstance(it, str) and "3.02" in it.split(","))
                       for f, it in zip(fl["form"], fl["items"])], dtype=bool)
    out = []
    for e in evs:
        tau = int(e["tau_ns"])
        k = int(np.searchsorted(acc, tau, "left"))               # filings accepted strictly before tau: [0, k)
        j = int(np.searchsorted(acc, tau - NS72, "left"))
        last_form = fl["form"].iloc[k - 1] if k > 0 else None
        dil = bool(is_dil[j:k].any() or (k > 0 and last_form in dil_forms))
        n24 = k - int(np.searchsorted(acc, tau - NS24, "left"))
        r = {"event_id": e["event_id"], "n_filings_before_tau": k, "last_form_tau": last_form,
             "last_accepted_tau_ns": int(acc[k - 1]) if k > 0 else None, "filing_24h_recomputed": n24 > 0,
             "dilution_tau": dil, "ts__dilution": int(acc[k - 1]) if k > 0 else None}
        c = obs[(obs["accepted_ns"] < tau) & (obs["asof_ns"] < tau)]
        if len(c):
            c = c.sort_values("accepted_ns", kind="mergesort").iloc[-1]
            r.update({"shs_tau": float(c["shares"]), "shs_tau_asof_ns": int(c["asof_ns"]), "shs_tau_accepted_ns": int(c["accepted_ns"]),
                      "shs_tau_accession": c["accession"], "shs_tau_form": c["source_form"]})
        out.append(r)
    return out


# ------------------------------------------------------------------ short interest (R2)

def short_interest_tau(pop: pd.DataFrame, cik: pd.Series, sessions_lag: int) -> pd.DataFrame:
    rows = []
    for p in glob.glob(os.path.join(SI_RAW, "*.json")):
        c = os.path.basename(p)[:-5]
        for r in json.load(open(p)):
            rows.append((c, r.get("settlement_date"), r.get("short_interest")))
    si = pd.DataFrame(rows, columns=["cik", "settlement_date", "si_shares"]).dropna(subset=["settlement_date"])
    si = si.drop_duplicates(["cik", "settlement_date"])
    cal = C1.xnys()
    sess = cal.sessions.values
    sd = pd.to_datetime(si["settlement_date"]).values
    i = np.searchsorted(sess, sd, side="right")                     # first session strictly after settlement
    si["pub_session"] = pd.to_datetime(sess[np.minimum(i + sessions_lag - 1, len(sess) - 1)])
    pub_ns = {x: C1.et_ns(str(x.date()), "20:00:00") for x in si["pub_session"].unique()}
    si["pub_ns"] = si["pub_session"].map(pub_ns)
    e = pd.DataFrame({"event_id": pop["event_id"], "cik": cik.values, "event_date": pd.to_datetime(pop["event_date_canonical"])})
    x = e.dropna(subset=["cik"]).merge(si, on="cik")
    x = x[x["pub_session"] < x["event_date"]].sort_values("settlement_date").groupby("event_id").tail(1)
    return x[["event_id", "settlement_date", "si_shares", "pub_ns"]].rename(
        columns={"settlement_date": "si_tau_settlement_date", "si_shares": "si_tau_shares", "pub_ns": "ts__short_interest"})


# ------------------------------------------------------------------ main

def main() -> int:
    t_start = time.perf_counter()
    pop = S.load_population()
    recs = pop[["event_id", "event_date_canonical", "tau_ns", "tau_price"]].to_dict("records")

    # ---------------- pre-tau tick pass
    pre = []
    with ProcessPoolExecutor(max_workers=S.B2.cpu_workers()) as ex:
        for n, r in enumerate(ex.map(pre_tau, recs, chunksize=25)):
            pre.append(r)
            if (n + 1) % 3000 == 0:
                print(f"  pre-tau {n + 1:,}/{len(recs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    pre = pd.DataFrame(pre)
    print(f"pre-tau pass {time.perf_counter() - t_start:,.0f}s")

    s1 = pd.read_parquet(S.src("s1_events"), columns=["event_id", "tau_anchor_segment", "gap_share", "runup_available", "runup_u_launch",
                                                       "runup_height_s", "runup_max_drawdown_s", "runup_pushes", "runup_minutes",
                                                       "runup_shares", "runup_sigma_path", "sec_from_0400"])
    at = pd.read_parquet(S.src("b2_attention"), columns=["event_id", "a2_ignition", "a2_state", "filing_24h", "last_form_before_tau",
                                                          "shares_0400_tau", "a3_available", "hours_since_last_filing"])
    rg = pd.read_parquet(S.src("b2_a2_rungs"), columns=["event_id", "k", "valid", "accel", "win_lo_ns", "W_s"])
    xs = pd.read_parquet(S.src("b2_cross_section"), columns=["event_id", "liveness", "live_n", "k", "flow_share", "win_lo_ns"])
    lv = pd.read_parquet(S.src("b2_live_names"), columns=["event_id", "sec_since_own_tau"])
    b1 = pd.read_parquet(S.src("b1_tau"), columns=["event_id", "tau_ns", "tau_ns_mb", "tau_close_sensitive"]).rename(columns={"tau_ns": "tau_ns_b1"})
    fu = pd.read_parquet(S.src("fundamentals"), columns=["event_id", "cik", "t0_ns", "spl_reverse_split_365d", "spl_last_split_ns",
                                                          "spl_last_split_ratio", "spl_quality", "shs_shares_outstanding", "shs_accepted_ns",
                                                          "flg_dilution_form_before_t0", "si_shares_short"])

    d = pop.merge(pre, on="event_id", how="left").merge(s1.drop(columns=["tau_anchor_segment", "sec_from_0400"]), on="event_id", how="left") \
        .merge(at, on="event_id", how="left").merge(b1, on="event_id", how="left").merge(fu, on="event_id", how="left")
    assert len(d) == len(pop)
    assert (d["segment_check"] == d["tau_anchor_segment"]).all(), "tick-pass segment differs from S1's"
    assert (d["tau_ns_b1"] == d["tau_ns"]).all(), "b1 tau differs from S1 tau"

    # ---------------- rungs 0-4
    r = rg[rg["k"].between(0, 4)]
    assert (r["win_lo_ns"].notna() | ~r["valid"]).all()
    for k in range(5):
        rk = r[r["k"] == k].set_index("event_id")
        d[f"accel_valid_k{k}"] = d["event_id"].map(rk["valid"]).fillna(False).astype(bool)
        d[f"accel_k{k}"] = d["event_id"].map(rk["accel"].where(rk["valid"]))
    # rung windows are [tau - W_k, tau]; b2 asserted causality (attention.assert_segment_windows) on every ladder
    d["ts__accel"] = d["tau_ns"]

    # ---------------- cross-section
    for L in ("15", "60", "rest_of_session"):
        g = xs[xs["liveness"] == L]
        ln = g.drop_duplicates("event_id").set_index("event_id")["live_n"]
        tag = "rest" if L == "rest_of_session" else L
        d[f"live_n_{tag}"] = d["event_id"].map(ln).astype(float)
        f0 = g[g["k"] == 0].set_index("event_id")["flow_share"]
        d[f"flow_share_{tag}_k0"] = d["event_id"].map(f0)
    assert (lv["sec_since_own_tau"] >= 0).all(), "a live name crossed after the crosser's tau (stored values)"
    lvx = pd.read_parquet(S.src("b2_live_names"), columns=["event_id", "live_event_id"])
    ex_map = d.set_index("event_id")["tau_exact_ns"]
    lvx["live_exact"] = lvx["live_event_id"].map(ex_map)
    assert lvx["live_exact"].notna().all(), "a live name outside the population"
    latest_live = lvx.groupby("event_id")["live_exact"].max()
    # live sets: other names' crossings (their exact prints) and windows ending at the stored tau (<= tau_d)
    d["ts__cross_section"] = np.fmax(d["event_id"].map(latest_live).astype(float), d["tau_ns"].astype(float))

    # ---------------- fundamentals re-anchored at tau (R3)
    dil_forms = set(json.load(open(S.REPO / "config/fundamentals_f1.json"))["dilution_form_set"]["minimum_forms"]) - {"8-K (Item 3.02)"}
    by_cik = {}
    for e in d.dropna(subset=["cik"]).itertuples():
        by_cik.setdefault(e.cik, []).append({"event_id": e.event_id, "tau_ns": int(e.tau_d_ns)})
    fres = []
    with ProcessPoolExecutor(max_workers=S.B2.cpu_workers()) as ex:
        for part in ex.map(fundamentals_for_cik, [(c, v, dil_forms) for c, v in by_cik.items()], chunksize=8):
            fres.extend(part)
    fr = pd.DataFrame(fres)
    d = d.merge(fr, on="event_id", how="left")
    print(f"fundamentals re-anchored {time.perf_counter() - t_start:,.0f}s")
    # E1's correction rule with the tau-anchored count (research/fundamental_exploration/common.py)
    zero = d["shs_tau"] == 0
    need = d["spl_last_split_ns"].notna() & d["shs_tau_asof_ns"].notna() & (d["shs_tau_asof_ns"] < d["spl_last_split_ns"]) & ~zero
    d["shs_tau_corrected"] = np.where(need, d["shs_tau"] * d["spl_last_split_ratio"], d["shs_tau"])
    d.loc[zero, "shs_tau_corrected"] = np.nan
    d["shs_tau_correction_applied"] = need
    d["turnover_tau"] = d["shares_0400_tau"] / d["shs_tau_corrected"]
    d["ts__shares"] = d["shs_tau_accepted_ns"]
    d["ts__reverse_split"] = d["spl_last_split_ns"]

    # ---------------- short interest (R2)
    lag = 10
    si = short_interest_tau(pop, d["cik"], lag)
    d = d.merge(si, on="event_id", how="left")
    d["short_interest_share"] = d["si_tau_shares"] / d["shs_tau_corrected"]

    # ---------------- filings (b2, accepted < tau), cross-checked against the recomputation
    has = d["a3_available"].fillna(False).astype(bool)
    chk_24 = (d.loc[has, "filing_24h"].astype(bool) == d.loc[has, "filing_24h_recomputed"].fillna(False).astype(bool)).mean()
    chk_form = (d.loc[has, "last_form_before_tau"].fillna("none") == d.loc[has, "last_form_tau"].fillna("none")).mean()
    d["ts__filings"] = d["last_accepted_tau_ns"]

    # ---------------- model inputs
    grp = CFG["inputs"]["group_a"]["last_form_groups"]
    fmap = {f: gname for gname, fs in grp.items() if not gname.startswith("_") for f in fs}
    lf = d["last_form_before_tau"]
    d["last_form"] = np.where(~has, None, np.where(lf.isna(), "none", lf.map(fmap).fillna("other")))
    lg = lambda x: np.log10(np.where(np.asarray(x, dtype=float) > 0, np.asarray(x, dtype=float), np.nan))  # noqa: E731
    A = pd.DataFrame({"event_id": d["event_id"]})
    A["tod_h"] = d["sec_from_0400"] / 3600.0
    A["segment"] = d["tau_anchor_segment"]
    A["auction_minute"] = d["tau_anchor_segment"].isin(C1.AUCTION)
    A["tau_is_first_print"] = d["first_print_ns"] == d["tau_exact_ns"]
    for c in ("gap_share", "runup_u_launch", "runup_height_s", "runup_max_drawdown_s", "runup_pushes"):
        A[c] = d[c].astype(float)
    A["log10_runup_minutes"] = lg(d["runup_minutes"])
    A["log10_runup_shares"] = lg(d["runup_shares"])
    A["log10_turnover"] = np.log10(np.clip(d["turnover_tau"].astype(float), 1e-7, None))
    for k in range(5):
        A[f"accel_k{k}"] = d[f"accel_k{k}"].astype(float)
        A[f"accel_valid_k{k}"] = d[f"accel_valid_k{k}"]
    A["log10_pre_trades_per_min"] = lg(d["pre_trades_per_min"])
    A["log10_pre_dollars_per_min"] = lg(d["pre_dollars_per_min"])
    A["a2_ignition"] = d["a2_ignition"].astype("boolean")
    for t in ("15", "60", "rest"):
        A[f"live_n_{t}"] = d[f"live_n_{t}"]
        A[f"flow_share_{t}_k0"] = d[f"flow_share_{t}_k0"]
    A["filing_24h"] = d["filing_24h"].where(has).astype("boolean")
    A["last_form"] = d["last_form"]
    A["dilution_tau"] = d["dilution_tau"].where(d["cik"].notna()).astype("boolean")
    A["reverse_split_365d"] = d["spl_reverse_split_365d"].astype("boolean")
    A["short_interest_share"] = d["short_interest_share"]
    A["log10_shares_outstanding"] = lg(d["shs_tau"])
    A["price_tier"] = d["price_tier"]
    # carried, not inputs
    keep = ["tau_ns", "tau_exact_ns", "tau_d_ns", "n_prints_after_crossing_to_stored", "tau_price", "ticker", "year", "event_date_canonical", "tau_ns_mb", "tau_close_sensitive", "ref_shares", "pre_trades_per_min",
            "pre_dollars_per_min", "pre_lo_ns", "pre_window", "runup_available", "runup_sigma_path", "runup_minutes", "cik", "t0_ns",
            "shs_tau", "shs_tau_corrected", "shs_tau_accepted_ns", "shs_tau_asof_ns", "shs_tau_accession", "shs_shares_outstanding", "shs_accepted_ns",
            "dilution_tau", "flg_dilution_form_before_t0", "si_tau_settlement_date", "si_tau_shares", "si_shares_short", "turnover_tau",
            "ts__pre", "ts__accel", "ts__cross_section", "ts__shares", "ts__dilution", "ts__reverse_split", "ts__short_interest", "ts__filings"]
    for c in keep:
        A[f"c__{c}" if not c.startswith("ts__") else c] = d[c].to_numpy()
    A["sigma_pre"] = d["runup_sigma_path"] / np.sqrt(d["runup_minutes"])        # log units per sqrt(minute), from the run-up
    A.loc[~d["runup_available"].fillna(False).astype(bool), "sigma_pre"] = np.nan
    A["ts__first_print"] = d["first_print_ns"]
    A["ts__timing"] = d["tau_d_ns"]
    A["ts__runup"] = d["tau_ns"]                   # S1 run-up: prints in [segment start, stored tau]
    A["ts__turnover"] = np.fmax(d["tau_ns"].astype(float), d["shs_tau_accepted_ns"].astype(float))
    A["config_hash"] = S.cfg_hash()

    # ---------------- T0 assertion on Group A: every latest timestamp <= tau, per event
    tau = d["tau_d_ns"].astype("int64").to_numpy()
    viol = {}
    for c in [c for c in A.columns if c.startswith("ts__")]:
        v = pd.to_numeric(A[c], errors="coerce").to_numpy(dtype=float)
        bad = np.isfinite(v) & (v > tau)
        viol[c] = int(bad.sum())
    A.to_parquet(S.art("t1_group_a.parquet"), index=False)
    assert all(v == 0 for v in viol.values()), f"HARD STOP row 1 (Group A): {viol}"

    # ---------------- verification against F1 where the anchors cannot differ
    same_shs = d["shs_tau"].eq(d["shs_shares_outstanding"]) | (d["shs_tau"].isna() & d["shs_shares_outstanding"].isna())
    summary = {
        "config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1), "events": int(len(A)),
        "latest_timestamp_violations_group_a": viol,
        "tau_rounding": {"stored_multiple_of_256": int((d["tau_ns"] % 256 == 0).sum()), "exact_equals_stored": int((d["tau_exact_ns"] == d["tau_ns"]).sum()),
                         "crossing_after_stored": int((d["tau_exact_ns"] > d["tau_ns"]).sum()), "crossing_before_stored": int((d["tau_exact_ns"] < d["tau_ns"]).sum()),
                         "max_abs_ns": int((d["tau_exact_ns"] - d["tau_ns"]).abs().max()),
                         "events_with_prints_after_crossing_up_to_stored": int((d["n_prints_after_crossing_to_stored"] > 0).sum()),
                         "prints_after_crossing_up_to_stored": int(d["n_prints_after_crossing_to_stored"].sum()),
                         "live_names_crossing_after_tau_d": int((d["event_id"].map(latest_live).astype(float) > d["tau_d_ns"].astype(float)).sum())},
        "pre_window": d["pre_window"].value_counts().to_dict(),
        "ref_shares_defined": int(d["ref_shares"].notna().sum()),
        "tau_is_first_print": int(A["tau_is_first_print"].sum()),
        "shares_tau": {"available": int(d["shs_tau"].notna().sum()), "f1_t0_available": int(d["shs_shares_outstanding"].notna().sum()),
                       "equal_to_f1": int(same_shs.sum()), "differs_from_f1": int((~same_shs).sum()),
                       "lnsr_2024_11_07": d.loc[d["event_id"] == "LNSR_2024-11-07_31.57", ["shs_tau", "shs_tau_accepted_ns", "shs_shares_outstanding", "shs_accepted_ns"]].to_dict("records"),
                       "correction_applied": int(d["shs_tau_correction_applied"].sum())},
        "dilution_tau": {"true": int((d["dilution_tau"] == True).sum()), "f1_t0_true": int((d["flg_dilution_form_before_t0"] == True).sum()),  # noqa: E712
                         "differs_from_f1": int((d["dilution_tau"].fillna(False).astype(bool) != d["flg_dilution_form_before_t0"].fillna(False).astype(bool)).sum())},
        "short_interest_tau": {"available": int(d["si_tau_shares"].notna().sum()), "f1_settlement_dated_available": int(d["si_shares_short"].notna().sum()),
                               "same_value_as_f1": int((d["si_tau_shares"] == d["si_shares_short"]).sum()), "sessions_lag": lag,
                               "settlement_to_event_days_median": float((pd.to_datetime(d["event_date_canonical"]) - pd.to_datetime(d["si_tau_settlement_date"])).dt.days.median())},
        "filings_crosscheck_vs_b2": {"filing_24h_agree": float(chk_24), "last_form_agree": float(chk_form), "events_with_cik_filings": int(has.sum())},
        "sigma_pre_available": int(A["sigma_pre"].notna().sum()),
        "missing_share_by_input": {c: float(A[c].isna().mean()) for c in A.columns if not c.startswith(("ts__", "c__")) and c not in ("event_id", "config_hash")},
    }
    S.write_json("t1_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("seconds", "tau_rounding", "latest_timestamp_violations_group_a", "shares_tau", "dilution_tau", "short_interest_tau",
                                              "filings_crosscheck_vs_b2")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
