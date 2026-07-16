<!-- fullWidth: false tocVisible: false tableWrap: true -->
# Agent Prompt Standard

**Version:** 1.3\
**Project:** Momentum Event Research — Mom_db

This document defines the standard structure for all Claude Code agent prompts in this project. Every phase prompt must follow this format. Deviations require explicit justification in the prompt itself.

---

## Why This Exists

Agent prompts have grown organically across phases. Inconsistent structure causes three problems:

1. Agents make judgment calls they shouldn't (self-resolve vs. escalate)
2. Results are hard to audit because output contracts vary phase to phase
3. Claims arrive without the evidence needed to check them

This standard fixes all three.

---

## The Evidence Standard

**This is the rule the whole document exists to serve. Read it before anything else.**

The agent is not banned from stating what it found. It is banned from stating what it found **without showing the distribution behind it**.

A mean is a claim about a distribution with the distribution deleted. "Spread is lower during bursts, mean 0.9% vs 3.4%" could be true, or it could be two bimodal distributions that overlap almost entirely with a few outliers dragging the means apart. From the sentence alone, you cannot tell. That is the failure mode this standard exists to prevent.

### The rule

> **Every claim in an agent report must point to a chart that shows the underlying distribution, and every summary statistic must be accompanied by n.**

Concretely:

| Instead of | Show |
| --- | --- |
| A mean | The distribution — histogram, violin, ECDF, or strip plot with the mean marked |
| A mean by group | The distribution per group, side by side, with per-group n |
| A correlation or fitted slope | The scatter, with the fit overlaid and the raw points visible |
| A win rate | The PnL distribution, not just the fraction above zero |
| "X increases with Y" | Bucketed conditional means **with dispersion bands and per-bucket n** — and a monotonicity check |
| "No relationship found" | The same chart. Nulls need evidence too, or you can't distinguish "no effect" from "no power." |

### What is and isn't allowed

**Allowed and expected:**

- Measurements with n: "median burst spread 0.9% (n=8,412), median quiet spread 3.4% (n=61,003) — see `charts/03_spread_by_participation.html`"
- Description of what's visible in a chart: "the relationship is monotonic across all eight buckets; the bottom two buckets have n < 50 and wide dispersion"
- Explicit uncertainty: "the effect direction is consistent but the two bottom buckets are too thin to read"
- Explicit "I don't know"

**Not allowed:**

- Any claim whose supporting chart doesn't exist
- A summary statistic without n
- Recommendations ("we should proceed to...", "this parameter should be raised to...")
- Interpretation of what a result means for the strategy — that is Cooper's call, made from the charts
- Any parameter change made in response to a bad result

The line: **the agent describes the picture, Cooper decides what the picture means.** If a claim can't be checked against a chart in under ten seconds, it doesn't belong in the report.

---

## Prompt Structure

Every agent prompt has these twelve sections, in this order.

---

### 1\. Header Block

One paragraph. Covers: what phase this is, what the previous phase established, what this phase changes or validates, and the primary success metric.

```
## Phase [X] — [Short Name]

**Date:** YYYY-MM-DD  
**Baseline:** [Prior phase] — [val sample], PF=[X.XXXX], [N] trades  
**Objective:** [One sentence — what this phase accomplishes]  
**Primary success metric:** [e.g., PF > 1.53 on 100-event val sample, seed=42]
```

Keep it tight. If the agent needs more context, link to the relevant result file — don't inline it.

---

### 2\. Context & Constraints

A short bullet list of facts the agent must hold in mind. These are not tasks — they're operating constraints.

```
**Context:**
- Train/val/test separation is strictly enforced. No test set access.
- Hardware: Ryzen 5 3600, GTX 1070 (FP32 only), 32GB RAM. No CUDA FP16.
- Working directory: [repo root]
- Config files live in config/. Do not modify configs that belong to a prior phase without explicit instruction.
- [Any phase-specific constraints]
```

