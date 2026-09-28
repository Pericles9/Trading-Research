# Relative momentum — build & evaluate v0

**Date:** 2026-09-18 · **Type:** build. Produces a real backtest, not a read. Supersedes the scoping
approach in `prompts/relative_momentum.md` in practice — that document's stopping gate and re-slice
findings stand as background, not as gates on this work.

> **Filing note, added by the v0 run, not part of the brief as authored.** Filed at this path so
> `config/relative_momentum_v0.json`'s `_meta.prompt` citation resolves. The brief cites
> `prompts/relative_momentum.md`; the document at the equivalent path in this checkout is
> `prompts/relative_momentum_r0.md` (filed by the R0 run, and itself the subject of the unreconciled
> stub drift recorded in the 2026-09-18 read §5). Result: `results/relative_momentum/v0/REPORT.md`.

**Two things carried forward, non-negotiable, everything else dropped:**
1. **`move_at` (causal), never `momentum_pct`**, in any threshold, score, or slice.
2. **The old PF = 1.9194 figure is not ground truth.** Its population depended on filter logic no longer
   in source. Build fresh; don't validate against it.

---

## Facet 1 — Entry/exit (existing, reuse as-is)

The participation gate in `scanner-epg-momentum`. **First window only** — rising edge entry, window-close
exit, real realized hold length.

**Population:** whichever is cheaper to get running today —
- re-run the gate's own logic causally against all of D1, if that's a small lift, **or**
- use the existing fired population (currently ~1,087 D1 events) as-is.

Either is fine. **State plainly which one was used and its coverage** — no requirement to reconcile it
further right now.

## Facet 2 — Qualification (build fresh)

**Attention score v0 = relative volume**: 10-minute trailing window, causal, using the existing E2
3-session baseline (`B_e`). One measure, not a composite — keep it simple until it's shown to do anything.

**Two gates, applied at the moment of each candidate's first rising edge:**
1. **Score ≥ 75th percentile** of the score's own distribution across all candidate moments (a round,
   defensible v0 default — not fitted, revisit later if this survives).
2. **Score is the highest** among all names whose gate is concurrently live at that same moment.
   Liveness = the gate's own window-close definition (what the deployed system would actually use).

## Evaluate

Run the gate's real trade — rising-edge entry, window-close exit — under two policies, side by side:

- **Policy A (EPG-only):** take every first-window rising-edge signal.
- **Policy B (EPG+Qual):** take only signals passing both qualification gates.

**Report, same table, both policies:**
- trade count
- markout distribution — full distribution, not just the median
- net-of-cost median (use Phase 11's 70.98 bp / 2.512 cents unless the gate's own native fill/cost model
  is more realistic for a ~52-second hold — use whichever fits better, state which)
- win rate

**One diagnostic panel alongside, not gating anything:** correlation between the attention score and
`move_at` at each candidate moment. Answers the collinearity question in the same pass instead of a
separate phase.

## Constraints, stated once

D4 (tick-derived only) · D5 (long-only) · flag and carry coverage gaps, never drop · state population
coverage plainly rather than assume it equals all of D1.

**That's the whole brief. Build it and report what comes out.**
