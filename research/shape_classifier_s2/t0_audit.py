"""
Shape classifier S2, T0 -- the timing audit (brief section 7, escalation row 1).

Part 1  A12. How `flag_cross_session_extreme` is built (research/phase_9/t1_ca_detector.py + common.py), checked on
        disk: the event-day close it reads equals the event day's last print (at or before 20:00) and that print is
        after tau; and every tracked file that reads the flag, classified as an input or a facet. The file list is
        checked against `git grep` so the inventory is complete by construction.
Part 2  Every model input: the latest data timestamp it reads, per event (Group A, T1) or per event x decision
        time (Group B and the tcs state, T2; Group C's query grid, recomputed here), asserted <= its decision time.
        A violation is a HARD STOP (row 1).
Part 3  Properties of the decision times themselves, recorded: the tau spike guard reads the print after tau;
        the live set is conditional on the vendor's day-level selection (D4 / A13); CLAUDE.md index check.

Runs after T1 and T2 (it audits what they built). Writes artifacts/t0_a12.json, t0_audit.parquet, t0_summary.json.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/t0_audit.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

# Every tracked .py that reads flag_cross_session_extreme, and how (read from each file's own use, 2026-09-28).
# "facet": a split or with/without sensitivity (A12's mandate) or a carried column; "input": feeds a fitted model,
# a selection rule or a threshold. The check below fails if git grep finds a file not listed here.
CONSUMERS = {
    "research/phase_9/t1_ca_detector.py": ("builder", "builds the flag for pairs tm1_t0, t0_t1, t0_t2, t0_t3"),
    "research/phase_9/t2_sensitivity.py": ("facet", "markouts reported flagged-only / unflagged / flagged-excluded per pair"),
    "research/phase_9/t3_retracement.py": ("facet", "retracement reported with the flag (either side) excluded and only"),
    "research/phase_9/t5_clustered.py": ("facet", "clustered interval with the t0_t1-flagged set removed, beside the full set"),
    "research/phase_9/chart_01.py": ("facet", "chart annotation"),
    "research/phase_9/chart_02.py": ("facet", "chart split flagged / unflagged"),
    "research/phase_10/v2_r13_detection.py": ("facet", "joined tm1_t0 flag; counts of flagged events reported"),
    "research/phase_10e/t1_candidate_entries.py": ("facet", "tm1_t0 flag carried on every candidate entry; count reported"),
    "research/phase_10e/t2_excursion.py": ("facet", "flag carried"),
    "research/phase_10e/t5_costed_markouts.py": ("facet", "every statistic with and without the tm1_t0-flagged set (A12)"),
    "research/phase_10e/t6_adverse_tail.py": ("facet", "with and without the tm1_t0-flagged set (A12)"),
    "research/phase_11/t4b_ordering_audit.py": ("facet", "file-ordering audit lists the flag artifact"),
    "research/phase_11/t7_cost_vs_capture.py": ("facet", "flag joined as one of three carried flags"),
    "research/relative_momentum/t0c_phase11_reslice.py": ("facet", "every slice with and without the flagged set (A12)"),
    "research/relative_momentum/t0c2_move_at_reslice.py": ("facet", "every headline with and without the flagged set (A12)"),
    "research/relative_momentum_v0/t4_diagnostic.py": ("facet", "split on the flag, flagged rows never dropped"),
    "research/relative_momentum_v1/t4_diagnostic.py": ("facet", "split on the flag, flagged rows never dropped"),
    "research/scale_field/event_panels.py": ("facet", "flag listed on event panels (any pair)"),
    "research/scope_universe_scan/basis_test.py": ("facet", "carried per A12 (docstring)"),
    "research/scope_universe_scan/basis_test_stage2.py": ("facet", "basis test reported with and without the tm1_t0-flagged set"),
    "research/attention_excursion_b1/t1_t2_summary.py": ("facet", "tm1_t0 flag joined to t2_tau; flagged count reported"),
    "research/attention_excursion_b1/t4_excursion.py": ("facet", "flag carried on the excursion rows"),
    "research/attention_excursion_b1/t5_attention.py": ("facet", "flag carried on the attention rows"),
    "research/attention_excursion_b1/charts.py": ("facet", "chart annotation"),
    "research/attention_excursion_b1/build_report.py": ("facet", "report sentence (flagged count)"),
    "research/attention_excursion_b2/t0_population.py": ("facet", "flag carried; counts reported"),
    "research/attention_excursion_b2/t1_excursion.py": ("facet", "flag carried"),
    "research/attention_excursion_b2/t2_attention.py": ("facet", "flag carried"),
    "research/attention_excursion_b2/t4_step_zero.py": ("facet", "one facet of the step-zero panels"),
    "research/attention_excursion_b2/build_report.py": ("facet", "facet listing in the report"),
    "research/shape_atlas_s1/t1_paths.py": ("facet", "flag carried on s1_events"),
    "research/shape_atlas_s1/t5_atlas.py": ("facet", "tape descriptor shown per type (hindsight allowed in S1)"),
    "research/shape_atlas_s1/build_report.py": ("facet", "descriptor listing in the report"),
}


def a12_part(pop: pd.DataFrame) -> dict:
    cfg9 = json.load(open(S.REPO / "config/phase_9.json"))
    fl = pd.read_parquet(S.src("a12_flags"))
    fl = fl[fl["session_pair"] == "tm1_t0"].copy()
    fl["event_date_canonical"] = pd.to_datetime(fl["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    meta = pd.read_parquet(S.art("t2_event_meta.parquet"))
    x = pop[["event_id", "ticker", "event_date_canonical", "tau_ns", "type100"]].merge(meta, on="event_id").merge(
        fl[["ticker", "event_date_canonical", "price_later", "price_earlier", "flag_cross_session_extreme"]], on=["ticker", "event_date_canonical"], how="left")
    have = x["price_later"].notna()
    same = have & np.isclose(x["price_later"], x["last_print_px"], rtol=0, atol=1e-9)
    after = x["last_print_ns"] > x["tau_ns"]
    flag = x["flag_cross_session_extreme"].fillna(False).astype(bool)
    by_type = x[have].groupby("type100")["flag_cross_session_extreme"].agg(["mean", "sum", "size"]).reindex(S.TYPES)
    grep = subprocess.run(["git", "grep", "-l", "flag_cross_session_extreme", "--", "*.py"], cwd=S.REPO, capture_output=True, text=True).stdout.split()
    grep = sorted(g for g in grep if not g.startswith("research/shape_classifier_s2/"))
    missing = sorted(set(grep) - set(CONSUMERS))
    stale = sorted(set(CONSUMERS) - set(grep))
    assert not missing, f"A12 consumers not classified: {missing}"
    other = subprocess.run(["git", "grep", "-l", "flag_cross_session_extreme", "--", "*.md", "prompts", "docs", "config"], cwd=S.REPO,
                           capture_output=True, text=True).stdout.split()
    out = {
        "construction": {
            "code": "research/phase_9/t1_ca_detector.py:main, research/phase_9/common.py::session_closes / closes_wide",
            "per_pair": "r = log(p_later_close / p_earlier_close); flag = |r| >= ca_flag_log_threshold",
            "threshold": {"log": cfg9["ca_flag_log_threshold"], "ratio": [float(np.exp(-cfg9["ca_flag_log_threshold"])), float(np.exp(cfg9["ca_flag_log_threshold"]))]},
            "close": "ARG_MAX(last_price, minute_index) over event_minute_bars_v2 rows of that session offset: the last trade of the extended day (any segment)",
            "pair_used_by_b1_b2_s1": "tm1_t0 -- (close of T-1, close of T0); research/attention_excursion_b1/t1_t2_summary.py joins session_pair == 'tm1_t0'",
            "consequence": "the T0 close is the event day's last trade, so the flag reads the whole event day, after tau",
        },
        "checked_on_disk": {
            "events": int(len(x)), "with_tm1_t0_pair": int(have.sum()),
            "t0_close_equals_event_day_last_print_at_or_before_2000": int(same.sum()),
            "t0_close_differs": int((have & ~same).sum()),
            "event_day_last_print_after_tau": int((have & after).sum()),
            "flagged": int(flag.sum()),
            "flag_rate_by_type": {t: {"rate": float(r["mean"]) if pd.notna(r["mean"]) else None, "flagged": int(r["sum"]) if pd.notna(r["sum"]) else 0,
                                      "n": int(r["size"]) if pd.notna(r["size"]) else 0} for t, r in by_type.iterrows()},
        },
        "consumers_code": [{"file": f, "use": CONSUMERS[f][0], "how": CONSUMERS[f][1]} for f in grep],
        "consumers_as_input": [f for f in grep if CONSUMERS[f][0] == "input"],
        "consumers_listed_not_found": stale,
        "consumers_non_code_records": sorted(other),
        "outside_repo": "the rough pre-S2 run (Claude, on S1's per-event tables, brief 'What came before') used the flag as a model input; it is not in the repository",
    }
    S.write_json("t0_a12.json", out)
    return out


def input_part(pop: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    A = pd.read_parquet(S.art("t1_group_a.parquet"))
    tau = A["c__tau_d_ns"].astype("int64").to_numpy()                       # the decision time at tau (tau_d)
    rows = []
    groups = {"ts__timing": "timing (time of day, segment, auction minute)", "ts__first_print": "tau_is_first_print",
              "ts__runup": "run-up descriptors, gap_share (S1: prints in [segment start, tau])", "ts__pre": "pre-tau trade rate and dollar flow",
              "ts__turnover": "turnover (shares 04:00 -> tau; tau-anchored count)", "ts__accel": "accel_k0..4, validity, a2_ignition (rung windows end at tau)",
              "ts__cross_section": "live_n, flow_share (live names crossed at or before tau; windows end at tau)",
              "ts__filings": "filing_24h, last_form (accepted < tau)", "ts__dilution": "dilution_tau (R3)", "ts__shares": "shares outstanding (R3)",
              "ts__reverse_split": "reverse split in 365 days (last split timestamp)", "ts__short_interest": "short interest share (R2: assumed publication 20:00 ET)"}
    for c, what in groups.items():
        v = pd.to_numeric(A[c], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(v)
        lag = (v[ok] - tau[ok]) / S.NS
        rows.append({"group": "A", "input": c.replace("ts__", ""), "what": what, "decision_time": "tau", "n": int(ok.sum()),
                     "n_after_decision": int((v[ok] > tau[ok]).sum()), "max_latest_minus_decision_s": float(lag.max()) if lag.size else None,
                     "median_latest_minus_decision_s": float(np.median(lag)) if lag.size else None})
    ck = pd.read_parquet(S.art("t2_checkpoints.parquet"), columns=["event_id", "time", "state", "d_ns", "ts__B", "ts__tcs", "elapsed_min"])
    r = ck[ck["state"] == "reached"]
    for t in S.TIMES:
        g = r[r["time"] == t]
        d = g["d_ns"].astype("int64").to_numpy()
        for c, what in (("ts__tcs", "tcs_state (R1)"), ("ts__B", "Group B (prints tau < ts <= d)")):
            v = g[c].astype("float64").to_numpy()
            ok = np.isfinite(v)
            if not ok.any():
                continue
            lag = (v[ok] - d[ok]) / S.NS
            rows.append({"group": "B" if c == "ts__B" else "tape", "input": c.replace("ts__", ""), "what": what, "decision_time": t, "n": int(ok.sum()),
                         "n_after_decision": int((v[ok] > d[ok]).sum()), "max_latest_minus_decision_s": float(lag.max()),
                         "median_latest_minus_decision_s": float(np.median(lag))})
        if t != "tau":
            grid = S.master_grid_s()
            E = g["elapsed_min"].to_numpy() * 60.0
            used = grid[S.query_index(E, grid)].max(axis=1)                 # latest elapsed second Group C reads
            lag = used - E
            rows.append({"group": "C", "input": "group_c_query_grid", "what": "path so far on the master grid (x(t) reads prints <= tau + t)",
                         "decision_time": t, "n": int(len(g)), "n_after_decision": int((lag > 1e-9).sum()),
                         "max_latest_minus_decision_s": float(lag.max()), "median_latest_minus_decision_s": float(np.median(lag))})
    au = pd.DataFrame(rows)
    au["config_hash"] = S.cfg_hash()
    au.to_parquet(S.art("t0_audit.parquet"), index=False)
    return au, int(au["n_after_decision"].sum())


def main() -> int:
    pop = S.load_population()
    a12 = a12_part(pop)
    au, viol = input_part(pop)
    t2 = S.read_json("t2_summary.json")
    t1 = S.read_json("t1_summary.json")
    idx = subprocess.run([str(S.REPO / ".venv/Scripts/python.exe"), "tools/verify_claude_md_indices.py"], cwd=S.REPO, capture_output=True, text=True)
    S.write_json("t0_summary.json", {
        "config_hash": S.cfg_hash(),
        "row1": {"rule": "any input uses data after its decision time", "violations": viol, "fires": bool(viol > 0)},
        "a12": {"flagged": a12["checked_on_disk"]["flagged"], "t0_close_is_last_print": a12["checked_on_disk"]["t0_close_equals_event_day_last_print_at_or_before_2000"],
                "last_print_after_tau": a12["checked_on_disk"]["event_day_last_print_after_tau"], "consumers_as_input": a12["consumers_as_input"],
                "code_consumers": len(a12["consumers_code"])},
        "tau_rounding": {"finding": "every stored tau_ns in b1 t2_tau, b2 and S1 is a multiple of 256 ns: float64-rounded upstream (error <= 128 ns either way)",
                         "handling": "decision time at tau = tau_d = max(stored tau, the crossing print's own timestamp); b2 / S1 inputs built on the stored tau "
                                     "are then <= tau_d, the crossing print is <= tau_d, and entries are after it", **t1["tau_rounding"]},
        "short_interest_dating": "F1 si_asof_ns is the settlement date, not publication (Cooper R2)",
        "decision_time_properties": {
            "tau_spike_guard": {"note": "tau is the first print >= 1.30 x prior close that is not a spike; the spike test reads the print after it, so tau is confirmed at its successor",
                                **t2["tau_confirmation"]},
            "live_set": "live_n / flow_share count other D1 names that crossed at or before tau; D1 membership is the vendor's day-level selection (momentum_pct, RTH high), so the live set is conditional on that selection boundary like the whole population (D4, A13)",
            "label": "the label (S1 theory type) is hindsight by definition and is only ever an output",
        },
        "claude_md_indices": {"exit_code": idx.returncode, "stdout_tail": idx.stdout[-600:]},
    })
    print(au.groupby(["group", "input"])["n_after_decision"].sum().to_string())
    print("row 1 violations:", viol, "| A12:", {k: a12["checked_on_disk"][k] for k in ("with_tm1_t0_pair", "t0_close_equals_event_day_last_print_at_or_before_2000", "event_day_last_print_after_tau", "flagged")})
    print("claude_md indices exit", idx.returncode)
    assert viol == 0, f"HARD STOP row 1: {viol} input rows read data after their decision time"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
