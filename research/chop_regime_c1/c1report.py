"""
Chop regime C1 -- REPORT.md (T9), generated from the artifacts: every number is read by code. Describes; interprets
nothing; no outcome is summarised (the outcome panels are in the suite).

Amendment 1 run: T0, the T5 re-run, T6, T6b, T7, T8. The first T5 run's numbers quoted in the A1.0 cause list are read
from that run's own artifacts at commit 1be4f65 through git (they were replaced in the tree by the re-run).

Writes results/chop_regime/c1/REPORT.md and its copy results/reports/chop_regime_c1_report.md.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/c1report.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402

FIRST = "1be4f65"


def f(x, d=3):
    if x is None:
        return "—"
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x))
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    x = float(x)
    if np.isnan(x):
        return "—"
    if np.isinf(x):
        return "inf" if x > 0 else "-inf"
    ax = abs(x)
    if ax != 0 and (ax >= 1e6 or ax < 1e-3):
        return f"{x:.3g}"
    return f"{x:,.{d}f}"


def git_bytes(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, cwd=C.REPO, check=True).stdout


HINDSIGHT = tuple(f"{h}_" for h in C.HORIZONS) + ("g3_fwd_max_px", "rem_type", "rem_state_s2")
DICT = [  # (prefix or name, units, meaning, panel)
    ("event_id", "", "event key (folder name)", "all"), ("j", "", "grid index (0..60 every minute, then every 5 min)", "all"),
    ("t_ns", "ns", "moment time, int64", "G"), ("weight", "minutes", "moment-minutes the moment stands for", "all"), ("minutes_since_tau", "min", "t - tau", "E"),
    ("segment", "", "t's clock segment", "all"), ("in_auction_minute", "", "t in an auction minute (no measures)", "header"),
    ("no_print_since_last_moment", "", "no print in (previous moment, t]", "flags"), ("tcs_state", "", "S2 R1 causal tau_close_sensitive at t", "facet"),
    ("halt_state", "", "label / gap_proxy (>= 300 s regular hours) / none", "flags"), ("shares_0400_t", "shares", "shares traded 04:00 -> t", "—"),
    ("turnover_t", "fraction", "shares 04:00 -> t / S2's tau-anchored share count (lower bound; D41)", "G2"),
    ("quote_at_t", "", "a D17-valid D16 quote prevails at t", "flags"), ("bid_t", "$", "D16 bid at t", "G3"), ("ask_t", "$", "D16 ask at t", "G3"), ("mid_t", "$", "D16 midpoint at t", "—"),
    ("spread_bp_t", "bp", "ask - bid over the midpoint, at t", "B, C (net)"), ("spread_c_t", "cents", "ask - bid, at t", "B, C (net)"),
    ("quote_age_s", "s", "time since the best bid or ask price changed", "B"), ("depth_ask_usd", "$", "displayed ask size x ask (shares, T0 census)", "B"),
    ("depth_bid_usd", "$", "displayed bid size x bid", "—"), ("measure_state", "", "ok / auction_minute / at_segment_start", "flags"), ("H_min", "min", "t - segment start", "—"),
    ("n_rate_rungs_valid", "", "valid rungs of the rate ladder", "—"), ("rate_rung0", "trades/min", "collapsed trade rate over rung 0", "—"),
    ("finest_rate_rung", "", "smallest valid window of the rate ladder", "—"), ("trade_rate", "trades/min", "collapsed trades / min, finest rate rung", "B"),
    ("raw_rate", "prints/min", "raw prints / min, finest rate rung", "—"), ("dollar_flow", "$/min", "dollar volume / min, finest rate rung", "B, G2"),
    ("turnover_rate", "1/min", "shares / share count / min, finest rate rung (D41)", "B"), ("n_eff", "orders", "1 / sum of squared order shares, finest rate rung", "B, G1"),
    ("top3_share", "fraction", "volume share of the 3 largest collapsed orders, finest rate rung", "B, G1"), ("move_per_trade", "bp/trade", "abs log move / collapsed trades, finest rate rung", "B"),
    ("n_orders", "orders", "collapsed orders in the finest rate window", "—"), ("spread_tw_bp", "bp", "time-weighted quoted spread over the finest rate rung", "—"),
    ("spread_tw_c", "cents", "the same in cents", "—"), ("spread_tw_cover", "fraction", "share of that window under a valid quote", "—"),
    ("act_ratio", "ratio", "finest-rate-rung trade rate / rung-0 rate", "override"), ("n_valid_rungs", "", "valid scale-free rungs (>= 64 collapsed trades)", "—"),
    ("n_valid_rungs_k1", "", "valid scale-free rungs with k >= 1", "—"), ("scale_free_cutoff_k", "", "first rung below the 64-trade stop", "—"),
    ("finest_rung", "", "smallest valid scale-free window", "—"), ("finest_mid_ok", "", "the finest rung has a midpoint path", "—"),
    ("price_basis", "", "mid / vwap_fallback at the finest rung (A1.2)", "flags"), ("context_basis", "", "mid / vwap_fallback for rung-0 context", "flags"),
    ("er_allmax", "0-1", "largest er over valid rungs k >= 1 (the 'every valid rung' option)", "B (reference)"),
    ("er0", "0-1", "closed-form er reference at the finest rung (a column, not a condition; A1.3)", "—"), ("er_rel", "ratio", "er / er0 (a column, not a condition)", "—"),
    ("er", "0-1", "efficiency ratio at the finest rung, primary price (A1.2)", "B (reference)"),
    ("sigma_", "log units", "own noise over horizon h from the finest rung's bucket returns", "G3 (w60)"),
    ("cost_noise_", "ratio", "spread_bp_t / own noise over h (1e4 sigma_h)", "B"),
    ("leg_state", "", "leg / no_leg / no_path (rung 0)", "—"), ("leg_s", "noise units", "largest rise low -> later high over the noise of the returns it spans", "override, G3"),
    ("leg_bp", "bp", "the same rise in bp", "—"), ("leg_c", "cents", "the same rise in cents", "—"), ("leg_low_px", "$", "leg low (bucket price)", "G"),
    ("leg_high_px", "$", "leg high (bucket price)", "G, G3"), ("leg_low_ns", "ns", "time of the leg low's bucket", "G"), ("leg_high_ns", "ns", "time of the leg high's bucket", "G"),
    ("since_high_min", "min", "minutes since the leg high", "—"), ("since_high_vol", "fraction", "share of rung-0 volume since the leg high", "—"),
    ("giveback", "ratio", "log(high / price at t) / log(high / low)", "override, G3"),
    ("g3_fwd_max_px", "$", "highest non-spike print in (t, t + 60 min] (HINDSIGHT)", "G3 only"), ("rem_type", "", "S2's remaining-path type at j = 0,1,2,5,10,20 (HINDSIGHT)", "D"),
    ("rem_state_s2", "", "S2's state for that label (HINDSIGHT)", "—"),
    ("ticker", "", "event ticker", "G"), ("year", "", "event year", "facet"), ("event_date_canonical", "", "event date", "G"), ("tau_segment", "", "tau's segment", "sample strata"),
    ("price_tier", "", "price tier at tau (S1)", "facet, cells"), ("dilution", "", "S2 dilution flag at tau (D41)", "facet"), ("quotes_ingested", "", "D15 coverage", "facet"),
    ("quotes_event_day", "", "an event-day quote session in the D15 source", "—"), ("shs_quality", "", "F1's share-count quality (at F1's t0)", "—"),
    ("event_index", "", "S1 event index (seeds)", "—"), ("v_pre", "shares", "shares from tau's segment start to tau (S2 ref_shares)", "volume horizons"),
    ("tau_price", "$", "the crossing print's price", "—"), ("moment_uid", "", "event_index x 512 + j", "keys"), ("dev_slice", "", "TRUE for every row (asserted)", "row 9"),
]
HIND = {"_state": ("", "ok / no_print_in_h / v_pre_undefined / auction_moment"), "_censored": ("", "window cut at 20:00 or the segment end"),
        "_entry_px": ("$", "first non-spike print after t"), "_entry_ns": ("ns", "its time"), "_ret_bp": ("bp", "last non-spike print <= end vs entry, gross"),
        "_ret_c": ("cents", "the same in cents"), "_mfe_bp": ("bp", "highest non-spike print in (t, end] vs entry"), "_mfe_c": ("cents", "the same in cents"),
        "_mae_bp": ("bp", "lowest non-spike print in (t, end] vs entry"), "_mae_c": ("cents", "the same in cents")}


def describe(col: str, dtype: str) -> tuple:
    hs = col.startswith(HINDSIGHT)
    if col.startswith(tuple(f"{h}_" for h in C.HORIZONS)):
        h, rest = col.split("_", 1)
        u, mtxt = HIND.get("_" + rest, ("", ""))
        return col, dtype, u, "hindsight", f"{mtxt} (horizon {h})", "C, D" if rest in ("ret_bp", "mfe_bp", "state", "entry_px") else "—"
    base = col
    for suf in ("_mid", "_vwap"):
        if col.endswith(suf) and not col.startswith(("mid_",)):
            base = col[: -len(suf)]
    best = None
    for name, u, mtxt, panel in DICT:
        if base == name or (name.endswith("_") and base.startswith(name)):
            best = (u, mtxt, panel)
            break
    if best is None:
        best = ("", "(not described)", "—")
    u, mtxt, panel = best
    if base != col:
        mtxt += f" -- {col.rsplit('_', 1)[1]} price"
        panel = "check column" if col.endswith("_vwap") else panel
    return col, dtype, u, "hindsight" if hs else "causal / identifier", mtxt, panel


def main() -> int:
    cfg = C.load_cfg()
    t0, t5, t6, t6b, t7, t8 = (C.read_json(x) for x in ("t0_summary.json", "t5_summary.json", "t6_summary.json", "t6b_summary.json", "t7_summary.json", "t8_summary.json"))
    test = C.read_json("t8_page_test.json") if C.art("t8_page_test.json").exists() else None
    t5a = C.read_json("t5a_summary.json")
    first = json.loads(git_bytes(FIRST, "results/chop_regime/c1/artifacts/t5_summary.json"))
    fw = pd.read_parquet(io.BytesIO(git_bytes(FIRST, "results/chop_regime/c1/artifacts/t5_windows.parquet")), columns=["basis", "vz2"])
    cells = pd.read_parquet(C.art("t5_cells.parquet"))
    bands = pd.read_parquet(C.art("t6b_null_bands.parquet"))
    Q = pd.read_parquet(C.art("t6_measure_quantiles.parquet"))
    man = C.read_json("t6_manifest.json")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    freeze = subprocess.run(["git", "log", "--format=%h", "-1", "--grep=T0 freeze"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    pop, tim, cen = t0["population"], t0["timing"], t0["quote_size_census"]
    esc = t5["escalation"]
    L = []
    a = L.append
    a("# Chop regime filter — C1: the measures and the tuning suite")
    a("")
    a(f"**Generated by** `research/chop_regime_c1/c1report.py` from `results/chop_regime/c1/artifacts/` at `HEAD {head}`; every number below is read from an artifact. "
      f"**Config** `config/chop_regime_c1.json`, hash `{C.cfg_hash()}` (its `amendment_1` block holds Amendment 1). **Briefs** `prompts/chop_regime_c1.md`, "
      f"`prompts/chop_regime_c1_amendment_1.md` and `prompts/chop_regime_c1_amendment_2.md`. **Branch** `explore/chop-regime-c1` (cut from `explore/shape-classifier-s2` at `e71b68a`).")
    a("")
    a(f"**Status: complete to T9, stopped with the suite in Cooper's hands.** The suite is `results/chop_regime/c1/suite/chop_suite.html` "
      f"({f(t8['bytes'] / 1e6, 1)} MB). The first T5 run stopped on escalation row 3 (commit `{FIRST}`). Amendment 1 re-specified the controls and split row 3. "
      "No HARD STOP fired on the re-run. Amendment 2 reads the positive control per rung, reinstates `er` as a condition, and rebuilt T8 only "
      f"(data hash unchanged, `{t8['data_hash']}`).")
    a("")
    # ------------------------------------------------------------ escalation
    a("## Escalation table (Amendment 1 A1.5)")
    a("")
    a("| row | criterion | tier | status | observed |")
    a("|---|---|---|---|---|")
    tests = t5["tests"]
    a(f"| 1 | any causality assertion fires | HARD STOP | clear | the causality test raises in every case ({tests['causality']['passes']}); no assertion fired in T0, T5, T6, T6b or T7 |")
    a(f"| 2 | any segment assertion fires | HARD STOP | clear | the segment test raises in every case ({tests['segment']['passes']}); no assertion fired in any build |")
    a(f"| 3a | a presence or cost measure fails blindness | HARD STOP | clear | presence / cost columns failing: {t5['blindness']['by_group']['presence_cost'] or 'none'} |")
    rem3b = esc["row3b_removed"]
    a(f"| 3b | a scale-free measure fails its positive or blindness control | LOG | **fired** on the per-cell reading | " + ("; ".join(f"`{k}`: {v}" for k, v in rem3b.items()) or "none")
      + (f". **Amendment 2:** {t8['er_note']}" if t8.get("er_note") else "") + " |")
    a(f"| 4 | quote-size units cannot be established for a year | LOG | clear | shares in {', '.join(y for y, v in cen.items() if v['unit'] == 'shares')} |")
    s7 = t7["sample"]
    a(f"| 5 | embedded sample below 50% of development-slice events | LOG | {'**fires**' if s7['row5_fires'] else 'clear'} | sample fraction {s7['fraction']}: "
      f"{f(s7['events_embedded'])} of {f(s7['events'])} events ({f(100 * s7['events_share'], 1)}%) |")
    r6 = t6["row6_no_scale_free_rung_share"]
    a(f"| 6 | no valid scale-free rung above 40% of moment-minutes in any segment | LOG | {'**fires**' if any(t6['row6_fires'].values()) else 'clear'} | "
      + ", ".join(f"{s} {f(100 * v, 1)}%" for s, v in r6.items()) + " |")
    a(f"| 7 | events with quotes unavailable | LOG | **fires** | {pop['development_quotes_ingested_false']} development-slice events with `quotes_ingested = FALSE` (D15), carried as their own facet value |")
    a(f"| 8 | A12 or a hindsight column reaches the suite's condition inputs | HARD STOP | clear | build assertions passed: {', '.join(t8['assertions'])} |")
    a("| 9 | any embedded row outside the development slice | HARD STOP | clear | asserted in `suite_table.build` (every row `dev_slice`, every event in the development slice) |")
    a(f"| 10 | extrapolated runtime above 6 hours | HARD STOP | clear | T0 extrapolated {f(tim['extrapolated_wall_hours'], 2)} h; the T6 build took {f(t6['build_seconds'] / 3600, 2)} h on {tim['workers']} workers |")
    a("")
    a(f"**D40 and D41** were appended to `docs/Universe-Decisions.md`, with the `CLAUDE.md` index (next free D42), in the T0 freeze commit `{freeze}`, before any run. "
      "D41 is Cooper's ruling at T0. It makes turnover (F1 denominator) and the dilution flag usable beside outcome panels as an exploratory, by-eye exception to D32, in the same shape as D39.")
    a("")
    # ------------------------------------------------------------ A1.0
    a("## What went wrong in the first T5 run (Amendment 1 A1.0)")
    a("")
    fb = first["table"]
    fz = fw.groupby("basis")["vz2"].agg(lambda s: (s.abs() > 10).mean())
    a(f"1. **The whole-pipeline null was mis-specified.** A shuffle keeps the window's sum, so every shuffled path is a bridge carrying the window's own net move. "
      f"`t5a_whole_pipeline_diagnosis.py` measured three constructions on the first run's windows (`charts/t5/03_whole_pipeline_constructions.html`). "
      f"The literal shuffle's ER statistic was {f(fb['whole_pipeline|mid']['all_rungs']['er_statistic_median'])} on the midpoint and "
      f"{f(fb['whole_pipeline|vwap']['all_rungs']['er_statistic_median'])} on VWAP.")
    a("2. **The stop rule was too broad.** Every failure was in a scale-free measure. Row 3 is now split (3a / 3b).")
    a(f"3. **The robust variance-ratio z is unstable on sparse returns.** On the first run's real windows, |vz2| > 10 in "
      f"{f(100 * fz['mid'], 2)}% of midpoint windows and {f(100 * fz['vwap'], 2)}% of VWAP windows. VWAP's vz2 median on the whole-pipeline null was "
      f"{f(fb['whole_pipeline|vwap']['all_rungs']['vz2_median'])} (the averaging bias). The variance ratio is dropped (A1.1). Before it was retired, the AR(1) positive control "
      f"read +{f(t5['ar1_retired_values']['mid'][0], 2)} / {f(t5['ar1_retired_values']['mid'][1], 2)} on the midpoint and +{f(t5['ar1_retired_values']['vwap'][0], 2)} / "
      f"{f(t5['ar1_retired_values']['vwap'][1], 2)} on VWAP ({t5['ar1_retired_values']['source']}).")
    a("")
    # ------------------------------------------------------------ T0
    a("## T0 — population, τ, quote sizes, timing")
    a("")
    a(f"- **τ:** {t0['tau_source']}.")
    a(f"- **Development slice:** {f(pop['slices_development'])} events; {f(pop['development_with_tau'])} with τ (b2: {f(pop['b2_development_tau_available'])}). Without τ: "
      + ", ".join(f"{k} {v}" for k, v in pop["development_without_tau"].items()) + ". By year: " + ", ".join(f"{k} {f(v)}" for k, v in pop["development_by_year"].items()) + ".")
    a(f"- **Quarantine:** {pop['slices_quarantine']} events, {pop['quarantine_with_tau']} with τ; the controls run on those {pop['quarantine_with_tau']}.")
    a(f"- **Carried gaps:** `V_pre` undefined for {pop['development_v_pre_undefined']} (τ in an auction minute; volume horizons undefined there); share count missing for "
      f"{f(pop['development_shares_outstanding_missing'])} (turnover unavailable).")
    a("- **Quote sizes are shares** in every year, by the config's declared rule:")
    a("")
    a("| year | events | D17-valid sizes | share multiple of 100 | at-touch trades | median trade / displayed | share trade ≤ displayed | unit |")
    a("|---|---|---|---|---|---|---|---|")
    for y, v in cen.items():
        a(f"| {y} | {v['events']} | {f(v['sizes'])} | {f(v['share_multiple_of_100'], 4)} | {f(v['at_touch_trades'])} | {f(v['median_trade_over_displayed'])} | "
          f"{f(v['share_trade_le_displayed'])} | {v['unit']} |")
    a("")
    # ------------------------------------------------------------ T5
    a("## T5 re-run — the Amendment 1 controls (53 quarantined events)")
    a("")
    a(f"Windows: midpoint {f(t5['windows_by_basis']['mid'])}, VWAP {f(t5['windows_by_basis']['vwap'])}; {t5['draws_per_window']} null draws each; {t5['cells']} cells "
      "(t's segment × rung × price tier × basis). Charts: `charts/t5/`.")
    a("")
    a("**Negative (the A1.3 null, reported, no band)** and **positive trend**, pooled per rung (`charts/t5/01_null_er_by_rung.html`):")
    a("")
    a("| basis | rung | windows | null median | null 5th | null 95th | real er median | null + d = 1 | d = 2 | d = 4 |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for r in t5["per_rung"]:
        a(f"| {r['basis']} | {r['k']} | {f(r['windows'])} | {f(r['null_median'])} | {f(r['null_p05'])} | {f(r['null_p95'])} | {f(r['real_er_median'])} | "
          f"{f(r['median_er_d1'])} | {f(r['median_er_d2'])} | {f(r['median_er_d4'])} |")
    a("")
    pt = t5["positive_trend"]
    a("**Positive trend, the gate** (per cell with ≥ 20 windows: median er at d = 4 above the cell's null 95th value; `charts/t5/02_positive_cells.html`):")
    a("")
    a("| basis | cells | gated (≥ 20 windows) | failing | pass |")
    a("|---|---|---|---|---|")
    for bs in ("mid", "vwap"):
        a(f"| {bs} | {pt[bs]['cells']} | {pt[bs]['cells_gated']} | {', '.join(pt[bs]['cells_failing']) or 'none'} | {pt[bs]['pass']} |")
    a("")
    fc = cells[cells["pass"] == False]  # noqa: E712
    if len(fc):
        a("Failing cells: " + "; ".join(f"`{r.cell}` ({r.windows} windows): median er at d = 4 {f(r.median_er_d4)}, null 95th {f(r.null_p95)}, null median {f(r.null_median)}"
                                         for r in fc.itertuples()) + ". er cannot exceed 1.")
        rr = pd.DataFrame(t5["per_rung"])
        rg = rr[rr["windows"] >= cfg["amendment_1"]["A1_3_null"]["min_windows_label"]]
        a("")
        a(f"Read per rung instead (pooled over segments and tiers, every rung with ≥ 20 windows), the d = 4 median exceeds the pooled null 95th value at "
          f"{int((rg['median_er_d4'] > rg['null_p95']).sum())} of {len(rg)} rung-bases. The config declared the per-cell reading before the run.")
    a("")
    a("**Row 3b (as run):** " + ("; ".join(f"`{k}` removed from the suite's conditions — {v}" for k, v in rem3b.items()) if rem3b else "nothing removed") + ".")
    if t8.get("er_note"):
        a2 = cfg["amendment_2"]
        a("")
        a(f"**Amendment 2 (2026-10-01):** {t8['er_note']}. The suite marks every cell whose null 95th value is ≥ {a2['A2_1_ceiling_label']['null_p95_at_least']} "
          f"\"{a2['A2_1_ceiling_label']['text']}\" ({t8['ceiling_cells']} of {len(bands)} development-slice cells), in panel B and in the `er` condition row. This is a label, not a rule. "
          f"The `er` bucket-dependence label carries the line: \"{a2['A2_2_bucket_line']}\" Panel A shows per-segment counts first and the pooled total last.")
    a("")
    bl = t5["blindness"]
    a(f"**Blindness:** rule `{bl['rule'].split('. Set')[0]}`. Columns failing: {list(bl['columns_failing']) or 'none'} (presence/cost {bl['by_group']['presence_cost'] or 'none'}, "
      f"scale-free {bl['by_group']['scale_free'] or 'none'}, relative/context {bl['by_group']['relative_context'] or 'none'}). Sub-$1 rounding is reported per event in "
      f"`t5_blindness.parquet` ({bl['events_with_sub_dollar_prints']} events have sub-$1 prints).")
    a("")
    a("**Sweep** (16 / 32 / 64 buckets; `charts/t5/04_sweep.html`):")
    a("")
    a("| measure | 16 | 32 | 64 | relative change 16 / 64 | bucket-dependent |")
    a("|---|---|---|---|---|---|")
    for k, v in t5["sweep"].items():
        a(f"| {k} | {f(v['16'])} | {f(v['32'])} | {f(v['64'])} | {f(v['rel_change_16'])} / {f(v['rel_change_64'])} | {'**yes**' if v['bucket_dependent'] else 'no'} |")
    a("")
    a(f"**Tests:** causality {tests['causality']['passes']}, segment {tests['segment']['passes']}, bucket equality against Brief 1's `bucketize` {tests['bucket_equality']['passes']} "
      f"(max relative VWAP difference {f(tests['bucket_equality']['max_rel_vwap_diff'])}). Price-basis agreement on the 53 events: `t5_basis_agreement.parquet`.")
    a("")
    # ------------------------------------------------------------ T6
    a("## T6 — the full build (development slice)")
    a("")
    a(f"{f(t6['events'])} events, {f(t6['moments'])} moments, {f(t6['moment_minutes'])} moment-minutes, from {f(t6['prints'])} prints and {f(t6['quotes'])} quotes "
      f"({f(t6['spike_prints'])} spike prints skipped by the hindsight columns). The weights reconcile to the minutes covered in every event (asserted). Build {f(t6['build_seconds'] / 60, 1)} min. "
      f"`rem_type` {t6['rem_type_moments']}. Charts: `charts/t6/01_coverage.html`, `charts/t6/02_rung_availability.html`.")
    a("")
    a("| segment of t | moments | moment-minutes | events | no valid scale-free rung | no valid rate rung | no quote at t | VWAP fallback |")
    a("|---|---|---|---|---|---|---|---|")
    for s, v in t6["per_segment"].items():
        a(f"| {s} | {f(v['moments'])} | {f(v['moment_minutes'])} | {f(v['events'])} | {f(v.get('no_scale_free_rung_share'))} | {f(v.get('no_rate_rung_share'))} | "
          f"{f(v.get('no_quote_at_t_share'))} | {f(v.get('vwap_fallback_share'))} |")
    a("")
    a("**Distribution of every causal measure per segment** (weighted by moment-minutes; unavailable = NaN share, inf = a flat window's cost_noise; `t6_measure_quantiles.parquet`, "
      "`charts/t6/03_measure_distributions.html`):")
    a("")
    a("| measure | segment | unavailable | inf | 5th | 25th | median | 75th | 95th |")
    a("|---|---|---|---|---|---|---|---|---|")
    for r in Q.sort_values(["measure", "segment"]).itertuples():
        a(f"| {r.measure} | {r.segment} | {f(r.unavailable_share)} | {f(r.inf_share)} | {f(r.q05)} | {f(r.q25)} | {f(r.q50)} | {f(r.q75)} | {f(r.q95)} |")
    a("")
    a("Price-basis agreement on the development slice: `t6_basis_agreement.parquet`, `charts/t6/04_basis_agreement.html`.")
    a("")
    # ------------------------------------------------------------ T6b
    a("## T6b — the A1.3 null bands per cell (development slice)")
    a("")
    a(f"{f(t6b['windows'])} valid scale-free windows. Up to {t6b['cap']:,} seeded windows per cell, {t6b['draws_per_window']} draws each: {f(t6b['window_bases_sampled'])} window-bases "
      f"in {f(t6b['events_revisited'])} events, {t6b['cells']} cells, {t6b['cells_labelled_few_windows']} labelled with fewer than 20 sampled windows "
      "(`t6b_null_bands.parquet`, `charts/t6b/01_null_bands.html`). Midpoint cells at rungs 0, 2, 4 and 6:")
    a("")
    a("| segment | tier | rung | windows sampled | null median | null 5th | null 95th | real er median | real IQR |")
    a("|---|---|---|---|---|---|---|---|---|")
    for r in bands[(bands["basis"] == "mid") & bands["k"].isin([0, 2, 4, 6])].sort_values(["segment", "tier", "k"]).itertuples():
        a(f"| {r.segment} | {r.tier} | {r.k} | {f(r.windows_sampled)}{' (few)' if r.label_few_windows else ''} | {f(r.null_median)} | {f(r.null_p05)} | {f(r.null_p95)} | "
          f"{f(r.real_q50)} | {f(r.real_q25)}–{f(r.real_q75)} |")
    a("")
    # ------------------------------------------------------------ T7, T8
    a("## T7 — gallery flags, the embedded sample, the pools")
    a("")
    a(f"Flags on every development-slice moment (`t7_flags.parquet`): G1 {f(t7['flags']['g1'])} moments, G2 {f(t7['flags']['g2'])}. G3 uses hindsight and is shown only in the suite. "
      "These are gallery finders, not filters.")
    a("")
    a(f"**Embedded sample:** fraction {s7['fraction']}, {f(s7['events_embedded'])} of {f(s7['events'])} events ({f(100 * s7['events_share'], 1)}%), {f(s7['moments_embedded'])} of "
      f"{f(s7['moments'])} moments. Strata are year × τ's segment, seeded, whole events only, sized with the page's own encoder and the strips' worst case reserved. Pools: "
      + ", ".join(f"{k} {v['n']} (of {f(v['available'])} available)" if k != "G3" else f"G3 {v['n']}" for k, v in t7["pools"].items())
      + f"; {t7['strips']['n']} strips.")
    a("")
    a("## T8 — the suite")
    a("")
    a(f"`results/chop_regime/c1/suite/chop_suite.html` (rebuilt under Amendment 2; config `{t8['config_hash']}`): {f(t8['bytes'] / 1e6, 1)} MB ({f(t8['bytes'])} bytes), {f(t8['rows'])} non-auction moments of {f(t8['events'])} events, {t8['strips']} strips, "
      f"data hash `{t8['data_hash']}`. Build assertions: {', '.join(t8['assertions'])}. `cost_noise` at w15, w60, v05 and v1 is the embedded w5 / v025 value × √(h0/h), "
      f"exact within a ladder (asserted on {f(sum(t8['cost_noise_scaling_rows_checked'].values()))} values). The header carries the brief's text, the sample fraction, the "
      f"{'Amendment 2 reinstatement of er' if t8.get('er_note') else 'row 3b removal'} and the LOG rows.")
    if test:
        a("")
        a(f"**Page test** (`research/chop_regime_c1/t8_page_test.js` under node with a stub DOM and a recording Plotly stub, on the real embedded data): exit {test['exit']}. "
          f"{test['summary']}. The test's first run printed panel C's ticker-bootstrap line (an outcome reading for an arbitrary all-conditions-at-mid-slider "
          "setting) to the console; the test now records only that each computation completed, and no artifact holds that line.")
    a("")
    # ------------------------------------------------------------ dictionary
    a("## Column dictionary (generated from the T6 moment table)")
    a("")
    first_file = [k for k in man["files"] if k.startswith("t6_moments_")][0]
    cols = man["files"][first_file]["columns"]
    dt = pd.read_parquet(C.art(first_file)).dtypes if C.art(first_file).exists() else {}
    a("| column | type | units | causal / hindsight | meaning | used in |")
    a("|---|---|---|---|---|---|")
    for c in cols:
        r = describe(c, str(dt[c]) if c in dt else "")
        a("| " + " | ".join(str(x) for x in r) + " |")
    a("")
    a("Per-rung tables: `t6_sf_rungs_<year>` (scale-free rungs: er, er0, er_rel and sum r² on both prices, the primary `er`, `price_basis`) and `t6_rate_rungs_<year>` "
      "(rate rungs: validity class, half-window counts, the presence and relative measures). They are git-ignored and regenerable, with rows, columns and sha256 in `t6_manifest.json`:")
    a("")
    for k, v in man["files"].items():
        a(f"- `{k}`: {f(v['rows'])} rows, {f(v['bytes'] / 1e6, 1)} MB, sha256 `{v['sha256_16']}`")
    a("")
    a("## Files")
    a("")
    a("- Code: `research/chop_regime_c1/` — `c1common.py`, `measures.py`, `nulls.py`, `t0_population.py`, `t5_controls.py`, `t5a_whole_pipeline_diagnosis.py`, "
      "`t5b_blindness_detail.py` (first run), `t6_build.py`, `t6b_null_bands.py`, `t7_galleries.py`, `suitedata.py`, `suite_table.py`, `t8_suite.py`, `t8_page_test.js`, `c1charts.py`, "
      "`c1report.py`.")
    a("- Charts: `charts/t5/` (01–04), `charts/t6/` (01–04), `charts/t6b/01_null_bands.html`. Two categorical slots per chart (blue / orange) or one per segment (three). "
      f"The first run's charts are in git at `{FIRST}`.")
    out = C.REPO / C.OUT / "REPORT.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    shutil.copyfile(out, C.REPO / "results" / "reports" / "chop_regime_c1_report.md")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
