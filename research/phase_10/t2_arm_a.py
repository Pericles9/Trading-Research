"""
Phase 10 T2 -- Arm A run: Kleinberg continuous two-state over the T=0 session.

Runs the reference parameter point AND every sensitivity-grid cell in one read
pass per event, so T5 consumes this artifact rather than re-reading ticks.

Non-causal by construction: the optimal state sequence uses the whole session.
That is correct for offline segmentation and is the same relationship Phase 16's
offline regime labels have to Phase 17's online detector. Nothing here is a
detector, an entry signal, or an operating point.

Usage: python research/phase_10/t2_arm_a.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    config_hash, load_cohort, load_config, quantiles, read_event_trades, rel,
    session_window, write_json,
)
from kleinberg import bursts_from_states, kleinberg_two_state  # noqa: E402

OUT_BURSTS = "t2_bursts_arm_a.parquet"
OUT_EVENTS = "t2_arm_a_events.parquet"
OUT_SUMMARY = "t2_arm_a_summary.json"


def param_sets(cfg) -> list[dict]:
    g = cfg["sensitivity_grid"]["arm_a"]
    ref = g["reference_point"]
    out = []
    for s in g["s"]:
        for gam in g["gamma"]:
            is_ref = (s == ref["s"] and gam == ref["gamma"])
            out.append({
                "param_set": "ref" if is_ref else f"s{s}_g{gam}",
                "s": float(s), "gamma": float(gam), "is_ref": is_ref,
            })
    return out


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_cohort(cfg)
    a_cfg = cfg["arm_a"]
    psets = param_sets(cfg)
    ceil_ev = cfg["runtime_ceilings"]["arm_a_seconds_per_event"]
    ceil_ag = cfg["runtime_ceilings"]["arm_a_seconds_aggregate"]

    burst_rows, event_rows, timings = [], [], []
    t_start = time.perf_counter()

    for i, r in enumerate(cohort.itertuples(index=False), 1):
        data = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = data.get(0)
        win = session_window(r.event_date_canonical, 0)
        n_prints = 0 if t0 is None else int(len(t0))
        ts = np.zeros(0, dtype=np.int64) if t0 is None else t0["sip_timestamp"].to_numpy()

        undefined = n_prints < a_cfg["min_prints_for_arm_a"]
        ev = {
            "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
            "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
            "n_prints_t0": n_prints,
            "t0_start_ns": win["start_ns"], "t0_end_ns": win["end_ns"],
            "t0_span_minutes": win["span_minutes"],
            "first_print_ns": int(ts[0]) if n_prints else None,
            "last_print_ns": int(ts[-1]) if n_prints else None,
            "print_span_seconds": float(ts[-1] - ts[0]) / 1e9 if n_prints > 1 else 0.0,
            "arm_a_label": "arm_a_undefined" if undefined else "defined",
            "flag_possible_row_cap": bool(r.flag_possible_row_cap),
        }

        t_ev = time.perf_counter()
        if not undefined:
            for ps in psets:
                res = kleinberg_two_state(
                    ts, ps["s"], ps["gamma"],
                    zero_gap_floor_seconds=a_cfg["zero_gap_floor_seconds"],
                )
                bl = bursts_from_states(ts, res["states"])
                if ps["is_ref"]:
                    ev.update({
                        "n_gaps_floored": res["n_gaps_floored"],
                        "alpha_0_per_sec": res["alpha_0"],
                        "alpha_1_per_sec": res["alpha_1"],
                        "transition_cost": res["transition_cost"],
                        "state1_gap_share": float(np.mean(res["states"])) if res["n_gaps"] else 0.0,
                    })
                for k, (i0, i1, s_ns, e_ns) in enumerate(bl):
                    burst_rows.append({
                        "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                        "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                        "arm": "A", "param_set": ps["param_set"], "is_ref": ps["is_ref"],
                        "s": ps["s"], "gamma": ps["gamma"],
                        "burst_index": k, "start_idx": i0, "end_idx": i1,
                        "start_ns": s_ns, "end_ns": e_ns,
                        "duration_seconds": (e_ns - s_ns) / 1e9,
                        "n_prints": i1 - i0 + 1,
                    })
        el = time.perf_counter() - t_ev
        timings.append(el)
        ev["arm_a_seconds_all_param_sets"] = round(el, 3)
        event_rows.append(ev)
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events segmented ({time.perf_counter()-t_start:.0f}s)", flush=True)

    total = time.perf_counter() - t_start
    bursts = pd.DataFrame(burst_rows)
    events = pd.DataFrame(event_rows)
    bursts.to_parquet(os.path.join(out_dir, OUT_BURSTS), index=False)
    events.to_parquet(os.path.join(out_dir, OUT_EVENTS), index=False)

    ref = bursts[bursts["is_ref"]] if len(bursts) else bursts
    pooled = events[~events["cohort_group"].isin(["dev_v4_sidecar", "row_cap_census"])]
    counts = (
        ref[ref["cohort_group"].isin(["dev_v4_primary", "activity_extension"])]
        .groupby(["ticker", "event_date_canonical", "momentum_pct"]).size()
        if len(ref) else pd.Series(dtype=int)
    )
    cnt_full = pd.Series(0, index=pd.MultiIndex.from_frame(
        pooled[["ticker", "event_date_canonical", "momentum_pct"]]))
    if len(counts):
        cnt_full = cnt_full.add(counts, fill_value=0)

    max_ev = float(np.max(timings)) if timings else 0.0
    summary = {
        "phase": "10", "task": "T2", "arm": "A", "config_hash": chash,
        "method": "Kleinberg 2002 continuous two-state automaton, k=2, implemented directly",
        "implementation": "research/phase_10/kleinberg.py",
        "verification": "brute-force enumeration of all 2^5 state paths on 200 randomized "
                        "quiet-burst-quiet trials matched the Viterbi result exactly; burst "
                        "index-resolution cases asserted. Run: python research/phase_10/kleinberg.py",
        "reference_point": cfg["sensitivity_grid"]["arm_a"]["reference_point"],
        "gamma_note": "gamma is doing the work a minimum-dwell floor does in Arm B. Arm A has "
                      "NO explicit duration floor: the transition cost gamma*ln(n) is the only "
                      "thing preventing single-gap state flips.",
        "baseline": a_cfg["baseline"],
        "n_param_sets": len(psets),
        "param_sets": [p["param_set"] for p in psets],
        "n_events": int(len(events)),
        "n_events_arm_a_undefined": int((events["arm_a_label"] == "arm_a_undefined").sum()),
        "arm_a_undefined_events": events.loc[
            events["arm_a_label"] == "arm_a_undefined",
            ["ticker", "event_date_canonical", "momentum_pct", "cohort_group", "n_prints_t0"],
        ].to_dict("records"),
        "n_bursts_all_param_sets": int(len(bursts)),
        "n_bursts_reference": int(len(ref)),
        "reference_burst_count_pooled": quantiles(cnt_full.to_numpy()),
        "reference_burst_count_by_group": {
            g: quantiles(
                ref[ref["cohort_group"] == g]
                .groupby(["ticker", "event_date_canonical", "momentum_pct"]).size()
                .reindex(pd.MultiIndex.from_frame(
                    events.loc[events["cohort_group"] == g,
                               ["ticker", "event_date_canonical", "momentum_pct"]]),
                    fill_value=0).to_numpy()
            )
            for g in events["cohort_group"].unique()
        },
        "gaps_floored_total": int(events["n_gaps_floored"].fillna(0).sum()),
        "timing": {
            "total_seconds": round(total, 1),
            "max_seconds_per_event_all_param_sets": round(max_ev, 2),
            "median_seconds_per_event": round(float(np.median(timings)), 3),
            "ceiling_per_event": ceil_ev, "ceiling_aggregate": ceil_ag,
            "escalation_row_5_triggered": bool(max_ev > ceil_ev or total > ceil_ag),
        },
        "source": "research/phase_10/t2_arm_a.py:main",
        "artifacts": [f"{cfg['paths']['out_artifacts']}{OUT_BURSTS}",
                      f"{cfg['paths']['out_artifacts']}{OUT_EVENTS}"],
    }
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    print(f"Arm A: {len(events)} events, {len(ref)} reference bursts, "
          f"{len(bursts)} bursts across {len(psets)} param sets")
    print(f"  runtime total {total:.0f}s, max/event {max_ev:.2f}s (ceiling {ceil_ev}s)")
    print(f"  arm_a_undefined: {summary['n_events_arm_a_undefined']}")
    if summary["timing"]["escalation_row_5_triggered"]:
        print("ESCALATION ROW 5 TRIGGERED")
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
