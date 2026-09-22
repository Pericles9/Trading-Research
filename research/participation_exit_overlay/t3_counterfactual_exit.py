"""
T3: the counterfactual exit. This is the task that decides the rebuild.

Same entry at tau, same fill assumptions, ONE round trip in each arm. Two exits:

    A  window close          -- what EPG does today
    B  participation decay   -- what the rebuild would do (at the CONFIRMED instant, C minutes
                                after the crossing, because that is when it is knowable)

Both exits are priced tick-exactly from the event's own trades.parquet: the last print at or
before the exit timestamp. Pricing A from v1's stored tick fill and B from a minute bar would
compare two different bases, so both are recomputed here on one basis and A is cross-checked
against v1's own recorded price.

Extending a hold adds exposure, not a round trip. Each arm pays ONE Phase 11 round trip, so the
comparison is the same single cost amortised over a longer move.

THE COUNTER-CASE IS GIVEN A FAIR CHANCE. The programme's founding thesis is a bull impulse
followed by a sharp bear impulse. If EPG's early exit steps out just before the flip, Exit B walks
into it and is WORSE -- in which case the timing mismatch is real and closing it is still the wrong
move. That outcome is reported as plainly as the other.

Censored events (participation never decays inside the session) exit at the censoring horizon, are
their own class, and are never silently pooled with intraday holds -- a session-end hold is a
different risk under D5.

Halt exposure: exact labels where they exist (73 of 903), plus a declared inter-trade-gap proxy
for the whole population. The proxy is a gap measurement, not a halt classifier.

Usage: .venv/Scripts/python.exe research/participation_exit_overlay/t3_counterfactual_exit.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.participation_exit_overlay import common as C  # noqa: E402

IN = f"{C.ART}/t2_overlay.parquet"
OUT_JSON = f"{C.ART}/t3_counterfactual_exit.json"
OUT_PARQUET = f"{C.ART}/t3_counterfactual_exit.parquet"

QS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
FLOOR = 20


def arm(d: pd.DataFrame, label: str, px_col: str, ts_col: str, cost_bp: float,
        note: str = "") -> dict:
    if len(d) == 0:
        return {"arm": label, "n": 0, "note": note}
    g = (d[px_col].to_numpy(float) / d["entry_price"].to_numpy(float) - 1.0) * 1e4
    ok = np.isfinite(g)
    g = g[ok]
    ps_bp = d["cost_cents_bp"].to_numpy(float)[ok]
    net_flat = g - cost_bp
    net_ps = g - ps_bp
    hold = (d[ts_col].to_numpy(float) - d["tau_ns"].to_numpy(float))[ok] / C.NS
    return {
        "arm": label, "n": int(g.size),
        "gross_bp": {f"p{int(q * 100)}": round(float(np.quantile(g, q)), 1) for q in QS},
        "gross_bp_median": round(float(np.median(g)), 1),
        "gross_bp_mean": round(float(g.mean()), 1),
        "net_bp_median_flat": round(float(np.median(net_flat)), 1),
        "net_bp_median_per_share": round(float(np.median(net_ps)), 1),
        "win_rate_gross": round(float((g > 0).mean()), 4),
        "win_rate_net_flat": round(float((net_flat > 0).mean()), 4),
        "win_rate_net_per_share": round(float((net_ps > 0).mean()), 4),
        "hold_sec_median": round(float(np.median(hold)), 1),
        "hold_sec_p95": round(float(np.quantile(hold, .95)), 1),
        "note": note,
    }


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["cost"]["round_trip_bp"]
    cost_cents = cfg["cost"]["round_trip_cents"]
    gap_thr = cfg["halt_exposure"]["proxy"]["threshold_seconds"]

    d = pd.read_parquet(C.REPO / IN)
    halts = C.load_halt_labels()

    rows = []
    t0 = time.time()
    for n, r in enumerate(d.itertuples(index=False), 1):
        folder = C.event_folder(r.ticker, r.date)
        rec = {"key": r.key}
        if folder is None:
            rows.append({**rec, "priced": False})
            continue
        t = C.read_ticks_px(folder)
        if t is None:
            rows.append({**rec, "priced": False})
            continue
        ts, px = t
        a_ts, b_ts = int(r.natural_exit_ts), int(r.exit_b_ns_effective)
        # robust picker (see common.py): guards both exits against a single isolated bad tick,
        # found mid-run on AMC 2024-05-14 (a 4-share, condition [32,37] print at $11.48 sandwiched
        # between two $6.63 prints). Applied to both arms identically so the comparison stays fair.
        ra = C.last_print_at_or_before_robust(ts, px, a_ts)
        rb = C.last_print_at_or_before_robust(ts, px, b_ts)
        rec.update({
            "priced": True,
            "exit_a_price_tick": ra["price"],
            "exit_a_spike_replaced": ra["spike_replaced"],
            "exit_b_price_tick": rb["price"],
            "exit_b_spike_replaced": rb["spike_replaced"],
            "max_gap_a_sec": C.max_gap_in(ts, int(r.tau_ns), a_ts),
            "max_gap_b_sec": C.max_gap_in(ts, int(r.tau_ns), b_ts),
        })
        lab = halts.get(r.key)
        rec["halt_label_available"] = lab is not None
        if lab is not None:
            rec["halt_label_in_a"] = any(s <= a_ts and e >= int(r.tau_ns) for s, e in lab)
            rec["halt_label_in_b"] = any(s <= b_ts and e >= int(r.tau_ns) for s, e in lab)
        rows.append(rec)
        if n % 250 == 0:
            print(f"  {n}/{len(d)}  {time.time() - t0:.0f}s", flush=True)

    px = pd.DataFrame(rows)
    d = d.merge(px, on="key", how="left")
    d["priced"] = d["priced"].fillna(False).astype(bool)
    d["exit_a_spike_replaced"] = d["exit_a_spike_replaced"].fillna(False).astype(bool)
    d["exit_b_spike_replaced"] = d["exit_b_spike_replaced"].fillna(False).astype(bool)
    ent = d["entry_price"].to_numpy(float)
    d["cost_cents_bp"] = np.where(ent > 0, (cost_cents / 100.0) / ent * 1e4, np.nan)
    d["halt_proxy_a"] = d["max_gap_a_sec"] > gap_thr
    d["halt_proxy_b"] = d["max_gap_b_sec"] > gap_thr
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    # validation: the recomputed Exit A price against v1's own recorded tick fill
    va = d[d["priced"] & d["natural_exit_price"].notna()]
    rel = np.abs(va["exit_a_price_tick"] - va["natural_exit_price"]) / va["natural_exit_price"]
    validation = {
        "n": int(len(va)),
        "share_within_0.1pct": round(float((rel <= 0.001).mean()), 4),
        "median_abs_rel_diff": round(float(np.nanmedian(rel)), 6),
        "note": "Exit A is recomputed here on the same tick basis as Exit B and cross-checked "
                "against v1's recorded natural_exit_price. Agreement confirms the two arms are "
                "priced on one basis.",
    }

    ok = d[d["priced"]]
    unc = ok[~ok["exit_b_censored"].fillna(False)]
    cen = ok[ok["exit_b_censored"].fillna(False)]

    table = [
        arm(ok, "A · window close — ALL", "exit_a_price_tick", "natural_exit_ts", cost_bp,
            "as traded today"),
        arm(ok, "B · participation decay — ALL", "exit_b_price_tick", "exit_b_ns_effective",
            cost_bp, "includes censored events exiting at the session-end horizon"),
        arm(unc, "A · window close — uncensored only", "exit_a_price_tick", "natural_exit_ts",
            cost_bp, "the like-for-like pair"),
        arm(unc, "B · participation decay — uncensored only", "exit_b_price_tick",
            "exit_b_ns_effective", cost_bp, "the like-for-like pair"),
        arm(cen, "A · window close — CENSORED class", "exit_a_price_tick", "natural_exit_ts",
            cost_bp, "participation never decays inside the session"),
        arm(cen, "B · session-end horizon — CENSORED class", "exit_b_price_tick",
            "exit_b_ns_effective", cost_bp,
            "NOT an intraday hold; a session-end hold is a different risk under D5"),
    ]

    # what EPG leaves on the table, or avoids: price change from window close to Exit B
    gap_move = ((ok["exit_b_price_tick"] / ok["exit_a_price_tick"] - 1.0) * 1e4)
    gap_block = {
        "n": int(gap_move.notna().sum()),
        **{f"p{int(q * 100)}": round(float(np.nanquantile(gap_move, q)), 1) for q in QS},
        "median": round(float(np.nanmedian(gap_move)), 1),
        "mean": round(float(np.nanmean(gap_move)), 1),
        "share_positive": round(float((gap_move.dropna() > 0).mean()), 4),
        "reading": "price change from window close to the participation-decay exit. Positive means "
                   "EPG left it on the table; negative means EPG avoided it.",
    }

    def by_facet(col: str) -> list:
        out = []
        for k, g in unc.groupby(col, dropna=False):
            if len(g) < FLOOR:
                out.append({col: str(k), "n": int(len(g)), "below_display_floor": True})
                continue
            a = arm(g, "A", "exit_a_price_tick", "natural_exit_ts", cost_bp)
            b = arm(g, "B", "exit_b_price_tick", "exit_b_ns_effective", cost_bp)
            out.append({col: str(k), "n": int(len(g)),
                        "A_gross_median": a["gross_bp_median"], "B_gross_median": b["gross_bp_median"],
                        "A_net_flat": a["net_bp_median_flat"], "B_net_flat": b["net_bp_median_flat"],
                        "A_net_ps": a["net_bp_median_per_share"],
                        "B_net_ps": b["net_bp_median_per_share"],
                        "A_win": a["win_rate_gross"], "B_win": b["win_rate_gross"]})
        return out

    lab = ok[ok["halt_label_available"].fillna(False)]
    halt_block = {
        "exact_labels": {
            "coverage_n": int(len(lab)), "coverage_share": round(float(len(lab) / len(ok)), 4),
            "share_A_spans_a_labelled_halt": (round(float(lab["halt_label_in_a"].mean()), 4)
                                              if len(lab) else None),
            "share_B_spans_a_labelled_halt": (round(float(lab["halt_label_in_b"].mean()), 4)
                                              if len(lab) else None),
            "source": C.HALT_LABELS,
            "limitation": "exact halt labels exist for 73 of the 903. The Exit B halt figure on "
                          "the other 830 rests on the gap proxy below.",
        },
        "gap_proxy": {
            "threshold_seconds": gap_thr,
            "share_A_holds_with_a_gap": round(float(ok["halt_proxy_a"].mean()), 4),
            "share_B_holds_with_a_gap": round(float(ok["halt_proxy_b"].mean()), 4),
            "max_gap_b_sec_quantiles": {
                f"p{int(q * 100)}": round(float(np.nanquantile(ok["max_gap_b_sec"], q)), 1)
                for q in (.5, .75, .95, .99)},
            "status": "PROXY, not a halt classifier -- a 60 s print gap in a name running "
                      "thousands of prints per 10 minutes is almost certainly a halt, but the "
                      "flag measures a gap.",
        },
    }

    summary = {
        "task": "T3 counterfactual exit -- the task that decides the rebuild",
        "config_hash": C.cfg_hash(),
        "spike_guard": {
            "found": "AMC 2024-05-14: naive last-print-at-or-before priced the exit at $11.48 "
                     "against entry and v1's own recorded exit both at $6.63 -- a single 4-share "
                     "print (conditions [32,37]) reverting immediately. NOT anticipated by the "
                     "brief; found mid-run. See common.py::last_print_at_or_before_robust for the "
                     "full account and why odd lots were not excluded outright (44% of all "
                     "trades in this archive).",
            "spike_threshold": C.SPIKE_THRESHOLD,
            "n_exit_a_spike_replaced": int(d["exit_a_spike_replaced"].sum()),
            "n_exit_b_spike_replaced": int(d["exit_b_spike_replaced"].sum()),
            "status": "a new, declared rule for this task only, not a claimed repo convention",
        },
        "n_population": int(len(d)), "n_priced": int(len(ok)),
        "round_trips_per_arm": 1,
        "round_trips_note": cfg["exits"]["round_trips_note"],
        "cost": {"flat_bp": cost_bp, "per_share_cents": cost_cents,
                 "per_share_bp_median": round(float(np.nanmedian(d["cost_cents_bp"])), 1)},
        "exit_a_price_validation": validation,
        "censoring": {
            "n_uncensored": int(len(unc)), "n_censored": int(len(cen)),
            "share_censored": round(float(len(cen) / len(ok)), 4),
            "treatment": cfg["participation_rule"]["censoring"]["exit_for_censored"],
        },
        "policy_table": table,
        "markout_in_the_gap_bp": gap_block,
        "by_detection_price_decile_uncensored": by_facet("detection_price_decile"),
        "by_move_at_decile_uncensored": by_facet("move_at_decile"),
        "halt_exposure": halt_block,
        "output_parquet": OUT_PARQUET,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    C.write_json(OUT_JSON, summary)

    cols = ["arm", "n", "gross_bp_median", "gross_bp_mean", "net_bp_median_flat",
            "net_bp_median_per_share", "win_rate_gross", "win_rate_net_flat", "hold_sec_median"]
    print("\n=== EXIT A vs EXIT B ===")
    print(pd.DataFrame(table)[cols].to_string(index=False))
    print("\n=== GROSS DISTRIBUTION (bp) ===")
    print(pd.DataFrame([{"arm": t["arm"][:44], **t["gross_bp"]} for t in table if t["n"]])
          .to_string(index=False))
    print("\n=== MARKOUT IN THE GAP (window close -> participation decay), bp ===")
    print(json.dumps(gap_block, indent=2))
    print("\n=== HALT EXPOSURE ===")
    print(json.dumps(halt_block, indent=2))
    print("\n=== Exit A price validation ===")
    print(json.dumps(validation, indent=2))
    print("\n=== BY move_at DECILE (uncensored) ===")
    print(pd.DataFrame(summary["by_move_at_decile_uncensored"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
