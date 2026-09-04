<!-- fullWidth: false tocVisible: false tableWrap: true -->
# Agent Prompt Standard

**Version:** 1.4 (draft — supersedes 1.3 pending your review)
**Project:** Momentum Event Research — Mom_db

This document defines the standard structure for all Claude Code agent prompts in this project. Every phase prompt must follow this format. Deviations require explicit justification in the prompt itself.

---

## Changelog from v1.3

Three changes, discussed 2026-08-31, aimed at cutting round-trips between you and the agent without weakening the evidence trail:

1. **New §3 — Plan Authorship.** Phase prompts state the goal, constraints, escalation criteria, and chart contract; the agent drafts its own task breakdown against them and gets one plan-approval before executing, instead of you writing the T1/T2/T3 list yourself. (Old §3 "Task Checklist" is now §3b — the *format* rules for the resulting plan are unchanged, only *who writes it* changes.)
2. **§5 Escalation Criteria (renumbered from §4) is now two-tier.** Every condition is tagged `HARD STOP` or `LOG`, decided by you up front when the prompt is written — not improvised by the agent mid-run. `LOG` conditions no longer interrupt.
3. **§9 Approval Gate (renumbered from §8) defaults to async.** A phase with `Gate Mode: async` auto-continues into the next approved phase when every `HARD STOP` criterion passes; you review the digest and charts after the fact instead of blocking the run. `Gate Mode: sync-required` keeps the old behavior for phases you flag as needing a live decision before anything continues.

Everything else — the Evidence Standard, Chart Contract, Verification Block, Digest Contract, Git Discipline, and the "agent never recommends" rule — is unchanged. This draft is not yet applied; it's here for you to mark up or approve.

---

## Why This Exists

Agent prompts have grown organically across phases. Inconsistent structure causes three problems:

1. Agents make judgment calls they shouldn't (self-resolve vs. escalate)
2. Results are hard to audit because output contracts vary phase to phase
3. Claims arrive without the evidence needed to check them

This standard fixes all three. Nothing in v1.4 relaxes any of it — the changes are about *who plans the work* and *which decisions block on you live*, never about *what counts as evidence* or *whether the agent gets to interpret a result*.

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

**This line does not move in v1.4.** Plan authorship (§3) is about task sequencing, not about results. Async gating (§9) is about when you look, not whether you look. Neither one gives the agent a way to decide what a result *means* — that still requires you.

---

## Prompt Structure

Every agent prompt has these thirteen sections, in this order.

---

### 1. Header Block

One paragraph. Covers: what phase this is, what the previous phase established, what this phase changes or validates, and the primary success metric. **New in v1.4:** also states the gate mode for this phase.

```
## Phase [X] — [Short Name]

**Date:** YYYY-MM-DD
**Baseline:** [Prior phase] — [val sample], PF=[X.XXXX], [N] trades
**Objective:** [One sentence — what this phase accomplishes]
**Primary success metric:** [e.g., PF > 1.53 on 100-event val sample, seed=42]
**Gate Mode:** async | sync-required   ← see §9
```

Keep it tight. If the agent needs more context, link to the relevant result file — don't inline it.

---

### 2. Context & Constraints

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

### 3. Plan Authorship — **NEW in v1.4**

This is the section that changes who writes the task list.

A v1.4 prompt does not hand the agent a pre-written T1/T2/T3 breakdown. It hands the agent everything it needs to write one itself:

- The objective and primary success metric (§1)
- The operating constraints (§2)
- The full Escalation Criteria table (§5), already tiered `HARD STOP` / `LOG`
- The Chart Contract (§10) and, if applicable, the Per-Event Chart requirement (§8)
- The Output File Contract (§6) — the *what*, not the *how*

The agent's first deliverable is a plan, not code: a task breakdown in the §3b format (below), covering how it intends to reach the objective within the stated constraints, which tasks it believes can run `[PARALLEL OK]` as subagents, and where it expects to need a decision criterion it doesn't already have. **Post the plan and stop. Do not begin implementation until Cooper approves the plan.**

This is one round-trip per phase, not one per task. Once the plan is approved, the agent executes it against the same rules as before — each task still ends in a commit, the escalation table still governs when it must stop, and it still isn't allowed to deviate from the approved plan's scope without flagging the deviation and why.