List only what's actually relevant to this phase. Don't copy-paste the full project context every time — standing constraints live in `CLAUDE.md` and are already loaded.

---

### 3\. Task Checklist

A numbered checkbox list. Each item is a discrete, verifiable unit of work.

Rules:

- Tasks are sequential unless explicitly marked `[PARALLEL OK]`
- Each task produces a concrete artifact (file, metric, log line) — no open-ended tasks
- If a task requires a decision (e.g., parameter selection), state the selection criterion explicitly so the agent doesn't invent one
- Break compound tasks into sub-tasks with indented checkboxes
- **Each task ends with a commit** (§12)

```
## Tasks

- [ ] **T1 — [Short label]**  
  [What to do. What file to write. What criterion to use if a choice is involved.]

  - [ ] T1a — [Sub-task if needed]
  - [ ] T1b — [Sub-task if needed]

- [ ] **T2 — [Short label]**  
  [Same pattern]
```

---

### 4\. Escalation Criteria

An explicit table. The agent checks every row after each task that could trigger one.

```
## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| Condition | Threshold | Action |
|-----------|-----------|--------|
| [Metric] [comparison] [value] | e.g., PF < 1.30 | Hard stop — post results, await instruction |
| [Metric] [comparison] [value] | e.g., null_spread_pct > 5% | Hard stop — post results, await instruction |
| [Condition] | e.g., Any WF window 5th pct < 1.0 | Hard stop — post results, await instruction |
```

**Hard stop** means: commit the current state, post results, explain which criterion was triggered and the observed value, and wait. The agent does not attempt to fix the problem or move to the next task.

If multiple criteria trigger at once, report **in table order** — the table is the priority order.

If no escalation criteria apply to a task, state that explicitly: `No escalation criteria for this task.`

---

### 5\. Output File Contract

A table listing every file this phase must produce. Agent marks status as it goes.

```
## Output Files

| File | Description | Status |
|------|-------------|--------|
| `results/phase_[x]/[task]/[filename].json` | [What it contains] | [ ] |
| `results/phase_[x]/[task]/charts/[name].html` | [Chart description] | [ ] |
| `config/[name].json` | [What params it holds] | [ ] |
```

Rules:

- Every output file must be listed before the agent starts
- If a file is conditional (e.g., only written on escalation), note that in the description
- The agent must not write files to locations not listed here without posting to chat first
- `digest.json` and `REPORT.md` are implicit on every phase — no need to list them

---

### 6\. Reporting Format

Tells the agent exactly what to post when the phase is complete (or when escalating).

```
## Reporting

On completion, post:
1. Comparison table: [prior baseline] vs. Phase [X] — columns: [list the metrics]
2. Exit breakdown table: count and % for each exit type
3. Escalation check table: each criterion, observed value, pass/fail
4. Walk-forward table if applicable
5. Output file table with final status column filled in
6. [Any phase-specific charts or summaries]

On escalation, post:
1. Which criterion triggered and the observed value
2. The metrics table up to the point of failure
3. No recommendations — present data only
```

**Every posted table carries n per row.** Every claim in prose carries the chart filename that supports it. A report that states a finding with no chart reference is incomplete and gets sent back.

---

### 7\. Per-Event Charts

**This section is mandatory for every phase that produces trade records.** Analysis-only phases (no backtest run) are exempt from *per-event* charts but are **not** exempt from §9 — they still have a chart contract.

Per-event charts are the primary tool for keeping the strategy auditable. They turn backtest output into something that can be read and inspected, not just measured.

#### Why this is required

- Aggregate metrics (PF, win rate) can mask event-level pathology — a handful of outlier events can carry or drag the whole sample
- Signal behavior on individual events reveals whether exits, entries, and gates are firing for the right reasons
- Without per-event charts, parameter changes are optimizing into a black box

#### Standard chart format

Every per-event chart is a **standalone Plotly HTML file** with a **multi-panel layout**, shared x-axis, vertical shading for Regime windows:

