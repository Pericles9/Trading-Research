# Phase 10c — Stage 1: Multi-Kernel Sub-Burst Detection

**Governing document:** Agent Prompt Standard v1.3
**Branch:** `phase-10c-stage-1`
**Precedes:** nothing. Stage 1 is the first stage to produce sub-bursts. Stage 0 and 0b measured
the interval landscape and produced none.

**Prerequisite — commit this prompt and the frozen config before any code runs.** Per standing
git discipline: commit before run (prompt and config both), commit at every task boundary, commit
before escalation, tag at the approval gate.

---

## §0 — What Stage 1 is for

Stage 0b established that every event in the cohort produces a computable trough, that both
segments clear the void reference, and that the interval landscape is multi-modal (median 10
surviving peaks per event, up to 17).

**Stage 1 produces sub-bursts for the first time under the clock-time normalization window**, across
the full nine-cell grid, and reports what the kernels show relative to each other.

**Stage 1 does not:**
- Combine, merge, or collapse kernel outputs into a single per-event signal. Explicitly out of
  scope (Amendment 1, deferred items).
- Select a threshold variant. Carrying three in parallel is the decision; selecting one is a later,
  separate decision on stated grounds (Amendment 3 A2).
- Characterize any result evaluatively. The agent describes the picture; Cooper holds all reads.

---

## §1 — Frozen configuration

### Class E — economically derived, set before Stage 0

