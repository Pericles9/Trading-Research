> **Filing note (Claude Code, 2026-09-23).** Filed verbatim as pasted, on branch
> `explore/attention-excursion-b1`. Amends Part II of `prompts/attention_excursion_b1.md` (Cooper's
> `prompts/attention_excursion.md` / `prompts/Attention excursion.md`). Config changes it requires are in
> `config/attention_excursion_b1.json` under `amendment_1`.

# Brief 1 — Amendment 1: the row-4 stop, the prior close, and what runs next

**Date:** 2026-09-23 · **Amends:** Part II of `prompts/attention_excursion.md` (Brief 1).
**Occasioned by:** the HARD STOP at T2 on escalation row 4, commit `a3f6a9c` on
`explore/attention-excursion-b1`. **This is an audit finding about the instrument, not a reaction to an
outcome.** No outcome has been read.
**Size note:** the combined document is ~56,000 characters and was truncated at 50,000 in transfer. Read
it from the repo or project file, not a paste. This amendment is short enough to paste whole.

---

## A1.0 What the stop showed

| comparison | outside [−1, 61] s |
|---|---|
| as run: exact rule vs the old proxy, each with its own prior close | 2,774 of 15,763 (17.6%) — **fired** |
| prior close held at the proxy's own, so only timestamping differs | 223 of 15,313 (1.5%) — **would clear** |

The row was written to catch one thing: the exact rule and the proxy disagreeing about **when the
crossing happens**. It assumed timestamping was the only difference. It was not. T1 deliberately changed
the prior close from the last regular-hours minute bar to the closing auction print, and on a tape
sitting near +30% a close that moves by tens of basis points moves the crossing by minutes to hours.
**The row fired correctly on an expectation of mine that was wrong.** The build's timestamping is sound
(1.5%). The disagreement is a definition change, and the prior close is the right thing to change.

It also found something worth keeping: **τ is fragile for events that hover near the +30% line.** That
is a property of the event, not a defect, and it becomes a carried flag (A1.3).

## A1.1 Row 4 and the matching II.5 check, re-specified

- **Row 4 (HARD STOP):** `τ_exact − τ_proxy'` outside [−1, 61] s for more than 2% of D1, where
  `τ_proxy'` is the old minute-level proxy **recomputed with the same prior close as τ_exact**. It now
  tests only what it was meant to test.
- **II.5 "τ ≥ proxy minute start":** same change. It compares against `τ_proxy'`.
- The as-run comparison, with the prior close free to differ, is kept as a **reported sensitivity**,
  not a gate.

## A1.2 T1 re-specified: the listing venue's closing cross

T1's "largest print carrying the closing codes" picked another venue's own official close over the
listing venue's closing cross on 2,599 events. The official close of a listed stock is the **listing
exchange's** closing auction. Revised rule, first that exists wins:

1. **`listing_cross`** — the closing-cross print on the listing venue.
2. **`listing_official`** — the listing venue's official-close print, if no cross print exists (for
   example, halted into the close).
3. **`last_rth_print`** — the last regular-hours consolidated print at or before 16:00:00 ET that is
   not an auction print from another venue.
4. **`unavailable`** — carried, never dropped.

- **Listing venue:** from the Phase 1b ticker reference snapshot (the classification source of record),
  never a fresh API query. Flag `listing_venue_mismatch` where the chosen print's venue disagrees with
  the snapshot, since listings change (uplistings, downlistings).
- **Condition codes:** map "closing cross" and "official close" from `docs/massive_trade_conditions.json`
  by meaning, and record the codes used in config. Do not assume which of 8 and 15 is which.
- **Carry `prior_close_source`.** Row 7 (LOG) counts `last_rth_print` plus `unavailable`.
- **Report:** counts per source; the distribution of revised-minus-previous T1 close in bp; the 2,599
  other-venue cases, showing where each now resolves.

## A1.3 New carried flag: `tau_close_sensitive`

TRUE when τ computed with the revised T1 close and τ computed with the old minute-bar close differ by
more than 60 s. These are events that crossed +30% gradually rather than decisively. **A facet on every
later panel, never a filter.** Also carry `tau_gap_close_s`, that difference in seconds.

## A1.4 Spike guard

**Keep 3%** for neighbour agreement, as written. Carry the 1.5% variant used by the exit overlay's code
as a sensitivity column, `tau_ns_guard15`, and report the count where it differs (observed: 148).

## A1.5 What runs, and where it stops

1. Re-run **T1** under A1.2 and **T2** on the revised close.
2. Evaluate the revised row 4 and row 1. **If both clear, continue through T3–T7 without stopping.** If
   either fires, HARD STOP as before.
3. **T7 remains the HARD STOP** for Cooper's review, as in the brief. Every row, every control and every
   II.5 check is reported there.

## A1.6 Housekeeping, in the same branch

- **`CLAUDE.md`:** add the D38 exception to the standing line "Ticker-blocked splits — no ticker on both
  sides" in the same commit that re-runs T1. As it stands, the rule text contradicts D38.
- **Charts** move to `results/attention_excursion/b1/charts/<task>/`, the programme's convention, not a
  new top-level `charts/` folder. Dark theme stays.
- **The stop report** is regenerated by code from artifacts, with rows 6–7 and the II.5 checks. So is
  every later REPORT.md.
- **Config** gains rows 6–7, `prior_close_source` precedence, the condition-code mapping, and the
  `tau_close_sensitive` threshold.

## A1.7 Part III — authorised now

Run the E2 units fix on `fix/e2-window-units` independently, including correcting the overlay report's
false "never committed" sentence. It does not wait on Brief 1.

## A1.8 Recorded, not acted on

Every earlier `move_at` (R0-T0c, v0, v1, v2, the exit overlay) used the minute-bar prior close, which
differs from the revised close by a median of 25.5 bp (p95 345 bp). Those results are not re-run.
Their +30% membership and `move_at` values carry this known basis difference, whose direction on their
findings has not been assessed.
