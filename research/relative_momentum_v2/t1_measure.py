"""
v2-T1: measure the floor quantities on ALL 903 candidates.

Correction 1 section 5b: the ladder rungs are positioned against the full population, not against a
90-row sample whose p5 and p95 rest on ~4 observations each. T1 makes that pass anyway, so measuring
all 903 costs nothing extra.

One tick pass per candidate: the event's own trades.parquet and quotes.parquet over [tau - 600s, tau].
tau is the gap-gated entry TRIGGER instant from v1-T0 (ts[i]), not the fill instant.

Trades give print_count, notional_usd, venue_count, last_price, share_volume.
Quotes give quote_count, spread_bp, spread_cents, depth_usd -- under D17 exclusions, locked carried.

Causality is asserted inside common.measure, not assumed.

Usage: .venv/Scripts/python.exe research/relative_momentum_v2/t1_measure.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v2 import common as C  # noqa: E402

OUT_JSON = f"{C.ART}/t1_measure.json"
OUT_PARQUET = f"{C.ART}/t1_measured.parquet"


def qd(x, ps=(0, .01, .05, .10, .25, .5, .75, .90, .95, 1.0)):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {}
    return {f"p{int(p * 100)}": round(float(np.quantile(x, p)), 4) for p in ps}


def main() -> int:
    cfg = C.load_cfg()
    W = cfg["window_seconds"]

    pop = C.load_population()
    print(f"population: {len(pop)} gap-gated candidates (v1-T0, reused)", flush=True)

    rows = []
    t0 = time.time()
    for n, r in enumerate(pop.itertuples(index=False), 1):
        folder = C.event_folder(r.ticker, r.date)
        if folder is None:
            rows.append({"key": r.key, "measured": False, "measure_reason": "no_folder"})
            continue
        snap = C.snap_tau_to_tick(folder, float(r.entry_ts))
        m = C.measure(folder, snap["tau_ns"], W)
        rows.append({"key": r.key, "measured": True, "measure_reason": None,
                     "tau_ns": snap["tau_ns"], "tau_snap_ns": snap["snap_ns"], **m})
        if n % 250 == 0:
            print(f"  {n}/{len(pop)}  {time.time() - t0:.0f}s", flush=True)

    mm = pd.DataFrame(rows)
    # v1's population artifact already carries a 'reason' column; the measurement's own status
    # column is named measure_reason so the merge cannot silently suffix either of them.
    assert not (set(mm.columns) - {"key"}) & set(pop.columns),         f"measurement columns collide with the population: "         f"{sorted((set(mm.columns) - {'key'}) & set(pop.columns))}"
    d = pop.merge(mm, on="key", how="left")
    assert len(d) == len(pop), "measurement join changed the row count"
    d["measured"] = d["measured"].fillna(False).astype(bool)

    # The floor never sees the ranker's inputs. Verify the projection the floor will be handed.
    C.assert_floor_inputs_absolute(list(C.FLOOR_INPUTS))
    try:
        C.assert_floor_inputs_absolute(list(C.FLOOR_INPUTS) + ["score"])
        raise SystemExit("ASSERT IS NOT WORKING: a score column passed the floor contract")
    except C.FloorContractViolation:
        contract_test = "passes -- adding a 'score' column to the projection raises"

    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    ok = d[d["measured"]]
    seg_col = "session_bucket"

    summary = {
        "task": "v2-T1 floor quantities measured on all 903 candidates",
        "config_hash": C.cfg_hash(),
        "window_seconds": W,
        "population_source": C.POPULATION,
        "population_reused_not_rebuilt": cfg["population"]["reused_not_rebuilt"],
        "n_candidates": int(len(d)),
        "n_measured": int(d["measured"].sum()),
        "n_unmeasured": int((~d["measured"]).sum()),
        "unmeasured_reasons": d.loc[~d["measured"], "measure_reason"].value_counts().to_dict(),
        "coverage": {
            "n_trades_read": int(ok["trades_read"].sum()),
            "n_quotes_read": int(ok["quotes_read"].sum()),
            "n_depth_available": int(ok["depth_available"].sum()),
            "n_depth_unavailable": int((~ok["depth_available"]).sum()),
            "depth_guard_note": "an event with no D17-surviving quote in the window is NOT rejected "
                                "on no_depth; the pseudocode's DEPTH_AVAILABLE guard applies and "
                                "depth_available = FALSE is carried.",
        },
        "d17": {
            "n_quote_rows_raw_total": int(ok["n_quote_rows_raw"].sum()),
            "n_quote_rows_excluded_total": int(ok["n_quote_rows_excluded_d17"].sum()),
            "excluded_share": round(float(ok["n_quote_rows_excluded_d17"].sum()
                                          / max(ok["n_quote_rows_raw"].sum(), 1)), 6),
            "rule": cfg["quote_exclusions_d17"],
        },
        "build_time_assert": contract_test,
        "tau_precision_recovery": {
            "why": "v1-T0 wrote entry_ts as float64; at 1.7e18 the float64 grid spacing is 256 ns, "
                   "so every stored tau was rounded by up to ~128 ns. tau is a tick timestamp by "
                   "construction, so it is snapped back to its nearest real tick.",
            "n_snapped": int(ok["tau_snap_ns"].notna().sum()),
            "n_snap_nonzero": int((ok["tau_snap_ns"].fillna(0) != 0).sum()),
            "snap_ns_abs_max": int(ok["tau_snap_ns"].abs().max()) if ok["tau_snap_ns"].notna().any() else None,
            "snap_ns_quantiles": qd(ok["tau_snap_ns"], (0, .25, .5, .75, 1.0)),
            "impact": "two candidates (BENF 2024-07-05, JL 2024-01-29) were rounded UPWARD past "
                      "their own trigger print by 115 ns and 58 ns; their previous print was 601 s "
                      "and 4,639 s earlier, so the window measured EMPTY and the floor would have "
                      "rejected them for a floating-point reason. v1's own score window carries the "
                      "same two zero-volume windows.",
        },
        "distributions_all_903": {
            q: qd(ok[q]) for q in ["print_count", "notional_usd", "venue_count", "quote_count",
                                   "spread_bp", "spread_cents", "depth_usd", "last_price",
                                   "share_volume"]
        },
        "distributions_by_session_segment": {
            str(seg): {"n": int(len(g)),
                       **{q: qd(g[q], (.05, .25, .5, .75, .95))
                          for q in ["print_count", "notional_usd", "venue_count", "quote_count",
                                    "spread_bp", "spread_cents", "depth_usd", "last_price"]}}
            for seg, g in ok.groupby(seg_col)
        },
        "entry_kind_counts": ok["entry_kind"].value_counts().to_dict(),
        "output_parquet": OUT_PARQUET,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    C.write_json(OUT_JSON, summary)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("distributions_all_903", "distributions_by_session_segment")},
                     indent=2, default=str))
    print("\nDISTRIBUTIONS, all measured candidates")
    print(pd.DataFrame(summary["distributions_all_903"]).T.to_string())
    print("\nBY SESSION SEGMENT")
    for seg, blk in summary["distributions_by_session_segment"].items():
        print(f"\n  {seg}  n={blk['n']}")
        print(pd.DataFrame({k: v for k, v in blk.items() if k != "n"}).T.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
