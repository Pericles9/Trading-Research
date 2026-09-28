"""
R0-T0c: re-slice Phase 11's existing T7 output onto the gate-admissible domain.

The 2026-09-18 read of T0b (section 3) proposes this as the cheap next check, and it is
exactly that: no new data pass, no tick read, no new measurement. Phase 11's
t7_cost_vs_capture.parquet is already per (ticker, event_date, latency, hold); this
re-slices the named cell and reports the same statistics on nested sub-populations.

The question: Phase 11's negative median is measured over (approximately) all of D1, while
PF = 1.9194 is measured over a mom_pct >= 50, date >= 2023-11-17 sliver of it. Does the
median flip on that sliver?

WHAT THIS CANNOT SETTLE, stated before the numbers rather than after. Phase 11's markout is
a FIXED-HORIZON trade: enter at the detection anchor + 5 min latency, hold 30 min, exit.
The gate's PF is a DIFFERENT trade: enter on an EPG rising edge, exit on window close,
median hold 52 seconds in the val_full run. Re-slicing the population does not make the two
the same trade. A flip would show that Phase 11's own measurement behaves differently on
the gate's domain; it would not reconcile the two figures. A non-flip would show the
population split does not explain the gap, leaving the trade definition and the other
repository's cost and fill assumptions as the remaining explanations. Either way this is a
population diagnostic, not a reconciliation.

D4 Amendment A12: flag_cross_session_extreme is carried and every slice is reported with
and without it, untrimmed first, flagged rows never dropped.

Units: markout and rt_cost are both fractions of price (research/phase_10e/t6_adverse_tail.py
reads markout * 10000 as bp; 70.98 bp = 0.007098), so markout - rt_cost is well posed.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0c_phase11_reslice.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402

T7 = "results/phase_11/artifacts/t7_cost_vs_capture.parquet"
MEMBERSHIP = f"{C.ART}/t0b_membership.parquet"
OUT_JSON = f"{C.ART}/t0c_phase11_reslice.json"
OUT_PARQUET = f"{C.ART}/t0c_named_cell_sliced.parquet"

NAMED = {"det_segment": "rth", "latency": 5, "hold": 30}
GATE_DATE = "2023-11-17"   # scanner-epg-momentum/backtest/config/holdout_boundary.json
GATE_MOM = 50.0            # scanner .../data/loaders/trades.py::list_events min_mom


def stats(d: pd.DataFrame, label: str, note: str = "") -> dict:
    """Distribution first. Medians are reported with the quartiles around them and with
    the share of the population on each side, never alone."""
    if len(d) == 0:
        return {"slice": label, "n": 0, "note": note}
    mk = d["markout"].to_numpy(dtype=float)
    rt = d["rt_cost"].to_numpy(dtype=float)
    net = mk - rt
    ok_net = np.isfinite(net)

    def q(a, p):
        a = a[np.isfinite(a)]
        return float(np.quantile(a, p)) * 1e4 if a.size else None

    return {
        "slice": label,
        "n": int(len(d)),
        "n_markout_defined": int(np.isfinite(mk).sum()),
        "n_net_defined": int(ok_net.sum()),
        "markout_bp_p25": q(mk, 0.25),
        "markout_bp_median": q(mk, 0.50),
        "markout_bp_p75": q(mk, 0.75),
        "share_markout_nonpositive": float((mk[np.isfinite(mk)] <= 0).mean())
                                     if np.isfinite(mk).any() else None,
        "rt_cost_bp_median": q(rt, 0.50),
        "net_bp_p25": q(net, 0.25),
        "net_bp_median": q(net, 0.50),
        "net_bp_p75": q(net, 0.75),
        "share_net_nonpositive": float((net[ok_net] <= 0).mean()) if ok_net.any() else None,
        "note": note,
    }


def main() -> int:
    g = pd.read_parquet(os.path.join(C.REPO, T7))
    g["event_date"] = g["event_date"].astype(str).str.slice(0, 10)
    cell = g[(g["det_segment"] == NAMED["det_segment"])
             & (g["latency"] == NAMED["latency"])
             & (g["hold"] == NAMED["hold"])].copy()

    checks = [{
        "name": "named_cell_reproduces_phase_11_n",
        "pass": bool(len(cell) == 10544), "n": int(len(cell)), "expected": 10544,
        "cell": NAMED,
        "source": "results/phase_11/artifacts/t7_cost_vs_capture.json named_cell.n",
    }]

    d1 = C.load_d1()
    d1["key"] = d1["ticker"] + "|" + d1["event_date_canonical"]
    mem = pd.read_parquet(os.path.join(C.REPO, MEMBERSHIP))
    mem["key"] = mem["ticker"] + "|" + mem["event_date_canonical"]

    cell["key"] = cell["ticker"] + "|" + cell["event_date"]
    cell = cell.merge(d1[["key", "momentum_pct"]], on="key", how="left")
    cell = cell.merge(mem[["key", "gate_admitted", "gate_run", "in_pf_run"]],
                      on="key", how="left")
    for c in ("gate_admitted", "gate_run", "in_pf_run"):
        cell[c] = cell[c].fillna(False)

    n_unmatched = int(cell["momentum_pct"].isna().sum())
    checks.append({
        "name": "named_cell_rows_resolve_to_D1",
        "pass": bool(n_unmatched == 0),
        "n_rows": int(len(cell)), "n_not_in_D1": n_unmatched,
        "note": "rows not in D1 are carried, never dropped; they are file2 or out-of-scope "
                "events that Phase 11's own detection universe included.",
    })

    cell["mom_ge_50"] = cell["momentum_pct"] >= GATE_MOM
    cell["date_ge_boundary"] = cell["event_date"] >= GATE_DATE
    cell.to_parquet(os.path.join(C.REPO, OUT_PARQUET), index=False)

    in_d1 = cell[cell["momentum_pct"].notna()]

    rows = [
        stats(cell, "S0 Phase 11 named cell, as published",
              "the baseline the published median comes from"),
        stats(in_d1, "S1 named cell, D1 only", "drops rows outside D1"),
        # the 2x2: the two mechanisms T0b identified, separated
        stats(in_d1[~in_d1["mom_ge_50"] & ~in_d1["date_ge_boundary"]],
              "S2 mom < 50 AND before 2023-11-17", "neither gate mechanism"),
        stats(in_d1[in_d1["mom_ge_50"] & ~in_d1["date_ge_boundary"]],
              "S3 mom >= 50 AND before 2023-11-17", "momentum floor only"),
        stats(in_d1[~in_d1["mom_ge_50"] & in_d1["date_ge_boundary"]],
              "S4 mom < 50 AND on/after 2023-11-17", "date boundary only"),
        stats(in_d1[in_d1["mom_ge_50"] & in_d1["date_ge_boundary"]],
              "S5 mom >= 50 AND on/after 2023-11-17 -- THE GATE-ADMISSIBLE DOMAIN",
              "both mechanisms; this is the slice section 3 asks about"),
        stats(in_d1[in_d1["gate_admitted"] & in_d1["date_ge_boundary"]],
              "S6 gate lister admits AND on/after 2023-11-17",
              "the gate's own lister rule rather than the mom >= 50 proxy"),
        stats(in_d1[in_d1["in_pf_run"]],
              "S7 the phase_f/val_full PF population itself",
              "the exact events PF = 1.9194 was computed on, intersected with the named cell"),
    ]

    # A12: the same ladder split on the cross-session magnitude flag. Untrimmed is primary.
    xs = "flag_cross_session_extreme"
    flag_rows = []
    for label, sub in [("S0 named cell", cell),
                       ("S5 gate-admissible domain",
                        in_d1[in_d1["mom_ge_50"] & in_d1["date_ge_boundary"]]),
                       ("S7 PF population", in_d1[in_d1["in_pf_run"]])]:
        flag_rows.append(stats(sub[~sub[xs].fillna(False)], f"{label} — flag clear", "A12"))
        flag_rows.append(stats(sub[sub[xs].fillna(False)], f"{label} — FLAGGED", "A12"))

    n_fail = sum(1 for c in checks if not c["pass"])
    summary = {
        "task": "R0-T0c Phase 11 T7 named cell re-sliced on the gate-admissible domain",
        "config_hash": C.cfg_hash(),
        "prompted_by": "the 2026-09-18 read of T0b, section 3",
        "what_this_cannot_settle":
            "Phase 11's markout is a fixed-horizon trade (detection anchor + 5 min latency, "
            "30 min hold). The gate's PF is a rising-edge entry with a window-close exit and "
            "a 52-second median hold. Re-slicing the population does not make them the same "
            "trade. This is a population diagnostic, not a reconciliation.",
        "named_cell": NAMED,
        "gate_domain_definition": {"min_momentum_pct": GATE_MOM,
                                   "min_event_date": GATE_DATE,
                                   "date_source": "scanner-epg-momentum/backtest/config/"
                                                  "holdout_boundary.json val_split_start_date"},
        "units": "all *_bp columns are basis points (fraction * 1e4)",
        "n_checks": len(checks), "n_fail": n_fail, "checks": checks,
        "slices": rows,
        "cross_session_flag_split_A12": flag_rows,
        "outputs": [OUT_PARQUET],
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("slices", "cross_session_flag_split_A12")},
                     indent=2, default=str))
    cols = ["slice", "n", "markout_bp_p25", "markout_bp_median", "markout_bp_p75",
            "share_markout_nonpositive", "rt_cost_bp_median", "net_bp_median",
            "share_net_nonpositive"]
    print("\nSLICES")
    print(pd.DataFrame(rows)[cols].to_string(index=False))
    print("\nA12 cross-session split")
    print(pd.DataFrame(flag_rows)[cols].to_string(index=False))
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
