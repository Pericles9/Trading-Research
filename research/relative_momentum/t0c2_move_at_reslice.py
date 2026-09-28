"""
R0-T0c2: the T0c check re-run with move_at, the causal measure, replacing momentum_pct.

Mandated by the 2026-09-18 erratum, which records a defect in T0c's specification rather
than in its execution: T0c sliced a forward markout on momentum_pct, a prior-close-to-
day's-high quantity that brief section I.2 bars from any bucketing use because it is not
known at decision time. Conditioning on it selects sessions that already ran, so a positive
shift is close to guaranteed by construction.

THE CAUSAL REPLACEMENT, per brief section I.2:

    move_at(e, tau) = (last qualifying trade price at or before tau - prior session close)
                      / prior session close

evaluated at tau = the entry instant of Phase 11's named cell, i.e. the detection anchor
plus 5 minutes of latency. Phase 11 already stores that price as `entry_price`, so:

    move_at_entry = (entry_price - prior_close) / prior_close

Both terms are tick-derived (D4). prior_close comes from t0a2_prior_close.py. `entry_price`
is known at entry by construction, so nothing after tau enters the slicing variable -- which
is the whole point of the re-run.

D4 Amendment A12 applies TO THE SLICING VARIABLE ITSELF: move_at is a cross-session ratio,
its denominator spanning (T-1, T0). flag_cross_session_extreme is carried and every headline
is reported with and without the flagged set, untrimmed first, flagged never dropped.

NO THRESHOLD IS SET. The primary object is the response curve across move_at_entry in
declared equal-population deciles, with the distribution and n in every bucket. The
50%-level slices are reported alongside only because they are the causal analogue of the
gate's own inherited floor, and they are labelled as such -- not as a chosen cut.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0c2_move_at_reslice.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402

SLICED = f"{C.ART}/t0c_named_cell_sliced.parquet"
PRIOR = f"{C.ART}/t0a2_prior_close.parquet"
OUT_JSON = f"{C.ART}/t0c2_move_at_reslice.json"
OUT_PARQUET = f"{C.ART}/t0c2_named_cell_move_at.parquet"

GATE_DATE = "2023-11-17"
LEVEL = 0.50   # the causal analogue of the gate's inherited min_mom = 50.0 floor
XS = "flag_cross_session_extreme"


def stats(d: pd.DataFrame, label: str, note: str = "") -> dict:
    if len(d) == 0:
        return {"slice": label, "n": 0, "note": note}
    mk = d["markout"].to_numpy(dtype=float)
    rt = d["rt_cost"].to_numpy(dtype=float)
    net = mk - rt

    def q(a, p):
        a = a[np.isfinite(a)]
        return round(float(np.quantile(a, p)) * 1e4, 1) if a.size else None

    return {
        "slice": label, "n": int(len(d)),
        "markout_bp_p25": q(mk, .25), "markout_bp_median": q(mk, .50),
        "markout_bp_p75": q(mk, .75),
        "share_markout_nonpositive": round(float((mk[np.isfinite(mk)] <= 0).mean()), 4)
                                     if np.isfinite(mk).any() else None,
        "rt_cost_bp_median": q(rt, .50),
        "net_bp_median": q(net, .50),
        "share_net_nonpositive": round(float((net[np.isfinite(net)] <= 0).mean()), 4)
                                 if np.isfinite(net).any() else None,
        "note": note,
    }


def main() -> int:
    cell = pd.read_parquet(os.path.join(C.REPO, SLICED))
    prior = pd.read_parquet(os.path.join(C.REPO, PRIOR))

    cell["key"] = cell["ticker"] + "|" + cell["event_date"]
    prior["key"] = prior["ticker"] + "|" + prior["event_date_canonical"]
    cell = cell.merge(prior[["key", "prior_close", "prior_close_available"]],
                      on="key", how="left")
    cell["prior_close_available"] = cell["prior_close_available"].fillna(False)

    cell["move_at_entry"] = np.where(
        cell["prior_close_available"] & (cell["prior_close"] > 0),
        (cell["entry_price"] - cell["prior_close"]) / cell["prior_close"], np.nan)
    cell["move_ge_level"] = cell["move_at_entry"] >= LEVEL
    cell["date_ge_boundary"] = cell["event_date"] >= GATE_DATE
    cell.to_parquet(os.path.join(C.REPO, OUT_PARQUET), index=False)

    n_cell = len(cell)
    n_move = int(cell["move_at_entry"].notna().sum())
    m = cell[cell["move_at_entry"].notna()].copy()

    checks = [
        {"name": "named_cell_row_count", "pass": bool(n_cell == 10544),
         "n": n_cell, "expected": 10544},
        {"name": "move_at_entry_coverage_of_named_cell",
         "pass": bool(n_cell - n_move == 0),
         "n_covered": n_move, "n_not_covered": int(n_cell - n_move),
         "note": "rows without a tick-derived prior close are carried in the parquet with "
                 "move_at_entry NULL, never dropped. unavailable, zero and censored stay "
                 "three distinct states."},
    ]

    # ---- how much of T0c's flip population was lookahead ------------------
    ct = pd.crosstab(m["mom_ge_50"], m["move_ge_level"])
    ct.index = [f"momentum_pct>=50 {i}" for i in ct.index]
    ct.columns = [f"move_at_entry>=50% {c}" for c in ct.columns]

    # ---- the response curve: no threshold, equal-population deciles -------
    m["move_decile"] = pd.qcut(m["move_at_entry"], 10, labels=False, duplicates="drop")
    curve = []
    for dec, g in m.groupby("move_decile"):
        row = stats(g, f"decile {int(dec)}")
        row["move_at_entry_lo"] = round(float(g["move_at_entry"].min()), 4)
        row["move_at_entry_hi"] = round(float(g["move_at_entry"].max()), 4)
        row["move_at_entry_median"] = round(float(g["move_at_entry"].median()), 4)
        curve.append(row)

    # ---- the T0c table, rebuilt on the causal variable --------------------
    rows = [
        stats(cell, "S0 Phase 11 named cell, as published", "unchanged baseline"),
        stats(m, "S1 named cell with move_at_entry defined", "the causal-variable population"),
        stats(m[~m["move_ge_level"] & ~m["date_ge_boundary"]],
              "C2 move < 50% AND before 2023-11-17", "neither"),
        stats(m[m["move_ge_level"] & ~m["date_ge_boundary"]],
              "C3 move >= 50% AND before 2023-11-17", "causal move level only"),
        stats(m[~m["move_ge_level"] & m["date_ge_boundary"]],
              "C4 move < 50% AND on/after 2023-11-17", "date boundary only"),
        stats(m[m["move_ge_level"] & m["date_ge_boundary"]],
              "C5 move >= 50% AND on/after 2023-11-17 — causal analogue of S5",
              "compare against T0c's S5 (+66 bp markout, -57 bp net)"),
        stats(m[m["in_pf_run"].fillna(False)],
              "C7 the phase_f/val_full PF population itself",
              "same population as T0c's S7, unchanged -- listed for continuity"),
    ]

    # ---- A12 on the causal slices, including the erratum's one lead -------
    flag_rows = []
    for label, sub in [("S0 named cell", cell),
                       ("C5 causal gate-analogue domain",
                        m[m["move_ge_level"] & m["date_ge_boundary"]]),
                       ("C7 PF population", m[m["in_pf_run"].fillna(False)])]:
        f = sub[XS].fillna(False)
        flag_rows.append(stats(sub[~f], f"{label} — flag clear", "A12"))
        flag_rows.append(stats(sub[f], f"{label} — FLAGGED", "A12"))

    n_fail = sum(1 for c in checks if not c["pass"])
    summary = {
        "task": "R0-T0c2 named cell re-sliced on move_at (causal), replacing momentum_pct",
        "config_hash": C.cfg_hash(),
        "mandated_by": "2026-09-18 erratum to claude/r0_t0b_population_overlap_read.md",
        "slicing_variable": {
            "name": "move_at_entry",
            "formula": "(entry_price - prior_close) / prior_close",
            "tau": "Phase 11 named-cell entry = detection anchor + 5 min latency",
            "causal": "entry_price is known at tau by construction; prior_close is a T-1 "
                      "quantity. Nothing after tau enters the slicing variable.",
            "prior_close_source": PRIOR,
            "d4": "both terms tick-derived; no spine numeric column enters.",
            "a12": "move_at is a cross-session ratio (denominator spans T-1 to T0), so "
                   "flag_cross_session_extreme applies to the SLICING VARIABLE itself and "
                   "every headline is reported with and without the flagged set.",
        },
        "level_note": f"the {LEVEL:.0%} level is the causal analogue of the gate's inherited "
                      "min_mom = 50.0 floor and is labelled as such. It is not a chosen cut; "
                      "the response curve below sets no threshold at all.",
        "n_checks": len(checks), "n_fail": n_fail, "checks": checks,
        "lookahead_vs_causal_crosstab": ct.to_dict(),
        "lookahead_vs_causal_note":
            "off-diagonal cells are the events T0c's momentum_pct >= 50 slice included that a "
            "decision-time measure would not have (and vice versa). The size of the top-right "
            "cell is how much of T0c's flip population was only visible in hindsight.",
        "slices": rows,
        "response_curve_deciles": curve,
        "cross_session_flag_split_A12": flag_rows,
        "outputs": [OUT_PARQUET],
    }
    C.write_json(OUT_JSON, summary)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("slices", "response_curve_deciles",
                                   "cross_session_flag_split_A12")},
                     indent=2, default=str))
    cols = ["slice", "n", "markout_bp_p25", "markout_bp_median", "markout_bp_p75",
            "share_markout_nonpositive", "rt_cost_bp_median", "net_bp_median",
            "share_net_nonpositive"]
    print("\nSLICES (causal variable)")
    print(pd.DataFrame(rows)[cols].to_string(index=False))
    print("\nRESPONSE CURVE — equal-population deciles of move_at_entry")
    print(pd.DataFrame(curve)[["slice", "n", "move_at_entry_lo", "move_at_entry_hi",
                               "markout_bp_median", "rt_cost_bp_median", "net_bp_median",
                               "share_net_nonpositive"]].to_string(index=False))
    print("\nA12 cross-session split")
    print(pd.DataFrame(flag_rows)[cols].to_string(index=False))
    print("\nLOOKAHEAD vs CAUSAL crosstab")
    print(ct.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