| Panel                        | Content                                                                                 | Always required |
| ---------------------------- | --------------------------------------------------------------------------------------- | --------------- |
| 1 — Price                    | 10s candlesticks + entry markers (green ▲) + exit markers (green ▼ = win, red ▼ = loss) | Yes             |
| 2+ — Indicators and features | show values over time, thresholds, regimes etc.                                         | Yes             |

Panel 2+ content adapts per phase.

#### Index file

Every phase must also produce a **sortable HTML index** at `results/phase_{x}/event_charts/index.html`.

The index must be sortable by: ticker, date, session, n_trades, n_reentries (if applicable), event_pf.\
Each row links to the individual event chart.

**The index always covers every event in the sample, with no exceptions.** Chart coverage may be sampled (see below); index coverage may not.

#### Output path convention

```
results/phase_{x}/event_charts/{TICKER}_{DATE}.html   ← one per event
results/phase_{x}/event_charts/index.html              ← sortable index
```

#### Chart task template

Add this task to every phase prompt that runs a backtest:

```
- [ ] **T[N] — Per-event charts**
  Produce one 4-panel Plotly HTML chart per traded event using the standard panel layout
  defined in Agent_Prompt_Standard.md §7. Write to `results/phase_{x}/event_charts/`.
  Adapt Panel 3 to [phase-specific signal or re-entry if active].

  - [ ] T[N]a — Charts written for all [N] events with trades
  - [ ] T[N]b — Sortable index written to `results/phase_{x}/event_charts/index.html`
```

> **Sampling:** [Cooper to fill in — samples ≤ N events get full chart coverage; above that, define the stratification rule here. Index coverage stays complete either way.]

---

### 8\. Approval Gate

Placement note: this stays the final line of every prompt. Sections 9–12 below are contract sections that appear before it.

```
## Approval Gate

Do not begin Phase [X+1] or any follow-on work until Cooper has reviewed results and given explicit approval.
```

---

### 9\. Chart Contract

**Mandatory for every phase, including analysis-only phases.** §7 covers per-event charts for backtest phases; this section covers everything else. An audit or measurement phase produces no trades and is the phase where seeing the data matters most — exempting it from charts is backwards.

Every chart is specified **in the prompt, before any code runs**. Charts are a deliverable spec, not something the agent invents at the end.

Each chart in the contract gets five fields:

| Field | Meaning |
| --- | --- |
| **Filename** | `results/phase_{x}/charts/NN_name.html` |
| **Question** | The single question this chart answers |
| **Encoding** | x, y, color, facet, marks |
| **n annotation** | Where per-bucket n appears on the chart — required, not optional |
| **Failure appearance** | What this chart looks like if the hypothesis is wrong |

The last field is the important one. It's the visual version of "if the failure mode can't be written down, the hypothesis isn't ready." It also stops the agent from producing a chart that can only look like success.

#### Standard chart rules

These apply to every chart in the project and don't need restating per phase:

- Plotly, standalone HTML, one chart per file
- **n annotated per bucket, always**
- **Show the distribution, not just the center** — violin, box, ECDF, or strip overlay. A bar chart of means is not an acceptable primary chart. If a bar-of-means is genuinely the clearest view, it ships *alongside* the distribution view, not instead of it.
- Raw scatter or strip overlay behind any aggregate wherever the point count permits; sub-sample the overlay if it doesn't, and say so in the caption
- No smoothing or interpolation unless the prompt asks for it
- Axes labeled with units. Log scale where the data is multiplicative (in this universe, it usually is)
- Outliers shown, never clipped. Zoom with a range slider, don't delete points.
- Every chart carries a caption stating: sample, filters applied, config hash

#### Chart contract template

```
## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|------|----------|----------|---------|--------------------------|
| 01 | `charts/01_spread_by_participation.html` | Does spread compress as participation rises? | x=participation decile, y=effective spread (log), violin + strip, n label per decile | Per-decile count above each violin | Violins overlap across deciles; no monotonic shift in medians |
```

