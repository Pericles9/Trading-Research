# Phase 0b Report — Harness Setup

**Branch:** `phase/0b` (from tag `phase-0a-approved`) | **Commits:** 11 (list below) | **Status:** Complete, awaiting Cooper's review/approval per the Approval Gate.

## 1. T1 findings summary + hosting decision

T1's three-pass search (both nested repos' working trees, both repos' full git history, rest of E:\ outside `data/`) found `src/data/db.py`/`ingest.py`/`paths.py`/`prepare_database_split.py` **nowhere** — the "missing everywhere" hard stop. T1d extended the search to all of D:\, found `D:\Trading Research\src\data\` (uncommitted/untracked working-tree state, no clean commit hash), and confirmed content matches `data/Schema.md`'s documented interface exactly. **Hosting decision resolved by elimination**: "vendor from nested repo" wasn't available (neither has this code), "rewrite" was moot once intact code was found — leaving "copy with a provenance note" as the only live option, so T2 proceeded on that basis without a further question.

## 2. DuckDB state before/after this phase

| Table | Before (Phase 0a end) | After (Phase 0b end) |
|---|---|---|
| `filtered_trades` | 4,899,401,773 | 4,899,401,773 (unchanged) |
| `filtered_quotes` | 3,775,991,856 | 3,775,991,856 (unchanged) |
| `raw_quotes` | 1,757,761,017 | 1,757,761,017 (unchanged) |
| `collection_stats` | 1 | 1 (unchanged) |
| `symbols_metadata` | 2 | 2 (unchanged) |
| `momentum_events` | did not exist | 23,268 (new, T4) |
| `dev_events` | did not exist | 50 (new, T5) |
| `filtered_trades_dev` | did not exist | 8,198,488 (new, T5) |
| `filtered_quotes_dev` | did not exist | 7,152,287 (new, T5) |

## 3. Dev-sample stratification

| Decile | Eligible (of 17,203 total eligible) | Selected |
|---|---|---|
| 0 | 1,721 | 5 |
| 1 | 1,721 | 5 |
| 2 | 1,721 | 5 |
| 3-9 | 1,720 each | 5 each |

Eligibility waterfall: 23,268 `momentum_events` rows → 17,203 with a matching `data/filtered/{ticker}_{date}_{momentum_pct:.2f}/` folder containing both `trades.parquet` and `quotes.parquet` → 50 selected (5/decile, seed=42). Full detail: `results/phase_0b/artifacts/dev_sample_build.json`.

## 4. T5d timing

Representative dev-tier query (per-event trade count + minute-bucketed volume, all 50 events): **5.31s**, 123,145 rows returned — well under the 60s target and the 600s hard-stop threshold.

## 5. Escalation check table

| Criterion | Threshold | Observed | Pass/Fail |
|---|---|---|---|
| Data-layer files missing everywhere | any of 3 core files missing | Fired at T1 (E:\ + nested-repo search) → resolved by T1d (found on D:) before T2 executed | Resolved, not a live escalation |
| Multiple conflicting data-layer versions | non-trivial diffs | Only one copy found anywhere (D:); single commit in that repo's history ever touched these files | PASS |
| E: DuckDB row counts vs. `Schema.md` | any table differs | Exact match on all 5 pre-existing tables (T1b and T2's `--verify-only` both confirm) | PASS |
| `momentum_events` 3-way count | any mismatch | 23,268 = 23,268 = 23,268 | PASS |
| `momentum_pct` nulls | > 0 | 0 | PASS |
| Eligible events per decile | < 5 (per_stratum) | min 1,720 | PASS |
| Dev sample rebuild (T5c) | not byte-identical | SHA256 identical across two fresh runs | PASS |
| Representative dev-tier query (T5d) | > 600s | 5.31s | PASS |
| Digest round-trip (T6c) | Phase 0a digest fails validation | **Failed** `headline_metrics_present` — reported per the escalation table, Phase 0a's digest not edited | Reported as finding, not a blocker |

## 6. The standard-document gap (carried through this whole phase)

`docs/Agent_Prompt_Standard.md` doesn't exist at that path. The only copy found anywhere (E: or D:) is `scanner-epg-momentum/backtest/docs/Agent_Prompt_Standard (1).md` — v1.1, dated 2026-05-10, inside a nested repo this program treats as independent and read-only. It does not define "§10 Verification Block" or "§11 Digest Contract," both referenced by name in `prompts/phase_0a.md` and `prompts/phase_0b.md`. This matches an earlier reference in this program to "prompt standard v1.2" — a version that wasn't found anywhere this search reached. `docs/Mom-DB-Strategy-Research-Program.md` likewise doesn't exist anywhere found. `CLAUDE.md`'s Pointers section states both gaps plainly rather than pointing at fabricated locations. `research/phase_0b/validate_digest.py` was built from the one concrete spec fragment that does exist (`prompts/phase_0b.md`'s own T6a task text) plus `results/phase_0a/digest.json`'s actual field usage.

## 7. Output files

| File | Status |
|---|---|
| `config/phase_0b.json` | Done |
| `config/dev_sample_events.csv` | Done — pinned, byte-identical on rebuild |
| `results/phase_0b/artifacts/data_layer_search.json` | Done — E:\ search, zero matches |
| `results/phase_0b/artifacts/data_layer_search_d_drive.json` | Done — D:\ search, 4/4 found |
| `results/phase_0b/artifacts/duckdb_state_check.json` | Done — clean match |
| `results/phase_0b/artifacts/momentum_events_load.json` | Done |
| `results/phase_0b/artifacts/dev_sample_build.json` | Done |
| `results/phase_0b/artifacts/dev_tables_materialized.json` | Done |
| `results/phase_0b/artifacts/digest_roundtrip_check.json` | Done |
| `CLAUDE.md` | Done — 54 lines |
| `research/phase_0b/validate_digest.py` | Done |
| `.claude/commands/{digest,verify,gate}.md` | Done |
| `results/phase_0b/charts/01_dev_sample_stratification.html` | Done |
| `results/phase_0b/charts/02_dev_sample_event_sizes.html` | Done |
| `results/phase_0b/REPORT.md`, `digest.json` | Done (this file; digest passes its own validator, 61 lines) |

## 8. Commit list

```text
98d6598 docs: Phase 0b prompt + dev-sample config
6f5b3d0 data: Phase 0b T1 - data access layer not found anywhere (hard stop)
11c7d99 data: Phase 0b T1d - data access layer found on D:, unique copy
2a63cd2 feat: Phase 0b T2 - recover src/data/ data access layer from D:
866dea9 fix: .gitignore data/ rule was also matching src/data/
c627ec1 docs: Phase 0b T3 - add CLAUDE.md standing constraints
2bad6cb data: Phase 0b T4 - momentum_events loaded, 23268 rows, 3-way match
2e1c953 data: Phase 0b T5a - pinned dev sample event list (50 events)
585647a data: Phase 0b T5 - dev tables materialized, charts, T5d timing
ec90609 feat: Phase 0b T6 - digest validator, slash commands, round-trip check
```

(A final commit follows this REPORT.md + digest.json.)
