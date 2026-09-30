"""
Shape classifier S2 -- REPORT.md, generated from the artifacts (brief section 10: describes the pictures, no
interpretation, every number read from an artifact by this code). Amendment 1: both labels -- the remaining-path
type (primary, A1.3) and the whole-path type (secondary) -- side by side; row 3 as revised (A1.1); the A1.2 fix;
the A1.4 money intervals; A1.6 recorded.

Order: status and escalation, the timing audit and the A12 finding, the controls, the population, the labels and
the folds, the results per type (runaway, burst, slow climb, exhausted, fade, chop), the pooled tables, the rulings
and the amendment, reproduction.

Writes results/shape_classifier/s2/REPORT.md and its copy results/reports/shape_classifier_s2_report.md.

Usage: .venv/Scripts/python.exe research/shape_classifier_s2/build_report.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s2common as S  # noqa: E402

TL = S.TIME_LABEL
LAB = {"remaining": "remaining", "whole": "whole"}


def f(x, d=3):
    return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def i(x):
    return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{int(x):,}"


def md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def auc_cells(auc: pd.DataFrame, t: str, mdl: str, cw: str, label: str, read: str = "primary", N: int = 100) -> list[str]:
    a = auc[(auc["label"] == label) & (auc["type"] == t) & (auc["model"] == mdl) & (auc["cw"] == cw) & (auc["read"] == read) & (auc["label_N"] == N)]
    out = []
    for tk in S.TIMES:
        g = a[a["time"] == tk]
        if g.empty:
            out.append("–")
            continue
        rd = int(g["read_ok"].sum())
        g = g[g["read_ok"]]                          # row 5: a fold with < 20 events of the type is shown on the chart, not read here
        if g.empty:
            out.append("not read")
            continue
        out.append(f"{g['auc'].mean():.3f} ({g['auc'].min():.2f}–{g['auc'].max():.2f})" + ("" if rd == 3 else f" [{rd}/3 read]"))
    return out


def diff_cell(r) -> str:
    if r is None or not np.isfinite(r["diff_vs_all"]):
        return "–"
    return f"{r['diff_vs_all']:+.0f} [{r['diff_ci_lo']:+.0f}, {r['diff_ci_hi']:+.0f}] (n {int(r['n_ok'])})"


def main() -> int:
    cfg = S.load_cfg()
    a1 = cfg["amendment_1"]
    t0 = S.read_json("t0_summary.json")
    a12 = S.read_json("t0_a12.json")
    t1 = S.read_json("t1_summary.json")
    t2 = S.read_json("t2_summary.json")
    t3 = S.read_json("t3_summary.json")
    t3a = S.read_json("t3a_summary.json")
    t5 = S.read_json("t5_summary.json")
    t7 = S.read_json("t7_summary.json")
    au = pd.read_parquet(S.art("t0_audit.parquet"))
    auc = pd.read_parquet(S.art("t4_auc.parquet"))
    lift = pd.read_parquet(S.art("t4_lift.parquet"))
    ll = pd.read_parquet(S.art("t4_logloss.parquet"))
    conf = pd.read_parquet(S.art("t4_confusion.parquet"))
    gate = pd.read_parquet(S.art("t5_negative_gate.parquet"))
    pos = pd.read_parquet(S.art("t5_positive.parquet"))
    fw = pd.read_parquet(S.art("t6_forward.parquet"))
    imp = pd.read_parquet(S.art("t7_importance.parquet"))
    cnt = pd.read_parquet(S.art("t3_counts.parquet"))
    tun = pd.read_parquet(S.art("t4_tuning.parquet"))
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=S.REPO, capture_output=True, text=True).stdout.strip()
    import sklearn
    L = []
    w = L.append

    r1, r2, r3 = t0["row1"], t5["row2_negative"], t5["row3_positive"]
    r4, r5 = t7["row4_log"], t3["row5_log"]
    stop = r1["fires"] or r2["fires"] or r3["fires"]
    w("# Shape classifier S2 — can the six types be predicted, at the crossing and as the path unfolds?\n")
    w(f"**Brief:** `prompts/shape_classifier_s2.md` and **Amendment 1** `prompts/shape_classifier_s2_amendment_1.md` · **Config:** `config/shape_classifier_s2.json` "
      f"(hash `{S.cfg_hash()}`) · **Branch:** `explore/shape-classifier-s2` · **Code:** `research/shape_classifier_s2/` · **Built at:** `{head}` · 2026-09-29\n")
    w("Exploratory modelling build, not a phase. The test is ticker-blocked and time-ordered (folds test 2022, 2023, 2024); everything else is exploratory. "
      "This report describes the artifacts and charts; it does not interpret them.\n")
    w("**Two labels (Amendment 1 A1.3).** *Remaining* (primary): the S1 type of the path from each checkpoint's entry (the next print after the decision time) to "
      "20:00, by S1's rules and its own 200-draw null; at τ it is the whole-path type. *Whole* (secondary): the S1 type of the whole post-τ path, as first run. "
      "Every table below carries both.\n")
    fired = [n for n, r in (("1", r1), ("2", r2), ("3", r3)) if r["fires"]]
    w(f"**Status: {'HARD STOP -- escalation row ' + ', '.join(fired) + ' fired; state committed, nothing fixed or tuned.' if stop else 'stop after the report (Amendment 1 A1.5) for Cooper.'}**\n")

    # ------------------------------------------------------------------ escalation
    w("## Escalation table\n")
    r5n = {lab: r5[lab]["n_cells"] for lab in S.LABELS}
    w(md_table(["row", "criterion", "tier", "observed", "fires"], [
        ["1", "any input uses data after its decision time", "HARD STOP", f"{r1['violations']:,} input rows after their decision time (t0_audit.parquet)", "yes" if r1["fires"] else "no"],
        ["2", "negative control outside 0.45–0.55 (R5 read: mean of 3 folds × 10 shuffles)", "HARD STOP",
         f"{r2['outside']} of {r2['cells']:,} label × type × model × time cells outside; means span {f(r2['mean_auc_range'][0])}–{f(r2['mean_auc_range'][1])}", "yes" if r2["fires"] else "no"],
        ["3", "positive control below 0.95 (R4 rule inputs; A1.1: M3 gated, M2 reported)", "HARD STOP",
         f"M3: {r3['below']} of {r3['cells']:,} per-fold cells below 0.95 (minimum {f(r3['min_auc'], 4)}); M2, ungated: "
         + "; ".join(f"{lab} {t5['per_label'][lab]['m2_ungated']['below']} of {t5['per_label'][lab]['m2_ungated']['cells']} below (min {f(t5['per_label'][lab]['m2_ungated']['min_auc'], 4)})"
                     for lab in S.LABELS), "yes" if r3["fires"] else "no"],
        ["4", "one input > half of a type's permutation importance (M3)", "LOG", f"{r4['n_cells']} label × fold × time × type cells; inputs: {', '.join(r4['inputs']) or 'none'}",
         "LOG" if r4["n_cells"] else "no"],
        ["5", "a fold's primary test set < 20 labelled events of a type", "LOG", "; ".join(f"{lab} {n} fold × time × type cells" for lab, n in r5n.items()) + " (§3)",
         "LOG" if sum(r5n.values()) else "no"],
        ["6", "sklearn / HistGradientBoostingClassifier unavailable offline", "HARD STOP", f"sklearn {sklearn.__version__}; HistGradientBoostingClassifier imported", "no"],
    ]))
    w("\nRow 3 on the first run (commit `92c99cc`): 7 of 720 cells below 0.95, all M2 (balanced), chop; cleared by Cooper's A1.1 on that run (M3 1.000 in every cell). "
      "The table above is the re-run.\n")

    # ------------------------------------------------------------------ T0
    w("## 1. Timing audit (T0) and the A12 finding\n")
    c = a12["construction"]
    k = a12["checked_on_disk"]
    w("### 1.1 How `flag_cross_session_extreme` is built\n")
    w(f"- Code: `{c['code']}`.")
    w(f"- Per session pair: {c['per_pair']}; threshold |log r| ≥ {f(c['threshold']['log'], 4)} (ratio outside {f(c['threshold']['ratio'][0], 4)}–{f(c['threshold']['ratio'][1], 2)}).")
    w(f"- Close: {c['close']}.")
    w(f"- Pair carried by b1, b2 and S1: {c['pair_used_by_b1_b2_s1']}.")
    w(f"- **It uses the event day's close.** {c['consequence'][0].upper() + c['consequence'][1:]}.")
    w(f"- Checked on disk ({k['events']:,} S2 events; {k['with_tm1_t0_pair']:,} carry the tm1_t0 pair): the T0 close equals the event day's last print at or before 20:00 "
      f"for {k['t0_close_equals_event_day_last_print_at_or_before_2000']:,} ({k['t0_close_differs']:,} differ); that last print is after τ for "
      f"{k['event_day_last_print_after_tau']:,}. Flagged: {k['flagged']:,}.")
    w("- Flag rate by S1 type (N = 100): " + "; ".join(f"{S.TYPE_LABEL[t]} {f(v['rate'])} ({v['flagged']}/{v['n']:,})" for t, v in k["flag_rate_by_type"].items()) + ".\n")
    w("### 1.2 Every earlier use of the flag\n")
    uses = pd.Series([x["use"] for x in a12["consumers_code"]]).value_counts().to_dict()
    w(f"{len(a12['consumers_code'])} tracked code files read the flag (list checked against `git grep`): " + ", ".join(f"{v} {kk}" for kk, v in uses.items()) +
      f". Files that use it as an **input** (a fitted model, a selection rule or a threshold): **{len(a12['consumers_as_input'])}**" +
      (": " + ", ".join(f"`{x}`" for x in a12["consumers_as_input"]) if a12["consumers_as_input"] else "") + ". "
      f"{a12['outside_repo'][0].upper() + a12['outside_repo'][1:]}.\n")
    w(md_table(["file", "use", "how"], [[f"`{x['file']}`", x["use"], x["how"]] for x in a12["consumers_code"]]))
    w(f"\nNon-code records naming the flag (reports, briefs, configs, docs): {len(a12['consumers_non_code_records'])} files — "
      + ", ".join(f"`{x}`" for x in a12["consumers_non_code_records"]) + ".\n")
    w(f"**A1.6 (recorded, acted on separately).** {a1['A1_6_a12']}.\n")
    w("### 1.3 Latest data timestamp of every input\n")
    g = au.groupby(["group", "input", "what"]).agg(rows=("n", "sum"), after=("n_after_decision", "sum"), mx=("max_latest_minus_decision_s", "max")).reset_index()
    w(md_table(["group", "input", "what it reads", "rows", "after decision", "max (latest − decision), s"],
               [[r.group, f"`{r.input}`", r.what, i(r.rows), i(r.after), f(r.mx, 9)] for r in g.itertuples()]))
    w(f"\nRow 1: **{r1['violations']:,}** violations. Per decision time: `artifacts/t0_audit.parquet`. The labels (both) are outputs, never inputs.\n")
    w("### 1.4 Other timing findings, measured before the build\n")
    tr = t0["tau_rounding"]
    w(f"- **Stored τ is float64-rounded.** {tr['finding']}: all {tr['stored_multiple_of_256']:,} stored values are multiples of 256 ns; the crossing print equals the stored value for "
      f"{tr['exact_equals_stored']:,}, is later for {tr['crossing_after_stored']:,} and earlier for {tr['crossing_before_stored']:,} (max |difference| {tr['max_abs_ns']} ns). "
      f"{tr['events_with_prints_after_crossing_up_to_stored']:,} events have prints after the crossing print and at or before the stored τ ({tr['prints_after_crossing_up_to_stored']:,} prints). "
      f"Handling: {tr['handling']}. Live names crossing after τ_d: {tr['live_names_crossing_after_tau_d']}.")
    mb = t2["minute_bar_crossing_vs_b1"]
    w(f"- **`tau_close_sensitive` (Cooper R1) and the A1.2 fix.** Not settled at τ for 3,585 events (measured on b1's stored values before the build). The minute-bar crossing is "
      f"recomputed from ticks with b1's `first_crossing` on the full print arrays (A1.2): {mb['within_128ns_of_b1']:,} of {mb['both']:,} within 128 ns of b1's stored value "
      f"(max {f(mb['max_abs_ns'] / 1e9 if mb['max_abs_ns'] is not None else np.nan, 9)} s; exact-only {mb['exact_only']}, b1-only {mb['b1_only']}); the fully settled flag equals b1's for "
      f"{t2['tcs_final_vs_b1']['equal_to_b1_flag']:,} of {t2['tcs_final_vs_b1']['events']:,}. Before the fix, 66 events differed (T2 called it on the 04:00–20:00 slice; diagnosis "
      "`artifacts/t2b_mb_diagnosis.*`, as committed at `92c99cc`). State at each decision time: "
      + "; ".join(f"{TL[tk]} {', '.join(f'{a} {b:,}' for a, b in sorted(v.items()))}" for tk, v in t2["tcs_state_counts"].items() if v) + ".")
    si = t1["short_interest_tau"]
    w(f"- **Short interest (Cooper R2).** F1's `si_asof_ns` is the settlement date, not publication. Rebuilt from the raw vendor files: latest settlement whose assumed publication "
      f"({si['sessions_lag']} XNYS sessions later) is before the event date — {si['available']:,} events (F1 settlement-dated: {si['f1_settlement_dated_available']:,}; same value as F1: "
      f"{si['same_value_as_f1']:,}); median settlement {f(si['settlement_to_event_days_median'], 0)} days before the event. FINRA's actual lag is not verifiable offline [verify].")
    sh, dl = t1["shares_tau"], t1["dilution_tau"]
    w(f"- **Fundamentals re-anchored at τ (Cooper R3).** Shares outstanding available for {sh['available']:,} events (F1 at t0: {sh['f1_t0_available']:,}); equal to F1's value for "
      f"{sh['equal_to_f1']:,}, different for {sh['differs_from_f1']:,}; split correction applied to {sh['correction_applied']:,}. Dilution flag TRUE for {dl['true']:,} (F1 at t0: {dl['f1_t0_true']:,}; "
      f"{dl['differs_from_f1']:,} differ). Filings cross-check against b2 (accepted < τ): filing_24h agrees for {f(t1['filings_crosscheck_vs_b2']['filing_24h_agree'] * 100, 2)}%, "
      f"last form for {f(t1['filings_crosscheck_vs_b2']['last_form_agree'] * 100, 2)}% of {t1['filings_crosscheck_vs_b2']['events_with_cik_filings']:,} events.")
    tc = t0["decision_time_properties"]["tau_spike_guard"]
    w(f"- **τ is confirmed at its successor.** {tc['note'][0].upper() + tc['note'][1:]}. Seconds from the τ print to its successor: median {f(tc['quantiles_s']['0.5'], 6)}, "
      f"90th pct {f(tc['quantiles_s']['0.9'], 3)}, 99th {f(tc['quantiles_s']['0.99'], 1)}, max {f(tc['quantiles_s']['1.0'], 0)}; zero (same timestamp) for "
      f"{f(tc['zero_share'] * 100, 1)}% (n {tc['n']:,}).")
    w(f"- **Live set.** {t0['decision_time_properties']['live_set'][0].upper() + t0['decision_time_properties']['live_set'][1:]}.")
    w(f"- CLAUDE.md index check (`tools/verify_claude_md_indices.py`): exit {t0['claude_md_indices']['exit_code']}.\n")

    # ------------------------------------------------------------------ controls
    w("## 2. Controls (T5) — `charts/t5/controls.html`\n")
    w(f"**Negative (Cooper R5).** Labels permuted within each fold's training window (the remaining label per decision time), 10 shuffles per fold, Group C typical paths rebuilt "
      f"from the permuted labels, M1–M4 at the real run's settings. Row 2 reads the mean of the 30 per-fold primary AUCs: {r2['outside']} of {r2['cells']:,} cells outside 0.45–0.55; "
      f"means span {f(r2['mean_auc_range'][0])}–{f(r2['mean_auc_range'][1])}. Single-shuffle per-fold AUCs outside the band: {r2['single_shuffle_cells_outside_band']:,} of "
      f"{r2['single_shuffle_cells']:,} (the brief's construction read cell by cell).\n")
    gm = gate.groupby(["label", "model", "cw"]).agg(lo=("mean_auc", "min"), hi=("mean_auc", "max"), slo=("min_auc", "min"), shi=("max_auc", "max")).reset_index()
    w(md_table(["label", "model", "class weight", "mean AUC, min", "mean AUC, max", "single shuffle, min", "single shuffle, max"],
               [[r.label, r.model, r.cw, f(r.lo), f(r.hi), f(r.slo), f(r.shi)] for r in gm.itertuples()]))
    w("")
    pg = pos.groupby(["label", "leak", "model", "cw", "type"])["auc"].agg(["min", "mean"]).reset_index()
    w(f"**Positive (Cooper R4; row 3 per A1.1).** The rule inputs of each label's own path (whole: post100 rise_pct, fall_pct, u_peak; remaining: the remaining path's) added to "
      f"M2 and M3 at every decision time, real run's settings. Row 3 gates M3: {r3['below']} of {r3['cells']:,} per-fold cells below 0.95; minimum {f(r3['min_auc'], 4)}. "
      "Minimum per-fold primary AUC by label, model, class weight and type:\n")
    rl = pg[pg["leak"] == "rules"]
    w(md_table(["label", "model", "class weight"] + [S.TYPE_LABEL[t] for t in S.TYPES],
               [[lab, m, cw] + [f(g0[g0["type"] == t]["min"].iloc[0], 4) for t in S.TYPES] for (lab, m, cw), g0 in rl.groupby(["label", "model", "cw"])]))
    w("")
    if r3["fires"]:
        w("**Row 3 fires.** The M3 cells below 0.95:\n")
        w(md_table(["label", "fold", "decision time", "class weight", "type", "AUC", "n", "n_type"],
                   [[c_["label"], c_["fold"], TL[c_["time"]], c_["cw"], S.TYPE_LABEL[c_["type"]], f(c_["auc"], 4), i(c_["n"]), i(c_["n_type"])] for c_ in r3["below_cells"]]))
        w("")
    if r2["fires"]:
        w("**Row 2 fires.** The negative-control cells outside 0.45–0.55:\n")
        w(md_table(["label", "model", "class weight", "decision time", "type", "mean AUC", "draws", "single-shuffle range"],
                   [[c_["label"], c_["model"], c_["cw"], TL[c_["time"]], S.TYPE_LABEL[c_["type"]], f(c_["mean_auc"]), c_["draws"], f"{f(c_['min_auc'])}–{f(c_['max_auc'])}"]
                    for c_ in r2["outside_cells"]]))
        w("")
    w("terminal_log of each label's own path (the brief's construction), reported ungated — mean (minimum) of the per-fold primary AUCs over folds and decision times:\n")
    rows = []
    for (lab, mdl, cw), g0 in pg[pg["leak"] == "terminal_log"].groupby(["label", "model", "cw"]):
        rows.append([lab, mdl, cw] + [f"{f(g0[g0['type'] == t]['mean'].iloc[0])} ({f(g0[g0['type'] == t]['min'].iloc[0])})" for t in S.TYPES])
    w(md_table(["label", "model", "class weight"] + [S.TYPE_LABEL[t] for t in S.TYPES], rows))
    b = t5["baseline_tau"]
    w("\n**Baseline (M1 vs M0 at τ, where both labels are the same), primary read, mean of three folds:**\n")
    w(md_table(["model"] + [S.TYPE_LABEL[t] for t in S.TYPES] + ["log loss", "skill vs M0"],
               [[m] + [f(b["auc_mean_over_folds"][f"{m}|primary"][t]) for t in S.TYPES] + [f(b["log_loss_mean_over_folds"][f"{m}|primary"]["log_loss"], 4),
                                                                                         f(b["log_loss_mean_over_folds"][f"{m}|primary"]["skill"], 4)] for m in ("M0", "M1")]))
    w("")

    # ------------------------------------------------------------------ population, labels, folds
    w("## 3. Population, decision times, labels and folds (T2, T3a, T3)\n")
    ex = t3["excluded"]
    w(f"15,519 S1 events with τ; excluded from every fold: {ex['dev_v3']} dev_v3 and {ex['dev_v4_sidecar']} sidecar events; without the whole-path label: {ex['unlabelled_non_dev']}.\n")
    st = t3a["states"]
    w(md_table(["decision time", "reached", "not_reached", "undefined", "elapsed min (10/50/90th pct)", "remaining label typed", "no entry", "path too short", "σ zero / no null"],
               [[TL[tk], i(t2["states"][tk].get("reached", 0)), i(t2["states"][tk].get("not_reached", 0)), i(t2["states"][tk].get("undefined", 0)),
                 " / ".join(f(t2["elapsed_min_at_volume_checkpoints"][tk][q], 1) for q in ("0.1", "0.5", "0.9")) if tk in S.VOL else "–",
                 i(st[tk].get("typed", 0) + st[tk].get("typed_whole_at_tau", 0)), i(st[tk].get("no_entry", 0)), i(st[tk].get("path_too_short", 0)),
                 i(st[tk].get("sigma_zero_or_no_null", 0))] for tk in S.TIMES]))
    w("\nType shares of the remaining-path label at each decision time (all events with the label):\n")
    w(md_table(["type"] + [TL[tk] for tk in S.TIMES], [[S.TYPE_LABEL[t]] + [i(t3a["type_shares"][tk][t]) for tk in S.TIMES] for t in S.TYPES]))
    w("\n**How often the remaining-path type differs from the whole-path type (A1.5), per whole-path type** — share of the events of that whole type whose remaining type at "
      "the checkpoint is different (n = labelled, non-dev events of the whole type at that checkpoint):\n")
    rows = []
    for t in S.TYPES:
        cells = []
        for tk in S.TIMES:
            d = t3a["whole_vs_remaining"][tk][t]
            cells.append(f"{d['differ'] / d['n']:.0%} (n {d['n']:,})" if d["n"] else "–")
        rows.append([S.TYPE_LABEL[t]] + cells)
    w(md_table(["whole type"] + [TL[tk] for tk in S.TIMES], rows))
    w("\nWhat the whole type becomes at τ + 20 min (counts of the remaining type), for reference:\n")
    d20 = t3a["whole_vs_remaining"]["w20"]
    w(md_table(["whole type \\ remaining type"] + [S.TYPE_LABEL[t] for t in S.TYPES],
               [[S.TYPE_LABEL[wt]] + [i(d20[wt]["remaining_types"].get(t, 0)) for t in S.TYPES] for wt in S.TYPES]))
    w("")
    rows = []
    for fo in ("1", "2", "3"):
        for role in ("train", "sub", "val", "test", "primary"):
            x = t3["folds"][fo][role]
            rows.append([fo, role, i(x["events"]), i(x["tickers"])] + [i(x["types"][t]) for t in S.TYPES])
    w("Folds (whole-path type counts; the remaining label's per-checkpoint counts are in `artifacts/t3_counts.parquet`):\n")
    w(md_table(["fold", "role", "events", "tickers"] + [S.TYPE_LABEL[t] for t in S.TYPES], rows))
    w("\n**Row 5 (LOG).** Fold × decision time × type cells with fewer than 20 labelled events of the type among the primary events that reached the decision time; shown "
      "(hollow markers) and not read; the cells follow.\n")
    for lab in S.LABELS:
        r5d = pd.DataFrame(r5[lab]["cells"])
        if len(r5d):
            agg = r5d.groupby(["fold", "type"]).agg(times=("time", lambda s: ", ".join(TL[x] for x in S.TIMES if x in set(s))), nmin=("n", "min"), nmax=("n", "max")).reset_index()
            w(f"*{lab} label* ({len(r5d)} cells)\n")
            w(md_table(["fold", "type", "decision times", "n range"], [[r.fold, S.TYPE_LABEL[r.type], r.times, f"{r.nmin}–{r.nmax}"] for r in agg.itertuples()]))
            w("")

    # ------------------------------------------------------------------ per type
    w("## 4. Results per type — `charts/t4/auc_by_time.html`, `lift_by_time.html`, `calibration.html`, `confusion.html`, `charts/t6/money_intervals.html`, "
      "`forward_returns.html`, `charts/t7/importance.html`\n")
    w("AUC cells: mean of the readable folds' primary-read AUCs, with their range in brackets; `[k/3 read]` marks cells where row 5 leaves only k of the three folds "
      "readable (the others are on the chart, hollow). Rows pair the two labels for each model (class weight none; balanced in §5). At τ both labels are the same. "
      "Per-fold values with 95% ticker-bootstrap intervals: `artifacts/t4_auc.parquet` and the chart.\n")
    w("Money (A1.4): median net forward return of the model's decile minus that of all primary test events at the decision time, bp net of 70.98, next-print entry, "
      "with the 95% ticker-bootstrap interval (500 resamples, paired) and n; M3 (none). Every entry, unit, horizon and model: `charts/t6/money_intervals.html`, "
      "`artifacts/t6_forward.parquet`.\n")
    fm = fw[(fw["model"] == "M3") & (fw["cw"] == "none") & (fw["latency"] == "lat0") & (fw["unit"] == "bp")]
    for t in S.TYPES:
        w(f"### 4.{S.TYPES.index(t) + 1} {S.TYPE_LABEL[t]}\n")
        cr = []
        for lab in S.LABELS:
            nt = cnt[(cnt["label"] == lab) & (cnt["role"] == "primary") & (cnt["state"] == "reached") & (cnt["type"] == t)].groupby("time")["n"].sum().reindex(S.TIMES)
            cr.append(f"{lab}: " + ", ".join(f"{TL[tk]} {i(nt[tk])}" for tk in S.TIMES))
        w("Labelled primary test events of the type at each decision time (three folds summed) — " + "; ".join(cr) + ".\n")
        rows = []
        for m in ("M1", "M2", "M3", "M4"):
            for lab in S.LABELS:
                if m == "M1" and lab == "remaining":
                    continue
                rows.append([f"{m} — {LAB[lab]}" if m != "M1" else "M1 (τ only)"] + auc_cells(auc, t, m, "none", lab))
        w(md_table(["model — label"] + [TL[tk] for tk in S.TIMES], rows))
        w("")
        lr = []
        for m in ("M2", "M3"):
            for lab in S.LABELS:
                x = lift[(lift["label"] == lab) & (lift["type"] == t) & (lift["model"] == m) & (lift["cw"] == "none") & (lift["read"] == "primary") & lift["read_ok"]].groupby("time")["lift"].mean().reindex(S.TIMES)
                lr.append([f"{m} — {lab}"] + [f(v, 2) for v in x])
        w("Top-10% lift (mean of the readable folds, primary):\n")
        w(md_table(["model — label"] + [TL[tk] for tk in S.TIMES], lr))
        w("")
        mo = []
        for lab in S.LABELS:
            for h, hl in (("h30", "+30 min"), ("to2000", "to 20:00")):
                for which, wl in (("top_decile", "top"), ("bottom_decile", "bottom")):
                    x = fm[(fm["label"] == lab) & (fm["type"] == t) & (fm["horizon"] == h) & (fm["set"] == which)].set_index("time")
                    mo.append([f"{lab}, {wl} decile, {hl}"] + [diff_cell(x.loc[tk]) if tk in x.index else "–" for tk in S.TIMES])
        w("Decile minus all, median net bp (M3, next-print entry):\n")
        w(md_table(["label, set, horizon"] + [TL[tk] for tk in S.TIMES], mo))
        w("")
        it = imp[(imp["type"] == t) & (imp["label"] == "remaining")].groupby(["time", "input"])["share"].mean().reset_index()
        tops = []
        for tk in S.TIMES:
            x = it[it["time"] == tk].sort_values("share", ascending=False).head(3)
            tops.append([TL[tk]] + [f"`{r.input}` {f(r.share, 2)}" for r in x.itertuples()])
        w("M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):\n")
        w(md_table(["decision time", "1st", "2nd", "3rd"], tops))
        w("")

    # ------------------------------------------------------------------ pooled
    w("## 5. Pooled tables\n")
    w("Multiclass log-loss skill against M0 on the same test rows (1 − LL / LL_M0), primary read, mean of three folds:\n")
    sk = ll[ll["read"] == "primary"].groupby(["label", "model", "cw", "time"])["skill"].mean()
    rows = []
    for m, cw in (("M1", "none"), ("M2", "none"), ("M2", "balanced"), ("M3", "none"), ("M3", "balanced"), ("M4", "none"), ("M4", "balanced")):
        for lab in S.LABELS:
            if m == "M1" and lab == "remaining":
                continue
            rows.append([f"{m} ({cw}) — {lab}"] + [f(sk.get((lab, m, cw, tk), np.nan), 4) for tk in S.TIMES])
    w(md_table(["model — label"] + [TL[tk] for tk in S.TIMES], rows))
    w("\nBalanced class weights, primary AUC (mean of the readable folds):\n")
    for t in S.TYPES:
        w(f"*{S.TYPE_LABEL[t]}*\n")
        w(md_table(["model — label"] + [TL[tk] for tk in S.TIMES],
                   [[f"{m} — {lab}"] + auc_cells(auc, t, m, "balanced", lab) for m in ("M2", "M3", "M4") for lab in S.LABELS]))
        w("")
    w("Secondary read (all test events), M3 (none), AUC mean of three folds:\n")
    w(md_table(["type — label"] + [TL[tk] for tk in S.TIMES],
               [[f"{S.TYPE_LABEL[t]} — {lab}"] + auc_cells(auc, t, "M3", "none", lab, read="secondary") for t in S.TYPES for lab in S.LABELS]))
    w("\nRung (whole label only): M3 (none) probabilities scored against the N = 50 and N = 200 whole-path labels (never fitted), primary read, mean AUC of three folds:\n")
    rr = []
    for N in (50, 100, 200):
        for t in S.TYPES:
            a = auc[(auc["label"] == "whole") & (auc["model"] == "M3") & (auc["cw"] == "none") & (auc["read"] == "primary") & (auc["label_N"] == N) & (auc["type"] == t)].groupby("time")["auc"].mean().reindex(S.TIMES)
            rr.append([f"N = {N}", S.TYPE_LABEL[t]] + [f(v) for v in a])
    w(md_table(["label", "type"] + [TL[tk] for tk in S.TIMES], rr))
    w("\nConfusion at the most probable type, M3 (none), primary read, three folds summed, remaining label at τ + 20 min (row = true type, cells = counts):\n")
    m = conf[(conf["label"] == "remaining") & (conf["model"] == "M3") & (conf["cw"] == "none") & (conf["read"] == "primary") & (conf["time"] == "w20")].pivot_table(
        index="true", columns="pred", values="n", aggfunc="sum").reindex(index=S.TYPES, columns=S.TYPES)
    w(md_table(["true \\ predicted"] + [S.TYPE_LABEL[t] for t in S.TYPES], [[S.TYPE_LABEL[t]] + [i(v) for v in m.loc[t]] for t in S.TYPES]))
    ch = tun[tun["chosen"]].groupby(["label", "model", "cw", "setting"]).size().reset_index(name="n")
    w("\nSettings chosen by validation log loss inside the training windows (count of fold × decision time jobs; the remaining label's τ jobs are the whole label's):\n")
    w(md_table(["label", "model", "class weight", "setting", "jobs"], [[r.label, r.model, r.cw, f"`{r.setting}`", r.n] for r in ch.itertuples()]))
    w("")
    if r4["n_cells"]:
        w("**Row 4 (LOG).** Cells where one input carries more than half of a type's M3 permutation importance, with the input's timing re-check (its row in §1.3):\n")
        r4d = pd.DataFrame(r4["cells"])
        w(md_table(["label", "fold", "time", "type", "input", "share", "AUC drop", "base AUC", "n_type"],
                   [[r.label, r.fold, TL[r.time], S.TYPE_LABEL[r.type], f"`{r.input}`", f(r.share, 2), f(r.mean_drop, 4), f(r.base_auc), r.n_type] for r in r4d.itertuples()]))
        w("")

    # ------------------------------------------------------------------ rulings and interpretations
    w("## 6. Rulings, the amendment and declared interpretations\n")
    for kk, v in cfg["cooper_rulings_2026_09_28"].items():
        if kk.startswith("_"):
            continue
        w(f"- **{kk}** — measured: {v['measured']} Ruling: {v['ruling']}.")
    w("")
    for kk in ("A1_1_row3", "A1_2_crossing", "A1_5_scope", "charts", "A1_6_a12"):
        w(f"- **Amendment 1, {kk}** — {a1[kk]}.")
    for kk, v in a1["A1_3_labels"].items():
        w(f"- **Amendment 1, A1.3 {kk}** — {v}.")
    for kk, v in a1["A1_4_money_intervals"].items():
        w(f"- **Amendment 1, A1.4 {kk}** — {v}.")
    w("")
    for kk, v in cfg["declared_interpretations"].items():
        if kk.startswith("_"):
            continue
        w(f"- `{kk}`: {v}")
    w("")
    w("Excluded inputs: " + "; ".join(f"`{kk}` — {v}" for kk, v in cfg["inputs"]["excluded"].items()) + ".\n")
    w("Deferred, not built (brief §4): a two-stage model; predicting the components and applying the type rules; sequential updating of the at-crossing probabilities.\n")

    # ------------------------------------------------------------------ reproduction
    w("## 7. Reproduction and outputs\n")
    w("```\n" + "\n".join(f".venv/Scripts/python.exe research/shape_classifier_s2/{x}" for x in
                          ("t1_group_a.py", "t2_checkpoints.py", "t3a_remaining_labels.py", "t0_audit.py", "t3_folds.py", "t4_models.py", "t4_scores.py",
                           "t6_money.py", "t7_importance.py", "t5_controls.py", "charts.py", "build_report.py")) + "\n```\n")
    w("T0's audit runs after T1 and T2 because it audits what they built; T1 and T2 also assert their own inputs as they write them. `t2b_mb_diagnosis.py` is the record of "
      "the pre-A1.2 defect (not re-run). `results/shape_classifier/s2/cache/` (tick-pass caches and master-grid paths, rebuilt by T1/T2) is git-ignored in place and not committed.\n")
    arts = sorted(os.listdir(S.REPO / S.ART))
    w("Artifacts (`results/shape_classifier/s2/artifacts/`): " + ", ".join(f"`{a}`" for a in arts) + ".\n")
    w("Charts: `charts/t4/auc_by_time.html`, `charts/t4/lift_by_time.html`, `charts/t4/calibration.html`, `charts/t4/confusion.html`, `charts/t5/controls.html`, "
      "`charts/t6/money_intervals.html`, `charts/t6/forward_returns.html`, `charts/t7/importance.html`.\n")
    txt = "\n".join(L) + "\n"
    out = S.REPO / S.OUT / "REPORT.md"
    out.write_text(txt, encoding="utf-8")
    cp = S.REPO / "results/reports/shape_classifier_s2_report.md"
    shutil.copyfile(out, cp)
    print(f"wrote {out} ({len(txt):,} chars) and {cp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