---

### 10\. Verification Block

Every phase report includes, for every headline number:

- The exact SQL, or the script path + function, that produced it
- Row counts **in and out of every filter step**
- A one-line reproduction command
- The config hash

A number without a reproduction path is treated as not produced. This is the control that keeps reported metrics tied to code that actually ran.

```
## Verification

| Metric | Value | n | Source | Repro |
|--------|-------|---|--------|-------|
| Median burst spread | 0.0091 | 8,412 | `research/phase_5/spread.py:by_participation` | `python -m research.phase_5.run --config config/phase_5.json --step spread` |

**Filter waterfall:**
| Step | Rows in | Rows out | Dropped | Why |
|------|---------|----------|---------|-----|
```

---

### 11\. Digest Contract

`results/phase_{x}/digest.json` is the machine-readable return path — the only artifact that goes back into the strategy conversation. Everything else stays in the repo.

Cap it at ~100 lines. If it doesn't fit, the phase was scoped too large.

```json
{
  "phase": "5",
  "config_hash": "a3f9c21e",
  "status": "complete | escalated",
  "escalation": { "criterion": null, "observed": null },
  "headline_metrics": [
    { "name": "median_burst_spread", "value": 0.0091, "n": 8412,
      "source": "research/phase_5/spread.py:by_participation",
      "chart": "results/phase_5/charts/01_spread_by_participation.html" }
  ],
  "decisions_log": [
    { "decision": "aggressor classification method",
      "options_considered": ["quote rule", "tick rule", "Lee-Ready"],
      "chose": "Lee-Ready with tick-rule fallback",
      "why": "prompt specified Lee-Ready; fallback needed for 3.1% of prints with no prevailing quote" }
  ],
  "surprises": ["1,540 event folders have trades.parquet but no quotes.parquet"],
  "artifacts": ["results/phase_5/artifacts/spread_by_bucket.parquet"],
  "charts": ["results/phase_5/charts/01_spread_by_participation.html"],
  "commits": ["a1b2c3d", "d4e5f6a"],
  "reproduce": "python -m research.phase_5.run --config config/phase_5.json"
}
```

Field notes:

- **`headline_metrics[].chart` is required.** A metric with no chart violates the Evidence Standard and the digest is invalid.
- **`decisions_log`** captures implementation micro-decisions. Not for approval — so that when a number looks wrong six weeks later, the reason is written down.
- **`surprises`** is the one field where the agent may volunteer something nobody asked for. It's how undocumented data problems surface. An empty `surprises` array on a data-touching phase is itself worth a second look.

---

### 12\. Git Discipline

Commits are the audit trail. A phase that runs to completion and commits once at the end is unauditable — there's no way to see which change produced which number.

#### Rules

| Rule | Detail |
| --- | --- |
| **Branch per phase** | `phase/{x}`. Cut from main at phase start. Merged only at the approval gate. |
| **Prompt committed before the run** | `prompts/phase_{x}.md` lands on the branch as the first commit. The prompt is the spec; the commit is proof of what was actually asked. |
| **Config committed before the run that uses it** | No run against an uncommitted config. Config hash in the digest must resolve to a committed file. |
| **Commit at every task boundary** | One commit per T-number, minimum. `T3` done → commit. Not at phase end. |
| **Commit before every escalation** | Hard stop = commit current state first, then post. The failure must be reproducible from the tree. |
| **Commit before any long run** | Anything over ~10 minutes gets a commit first, so an interrupted run doesn't lose the code that produced the partial output. |
| **Never rewrite history** | No force push, no rebase of pushed work, no amending a commit that's already been reported in a digest. |
| **Tag at approval gates** | `phase-{x}-approved` on merge. That tag is the reproducible baseline the next phase cites. |
| **Working tree clean at phase end** | If `git status` isn't clean when the report posts, the report is incomplete. |