If a phase is small enough, or Cooper already knows exactly how it should be broken down, Cooper may skip plan authorship and hand the agent a pre-written task list directly — in that case this section is simply omitted from the prompt and execution starts at §3b's format with the tasks already filled in. Either way, the *plan itself*, once it exists, follows §3b's rules.

#### 3b. Task Checklist Format

A numbered checkbox list. Each item is a discrete, verifiable unit of work — whether written by Cooper or, per §3, proposed by the agent and approved by Cooper.

Rules:

- Tasks are sequential unless explicitly marked `[PARALLEL OK]`
- Each task produces a concrete artifact (file, metric, log line) — no open-ended tasks
- If a task requires a decision (e.g., parameter selection), state the selection criterion explicitly so the agent doesn't invent one
- Break compound tasks into sub-tasks with indented checkboxes
- **Each task ends with a commit** (§13)
- **New in v1.4:** any `[PARALLEL OK]` group of independent, non-judgment tasks (per-event chart rendering is the standard case — see §8) should be dispatched as subagents rather than run inline in the root agent's context. This is an execution detail, not a plan-approval item — Cooper doesn't need to bless it separately.

```
## Tasks

- [ ] **T1 — [Short label]**
  [What to do. What file to write. What criterion to use if a choice is involved.]

  - [ ] T1a — [Sub-task if needed]
  - [ ] T1b — [Sub-task if needed]

- [ ] **T2 — [Short label]** [PARALLEL OK]
  [Same pattern. Note if this is meant to fan out across subagents.]
```

---

### 4. (removed — merged into §3/§3b above)

---

### 5. Escalation Criteria — **two-tier in v1.4**

An explicit table. The agent checks every row after each task that could trigger one. **Every row now carries a tier**, decided by Cooper when the prompt is written:

- **`HARD STOP`** — unchanged from v1.3. Commit the current state, post results, explain which criterion was triggered and the observed value, and wait. The agent does not attempt to fix the problem or move to the next task. In `sync-required` gate mode this always blocks; in `async` gate mode this is the one thing that still blocks even though the gate is otherwise async (see §9).
- **`LOG`** — new. The agent records the condition and observed value in the `surprises` field of `digest.json` (§12) and continues. It does **not** stop, and it does **not** act on it — no parameter tweak, no re-run, no interpretation. A `LOG` row exists so you see it in the digest, not so the agent can decide what it means.

```
## Escalation Criteria

Stop and post results only for HARD STOP rows. LOG rows continue and are recorded in digest.json.

| # | Condition | Threshold | Tier | Action |
|---|-----------|-----------|------|--------|
| 1 | [Metric] [comparison] [value] | e.g., PF < 1.30 | HARD STOP | Commit, post results, await instruction |
| 2 | [Metric] [comparison] [value] | e.g., null_spread_pct > 5% | HARD STOP | Commit, post results, await instruction |
| 3 | [Condition] | e.g., per-bucket n < 50 in a non-headline bucket | LOG | Continue; note in `surprises` |
```

**Every condition needs an explicit tier — there is no default.** A row with no tier is treated as `HARD STOP`; that's the fail-safe direction, not a shortcut for skipping the decision. Deciding the tier for each row is Cooper's job at prompt-writing time (or during plan approval, §3), precisely so the agent is never the one deciding, mid-run, whether something is worth interrupting you for.

If multiple `HARD STOP` criteria trigger at once, report **in table order** — the table is the priority order. `LOG` rows never take priority over a `HARD STOP` — a `HARD STOP` always halts regardless of how many `LOG` conditions also fired.

If no escalation criteria apply to a task, state that explicitly: `No escalation criteria for this task.`

---

### 6. Output File Contract

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

- Every output file must be listed before the agent starts (or, under §3 plan authorship, before the plan is approved)
- If a file is conditional (e.g., only written on escalation), note that in the description
- The agent must not write files to locations not listed here without posting to chat first
- `digest.json` and `REPORT.md` are implicit on every phase — no need to list them

---

### 7. Reporting Format

Tells the agent exactly what to post when the phase is complete (or when escalating).

```
## Reporting

On completion, post:
1. Comparison table: [prior baseline] vs. Phase [X] — columns: [list the metrics]
2. Exit breakdown table: count and % for each exit type
3. Escalation check table: each criterion, tier, observed value, pass/fail
4. Walk-forward table if applicable
5. Output file table with final status column filled in
6. [Any phase-specific charts or summaries]

On HARD STOP escalation, post:
1. Which criterion triggered and the observed value
2. The metrics table up to the point of failure
3. No recommendations — present data only
```

