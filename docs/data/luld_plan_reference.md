<!-- COPY OF RECORD. Compiled by Claude Code via live web research, 2026-09-13, under Cooper's
     explicit authorization to research and verify the LULD band parameters for Phase 12
     (see docs/Universe-Decisions.md D34 for the authorization and its scope). This is a
     SECONDARY, compiled reference -- it quotes and cites primary/regulatory-notice sources,
     it is not itself the primary LULD Plan document (the actual Plan PDF and SRO rule filings
     could not be extracted as readable text by the tools available in this session; see
     Sources below for what was and was not machine-readable). D14 (environment is offline)
     stands for the phase's own data pipeline -- this document exists so the phase's static
     config can cite a committed, dated, sourced file instead of a live URL or agent memory. -->

# LULD price bands, doubling, and reference-price mechanics — compiled reference

**Compiled:** 2026-09-13, via live web research (WebSearch/WebFetch), explicitly authorized by
Cooper for Phase 12's `config/phase_12.json` `source_document`. **Confidence is stated per fact**
— this document does not present everything at the same certainty level, on purpose.

---

## 1. Price band table (regular session, 9:30am–3:35pm ET)

**HIGH CONFIDENCE — corroborated verbatim across FINRA, Cboe's technical-spec FAQ, and
luldplan.com's own summary table, all independently:**

| Tier | Previous-close bracket | Percentage parameter |
|---|---|---|
| Tier 1 | > $3.00 | 5% |
| Tier 1 | $0.75–$3.00 | 20% |
| Tier 1 | < $0.75 | lesser of $0.15 or 75% |
| Tier 2 | > $3.00 | 10% |
| Tier 2 | $0.75–$3.00 | 20% |
| Tier 2 | < $0.75 | lesser of $0.15 or 75% |

**The bracket (which row applies) is keyed to the security's PREVIOUS CLOSING PRICE**, fixed for
the session — luldplan.com's own table headers state this explicitly ("PREVIOUS CLOSING PRICE" as
the row determinant), and a search-engine synthesis of Amendment 18 materials independently states
"for Tier 2 securities with a previous closing price greater than $3.00, the percentage parameter
is 10%." This resolves the config's open verification question 2 **for the bracket/percentage
selection specifically** — see §3 for the separate, different answer on *doubling* eligibility.

