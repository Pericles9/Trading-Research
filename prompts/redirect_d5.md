# Documentation Redirect — D5 Strategy Surface

**This is not a phase.** It is a documentation-only change. No data is read, no measurement is produced, no code is executed against DuckDB.

**Applicability of `docs/Agent_Prompt_Standard.md`:**
- §7 (per-event charts) — does not apply.
- §9 (chart contract) — does not apply. No measurements are produced.
- §11 (digest contract) — does not apply. No `digest.json`.
- §10 (verification block) — **applies**, in the reduced form specified in T7 below.
- §12 (git discipline) — **applies in full**. Branch, commit at every task boundary, commit before escalation, no deletions.

**Role boundary:** every substantive text block in this prompt is Cooper-approved and is to be **transcribed verbatim**. Do not paraphrase, condense, improve, or re-order the decision text, the constraint block, the §3.3 replacement, or the phase map rows. Where a task calls for prose you must write yourself, it says so explicitly.

---

## T0 — Preconditions and branch

- [ ] T0a — Verify the tag `phase-7-approved` exists. **If absent → hard stop, report, do not proceed.**
- [ ] T0b — Cut branch `docs/d5-redirect` from `main`.
- [ ] T0c — Write this prompt to `prompts/redirect_d5.md` and commit it before any other work.

### T0d — Existence audit (do this before editing anything)

Report, as a plain table, whether each of the following exists on disk in the checkout, with its path and line count if present:

| Path | Exists? | Lines |
|---|---|---|
| `CLAUDE.md` | | |
| `docs/Universe-Decisions.md` | | |
| `docs/Open-Items-Register.md` | | |
| `docs/Mom-DB-Strategy-Research-Program.md` | | |
| `docs/Agent_Prompt_Standard.md` | | |
| `docs/Claude-Code-Operating-Plan.md` | | |
| `prompts/phase_6b.md` | | |
| `config/phase_6b.json` | | |

**Context:** the Phase 0b report recorded that `docs/Mom-DB-Strategy-Research-Program.md` could not be found anywhere in the checkout, and that `CLAUDE.md`'s Pointers section documents the gap. It may still be missing. Search the full checkout, including `archive/`, `research/`, `notebooks/`, and the two nested independent repos, before declaring anything absent.

**Escalation:** if `docs/Mom-DB-Strategy-Research-Program.md` or `docs/Agent_Prompt_Standard.md` is absent → **hard stop.** Do not create it, do not reconstruct it from memory or from quotations in phase reports, do not draft a replacement. Report the absence and stop. Cooper supplies the canonical copy.

Commit the audit result as an artifact at `results/redirect_d5/doc_existence_audit.json` before proceeding.

---

## T1 — Record D5 (do this first; everything downstream cites it)

Append the following to `docs/Universe-Decisions.md`, verbatim, in the same format as D1/D2/D4.

