<!-- COPY OF RECORD. Compiled by Claude Code via live web research, 2026-09-14, under Cooper's
     explicit authorization ("Yes, research Reg SHO 201 as a first step", AskUserQuestion response)
     to research SEC Regulation SHO Rule 201 and check its applicability to this cohort's events.
     See docs/Universe-Decisions.md D36 for the authorization's exact scope. **This document and
     the measurement it supports do NOT authorize or implement any short-side strategy work** —
     D5's long-only constraint stands unchanged; see the scope note below. -->

# Reg SHO Rule 201 (the short-sale circuit breaker) — compiled reference

**Compiled:** 2026-09-14, via live web research (WebSearch/WebFetch), explicitly authorized for
this one instance (D36 — same shape as D34's LULD authorization and D35's condition-code attempt).
**Scope, stated before anything else:** this is a **measurement** task only — does Rule 201 apply
to each historical event, and when. It is **not** authorization to design, implement, or measure
any short-side execution logic, position, or strategy. D5 ("Long-only... Do not specify,
implement, or measure short-side or fade variants. Do not implement SSR or borrow logic") stands
completely unchanged. This document supplies one of the three inputs `docs/Universe-Decisions.md`
D25 named as needed to close the short-side question — the other two (locate/borrow availability,
and halt/reopen risk specifically on the short side) remain unavailable or unmeasured.

---

## 1. The rule, in plain terms — HIGH confidence, sourced from the SEC's own FAQ page

**Trigger.** Rule 201 (part of Regulation SHO) activates for a stock when its price declines **10%
or more, intraday, from its closing price on the prior trading day** (regular-hours close,
9:30am–4:00pm ET). The trigger is based on **traded prices** (actual executions), checked
continuously through the regular session — not on the bid/ask quote. Quoted directly from the SEC:
*"the price of a covered security decreases by 10% or more from the covered security's closing
price... as of the end of regular trading hours on the prior day."*
[Source](https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions-7).

**Duration.** Once triggered, the restriction applies **for the remainder of the triggering day,
and the entire following trading day** — quoted: *"the price test restriction will apply to short
sale orders in that security for the remainder of the day and the following day... unless an
exception applies."* No limit on how many times it can re-trigger for the same security. Applies
to any NMS stock (any security listed on a national exchange) — this cohort's micro-caps are
covered securities.

**What the restriction actually does, once triggered** (not implemented here, stated for
completeness): trading centers must prevent short sale orders from executing at a price at or
below the current National Best Bid, with listed exceptions (short-exempt marked orders, crossed
NBBO, certain riskless-principal and VWAP transactions). **This mechanism is not modeled by this
document or its measurement — only the trigger/duration fact is used.**

## 2. What "closing price" means, and the D4 consequence

The reference price is the **prior day's regular-hours closing price**, determined by the listing
market. Per `docs/Universe-Decisions.md` D4, the canonical spine's `prev_close`/`close` columns are
permanently quarantined from any computed quantity — so, exactly as `docs/data/luld_plan_reference.md`
already established for the LULD previous-close input, **the "prior close" for Rule 201 must be
computed from tick data, not the spine.** `research/phase_12/t2b_band_arithmetic.py` already builds
this exact quantity (the last T-1 RTH minute bar's `last_price` from `event_minute_bars_v2`,
tick-derived) — reused, not rebuilt, for this measurement.

## 3. What was NOT independently verified

The SEC FAQ page and a secondary trader-facing explainer (`stocktitan.net`) agree on the trigger
mechanism and duration; a third source (Ropes & Gray's client alert on the original 2010 rule
adoption) was found in search results but not independently fetched, since the SEC's own FAQ page
already gave a directly quotable, authoritative answer. **Not independently checked**: the exact
list of exceptions (short-exempt marking, riskless-principal, VWAP) in full legal detail — not
needed for a trigger/duration measurement and explicitly out of scope (§0). **Not checked**: any
amendment history to Rule 201 since its 2010 adoption — a search for later amendments was not run
this session (unlike D34's explicit post-Amendment-18 sweep for LULD); if this measurement is ever
promoted beyond a first look, that sweep should run first.

## 4. Consequence — what this authorizes and what it does not

**Authorizes**: computing, per dev-tier event, whether and when a 10%-intraday-decline-from-prior-close
trigger would have occurred during the T=0 session, using tick data and the same D4-safe
previous-close construction as Phase 12's T2b. Reported as data — trigger yes/no, and if yes, the
approximate time of trigger — with no interpretation of what it means for tradeability.

**Does not authorize**: any short-side entry/exit logic, position sizing, or backtest; any claim
about profitability; borrow/locate availability (still unavailable in this checkout); or halt risk
specifically conditioned on a short position (Phase 12 measures halt risk for the existing long-only
framing only, and would need separate work to condition it on a short entry). **D5 stands. This is
one input among three D25 named, not a reopening of the short-side question.**