Sources: [FINRA — Guardrails for Market Volatility](https://www.finra.org/investors/insights/guardrails-market-volatility);
[Cboe Limit Up/Down FAQ (tech-spec page)](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-limit-updown-faq);
[luldplan.com](https://www.luldplan.com/).

## 2. Reference price calculation

**HIGH CONFIDENCE, quoted directly from Cboe's FAQ page:** *"The Reference Price will be the
arithmetic mean price of Eligible Reported Transactions over the past five minutes."* It is
**not** a plain rolling mean recomputed every tick — it has hysteresis: *"The Reference Price is
updated only if the new Reference Price is at least 1% away in either direction from the current
Reference Price."* If no eligible trades occurred in the prior five minutes, *"the previous
Reference Price shall remain in effect."*

**MODERATE CONFIDENCE (one source, not independently corroborated):** luldplan.com states the
recalculation itself runs on a 30-second cadence ("updated after 30 seconds only if a new
Reference price would be least 1% away from the current Reference Price") — i.e. the 1%-hysteresis
check is evaluated every 30 seconds, not continuously. Cboe's FAQ did not mention a 30-second
cadence explicitly; the two are not contradictory (a 30s evaluation cadence is consistent with
Cboe's "is updated only if" language) but the specific number is single-sourced here.

**Price bands are computed from the current reference price, not previous close**, once the
percentage parameter (§1) has been selected: *"Price Band = (Reference Price) +/- ((Reference
Price) x (Percentage Parameter))."* So previous close picks the row; the live reference price sets
the dollar width within that row.

Source: [Cboe Limit Up/Down FAQ](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-limit-updown-faq).

## 3. Doubling window — CORRECTS the current config draft

**HIGH CONFIDENCE, corroborated across Cboe's FAQ, and independently across NYSE/CTA-Plan/Nasdaq
trader-update notices found via search:** as of **Amendment 18, effective 2020-02-24**:

- The **9:30–9:45am opening doubling window was eliminated entirely, for all securities.** (Prior
  to Amendment 18, both an opening and a closing doubling window existed; only the closing one
  survives.)
- The **3:35–4:00pm closing doubling window continues for Tier 1 securities and for Tier 2
  securities with a reference price AT OR BELOW $3.00 at the relevant time.** Quoted directly:
  *"Tier 1 NMS securities and Tier 2 NMS securities with a reference price at or below $3.00 will
  continue to apply double percentage parameters between 3:35 p.m. and 4:00 p.m. ET."* Tier 2
  securities with a reference price **above** $3.00 lost the closing doubling under Amendment 18.

**Correction to the current draft:** `config/phase_12.json`'s `doubling_windows[0].applies_to` and
`.does_not_apply_to` currently say the Tier-2 boundary is "**below** $3.00" / "**at or above**
$3.00." The corroborated boundary is **at or below $3.00 gets doubling; strictly above $3.00 does
not** — i.e. the boundary case ($3.00 exactly) doubles. This is the load-bearing edge case the
config's own note already flags as critical for this universe (median event crosses $3.00
mid-event) — the boundary direction matters and this draft had it backwards by one inclusive/
exclusive step.

**The doubling criterion uses the reference price at the time in question, not previous close** —
a different determinant from §1's bracket selection. This resolves the config's open verification
question 1: doubling eligibility is assessed dynamically (by current reference price during the
window), not fixed from the previous close, and not fixed once at 3:35pm either — the same
reference-price mechanics from §2 apply continuously through the window, so a security's doubling
status can in principle change within the 25-minute window if its reference price crosses $3.00
during it. This document does not find a source explicitly confirming continuous re-evaluation
within the window versus a single check at 3:35pm exactly — flagged as **not fully resolved**,
lower priority than the boundary-direction correction above but still open.

Sources: [Cboe Limit Up/Down FAQ](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-limit-updown-faq);
search synthesis of NYSE ([LULD18_testing.pdf](https://www.nyse.com/publicdocs/nyse/notifications/trader-update/LULD18_testing.pdf)),
CTA Plan ([Amendment 18 notice](https://www.ctaplan.com/publicdocs/ctaplan/notifications/trader-update/CQS_CTS_LULD_A18_Notice_Feb_22_2020_Conf_Test_%26_Activation_LA.pdf)),
and [Nasdaq Trader UTP2019-09](https://www.nasdaqtrader.com/TraderNews.aspx?id=UTP2019-09).

## 4. Sub-$0.75 doubling asymmetry — the config's "upper band only" claim

**MODERATE CONFIDENCE.** A search-engine synthesis states: *"For stocks with a previous close
below $0.75 during market close (3:35pm–4:00pm), the upper band is the lesser of $0.30 or 150%...
For the lower band, if the lesser of the two happens to exceed the minimum price variant ($0.01),
then no lower band is needed."* This reads as a **consequence of the $0.01 minimum price
variation floor**, not a distinct regulatory carve-out that only the upper band doubles by rule —
for a low enough previous close, a doubled lower band would imply a lower bound below the minimum
tick, so no separate lower band is set. The config's existing "UPPER BAND ONLY" language is
directionally supported but the *mechanism* (price-floor consequence, not an asymmetric rule) is
worth keeping in mind since it changes what "upper band only" would mean for events with a
previous close closer to $0.75 than to $0.01. **This sub-detail was not resolved against a fully
verbatim primary-source quote** and is lower priority for this cohort specifically — the config's
own note identifies the $3.00 crossing, not the sub-$0.75 range, as load-bearing for this universe
(Phase 11 A2-6's implied price path is ~$2.21 to ~$4.52, nowhere near $0.75).

Source: search-engine synthesis, exact page not individually re-verified by direct fetch (both
direct PDF fetches attempted for this specific point — Nasdaq's LULD FAQ and Cboe's LULD FAQ PDF —
failed to extract readable text; see §6).

## 5. Limit State and Trading Pause durations

**HIGH CONFIDENCE, quoted:** *"If a security remains in a Limit State for 15 seconds the security
will enter a five minute Trading Pause."* Trading Pause = 5 minutes, followed by a reopening
auction at the primary listing exchange. **Under Amendment 12**, if the reopening auction would
still leave an imbalance, the collar widens by the initial band amount and the pause extends
another 5 minutes; this can repeat. (This specific mechanism was corroborated via one fetch's
paraphrase, not a direct verbatim quote from Amendment 12's own fact sheet — the fact sheet PDF
did not extract readable text in this session; flagged as moderate, not high, confidence, though
it matches `config/phase_12.json`'s existing `pause_duration_seconds: 300` /
`pause_extension_seconds: 300` values.)

Source: [Cboe Limit Up/Down FAQ](https://www.cboe.com/document/tech-spec/document/technical-specifications/cboe-limit-updown-faq).

## 6. Pre-Amendment-18 regime — relevant to this cohort's earliest events

**HIGH CONFIDENCE.** Before **2020-02-24**, LULD doubled percentage parameters in **both** the
9:30–9:45am window and the 3:35–4:00pm window, **for all securities regardless of tier or price**
— there was no Tier-2-above-$3.00 exclusion, because that exclusion is exactly what Amendment 18
introduced. **This cohort's dev sample includes at least one event dated 2020-02-18 (AACG)** —
six calendar days before Amendment 18's effective date — so any band-arithmetic computation on
events before 2020-02-24 must use the pre-Amendment-18 doubling rule (both windows, no Tier-2
price exclusion), not the current-regime rule in §3. Route 3 (band arithmetic) needs an
`effective_date` branch on `2020-02-24`, which the current config does not yet carry.

**No further material LULD price-band, tier, or doubling changes were found between Amendment 18
(2020-02-24) and 2024** — a 2021–2023 annual-report search found only halt/limit-state volume
statistics (e.g. 2023: 64,455 limit states, 7,790 pauses), no rule changes; later amendments found
(No. 23, No. 27) concern SEC filing procedure and overnight-trading protections respectively, not
regular-session band mechanics. This cohort's `era_2022_2024` events are therefore entirely under
the Amendment-18 regime described in §§1–5.

Sources: search synthesis citing [Nasdaq Trader UTP2019-09](https://www.nasdaqtrader.com/TraderNews.aspx?id=UTP2019-09);
[LULD 2021 Annual Report](https://cdn.luldplan.com/reports/LULD-2021-Annual-Report.pdf);
[LULD 2022 Annual Report](https://cdn.luldplan.com/reports/LULD-2022-Annual-Report.pdf);
[LULD 2023 Annual Report](https://cdn.luldplan.com/reports/LULD-2023-Annual-Report.pdf).

## 7. What could not be verified in this session

Direct PDF fetches of the two documents originally drafted as `_draft_sources`
(`nasdaqtrader.com/content/MarketRegulation/LULD_FAQ.pdf` and `luldplan.com`) and of
Cboe's PDF-format FAQ and Amendment 12 fact sheet **did not yield machine-readable text** — the
fetch tool returned binary/encoded PDF structure rather than extractable prose for the PDF-format
documents specifically. `luldplan.com`'s **HTML** page and Cboe's **HTML** tech-spec FAQ page both
fetched cleanly and are this document's primary sources. **This document is therefore a compiled
secondary reference sourced from regulator-adjacent explainer pages and technical-spec FAQs (FINRA,
Cboe, luldplan.com) and a search-engine synthesis of primary regulatory notices (NYSE, CTA Plan,
Nasdaq Trader, SEC DERA), not a direct transcription of the LULD Plan's own legal text or an SRO
rule filing.** Where a fact is corroborated by 2+ independent sources and/or directly quoted, it is
marked HIGH CONFIDENCE above; where it rests on one source or a paraphrase, it is marked MODERATE
and the residual uncertainty is stated plainly rather than smoothed over.
