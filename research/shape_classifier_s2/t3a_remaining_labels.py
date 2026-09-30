"""
Shape classifier S2, T3a -- Amendment 1 A1.3: the remaining-path type at every checkpoint after tau.

S1's rules unchanged, applied to what is left of the path: from the checkpoint's entry (the first print after the
decision time, T2's zero-latency entry) to 20:00. S1's post-tau construction with the entry print in tau's place:
element 0 = the entry print's price; N = 100 equal-volume buckets (Brief 1's instruments.bucketize) over the prints
with ts > the entry's timestamp up to the last print <= 20:00; the components, sigma_path and the 200-draw
shuffled null through S1's s1common.real_pipeline / null_pipeline; rise_pct / fall_pct mid-rank against the draws;
s1common.theory_type. At tau the label is S1's whole-path type (the same by construction, A1.3).

Also writes each checkpoint's remaining-path rise_pct, fall_pct, u_peak and terminal_log (the positive control's
leak inputs, A1.3) and the whole-vs-remaining comparison per type (A1.5 report addition).

Writes artifacts/t3a_remaining_labels.parquet (event x decision time), t3a_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t3a_remaining_labels.py
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

C1, I, S1 = S.C1, S.I, S.S1
N, ND, G = 100, 200, 100
NULL_SEED = 20260927                     # S1's null seed (config/shape_atlas_s1.json null.seed)


def label_path(ts, px, sz, e: int, event_index: int, time_idx: int) -> dict:
    """Remaining-path type from entry print index e (arrays already cut to <= 20:00)."""
    k = int(np.searchsorted(ts, ts[e], "right"))          # prints strictly after the entry's timestamp
    if ts.size - k < 2:
        return {"rem_state": "path_too_short", "rem_n_prints": int(ts.size - k)}
    b = I.bucketize(ts[k:], px[k:], sz[k:], N)
    if not b["ok"]:
        return {"rem_state": b["reason"], "rem_n_prints": int(ts.size - k)}
    lp = np.log(np.r_[px[e], b["vwap"]])
    _, c, _ = S1.real_pipeline(lp, G)
    out = {"rem_n_prints": int(ts.size - k), "rem_u_peak": float(c["u_peak"][0]), "rem_rise_s": float(c["rise_s"][0]),
           "rem_fall_s": float(c["fall_s"][0]), "rem_terminal_log": float(c["terminal_log"][0]), "rem_sigma_path": float(c["sigma_path"][0])}
    idx = np.random.default_rng([NULL_SEED, int(event_index), 10 + time_idx, N]).integers(0, N, size=(ND, N))
    _, nc, _ = S1.null_pipeline(lp, idx, G)
    ok = ~nc["sigma_zero"]
    if c["sigma_zero"][0] or not ok.any():
        out["rem_state"] = "sigma_zero_or_no_null"
        return out
    rp = S1.pct_vs(nc["rise_s"][ok], c["rise_s"][0])
    fp = S1.pct_vs(nc["fall_s"][ok], c["fall_s"][0])
    out.update({"rem_state": "typed", "rem_null_n": int(ok.sum()), "rem_rise_pct": rp, "rem_fall_pct": fp,
                "rem_type": str(S1.theory_type([rp], [fp], [c["u_peak"][0]])[0])})
    return out


def one(rec: dict) -> list[dict]:
    tr = C1.read_trades(rec["event_id"], with_conditions=False)
    date = rec["event_date_canonical"]
    t0400, t2000 = C1.et_ns(date, "04:00:00"), C1.et_ns(date, "20:00:00")
    a, b = int(np.searchsorted(tr["ts"], t0400, "left")), int(np.searchsorted(tr["ts"], t2000, "right"))
    ts, px, sz = tr["ts"][a:b], tr["px"][a:b], tr["sz"][a:b]
    rows = []
    for ti, (tkey, d, entry) in enumerate(zip(rec["times"], rec["d_ns"], rec["entry_ns"])):
        row = {"event_id": rec["event_id"], "time": tkey}
        if d is None:
            row["rem_state"] = "checkpoint_not_reached"
        else:
            e = int(np.searchsorted(ts, int(d), "right"))
            if e >= ts.size:
                row["rem_state"] = "no_entry"
            else:
                assert entry is not None and int(ts[e]) == int(entry), f"{rec['event_id']} {tkey}: entry differs from T2's"
                row["rem_entry_ns"] = int(ts[e])
                row.update(label_path(ts, px, sz, e, rec["event_index"], S.TIMES.index(tkey)))
        rows.append(row)
    return rows


def main() -> int:
    t_start = time.perf_counter()
    pop = S.load_population()
    s1 = pd.read_parquet(S.src("s1_events"), columns=["event_id", "event_index", "post100_rise_pct", "post100_fall_pct", "post100_u_peak"])
    ex = pd.read_parquet(S.src("b2_excursion"), columns=["event_id", "N", "terminal_log"])
    ex = ex[ex["N"] == 100][["event_id", "terminal_log"]]
    ck = pd.read_parquet(S.art("t2_checkpoints.parquet"), columns=["event_id", "time", "state", "d_ns"])
    fw = pd.read_parquet(S.art("t2_forward.parquet"), columns=["event_id", "time", "entry_lat0_ns"])
    ck = ck.merge(fw, on=["event_id", "time"], how="left")
    after = [t for t in S.TIMES if t != "tau"]
    ck = ck[ck["time"].isin(after)]
    ck["d_py"] = [int(v) if (pd.notna(v) and s == "reached") else None for v, s in zip(ck["d_ns"], ck["state"])]
    ck["e_py"] = [int(v) if pd.notna(v) else None for v in ck["entry_lat0_ns"]]
    g = ck.groupby("event_id")
    dmap = {e: (list(x["time"]), list(x["d_py"]), list(x["e_py"])) for e, x in g}
    base = pop[["event_id", "event_date_canonical"]].merge(s1[["event_id", "event_index"]], on="event_id")
    recs = [{"event_id": r.event_id, "event_date_canonical": r.event_date_canonical, "event_index": int(r.event_index),
             "times": dmap[r.event_id][0], "d_ns": dmap[r.event_id][1], "entry_ns": dmap[r.event_id][2]} for r in base.itertuples()]
    rows = []
    with ProcessPoolExecutor(max_workers=S.B2.cpu_workers()) as ex_:
        for n, r in enumerate(ex_.map(one, recs, chunksize=20)):
            rows.extend(r)
            if (n + 1) % 2000 == 0:
                print(f"  {n + 1:,}/{len(recs):,}  {time.perf_counter() - t_start:,.0f}s", flush=True)
    rem = S.ns_frame(rows, ["rem_entry_ns"])
    # tau: the whole-path label, by construction (A1.3)
    tau = pop[["event_id", "type100"]].merge(s1, on="event_id").merge(ex, on="event_id", how="left")
    tau = pd.DataFrame({"event_id": tau["event_id"], "time": "tau", "rem_state": np.where(tau["type100"].notna(), "typed_whole_at_tau", "untyped_at_tau"),
                        "rem_type": tau["type100"], "rem_rise_pct": tau["post100_rise_pct"], "rem_fall_pct": tau["post100_fall_pct"],
                        "rem_u_peak": tau["post100_u_peak"], "rem_terminal_log": tau["terminal_log"]})
    rem = pd.concat([tau, rem], ignore_index=True)
    rem["whole_type"] = rem["event_id"].map(pop.set_index("event_id")["type100"])
    rem["config_hash"] = S.cfg_hash()
    rem.to_parquet(S.art("t3a_remaining_labels.parquet"), index=False, compression="zstd")

    # ---------------- summary: states, type shares, and whole vs remaining per type
    ok = rem[rem["rem_type"].notna() & rem["whole_type"].notna() & ~rem["event_id"].isin(pop.loc[pop["excluded_dev"], "event_id"])]
    differ = {}
    for t in S.TIMES:
        g = ok[ok["time"] == t]
        differ[t] = {w: {"n": int((g["whole_type"] == w).sum()), "differ": int(((g["whole_type"] == w) & (g["rem_type"] != w)).sum()),
                         "remaining_types": g.loc[g["whole_type"] == w, "rem_type"].value_counts().to_dict()} for w in S.TYPES}
    S.write_json("t3a_summary.json", {
        "config_hash": S.cfg_hash(), "seconds": round(time.perf_counter() - t_start, 1),
        "states": {t: rem[rem["time"] == t]["rem_state"].value_counts().to_dict() for t in S.TIMES},
        "type_shares": {t: rem[(rem["time"] == t)]["rem_type"].value_counts().reindex(S.TYPES).fillna(0).astype(int).to_dict() for t in S.TIMES},
        "whole_vs_remaining": differ,
        "null": {"draws": ND, "seed": NULL_SEED, "rng": "default_rng([seed, S1 event_index, 10 + position in TIMES, 100])"},
    })
    for t in S.TIMES:
        print(t, rem[rem["time"] == t]["rem_state"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