**Every posted table carries n per row.** Every claim in prose carries the chart filename that supports it. A report that states a finding with no chart reference is incomplete and gets sent back.

---

### 8. Per-Event Charts

**This section is mandatory for every phase that produces trade records.** Analysis-only phases (no backtest run) are exempt from *per-event* charts but are **not** exempt from §10 — they still have a chart contract.

Per-event charts are the primary tool for keeping the strategy auditable. They turn backtest output into something that can be read and inspected, not just measured.

#### Why this is required

- Aggregate metrics (PF, win rate) can mask event-level pathology — a handful of outlier events can carry or drag the whole sample
- Signal behavior on individual events reveals whether exits, entries, and gates are firing for the right reasons
- Without per-event charts, parameter changes are optimizing into a black box

#### Standard chart format

Every per-event chart is a **standalone Plotly HTML file** with a **multi-panel layout**, shared x-axis, vertical shading for Regime windows:

| Panel | Content | Always required |
| --- | --- | --- |
| 1 — Price | 10s candlesticks + entry markers (green ▲) + exit markers (green ▼ = win, red ▼ = loss) | Yes |
| 2+ — Indicators and features | show values over time, thresholds, regimes etc. | Yes |

Panel 2+ content adapts per phase.

**New in v1.4:** per-event chart generation is the standard case for `[PARALLEL OK]` subagent dispatch (§3b). With potentially hundreds of events per phase, rendering them inline in the root agent's context burns tokens it needs for the report and escalation checks — fan them out.

#### Index file

Every phase must also produce a **sortable HTML index** at `results/phase_{x}/event_charts/index.html`.

The index must be sortable by: ticker, date, session, n_trades, n_reentries (if applicable), event_pf.
Each row links to the individual event chart.

**The index always covers every event in the sample, with no exceptions.** Chart coverage may be sampled (see below); index coverage may not.

#### Output path convention

```
results/phase_{x}/event_charts/{TICKER}_{DATE}.html   ← one per event
results/phase_{x}/event_charts/index.html              ← sortable index
```

#### Chart task template

Add this task to every phase prompt (or agent-authored plan, §3) that runs a backtest:

```
- [ ] **T[N] — Per-event charts** [PARALLEL OK]
  Produce one 4-panel Plotly HTML chart per traded event using the standard panel layout
  defined in Agent_Prompt_Standard.md §8. Write to `results/phase_{x}/event_charts/`.
  Adapt Panel 3 to [phase-specific signal or re-entry if active]. Dispatch as subagents.

  - [ ] T[N]a — Charts written for all [N] events with trades
  - [ ] T[N]b — Sortable index written to `results/phase_{x}/event_charts/index.html`
```

> **Sampling:** [Cooper to fill in — samples ≤ N events get full chart coverage; above that, define the stratification rule here. Index coverage stays complete either way.]

---

### 9. Approval Gate — **async-by-default in v1.4**

Placement note: this stays the final line of every prompt. Sections 10–13 below are contract sections that appear before it.

Every phase declares its gate mode in the Header Block (§1):

- **`Gate Mode: async`** — the default. If the phase completes with every `HARD STOP` criterion passed, the agent commits, posts the digest and charts, and **proceeds directly into the next already-approved phase in the plan** without waiting for Cooper to respond live. Cooper reviews the digest and charts whenever he gets to them; if something looks wrong on review, the fix is the same as always — a new prompt, on a new branch, that starts from the last good commit. Async mode requires that the next phase already has an approved plan (§3) to proceed into; if it doesn't, the agent stops and waits regardless of gate mode, because there's nothing approved to run.
- **`Gate Mode: sync-required`** — the v1.3 behavior. The agent stops after this phase no matter what the results show, and waits for Cooper's explicit review and approval before anything else happens. Use this for phases where a bad call is expensive or hard to reverse: anything touching capital allocation, anything that's the last phase before a walk-forward or out-of-sample test, anything Cooper flags for any other reason when writing the prompt.

**A `HARD STOP` always blocks, in either gate mode.** Async only removes the wait when nothing tripped a hard stop — it never removes the wait when something did.

