"""
Chop regime C1, T6 -- the full build: T1-T4 and the section 5 hindsight columns on every development-slice event with tau
(Amendment 1: no variance ratio; the midpoint primary with a flagged VWAP fallback), plus S2's remaining-path type.

One process per event (measures.build_event, the code the controls exercised). Each worker writes its event's three
tables as parquet parts in the git-ignored cache; the parent merges them per year. Nanosecond columns are carried as
exact Int64 (a column mixing ints and None would otherwise be inferred float64 -- the 256 ns defect S2 recorded).

rem_type: S2's t3a_remaining_labels at tau, w1, w2, w5, w10, w20 joined at moments j = 0, 1, 2, 5, 10, 20, with S2's
checkpoint time asserted equal to the C1 moment.

Writes (git-ignored, regenerable; see t6_manifest.json): artifacts/t6_moments_<year>.parquet, t6_sf_rungs_<year>.parquet,
t6_rate_rungs_<year>.parquet. Tracked: t6_summary.json (coverage, unavailable shares, row 6, basis agreement),
t6_measure_quantiles.parquet (every measure's distribution per segment, weighted by moment-minutes; no outcome column),
t6_manifest.json.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t6_build.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402
import measures as M  # noqa: E402

CFG = C.load_cfg()
PARTS = C.REPO / C.OUT / "cache" / "t6_parts"
NS_COLS = ["t_ns", "leg_low_ns", "leg_high_ns", "leg_low_ns_mid", "leg_high_ns_mid", "leg_low_ns_vwap", "leg_high_ns_vwap"] + \
          [f"{h}_entry_ns" for h in C.HORIZONS]
_HALTS = None
_MULT = None


def halts_for(ticker: str, date: str) -> list:
    global _HALTS
    if _HALTS is None:
        _HALTS = C.B1.load_halt_labels()
    return _HALTS.get(f"{ticker}|{date}", [])


def size_mult(year) -> float | None:
    global _MULT
    if _MULT is None:
        _MULT = {int(y): v["depth_multiplier"] for y, v in C.read_json("t0_summary.json")["quote_size_census"].items()}
    return _MULT.get(int(year))


def frame(rows: list[dict], ns_cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in ns_cols:
        if c in df:
            df[c] = pd.array([None if (r.get(c) is None or (isinstance(r.get(c), float) and np.isnan(r.get(c)))) else int(r.get(c)) for r in rows],
                             dtype="Int64")
    return df


def one(rec: dict) -> dict:
    t0 = time.perf_counter()
    o = M.build_event(rec, CFG, size_mult(rec["year"]), halts_for(rec["ticker"], rec["event_date_canonical"]))
    eid = rec["event_id"]
    m = frame(o["rows"], NS_COLS)
    m.to_parquet(PARTS / f"{eid}__m.parquet", index=False)
    pd.DataFrame(o["rate_rungs"]).to_parquet(PARTS / f"{eid}__r.parquet", index=False)
    pd.DataFrame(o["sf_rungs"]).to_parquet(PARTS / f"{eid}__s.parquet", index=False)
    return {"event_id": eid, "seconds": time.perf_counter() - t0, "n_prints": o["n_prints"], "n_quotes": o["n_quotes"], "n_spikes": o["n_spikes"],
            "moments": len(o["rows"]), "weights": int(m["weight"].sum()) if len(m) else 0,
            "minutes_covered": int((m["t_ns"].max() - int(rec["tau_ns"])) // C.MIN_NS + 1) if len(m) else 0}


def wq(x: np.ndarray, w: np.ndarray, qs) -> list:
    """Weighted quantiles (moment-minute weights), finite values only; inf counted separately by the caller."""
    m = np.isfinite(x)
    x, w = x[m], w[m]
    if not x.size:
        return [np.nan] * len(qs)
    o = np.argsort(x, kind="mergesort")
    cw = np.cumsum(w[o]) / w.sum()
    return [float(x[o][min(np.searchsorted(cw, q, "left"), x.size - 1)]) for q in qs]


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


MEASURES = ["trade_rate", "raw_rate", "dollar_flow", "spread_bp_t", "spread_c_t", "spread_tw_bp", "spread_tw_c", "quote_age_s", "depth_ask_usd", "depth_bid_usd",
            "turnover_t", "turnover_rate", "n_eff", "top3_share", "move_per_trade", "er", "er_mid", "er_vwap", "er_rel", "er0", "er_allmax",
            "leg_s", "leg_bp", "leg_c", "giveback", "since_high_min", "since_high_vol", "act_ratio", "n_valid_rungs", "finest_rung", "n_rate_rungs_valid"] + \
           [f"cost_noise_{h}" for h in C.HORIZONS]


def main() -> int:
    t_start = time.perf_counter()
    pop = C.load_population()
    dev = C.dev_slice(pop)
    if PARTS.exists():
        shutil.rmtree(PARTS)
    PARTS.mkdir(parents=True)
    gi = PARTS.parent / ".gitignore"
    if not gi.exists():
        gi.write_text("# rebuildable cache (T6 parts, T7 strips); never committed\n*\n", encoding="utf-8")
    if len(sys.argv) > 2 and sys.argv[1] == "--limit":                                  # a smoke run of the merge path only
        dev = dev.sample(int(sys.argv[2]), random_state=0).reset_index(drop=True)
    recs = dev.sort_values("n_day_prints", ascending=False).to_dict("records")          # longest first
    res = []
    with ProcessPoolExecutor(max_workers=C.B2.cpu_workers()) as ex:
        for n, r in enumerate(ex.map(one, recs, chunksize=1)):
            res.append(r)
            if (n + 1) % 500 == 0:
                print(f"  {n + 1:,}/{len(recs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    R = pd.DataFrame(res)
    build_s = time.perf_counter() - t_start
    assert (R["weights"] == R["minutes_covered"]).all(), "weights do not sum to the minutes covered"
    print(f"build {build_s:,.0f}s", flush=True)

    # ---------------- S2's remaining-path type at its checkpoints
    rem = pd.read_parquet(C.src("s2_remaining_labels"), columns=["event_id", "time", "rem_state", "rem_type"])
    ck = pd.read_parquet(C.src("s2_checkpoints"), columns=["event_id", "time", "state", "d_ns"])
    rem = rem[rem["time"].isin(C.REM_TIMES)].merge(ck, on=["event_id", "time"], how="left")
    rem["j"] = rem["time"].map(C.REM_TIMES)

    ev = dev.set_index("event_id")
    evcols = ["ticker", "year", "event_date_canonical", "tau_segment", "price_tier", "dilution", "quotes_ingested", "quotes_event_day", "shs_quality", "event_index",
              "v_pre", "tau_price"]
    manifest, quant, cover = {}, [], {}
    agree = []
    seg_tot = {}
    rows6 = {}
    for y in sorted(dev["year"].unique()):
        ids = dev.loc[dev["year"] == y, "event_id"]
        for kind, name in (("m", "moments"), ("s", "sf_rungs"), ("r", "rate_rungs")):
            parts = [pd.read_parquet(PARTS / f"{e}__{kind}.parquet") for e in ids]
            df = pd.concat([p for p in parts if len(p)], ignore_index=True)
            if kind == "m":
                for c in NS_COLS:
                    if c in df:
                        df[c] = C.as_int64(df[c])
                for c in evcols:
                    df[c] = df["event_id"].map(ev[c])
                df["moment_uid"] = C.moment_uid(df["event_index"], df["j"])
                rr = rem[rem["event_id"].isin(ids)]
                df = df.merge(rr[["event_id", "j", "rem_type", "rem_state", "d_ns", "state"]], on=["event_id", "j"], how="left")
                chk = df["d_ns"].notna()
                assert (C.as_int64(df.loc[chk, "d_ns"]) == df.loc[chk, "t_ns"]).all(), "S2 checkpoint time differs from the C1 moment"
                df = df.drop(columns=["d_ns", "state"]).rename(columns={"rem_state": "rem_state_s2"})
                df["dev_slice"] = True
                assert str(df["t_ns"].dtype) == "Int64"
                mom = df
            else:
                if kind == "s":
                    df = df.merge(mom[["event_id", "j", "segment", "price_tier", "event_index"]], on=["event_id", "j"], how="left")
                df["moment_uid"] = C.moment_uid(df["event_id"].map(ev["event_index"]), df["j"])
            p = C.art(f"t6_{name}_{y}.parquet")
            df.to_parquet(p, index=False, compression="zstd")
            manifest[p.name] = {"rows": int(len(df)), "columns": list(df.columns), "bytes": p.stat().st_size, "sha256_16": sha(p)}
            if kind == "s":
                for (k, seg), g in df.groupby(["k", "segment"]):
                    a, b = g["er_mid"], g["er_vwap"]
                    mm = a.notna() & b.notna()
                    agree.append({"year": int(y), "rung": int(k), "segment": seg, "n": int(mm.sum()),
                                  "spearman": float(a[mm].rank().corr(b[mm].rank())) if mm.sum() >= 3 else np.nan})
                sfv = df
            if kind == "r":
                rate = df
        # coverage, unavailability and distributions per segment (weighted by moment-minutes)
        for seg, g in mom.groupby("segment"):
            w = g["weight"].to_numpy(float)
            sd = seg_tot.setdefault(seg, {"moments": 0, "moment_minutes": 0, "no_scale_free_rung_mm": 0, "no_rate_rung_mm": 0, "no_quote_mm": 0,
                                          "vwap_fallback_mm": 0, "events": set()})
            sd["moments"] += len(g)
            sd["moment_minutes"] += int(w.sum())
            sd["events"] |= set(g["event_id"])
            if seg in C.SEGS:
                sd["no_scale_free_rung_mm"] += int(w[(g["n_valid_rungs"].fillna(0) == 0).to_numpy()].sum())
                sd["no_rate_rung_mm"] += int(w[(g["n_rate_rungs_valid"].fillna(0) == 0).to_numpy()].sum())
                sd["no_quote_mm"] += int(w[(~g["quote_at_t"].fillna(False).astype(bool)).to_numpy()].sum())
                sd["vwap_fallback_mm"] += int(w[(g["price_basis"] == "vwap_fallback").to_numpy()].sum())
                for c in MEASURES:
                    if c not in g:
                        continue
                    x = g[c].astype(float).to_numpy()
                    cover.setdefault((seg, c), {"mm": 0, "nan_mm": 0, "inf_mm": 0, "x": [], "w": []})
                    cv = cover[(seg, c)]
                    cv["mm"] += int(w.sum())
                    cv["nan_mm"] += int(w[np.isnan(x)].sum())
                    cv["inf_mm"] += int(w[np.isinf(x)].sum())
                    cv["x"].append(x.astype(np.float32))
                    cv["w"].append(w.astype(np.float32))
        # per-rung availability (scale-free and rate), moment-minute weighted, per segment
        wmap = mom.set_index(["event_id", "j"])["weight"]
        for name_, tab, valid_col in (("scale_free", sfv, None), ("rate", rate, "valid")):
            t = tab if valid_col is None else tab[tab[valid_col]]
            t = t.merge(mom[["event_id", "j", "segment", "weight"]], on=["event_id", "j"], how="left", suffixes=("", "_m")) if "segment" not in t else \
                t.merge(mom[["event_id", "j", "weight"]], on=["event_id", "j"], how="left")
            seg_col = "segment"
            for (seg, k), g in t.groupby([seg_col, "k"]):
                rows6.setdefault((name_, seg, int(k)), 0)
                rows6[(name_, seg, int(k))] += int(g["weight"].sum())
        del mom, sfv, rate
        print(f"  merged {y}  {time.perf_counter() - t_start:,.0f}s", flush=True)

    QS = [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
    for (seg, c), cv in cover.items():
        x, w = np.concatenate(cv["x"]).astype(np.float64), np.concatenate(cv["w"]).astype(np.float64)
        qv = wq(x, w, QS)
        quant.append({"segment": seg, "measure": c, "moment_minutes": cv["mm"], "unavailable_share": cv["nan_mm"] / cv["mm"] if cv["mm"] else np.nan,
                      "inf_share": cv["inf_mm"] / cv["mm"] if cv["mm"] else np.nan, **{f"q{int(q * 100):02d}": v for q, v in zip(QS, qv)}})
    Q = pd.DataFrame(quant)
    Q["config_hash"] = C.cfg_hash()
    Q.to_parquet(C.art("t6_measure_quantiles.parquet"), index=False)
    A = pd.DataFrame(agree)
    A["config_hash"] = C.cfg_hash()
    A.to_parquet(C.art("t6_basis_agreement.parquet"), index=False)
    segs = {}
    for seg, sd in seg_tot.items():
        mm = sd["moment_minutes"]
        segs[seg] = {"moments": sd["moments"], "moment_minutes": mm, "events": len(sd["events"])}
        if seg in C.SEGS:
            segs[seg].update({"no_scale_free_rung_share": sd["no_scale_free_rung_mm"] / mm, "no_rate_rung_share": sd["no_rate_rung_mm"] / mm,
                              "no_quote_at_t_share": sd["no_quote_mm"] / mm, "vwap_fallback_share": sd["vwap_fallback_mm"] / mm})
    rung_avail = [{"ladder": a, "segment": s, "k": k, "valid_moment_minutes": v, "share": v / segs[s]["moment_minutes"]} for (a, s, k), v in rows6.items()]
    row6 = {s: v["no_scale_free_rung_share"] for s, v in segs.items() if s in C.SEGS}
    summary = {"config_hash": C.cfg_hash(), "build_seconds": round(build_s, 1), "seconds": round(time.perf_counter() - t_start, 1),
               "events": int(len(R)), "moments": int(R["moments"].sum()), "moment_minutes": int(R["weights"].sum()),
               "prints": int(R["n_prints"].sum()), "quotes": int(R["n_quotes"].sum()), "spike_prints": int(R["n_spikes"].sum()),
               "per_segment": segs, "row6_no_scale_free_rung_share": row6, "row6_fires": {s: bool(v > 0.40) for s, v in row6.items()},
               "rung_availability": rung_avail, "weights_reconcile": True,
               "rem_type_moments": "joined at j = 0, 1, 2, 5, 10, 20 with S2's checkpoint time asserted equal",
               "worker_seconds": {"median": float(R["seconds"].median()), "max": float(R["seconds"].max()), "sum": float(R["seconds"].sum())}}
    C.write_json("t6_summary.json", summary)
    C.write_json("t6_manifest.json", {"config_hash": C.cfg_hash(), "files": manifest,
                                      "note": "git-ignored, regenerable: .venv/Scripts/python.exe research/chop_regime_c1/t6_build.py"})
    print(json.dumps({k: summary[k] for k in ("events", "moments", "moment_minutes", "per_segment", "row6_fires", "build_seconds")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
