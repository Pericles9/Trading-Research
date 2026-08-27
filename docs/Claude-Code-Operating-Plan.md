---
tags:
  - type/process-spec
  - domain/workflow
  - project/src-core
  - status/draft
created: 2026-07-14
---

# Claude Code Operating Plan

**How architecture decisions in this project become executed, auditable work in the repo — with zero code written by hand and zero conclusions drawn by the agent.**

---

## 0. The Split

Three roles. Keep them separate or the whole thing degrades into one blurry conversation where nobody knows who decided what.

| Role | Who | Owns | Never does |
|---|---|---|---|
| **Architect** | This project (chat) | Strategy, phase design, hypothesis specs, escalation thresholds, chart specs, prompt drafting | Runs code. Sees raw data. Invents numbers. |
| **Executor** | Claude Code | Reads data, writes code, runs it, produces artifacts + charts, reports measurements | Interprets results. Recommends next steps. Changes parameters to fix a failure. |
| **Decider** | Cooper | Reads charts and digests, draws conclusions, approves gates, sets direction | — |

The load-bearing rule: **Claude Code reports what it measured, not what it means.**

### 0.1 An honest caveat on "no conclusions"

You cannot remove all judgment from the executor — it makes hundreds of micro-decisions (how to window a rolling calc, how to handle a null, which join key to use). Trying to ban judgment produces an agent that either stalls or hides the calls it made.

The workable version is a distinction, not a ban:

- **Measurement** — "spread median in burst buckets is 0.9%, in quiet buckets 3.4%, n=8,412 / 61,003." → Executor's job. Required.
- **Description** — "the burst bucket median is lower across all deciles; the relationship is monotonic." → Executor's job. Allowed, because it's checkable against the chart.
- **Interpretation** — "this confirms spread compression, so we should proceed to the detector." → Yours. Banned in agent output.

Every implementation micro-decision the executor makes goes in a **Decisions Log** section of its report (see §4.3). Not so you approve each one — so that when a number looks wrong six weeks later, the reason is written down.

---

## 1. The Loop

One phase = one full turn of this loop. Never overlap phases.

```
[1] Chat: design phase        → hypothesis spec, chart spec, escalation thresholds
[2] Chat: draft agent prompt  → Agent_Prompt_Standard.md format, saved to prompts/
[3] You: paste into Claude Code (fresh session, plan mode first)
[4] Code: executes tasks      → artifacts, charts, digest.json, REPORT.md
[5] You: read charts          → draw conclusions
[6] Chat: paste digest.json + your read → decide next phase / revise / kill
[7] Approval gate             → back to [1]
```

Two things make or break this loop:

**Prompts are files, not chat messages.** Every prompt gets written to `prompts/phase_{x}.md` in the repo and committed. The prompt is the spec; the commit is the audit trail. If a phase gets re-run, you re-run the file, not your memory of what you typed.

**The digest is the return path.** Claude Code produces gigabytes of parquet and hundreds of HTML charts. None of that comes back into chat. What comes back is a single small `digest.json` plus your own read of the charts. This is non-negotiable — if you start pasting raw output into chat, context fills with noise and the architecture conversation degrades.

---

## 2. Repo Scaffolding (Phase 0 setup, do once)

### 2.1 `CLAUDE.md` at repo root

This is the standing constraint layer. It gets loaded into every Claude Code session automatically, which means **phase prompts stop repeating it** — directly killing the "phase context duplicated in full" anti-pattern.

Contents:

