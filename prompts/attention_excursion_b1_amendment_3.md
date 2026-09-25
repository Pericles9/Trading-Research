> **Filing note (Claude Code, 2026-09-25).** Filed verbatim as pasted, on branch
> `explore/attention-excursion-b1`. Amends Part II of `prompts/attention_excursion.md` (Brief 1) after
> Amendments 1–2 (`prompts/attention_excursion_b1_amendment_1.md`, `..._amendment_2.md`). Config changes
> it requires are in `config/attention_excursion_b1.json` under `amendment_3`.

# Brief 1 — Amendment 3: anchor acceleration to the event's own session segment

**Date:** 2026-09-25 · **Amends:** Part II of `prompts/attention_excursion.md` (Brief 1), after
Amendments 1–2. **Occasioned by:** the unset open-adjacent boundary (DA-4, Amendment 2 A2.7) at the T7
review of commit `99b7e51`. **An audit finding about the instrument, from the T3 open profile, which
reads no outcome.** Replaces DA-4 entirely.

---

## A3.0 Why the boundary was the wrong tool

The T3 open profile (each event's per-minute trades ÷ its own day's median, n ≈ 9–15k events per
minute) shows two things at 09:30, not one:

| clock | median | mean | share of events with zero trades |
|---|---|---|---|
| 09:00–09:24 (premarket) | 0.00 | ~0.30 | ~64% |
| 09:30 (opening-cross minute) | 2.67 | 6.80 | 3% |
| 09:31 | 1.00 | 4.49 | 25% |
| 10:00 | 1.00 | 3.47 | 25% |

1. **A one-minute spike**: the opening auction.
2. **A step of roughly 10× in mean activity** from premarket to regular hours, which persists.

Acceleration compares the recent half of a window against the older half, with every event's ladder
anchored at 04:00. For any regular-hours crosser, the coarse rungs put premarket in the older half and
regular hours in the recent half. **They measure the session step (a log ratio of about 2.3), not the
stock's attention.** That affects the coarse rungs of the ~70% of events that cross after 09:30. A
boundary "X minutes after the open" cannot fix this, because the contamination depends on the rung's
width, not on how close the crossing is to the open. A crossing at 11:00 is contaminated at every rung
wider than about 90 minutes.

The dev run is consistent with this. 227 invalid rungs were `from_nothing` (the older half empty), and
rung 0 was `from_nothing` on 13 events: the premarket half of a 04:00-anchored history is often empty.

## A3.1 The rule — derived from market structure, nothing to choose

**H = τ − the start of the segment τ falls in:**

| segment of τ | segment start | reason |
|---|---|---|
| premarket (04:00 ≤ τ < 09:30) | 04:00:00 | unchanged |
| regular hours (09:31 ≤ τ < 16:00) | **09:31:00** | after the opening-cross minute |
| after hours (τ ≥ 16:01) | **16:01:00** | after the closing-cross minute, by the same logic |

Rungs remain `W_k = H / 2^k`, each judged on its own (Amendment 2 A2.4). Every half-window now lies
inside one segment and excludes the auction minutes by construction.

**Verification (II.5, added):** assert in code that no rung half-window contains any part of
09:30:00–09:31:00 or 16:00:00–16:01:00, or spans a segment boundary. A violation raises.

## A3.2 The auction-minute class

Crossings with τ inside 09:30:00–09:31:00 (148 of 15,519 crossings, 1.0%) or 16:00:00–16:01:00 have no
segment history, so A2 cannot be measured for them. They are carried as `tau_in_auction_minute = TRUE`,
with A2 `unavailable`: a label, never dropped. All other measures (turnover, catalyst, cross-section,
excursion) are computed as normal.

## A3.3 What this retires and what it costs

- **Retired:** DA-4, the `open_adjacent_0930` column and its pending state. `sec_from_0930` stays as a
  descriptor.
- **Cost, stated:** a regular-hours crosser's acceleration no longer sees its premarket build-up. That
  build-up happened under different trading conditions, and it is not lost from the design: **turnover
  (A1) still counts every share since 04:00.** Early regular-hours crossers (say τ = 09:35) get only
  short rungs. That is the honest amount of history they have.

## A3.4 The cross-sectional windows follow the same rule

`flow_share_k` and `accel_rank_k` are taken over the new crosser's rung windows, so they inherit the
anchoring automatically. Every live name is measured on those identical clock windows. A window
straddling the open would weight names by how much they traded premarket, and that is now excluded.

## A3.5 Competition check — tighten the matched control

The first look at T5b (dev dates only, no outcome involved) shows the control moments falling further
than the crossing moments in most cells. At L = rest of session, W = 60: crossing median −0.213 against
control −0.586. **The controls are not matched on time.** They are drawn uniformly across a live name's
span, so they over-sample late, decaying parts of the day. That difference cannot be read as evidence
for or against crowding-out until the match is fixed.

**Revised control:** for each (live name i, crossing j) pair, draw control moments from i's own live
span that fall in **the same octave of time since i's own crossing** as τ_j (the same base-2 bins used
elsewhere) and **in the same session segment**, still with no other D1 crossing within ±W. Report the
number of matched controls per cell. A pair with no matched control is carried as `no_match`, not
filled from outside its bin.

## A3.6 Rulings on the other items from the T7 report

- **Per-event charts as one chart with an event selector:** accepted. It is the better format at 5 MB
  per chart.
- **run1/ and run2/ charts that load Plotly from the internet:** leave them as the historical record.
  Add one line to a `README.md` in each folder: *generated by a superseded instrument; requires an
  internet connection to render.*
- **The threshold-suite session:** read-only, as it is working now. Its column gaps come to Claude (chat)
  and are folded into Brief 2's column list. It builds nothing that reads outcomes until Brief 2's
  full-D1 build exists and the development slice is embedded under the suite's slice guard.

## A3.7 What re-runs, and where it stops

Re-run **T5** (A2 with the new anchoring, plus the cross-sectional windows), **T5b** (with A3.5
matching), and the **two acceleration controls in T6** (synthetic tapes generated over the
segment-anchored history). **T4 does not re-run.** The excursion vector is untouched by this amendment.
Then **T7: HARD STOP** for Cooper's review, as before.

**Report additions:**

- valid rungs per event, by segment, **before and after** the anchoring change — the weight of this
  amendment, measured;
- how many previously valid rungs straddled the open;
- the `from_nothing` count, before and after;
- the auction-minute class count;
- matched-control counts per T5b cell.
