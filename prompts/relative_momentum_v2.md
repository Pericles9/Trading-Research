# Relative momentum — build v2: absolute floor, then cross-sectional rank

**Date:** 2026-09-21 · **Type:** build. **Supersedes v1, which was never sent.** v1's Fix 1 made the
level gate causal but left it relative — a percentile of ratios is still a ratio, and it fails on a dead
tape exactly like the thing it was supposed to catch. v2 replaces it with an absolute floor.

> **Filing note, added by the v2 run, not part of the brief as authored.** Filed here so
> `config/relative_momentum_v2.json`'s `_meta.prompt` citation resolves. **Record correction:** v1 *was*
> sent, built, committed and pushed on 2026-09-18 (`a97f06e`, branch `explore/relative-momentum-v1`).
> Correction 1 (2026-09-21) accepted this both ways and directed that v1's population and D1-concurrency
> artifacts be reused. Result: `results/relative_momentum/v2/REPORT.md`. The supplied pseudocode and
> Correction 1 are reproduced in `config/relative_momentum_v2.json`.

---

## The architecture

```
candidates at tau
      |
      v
ABSOLUTE FLOOR  — hard conditions, all in units, all AND'd
      |
      v
survivors  ──(empty)──> NO_TRADE
      |
      v
CROSS-SECTIONAL RANK  — relative volume, highest wins
      |
      v
one trade
```

**Order is the point.** The floor runs first and is absolute. Ranking only ever operates on survivors, so
a name can no longer win a contest among corpses. And the system can now return **NO_TRADE**, which the
v0/v1 design structurally could not — ranking always names a winner.

**One consequence worth noting: the floor needs no warmup.** It references no historical distribution, so
there is no burn-in period and no "first 250 observations behave differently." It works on day one, live.

## Gate 1 — the absolute floor

Full algorithm as specified in the pseudocode. Quantities, all unit-bearing, measured causally in a
600-second trailing window ending at `tau`:

| condition | quantity | threshold | source |
|---|---|---|---|
| `too_few_prints` | print count | `MIN_PRINTS` | **declared, laddered** |
| `thin_notional` | Σ price × size, dollars | `INTENDED_SIZE_USD / PARTICIPATION_CAP` | derived |
| `single_venue` | distinct executing venues | 2 | structural |
| `dead_book` | NBBO update count | `MIN_QUOTES` | **declared, laddered** |
| `price_too_low` | last print price | `PER_SHARE_COST_USD × 10000 / MAX_PER_SHARE_COST_BP` | derived |
| `spread_too_wide` | median spread, bp | `TOTAL_COST_BUDGET_BP − MAX_PER_SHARE_COST_BP` | derived |
| `no_depth` *(if available)* | dollar depth at touch | `CLIP_SIZE_USD × DEPTH_MULTIPLE` | derived |

**Print count is a primary condition, not a degenerate-case catch.** Jones, Kaul & Lipson (1994) and the
literature following it find trade count carries the activity information and volume adds nothing beyond
it. One 50,000-share block and 200 separate prints are identical notional and completely different
amounts of attention.

**The two declared thresholds are laddered, not chosen.** `MIN_PRINTS` and `MIN_QUOTES` have no economic
derivation available — say so rather than dressing up a guess. Carry each as a declared 3-rung ladder,
read side by side, no rung privileged. If the result only exists at one rung, the rung is the finding.

**`MAX_SPREAD_BP` must be calibrated against this universe's actual spreads, not intuition.** The SEC's
small-cap study reports median quoted spreads of 6.22–113.52 cents for sub-$100M-cap names. A ceiling set
from a mental model of normal stocks rejects the entire population.

**Not built, deliberately:** Amihud illiquidity (Lou & Shu show the dollar-volume denominator carries it —
the price-impact construct adds nothing and explodes on a thin tape), VPIN (wrong shape, not absolute),
sub-penny retail identification (Rule 612 sets the minimum increment at $0.0001 below $1.00, so sub-penny
prices are the normal tick grid there — it would be silently broken in exactly the cheapest names).

## Gate 2 — cross-sectional rank

Unchanged from v0: **relative volume**, 10-min trailing, E2's 3-session baseline, highest among live
candidates. Liveness = the gate's own window-close definition.

Relative volume stays a ratio, and that's correct — **it is now only a ranking key among survivors, never
a floor.** The pathology it caused in v0 was being asked to do a job it can't do.

## Population fix

**Gap gate on.** v0 ran with `gap_gate_enabled: false` on all 1,027 events — entries as low as −23%
intraday, not the program's +30% definition. Re-run with it enabled. State the run/config used and its
coverage.

## Tasks

**T1 — Build and run the floor + rank pipeline** on the gap-gated population, the gate's own trade
(first-window rising-edge entry, window-close exit).

**T2 — True D1 candidate density.** Per session: D1 event count, clock-time distribution of first rising
edges, candidate-set size on a 5-minute grid, faceted by year. Cheap read, reuses the design in
`prompts/relative_momentum.md` Part I T1, never run. **This decides whether the expensive causal
re-derivation of the gate over all of D1 is worth doing** — if true concurrency is thin, no population
correction rescues Gate 2.

**T3 — Settle v0's gate-1 mechanism.** One query on data already computed: compare **notional, print
count, and price** between v0's gate-1 passes and fails. Two competing explanations are on the record —
that the percentile gate selected deep into the move (ρ = 0.69 with `move_at`), or that it selected thin
tape. If passes are systematically thinner and cheaper, it was never an attention gate, it was an
illiquidity filter pointed the wrong way.

## Evaluate

Five policies, same table:

| policy | definition |
|---|---|
| **A** | baseline — every first-window signal, no qualification |
| **F** | floor only — everything passing the absolute floor, no ranking |
| **R** | rank only — cross-sectional, no floor. **Control: reproduces the broken v0 case deliberately** |
| **F+R** | floor, then rank survivors. The proposal |
| **F+R contested** | F+R where ranking actually chose among ≥ 2 survivors |

Columns: n, gross median/mean, net median (flat and per-share), win rate.

**Also record:**
- **fail-reason histogram** per candidate moment — which condition is doing the rejecting
- **NO_TRADE frequency** — how often the floor rejects the whole field
- **net markout by detection-price decile**, separate from the policy table, so a price-level effect
  isn't misread as a gate effect
- Spearman(rank score, `move_at`) on floor survivors

**R vs F+R is the test of the whole thesis of this version.** If R picks dead-tape winners and F+R doesn't,
the floor did its job. If F rejects nearly everything, the thresholds are wrong and the histogram says
which one.

## Constraints

`move_at` never `momentum_pct` · D4 tick-derived · D5 long-only · flag and carry, never drop · Phase 11
cost stack (flat and per-share, both reported) · state population coverage plainly.
