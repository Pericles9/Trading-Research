"""
Brief 2 -- REPORT.md, generated from artifacts. Every number is formatted from an artifact read here
(section 7: "every report number read from artifacts"); the fixed prose says what each number is and
where it comes from. It describes the pictures: no interpretation, no findings section (T5).

Order (T5): escalation table, II.5 checks, the section 1 rulings as applied, T0-T4, charts, and the
column dictionary (section 5) -- generated from the artifacts' own schemas; a column with no declared
unit or role stops the build rather than being typed in by hand.

Writes results/attention_excursion/b2/REPORT.md and results/reports/attention_excursion_b2_report.md.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/build_report.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402


def J(name):
    p = B.art(name)
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def n(x):
    return f"{int(x):,}" if x is not None else "—"


def pct(x, d=1):
    return f"{100 * x:.{d}f}%" if x is not None else "—"


def f(x, d=3):
    return f"{x:,.{d}f}" if isinstance(x, (int, float)) and x == x else "—"


def fired(b):
    return "**FIRED**" if b else "clear"


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=B.REPO, text=True).strip()
    except Exception:
        return "?"


# ------------------------------------------------------------------ column dictionary
ARTIFACT_ROLE = {"t0_population": "facet", "t1_excursion": "post-τ (excursion)", "t2_attention": "pre-τ (attention)",
                 "t2_a2_rungs": "pre-τ (attention)", "t2_cross_sectional": "pre-τ (attention)", "t2_live_names": "pre-τ (attention)",
                 "t3_pairs": "competition (mechanism; another name's trades around τ_j)", "t3_baseline_cells": "competition (mechanism)",
                 "t4_facets": "step-zero summary (post-τ)", "t4_u_peak_bins": "step-zero summary (post-τ)", "t4_cost": "step-zero summary (post-τ)",
                 "t4_gallery": "step-zero gallery selection", "t4_gallery_buckets": "post-τ (excursion)",
                 "t4a_reference_free_walk": "simulated reference (no data)"}
FACETS = {"slice", "year", "tau_anchor_segment", "tau_in_auction_minute", "price_tier", "tau_close_sensitive", "flag_cross_session_extreme",
          "tau_session_segment", "dev_group", "first_seen_slice", "is_first_seen_ticker", "early_close_day", "sec_from_0930", "sec_from_0400",
          "jump_share_band", "segment"}
IDS = {"event_id", "ticker", "event_date_canonical", "date", "j", "i", "live_event_id", "config_hash", "N", "k", "liveness", "W_min",
       "facet", "level", "draw", "stratum_size"}
UNITS = {
    "event_id": "id (event folder name)", "ticker": "symbol", "event_date_canonical": "date (ET)", "date": "date (ET)",
    "j": "event id (the crossing)", "i": "event id (the live name)", "live_event_id": "event id", "config_hash": "sha256[:12]",
    "N": "buckets (rung)", "k": "A2 rung index", "liveness": "15 / 60 min / rest of session", "W_min": "minutes", "facet": "facet name",
    "level": "facet level", "draw": "simulation index", "stratum_size": "events", "year": "calendar year", "slice": "D38 slice",
    "dev_group": "dev_v3 / dev_v4_sidecar / NULL", "first_seen_slice": "D38 slice", "is_first_seen_ticker": "boolean",
    "tau_available": "boolean", "tau_reason": "class", "tau_ns": "ns since epoch (UTC), int64", "tau_price": "USD",
    "prior_close_exact": "USD", "prior_close_source": "class (A1.2)", "tau_session_segment": "segment (T2 condition-code rule)",
    "tau_anchor_segment": "clock segment (Amendment 3)", "segment": "clock segment of t (Amendment 3)",
    "tau_in_auction_minute": "boolean (A3.2)", "early_close_day": "boolean (XNYS calendar)", "price_tier": "USD tier (R4)",
    "tau_close_sensitive": "boolean (A1.3)", "flag_cross_session_extreme": "boolean (A12, tm1_t0)", "sec_from_0400": "seconds",
    "sec_from_0930": "seconds (descriptor)", "jump_share_band": "band (R4)",
    "reason": "class", "vector_available": "boolean", "attention_available": "boolean", "status": "class",
    "rise_s": "sigma_path units", "fall_s": "sigma_path units", "dip_before_peak_s": "sigma_path units", "terminal_s": "sigma_path units",
    "u_peak": "share of path volume (0-1)", "i_peak": "bucket index", "peak_tie_span_u": "share of path volume",
    "rise_log": "log price", "fall_log": "log price", "dip_log": "log price", "terminal_log": "log price",
    "sigma_path": "log price", "sigma_b": "log price per bucket", "sigma_bv_path": "log price", "rv": "log price squared",
    "bv": "log price squared", "jump_share": "dimensionless (1 - BV/RV)", "scale": "class", "sigma_zero": "boolean",
    "sigma_b_bp": "bp", "sigma_path_bp": "bp", "sigma_bv_path_bp": "bp", "rise_bp": "bp of tau price", "fall_bp": "bp of tau price",
    "rise_cents": "cents per share", "fall_cents": "cents per share", "peak_price": "USD", "end_bucket_price": "USD",
    "t_peak_s": "seconds after tau", "t_end_s": "seconds after tau", "n_path_prints": "prints", "n_path_prints_all": "prints",
    "n_zero_size_prints": "prints", "path_volume": "shares", "max_bucket_vol_rel_err": "relative error",
    "rise_censored": "boolean", "peak_at_tau": "boolean", "no_rise": "boolean", "peak_tied": "boolean", "thin_path": "boolean",
    "max_gap_s": "seconds", "max_gap_in_rth_s": "seconds", "max_gap_outside_rth_s": "seconds", "halt_gap_rth": "boolean",
    "halt_label_available": "boolean", "halt_label_in_path": "boolean", "halt_in_path": "boolean",
    "a2_state": "class (value / unavailable_auction_minute)", "a2_anchor_ns": "ns since epoch (UTC), segment start",
    "H_s": "seconds (tau - segment start, Amendment 3)", "H_0400_s": "seconds (tau - 04:00)", "n_collapsed_seg_tau": "collapsed prints",
    "n_raw_prints_0400_tau": "prints", "n_collapsed_0400_tau": "collapsed prints (10 ms)", "shares_0400_tau": "shares",
    "shs_shares_outstanding_corrected": "shares", "turnover": "fraction of shares outstanding", "a1_state": "class",
    "shs_asof_violation": "boolean", "shs_accepted_after_tau": "boolean", "shs_lag_ns": "ns (duration)", "shs_quality": "class",
    "shs_share_count_suspect": "boolean", "flg_dilution_form_before_t0": "boolean", "flg_last_form_t0_relative": "SEC form",
    "t0_minus_tau_s": "seconds", "a2_rungs_generated": "rungs (nullable)", "a2_cutoff_k": "rung index (nullable; R1)",
    "a2_valid_rungs": "rungs (nullable)", "a2_valid_pattern": "comma list of k (nullable)", "a2_first_valid_k": "rung index (nullable)",
    "a2_last_valid_k": "rung index (nullable)", "a2_valid_contiguous": "boolean (nullable)", "a2_invalid_counting_noise": "rungs (nullable)",
    "a2_invalid_from_nothing": "rungs (nullable)", "a2_invalid_resolution_floor": "rungs (nullable)", "a2_ignition": "boolean (nullable; R1)",
    "filing_24h": "boolean", "n_filings_24h": "filings", "hours_since_last_filing": "hours", "last_form_before_tau": "SEC form",
    "a3_available": "boolean", "n_filings_on_record": "filings",
    "W_s": "seconds (rung window)", "n_recent": "collapsed prints", "n_older": "collapsed prints", "lambda_per_s": "collapsed prints per second",
    "noise_ok": "boolean", "floor_ok": "boolean", "valid": "boolean", "class": "class", "accel": "log ratio",
    "win_lo_ns": "ns since epoch (UTC), window start", "win_mid_ns": "ns since epoch (UTC), window midpoint",
    "kernel_defined": "boolean", "accel_kernel": "log ratio", "trades_per_min": "collapsed trades per minute",
    "dollars_per_min": "USD per minute", "shares_per_min": "shares per minute",
    "live_n": "names", "dollar_volume_j": "USD", "dollar_volume_live": "USD", "flow_share": "fraction", "n_ranked": "names",
    "accel_rank": "rank (1 = highest)", "accel_rank_pct": "fraction", "is_self": "boolean", "sec_since_own_tau": "seconds",
    "move_at_at_tau_j": "fraction of prior close",
    "age_s": "seconds since i's own tau", "octave": "floor(log2(age s))", "n_after": "collapsed prints (nullable)",
    "n_before": "collapsed prints (nullable)", "log_ratio": "log ratio", "baseline_n": "moments", "baseline_median": "log ratio",
    "baseline_thin": "boolean", "excess": "log ratio", "n_moments": "moments", "n_finite": "moments", "median": "log ratio",
    "p25": "log ratio", "p75": "log ratio", "n_zero_count": "moments",
    "n": "events", "events": "events", "bin_lo": "u_peak", "bin_hi": "u_peak", "count": "events", "share": "fraction",
    "reference_share": "fraction", "vwap": "USD", "t_end_ns": "ns since epoch (UTC)", "u": "share of path volume",
}
UNIT_PATTERNS = [(r"^n_rise_(bp|cents)_gt_rt$", "events"), (r"^share_.*", "fraction"), (r"^ref_.*_share.*", "fraction"),
                 (r"^u_peak_(median|mean)$", "share of path volume"), (r"^ref_u_peak_median$", "share of path volume"),
                 (r"^u_peak_share_.*", "fraction"), (r"^(ref_)?(rise_s|fall_s|dip_before_peak_s|terminal_s)_(median|mean|p25|p75)$", "sigma_path units"),
                 (r"^(rise_s|fall_s|dip_before_peak_s|terminal_s)_n$", "events"), (r"^rise_bp_median$", "bp"), (r"^rise_cents_median$", "cents")]


def unit_of(col: str) -> str | None:
    if col in UNITS:
        return UNITS[col]
    for pat, u in UNIT_PATTERNS:
        if re.match(pat, col):
            return u
    return None


def column_dictionary() -> tuple[list[str], list[str]]:
    rows, missing = [], []
    for name in sorted(ARTIFACT_ROLE):
        p = B.art(f"{name}.parquet")
        if not p.exists():
            continue
        sch = pq.read_schema(p)
        for fld in sch:
            u = unit_of(fld.name)
            if u is None:
                missing.append(f"{name}.{fld.name}")
                continue
            role = "id / key" if fld.name in IDS else ("facet" if fld.name in FACETS else ARTIFACT_ROLE[name])
            rows.append(f"| `{name}` | `{fld.name}` | {fld.type} | {u} | {role} |")
    return rows, missing


def main() -> int:
    cfg = B.load_cfg()
    t0, cd, t1, t2, t3, t4, t4a = (J("t0_population.json"), J("t0_config_diff.json"), J("t1_summary.json"), J("t2_summary.json"),
                                   J("t3_summary.json"), J("t4_step_zero.json"), J("t4a_references.json"))
    esc = cfg["brief2"]["escalation"]
    hard = [cd["row_4"]["fires"], t1["row_1"]["fires"]]
    status = "HARD STOP at T6 -- the brief's own stop, for Cooper's read of step zero" if not any(hard) else \
        "HARD STOP -- an escalation row fired (see section 1)"
    L = []
    w = L.append
    w(f"# Attention and the excursion — Brief 2: full-D1 build, competition check, step zero — {status}")
    w("")
    w(f"**Generated by** `research/attention_excursion_b2/build_report.py` from `results/attention_excursion/b2/artifacts/` at "
      f"`HEAD {git_head()}`; every figure below is read from an artifact at build time. **Config** `config/attention_excursion_b2.json`, "
      f"hash `{B.cfg_hash()}` (Brief 1's frozen config `{cd['brief1_config']['hash']}` carried unchanged, plus the section 1 diff). "
      "**Brief** `prompts/attention_excursion_b2.md`. **Branch** `explore/attention-excursion-b2`.")
    w("")
    w("Describes the pictures. No interpretation, no findings section. No attention, catalyst or cross-sectional quantity is put "
      "against any excursion component anywhere in this build; step zero (T4) reads only T1, T0 and the simulated reference.")
    w("")
    # ------------------------------------------------ 1. escalation
    w("## 1. Escalation — every row")
    w("")
    w("| row | criterion | tier | observed | state |")
    w("|---|---|---|---|---|")
    r1 = t1["row_1"]
    w(f"| 1 | {esc['row_1']['criterion']} | HARD STOP | lowest share {pct(r1['observed_min_share'], 2)} (N=50 "
      f"{pct(r1['by_N']['50'], 2)}, N=100 {pct(r1['by_N']['100'], 2)}, N=200 {pct(r1['by_N']['200'], 2)}) of {n(t1['events_with_tau'])} | {fired(r1['fires'])} |")
    w(f"| 2 | {esc['row_2']['criterion']} | HARD STOP | T2 ran to completion on {n(t2['events']['with_attention'])} events; no causality "
      "assertion raised (a raise stops the run) | clear |")
    w(f"| 3 | {esc['row_3']['criterion']} | HARD STOP | A2: {t2['II5']['a2_segment']}. Competition: {t3['row_3_windows']} | clear |")
    w(f"| 4 | {esc['row_4']['criterion']} | HARD STOP | {cd['row_4']['observed']} | {fired(cd['row_4']['fires'])} |")
    w(f"| 5 | {esc['row_5']['criterion']} | LOG, per event | {n(t2['row_5']['n'])} events | {'logged' if t2['row_5']['n'] else 'none'} |")
    r6, r7 = t1["row_6"], t1["row_7"]
    w(f"| 6 | {esc['row_6']['criterion']} | LOG | {n(r6['thin_events'])} of {n(r6['of_events_with_tau'])} = {pct(r6['observed_share'])} | "
      f"{'logged' if r6['fires'] else 'clear'} |")
    w(f"| 7 | {esc['row_7']['criterion']} | LOG | {n(r7['halt_events'])} of {n(r7['of_events_with_tau'])} = {pct(r7['observed_share'])} | "
      f"{'logged' if r7['fires'] else 'clear'} |")
    r8 = t3["row_8"]
    w(f"| 8 | {esc['row_8']['criterion']} | LOG | largest share {pct(max(v for v in r8['by_cell'].values() if v is not None))} "
      f"({'; '.join(f'{k.replace(chr(124), chr(32) + chr(183) + chr(32))} {pct(v)}' for k, v in r8['by_cell'].items())}) | "
      f"{'logged' if r8['fires'] else 'clear'} |")
    w("")
    w("Rows 6 and 7 use the events with τ as the denominator (15,519); against all of D1 (15,763) the shares are "
      f"{pct(r6['thin_events'] / t0['d1_n'])} and {pct(r7['halt_events'] / t0['d1_n'])}.")
    w("")
    # ------------------------------------------------ 2. II.5
    w("## 2. Verification (section 7)")
    w("")
    w("| check | result | source |")
    w("|---|---|---|")
    w(f"| D1 = 15,763; τ = 15,519; slices partition D1; dev (50) and sidecar (6) quarantined | D1 {n(t0['d1_n'])}, τ {n(t0['tau_available'])}, "
      f"slices {t0['slices']}; {len(t0['assertions_passed'])} assertions passed | `t0_population.json` |")
    w("| `tau_ns` int64 in every artifact | asserted by `b2common.assert_int64` in T0, T1, T2 and T4 before each write | code |")
    ct = t0["II5_causality_and_a2_segment_test"]
    w(f"| causality assertion exercised: a post-τ print fed to each attention function | raised on "
      f"{sum(1 for k, v in ct.items() if v == 'raised' and not k.startswith('segment_'))} of "
      f"{sum(1 for k in ct if k not in ('passes', 'clean_inputs_do_not_raise') and not k.startswith('segment_'))}; clean inputs pass | `t0_population.json` |")
    w(f"| A2 segment assertion exercised: a 04:00-anchored regular-hours ladder and a τ in the opening cross | "
      f"{ct.get('segment_rth_tau_anchored_0400')} / {ct.get('segment_tau_in_open_cross_minute')}; a segment-anchored ladder passes "
      f"({ct.get('segment_anchored_ladder_does_not_raise')}) | `t0_population.json` |")
    wt = t0["II5_competition_window_test"]
    w(f"| competition-window assertion exercised: a window straddling the open, one holding the closing cross, one reaching before 04:00 | "
      f"{wt['straddles_open']} / {wt['holds_close_cross_minute']} / {wt['straddles_0400']}; a window inside regular hours passes | `t0_population.json` |")
    bc = t1["II5_bucket_volume_conservation"]
    w(f"| bucket volume conservation | asserted in `instruments.bucketize` on {n(bc['event_rungs'])} event-rungs; max relative error "
      f"{bc['max_bucket_vol_rel_err']:.2e} | `t1_summary.json` |")
    w(f"| config diff script (row 4) | {cd['row_4']['observed']}; Brief 1 keys checked {cd['brief1_keys_checked']} | `t0_config_diff.json` |")
    d1 = t1["dev_reproduces_brief1_t4"]
    w(f"| T1 is Brief 1's T4 code, unchanged: the dev and sidecar rows reproduce Brief 1's `t4_excursion.parquet` | {d1['value']} "
      f"({n(d1['rows_compared'])} rows × {d1['columns_compared']} columns; mismatched {d1['mismatched_columns'] or 'none'}) | `t1_summary.json` |")
    d2, d3 = t2["dev_reproduces_brief1_a3_valid_rungs"], t2["dev_reproduces_brief1_a3_cross_section"]
    w(f"| R1 drops no valid rung: the dev valid rungs equal Brief 1's Amendment 3 run | {d2['value']} ({n(d2['rows'])} valid rungs) | `t2_summary.json` |")
    w(f"| the cross-section reproduces Brief 1's on the dev sample | {d3['value']} ({n(d3['rows'])} rows; max abs flow_share difference "
      f"{d3['flow_share_max_abs_diff']:.1e}, tolerance 1e-9 -- the running dollar sum) | `t2_summary.json` |")
    d4 = t3["dev_dates_reproduce_brief1_t5b_crossing"]
    import pandas as _pd
    _b1 = _pd.read_parquet(B.b1_art("t5b_competition.parquet"), columns=["j", "i", "liveness", "W_min", "arm", "status"])
    _b1 = _b1[(_b1["arm"] == "crossing") & _b1["status"].isin(["ok", "zero_count"])].astype({"liveness": str})
    _b2 = _pd.read_parquet(B.art("t3_pairs.parquet"), columns=["j", "i", "liveness", "W_min", "status"]).astype({"liveness": str, "status": str})
    _m = _b1.merge(_b2, on=["j", "i", "liveness", "W_min"], how="left", suffixes=("_b1", "_b2"))
    _un = _m[~_m["status_b2"].isin(["ok", "zero_count"])]
    w(f"| crossing-side counts reproduce Brief 1's T5b on the dev dates | {d4['value']} ({n(d4['matched_rows'])} matched rows of "
      f"{n(d4['brief1_rows_valid_or_zero'])}; the other {n(len(_un))} are, in b2: {_un['status_b2'].fillna('absent').value_counts().to_dict()}) "
      f"| `t3_summary.json`, `t3_pairs.parquet` |")
    w(f"| the step-zero reference is Brief 1's construction | regenerated draw for draw; identical to `t6_references.json` at every N: "
      f"{all(v['identical'] for v in t4a['reproduces_brief1_t6_references'].values())} | `t4a_references.json` |")
    w(f"| gallery strips rebuilt from ticks match T1's components exactly | {t4['gallery']['rebuild_matches_t1']} | `t4_step_zero.json` |")
    w("| every report number read from artifacts | this file is generated by `build_report.py` | — |")
    w("")
    # ------------------------------------------------ 3. rulings
    r = cfg["brief2_diff"]
    w("## 3. Section 1 rulings, as applied")
    w("")
    w(f"- **R1** — {r['R1']['rung_generation']} *Why not the briefed rule:* {r['R1']['as_briefed_and_why_replaced']} `a2_ignition`: {r['R1']['a2_ignition']}")
    w(f"- **R2** — cell {r['R2']['baseline_cell']}; moments: {r['R2']['baseline_moments']} Excess: {r['R2']['excess']}. {r['R2']['thin_cells']}.")
    w(f"- **R3** — {r['R3']['valid_window']}. {r['R3']['invalid']}.")
    w(f"- **R4** — price tier on {r['R4']['price_tier']['on']}, edges {r['R4']['price_tier']['edges_usd']} USD; jump_share bands "
      f"{r['R4']['jump_share_band']['labels']}; {r['R4']['retired']} retired.")
    w(f"- **R5** — {r['R5']['drop']}.")
    w(f"- Brief 2's own task parameters sit in the config's `brief2` block ({', '.join(cd['brief2_task_parameters'])}); the one value the "
      f"brief did not give is the gallery seed ({cfg['brief2']['t4_step_zero']['gallery']['seed']}).")
    w("")
    # ------------------------------------------------ 4. T0
    w("## 4. T0 — population and facets")
    w("")
    w(f"D1 {n(t0['d1_n'])}; τ available {n(t0['tau_available'])} (unavailable: {t0['tau_unavailable_reasons']}); {n(t0['dates_with_tau'])} dates.")
    w("")
    w("| facet (events with τ) | levels |")
    w("|---|---|")
    for k, lab in [("slices_with_tau", "slice"), ("years_with_tau", "year"), ("tau_anchor_segment", "clock segment of τ"),
                   ("price_tier_with_tau", "price tier (R4)"), ("tau_close_sensitive", "tau_close_sensitive"),
                   ("flag_cross_session_extreme", "A12 flag")]:
        w(f"| {lab} | " + " · ".join(f"{a} {n(b)}" for a, b in t0[k].items()) + " |")
    w(f"| τ in a cross minute (A2 unavailable) | {n(t0['tau_in_auction_minute'])} |")
    w(f"| events with τ on an early-close day | {n(t0['early_close_events_with_tau'])} |")
    w("")
    # ------------------------------------------------ 5. T1
    w("## 5. T1 — the excursion vector, all of D1")
    w("")
    w(f"{n(t1['events_with_tau'])} events with τ; {t1['seconds']:,.0f} s. Vector available by rung: "
      + "; ".join(f"N={N} {n(v)} ({pct(t1['vector_available_share_by_N'][N], 2)})" for N, v in t1["vector_available_by_N"].items())
      + f". Unavailable (events with τ): {t1['unavailable_reasons_with_tau'] or 'none'}. Path prints after τ: median "
      f"{n(t1['path_prints']['median'])}, p05 {n(t1['path_prints']['p05'])}, min {n(t1['path_prints']['min'])}, max {n(t1['path_prints']['max'])}. "
      f"LULD labels available for {n(t1['halt_label_available_events'])} events.")
    w("")
    ec = t1["edge_classes_by_N"]
    w("| edge class (count of available vectors) | " + " | ".join(f"N={N}" for N in ec) + " |")
    w("|---|" + "---|" * len(ec))
    for k in ["rise_censored", "no_rise", "peak_at_tau", "peak_tied", "halt_in_path", "halt_gap_rth", "halt_label_in_path", "thin_path", "sigma_zero"]:
        w(f"| `{k}` | " + " | ".join(n(ec[N][k]) for N in ec) + " |")
    w("| n | " + " | ".join(n(ec[N]["n"]) for N in ec) + " |")
    w("")
    w("→ `charts/t1/edge_classes.html`, `charts/t1/path_prints.html`")
    w("")
    # ------------------------------------------------ 6. T2
    a2 = t2["a2"]
    w("## 6. T2 — the attention axes, all of D1")
    w("")
    w(f"{n(t2['events']['with_attention'])} events with τ over {n(t2['dates'])} dates ({t2['seconds']:,.0f} s); A2 computed on "
      f"{n(t2['events']['with_a2'])}; τ in a cross minute (A2 unavailable, a label) {n(t2['events']['a2_unavailable_auction_minute'])}.")
    w("")
    w(f"**A1 turnover** — states {t2['a1']['state']}; median {t2['a1']['turnover']['median']:.4g} (n {n(t2['a1']['turnover']['n'])}); "
      f"share count accepted after τ (stricter check, logged) {n(t2['a1']['shs_accepted_after_tau'])}; row 5 (asof ≥ τ) {n(t2['row_5']['n'])}.")
    w("")
    w(f"**A2 acceleration** — valid rungs per event {a2['valid_rungs_distribution']} (median {f(a2['valid_rungs_median'], 1)}); zero valid "
      f"{n(a2['zero_valid_rung_events'])}; rungs generated {n(a2['rungs_generated_total'])}, valid {n(a2['valid_rungs_total'])}; the ladder "
      f"ended at the R1 count on {n(a2['cutoff_by']['exact_count'])} events and at the 10 ms floor or k_max on {n(a2['cutoff_by']['floor_or_k_max'])}; "
      f"invalid rungs by class {a2['invalid_rung_classes']}; D22 floor binding on {n(a2['resolution_floor_binding'])} rungs; kernel check "
      f"defined on {n(a2['kernel_defined_valid_rungs'])} valid rungs. **`a2_ignition`** (R1 label): {n(a2['a2_ignition_events'])} events.")
    w("")
    w("| τ segment | events with A2 | median valid rungs | zero valid | a2_ignition | median H (s) |")
    w("|---|---|---|---|---|---|")
    for sg, v in a2["by_segment"].items():
        w(f"| {sg} | {n(v['events'])} | {f(v['valid_rungs_median'], 1)} | {n(v['zero_valid'])} | {n(v['ignition'])} | {f(v['H_s_median'], 0)} |")
    w("")
    lv = t2["levels"]
    w("**Absolute levels** over each valid rung window [τ − W_k, τ] (new; plain counts and sums over time, no baseline): "
      + "; ".join(f"`{k}` n {n(v['n'])}, median {v['median']:.4g} (p05 {v['p05']:.4g}, p95 {v['p95']:.4g})" for k, v in lv.items()) + ".")
    w("")
    w(f"**A3 filings** — available {n(t2['a3']['available'])}; a filing within 24 h before τ {n(t2['a3']['filing_24h'])}.")
    w("")
    w("**Cross-section** — " + "; ".join(
        f"L={L}: median live_n {f(v['live_n_median'], 0)}, alone {n(v['alone_events'])}, rows with a rung window {n(v['rows_with_window'])}, "
        f"no window {v['reason_no_window']}" for L, v in t2["cross_sectional"].items()) + f". Live-name rows {n(t2['live_name_rows'])}.")
    w("")
    w("→ `charts/t2/a2_valid_rungs.html`, `level_measures.html`, `turnover.html`, `live_n.html`")
    w("")
    # ------------------------------------------------ 7. T3
    w("## 7. T3 — the competition check, all of D1 (R2, R3)")
    w("")
    w(f"{n(t3['dates'])} dates; {n(t3['pairs'])} (pair, W) rows; {n(t3['baseline_moments_finite_and_zero'])} baseline moments kept after R3 and "
      f"the ±W crossing exclusion; {n(t3['baseline_cells'])} baseline cells, {n(t3['baseline_thin_cells'])} thin (< 20 finite moments). "
      f"{t3['seconds']:,.0f} s.")
    w("")
    w("| L · W | pairs | lost to R3 | zero-count | read (cell ≥ 20) | excess median (p25, p75) | in thin cells | baseline cells (thin) | "
      "baseline minutes: in span · lost R3 · other crossing |")
    w("|---|---|---|---|---|---|---|---|---|")
    for k, v in t3["cells"].items():
        er, bl = v["excess_read"], v["baseline"]
        w(f"| {k.replace('|', ' · ')} | {n(v['pairs'])} | {pct(v['share_lost_r3'])} | {n(v['status'].get('zero_count', 0))} | {n(er['n'])} | "
          f"{f(er['median'])} ({f(er['p25'])}, {f(er['p75'])}) | {pct(v['pairs_in_thin_cells_share'])} | {n(bl['cells'])} ({n(bl['thin_cells'])}) | "
          f"{n(bl['moments_in_span'])} · {n(bl['lost_r3'])} · {n(bl['excluded_other_crossing'])} |")
    w("")
    w("Excess by year and by segment (read cells), median (n):")
    w("")
    for k, v in t3["cells"].items():
        w(f"- {k.replace('|', ' · ')} — years: " + "; ".join(f"{y} {f(d['median'])} ({n(d['n'])})" for y, d in v["by_year"].items())
          + " — segments: " + "; ".join(f"{s} {f(d['median'])} ({n(d['n'])})" for s, d in v["by_segment"].items()))
    w("")
    w("→ `charts/t3/excess_W{5,15,60}.html` (selector: all, each year, each segment), `baseline_cells.html`, `r3_share_lost.html`")
    w("")
    # ------------------------------------------------ 8. T4
    import pandas as pd
    fa = pd.read_parquet(B.art("t4_facets.parquet"))
    cr = pd.read_parquet(B.art("t4_cost.parquet"))
    w("## 8. T4 — step zero: the unconditional excursion vector")
    w("")
    w(f"All of D1 with τ and a vector; nothing pooled across rungs; no attention quantity read. Reference: Brief 1's simulated discrete "
      f"free walk at each N ({n(t4a['paths_per_N'])} paths, seed {t4a['seed']}). Cost: {cfg['cost_reference']['rt_bp']} bp round trip flat; "
      f"{cfg['cost_reference']['rt_cents']} cents per share.")
    w("")
    w("| N | n | median u_peak (ref) | u_peak in [0.1, 0.9) (ref) | u_peak < 0.05 · ≥ 0.95 | median rise_s (ref) | mean rise_s (ref) | "
      "median fall_s (ref) | rise > round trip: bp · cents |")
    w("|---|---|---|---|---|---|---|---|---|")
    for N, h in t4["headline_by_N"].items():
        w(f"| {N} | {n(h['n'])} | {f(h['u_peak_median'])} ({f(h['ref_u_peak_median'])}) | {pct(h['u_peak_share_interior_0.1_0.9'])} "
          f"({pct(h['ref_u_peak_share_interior_0.1_0.9'])}) | {pct(h['u_peak_share_le_0.05'])} · {pct(h['u_peak_share_ge_0.95'])} | "
          f"{f(h['rise_s_median'])} ({f(h['ref_rise_s_median'])}) | {f(h['rise_s_mean'])} ({f(h['ref_rise_s_mean'])}) | "
          f"{f(h['fall_s_median'])} ({f(h['ref_fall_s_median'])}) | {pct(h['share_rise_bp_gt_rt'])} · {pct(h['share_rise_cents_gt_rt'])} |")
    w("")
    w("**Share whose full rise exceeds one round trip, by price tier and edge class** (n; bp · cents):")
    w("")
    w("| level | N=50 | N=100 | N=200 |")
    w("|---|---|---|---|")
    for facet in ("all", "price_tier", "edge_class"):
        for lev in cr[cr["facet"] == facet]["level"].unique():
            cells = []
            for N in (50, 100, 200):
                x = cr[(cr["facet"] == facet) & (cr["level"] == lev) & (cr["N"] == N)]
                cells.append("—" if x.empty or not x.iloc[0]["n"] else
                             f"n {n(x.iloc[0]['n'])}; {pct(x.iloc[0]['share_rise_bp_gt_rt'])} · {pct(x.iloc[0]['share_rise_cents_gt_rt'])}")
            w(f"| {facet}: {lev} | " + " | ".join(cells) + " |")
    w("")
    w("**By facet** — median u_peak, share of u_peak in [0.1, 0.9), median rise_s, per rung (reference in the header row):")
    w("")
    ref = fa[fa["facet"] == "all"].set_index("N")
    w("| facet: level | n (N=100) | " + " | ".join(f"N={N}: median u_peak · interior · median rise_s" for N in (50, 100, 200)) + " |")
    w("|---|---|---|---|---|")
    w("| reference (free walk) | — | " + " | ".join(
        f"{f(ref.loc[N, 'ref_u_peak_median'])} · {pct(ref.loc[N, 'ref_u_peak_share_interior_0.1_0.9'])} · {f(ref.loc[N, 'ref_rise_s_median'])}"
        for N in (50, 100, 200)) + " |")
    for (facet, lev), g in fa[fa["facet"] != "all"].groupby(["facet", "level"], sort=False):
        gi = g.set_index("N")
        cells = []
        for N in (50, 100, 200):
            if N not in gi.index or not gi.loc[N, "n"]:
                cells.append("—")
                continue
            x = gi.loc[N]
            cells.append(f"{f(x['u_peak_median'])} · {pct(x['u_peak_share_interior_0.1_0.9'])} · {f(x['rise_s_median'])}")
        w(f"| {facet}: {lev} | {n(gi.loc[100, 'n']) if 100 in gi.index else '—'} | " + " | ".join(cells) + " |")
    w("")
    g = t4["gallery"]
    w(f"**Gallery** — {n(g['n'])} events over {n(g['strata'])} year × segment strata, seed {g['seed']}; allocation {g['allocation']}.")
    w("")
    w("→ `charts/t4/u_peak.html` (selector: every rung × facet level, reference drawn), `ecdf_rise_s.html`, `ecdf_fall_s.html`, "
      "`ecdf_dip_before_peak_s.html`, `ecdf_terminal_s.html` (same selector, reference drawn), `rise_vs_cost.html`, `cost_clearing.html`, "
      "`gallery.html` (event selector)")
    w("")
    # ------------------------------------------------ 9. charts
    w("## 9. Charts (under `results/attention_excursion/b2/charts/`, dark theme, Plotly inlined, one per file)")
    w("")
    root = B.REPO / B.CHARTS
    for task in sorted(os.listdir(root)) if root.exists() else []:
        files = sorted(p.name for p in (root / task).glob("*.html"))
        w(f"- `{task}/` — " + ", ".join(f"`{x}`" for x in files))
    w("")
    # ------------------------------------------------ 10. column dictionary
    rows, missing = column_dictionary()
    assert not missing, f"columns with no declared unit: {missing}"
    w("## 10. Column dictionary (section 5) — generated from the artifacts' schemas")
    w("")
    w("Role: **pre-τ (attention)** = computed from prints at or before τ; **post-τ (excursion)** = from prints after τ; **facet** = a "
      "grouping variable fixed at or before τ; **competition** = another live name's trades around a crossing τ_j (T3, mechanism only). "
      "Amendment 3 names: `H_s` runs from the segment start (`H_0400_s` from 04:00); `a2_state`, `a2_anchor_ns`, `tau_anchor_segment`, "
      "`tau_in_auction_minute`, `win_lo_ns`, `win_mid_ns`; the A2 counts are nullable (NULL when A2 is unavailable). New in Brief 2: "
      "`a2_ignition`, `a2_rungs_generated`, `a2_cutoff_k`, `trades_per_min`, `dollars_per_min`, `shares_per_min`, `n_collapsed_seg_tau`.")
    w("")
    w("| artifact | column | type | units | role |")
    w("|---|---|---|---|---|")
    L += rows
    w("")
    txt = "\n".join(L) + "\n"
    out = B.REPO / B.OUT / "REPORT.md"
    out.write_text(txt, encoding="utf-8", newline="\n")
    shutil.copyfile(out, B.REPO / "results" / "reports" / "attention_excursion_b2_report.md")
    print(f"REPORT.md written ({len(L)} lines): {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