#### Commit message format

```
phase-{x} T{n}: {imperative summary}

{what changed, one or two lines}
{escalation status if relevant}
```

Examples:

```
phase-5 T2: add quote-quality characterization queries

Crossed/locked rate and stale-run length by event, dev tier only.
Full-tier run not yet executed.
```

```
phase-5 T4: ESCALATION — null_spread_pct 8.3% exceeds 5% threshold

State committed before hard stop. No fix attempted.
```

#### What gets committed vs. ignored

| Committed | Ignored (`.gitignore`) |
| --- | --- |
| `prompts/`, `config/`, `research/`, `src/` | `results/**/artifacts/*.parquet` |
| `results/phase_{x}/digest.json` | `results/phase_{x}/event_charts/` (thousands of multi-MB HTML files) |
| `results/phase_{x}/REPORT.md` | Anything under the data root |
| `results/phase_{x}/charts/` (analysis charts — bounded count) | DuckDB files |

Charts and artifacts are regenerable from a committed config + committed code. The digest and report are not — they're the record.

#### Standing task template

Add to every phase prompt:

```
- [ ] **T0 — Branch and commit prompt**
  Cut `phase/{x}` from main. Commit `prompts/phase_{x}.md` and `config/phase_{x}.json` before any other work.
```

---

## Anti-Patterns

These are things that have caused problems in past phases. Don't do them.

| Anti-pattern                                                      | Why it's a problem                                                                                        |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Claim stated with a mean and no distribution chart**            | **A mean is a distribution with the distribution deleted. Bimodality, outlier dominance, and thin buckets all vanish into it.** |
| **Summary statistic posted without n**                            | **Unreadable — a 40% rate on n=5 and on n=5,000 are different facts.**                                     |
| **Null result reported without a chart**                          | **Can't distinguish "no effect" from "no statistical power."**                                             |
| Agent resolves an escalation by tweaking a parameter              | Produces untracked changes; bypasses validation discipline                                                |
| Tasks that don't produce a verifiable artifact                    | No way to confirm the task was done correctly                                                             |
| Selection criterion not specified (e.g., "choose the best gamma") | Agent invents a criterion, which may not match project intent                                             |
| Output file table omitted                                         | Files end up in inconsistent locations across phases                                                      |
| Escalation criteria missing units or direction                    | Agent misinterprets (e.g., "PF fails" is ambiguous — is 1.52 a failure?)                                  |
| Per-event charts omitted                                          | No way to audit whether signal behavior is correct on individual events; aggregate metrics mask pathology |
| Panel 3 substitution undocumented                                 | Agent picks an arbitrary signal; chart meaning is ambiguous across phases                                 |
| Index file missing or incomplete                                  | Per-event charts exist but can't be navigated efficiently; incomplete index hides the events you didn't chart |
| Phase context duplicated in full from prior prompts               | Inflates token usage; key constraints get buried                                                          |
| Multiple simultaneous hard-stop conditions with no priority       | Agent doesn't know which to report first — table order is the priority order                              |
| **Chart contract omitted on an analysis-only phase**              | **The audit phases are exactly where the data needs looking at; "no trades" is not "no charts."**          |
| **Single commit at phase end**                                    | **Can't trace which change produced which number; an interrupted run loses everything.**                   |
| **Run executed against an uncommitted config**                    | **Config hash in the digest resolves to nothing; the result is unreproducible.**                           |
| **Agent recommends a next step**                                  | **Conclusions are Cooper's, drawn from charts. An agent recommendation is an interpretation smuggled in as a finding.** |

---

## Minimal Working Example

