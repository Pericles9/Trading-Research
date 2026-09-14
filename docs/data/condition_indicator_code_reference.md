<!-- COPY OF RECORD. Compiled by Claude Code via live web research, 2026-09-14, under Cooper's
     explicit authorization ("Look up the code dictionary first", AskUserQuestion response) to
     research the trade/quote condition and indicator code dictionary for Phase 12's route 2.
     See docs/Universe-Decisions.md D35 for the authorization's exact scope. -->

# Trade condition and quote indicator code reference — partial, honestly incomplete

**Compiled:** 2026-09-14, live web research (WebSearch/WebFetch), authorized for this instance only
(D35, same shape as D34's LULD authorization). **Bottom line: this research did NOT resolve the
two codes that actually matter for Phase 12's route 2 — quote indicator codes 3 and 7, the ones
found exclusive to candidate-gap windows in T2a's census (`results/phase_12/artifacts/t2_code_census.json`).**
`config/phase_12.json`'s `dictionary_path` stays `NONE` — route 2 still identifies nothing. This
document exists so the attempt, and its limits, are on the record rather than silently re-tried
later without knowing it was already tried.

---

## 1. What this data source is

The trades/quotes schema in this checkout (`conditions`, `indicators`, `sip_timestamp`,
`participant_timestamp`, `trf_id`, `sequence_number`, `tape`) matches Polygon.io's flat-file /
API schema closely. Polygon.io's product documentation now redirects to `massive.com` (a rebrand
of the same vendor — this is also the source of the "Massive" fetches in the Build F1 fundamentals
work, `docs/Universe-Decisions.md` D27). **Polygon/Massive translates the raw CTA/UTP/OPRA SIP
condition codes (which are letter-coded at the regulatory level, e.g. `R`, `A`, `B`, `H`, `W`, `O`
for quote conditions) into their own unified numeric IDs.** The numeric codes in this repo's data
(2, 3, 7, 8, 14, 20, 37, 41, 81, 82, ...) are Polygon/Massive's numbering, not the raw SIP letters
— confirmed via Polygon's own documentation stating it provides "a unified and comprehensive list
of trade and quote conditions... translat[ing] condition codes from individual SIPs (CTA, OPRA,
UTP) to a unified code used by Polygon.io."
[Source](https://polygon.io/docs/rest/stocks/market-operations/condition-codes).

**This matters for what could and couldn't be found**: the raw regulatory SIP specifications (CTA,
UTP, NYSE Daily TAQ) document the letter codes and their meanings, not Polygon/Massive's numeric
re-mapping. The authoritative numeric table lives behind Polygon/Massive's own (authenticated)
`/v3/reference/conditions` API endpoint, which this session could not call (no API key), and their
public documentation page for it is JavaScript-rendered with no static table in the fetched HTML.

## 2. What was resolved — HIGH confidence

| code | meaning | population | source |
|---|---|---|---|
| 37 | Odd Lot Trade | trade condition | [heygotrade blog, search synthesis](https://www.heygotrade.com) citing standard SIP terminology — a trade smaller than the round-lot size |
| 2 | Average Price Trade | trade condition | [massive.com blog, "Understanding Trade Eligibility"](https://massive.com/blog/understanding-trade-eligibility) — a direct API response example shown in the article: `"condition ID 2 labeled 'Average Price Trade'"` |
| 14 | Intermarket Sweep (ISO) | trade condition | **Already confirmed in this repo**, not new research: `docs/Universe-Decisions.md` D26 point 3, supplied from the public trade-conditions glossary at a prior Cooper review. Cross-referenced here for completeness, not re-derived. |

**None of these three codes bear on halt identification.** Odd-lot and average-price trades are
routine market mechanics; ISO is about aggressive multi-venue order routing (D26's own subject).
Resolving them does not change route 2's ability to identify a halt.

## 3. What was attempted and NOT resolved

**Quote indicator codes 3 and 7** — the two found exclusive to candidate-gap windows in T2a's
census (54 and 63 occurrences respectively, zero in the matched non-candidate sample) — **could
not be resolved to a meaning in this session.** Also not resolved: trade condition codes 41, 81,
82, and quote indicator code 8.

**What was tried, so a future attempt doesn't repeat the same dead ends:**
- Polygon/Massive's own condition-codes documentation pages (HTML) — page structure only, no
  embedded numeric table (JavaScript-rendered).
- Polygon/Massive's REST API endpoint directly (`/v3/reference/conditions`) — HTTP 401,
  authentication required, no API key available to this session.
- Primary regulatory specifications in PDF form — NYSE Daily TAQ Client Specification, Nasdaq/UTP
  Quote Line Specification, the CQS Output Specification, an eodhd.com trade-conditions glossary
  PDF — **all failed to extract as readable text** with the tools available this session (binary/
  compressed PDF structure returned instead of prose, the same failure mode `docs/data/luld_plan_reference.md`
  §7 already recorded for a different set of PDFs).
- Interactive Brokers' trade-conditions reference page — HTTP 403 Forbidden.
- `submillisecond.com`'s microstructure glossary — HTTP 403 Forbidden on the specific page found by
  search; its indexed pages on adjacent terms (NBBO, SIP, quote) fetched fine but don't carry a
  condition-code table.
- GitHub — `pssolanki111/polygon` (a complete Python API wrapper) — no condition-code table
  committed to the repo's documentation.
- Multiple search-engine queries combining the specific numeric codes with likely category terms
  (halt, closing, resumption, regular market) — returned only the raw SIP letter-code table (§1),
  not Polygon/Massive's numeric re-mapping.

**What the raw SIP letter-code table did establish, for context (not a resolution of codes 3/7,
since the numbering differs)**: standard CQS quote conditions include `R` (Regular), `A` (Slow
Quote, Offer side), `B` (Slow Quote, Bid side), `H` (Slow Quote, both sides), `W` (Slow due to Set
Slow List), `O` (Opening Quote). If Polygon/Massive's numeric IDs follow SIP publication order or
some other discoverable convention, that mapping was not found this session — stated as a
possibility for a future attempt, not asserted as fact.

## 4. Consequence for Phase 12

`config/phase_12.json`'s `dictionary_path` **remains `NONE`.** Route 2 still produces a census
only and identifies zero candidates, exactly as before this research — Escalation row 5 still
applies (no meaning inferred without a dictionary), and none of what §2 resolved supplies one for
the halt question specifically. **The Stage A gate result (`results/phase_12/artifacts/t3_gate.json`)
is unchanged** — this research did not move it, and no task was re-run on the strength of a partial
dictionary that doesn't cover the two decision-relevant codes.

**What would actually resolve codes 3 and 7**: an authenticated call to Polygon/Massive's own
`/v3/reference/conditions` endpoint (this session has no API key), or a readable (non-PDF, or
independently OCR'd) copy of the CTA/UTP technical specification's National BBO Indicator table
(CTA spec Appendix G, per search-engine synthesis of the CQS Output Specification's table of
contents — the specification itself did not extract as text this session).
