# Participation / exit overlay — does the first window close inside live participation?

**Date:** 2026-09-21 · **Type:** measurement. Decides whether the entry/exit layer gets rebuilt.
**Runs before any rebuild.** Uses existing entries and existing artifacts; builds no new trade logic.

---

## The hypothesis under test

First-window EPG enters as early as possible and exits at window close. Participation in these names
tends to arrive *after* the run, and that participation is what sustains the move — so EPG may be
flattening and closing the ticker precisely when the thing the qualification layer detects starts to
matter.

T3 is consistent with this: gate-1 passes carried **10.3× notional and 14.9× prints** at **3.65× deeper
into the move**, and lost money under a 9-minute window-close exit. Loud and late.

**What has never been measured:** a deep entry with a *participation-tracking* exit. Phase 11 held 30
minutes fixed; v0 held to window close at a 540 s median. Both varied the entry and fixed the exit.

## The decisive test is a counterfactual exit, not the timing overlay

The overlay shows whether a mismatch exists. **T3 below shows whether closing it is worth anything**, and
that is the number that decides the rebuild. Same entries, same single round trip, two exits:

> **Exit A — window close** (what EPG does today).
> **Exit B — participation decay** (what the rebuild would do).

Both hold one position opened at the same τ. Extending a hold does not add a round trip; it adds
exposure. So the cost comparison is not "another 70.98 bp" — it is the same single round trip amortised
over a longer move, which *improves* the cost ratio if the move continues and worsens nothing if it
doesn't.

**The counter-case must be given a fair chance to win.** The programme's founding thesis is a strong bull
impulse followed by a sharp bear impulse. It is entirely possible EPG's early exit is *correct* — that it
steps out just before the flip, and that holding to participation decay walks straight into it. If Exit B
is worse, the timing mismatch is real and closing it is still the wrong move. Report it that way.

## T1 — Build participation onset and end

Reuse E2's machinery and its **already pre-registered decisions, carried verbatim, not re-opened**:
baseline `B_e` = total volume across T-3/T-2/T-1 regular hours ÷ number of 10-minute intervals, flat with
no time-of-day matching; at least one prior session with non-zero RTH volume; `n_baseline_sessions` (0–3)
carried and facetting every panel; `baseline_thin` flagged and carried; censoring at the event-day
extended session end.

From `event_minute_bars_v2`, per event:

- **`participation_end`** — E2's rule: first minute after `t0` where trailing 10-minute average volume is
  ≤ 3 × `B_e` **and stays there for C consecutive minutes**. C carried at E2's declared value.
- **`participation_onset`** — **new, the mirror of the same rule**: first minute after `t0` where trailing
  10-minute average volume is ≥ 3 × `B_e` and stays there for C consecutive minutes.

**Onset is the addition that makes the hypothesis testable.** E2 assumes participation begins at `t0` by
fiat, so as written it cannot see late arrival — which is the core of the claim. Measuring onset with the
same rule in the opposite direction costs nothing and is what shows whether participation arrives after
the run.

If E2-T2 already produced the window artifact, reuse it and build onset only.

## T2 — The timing overlay

Four timestamps per event, all expressed in seconds from `t0` so they sit on one clock:

`t0` → `participation_onset` → `τ` (EPG entry) → `window_close` (EPG exit) → `participation_end`

Report the distributions of:

- **`window_close − participation_end`** — negative means EPG exits while participation is still live.
  **This is the headline number.**
- **`τ − participation_onset`** — negative means EPG enters before participation arrives.

Both faceted by `n_baseline_sessions`, session segment, and detection-price decile. Censored events
(participation never decays before the horizon) reported as their own class with their share stated —
never pooled, never dropped, and no mean taken across them (E2's DE-3).

## T3 — The counterfactual exit. This decides the rebuild

Per event, from the same entry at `τ` and the same fill assumptions already used in v0/v1:

| | exit at | holds |
|---|---|---|
| **A** | `window_close` | as traded today |
| **B** | `participation_end` | to participation decay |

Report for both, side by side: gross and net markout median **and full distribution**, both cost units
(D19), win rate, realised hold length, and n. Net uses Phase 11's stack — **one round trip in each arm,
not two.**

**Censored events need an exit rule and it is a real decision, not a default.** Events where participation
never decays before the horizon exit at the censoring horizon, are reported as their own class, and are
**not** silently treated as tradeable — an overnight or session-end hold is a different risk from an
intraday one under D5.

**Halt exposure, required if obtainable.** A longer hold increases halt exposure, and the programme's own
standing finding is that exit timing dominates variance and ruin risk, halts particularly. Report the
share of Exit B holds that span a halt. If halt data is not available in this archive, state that plainly
as a limitation on the Exit B result rather than omitting it.

## T4 — Charts

- **Event timeline strip** — the four timestamps per event, sorted by `window_close − participation_end`.
  The picture that shows the mismatch directly.
- **Gap distributions** — `window_close − participation_end` and `τ − participation_onset`, ECDFs.
- **Exit A vs Exit B markout ECDFs**, both cost units, overlaid. The decision chart.
- **Markout in the gap** — price change from `window_close` to `participation_end`, distribution. What
  EPG leaves on the table, or avoids.
- Exit A vs B by detection-price decile, and by `move_at` decile — the latter tests directly whether the
  deeper-entry penalty found in T3 and R0-T0c2 survives a participation-tracking exit.

## T5 — Report

`results/participation_exit_overlay/REPORT.md`. Describes the pictures. No rebuild recommendation — that
call is Cooper's off these numbers.

## What this settles

- **Mismatch real, Exit B better** → the entry/exit layer gets rebuilt around participation, and E2's
  window definition is promoted from descriptive statistic to trade rule.
- **Mismatch real, Exit B worse** → EPG's early exit is doing real work by stepping out before the flip.
  The mismatch is structural and closing it is still wrong. The qualification layer's problem is
  elsewhere.
- **No mismatch** → EPG already exits as participation dies, and neither the floor nor the exit is the
  lever.

## Constraints

`move_at` never `momentum_pct` · D4 tick- or bar-derived from D4-clean sources · D5 long-only · D19 both
units · E2's DE-2 and DE-3 carried verbatim · flag and carry, never drop · state population coverage
plainly.
