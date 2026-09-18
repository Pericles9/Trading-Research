# Relative momentum — build v1: causal threshold, corrected population

**Date:** 2026-09-18 · **Type:** build. Fixes the two defects found in v0 — the level gate wasn't
computable live, and the tested population wasn't the program's actual momentum definition. Everything
else from v0 carries forward unchanged.

> **Filing note, added by the v1 run, not part of the brief as authored.** Filed here so
> `config/relative_momentum_v1.json`'s `_meta.prompt` citation resolves. Result:
> `results/relative_momentum/v1/REPORT.md`. The brief's `prompts/relative_momentum.md` is
> `prompts/relative_momentum_r0.md` in this checkout (see that file's own filing note).

---

## Carried from v0, unchanged

- **Score = relative volume**, 10-min trailing window, causal, E2's 3-session baseline. One measure.
- **Gate 2 (cross-sectional):** among candidates live at that moment, take the highest score. Liveness =
  the gate's own window-close definition.
- **Trade = the gate's real trade:** first-window rising-edge entry, window-close exit, realized hold
  length. Not Phase 11's fixed hold.
- **Cost = Phase 11's stack** (flat + per-share), unless the gate has its own native fill/cost model —
  state which was used.
- **Diagnostic panel:** Spearman(score, `move_at`) at candidate moments, alongside the backtest, not
  gating it.

## Fix 1 — Gate 1 made causal

v0's threshold was the 75th percentile of the score's own distribution **over the whole backtest sample**
— not computable at decision time in live trading. Replace it:

> **At each candidate moment, threshold = the 75th percentile of every candidate score observed strictly
> before that moment**, pooled across tickers, updated chronologically as new observations arrive.

**Minimum 250 prior observations before Gate 1 activates.** Before that count is reached, every candidate
passes Gate 1 by default and is flagged `gate1_warmup` — visible in the report, not silently different
behaviour. 250 is a round a-priori choice, not fitted; revisit only if the warmup period turns out to
cover a meaningful share of the sample.

This makes Gate 1 a rule that could actually run on day one of live trading: nothing in it depends on data
from after the trade it's gating.

## Fix 2 — Population corrected to the actual thesis

v0's population had `gap_gate_enabled: false` on every event — entries as low as −23% intraday, not the
program's +30% momentum definition. **Re-run with the gap gate on**, so the population tested is genuine
+30%+ crossers. Use whatever existing infrastructure produces this fastest; state which run/config was
used and its resulting coverage.

## Fix 3 — Candidate density, measured cheaply before any bigger rebuild

v0 found candidate density suppressed 2.84× relative to true D1 (6.11/session vs 17.35/session), which
starved Gate 2 of contests. Before spending anything on a full causal re-derivation of the gate over all of
D1 (a real lift — the online Hawkes refit), **measure true D1 concurrency directly** — this reuses the
design already written in `prompts/relative_momentum.md` Part I, T1, which never ran:

- Per session, the count of D1 events and the clock-time distribution of first rising edges.
- Candidate-set size on a 5-minute grid, faceted by year.

**This is a cheap read, not a rebuild**, and it answers the question that actually determines whether the
expensive re-derivation is worth doing: if true D1 concurrency is itself thin, no amount of population
correction fixes Gate 2, and that's worth knowing before committing to the bigger build.

## Fix 4 — Separate the price-level effect from the gate effect

Phase 11 already established net edge as a function of detection-price level. Report **net markout by
detection-price decile**, independent of the gate policy table, so a price-driven effect doesn't get
misread as a gate effect the way it nearly did in v0.

## Evaluate

Same table shape as v0 — **A (baseline), B1 (level only), B2 (cross-sectional only), B (both), B-contested
(cross-sectional actually decided)** — rerun on the corrected population with the causal Gate 1. Same
columns: n, gross median/mean, net median (flat and per-share), win rate. Add `gate1_warmup` share per
policy.

## What this settles

Whether a **causally computable** level gate, on the **correct** population, does what Gate 1 did in v0 —
or whether v0's damage was an artifact of the in-sample threshold and the broken gap gate rather than a
real property of level-gating. Either answer is usable; guessing further from the v0 run isn't.
