# Phase 3 — Amendment 1

**Branch:** `phase/3` (continue on the existing branch; do not cut a new one)
**Baseline for this amendment:** the committed T2 hard stop (`22d0123`)
**Triggered by:** T2 escalation — 15/50 pinned dev sample v2 events are `event_day_only`, not `full_window`. 14 are 2025 (expected); 1 is `PLBY_2021-02-16` (file1, one of the 287-cohort).

**What this amendment authorizes:**
1. Re-pinning the dev sample as **v3**, adding window-completeness to the eligibility rule. v2 is kept, committed, and untouched.
2. A refinement to the original T3 classification (a `weak_listing_signature` flag).

**What it does NOT authorize:** any change to `in_scope`, any deletion, any change to `coverage_class` semantics, or any universe-level exclusion of `event_day_only` events. Those events stay in the spine, flagged. The dev sample is scaffolding; this fixes the scaffolding, not the universe.

**Supersedes in `prompts/phase_3.md`:** the original **T2** task and its two escalation rows (dev-manifest-missing; dev-event-not-full_window). Original **T1, T3, T4, T5, T6** stand as written except for the T3 refinement in A1-T4 below.

---

## The eligibility decision (baked in — one knob)

v2 eligibility rule (from `config/dev_sample_v2.json`):
`in_scope=TRUE AND trades_ingested=TRUE AND quotes_ingested=TRUE AND flag_window_calendar_bug=FALSE`

**v3 eligibility rule:** v2's rule **AND** `coverage_class='full_window'` **AND** `quotes_full_window=TRUE`.

Rationale: `coverage_class='full_window'` is the trades-window analog of the existing `trades_ingested` conjunct; `quotes_full_window=TRUE` is the parallel for quotes, so the sample is clean for both trade- and quote-derived phases. The pre-2025 pool barely shrinks (Phase 2: 15,476 trades-full_window, 15,377 quotes-full_window pre-2025), so requiring both costs almost nothing. This also makes v3 strictly pre-2025 by construction (0/5,188 2025 events are full_window).

**The one knob:** if you want a trades-only dev sample, drop the `quotes_full_window=TRUE` conjunct. Default as written keeps both.

Everything else — seed 42, the decile stratification scheme, the count of 50 — is **inherited unchanged** from v2's builder. Do not reinvent the stratification.

---

## Tasks

- [ ] **A1-T0 — Commit this amendment**
  Commit `prompts/phase_3_amendment_1.md` to `phase/3` before any other work. Commit message: `phase-3 A1: dev sample v3 re-pin authorization + listing-signature refinement`.

