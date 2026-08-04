# Documentation Redirect — D5 Strategy Surface — REPORT

**Date:** 2026-08-03
**Branch:** `docs/d5-redirect` (cut from `master` @ `6dd52cf`)
**Prompt of record:** `prompts/redirect_d5.md`
**Status:** **COMPLETE.** All of T0–T7 executed. Three tasks (T3d, T4, T6) hard-stopped on the first pass and were cleared by Cooper the same day.

This was a documentation-only change. No DuckDB connection was opened. No file under `data/` was read.

**No cross-phase copy at `results/reports/`.** `CLAUDE.md`'s copy rule is scoped to "every phase's `REPORT.md`"; this is explicitly not a phase, and `results/reports/` sits outside T7's allowed write set (`docs/`, `prompts/`, `CLAUDE.md`, `results/redirect_d5/`) — writing there would trip escalation row 4. Say the word if you want it copied anyway.

---

## 1. Outcome summary

| Task | Status | Note |
|---|---|---|
| T0a — `phase-7-approved` exists | done | `b402dcab6583d173448ccef76dcc288634d75019` |
| T0b — branch from `main` | done, with discrepancy | No `main` branch exists; trunk is `master`. Cut from `master`. |
| T0c — prompt committed first | done | `46a70e9` |
| T0d — existence audit | done | `e90089f` |
| T1 — record D5 | done | `49eed7a` |
| T2 — `CLAUDE.md` | done | `787a85e`, 70 → 85 lines |
| T3 version bump + T3a/T3b/T3c | done | `2807c5e` |
| T5 — Open Items Register | done | `39bbab3` |
| *(first-pass report)* | — | `f90d401` — recorded three hard stops |
| **Operating Plan supplied by Cooper** | **C1 cleared** | `572deb9` — committed unmodified before any edit |
| T6 — Phase 6b disposition | **done** | `9efb30b` — D5 Amendment A11, archive-only |
| T4 — Operating Plan §6 phase map | **done** | `aba3927` — D5 rows renumbered 10–19 |
| T3d — §9 execution plan | **done** | `5251735` |
| T7 — verification, report, library map | done | this commit |

---

## 2. T0d — existence audit (as run, before Cooper's fix)

| Path | Exists? | Lines |
|---|---|---|
| `CLAUDE.md` | yes | 70 (85 after T2) |
| `docs/Universe-Decisions.md` | yes | 225 (288 after T1 + A11) |
| `docs/Open-Items-Register.md` | yes | 47 (50 after T5) |
| `docs/Mom-DB-Strategy-Research-Program.md` | yes | 375 (407 after T3) |
| `docs/Agent_Prompt_Standard.md` | yes | 572 |
| `docs/Claude-Code-Operating-Plan.md` | **no** → **yes** | Supplied by Cooper 2026-08-03, 261 lines as received (273 after T4) |
| `prompts/phase_6b.md` | yes | 125 |
| `config/phase_6b.json` | yes | 98 |

**Escalation row 2 did NOT trigger** — both documents it names were present. The missing document was a different one, `docs/Claude-Code-Operating-Plan.md`, cited by `prompts/phase_0a.md` (×2), `prompts/phase_0b.md` and `docs/Research-Library-Map.md:518` but never committed on any branch (`git log --all -- '*Operating*'` empty; full-tree `find` including `data/` and both nested repos, zero filename matches). Per T0d nothing was created or reconstructed; Cooper supplied the canonical copy, which was committed **unmodified** at `572deb9` before T4 edited it, so the T4 diff is reviewable against a clean baseline.

---

## 3. The three hard stops and how they were cleared

### C1 — Operating Plan absent → **resolved: Cooper supplied it**

### C2 — phase-map numbering → **resolved: renumber to 10+**

Reading the real §6 narrowed this considerably. The map is a **plan** document whose row numbers never tracked prompt filenames — the executed program inserted 0a/0b/0c/1b/1c/2b/5a and re-scoped several phases. Two plan rows executed under different numbers:

| Plan row | Ran as |
|---|---|
| row 8 — *Measurement 1 — concentration* | **Phase 6** (the session-anchored latency budget D5 demotes) |
| row 12 — *Event-study grid — T+1* | **Phase 8**, re-scoped to tradeable anchors |

