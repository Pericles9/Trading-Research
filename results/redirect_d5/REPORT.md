# Documentation Redirect — D5 Strategy Surface — REPORT

**Date:** 2026-08-03
**Branch:** `docs/d5-redirect` (cut from `master` @ `6dd52cf`)
**Prompt of record:** `prompts/redirect_d5.md`
**Status:** **PARTIAL — hard-stopped at T3d, T4 and T6.** T0, T1, T2, T3a–T3c and T5 complete.

This was a documentation-only change. No DuckDB connection was opened. No file under `data/` was read.

**No cross-phase copy at `results/reports/`.** `CLAUDE.md`'s copy rule is scoped to "every phase's `REPORT.md`"; this is explicitly not a phase, and `results/reports/` sits outside T7's allowed write set (`docs/`, `prompts/`, `CLAUDE.md`, `results/redirect_d5/`) — writing there would trip escalation row 4. Say the word if you want it copied anyway.

---

## 1. Outcome summary

| Task | Status | Note |
|---|---|---|
| T0a — `phase-7-approved` exists | **done** | Present, `b402dcab6583d173448ccef76dcc288634d75019` |
| T0b — branch from `main` | **done, with discrepancy** | No `main` branch exists; trunk is `master`. Cut from `master`. |
| T0c — prompt committed first | **done** | `46a70e9` |
| T0d — existence audit | **done** | `e90089f`, artifact `results/redirect_d5/doc_existence_audit.json` |
| T1 — record D5 | **done** | `49eed7a` |
| T2 — `CLAUDE.md` | **done** | `787a85e`, 70 → 85 lines |
| T3 version bump + T3a/T3b/T3c | **done** | `2807c5e` |
| T3d — §9 execution plan | **HARD STOP** | Depends on the T4 phase map, which cannot be written. §9 left at v1.x. |
| T4 — Operating Plan §6 phase map | **HARD STOP** | Escalation row 8. Two independent blockers, C1 and C2 below. |
| T5 — Open Items Register | **done** | `39bbab3` |
| T6 — Phase 6b disposition | **HARD STOP** | Escalation row 3. Disposition block unfilled. Premise also stale — see C3. |
| T7 — verification and report | **done** | This file |

Nothing was tagged. Nothing was merged. `prompts/phase_6b.md` and `config/phase_6b.json` were not touched.

---

## 2. T0d — existence audit

| Path | Exists? | Lines |
|---|---|---|
| `CLAUDE.md` | yes | 70 (at audit time; 85 after T2) |
| `docs/Universe-Decisions.md` | yes | 225 (254 after T1) |
| `docs/Open-Items-Register.md` | yes | 47 (50 after T5) |
| `docs/Mom-DB-Strategy-Research-Program.md` | yes | 375 (403 after T3) |
| `docs/Agent_Prompt_Standard.md` | yes | 572 |
| `docs/Claude-Code-Operating-Plan.md` | **no** | — |
| `prompts/phase_6b.md` | yes | 125 |
| `config/phase_6b.json` | yes | 98 |

**Escalation row 2 did NOT trigger.** Both documents it names — `docs/Mom-DB-Strategy-Research-Program.md` and `docs/Agent_Prompt_Standard.md` — are present. The Phase 0b-era gap on the Strategy Program is closed; `CLAUDE.md`'s Pointers section recorded no missing-document gap, so there was nothing to correct there.

**A different document is missing: `docs/Claude-Code-Operating-Plan.md`.** Search method, per T0d's instruction to sweep the full checkout including `archive/`, `research/`, `notebooks/` and the two nested independent repos:

1. `find . -not -path './.git/*' \( -iname '*operating*' -o -iname '*claude-code*' \)` — full traversal, including `data/`, `hawkes-ofi-impact/` and `scanner-epg-momentum/`. **Zero filename matches.**
2. ripgrep for `/Operating.?Plan/i` across the checkout excluding `data/` — four references found, all *citing* the document, none *being* it:
   - `prompts/phase_0a.md:4` — "Precedes Phase 0 (harness setup) from the Operating Plan §6."
   - `prompts/phase_0a.md:38` — "Target layout is the directory contract from the Operating Plan §2.2"
   - `prompts/phase_0b.md:5` — "Complete Phase 0 of the Operating Plan"
   - `docs/Research-Library-Map.md:518` — "the Operating Plan's `results/phase_{x}/` convention"
3. `git log --all -- '*Operating*'` — empty. `git log --all --diff-filter=D --name-only | grep -i operat` — empty. **The file has never existed in any commit on any branch.**

Per T0d, nothing was created, reconstructed, or drafted. The gap is now stated in `CLAUDE.md`'s Pointers section.

---

## 3. Conflicts — why T3d, T4 and T6 stopped

### C1 (blocking, T4 and T3d) — the target file does not exist

T4 says "Rows 0–7 of the existing map describe completed work: leave them exactly as they are. Replace rows 8 onward." There is no existing map. `docs/Claude-Code-Operating-Plan.md` has never been in this repository (§2 above). Creating it would mean authoring rows 0–7 from scratch — i.e. reconstructing a Cooper document from phase-report quotations, which T0d explicitly forbids for the documents it names and which the role boundary forbids generally. **Escalation row 8.**

T3d inherits the block: it specifies §9 as "a plan sequenced from the phase map in T4."

### C2 (blocking, T4) — the T4 map contradicts an approved phase and an in-flight one

The prompt's model of program state is roughly ten days stale. Two phases have been specified and run since `phase-7-approved` (2026-07-24):

| | T4 map says | Repo says |
|---|---|---|
| Phase 8 | Burst decomposition. Gate: "Burst timescale is a number." | **`prompts/phase_8.md` — "Event-Study Grid: Forward Markouts from Tradeable Anchors"**, dated 2026-08-01, merged to `master`, **tagged `phase-8-approved`**. Produced `results/phase_8/`, cited by two Open Items Register entries. |
| Phase 9 | Spread & impact by participation | **`prompts/phase_9.md` — "Path Shape, Cross-Session Integrity, and Clustered Inference"**, dated 2026-08-03, branch `phase/9`, **9 commits, unmerged**, with `config/phase_9.json`. |

Transcribing the T4 map verbatim would overwrite the record of a tagged, approved phase with a different, unexecuted plan, and would collide with work committed the same day this prompt was run. The Approval Gate's "do not begin Phase 8 scoping" is moot for the same reason — Phase 8 is finished and approved. **Escalation row 8.** Not resolved here; the renumbering is Cooper's call, not the agent's.

Note that this is a *numbering* conflict, not a substantive one. Nothing in the T4 map's content contradicts D5 — the executed Phase 8 measured markouts from anchors knowable in real time, which sits under D5's surface #1, not under the demoted T+1 surface.

### C3 (informational, T6) — stale premise, and the block is unfilled anyway

T6 states that `prompts/phase_6b.md` and `config/phase_6b.json` "are currently queued to resume the moment `phase-7-approved` exists." Phase 6b has already run and been approved: tag `phase-6b-approved` exists, branch `phase/6b` exists, `prompts/phase_6b_amendment_8.md` is committed, and `results/phase_6b/` is cited throughout the Open Items Register and as Phase 8's baseline ("`phase-6b-approved` — `event_minute_bars_v2`, 45,925,350 rows").

Independently of that, the Cooper disposition block is unfilled — no box ticked, no amendment number, no scope statement. **Escalation row 3.** No disposition was chosen; neither file was modified.

### C4 (informational, T0b) — no `main` branch

`git branch -a` lists `master` plus `phase/*`. The branch was cut from `master` @ `6dd52cf`. `prompts/phase_9.md` uses the same "cut from `main`" wording, so this appears to be a naming convention in the prompts rather than a real branch.

---

## 4. Verification block (T7)