```markdown
## Phase J — Event-Level PnL Analysis

**Date:** 2026-04-12  
**Baseline:** Phase H H4 full val — 1,088 events, PF=1.5297, 160,710 trades  
**Objective:** Compute event-level PnL aggregates and identify the top/bottom decile drivers  
**Primary success metric:** Event-level summary file written with no missing events from H4

---

**Context:**
- Source: `results/phase_h/h4_full_val/event_level_summary.json` (1,088 events)
- Val sample: full 1,228-event split (this is a milestone analysis run)
- No parameter changes in this phase — analysis only
- Charts: Plotly interactive HTML, standalone files, one chart per file

---

## Tasks

- [ ] **T0 — Branch and commit prompt**  
  Cut `phase/j` from main. Commit `prompts/phase_j.md`. No config for this phase — analysis only; note that in the commit message.

- [ ] **T1 — Load and validate event-level summary**  
  Load `event_level_summary.json`. Confirm 1,088 events present. Log any events with null PnL.
  - [ ] T1a — If null PnL count > 10, escalate before proceeding
  - [ ] T1b — Commit

- [ ] **T2 — Compute decile breakdown**  
  Sort events by total_pnl_usd. Split into deciles. For each decile compute: mean PF, mean hold_sec, exit type distribution, mean S score. **Also compute and retain the full within-decile distribution of each — the decile table is a summary of the charts, not a replacement for them.**
  - [ ] T2a — Commit

- [ ] **T3 — Write charts per the Chart Contract below**  
  - [ ] T3a — `01_event_pnl_ranked.html`
  - [ ] T3b — `02_decile_feature_distributions.html`
  - [ ] T3c — Commit

- [ ] **T4 — Digest and report**  
  Write `digest.json` per §11 and `REPORT.md`. Every claim in REPORT.md cites its chart file.
  - [ ] T4a — Commit; confirm working tree clean

---

## Escalation Criteria

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Null PnL event count | > 10 | Hard stop — commit, post null count and example events, await instruction |
| Bottom decile mean PF | < 0.5 | Hard stop — commit, post decile table + distribution chart, await instruction |

---

## Output Files

| File | Description | Status |
|------|-------------|--------|
| `results/phase_j/event_decile_summary.json` | Per-decile feature aggregates | [ ] |
| `results/phase_j/charts/01_event_pnl_ranked.html` | Ranked event PnL bar chart | [ ] |
| `results/phase_j/charts/02_decile_feature_distributions.html` | Feature distributions by decile | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|------|----------|----------|---------|--------------------------|
| 01 | `charts/01_event_pnl_ranked.html` | Is PnL carried by a handful of events? | x=event rank, y=total_pnl_usd, bar; cumulative PnL line on secondary axis | n_events in title; n_trades in hover | Bars roughly even; cumulative line near-linear |
| 02 | `charts/02_decile_feature_distributions.html` | Do features separate top from bottom deciles? | facet per feature, x=decile, y=feature value, violin + strip | Per-decile count above each violin | Violins overlap across all deciles; no ordering in medians |

---

## Reporting

On completion, post:
1. Decile table: decile, n_events, mean_pnl_usd, **median_pnl_usd, IQR**, mean_pf, mean_hold_sec, dominant_exit_type
2. Escalation check table
3. Verification block (§10)
4. Output file table with status filled in
5. Commit list

Every claim cites its chart. No recommendations.

---

## Approval Gate

Do not begin Phase K or any follow-on work until Cooper has reviewed results and given explicit approval.
```

---

## Version History

| Version | Date       | Change                                                                                                              |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------- |
| 1.3     | 2026-07-14 | Added the Evidence Standard (no claim without a distribution chart, no statistic without n); §9 Chart Contract, mandatory on analysis-only phases; §10 Verification Block; §11 Digest Contract; §12 Git Discipline. Anti-pattern table extended. |
| 1.2     | 2026-07-14 | Cooper Manually edited this to make it abstractable to all momentum event research, not just specific straegy (epg) |
| 1.1     | 2026-05-10 | Added §7 Per-Event Charts as mandatory standard deliverable for all backtest phases                                 |
| 1.0     | 2026-04-11 | Initial standard                                                                                                    |