- **Hard data rules:** Never write to D: (confirmed failing hardware). Data root `E:\Trading Research\data`. DuckDB at `E:\Trading Research\data\duckdb\main.duckdb`. Env override precedence per `src/data/paths.py`.
- **Provenance quarantine (§2.6 of the research program):** `filtered/` and `momentum_events` are Confirmed → primary surface. `daily/`, `minute/`, `second10/`, `quote_data/` are Inferred → baselines and reconciliation only, never headline results, until §2.5 passes. `trade_data/` is Unknown → do not touch, ever, without explicit instruction.
- **Standing methodology:** event-study before backtest. Effective spread, not quoted. Always cross the spread. Halts = forced hold. Lag every feature by realistic pipeline latency. Ticker-blocked splits. Time-based splits, never random.
- **Code layout:** exploratory code in `research/`, promoted code only in `src/`. Deterministic, config-driven, versioned outputs keyed by config hash.
- **Reporting:** never post a number without n. Never post a metric without the code path that produced it.
- **The escalation rule:** hard stop means stop. Do not fix. Do not tune. Do not proceed.
- **Pointer:** "All phase prompts follow `docs/Agent_Prompt_Standard.md`. All strategy context lives in `docs/Mom-DB-Strategy-Research-Program.md`. Read the referenced section, not the whole doc."

Keep CLAUDE.md under ~150 lines. It's a constraint sheet, not a second copy of the research program.

### 2.2 Directory contract

```
prompts/phase_{x}.md              ← the prompt, committed before the run
config/phase_{x}.json             ← every tunable, no magic numbers in code
research/phase_{x}/               ← exploratory scripts
src/                              ← promoted code only
results/phase_{x}/
├── digest.json                   ← the ONLY thing that returns to chat
├── REPORT.md                     ← agent's written report
├── charts/                       ← analysis charts
├── event_charts/                 ← per-event charts + index.html (§7 of standard)
└── artifacts/                    ← parquet outputs
```

### 2.3 Custom slash commands (optional, high value)

Wire `.claude/commands/` for the things you'll do every phase:

- `/verify` — re-run the reproduction commands in digest.json and diff the numbers
- `/digest` — regenerate digest.json from artifacts
- `/gate` — print the escalation check table

---

## 3. Additions to `Agent_Prompt_Standard.md`

The standard is good. It was written for backtest phases and needs three additions to carry pure-measurement phases and to close the trust gap.

### 3.1 New §9 — Chart Contract

§7 covers per-event charts for backtest phases. Measurement and audit phases produce no trades and are currently exempt, which is exactly backwards — **the audit phase is where you most need to see the data**.

Add: every phase, backtest or not, specifies its charts **in the prompt, before code runs**. Each chart gets:

| Field | Meaning |
|---|---|
| Filename | `results/phase_{x}/charts/NN_name.html` |
| Question | The one question this chart answers |
| Encoding | x, y, color, facet, marks |
| Sample size annotation | Required — n visible on the chart, per bucket |
| Failure appearance | What this chart looks like if the hypothesis is wrong |

That last row is the important one. It's §7.4 of the research program ("if the failure mode can't be written down, the hypothesis isn't ready") applied to visuals. It also stops the agent from producing a chart that can only look like success.

Standing chart rules for CLAUDE.md:
- Plotly, standalone HTML, one chart per file
- n annotated per bucket, always
- No smoothing/interpolation unless the prompt asks for it
- Axes labeled with units; log scale where the data is multiplicative (it usually is here)
- Raw scatter or strip overlay behind any aggregate, wherever the point count permits

### 3.2 New §10 — Verification Block

Every phase report includes, for every headline number:

- The exact SQL or the script path + function that produced it
- Row counts in and out of every filter step
- A one-line reproduction command
- The config hash

This is the anti-hallucination control. A number without a reproduction path is treated as not produced.

### 3.3 New §11 — Digest Contract

The machine-readable return path. Small enough to paste into chat whole.

```json
{
  "phase": "1",
  "config_hash": "a3f9...",
  "status": "complete | escalated",
  "escalation": { "criterion": null, "observed": null },
  "headline_metrics": [
    { "name": "...", "value": 0.0, "n": 0, "source": "research/phase_1/x.py:fn" }
  ],
  "decisions_log": [
    { "decision": "...", "options_considered": ["..."], "chose": "...", "why": "..." }
  ],
  "surprises": ["things the agent did not expect and did not resolve"],
  "artifacts": ["results/phase_1/artifacts/..."],
  "charts": ["results/phase_1/charts/01_....html"],
  "reproduce": "python -m research.phase_1.run --config config/phase_1.json"
}
```

Cap it at ~100 lines. If it doesn't fit, the phase was too big.

