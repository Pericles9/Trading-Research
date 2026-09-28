"""
Brief 2, T1 -- the excursion vector on all of D1 with tau. Brief 1's T4 code, unchanged.

`event_rows` is Brief 1's research/attention_excursion_b1/t4_excursion.py per-event loop body, lifted
into a function so a process pool can run it; the only edit is R5 (no open_adjacent_0930). The
components come from Brief 1's instruments.excursion_vector, imported unchanged. Path: every print
strictly after tau up to 20:00 ET on the event day. Rungs N in {50, 100, 200}; RV sigma_path;
earliest-peak tie rule; edge classes as flags (rise_censored, no_rise, peak_tied, halt_in_path by the
>= 300 s regular-hours gap rule plus LULD labels, thin_path < 250 prints).

Checks: the dev and sidecar rows must equal Brief 1's t4_excursion.parquet column for column (the
"unchanged" claim, tested); bucket volume conservation is asserted inside instruments.bucketize.
Escalation rows 1 (vector on < 95% of events with tau: HARD STOP), 6 (thin > 10%: LOG), 7 (halt > 40%: LOG).

Writes artifacts/t1_excursion.parquet (event x rung) and artifacts/t1_summary.json.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/t1_excursion.py
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402

C1, I = B.C1, B.I
_HALTS = None


def _init():
    global _HALTS
    _HALTS = C1.load_halt_labels()


def path_arrays(event_id: str, tau_ns: int, date: str):
    """Brief 1 t4_excursion.path_arrays."""
    tr = C1.read_trades(event_id, with_conditions=False)
    t2000 = C1.et_ns(date, "20:00:00")
    ts, px, sz = tr["ts"], tr["px"], tr["sz"]
    a = int(np.searchsorted(ts, tau_ns, "right"))      # strictly after tau
    b = int(np.searchsorted(ts, t2000, "right"))
    return ts[a:b], px[a:b], sz[a:b]


def event_rows(r: dict, ladder: list, thin_n: int, gap_s: float, halts: dict) -> list[dict]:
    """Brief 1 t4_excursion.main's per-event body (open_adjacent_0930 dropped, R5)."""
    base = {"event_id": r["event_id"], "ticker": r["ticker"], "event_date_canonical": r["event_date_canonical"],
            "dev_group": r["dev_group"], "tau_session_segment": r["tau_session_segment"],
            "flag_cross_session_extreme": r["flag_cross_session_extreme"],
            "tau_close_sensitive": r["tau_close_sensitive"], "year": r["event_date_canonical"][:4],
            "sec_from_0930": r["sec_from_0930"]}
    rows = []
    if not r["tau_available"]:
        for N in ladder:
            rows.append({**base, "N": N, "vector_available": False, "reason": f"tau_unavailable:{r['tau_reason']}"})
        return rows
    tau = int(r["tau_ns"])
    ts, px, sz = path_arrays(r["event_id"], tau, r["event_date_canonical"])
    # A2.6: a gap counts toward a halt only for the part of it that lies inside regular hours
    g_lo = np.r_[tau, ts[:-1]] if ts.size else np.array([], dtype=np.int64)
    g_hi = ts
    op, cl = C1.rth_bounds_ns(r["event_date_canonical"])
    in_rth = np.clip(np.minimum(g_hi, cl) - np.maximum(g_lo, op), 0, None) / 1e9 if ts.size else np.array([])
    outside = (g_hi - g_lo) / 1e9 - in_rth if ts.size else np.array([])
    key = f"{r['ticker']}|{r['event_date_canonical']}"
    lab = halts.get(key, [])
    end = int(ts[-1]) if ts.size else tau
    lab_in = [h for h in lab if h[1] > tau and h[0] <= end]
    flags = {"n_path_prints_all": int(ts.size), "thin_path": bool(ts.size < thin_n),
             "max_gap_s": float(((g_hi - g_lo) / 1e9).max()) if ts.size else np.nan,
             "max_gap_in_rth_s": float(in_rth.max()) if ts.size else np.nan,
             "max_gap_outside_rth_s": float(outside.max()) if ts.size else np.nan,
             "halt_gap_rth": bool(ts.size and in_rth.max() >= gap_s),
             "halt_label_available": bool(key in halts),
             "halt_label_in_path": bool(lab_in), "tau_price": float(r["tau_price"])}
    flags["halt_in_path"] = bool(flags["halt_gap_rth"] or flags["halt_label_in_path"])
    for N in ladder:
        if ts.size < 2:
            rows.append({**base, **flags, "N": N, "vector_available": False, "reason": "path_too_short"})
            continue
        v = I.excursion_vector(tau, float(r["tau_price"]), ts, px, sz, N)
        v.pop("_bucket_price", None)
        v.pop("_bucket_t_end", None)
        rows.append({**base, **flags, **v})
    return rows


def one(args):
    r, ladder, thin_n, gap_s = args
    try:
        return event_rows(r, ladder, thin_n, gap_s, _HALTS)
    except AssertionError:
        raise                                          # an instrument assertion stops the run
    except Exception as e:                             # carried, never dropped
        return [{"event_id": r["event_id"], "N": N, "vector_available": False, "reason": f"error:{type(e).__name__}: {e}"}
                for N in ladder]