```
## Approval Gate

Gate Mode: [async | sync-required]

async: If all HARD STOP criteria pass, proceed into the next approved phase.
  Post digest and charts for review; do not wait for a response to continue.
sync-required: Do not begin Phase [X+1] or any follow-on work until Cooper
  has reviewed results and given explicit approval.
```

---

### 10. Chart Contract

**Mandatory for every phase, including analysis-only phases.** §8 covers per-event charts for backtest phases; this section covers everything else. An audit or measurement phase produces no trades and is the phase where seeing the data matters most — exempting it from charts is backwards.

Every chart is specified **in the prompt, before any code runs** — or, under §3 plan authorship, in the approved plan before implementation starts. Charts are a deliverable spec, not something the agent invents at the end.

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

### 11. Verification Block

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

### 12. Digest Contract

`results/phase_{x}/digest.json` is the machine-readable return path — the only artifact that goes back into the strategy conversation. Everything else stays in the repo.

Cap it at ~100 lines. If it doesn't fit, the phase was scoped too large.

```json
{
  "phase": "5",
  "config_hash": "a3f9c21e",
  "status": "complete | escalated",
  "gate_mode": "async | sync-required",
  "escalation": { "criterion": null, "observed": null, "tier": null },
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
  "surprises": ["1,540 event folders have trades.parquet but no quotes.parquet", "LOG: per-bucket n < 50 in bucket 7 (see escalation #3)"],
  "artifacts": [
    { "path": "results/phase_5/artifacts/spread_by_bucket.parquet",
      "sha256": "9f2c…", "size_bytes": 918251 }
  ],
  "charts": ["results/phase_5/charts/01_spread_by_participation.html"],
  "commits": ["a1b2c3d", "d4e5f6a"],
  "reproduce": "python -m research.phase_5.run --config config/phase_5.json"
}
```

Field notes:

