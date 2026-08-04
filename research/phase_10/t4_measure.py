"""
Phase 10 T4 -- burst-level measurements, computed identically for both arms and
reported side by side. NEVER pooled across arms.

  T4a  burst count, duration, spacing
  T4b  fraction of the T=0 session move carried within each burst
  T4c  burst-relative concentration curve (move and volume vs time since burst
       start) -- the quantity that replaces the session-anchored decay curve
  T4d  time from burst start to the burst's own price extreme
  T4e  flag_possible_row_cap and dev v4 sidecar broken out as their own rows

D4: every quantity is tick-derived from filtered/ trade prints. No spine numeric
column is read. D4 Amendment A12 is not engaged -- every ratio here has both its
numerator and its denominator inside the single T=0 session, so no price basis
crosses a session boundary.

D5: the session-move denominator is the one session-scale anchor used, named and
justified by the prompt at T4b and recorded in config.measurements.
session_move_denominator.d5_anchor_declaration. Every horizon quantity (T4c,
T4d) is burst-relative.

Usage: python research/phase_10/t4_measure.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    NON_POOLED_GROUPS, config_hash, load_cohort, load_config, quantiles,
    read_event_trades, rel, write_json,
)

KEY = ["ticker", "event_date_canonical", "momentum_pct"]
OUT_BURSTS = "t4_burst_measurements.parquet"
OUT_EVENTS = "t4_event_measurements.parquet"
OUT_CONC = "t4_concentration_curves.parquet"
OUT_SUMMARY = "t4_burst_measurements.json"

POOLED = ["dev_v4_primary", "activity_extension"]


def measure_event(ts, px, sz, bursts: pd.DataFrame, grid: np.ndarray) -> tuple[list, list, dict]:
    """Per-burst measurements + concentration samples for one (event, arm)."""
    n = ts.size
    sess_move = float(px[-1] - px[0]) if n else np.nan
    sess_defined = bool(n and sess_move != 0.0)

    out, conc = [], []
    prev_end_ns = None
    for row in bursts.sort_values("start_ns").itertuples(index=False):
        i0, i1 = int(row.start_idx), int(row.end_idx)
        if i1 < i0 or i1 >= n:
            continue
        p, s, t = px[i0:i1 + 1], sz[i0:i1 + 1], ts[i0:i1 + 1]
        move = float(p[-1] - p[0])
        vol = float(s.sum())
        hi_rel = int(np.argmax(p))
        dur = float(t[-1] - t[0]) / 1e9

        rec = {
            "burst_index": int(row.burst_index),
            "start_idx": i0, "end_idx": i1,
            "start_ns": int(t[0]), "end_ns": int(t[-1]),
            "duration_seconds": dur,
            "n_prints": int(i1 - i0 + 1),
            "volume": vol,
            "first_price": float(p[0]), "last_price": float(p[-1]),
            "high_price": float(p[hi_rel]), "low_price": float(p.min()),
            "burst_move": move,
            "burst_move_abs": abs(move),
            "session_move": sess_move if sess_defined else np.nan,
            "move_share": (move / sess_move) if sess_defined else np.nan,
            "session_move_defined": sess_defined,
            "seconds_to_burst_high": float(t[hi_rel] - t[0]) / 1e9,
            "burst_high_excursion": float(p[hi_rel] - p[0]),
            "spacing_seconds": (float(t[0] - prev_end_ns) / 1e9) if prev_end_ns is not None else np.nan,
            "prints_per_second": (i1 - i0 + 1) / dur if dur > 0 else np.nan,
        }
        out.append(rec)
        prev_end_ns = int(t[-1])

        # ---- T4c concentration samples, anchored at burst start
        if dur > 0 and vol > 0:
            elapsed = (t - t[0]) / 1e9
            cum_move = p - p[0]
            cum_vol = np.cumsum(s)
            tot_move = cum_move[-1]
            pos = np.searchsorted(elapsed, grid, side="right") - 1
            for gi, g in enumerate(grid):
                j = pos[gi]
                if j < 0:
                    continue
                still_open = bool(g <= dur)
                conc.append({
                    "burst_index": int(row.burst_index),
                    "t_seconds": float(g),
                    "move_share_cum": float(cum_move[j] / tot_move) if tot_move != 0 else np.nan,
                    "volume_share_cum": float(cum_vol[j] / vol),
                    "still_open": still_open,
                    "burst_duration_seconds": dur,
                })

    ev = {
        "n_bursts": len(out),
        "session_move": sess_move if n else np.nan,
        "session_move_defined": sess_defined,
        "session_first_price": float(px[0]) if n else np.nan,
        "session_last_price": float(px[-1]) if n else np.nan,
        "session_high_price": float(px.max()) if n else np.nan,
        "session_span_seconds": float(ts[-1] - ts[0]) / 1e9 if n > 1 else 0.0,
        "session_volume": float(sz.sum()) if n else 0.0,
        "n_prints_t0": int(n),
        "burst_covered_seconds": float(sum(r["duration_seconds"] for r in out)),
        "burst_covered_prints": int(sum(r["n_prints"] for r in out)),
        "burst_covered_volume": float(sum(r["volume"] for r in out)),
        "abs_move_in_bursts": float(sum(abs(r["burst_move"]) for r in out)),
    }
    return out, conc, ev


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_cohort(cfg)
    grid = np.array(cfg["measurements"]["concentration_curve"]["grid_seconds"], dtype=float)

    arms = {
        "A": pd.read_parquet(os.path.join(out_dir, "t2_bursts_arm_a.parquet")),
        "B": pd.read_parquet(os.path.join(out_dir, "t3_bursts_arm_b.parquet")),
    }
    arms = {k: v[v["is_ref"]].copy() for k, v in arms.items()}
    for v in arms.values():
        v["event_date_canonical"] = v["event_date_canonical"].astype(str)

    burst_rows, conc_rows, event_rows = [], [], []
    t_start = time.perf_counter()

    for i, r in enumerate(cohort.itertuples(index=False), 1):
        data = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = data.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts = t0["sip_timestamp"].to_numpy()
        px = t0["price"].to_numpy(dtype=float)
        sz = t0["size"].to_numpy(dtype=float)

        for arm, allb in arms.items():
            sel = allb[
                (allb["ticker"] == r.ticker)
                & (allb["event_date_canonical"] == r.event_date_canonical)
                & (np.isclose(allb["momentum_pct"], r.momentum_pct))
            ]
            bl, cc, ev = measure_event(ts, px, sz, sel, grid)
            base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                    "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                    "arm": arm, "flag_possible_row_cap": bool(r.flag_possible_row_cap)}
            burst_rows.extend([{**base, **b} for b in bl])
            conc_rows.extend([{**base, **c} for c in cc])
            event_rows.append({**base, **ev})
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events measured ({time.perf_counter()-t_start:.0f}s)", flush=True)

    bursts = pd.DataFrame(burst_rows)
    conc = pd.DataFrame(conc_rows)
    events = pd.DataFrame(event_rows)
    bursts.to_parquet(os.path.join(out_dir, OUT_BURSTS), index=False)
    conc.to_parquet(os.path.join(out_dir, OUT_CONC), index=False)
    events.to_parquet(os.path.join(out_dir, OUT_EVENTS), index=False)

    # -------------------------------------------------- summaries, per arm x population
    def pop_slices(df: pd.DataFrame) -> dict:
        return {
            "pooled_analysis_cohort": df[df["cohort_group"].isin(POOLED)],
            "dev_v4_primary": df[df["cohort_group"] == "dev_v4_primary"],
            "activity_extension": df[df["cohort_group"] == "activity_extension"],
            "row_cap_census": df[df["cohort_group"] == "row_cap_census"],
            "dev_v4_sidecar": df[df["cohort_group"] == "dev_v4_sidecar"],
        }

    summary = {
        "phase": "10", "task": "T4", "config_hash": chash,
        "pooling_rule": "Never pooled across arms. row_cap_census and dev_v4_sidecar are "
                        "reported as their own rows and are NOT inside pooled_analysis_cohort.",
        "session_move_denominator": cfg["measurements"]["session_move_denominator"],
        "d4_a12_note": cfg["d4"]["a12_applicability"],
        "arms": {},
    }

    for arm in ("A", "B"):
        eb, ee, ec = (bursts[bursts["arm"] == arm], events[events["arm"] == arm],
                      conc[conc["arm"] == arm])
        arm_out = {}
        for pop, ev_sub in pop_slices(ee).items():
            b_sub = eb[eb.set_index(KEY).index.isin(ev_sub.set_index(KEY).index)]
            single = ev_sub[ev_sub["n_bursts"] == 1]
            arm_out[pop] = {
                "n_events": int(len(ev_sub)),
                "n_bursts": int(len(b_sub)),
                # T4a
                "burst_count": quantiles(ev_sub["n_bursts"]),
                "duration_seconds": quantiles(b_sub["duration_seconds"]),
                "spacing_seconds": quantiles(b_sub["spacing_seconds"]),
                "n_single_burst_events": int(len(single)),
                "n_zero_burst_events": int((ev_sub["n_bursts"] == 0).sum()),
                # T4b
                "move_share": quantiles(b_sub["move_share"]),
                "n_bursts_move_share_undefined": int(b_sub["move_share"].isna().sum()),
                "n_events_session_move_undefined": int((~ev_sub["session_move_defined"]).sum()),
                "move_share_by_rank": {
                    f"rank_{k}": quantiles(
                        b_sub.assign(absr=b_sub["burst_move"].abs())
                        .sort_values("absr", ascending=False)
                        .groupby(KEY).nth(k - 1)["move_share"]
                    ) for k in (1, 2, 3)
                },
                # T4d
                "seconds_to_burst_high": quantiles(b_sub["seconds_to_burst_high"]),
                # coverage context
                "share_of_session_seconds_in_bursts": quantiles(
                    ev_sub["burst_covered_seconds"] / ev_sub["session_span_seconds"].replace(0, np.nan)
                ),
                "share_of_session_prints_in_bursts": quantiles(
                    ev_sub["burst_covered_prints"] / ev_sub["n_prints_t0"].replace(0, np.nan)
                ),
                "share_of_session_volume_in_bursts": quantiles(
                    ev_sub["burst_covered_volume"] / ev_sub["session_volume"].replace(0, np.nan)
                ),
            }
        # T4c pooled concentration curve (analysis cohort only)
        cc_pool = ec[ec["cohort_group"].isin(POOLED)]
        curve = []
        for g, sub in cc_pool.groupby("t_seconds"):
            curve.append({
                "t_seconds": float(g),
                "n_bursts": int(len(sub)),
                "n_bursts_still_open": int(sub["still_open"].sum()),
                "move_share_p25": float(sub["move_share_cum"].quantile(0.25)),
                "move_share_p50": float(sub["move_share_cum"].quantile(0.50)),
                "move_share_p75": float(sub["move_share_cum"].quantile(0.75)),
                "volume_share_p25": float(sub["volume_share_cum"].quantile(0.25)),
                "volume_share_p50": float(sub["volume_share_cum"].quantile(0.50)),
                "volume_share_p75": float(sub["volume_share_cum"].quantile(0.75)),
            })
        arm_out["concentration_curve_pooled"] = sorted(curve, key=lambda d: d["t_seconds"])
        summary["arms"][arm] = arm_out

    summary["timing"] = {"total_seconds": round(time.perf_counter() - t_start, 1)}
    summary["source"] = "research/phase_10/t4_measure.py:main"
    summary["artifacts"] = [f"{cfg['paths']['out_artifacts']}{x}"
                            for x in (OUT_BURSTS, OUT_CONC, OUT_EVENTS)]
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    for arm in ("A", "B"):
        p = summary["arms"][arm]["pooled_analysis_cohort"]
        print(f"Arm {arm} pooled (n_events={p['n_events']}, n_bursts={p['n_bursts']}): "
              f"count med={p['burst_count']['q50']}, dur med={p['duration_seconds']['q50']:.3f}s, "
              f"spacing med={p['spacing_seconds']['q50']}, "
              f"move_share med={p['move_share']['q50']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