def main() -> int:
    t_start = time.perf_counter()
    cfg = B.load_cfg()
    c4 = cfg["t4_excursion"]
    ladder, thin_n = c4["bucket_ladder"], c4["thin_path_min_prints"]
    gap_s = cfg["amendment_2"]["halt_rule"]["gap_seconds"]
    esc = cfg["brief2"]["escalation"]
    pop = pd.read_parquet(B.art("t0_population.parquet"))
    cols = ["event_id", "ticker", "event_date_canonical", "dev_group", "tau_session_segment", "flag_cross_session_extreme",
            "tau_close_sensitive", "sec_from_0930", "tau_available", "tau_reason", "tau_ns", "tau_price"]
    recs = pop[cols].to_dict("records")
    jobs = [(r, ladder, thin_n, gap_s) for r in recs]
    rows = []
    with ProcessPoolExecutor(max_workers=B.cpu_workers(), initializer=_init) as ex:
        for k, rr in enumerate(ex.map(one, jobs, chunksize=25)):
            rows += rr
            if (k + 1) % 2000 == 0:
                print(f"  {k + 1:,}/{len(jobs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    out = pd.DataFrame(rows)
    out = out.merge(pop[["event_id", "tau_ns", "slice", "tau_anchor_segment", "tau_in_auction_minute", "price_tier"]],
                    on="event_id", how="left")
    out["tau_ns"] = out["tau_ns"].astype("Int64")
    B.assert_int64(out)
    assert "open_adjacent_0930" not in out, "R5"
    out["config_hash"] = B.cfg_hash()
    out.to_parquet(B.art("t1_excursion.parquet"), index=False)

    # ------------------------------------------------ Brief 1's T4 dev rows, reproduced
    b1 = pd.read_parquet(B.b1_art("t4_excursion.parquet"))
    common_cols = [c for c in b1.columns if c in out.columns and c not in ("config_hash",)]
    x = out[out["dev_group"].notna()].sort_values(["event_id", "N"])[common_cols].reset_index(drop=True)
    y = b1.sort_values(["event_id", "N"])[common_cols].reset_index(drop=True)
    mism = {}
    for c in common_cols:
        a, b = x[c], y[c]
        if pd.api.types.is_float_dtype(a) or pd.api.types.is_float_dtype(b):
            eq = (np.isclose(a.astype(float), b.astype(float), rtol=0, atol=0, equal_nan=True))
        else:
            eq = (a.astype("string").fillna("<NA>") == b.astype("string").fillna("<NA>")).to_numpy()
        if not eq.all():
            mism[c] = int((~eq).sum())
    reproduces = (len(x) == len(y)) and not mism

    ta = pop[pop["tau_available"]]
    wt = out[out["event_id"].isin(ta["event_id"])]
    per_ev = wt.drop_duplicates("event_id")
    n_ev = int(len(ta))
    avail = {int(N): int(g["vector_available"].fillna(False).astype(bool).sum()) for N, g in wt.groupby("N")}
    share = {N: v / n_ev for N, v in avail.items()}
    thin = int(per_ev["thin_path"].fillna(False).astype(bool).sum())
    halt = int(per_ev["halt_in_path"].fillna(False).astype(bool).sum())
    va = out[out["vector_available"] == True]  # noqa: E712
    edge = {int(N): {k: int(g[k].fillna(False).astype(bool).sum()) for k in
                     ["rise_censored", "no_rise", "peak_at_tau", "peak_tied", "halt_in_path", "halt_gap_rth", "halt_label_in_path",
                      "thin_path", "sigma_zero"]} | {"n": int(len(g))} for N, g in va.groupby("N")}
    summary = {
        "config_hash": B.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1),
        "events_with_tau": n_ev, "events_d1": int(len(pop)),
        "vector_available_by_N": avail, "vector_available_share_by_N": share,
        "unavailable_reasons_with_tau": wt.loc[wt["vector_available"] != True, "reason"].value_counts().to_dict(),  # noqa: E712
        "edge_classes_by_N": edge,
        "path_prints": {"median": float(per_ev["n_path_prints_all"].median()), "p05": float(per_ev["n_path_prints_all"].quantile(.05)),
                        "min": float(per_ev["n_path_prints_all"].min()), "max": float(per_ev["n_path_prints_all"].max())},
        "halt_label_available_events": int(per_ev["halt_label_available"].fillna(False).astype(bool).sum()),
        "dev_reproduces_brief1_t4": {"value": bool(reproduces), "rows_compared": int(len(x)), "columns_compared": len(common_cols),
                                     "mismatched_columns": mism},
        "II5_bucket_volume_conservation": {"asserted_in": "instruments.bucketize (Brief 1, unchanged)", "event_rungs": int(len(va)),
                                           "max_bucket_vol_rel_err": float(va["max_bucket_vol_rel_err"].max())},
        "row_1": {"criterion": esc["row_1"]["criterion"], "tier": "HARD STOP", "observed_min_share": min(share.values()),
                  "by_N": share, "fires": bool(min(share.values()) < esc["row_1"]["threshold"])},
        "row_6": {"criterion": esc["row_6"]["criterion"], "tier": "LOG", "thin_events": thin, "of_events_with_tau": n_ev,
                  "observed_share": thin / n_ev, "fires": bool(thin / n_ev > esc["row_6"]["threshold"])},
        "row_7": {"criterion": esc["row_7"]["criterion"], "tier": "LOG", "halt_events": halt, "of_events_with_tau": n_ev,
                  "observed_share": halt / n_ev, "fires": bool(halt / n_ev > esc["row_7"]["threshold"])},
    }
    B.write_json("t1_summary.json", summary)
    print({k: summary[k] for k in ("seconds", "vector_available_share_by_N", "unavailable_reasons_with_tau", "dev_reproduces_brief1_t4")})
    print(summary["row_1"], summary["row_6"], summary["row_7"], sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