**`surprises` is the most valuable field.** It's the one place the agent is permitted to volunteer something you didn't ask for, and it's how you find out about the data problem nobody specced a task for.

---

## 4. Rules of Engagement for Claude Code

### 4.1 Session hygiene

- **One phase per session.** Fresh context. Never continue a phase in a context that's already handled a different one.
- **Plan mode first.** Every session opens with the agent reading the prompt and posting its plan. You approve the plan before it writes a line. This catches misread tasks for free.
- **No auto-approve on writes outside the Output File Contract.** The standard already says this; enforce it with permissions, not trust.
- **Compact is a smell.** If a phase needs context compaction, the phase was scoped too large. Split it.

### 4.2 What the agent may and may not decide

| May decide | Must escalate |
|---|---|
| Implementation approach (library, query structure, chunking) | Any parameter that changes a result (thresholds, windows, k, N) |
| How to handle a documented null/edge case | An undocumented data anomaly |
| Chart cosmetics within the standing rules | Chart encoding changes vs. the contract |
| Refactors inside `research/` | Anything touching `src/` mid-phase |

### 4.3 Banned outputs

- Recommendations of any kind
- "This suggests / confirms / indicates / therefore"
- Any parameter change made in response to a bad result
- Any number without an n
- Any chart not in the contract

Allowed and encouraged: descriptions of what's visible, monotonicity checks, sample counts, explicit "I don't know."

---

## 5. Scale Reality (read this before Phase 1)

`filtered_trades` is **4.9 billion rows**. `filtered_quotes` is **3.8 billion**. An agent iterating on a query against those tables at 5 minutes a pass will burn a day on a typo.

**Mandatory: two-tier execution.** Every phase runs in two stages, and the prompt says so explicitly:

1. **Dev tier** — a fixed sample of ~50 events, pinned by seed, materialized once into `filtered_trades_dev` / `filtered_quotes_dev`. All development and iteration happens here. Runtime target: under 60 seconds per pass.
2. **Full tier** — one run against the full table, after dev-tier output is reviewed and the config is frozen.

The dev sample is built **once, in Phase 0**, and never changes. If it changes, every cross-phase comparison silently breaks.

Second constraint: the agent must default to **DuckDB SQL over pandas**. Pulling 4.9B rows into a dataframe on 32GB is not a mistake it should be allowed to make twice.

---

## 6. Phase Map

Mapped to §9 of the research program. Each row is one prompt, one session, one gate.