- **`headline_metrics[].chart` is required.** A metric with no chart violates the Evidence Standard and the digest is invalid.
- **Run the check that can come back against you, before the conclusion is committed to.**
  *(Added to the v1.4 draft 2026-09-02, at Cooper's direction.)* Pre-register the criterion, keep the
  check **cheaper than the thing it gates**, and run it **before** acting on the claim it tests — and
  design it so a negative result is a real possible outcome. Three instances in one stretch, each of
  which changed what was written: the driftless null's own expiry diagnostic caught a Parkinson
  miscalibration **before** "drift in 30 of 30 cells" was recorded; the T0d satisfiability audit caught
  three unsatisfiable escalation rows **before** the phase started, one of which would have fired on
  the phase's own tasks; and a free horizon re-cut **refuted the argument for spending a tick pass**
  that had just been made for it. The transferable part is not the checks but their shape: **the
  cheapest way to be wrong less often is to spend minutes testing your own claim before spending a
  day acting on it.**
- **Every list has one home.** *(Added to the v1.4 draft 2026-08-31, at Cooper's direction.)* An
  escalation row, a prompt, or a doc that needs a list **references the file that holds it**. No row
  restates a list that exists in config, and no doc restates a list a script can generate. **Four
  lists in this programme have drifted from their source** — the decision-pointer index in
  `CLAUDE.md` (near-collision at D20, real collision at D23), the `D:\` hardcode enumeration (11
  listed against 24 live, 7 of them writing to D:), the commit staging scope (`git add -A` swept an
  uncommitted human draft into an unrelated commit), and Phase 10e escalation row 20, whose inline
  path list was narrower than `config.write_allowlist` and than the phase's own Output Files table —
  so the phase could not have completed T8b without firing its own row. A restated list is a second
  source of truth, and the second one is always the stale one.
- **`artifacts[]` entries carry `sha256` and `size_bytes`, not just a path.** *(Added to the v1.4 draft 2026-08-31, at Cooper's direction, by the session that hit the gap.)* Parquet artifacts are gitignored under the standing regenerable-artifact rule, so **a path alone leaves no record of what the file contained when the phase was approved.** Phase 10e's escalation row 1a — "any frozen input differs in content hash from its state at `phase-11-approved`" — turned out to be **unsatisfiable for exactly this reason**: the `phase_8`, `phase_9` and `phase_11` digests record `config_hash` and artifact paths only, so the tag-period state was never captured and cannot be reconstructed. With this field, any future phase can verify a frozen input against the digest of the phase that produced it. The forward baseline at `results/phase_10e/artifacts/frozen_baseline.json` is the local patch; **this is the durable fix.**
- **`decisions_log`** captures implementation micro-decisions. Not for approval — so that when a number looks wrong six weeks later, the reason is written down.
- **`surprises`** is the one field where the agent may volunteer something nobody asked for. It's how undocumented data problems surface, and, as of v1.4, where every `LOG`-tier escalation lands. An empty `surprises` array on a data-touching phase is itself worth a second look.
- **`gate_mode`** and **`escalation.tier`** are new in v1.4 — they make it possible to tell, from the digest alone, whether a phase auto-continued and whether anything that fired was a `HARD STOP` or a `LOG`.

---

### 13. Git Discipline

Commits are the audit trail. A phase that runs to completion and commits once at the end is unauditable — there's no way to see which change produced which number.

#### Rules

| Rule | Detail |
| --- | --- |
| **Branch per phase** | `phase/{x}`. Cut from main at phase start. Merged only at the approval gate. |
| **Prompt committed before the run** | `prompts/phase_{x}.md` lands on the branch as the first commit. Under §3 plan authorship, the *approved plan* is committed alongside it before implementation starts. The prompt (and plan) is the spec; the commit is proof of what was actually asked and agreed. |
| **Config committed before the run that uses it** | No run against an uncommitted config. Config hash in the digest must resolve to a committed file. |
| **Commit at every task boundary** | One commit per T-number, minimum. `T3` done → commit. Not at phase end. |
| **Commit before every `HARD STOP` escalation** | Hard stop = commit current state first, then post. The failure must be reproducible from the tree. |
| **Commit before any long run** | Anything over ~10 minutes gets a commit first, so an interrupted run doesn't lose the code that produced the partial output. |
| **Bisect a regression, don't eyeball it** | If a headline metric regresses between phases with no expected cause, use `git bisect` against the phase's own reproduce command to isolate the exact commit, rather than manually diffing. |

---

## Anti-patterns — things this standard exists to prevent

| Anti-pattern | Why it's a problem |
| --- | --- |
| A mean reported with no distribution chart | Bimodality, outlier dominance, and thin buckets all vanish into it. |
| Summary statistic posted without n | Unreadable — a 40% rate on n=5 and on n=5,000 are different facts. |
| Null result reported without a chart | Can't distinguish "no effect" from "no statistical power." |
| Agent resolves an escalation by tweaking a parameter | Produces untracked changes; bypasses validation discipline — **this is what `HARD STOP` exists to prevent, and it applies exactly as much under async gating as it ever did.** |
| Tasks that don't produce a verifiable artifact | No way to confirm the task was done correctly |
| Selection criterion not specified (e.g., "choose the best gamma") | Agent invents a criterion, which may not match project intent |
| Output file table omitted | Files end up in inconsistent locations across phases |
| Escalation criteria missing units, direction, **or tier** | Agent misinterprets (e.g., "PF fails" is ambiguous — is 1.52 a failure?), or a condition silently defaults to `HARD STOP` when it should have been `LOG` — a decision made by default instead of by Cooper |
| Per-event charts omitted | No way to audit whether signal behavior is correct on individual events; aggregate metrics mask pathology |
| Panel 3 substitution undocumented | Agent picks an arbitrary signal; chart meaning is ambiguous across phases |
| Index file missing or incomplete | Per-event charts exist but can't be navigated efficiently; incomplete index hides the events you didn't chart |
| Phase context duplicated in full from prior prompts | Inflates token usage; key constraints get buried |
| Multiple simultaneous hard-stop conditions with no priority | Agent doesn't know which to report first — table order is the priority order |
| Chart contract omitted on an analysis-only phase | The audit phases are exactly where the data needs looking at; "no trades" is not "no charts." |
| Single commit at phase end | Can't trace which change produced which number; an interrupted run loses everything. |
| Run executed against an uncommitted config | Config hash in the digest resolves to nothing; the result is unreproducible. |
| Agent recommends a next step | Conclusions are Cooper's, drawn from charts. An agent recommendation is an interpretation smuggled in as a finding. |
| **Agent begins implementation before its plan (§3) is approved** | The one round-trip §3 exists to guarantee gets skipped, and scope drifts without Cooper having agreed to it |
| **Phase set to `async` gate mode with no `HARD STOP` rows at all** | An async phase with nothing that can stop it isn't async, it's unsupervised — every phase needs at least one row that actually blocks |