> **D5 — Strategy surface and horizon class.**
>
> **Selected surface:** intraday post-trigger (§3.3 surface #2), long-only, burst-scale horizons.
>
> **Definitions.**
> - *Burst* — a contiguous high-intensity trade-arrival cluster within a T=0 session.
> - *Burst-relative anchor* — a measurement origin located at a burst confirmation timestamp, as opposed to session open, session close, previous close, or session high.
>
> **What D5 selects.** §4 (trading intraday during high-participation windows) and §5 (regime detection, direction signal, end-detector) of `docs/Mom-DB-Strategy-Research-Program.md` become the program spine. The operating premise is: a strong bull impulse that flips sharply to a strong bear impulse, traded as a sequence of short-horizon long entries gated on regime, with minimized time exposure — not held to a fixed horizon.
>
> **What D5 demotes.** §3.3's ranking of T+1 (day-2) as surface #1. T+1 is reduced to one optional measurement pass for the "does this archive contain any edge at all" read. It is no longer a program pillar and no longer precedes detector work.
>
> **What D5 kills.** All short-side variants, including T+1 fade. The SSR and borrow-availability modeling requirement in §7.2 is void for as long as D5 stands. Long-only, for execution-logistics and risk-control reasons.
>
> **What D5 does not change.** §7.2 cost model (always cross the spread, effective spread as cost basis, slippage scaled to observed spread and participation, halts modeled as forced holds through the reopen). §7.3 validation discipline (time-based splits, ticker-blocked splits, universe-boundary and cost sensitivity). D1, D2, D4. Flag-never-delete. Two-tier dev/full discipline. The chart contract and the Evidence Standard.
>
> **Recorded consequences.**
> - (a) Session-anchored opportunity-decay measurements — Phase 6 RTH-only, and Phase 6b as currently scoped — measure a quantity outside D5's horizon class. They are retained as archive. They are **not** the operative latency budget.
> - (b) The latency budget under D5 must be re-derived burst-relative.
> - (c) Risk-register items #3 (missing counterfactuals) and #4 (circularity of regime frequency) are upgraded from "must happen before capital" to near-front blockers. Under D5 the false-positive rate of a live screen is a direct PnL term, not a caveat.
> - (d) The archive universe (q05 power-law filter applied to completed daily moves) and the intended live universe (real-time ≥30% from previous close, pre- and post-market inclusive) are different populations. This mismatch becomes a first-class open item.
>
> **Left open by D5, to be decided before any detector phase is specified.** Whether the entry signal is *onset prediction* (firing ahead of the cluster) or *fast detection and ride* (confirmation inside the cluster). §4.2 condition 4 bears directly on this. D5 does not decide it.

Commit.

---

## T2 — `CLAUDE.md`

Add the following section verbatim. Place it adjacent to the existing universe-rules / standing-methodology sections, not at the end of the file.

> ## Strategy surface (D5)
>
> - Selected surface: **intraday post-trigger, long-only, burst-scale horizons.**
> - **Long-only.** Do not specify, implement, or measure short-side or fade variants. Do not implement SSR or borrow logic.
> - **Measurement anchors are burst-relative by default.** Any session-relative or day-relative anchor — session open, previous close, session high, session close — must be named and justified in the phase prompt *before* it is used. An unjustified day-scale anchor is an escalation, not a style choice.
> - **Every feature is computed as of decision time minus realistic pipeline latency.** Lag is baked into research, not added later in production.
> - **The end-detector is a first-class deliverable.** Exit research is budgeted at least equally with entry research. Under a long-only strategy on a bull-to-bear flip, exit timing dominates variance and ruin risk.
> - The Phase 6 / 6b session-anchored decay figures are archive. They are not the operative latency budget.
> - Full text and scope: `docs/Universe-Decisions.md`, D5.

Update the Pointers section so it references D5. If the Pointers section currently records a missing-document gap that T0d resolved, correct it; if T0d confirmed the gap still stands, leave it stated.

Keep `CLAUDE.md` under ~150 lines. If this addition breaches that, **do not silently trim** — report the overage and which existing section you would compress, and stop for instruction.

Commit.

---

## T3 — `docs/Mom-DB-Strategy-Research-Program.md`

**Version this document rather than editing it surgically.** Bump to **v2.0**, add a version-history table if none exists (mirror the format in `docs/Agent_Prompt_Standard.md`), and add the row:

| 2.0 | (today's date) | D5 redirect: §3.3 re-ranked, §6 re-anchored, §8 risk items #3/#4 upgraded, §9 rewritten. Short-side variants removed. |

### T3a — §3.3 replacement

Replace the ranked list in §3.3 with the following verbatim. Leave §3.1 and §3.2 untouched.

> ### 3.3 Credible strategy surfaces, ranked (revised under D5)
>
> 1. **Intraday post-trigger, long-only** — the program spine. Requires ex-ante trigger reconstruction per §3.1 escape #1, with all outcomes measured strictly post-trigger. Carries the counterfactual gap on trigger precision (§3.2), which D5 upgrades from a caveat to a near-front blocker: under a gate-then-trade design, the live false-positive rate is a direct PnL term.
> 2. **T+1 (day-2) continuation** — the cleanest ex-ante surface the archive offers, retained as a **single optional measurement pass** answering "does this archive contain any edge at all." Not a pillar, and it no longer gates detector work. Long-only under D5; the fade variant is dropped.
> 3. **Pre-event detection (T-3…T-1)** — unchanged. One measurement pass, most likely a respectful burial.
>
> **Note on the prior ranking.** v1.x ranked T+1 first on ex-ante cleanliness, and the Operating Plan ordered the T+1 markout grid ahead of detector development on the reasoning that a flat grid saves six weeks. D5 overrides that ordering deliberately, accepting the cost: the cheapest edge-existence check is now optional rather than gating. Recorded here so the override is visible, not inferred.

### T3b — §6 re-anchoring

In §6, replace the markout grid bullet with:

> - **Markout grid (burst-relative under D5):** cost-adjusted forward returns at horizons matched to measured burst timescales, anchored on burst confirmation. Day-scale anchors (open, close, T+1, T+3) are retained only for the optional T+1 pass and are not the primary grid.

Leave the rest of §6 intact, including the conditioning-features list and the event-study-before-backtest standing rule.

### T3c — §8 risk register

Update the Status and Consequence cells for items #3 and #4 to reflect their upgrade under D5. Do not renumber, do not delete rows. Add one new row:

> | 9 | Archive universe (q05 on completed daily moves) vs. intended live universe (real-time ≥30% from previous close, pre/post-market inclusive) are different populations | Open — first-class under D5 | Every conditional result is measured on a population the live screen does not reproduce; live PnL diverges by an unquantified amount |

### T3d — §9 execution plan

Replace §9 entirely with a plan sequenced from the phase map in T4. Keep the existing closing line verbatim: *"Dates are ordinal, not promises. The gates between phases are the artifacts, not the calendar."*

Commit T3a–T3d as one commit, or as four — your call, but commit before moving to T4.

---

## T4 — `docs/Claude-Code-Operating-Plan.md`, §6 Phase Map

Rows 0–7 of the existing map describe completed work: **leave them exactly as they are.** Replace rows 8 onward with the following, verbatim.

| Phase | Name | Produces | Charts | Gate |
|---|---|---|---|---|
| **8** | Burst decomposition | Per-event burst segmentation; burst count, duration, spacing; fraction of session move carried per burst; burst-relative concentration curve | Burst count & duration distributions; per-burst move-share; burst-relative decay curve | **Burst timescale is a number.** Burst-relative latency budget replaces the session-anchored one |
| **9** | Spread & impact by participation | Quoted vs. effective spread bucketed by participation rate; impact per unit signed volume, burst vs. quiet | Spread-vs-participation; impact curves | Compression claim tested; FP cost is a number |
| **10** | Halts & LULD | P(halt \| state); time-to-halt; reopen gap distribution, long-side conditional | Reopen gap distribution; halt timing | Sizing constraint is a number |
| **11** | Noise floor & tape characterization | Inter-trade interval distributions, print-size distributions, quote flicker rates — inside bursts vs. outside | Interval & size distributions by regime | Detector null distribution known |
| **12** | Signed flow & impact efficiency — feature layer | Lee-Ready aggressor classification; rolling signed volume; impact-efficiency derivative. Precomputed once, cached, lag-baked | Feature distributions | Features cached, not recomputed in loops |
| **13** | Burst hazard function | Duration distributions → P(death \| age); spread re-widening and intensity decay as covariates | Hazard curves by age; covariate-conditioned survival | **Exit prior is a number** |
| **14** | Regime labeling + stability | Offline labels; label-perturbation stability test (§5.1.1) | Label-set overlap under perturbation | Foundation solid, or sand |
| **15** | Detector + end-detector | Threshold+hysteresis baseline; CUSUM/BOCPD and intensity challengers; operating point by expected PnL; flanking-day FP estimation | Detection latency vs. FP; PnL at operating point | Both detectors exist; complexity earned or discarded |
| **16** | Direction signal | Features vs. cost-adjusted markouts within true-positive regimes, against the always-long-while-on null | Markout tables; monotonicity plots | "Detector + market order" vs. "detector + signal" — decided |
| **17** | Joint walk-forward | Full stack under the §7.2 cost model, halts as forced holds; vectorized first, Nautilus for the short list | Per-event charts (§7 of the standard) | — |
| **Opt-A** | T+1 markout grid (optional, long-only) | The single day-2 edge-existence pass retained under D5 | Markout heatmaps | Runs when Cooper calls for it; gates nothing |
| **Parallel** | Unconditional universe scan | Scope + feasibility; live-screen population vs. archive population | Population comparison | **Gates capital.** Cannot start last |

Replace the ordering note that currently defends "12 before the detector work." Do not delete it — supersede it, and state that D5 overrode it and why. That paragraph is yours to write; keep it to three sentences and describe the override without arguing for it.

Commit.

---

## T5 — `docs/Open-Items-Register.md`

Add three items, in the register's existing format:

1. **Archive vs. live universe mismatch.** Full statement per D5 consequence (d). Opened by D5. Owner: unassigned.
2. **Unconditional universe scan.** Upgraded from "before capital" to near-front blocker per D5 consequence (c). Cross-reference risk-register items #3 and #4.
3. **Entry-signal class undecided.** Onset prediction vs. fast detection and ride. Must be resolved before Phase 15 is specified. Cross-reference §4.2 condition 4.

Update the existing **ARBB row-cap** item: annotate that its priority rises under D5, because concentration and spread measurements move from supporting evidence to load-bearing inputs. Do not close it.

Commit.

---

## T6 — Phase 6b disposition

`prompts/phase_6b.md` and `config/phase_6b.json` are currently queued to resume the moment `phase-7-approved` exists, per Amendment A8.2, which is written into the Phase 7 approval gate. D5 makes 6b's session-anchored extended-day output non-operative.

> **COOPER FILLS THIS IN BEFORE THE PROMPT IS RUN:**
>
> Phase 6b disposition — [ ] re-scope to burst-relative · [ ] kill · [ ] run as written for archive value
>
> Amendment number: A___
>
> Scope statement: ______________________________________________

**If the block above is unfilled → hard stop at T6.** Complete T0–T5, commit, report, and stop. Do not choose a disposition. Do not modify `prompts/phase_6b.md` or `config/phase_6b.json` on your own initiative. A8.2's terms are already written into an approved gate; changing them without a numbered amendment breaks the audit trail.

If filled: write the amendment to the repo's amendment location following the existing convention, apply the stated disposition, and commit.

---

## T7 — Verification and report

Reduced verification block (§10 of the standard, adapted — no measurements exist to verify, so the evidence burden is *diff fidelity*):

| Check | Method | Result |
|---|---|---|
| D5 text transcribed verbatim | Diff the committed D5 block against the block in `prompts/redirect_d5.md`, character-exact | |
| CLAUDE.md block transcribed verbatim | Same method | |
| §3.3 replacement transcribed verbatim | Same method | |
| Phase map rows 8–17 + Opt-A + Parallel transcribed verbatim | Same method | |
| Phase map rows 0–7 unmodified | `git diff` shows zero changes to those lines | |
| No file outside `docs/`, `prompts/`, `CLAUDE.md`, `results/redirect_d5/` was written | `git diff --stat` | |
| Zero deletions | `git diff --stat` shows no removed files | |
| No data access | No DuckDB connection opened; no read under `data/` | |
| CLAUDE.md line count | ≤150, or overage reported | |

Write `results/redirect_d5/REPORT.md` containing: the T0d existence audit table, the verification table above, a full `git diff --stat`, the commit list, and — separately labelled — **any prose you authored yourself** (the T4 superseding note, the T3d §9 rewrite, register entries), quoted in full so Cooper reviews your words rather than inferring them from the diff.

No `digest.json`. No charts.

---

## Escalation rows

| # | Condition | Action |
|---|---|---|
| 1 | `phase-7-approved` tag absent | Hard stop at T0a |
| 2 | `Mom-DB-Strategy-Research-Program.md` or `Agent_Prompt_Standard.md` not found in checkout | Hard stop at T0d. Do not create or reconstruct |
| 3 | T6 disposition block unfilled | Hard stop at T6. Complete T0–T5 and report |
| 4 | Any write outside `docs/`, `prompts/`, `CLAUDE.md`, `results/redirect_d5/` | Hard stop |
| 5 | Any DuckDB connection or read under `data/` | Hard stop |
| 6 | Any file deletion | Hard stop |
| 7 | `CLAUDE.md` exceeds 150 lines after T2 | Report and stop; do not trim |
| 8 | Any verbatim block cannot be transcribed as given (e.g. it contradicts existing document structure) | Report the conflict and stop. Do not resolve it yourself |

---

## Approval Gate

Do not tag, do not merge to `main`, and do not begin Phase 8 scoping until Cooper has reviewed the diff and given explicit approval. On approval: tag `d5-redirect-approved`.