Method for every "character-exact" row: extract the block from `prompts/redirect_d5.md`, strip the `> ` blockquote markers (prompt-quoting syntax, not content), and compare byte-for-byte against the committed text. Script output captured at `results/redirect_d5/verbatim_checks.json`.

| Check | Method | Result |
|---|---|---|
| D5 text transcribed verbatim | Character-exact diff, body from `**Selected surface:**` onward | **PASS** — see deviation note below |
| CLAUDE.md block transcribed verbatim | Character-exact diff, `## Strategy surface (D5)` through end of section | **PASS** |
| §3.3 replacement transcribed verbatim | Character-exact diff, heading through the prior-ranking note | **PASS** |
| Phase map rows 8–17 + Opt-A + Parallel transcribed verbatim | — | **NOT APPLICABLE — T4 hard-stopped (C1, C2). No phase map was written.** |
| Phase map rows 0–7 unmodified | — | **NOT APPLICABLE — no such file exists (C1).** Vacuously true: zero bytes written to any phase map. |
| §6 markout bullet transcribed verbatim | Character-exact substring match | **PASS** (T3b, not in the prompt's own table) |
| §8 row 9 transcribed verbatim | Character-exact substring match | **PASS** (T3c, not in the prompt's own table) |
| No file outside `docs/`, `prompts/`, `CLAUDE.md`, `results/redirect_d5/` was written | `git diff --name-status master...HEAD` | **PASS** — 6 paths, all inside the allowed set |
| Zero deletions | `git diff --name-status master...HEAD` | **PASS** — 4 `M`, 2 `A`, zero `D`. The 11 removed lines in `--stat` are line-level replacements inside modified files (§3.3 list, §6 bullet, §8 rows #3/#4, Pointers), not file deletions. |
| No data access | No `duckdb` import, no connection, no read under `data/` | **PASS** — the T0d filename traversal stat'd paths under `data/` but opened no file |
| CLAUDE.md line count | `wc -l` | **PASS** — 85, under the ~150 ceiling |

**Deviation note on the D5 block.** The prompt asked for two things at once: verbatim transcription, *and* "in the same format as D1/D2/D4." Those sections use a `## Dn — <title>` heading followed by `**Date:**` / `**Deciding phase gate:**` lines. The D5 title line `**D5 — Strategy surface and horizon class.**` was therefore promoted to the heading `## D5 — Strategy surface and horizon class` and two metadata lines were added beneath it. Every other line of the D5 block is byte-identical. This is the only place any Cooper text was re-shaped, and it was done to satisfy the format half of the same instruction.

---

## 5. `git diff --stat` (full)

```
 CLAUDE.md                                    |  17 +-
 docs/Mom-DB-Strategy-Research-Program.md     |  36 +++-
 docs/Open-Items-Register.md                  |   7 +-
 docs/Universe-Decisions.md                   |  29 ++++
 prompts/redirect_d5.md                       | 235 +++++++++++++++++++++++++++
 results/redirect_d5/doc_existence_audit.json |  82 ++++++++++
 6 files changed, 395 insertions(+), 11 deletions(-)
```

```
M	CLAUDE.md
M	docs/Mom-DB-Strategy-Research-Program.md
M	docs/Open-Items-Register.md
M	docs/Universe-Decisions.md
A	prompts/redirect_d5.md
A	results/redirect_d5/doc_existence_audit.json
```

(`results/redirect_d5/REPORT.md` and `results/redirect_d5/verbatim_checks.json` are added by the T7 commit, after this stat was taken.)

## 6. Commit list

```
39bbab3 d5-redirect T5: three open items opened, ARBB row-cap priority raised
2807c5e d5-redirect T3a-T3c: strategy program v2.0 (partial -- T3d blocked)
787a85e d5-redirect T2: CLAUDE.md strategy-surface block
49eed7a d5-redirect T1: record D5 -- strategy surface and horizon class
e90089f d5-redirect T0d: existence audit
46a70e9 d5-redirect T0c: prompt of record
```

---

# 7. AGENT-AUTHORED PROSE — every word below is mine, not Cooper's

Quoted in full for review. The T4 superseding note and the T3d §9 rewrite are **absent** — both were hard-stopped, so no prose exists for them.

## 7.1 `docs/Mom-DB-Strategy-Research-Program.md` §8, risk item #3 — Status and Consequence cells

> Structural — **near-front blocker under D5** (was: partially mitigated by flanking days). Hardened by Phase 8 A10.2d: the rejected-candidate population is confirmed absent from the archive, so the live FP rate is unmeasurable from what is on disk

> Under D5's gate-then-trade design the live false-positive rate is a **direct PnL term, not a caveat** — every markout is conditional on power-law-filter membership, which is not knowable at detection time

## 7.2 `docs/Mom-DB-Strategy-Research-Program.md` §8, risk item #4 — Status and Consequence cells

> Structural — **near-front blocker under D5** (was: requires unconditional universe scan before capital). The scan cannot be sequenced last

> Detector fire-rate in the wild unknown, so the cost of every false fire is unpriced; under a long-only burst strategy that cost is paid in round-trip effective spread on every wrong gate

## 7.3 `docs/Mom-DB-Strategy-Research-Program.md` — version-history table and status note

The 2.0 row is Cooper's text, transcribed verbatim. The 1.x row and the note beneath the table are mine:

> | 1.x     | 2026-07-13 | Initial spec. No version history was recorded before the 2.0 bump; "1.x" is the retroactive designation used by §3.3's note on the prior ranking. |

> **Status of the 2.0 row, 2026-08-03 (agent note, not Cooper text).** §3.3, §6 and §8 landed as described. **§9 was not rewritten** — `prompts/redirect_d5.md` T3d specifies §9 as "sequenced from the phase map in T4", and T4 hard-stopped: `docs/Claude-Code-Operating-Plan.md` does not exist in this checkout and the T4 map's rows 8 and 9 conflict with the already-approved Phase 8 and the in-flight Phase 9. §9 therefore still carries the v1.x week-numbered plan and is stale with respect to D5. Remove this note when T3d lands. See `results/redirect_d5/REPORT.md`.

**Why this note exists.** The 2.0 row asserts "§9 rewritten," and §9 was not rewritten. Rather than silently commit a false history row or alter Cooper's text, the row stands verbatim and the note states what is actually true. **This is the one place where an agent-authored annotation sits directly beneath Cooper text, and it is written to be deleted when T3d lands.** If you would rather the version bump wait for T3d entirely, say so and it comes out.

## 7.4 `CLAUDE.md` — Pointers section additions

The `## Strategy surface (D5)` block itself is Cooper's text, verbatim. These Pointers lines are mine:

> - Strategy context: docs/Mom-DB-Strategy-Research-Program.md (v2.0, 2026-08-03 — re-ranked under D5).
> - Standing decisions: docs/Universe-Decisions.md — D1 analysis universe, D2 `clean_window`, D3 analysis
>   clock, D4 tick-only measurement, **D5 strategy surface and horizon class** (2026-08-03).

> - `docs/Claude-Code-Operating-Plan.md` is cited by prompts/phase_0a.md, prompts/phase_0b.md and
>   docs/Research-Library-Map.md but has never existed in this checkout — Cooper holds it externally.
>   Gap confirmed 2026-08-03, `results/redirect_d5/doc_existence_audit.json`.

## 7.5 `docs/Universe-Decisions.md` D5 — heading and metadata lines

> ## D5 — Strategy surface and horizon class
>
> **Date:** 2026-08-03
> **Deciding phase gate:** `phase-7-approved` (documentation redirect, `prompts/redirect_d5.md` — not a phase)

Everything from `**Selected surface:**` onward is Cooper's text, byte-identical.

## 7.6 `docs/Open-Items-Register.md` — three new items

> - **Archive universe vs. intended live universe are different populations.** Opened by `docs/Universe-Decisions.md` D5, consequence (d), 2026-08-03. The archive universe is the q05 power-law filter applied to **completed daily moves**; the intended live universe is a real-time screen at **≥30% from previous close, pre- and post-market inclusive**. These are different populations: the archive's selection variable is only knowable after the session ends, and its RTH-scoped construction (D4's `momentum_pct` exception) does not see the extended-hours moves the live screen is meant to fire on. Consequence: every conditional result in this program is measured on a population the live screen does not reproduce, and live PnL diverges from measured PnL by an unquantified amount. Recorded as risk-register row 9 in `docs/Mom-DB-Strategy-Research-Program.md` §8. **Owner: unassigned.** — logged D5 redirect T5, 2026-08-03.

> - **Unconditional universe scan — upgraded to near-front blocker.** Per D5 consequence (c), 2026-08-03. The scan was previously scoped as "must happen before capital" (§5.4, §8 risk item #4, and the v1.x §9 "Weeks 8+ ... in parallel" line). Under D5's gate-then-trade design the detector's fire-rate in the wild is a **direct PnL term**, so the scan can no longer be sequenced late or in parallel-if-convenient — it gates the operating-point selection of any detector, not just capital. Cross-references risk-register items **#3** (missing counterfactual / near-miss set — hardened by Phase 8 A10.2d, which confirmed the rejected-candidate population is absent from `data/filtered/`, making the live FP rate unmeasurable from what is on disk) and **#4** (circularity of regime frequency). Not scheduled — the phase that takes it on is not yet specified. — logged D5 redirect T5, 2026-08-03.

> - **Entry-signal class undecided — onset prediction vs. fast detection and ride.** Left explicitly open by D5 ("Left open by D5, to be decided before any detector phase is specified"), 2026-08-03. *Onset prediction* fires ahead of the trade-arrival cluster; *fast detection and ride* confirms inside it. The two demand different features, different null distributions, and different latency budgets, so the choice cannot be deferred into the detector phase — it determines what that phase is. §4.2 condition 4 bears directly on it: retail-grade execution rules out sub-second signals but leaves 30-second-to-5-minute horizons intact, which constrains how early an onset call could be acted on at all. **Must be resolved before the detector phase is specified** (T4's map numbers that phase 15; that map is not committed — see `results/redirect_d5/REPORT.md` conflict C2). Cooper decision, unassigned. — logged D5 redirect T5, 2026-08-03.

## 7.7 `docs/Open-Items-Register.md` — ARBB row-cap annotation

Appended to the existing `flag_possible_row_cap` item. The item is **not** closed.

> **Priority raised under D5, 2026-08-03:** the row cap is no longer a bounded nuisance on aggregate markouts. D5 makes burst decomposition, concentration curves and spread-vs-participation measurements load-bearing program inputs rather than supporting evidence, and all three are computed from T=0 print counts and print sequences — exactly what a collector row cap truncates. A capped event does not merely lose volume; it loses the tail of the session, which is where burst termination and the bull-to-bear flip live. Item stays open, not closed; the (b) root-cause half is the part that rises.

Also changed, mine: the register's frontmatter `last_reviewed:` from `2026-08-01 (Phase 8)` to `2026-08-03 (D5 redirect)`.

---

## 8. What Cooper needs to decide before this can finish

1. **Supply `docs/Claude-Code-Operating-Plan.md`**, or authorize its creation in this repo. T4 and T3d are blocked until then.
2. **Resolve the phase numbering.** The T4 map's rows 8 and 9 are occupied by executed work. The map needs renumbering from 10 (or wherever), or an explicit statement of how it relates to the executed Phase 8/9.
3. **Fill the T6 disposition block** for Phase 6b — noting that 6b already ran and was approved, so the live question is what to do with `results/phase_6b/` output under D5, not whether to resume the phase.
4. **Confirm or reject the §7.3 annotation** — the agent note beneath the version-history table.

Per the Approval Gate: nothing tagged, nothing merged. On approval: tag `d5-redirect-approved`.
