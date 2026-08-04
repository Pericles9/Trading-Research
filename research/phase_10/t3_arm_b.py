"""
Phase 10 T3 -- Arm B run: threshold + hysteresis on a time-of-day-matched
flanking-session baseline.

Same output shape as T2 so the arms are directly comparable (T5b, chart 05).
Reference point plus every valid sensitivity cell in one read pass per event.

T3b: per-event baseline definedness is reported. Events with insufficient
flanking coverage to build a baseline are LABELED AND CARRIED, never dropped.

Usage: python research/phase_10/t3_arm_b.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arm_b import arm_b_segment, build_baseline  # noqa: E402
from common import (  # noqa: E402
    config_hash, load_cohort, load_config, quantiles, read_event_trades, rel,
    session_window, write_json,
)

OUT_BURSTS = "t3_bursts_arm_b.parquet"
OUT_EVENTS = "t3_arm_b_events.parquet"
OUT_SUMMARY = "t3_arm_b_summary.json"
FLANK_OFFSETS = (-3, -2, -1)


def param_sets(cfg) -> tuple[list[dict], int]:
    g = cfg["sensitivity_grid"]["arm_b"]
    ref = g["reference_point"]
    out, skipped = [], 0
    for on in g["on_multiplier"]:
        for off in g["off_multiplier"]:
            if off >= on:  # config constraint: off strictly below on
                skipped += 1
                continue
            for dw in g["min_dwell_seconds"]:
                is_ref = (on == ref["on_multiplier"] and off == ref["off_multiplier"]
                          and dw == ref["min_dwell_seconds"])
                out.append({
                    "param_set": "ref" if is_ref else f"on{on}_off{off}_dw{dw}",
                    "on_multiplier": float(on), "off_multiplier": float(off),
                    "min_dwell_seconds": float(dw), "is_ref": is_ref,
                })
    return out, skipped * len(g["min_dwell_seconds"])


def collected_offsets(row, per_offset_counts: dict) -> tuple[dict, str]:
    """Which flanking sessions were actually collected.

    Preferred source is the canonical `trades_bitmap` (7 chars, offsets -3..+3
    at index o+3). Where it is NULL -- the dev v4 sidecar carries no bitmap --
    fall back to print presence. The distinction matters: a COLLECTED session
    with zero prints is real information (the name did not trade) and must
    contribute zero-count minute slots to the denominator, whereas an
    UNCOLLECTED session must contribute nothing rather than silently pulling
    the baseline toward zero.
    """
    if not hasattr(row, "trades_bitmap"):
        # A missing COLUMN is a schema gap, not a per-event NULL. Silently falling
        # back would degrade every event's baseline to the fallback rule while the
        # config still claimed the bitmap rule -- which is exactly what happened on
        # the first T3 run. Fail loudly instead.
        raise KeyError(
            "cohort manifest has no `trades_bitmap` column; Arm B's baseline denominator "
            "rule (config.arm_b) requires it. Re-run research/phase_10/t1_cohort.py."
        )
    bm = row.trades_bitmap
    if isinstance(bm, str) and len(bm) == 7:
        return {o: bm[o + 3] == "1" for o in FLANK_OFFSETS}, "trades_bitmap"
    return {o: per_offset_counts.get(o, 0) > 0 for o in FLANK_OFFSETS}, "print_presence_fallback"


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_cohort(cfg)
    b = cfg["arm_b"]
    psets, n_skipped = param_sets(cfg)
    ceil_ev = cfg["runtime_ceilings"]["arm_b_seconds_per_event"]
    ceil_ag = cfg["runtime_ceilings"]["arm_b_seconds_aggregate"]

    burst_rows, event_rows, timings = [], [], []
    t_start = time.perf_counter()

    for i, r in enumerate(cohort.itertuples(index=False), 1):
        data = read_event_trades(
            cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
            offsets=(*FLANK_OFFSETS, 0),
        )
        win0 = session_window(r.event_date_canonical, 0)
        t0 = data.get(0)
        ts = np.zeros(0, dtype=np.int64) if t0 is None else t0["sip_timestamp"].to_numpy()
        counts = {o: (0 if data.get(o) is None else len(data[o])) for o in FLANK_OFFSETS}
        coll, coll_source = collected_offsets(r, counts)

        flank = {}
        for o in FLANK_OFFSETS:
            w = session_window(r.event_date_canonical, o)
            sub = data.get(o)
            flank[o] = {
                "ts": np.zeros(0, dtype=np.int64) if sub is None else sub["sip_timestamp"].to_numpy(),
                "start_ns": w["start_ns"] if w else 0,
                "span_minutes": w["span_minutes"] if w else 0,
                "collected": bool(coll[o]) and w is not None,
            }

        base = build_baseline(
            flank, win0["span_minutes"], b["baseline_window_minutes"], b["baseline_floor_per_min"]
        )

        ev = {
            "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
            "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
            "n_prints_t0": int(len(ts)),
            "t0_start_ns": win0["start_ns"], "t0_span_minutes": win0["span_minutes"],
            "baseline_label": base["label"],
            "baseline_source": coll_source,
            "n_collected_flanking": int(sum(coll.values())),
            "n_flanking_prints": int(sum(counts.values())),
            "baseline_minutes_with_support": base["n_minutes_with_support"],
            "baseline_minutes_with_prints": base["n_minutes_with_prints"],
            "baseline_minutes_total": base["n_minutes"],
            "baseline_median_rate_per_min": float(np.nanmedian(base["rate_per_min"]))
            if np.isfinite(base["rate_per_min"]).any() else None,
            "flag_possible_row_cap": bool(r.flag_possible_row_cap),
        }

        t_ev = time.perf_counter()
        for ps in psets:
            res = arm_b_segment(
                ts, win0["start_ns"], win0["span_minutes"], base,
                grid_seconds=b["grid_seconds"],
                rate_window_seconds=b["rate_window_seconds"],
                on_multiplier=ps["on_multiplier"],
                off_multiplier=ps["off_multiplier"],
                min_dwell_seconds=ps["min_dwell_seconds"],
                merge_gap_seconds=b["merge_gap_seconds"],
                baseline_floor_per_min=b["baseline_floor_per_min"],
            )
            if ps["is_ref"]:
                ev.update({
                    "n_candidates_raw": res["n_candidates_raw"],
                    "n_after_merge": res["n_after_merge"],
                    "n_dropped_short": res["n_dropped_short"],
                    "n_dropped_no_prints": res["n_dropped_no_prints"],
                    "median_z": float(np.median(res["z"])) if res["z"].size else None,
                    "max_z": float(np.max(res["z"])) if res["z"].size else None,
                })
            for k, bs in enumerate(res["bursts"]):
                burst_rows.append({
                    "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                    "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                    "arm": "B", "param_set": ps["param_set"], "is_ref": ps["is_ref"],
                    "on_multiplier": ps["on_multiplier"], "off_multiplier": ps["off_multiplier"],
                    "min_dwell_seconds": ps["min_dwell_seconds"],
                    "burst_index": k, "start_idx": bs["start_idx"], "end_idx": bs["end_idx"],
                    "start_ns": bs["start_ns"], "end_ns": bs["end_ns"],
                    "grid_start_ns": bs["grid_start_ns"], "grid_end_ns": bs["grid_end_ns"],
                    "duration_seconds": (bs["end_ns"] - bs["start_ns"]) / 1e9,
                    "n_prints": bs["end_idx"] - bs["start_idx"] + 1,
                })
        el = time.perf_counter() - t_ev
        timings.append(el)
        ev["arm_b_seconds_all_param_sets"] = round(el, 3)
        event_rows.append(ev)
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events segmented ({time.perf_counter()-t_start:.0f}s)", flush=True)

    total = time.perf_counter() - t_start
    bursts = pd.DataFrame(burst_rows)
    events = pd.DataFrame(event_rows)
    bursts.to_parquet(os.path.join(out_dir, OUT_BURSTS), index=False)
    events.to_parquet(os.path.join(out_dir, OUT_EVENTS), index=False)

    ref = bursts[bursts["is_ref"]] if len(bursts) else bursts
    key = ["ticker", "event_date_canonical", "momentum_pct"]

    def counts_for(group: str) -> np.ndarray:
        idx = pd.MultiIndex.from_frame(events.loc[events["cohort_group"] == group, key])
        c = ref[ref["cohort_group"] == group].groupby(key).size() if len(ref) else pd.Series(dtype=int)
        return c.reindex(idx, fill_value=0).to_numpy()

    pooled_groups = ["dev_v4_primary", "activity_extension"]
    pooled_idx = pd.MultiIndex.from_frame(events.loc[events["cohort_group"].isin(pooled_groups), key])
    c_pooled = (ref[ref["cohort_group"].isin(pooled_groups)].groupby(key).size()
                if len(ref) else pd.Series(dtype=int)).reindex(pooled_idx, fill_value=0)

    max_ev = float(np.max(timings)) if timings else 0.0
    summary = {
        "phase": "10", "task": "T3", "arm": "B", "config_hash": chash,
        "method": "trade-arrival rate vs time-of-day-matched flanking baseline (T-3..T-1), "
                  "log space, on/off hysteresis, merge-then-dwell",
        "implementation": "research/phase_10/arm_b.py",
        "verification": "synthetic quiet-burst-quiet session: the dense region is recovered as "
                        "exactly one burst with boundaries inside +/-2 min of truth carrying "
                        ">90% of its prints; baseline label transitions asserted; hysteresis "
                        "shown to widen the interval vs a single-threshold rule. "
                        "Run: python research/phase_10/arm_b.py",
        "reference_point": cfg["sensitivity_grid"]["arm_b"]["reference_point"],
        "baseline_rule": b["baseline_window_desc"],
        "baseline_denominator_rule": "collected flanking sessions only, from canonical trades_bitmap "
                                     "where present (fallback: print presence). A collected session "
                                     "with zero prints contributes zero-count minute slots; an "
                                     "uncollected session contributes nothing.",
        "n_param_sets": len(psets),
        "n_param_combinations_skipped_off_ge_on": n_skipped,
        "n_events": int(len(events)),
        "baseline_definedness": {
            "counts": events["baseline_label"].value_counts().to_dict(),
            "by_group": {
                g: sub["baseline_label"].value_counts().to_dict()
                for g, sub in events.groupby("cohort_group")
            },
            "source_used": events["baseline_source"].value_counts().to_dict(),
            "non_defined_events": events.loc[
                events["baseline_label"] != "defined",
                key + ["cohort_group", "baseline_label", "n_collected_flanking",
                       "n_flanking_prints", "baseline_minutes_with_prints", "baseline_minutes_total"],
            ].to_dict("records"),
            "carried_not_dropped": True,
        },
        "n_bursts_all_param_sets": int(len(bursts)),
        "n_bursts_reference": int(len(ref)),
        "reference_burst_count_pooled": quantiles(c_pooled.to_numpy()),
        "reference_burst_count_by_group": {
            g: quantiles(counts_for(g)) for g in events["cohort_group"].unique()
        },
        "candidate_funnel_reference": {
            "raw_candidates": int(events["n_candidates_raw"].fillna(0).sum()),
            "after_merge": int(events["n_after_merge"].fillna(0).sum()),
            "dropped_below_dwell": int(events["n_dropped_short"].fillna(0).sum()),
            "dropped_no_prints": int(events["n_dropped_no_prints"].fillna(0).sum()),
            "final": int(len(ref)),
        },
        "timing": {
            "total_seconds": round(total, 1),
            "max_seconds_per_event_all_param_sets": round(max_ev, 2),
            "median_seconds_per_event": round(float(np.median(timings)), 3),
            "ceiling_per_event": ceil_ev, "ceiling_aggregate": ceil_ag,
            "escalation_row_5_triggered": bool(max_ev > ceil_ev or total > ceil_ag),
        },
        "source": "research/phase_10/t3_arm_b.py:main",
        "artifacts": [f"{cfg['paths']['out_artifacts']}{OUT_BURSTS}",
                      f"{cfg['paths']['out_artifacts']}{OUT_EVENTS}"],
    }
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    print(f"Arm B: {len(events)} events, {len(ref)} reference bursts, "
          f"{len(bursts)} bursts across {len(psets)} param sets")
    print(f"  baseline definedness: {summary['baseline_definedness']['counts']}")
    print(f"  funnel: {summary['candidate_funnel_reference']}")
    print(f"  runtime total {total:.0f}s, max/event {max_ev:.2f}s (ceiling {ceil_ev}s)")
    if summary["timing"]["escalation_row_5_triggered"]:
        print("ESCALATION ROW 5 TRIGGERED")
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