| Phase | Name | Produces | Charts | Gate |
|---|---|---|---|---|
| **0** | Repo + harness setup | CLAUDE.md, dir contract, digest tooling, **dev sample**, missing table loads | none | Dev sample reproduces; digest tooling round-trips |
| **1** | Filter forensics | Plain-language spec of `filter_events_power_law.py`: regressor, `momentum_pct` definition, fitted boundary | Boundary plot; `momentum_pct` histogram | You understand the universe definition |
| **2** | Event universe stats | Event count, date range, ticker count, repeat-ticker frequency | Repeat-ticker distribution; events over time | Effective sample size known |
| **3** | Columns + timestamps | Column inventory; condition codes present y/n; venue codes; timestamp semantics + precision + monotonicity | Inter-quote interval distributions | Tick data declared trustworthy or not |
| **4** | Coverage + integrity | Both-direction join rates; 7-session completeness matrix; **the trades/quotes folder gap**; session boundary validation | Coverage heatmap; missing-session-by-offset bars | Orphans and gaps quantified |
| **5** | Quote quality | Crossed/locked rates and burst clustering; stale-quote run lengths; quote-to-trade ratios; spread distributions event day vs. T-3 | Spread violin by day offset; stale-run CDF; crossed-market time series | BBO-derived features declared usable or not |
| **6** | Cross-resolution reconciliation | Diffs vs. `second10_bars` / `minute_bars` / `daily_bars` on overlapping symbol-days | Diff distributions; outlier symbol-days | Inferred data promoted or stays quarantined |
| **7** | **Audit report** | The §2.7 deliverable, assembled | Index of all prior charts | **Program gate. No alpha work before this.** |
| **8** | Event-study grid — forward markouts from tradeable anchors | *(executed)* Markout grid over all D1 events from anchors knowable in real time, bucketed by participation, with survivorship and coverage reported alongside; zero full-table passes | Markout heatmaps; participation buckets | **`phase-8-approved`**, 2026-08-01 |
| **9** | Path shape, cross-session integrity, clustered inference | *(executed, unmerged)* Cross-session corporate-action flag; separation of the detection-time / holding-period / latency axes; retracement ECDFs at T0…T+3 with ticker-clustered CIs | Retracement ECDFs; axis-separation grid | Branch `phase/9`, pending approval |
| **10** | Burst decomposition | Per-event burst segmentation; burst count, duration, spacing; fraction of session move carried per burst; burst-relative concentration curve | Burst count & duration distributions; per-burst move-share; burst-relative decay curve | **Burst timescale is a number.** Burst-relative latency budget replaces the session-anchored one | **CLOSED 2026-08-27 — D21. The sub-burst line (v4 → 10c → 10d → Diag1) is closed: 10d-R0 fired on Cooper's tape review, and the histogram is richly multimodal rather than bimodal, so there is no privileged valley to select. The burst timescale is NOT a number and the burst-relative latency budget never replaced the session-anchored one — D13 had already re-anchored the downstream. See results/d9_lineage_closeout/REPORT.md.**
| **10b** | Randomness of trade arrivals under a non-constant rate | Crossing timescale at which arrivals stop being explainable by an inhomogeneous Poisson process whose rate varies more slowly than that timescale, per detection segment; Allan factor against a matched null; time-rescaling under held-out intensity; synthetic-control validation | Allan vs. matched-null band; KS-vs-bandwidth; cross-method agreement | Crossing timescale is a number, or its absence is a recorded finding | **CLOSED 2026-08-13 — no burst timescale established; failed its own synthetic control gate, zero real events read. See results/phase_10b/REPORT.md.**
| **11** | Spread & impact by participation | Quoted vs. effective spread bucketed by participation rate; impact per unit signed volume, burst vs. quiet | Spread-vs-participation; impact curves | Compression claim tested; FP cost is a number |
| **12** | Halts & LULD | P(halt \| state); time-to-halt; reopen gap distribution, long-side conditional | Reopen gap distribution; halt timing | Sizing constraint is a number |
| **13** | Noise floor & tape characterization | Inter-trade interval distributions, print-size distributions, quote flicker rates — inside bursts vs. outside | Interval & size distributions by regime | Detector null distribution known |
| **14** | Signed flow & impact efficiency — feature layer | Lee-Ready aggressor classification; rolling signed volume; impact-efficiency derivative. Precomputed once, cached, lag-baked | Feature distributions | Features cached, not recomputed in loops |
| **15** | Burst hazard function | Duration distributions → P(death \| age); spread re-widening and intensity decay as covariates | Hazard curves by age; covariate-conditioned survival | **Exit prior is a number** |
| **16** | Regime labeling + stability | Offline labels; label-perturbation stability test (§5.1.1) | Label-set overlap under perturbation | Foundation solid, or sand |
| **17** | Detector + end-detector | Threshold+hysteresis baseline; CUSUM/BOCPD and intensity challengers; operating point by expected PnL; flanking-day FP estimation | Detection latency vs. FP; PnL at operating point | Both detectors exist; complexity earned or discarded |
| **18** | Direction signal | Features vs. cost-adjusted markouts within true-positive regimes, against the always-long-while-on null | Markout tables; monotonicity plots | "Detector + market order" vs. "detector + signal" — decided |
| **19** | Joint walk-forward | Full stack under the §7.2 cost model, halts as forced holds; vectorized first, Nautilus for the short list | Per-event charts (§7 of the standard) | — |
| **Opt-A** | T+1 markout grid (optional, long-only) | The single day-2 edge-existence pass retained under D5 | Markout heatmaps | Runs when Cooper calls for it; gates nothing |
| **Parallel** | Unconditional universe scan | Scope + feasibility; live-screen population vs. archive population | Population comparison | **Gates capital.** Cannot start last |