So T4's own premise — "rows 0–7 describe completed work" — was not accurate; they are plan slots. Cooper's decision: **map numbers are prompt filenames from row 8 onward.** Applied as: rows 0–7 untouched (verified, zero changed lines); two executed-record rows added at 8 and 9; T4's twelve rows shifted 8–17 → 10–19 with Opt-A and Parallel unshifted, **all verbatim modulo the phase number**; crosswalk recorded in the map itself.

Substantively nothing in the T4 map contradicts D5 — the executed Phase 8 measured markouts from real-time-knowable anchors, which sits under D5's surface #1, not the demoted T+1 surface. The conflict was numbering only.

### C3 — Phase 6b disposition → **resolved: archive-only, D5 Amendment A11**

T6's premise was stale (6b already ran and was approved; `results/phase_6b/` is Phase 8's declared baseline), so the amendment states the correction on the record before the disposition. **A11** is the next free number in the global amendment sequence — A10 (Phase 8) was the highest previously used and Phase 9 consumed none.

Recorded as a **D5 sub-amendment inside `docs/Universe-Decisions.md`**, mirroring the D4/A9 pattern, rather than as `prompts/phase_6b_amendment_11.md` — a prompt file would imply a re-run, which is precisely what the disposition declines. `prompts/phase_6b.md` and `config/phase_6b.json` were not modified.

### C4 — no `main` branch (informational)

`git branch -a` lists `master` plus `phase/*`. Branch cut from `master` @ `6dd52cf`. `prompts/phase_9.md` uses the same "cut from `main`" wording, so this reads as prompt convention rather than a real branch.

---

## 4. Verification block (T7)

Method for every "character-exact" row: extract the block from `prompts/redirect_d5.md`, strip the `> ` blockquote markers (prompt-quoting syntax, not content), compare byte-for-byte against the committed text. Machine output: `results/redirect_d5/verbatim_checks.json`.

| Check | Method | Result |
|---|---|---|
| D5 text transcribed verbatim | Character-exact diff, body from `**Selected surface:**` to the A11 heading | **PASS** — see deviation note |
| CLAUDE.md block transcribed verbatim | Character-exact diff | **PASS** |
| §3.3 replacement transcribed verbatim | Character-exact diff | **PASS** |
| Phase map rows 8–17 + Opt-A + Parallel transcribed verbatim | Character-exact substring match after the agreed 8–17 → 10–19 shift; Opt-A and Parallel unshifted | **PASS (12/12)** — renumber is the Cooper decision above, the only change to any row |
| Phase map rows 0–7 unmodified | `git diff 572deb9 HEAD -- docs/Claude-Code-Operating-Plan.md`, count of removed lines matching `**[0-7]**` | **PASS — 0** |
| §6 markout bullet transcribed verbatim | Character-exact substring match | **PASS** (T3b) |
| §8 row 9 transcribed verbatim | Character-exact substring match | **PASS** (T3c) |
| §9 closing line kept verbatim | Substring match, and it is the last line of §9 | **PASS** |
| No file outside `docs/`, `prompts/`, `CLAUDE.md`, `results/redirect_d5/` was written | `git diff --name-status` | **PASS** — 9 paths, all inside the allowed set |
| Zero deletions | `git diff --name-status` | **PASS** — 5 `M`, 4 `A`, zero `D`. The 17 removed lines in `--stat` are line-level replacements inside modified files, not file deletions. |
| No data access | No `duckdb` import, no connection, no read under `data/` | **PASS** — the T0d filename traversal stat'd paths under `data/` but opened no file |
| CLAUDE.md line count | `wc -l` | **PASS** — 85, under the ~150 ceiling |

**Deviation note on the D5 block.** The prompt asked for verbatim transcription *and* "the same format as D1/D2/D4", which use a `## Dn — <title>` heading plus `**Date:**` / `**Deciding phase gate:**` lines. The title line `**D5 — Strategy surface and horizon class.**` was therefore promoted to the heading `## D5 — Strategy surface and horizon class` and two metadata lines added beneath. Every other line is byte-identical. Together with the phase-map renumber, these are the only two places Cooper text was re-shaped, and both were done to satisfy an explicit instruction.

---

## 5. `git diff --stat` (full, `6dd52cf..HEAD`)

