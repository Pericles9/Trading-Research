# Fundamentals sources — Build F1

Companion to `prompts/fundamentals_f1.md`. Tracked copy of record for `data/raw/fundamentals/` and
`data/fundamentals/`'s provenance, per the same `docs/data/` convention as `docs/data/Schema.md`
(`/data/` is wholly gitignored; this file is where the record lives).

## Status

Pre-flight only. Source schemas below are filled in as F1-T2 (Massive) and F1-T3 (SEC EDGAR) actually
run — this file is created now, empty of fetched-schema detail, so the decisions that must be recorded
*before* those tasks run have a committed home from the start.

## Identity key

`event_id = f"{ticker}_{event_date_canonical}_{momentum_pct:.2f}"` — reused verbatim from
`research/phase_10/common.py:215`. No second convention for the same concept exists in this build.

## t0 anchor (D33)

Tiered construction — see `docs/Universe-Decisions.md` D33 for the full reasoning and
`config/fundamentals_f1.json`'s `t0_spine` block for the exact artifact paths and thresholds:

1. `det_ns_poll1` from `results/phase_10/artifacts/v2_r13_detection.parquet`, threshold 1.3 (matching
   `config/phase_10_v4.json`'s own pin for this artifact) — 114 events.
2. `a102_detection_anchors.parquet`'s `det_minute`/`det_segment`, coarsened to nanosecond-at-minute-start
   via the pinned XNYS calendar — up to 15,763 events cumulative.
3. First regular-session trade of `event_date_canonical`, read fresh from `filtered_trades` — the
   remainder.

## Massive vendor pull (F1-T2)

- Credential: `.secrets/polygon_api_key.txt`, read via `research/fundamentals_f1/common.py:load_massive_api_key()`.
  Never hardcoded, printed, or logged. **Not** the pattern in
  `data/collection_scripts/collect_massive_data.py`, which embeds a live key in plaintext — that file
  is not reused or referenced by this build.
- Network authorization: `docs/Universe-Decisions.md` D14 Amendment A1, scoped to this task only.
- Per-source schema: **filled in at F1-T2e**, once the pull actually runs.
- Float endpoint (`/stocks/vX/float`): archived at F1-T2c for orientation only. **Banned from
  `event_fundamentals` or any downstream table by D27.**

## SEC EDGAR pull (F1-T3, F1-T4)

- Network authorization: D14 Amendment A1, scoped to this task only.
- User-Agent: **PENDING** — set in `config/fundamentals_f1.json`'s `sec_edgar.user_agent` before F1-T3
  runs. SEC requires a descriptive User-Agent with a real contact address on every request.
- Per-source schema: **filled in at F1-T3/F1-T4**, once the pull actually runs.

## Declared dilution form set (F1-T3e)

**PENDING finalization** — starting set in `config/fundamentals_f1.json`'s `dilution_form_set` block
(the 424B family, S-1/S-3 and their amendments, 8-A registrations, 8-K Item 3.02). Confirmed here, not
left as an inline literal in code, per the work order's own requirement. Finalize before F1-T3e runs.

## Cooper-set thresholds (F1-T4 gate)

Neither has been set yet. **F1-T4 does not run until both are recorded here with Cooper's actual
values** — the placeholders in `config/fundamentals_f1.json` are suggestions, not defaults to adopt
silently:

- `filed_stale_days` — placeholder 45. Governs `shs_quality`'s `filed_exact` vs. `filed_stale` split.
- `shs_quality_coverage_floor` — placeholder 0.70. Escalation row 5 in `prompts/fundamentals_f1.md` §6.

## Vendor-vs-SEC share count disagreement (F1-T4d)

**Filled in once F1-T4 runs.** Reported, not reconciled — a systematic disagreement is itself a finding
about the sources.