- [ ] **A1-T1 — Pre-repin safety check (was any reported result computed on the dev sample?)**
  Scan every committed `results/phase_*/digest.json` and `results/phase_*/REPORT.md`. For each, determine whether any **headline / reported metric** is sourced from the dev tier — i.e. its `source` (or the number's provenance in REPORT) points at `filtered_trades_dev` / `filtered_quotes_dev`, a `dev_sample` artifact, or a dev-tier run. Passing mentions of "developed on the dev tier, full-tier numbers below" are **not** a hit — only headline numbers whose value came from the 50-event sample.
  Write `results/phase_3/artifacts/a1_dev_usage_scan.json`: per phase, list of hits (metric name + source) or empty.
  - [ ] A1-T1a — **Escalation check:** if any headline metric is sourced from the dev tier → **hard stop.** Commit, post the full hit list, await instruction. (Re-pinning would break the comparability of those numbers; that is Cooper's call, not the agent's.)
  - [ ] A1-T1b — Commit.

- [ ] **A1-T2 — Locate the v2 builder**
  Find the committed script that produced dev sample v2 (search `research/` and `src/` for the writer of `config/dev_sample_v2.json` / the `filtered_trades_dev` materialization). Record its path in the digest.
  - [ ] A1-T2a — **Escalation check:** if the builder cannot be located **unambiguously** → hard stop. Commit, post candidate paths, await instruction. Do **not** reconstruct the stratification from scratch — divergence in the draw is exactly what must be avoided.

- [ ] **A1-T3 — Build dev sample v3**
  Copy the v2 builder to a v3 builder (`research/phase_3/build_dev_sample_v3.py` or the project's convention). Change **only** the eligibility `WHERE` clause to add `AND coverage_class='full_window' AND quotes_full_window=TRUE`. Keep seed 42, the decile-stratification logic, and count=50 byte-for-byte identical. Deciles are computed over the v3-eligible (post-filter) in-scope population, same as v2 computed them over its eligible population — inherit that logic, don't redefine it.
  Outputs: `config/dev_sample_v3.json` (manifest: 50 events, seed, rule, decile assignments), and re-materialize `filtered_trades_dev` / `filtered_quotes_dev` from the v3 event list **only if** the builder is the thing that materializes them; otherwise leave the dev tables and just write the manifest, and note which.
  - [ ] A1-T3a — Descriptive overlap report (no escalation): of the 35 v2 events that were already `full_window`, how many reappear in v3; total v2∩v3; the 15 dropped; any newly-drawn events. Write to `results/phase_3/artifacts/dev_sample_v3_vs_v2.json`. This is a description, not a pass/fail.
  - [ ] A1-T3b — Verify every v3 event satisfies the full rule (all 50 `full_window` AND `quotes_full_window=TRUE`). Any failure → hard stop.
  - [ ] A1-T3c — Commit.

- [ ] **A1-T4 — Refine original T3 classification: add `weak_listing_signature`**
  The 287-cohort classification in original T3 stands. Add one flag, mirroring the existing weak-delisting signature (original T3a) on the opposite edge:

  For every cohort event labeled `backward_missing` (all missing offsets ≤ T-1), compute `weak_listing_signature = TRUE` iff the ticker's **earliest** observed trade session anywhere in `filtered_trades` (spine-joined, `in_scope=TRUE`, across all of that ticker's own event windows) is **later than** the event's T-3 XNYS session date — i.e. the pre-event flank is absent because the ticker was not yet trading, not because collection failed.
  Report this exactly as a **weak within-archive listing signature**, with the same verbatim scope caveat as the delisting signature: absence of pre-event data is *consistent with* late listing but is not proof — within an event-conditional archive it is indistinguishable from flank-collection loss without external reference data, which is out of scope.
  Add `weak_listing_signature` as a column in `classification.parquet` and a count in `classification_summary.json`. **Do not** create a new label or change the 6-label precedence — this is a flag on `backward_missing`, symmetric to how `weak_delisting_signature` flags `forward_missing`.
  Note in REPORT: `PLBY_2021-02-16` is the known exemplar (SPAC merger with MCAC consummated 2021-02-10; began trading as PLBY on Nasdaq 2021-02-11; event day 2021-02-16 → T-3 predates the ticker's existence). State this as the illustrative case for the flag, not as a per-event external lookup performed on the cohort.
  - [ ] A1-T4a — Commit.

- [ ] **A1-T5 — Update the canonical-sample pointer**
  Wherever the repo names the canonical dev sample as v2 (check `CLAUDE.md` first), update the pointer to v3, one line, additive. Append one line to `docs/Open-Items-Register.md` noting the v2→v3 re-pin, the reason (v2 eligibility predated `coverage_class` and never screened window completeness), and that v2 remains committed as the historical sample. Do **not** edit strategy docs beyond the pointer.
  - [ ] A1-T5a — Commit; confirm working tree clean.

**Resume:** after A1-T5, proceed to original **T3 → T4 → T5 → T6** as written in `prompts/phase_3.md` (T3 now emits `weak_listing_signature` per A1-T4). The 287-cohort classification is independent of the dev sample and is unaffected by the re-pin.

---

## Revised escalation criteria (replaces the two superseded T2 rows)

| Condition | Threshold | Action |
|---|---|---|
| Any headline/reported metric in a committed digest/REPORT sourced from the dev tier | ≥ 1 | Hard stop — commit, post hit list, await instruction |
| v2 builder not locatable unambiguously | any | Hard stop — commit, post candidate paths, await instruction. Do not reconstruct from scratch. |
| Any v3 event fails `full_window` AND `quotes_full_window=TRUE` | ≥ 1 | Hard stop — commit, post the failing rows, await instruction |
| Any write to the data root, DB, or canonical **view** | any | Hard stop — this amendment re-materializes dev **tables** only if the v2 builder already did; it never modifies `momentum_events_canonical`, `filtered_trades`, or `filtered_quotes` |

All other original Phase 3 escalation rows (spine guard ≠ 20,951; cohort ≠ 287/386; unclassified > 30%) remain in force.

---

## Output files (additions)

| File | Description | Status |
|---|---|---|
| `prompts/phase_3_amendment_1.md` | This amendment | [ ] |
| `results/phase_3/artifacts/a1_dev_usage_scan.json` | Prior-use safety scan result | [ ] |
| `config/dev_sample_v3.json` | v3 manifest (50 events, seed 42, v3 rule, deciles) | [ ] |
| `research/phase_3/build_dev_sample_v3.py` | v3 builder (v2 builder + one WHERE conjunct) | [ ] |
| `results/phase_3/artifacts/dev_sample_v3_vs_v2.json` | Descriptive v2↔v3 overlap | [ ] |

`config/dev_sample_v2.json` and its builder are **not** modified.

---

## Reporting (additions)

On completion, in addition to the original Phase 3 report, post:
1. Prior-use scan result: hits per phase, or "none — dev sample used as speed harness only."
2. v3 build: eligibility rule used, pool size after filter, v2∩v3 count, the 15 dropped, any new draws.
3. `weak_listing_signature` count among `backward_missing`, with the verbatim weak-signal caveat and the PLBY exemplar note.
4. Verification block for the v3 manifest (builder path, repro command, config hash) and for the prior-use scan.

Descriptions of what's visible are allowed. No recommendations. No statement about what the listing/delisting flags imply for T+1 survivorship — counts and descriptions only.

---

## Approval Gate

Unchanged from `prompts/phase_3.md`. Do not begin any follow-on work — including any dev-sample action beyond v3, any `coverage_class` semantic change, or any recollection scoping — until Cooper has reviewed results and given explicit approval.