| Parameter | Value | Provenance |
|---|---|---|
| `D3_window_basis` | centered | Committed; trailing variants forbidden. Non-causal debt parked for Phase 17. |
| `D13_void_parameter` | threshold: `null` | Deliberate and permanent. Void parameter ranks; it never gates. 0.70 is the retired v4 value and must not appear anywhere. |
| Tie handling | `collapse_same_timestamp` | Reference variant. Zero intervals cannot occur by construction. |
| Histogram smoothing | none | Any bandwidth reintroduces the free parameter D9 exists to avoid. |
| Prominence floor | per-peak Poisson test | Prominence in counts > √k at its own bin. No global constant (A2.4 Part 1). |
| Trading day | (prior XNYS session close, this session's close] | Amendment 2A. `session_close` from `exchange_calendars`; no fixed clock constant. |
| Segments | `evening` / `premarket` / `rth` | Amendment 4 A2. `post` and `outside_redefined_day` retired. 20:00→04:00 measured-empty across all variants. |
| Auction assignment | codes {8, 15} → originating session, all trades | Amendments 5–6. Overrides the timestamp rule via `assign_segment()`. |

### Class M — measurement derived, set at Stage 0 approval

| Parameter | Value | Provenance |
|---|---|---|
| `A2.8.D4_median_precision_factor` | F = 1.5 | Amendment 1. Derived floor 156 prints (RTH), 94 (premarket). |
| `D5_first_kernel` | 8 minutes | Amendment 1. RTH floor-clearing rung. Reconfirmed with ACET genuinely in the RTH pool. |
| `D6_kernel_grid` | {2, 8, 32} minutes | {D5/4, D5, D5×4}. Base-2 rungs 1, 3, 5. Low ≥ 1, high ≤ D11 = 64. Confirmed under all three threshold variants. |
| Threshold variants | {1.25, 1.30, 1.35} | Amendment 3 A. All three carried; none selected. |
| Data floor label | `insufficient_context` | Per event/kernel pair below the derived floor. Carried, never given a fallback estimate. |

### Population

Dev sample: 56 events (50 primary + 6 sidecar), seed 42, `dev_v4_primary` manifest, stratified by
`t0_print_count` decile. **Manifest is variant-independent** — drawn before detection existed, so
no circularity between sample selection and the measured quantity.

Analysable subset varies by variant:

| Threshold | Anchored | rth | premarket | unlabelled |
|---|---|---|---|---|
| 1.25 | 54/56 | 37 | 16 | 2 |
| 1.30 | 53/56 | 37 | 15 | 3 |
| 1.35 | 45/56 | 28 | 15 | 11 |

**Every count in every output names its population inline** (R1 convention). No figure appears
beside a breakdown computed on a different denominator.

---

## §2 — Pre-run resolution required

- [ ] **T0 — Denominator clarification, before any Stage 1 computation.**
  Amendment 6's closure reports `n_rth 36→37` with ACET added to the floor-derivation pool. The
  dev-manifest table reports `rth 37` under 1.25/1.30 *excluding* ACET. Two different 37s. State
  which pool the 36 is, and identify the RTH event present in the manifest but absent from the
  floor derivation, with the reason. Not a stop; a naming requirement.

---

## §3 — Tasks

### T1 — Sub-burst extraction, nine cells

For each of the nine (variant × kernel) cells, per event, run the full pipeline: centered
clock-time local median → normalized log-interval histogram → per-peak Poisson prominence →
peak-finding → void parameter per trough → threshold → sub-burst runs.

- [ ] **T1a** — Per event/cell: threshold (or label), void parameter at the chosen trough, surviving
  peak count, sub-burst count, and the `insufficient_context` / `no_threshold` label where either
  applies. Labels are distinct and must not be merged: `insufficient_context` means the window held
  too few prints; `no_threshold` means the histogram produced no usable trough.
- [ ] **T1b** — Per sub-burst: start, end, duration, print count, share of the event's price move.
- [ ] **T1c** — Label population report: count and share of each label, per cell, per segment, with
  n stated. Expect non-trivial `insufficient_context` in RTH at the 2-minute kernel by construction
  — the floor clears at 8 for the median RTH event. Report it; do not treat it as a defect.
- [ ] **T1d** — Commit.

### T2 — Anchor-independent outputs

Reported together, separately from T3. These do not depend on where T=0 sits.

- [ ] **T2a** — Threshold location distribution, per cell, per segment.
- [ ] **T2b** — Sub-burst duration distribution, per cell, per segment. Log scale.
- [ ] **T2c** — Spacing between consecutive sub-bursts, per cell.
- [ ] **T2d** — Void parameter distribution at the chosen trough, per cell.
- [ ] **T2e** — **Cross-variant agreement on these quantities.** The three variants should agree
  closely here, since none of T2a–T2d depends on the anchor. Report the agreement. Disagreement
  would itself be a finding and must be stated, not smoothed.
- [ ] **T2f** — Charts 01–04. Commit.

### T3 — Anchor-relative outputs

Reported separately, each carrying the inherited variant uncertainty stated alongside it.

Measured anchor-timing deltas (Amendment 3 A1): median 112.9 s (1.25↔1.30), 313.6 s (1.25↔1.35),
53.4 s (1.30↔1.35); max 13,856 s. **The 2-minute kernel is 120 s.** The median disagreement about
where the origin sits is comparable to the smallest kernel and to a third of the 8-minute kernel.
Only the 32-minute kernel is comfortably larger than the widest pair's median.

- [ ] **T3a** — Sub-burst position relative to detection, per cell.
- [ ] **T3b** — Near-anchor print density, per cell, per segment.
- [ ] **T3c** — Which sub-burst is first, and which is largest by move-share, since detection.
- [ ] **T3d** — **Every T3 output carries the anchor-delta figures in its caption.** A T3 quantity
  reported without the inherited uncertainty beside it is a Chart Contract violation.
- [ ] **T3e** — Charts 05–07. Commit.

### T4 — Cross-kernel interpretation

Reading kernels side by side. **No combining rule. No single per-event number.**

- [ ] **T4a** — **Threshold location vs. kernel window size, per event.** Plot the chosen trough's
  absolute interval location against kernel width. Flat across kernels indicates the void gate is
  locating a real structural interval. Scaling ~1:1 with window width indicates the trough is
  landing wherever the local median puts it — the multi-kernel form of the free-parameter problem
  that ruled out the Allan/Fano knee. Report the relationship; do not characterize it.
- [ ] **T4b** — **Void parameter strength by kernel, per event.** Which kernel widths produce a
  clean, well-separated split for a given event and which produce mush or `no_threshold`. Expect
  this to differ by event; that is a finding, not a defect.
- [ ] **T4c** — **Heterogeneity.** Whether the legible kernel scale from T4b covaries with event
  duration, segment, or detection price decile.
- [ ] **T4d** — Charts 08–10. Commit.

### T5 — Descriptive-only reporting (no gates)

- [ ] **T5a** — **Sub-burst count vs. T=0 print count**, per cell. Spearman and log-log slope,
  scatter with raw points. **No threshold, no pass/fail, no hard stop.** A positive relationship is
  expected — a bigger, longer, more active event produces more sub-bursts under any reasonable
  definition. Reported as context (Amendment 1, row 1 retired as a gate).
- [ ] **T5b** — **A2.7 silent-failure rate**, per cell: share of events where the tallest peak at or
  below the burst-envelope boundary is other than the fastest. Descriptive. Carry the caveat: the
  58.0% / 64.0% figures are **not** comparable to Stage 0b's 30%, which measured a different
  statistic (whether the later of the top-two peaks was taller, with no boundary in existence).
- [ ] **T5c** — Commit.

### T6 — Animated histogram

- [ ] **T6a** — Per event, the local normalized log-interval histogram evolving across the session:
  density, detected peaks, chosen trough, void parameter. Frame-scrubbable HTML (Plotly animation
  frames or slider), consistent with existing chart tooling — not a rendered video.
- [ ] **T6b** — Synced to the existing tape-review time axis as an added panel, not a new chart
  grammar.
- [ ] **T6c** — **Multi-kernel layout: build both** — one animation per kernel, and a combined
  comparative view — on a handful of events, and post both for Cooper's choice. Not a decision the
  agent makes (outline open question 4).
- [ ] **T6d** — Produce for the full dev sample under the layout Cooper selects. Commit.

### T7 — Row 0: visual review against the tape

- [ ] **T7a** — Produce the tape-review chart set. **Do not evaluate it.**

**Row 0 is Cooper's, and it overrides the numeric rows in either direction.** It has been the only
criterion that fired correctly across all Phase 10 method families — numeric criteria passed in
every version while both arms were wrong.

---

## §4 — Escalation table

Every row satisfies the four-check audit (measurable, threshold set, reachable, non-contradictory).

| # | Condition | Threshold | Action |
|---|---|---|---|
| 0 | Visual review against the tape | `[Cooper]` | Reserved. Agent produces charts, never evaluates. |
| 1 | Any void parameter cutoff applied anywhere | any | **Hard stop.** `D13_void_parameter` is null, deliberate and permanent. |
| 2 | Any trailing-window implementation | any | **Hard stop.** D3 is centered; trailing forbidden. |
| 3 | Kernel or variant dropped, promoted, or selected on how its results look | any | **Hard stop.** Amendment 3 A2 pre-registration. |
| 4 | Kernel outputs combined into a single per-event signal | any | **Hard stop.** Out of scope for Phase 10c. |
| 5 | Any summary statistic stated without its supporting distributional chart | any | **Hard stop.** Chart Contract. |
| 6 | Any count stated without its population named inline | any | **Hard stop.** R1 convention. |
| 7 | Any T3 quantity reported without the anchor-delta uncertainty in its caption | any | **Hard stop.** |
| 8 | Any condition code interpreted beyond `docs/massive_trade_conditions.json` | any | **Hard stop.** Codes absent from the file have no offline meaning. |
| 9 | Any result characterized evaluatively rather than described | any | **Hard stop before posting.** |
| 10 | Prose asserts a membership, inclusion, or exclusion that the code does not assert | any | **Hard stop.** See §5. |
| 11 | Any write to an archived drive | any | **Hard stop.** |
| 12 | Any spine OHLC or volume numeric enters a computation | any | **Hard stop.** D4 quarantine. |
| 13 | Median sub-burst duration below `[Cooper]` at the 8- or 32-minute kernel | `[Cooper]` | Escalate. The v4 failure signature was 349 ns; a repeat at a clock-time kernel is a finding requiring a decision, not a patch. |
| 14 | `insufficient_context` share exceeds `[Cooper]` in any cell | `[Cooper]` | Escalate. |
| 15 | `no_threshold` share exceeds `[Cooper]` in any cell | `[Cooper]` | Escalate. |
| 16 | T4a shows threshold location scaling ~1:1 with kernel width | `[Cooper]` slope band | Escalate. Report the relationship; the read is Cooper's. |
| 17 | Any parameter marked `[Cooper]` filled by the agent | any | **Hard stop.** |
| 18 | Any agent-side workaround applied in place of stopping and escalating | any | **Hard stop.** |

---

## §5 — Verification Block

Standard requirements, plus one addition specific to this phase's history.

**Waterfall reconciliation** — raw prints → tie collapse → floor absorption → intervals, per cell,
with every stage's count and its population named.

**Class M held** — confirm at close: A2.8.D4, D5, D6, and the variant set unchanged from §1.

**Executable assertions, not prose claims.** Phase 10c has produced two defects where the written
record and the executed path diverged: `drop_duplicates` silently selecting variant 1.25 with no
recorded decision, and Amendment 4's re-derivation asserting ACET was in the RTH pool while the
segment loop had it bucketed `evening`. Both were true in spirit and false in execution; both were
found by unrelated later work rather than by verification.

**Requirement:** where a verdict claims something was included, excluded, or held fixed, the script
must `assert` it and fail loudly. Prose is not verification. Minimum assertions for Stage 1:

- Every event in the analysable subset appears in exactly one segment bucket per variant.
- Auction-code events land in the segment `assign_segment()` assigns, not the timestamp default.
- No variant's rows were deduplicated away at load.
- Class M values at close equal Class M values at open.

**Chart Contract** — Plotly, standalone HTML, one chart per file, n per bucket always, distribution
never centre-only, outliers shown never clipped, log scale where multiplicative, caption carries
sample + filters + config hash. Kaleido-verified before commit.

**Digest Contract** — `results/phase_10c/digests/stage1_digest.json`. Every figure carries its
population. No evaluative language.

---

## §6 — Carried forward, not blocking

- `det_ns_*` stored as float64 (256 ns quantization); int64 repair outstanding at source. Phase
  10c unaffected — nearest-match recovers all post-close anchors at 0 ns residual, and the
  timestamp-resolution chain is int64 end to end.
- Eligible-pool gap: 15,299 eligible against D14's 20,951 canonical in-scope events; 5,652 events
  (27%) unexplained. Required before any full-population run.
- Auction rule {8, 15} is empirical plus semantic, not validated.
- Odd-lot / fragmentation hypothesis and the two unrun measurements — recorded in
  `docs/Open-Items-Register.md`, deliberately not acted on in Phase 10c.
- `A2.7.D17_burst_envelope_boundary` — delivered in a3fe68b, pending Cooper's read.