```
 CLAUDE.md                                    |  17 +-
 docs/Claude-Code-Operating-Plan.md           | 273 +++++++++++++++++++++++++++
 docs/Mom-DB-Strategy-Research-Program.md     |  49 +++--
 docs/Open-Items-Register.md                  |   7 +-
 docs/Research-Library-Map.md                 |  15 +-
 docs/Universe-Decisions.md                   |  63 +++++++
 prompts/redirect_d5.md                       | 235 +++++++++++++++++++++++
 results/redirect_d5/REPORT.md                | 227 ++++++++++++++++++++++
 results/redirect_d5/doc_existence_audit.json |  82 ++++++++
 results/redirect_d5/verbatim_checks.json     |   8 +
```

```
M	CLAUDE.md
A	docs/Claude-Code-Operating-Plan.md
M	docs/Mom-DB-Strategy-Research-Program.md
M	docs/Open-Items-Register.md
M	docs/Research-Library-Map.md
M	docs/Universe-Decisions.md
A	prompts/redirect_d5.md
A	results/redirect_d5/REPORT.md
A	results/redirect_d5/doc_existence_audit.json
A	results/redirect_d5/verbatim_checks.json
```

`docs/Research-Library-Map.md` is updated per `CLAUDE.md`'s standing rule that anything adding or moving repo files updates the map in the same change. (Counts above are as of the final commit; this file and the library map are written by it.)

## 6. Commit list

```
5251735 d5-redirect T3d: 9 rewritten against the renumbered phase map
aba3927 d5-redirect T4: phase map -- D5 rows renumbered to 10-19
9efb30b d5-redirect T6: D5 Amendment A11 -- phase 6b archive-only, no new run
572deb9 d5-redirect: add docs/Claude-Code-Operating-Plan.md as supplied
f90d401 d5-redirect T7: verification and report -- PARTIAL, three hard stops
39bbab3 d5-redirect T5: three open items opened, ARBB row-cap priority raised
2807c5e d5-redirect T3a-T3c: strategy program v2.0 (partial -- T3d blocked)
787a85e d5-redirect T2: CLAUDE.md strategy-surface block
49eed7a d5-redirect T1: record D5 -- strategy surface and horizon class
e90089f d5-redirect T0d: existence audit
46a70e9 d5-redirect T0c: prompt of record
```

`f90d401` and `2807c5e` are superseded in substance but kept — they are the record of the hard stops, per §12's no-deletion rule.

---

# 7. AGENT-AUTHORED PROSE — every word below is mine, not Cooper's

Quoted in full for review.

## 7.1 `docs/Claude-Code-Operating-Plan.md` §6 — the superseding note (T4's three-sentence paragraph)

> **Superseded by D5, 2026-08-03.** D5 selects intraday post-trigger, long-only, burst-scale horizons as the program spine, which demotes T+1 from surface #1 to a single optional edge-existence pass (Opt-A) that gates nothing. The detector work is therefore no longer sequenced behind a T+1 grid; the burst-scale measurement chain (rows 10–15) precedes it instead, and the unconditional universe scan moves from "before capital" to a near-front blocker because under a gate-then-trade design the live false-positive rate is a direct PnL term. The six-weeks-saved argument above still holds on its own terms — D5 accepts that cost knowingly rather than disputing it.

The original ordering note is retained immediately above it, verbatim, labelled *(superseded — retained for the record)*.

## 7.2 `docs/Claude-Code-Operating-Plan.md` §6 — numbering note and the two executed-record rows

> **Numbering, from 2026-08-03 onward.** Rows 8 and up are prompt filenames — row *n* is `prompts/phase_{n}.md`. Rows 0–7 are the original plan slots and are left untouched; they never tracked filenames, because the executed program inserted 0a/0b/0c/1b/1c/2b/5a and re-scoped several phases along the way. The crosswalk for the two plan rows that did get executed under different numbers: the old row 8 (*Measurement 1 — concentration*) ran as **Phase 6**, and the old row 12 (*Event-study grid — T+1*) ran as **Phase 8** in the re-scoped, tradeable-anchor form recorded above.

> | **8** | Event-study grid — forward markouts from tradeable anchors | *(executed)* Markout grid over all D1 events from anchors knowable in real time, bucketed by participation, with survivorship and coverage reported alongside; zero full-table passes | Markout heatmaps; participation buckets | **`phase-8-approved`**, 2026-08-01 |
> | **9** | Path shape, cross-session integrity, clustered inference | *(executed, unmerged)* Cross-session corporate-action flag; separation of the detection-time / holding-period / latency axes; retracement ECDFs at T0…T+3 with ticker-clustered CIs | Retracement ECDFs; axis-separation grid | Branch `phase/9`, pending approval |