**Insert, 2026-08-27 — the scope of D21, stated so it is not over-read.** Row 10 is closed (see
its cell). **D21 closes one thing: deriving a boundary by selecting a trough from the
locally-normalized log-interval histogram. It blocks nothing.** No row in this map is blocked by
it, row 15 included.

*Corrected 2026-08-27, same day:* an earlier version of this insert said row 15 (*Burst hazard
function*) was "blocked on a successor object definition". **That was wrong and is withdrawn.**
Row 15 is open and unstarted, exactly as it was before D21. All D21 says about it is that the
histogram boundary-detection method is not available as a way to define its input; any other route
to a burst object, or any reformulation that does not need one, is untouched. Rows 13, 14, 16 and 17
are likewise unaffected — D13 re-anchored them to detection time, clock time or price-path events,
and that re-anchoring stands. Nothing is renumbered and no row is removed.

**Numbering, from 2026-08-03 onward.** Rows 8 and up are prompt filenames — row *n* is `prompts/phase_{n}.md`. Rows 0–7 are the original plan slots and are left untouched; they never tracked filenames, because the executed program inserted 0a/0b/0c/1b/1c/2b/5a and re-scoped several phases along the way. The crosswalk for the two plan rows that did get executed under different numbers: the old row 8 (*Measurement 1 — concentration*) ran as **Phase 6**, and the old row 12 (*Event-study grid — T+1*) ran as **Phase 8** in the re-scoped, tradeable-anchor form recorded above.

Ordering note *(superseded — retained for the record)*: **12 comes before the detector work**, deliberately. T+1 is the cleanest surface and the fastest read on whether there's anything here. If the markout grid is flat, you've saved six weeks of detector development.

**Superseded by D5, 2026-08-03.** D5 selects intraday post-trigger, long-only, burst-scale horizons as the program spine, which demotes T+1 from surface #1 to a single optional edge-existence pass (Opt-A) that gates nothing. The detector work is therefore no longer sequenced behind a T+1 grid; the burst-scale measurement chain (rows 10–15) precedes it instead, and the unconditional universe scan moves from "before capital" to a near-front blocker because under a gate-then-trade design the live false-positive rate is a direct PnL term. The six-weeks-saved argument above still holds on its own terms — D5 accepts that cost knowingly rather than disputing it.

---

## 7. Things I'd Push Back On

**The 12,100-event chart problem.** §7 of the standard bans sampled per-event charts. That's right for a 100-event val sample and unworkable at 12,100 — you will not read 12,100 charts, so a rule requiring them produces charts nobody looks at, which is worse than no rule. Suggested amendment: **all** charts for samples ≤ 200 events; above that, **stratified** charts (top/bottom PnL deciles + a seeded random draw + every escalation-triggering event) with the sortable index covering the full set. The index is what stays complete.

**`momentum_events` isn't loaded.** Per Schema.md, the E: DuckDB has exactly five tables and `momentum_events` isn't one of them. That's the spine of the whole archive and it's a hard blocker for Phase 2. It goes in Phase 0.

**24,200 trades files vs. 22,660 quotes files.** A 1,540-file gap, both "exact match" against source. That is not obviously benign — either ~1,540 event-folders have trades and no quotes, or the folder counts differ for a structural reason nobody has written down. Phase 4 owns it, and until it's explained, any quote-derived measurement has an unknown-size hole in its sample.

**"100% of the analysis" has a floor.** The agent can compute anything. It cannot tell you the q05 filter's regressor choice was a bad idea, or that the T+1 family is more honest than the intraday one. Those judgments come from here and from you. The plan holds only if you actually read the charts — if you start accepting the agent's REPORT.md narrative as the finding, you've rebuilt the exact black box §7 of the standard exists to prevent.

---

## 8. What to Do Next

1. Approve or amend the phase map (§6) and the three standard additions (§3).
2. Decide the dev-sample size and stratification (my default: 50 events, stratified across `momentum_pct` deciles, seed pinned).
3. Draft the Phase 0 prompt here, in this project.
4. Run it. Bring back digest.json.