## 7.3 `docs/Mom-DB-Strategy-Research-Program.md` §9 — full rewrite (T3d)

Everything between the `## 9. Sequenced Execution Plan` heading and the verbatim closing line:

> Sequenced under D5. Phase numbers are the phase map in `docs/Claude-Code-Operating-Plan.md` §6, which from row 8 onward are prompt filenames (`prompts/phase_{n}.md`).
>
> **Done — Phases 0–7, audit and analysis-readiness.** The §2 audit chain (filter forensics, universe stats, coverage and integrity, quote quality, window flags, canonical spine), closed out by the D4 tick-only quarantine and the Phase 7 readiness pass. The §2.7 deliverable exists. Everything below stands on it.
>
> **Done — Phases 8–9, first forward measurement.** Phase 8 produced the markout grid from anchors knowable in real time, and established that the rejected-candidate population is absent from the archive, so the live false-positive rate is not measurable from what is on disk (§8 item #3). Phase 9 repaired the cross-session price basis, separated the detection-time / holding-period / latency axes, and produced the first retracement measurement. Both are session- and day-anchored, and D5 reads them accordingly: they are archive, not the operative latency budget.
>
> **Next — Phases 10–13, the tape as it actually behaves.** Burst decomposition first (10): the burst timescale is the number every horizon downstream is expressed in, and the burst-relative latency budget replaces the session-anchored one from Phase 6/6b (D5 consequence (b), D5 Amendment A11). Then spread and impact by participation (11), which finally tests the §4.1 compression claim and prices a false positive; halts and LULD (12), which produces the sizing constraint; and the noise floor (13), which is the null distribution any detector is measured against. None of these need a model. All four are §4.3 measurements, re-anchored.
>
> **Then — Phases 14–15, features and the exit prior.** The feature layer (14) precomputes signed flow and impact efficiency once, cached and lag-baked, per §7.1 layer 2 — never recomputed inside a research loop. The burst hazard function (15) turns burst durations into P(death | age): under a long-only strategy on a bull-to-bear flip, this is the exit prior, and D5 budgets it at least equally with entry work.
>
> **Then — Phases 16–18, labels and signals.** Regime labeling with the §5.1.1 perturbation stability test (16) — if labels are unstable, everything after it is built on sand and the sequence stops there. The detector and end-detector together (17), both first-class, with the operating point chosen by expected PnL and false positives estimated on flanking days. Direction signal last (18), measured against the always-long-while-on null, because "detector plus market order" is the hypothesis to beat.
>
> **Last — Phase 19, joint walk-forward.** The full stack under the §7.2 cost model with halts as forced holds; vectorized first, Nautilus for the short list (§7.1 layers 4–5).
>
> **Not in the line — two items that do not wait their turn.**
> - *Unconditional universe scan (Parallel).* Upgraded by D5 consequence (c) from "before capital" to a near-front blocker: it gates the operating-point selection in Phase 17, not just capital, so it cannot be sequenced last. §5.4, §8 items #3 and #4.
> - *T+1 markout grid (Opt-A).* The single day-2 edge-existence pass retained under D5, long-only. It runs when Cooper calls for it and gates nothing.
>
> **Two decisions owed before Phase 17 can be specified.** Whether the entry signal is onset prediction or fast detection and ride (left open by D5; §4.2 condition 4 constrains it). And the archive-vs-live universe mismatch (§8 item #9) — Phase 17's operating point is otherwise chosen on a population the live screen does not reproduce.

## 7.4 `docs/Universe-Decisions.md` — D5 Amendment A11 (T6 disposition, written to Cooper's decision)

> ### D5 Amendment A11 — Phase 6b disposition: archive-only, no new run
>
> **Date:** 2026-08-03
> **Deciding phase gate:** Cooper decision at the D5 redirect (`prompts/redirect_d5.md` T6)
>
> **Correction of the T6 premise.** T6 as written states that `prompts/phase_6b.md` and `config/phase_6b.json` "are currently queued to resume the moment `phase-7-approved` exists, per Amendment A8.2." That premise is stale. Phase 6b has already run and been approved — tag `phase-6b-approved` exists, `prompts/phase_6b_amendment_8.md` is committed, and `results/phase_6b/` is the declared baseline of Phase 8 (`event_minute_bars_v2`, 45,925,350 rows). The live question is therefore not whether to resume 6b, but what standing its completed output has under D5.
>
> **Decision: archive-only, no new run.**
>
> - **6b's session-anchored extended-day decay output is archive.** It stays committed and citable. It is **not** the operative latency budget, exactly as D5 consequence (a) states. Any phase citing a 6b or Phase 6 decay figure labels it as the session-anchored quantity and does not present it as a budget under D5.
> - **No re-run, no re-scope, no successor phase is authorized by this amendment.** The burst-relative latency budget required by D5 consequence (b) will be derived by a phase specified on its own terms.
> - **`event_minute_bars_v2` is unaffected as a data artifact.** A11 demotes 6b's *conclusions*, not its tables. Phases 8 and 9 both build on `event_minute_bars_v2` and remain valid; the D4 rule that every measured quantity is tick-derived is what makes that table load-bearing, and nothing in D5 touches it.
> - **A8.2's terms are not modified.** Its sweep requirement (every spine numeric reference confirmed diagnostic-display only) stands unchanged. A11 adds a disposition; it does not amend A8.2.
> - **`prompts/phase_6b.md` and `config/phase_6b.json` are left exactly as committed** — the historical record of what ran, not a queue entry.
>
> **How to apply:** cite A11 when reusing any `results/phase_6/` or `results/phase_6b/` decay statistic, and state that it is session-anchored and superseded as a budget. Reuse of `event_minute_bars_v2` itself needs no citation.

## 7.5 `docs/Mom-DB-Strategy-Research-Program.md` §8 — risk items #3 and #4, Status and Consequence cells

> Structural — **near-front blocker under D5** (was: partially mitigated by flanking days). Hardened by Phase 8 A10.2d: the rejected-candidate population is confirmed absent from the archive, so the live FP rate is unmeasurable from what is on disk

> Under D5's gate-then-trade design the live false-positive rate is a **direct PnL term, not a caveat** — every markout is conditional on power-law-filter membership, which is not knowable at detection time

> Structural — **near-front blocker under D5** (was: requires unconditional universe scan before capital). The scan cannot be sequenced last

> Detector fire-rate in the wild unknown, so the cost of every false fire is unpriced; under a long-only burst strategy that cost is paid in round-trip effective spread on every wrong gate

## 7.6 `docs/Mom-DB-Strategy-Research-Program.md` — version-history 1.x row

The 2.0 row is Cooper's text, verbatim, and is now fully true (§9 was rewritten by T3d). The placeholder note that flagged it as not-yet-true on the first pass has been removed. This row is mine:

> | 1.x     | 2026-07-13 | Initial spec. No version history was recorded before the 2.0 bump; "1.x" is the retroactive designation used by §3.3's note on the prior ranking. |

## 7.7 `CLAUDE.md` — Pointers additions

The `## Strategy surface (D5)` block itself is Cooper's text, verbatim. These lines are mine:

> - Strategy context: docs/Mom-DB-Strategy-Research-Program.md (v2.0, 2026-08-03 — re-ranked under D5).
> - Standing decisions: docs/Universe-Decisions.md — D1 analysis universe, D2 `clean_window`, D3 analysis
>   clock, D4 tick-only measurement, **D5 strategy surface and horizon class** (2026-08-03).

> - `docs/Claude-Code-Operating-Plan.md` is cited by prompts/phase_0a.md, prompts/phase_0b.md and
>   docs/Research-Library-Map.md but has never existed in this checkout — Cooper holds it externally.
>   Gap confirmed 2026-08-03, `results/redirect_d5/doc_existence_audit.json`.

**⚠ This last pointer is now stale** — the file was supplied and tracked the same day. It reads as if the gap still stands. Flagging rather than silently rewriting Cooper-facing text: say the word and it becomes a one-line pointer to the tracked file.

## 7.8 `docs/Universe-Decisions.md` D5 — heading and metadata lines

> ## D5 — Strategy surface and horizon class
>
> **Date:** 2026-08-03
> **Deciding phase gate:** `phase-7-approved` (documentation redirect, `prompts/redirect_d5.md` — not a phase)

Everything from `**Selected surface:**` onward is Cooper's text, byte-identical.

## 7.9 `docs/Open-Items-Register.md` — three new items

> - **Archive universe vs. intended live universe are different populations.** Opened by `docs/Universe-Decisions.md` D5, consequence (d), 2026-08-03. The archive universe is the q05 power-law filter applied to **completed daily moves**; the intended live universe is a real-time screen at **≥30% from previous close, pre- and post-market inclusive**. These are different populations: the archive's selection variable is only knowable after the session ends, and its RTH-scoped construction (D4's `momentum_pct` exception) does not see the extended-hours moves the live screen is meant to fire on. Consequence: every conditional result in this program is measured on a population the live screen does not reproduce, and live PnL diverges from measured PnL by an unquantified amount. Recorded as risk-register row 9 in `docs/Mom-DB-Strategy-Research-Program.md` §8. **Owner: unassigned.** — logged D5 redirect T5, 2026-08-03.

> - **Unconditional universe scan — upgraded to near-front blocker.** Per D5 consequence (c), 2026-08-03. The scan was previously scoped as "must happen before capital" (§5.4, §8 risk item #4, and the v1.x §9 "Weeks 8+ ... in parallel" line). Under D5's gate-then-trade design the detector's fire-rate in the wild is a **direct PnL term**, so the scan can no longer be sequenced late or in parallel-if-convenient — it gates the operating-point selection of any detector, not just capital. Cross-references risk-register items **#3** (missing counterfactual / near-miss set — hardened by Phase 8 A10.2d, which confirmed the rejected-candidate population is absent from `data/filtered/`, making the live FP rate unmeasurable from what is on disk) and **#4** (circularity of regime frequency). Not scheduled — the phase that takes it on is not yet specified. — logged D5 redirect T5, 2026-08-03.

> - **Entry-signal class undecided — onset prediction vs. fast detection and ride.** Left explicitly open by D5 ("Left open by D5, to be decided before any detector phase is specified"), 2026-08-03. *Onset prediction* fires ahead of the trade-arrival cluster; *fast detection and ride* confirms inside it. The two demand different features, different null distributions, and different latency budgets, so the choice cannot be deferred into the detector phase — it determines what that phase is. §4.2 condition 4 bears directly on it: retail-grade execution rules out sub-second signals but leaves 30-second-to-5-minute horizons intact, which constrains how early an onset call could be acted on at all. **Must be resolved before Phase 17 (detector + end-detector) is specified** — `docs/Claude-Code-Operating-Plan.md` §6. Cooper decision, unassigned. — logged D5 redirect T5, 2026-08-03.

## 7.10 `docs/Open-Items-Register.md` — ARBB row-cap annotation

Appended to the existing `flag_possible_row_cap` item. The item is **not** closed.

> **Priority raised under D5, 2026-08-03:** the row cap is no longer a bounded nuisance on aggregate markouts. D5 makes burst decomposition, concentration curves and spread-vs-participation measurements load-bearing program inputs rather than supporting evidence, and all three are computed from T=0 print counts and print sequences — exactly what a collector row cap truncates. A capped event does not merely lose volume; it loses the tail of the session, which is where burst termination and the bull-to-bear flip live. Item stays open, not closed; the (b) root-cause half is the part that rises.

Also mine: the register's frontmatter `last_reviewed:` changed from `2026-08-01 (Phase 8)` to `2026-08-03 (D5 redirect)`.

## 7.11 `docs/Research-Library-Map.md` — new section and the Operating Plan entry

A `## D5 redirect additions` section listing the four added files and the six modified ones, plus a `docs/` inventory entry for `Claude-Code-Operating-Plan.md` recording that it was cited from Phase 0a onward but only tracked on 2026-08-03, and that its §6 rows 8+ are prompt filenames while rows 0–7 are legacy plan slots. Full text in the diff.

---

## 8. Open for Cooper

1. **The stale `CLAUDE.md` pointer** in §7.7 — it still describes the Operating Plan as missing.
2. **`prompts/phase_0a.md` / `phase_0b.md` unchanged.** They cite the Operating Plan and are now satisfiable, but they are committed phase prompts and were out of this prompt's scope. No action taken.
3. **Phase 9 is unmerged.** `phase/9` carries 9 commits and is recorded in the map as pending approval. It is a separate approval track from this one, and merging these two branches is likely to touch `docs/Research-Library-Map.md` in both.
4. **Two decisions the program now owes** before Phase 17 can be specified, both registered: the entry-signal class, and the archive-vs-live universe mismatch.

Per the Approval Gate: nothing tagged, nothing merged. On approval: tag `d5-redirect-approved`.
