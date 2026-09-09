# Scale Field — Reading, Detection and Testing: an index

**Added 2026-09-08.** Index for the derivational arc delivered as `scale_field_bundle/` and distributed
into the repo the same day. **Everything in it is synthetic or closed-form. Nothing here has touched the
cohort, and no file below is evidence about this tape.** It records no decision, applies no gate, and
consumes no decision number.

This is the reading order. The five documents cross-cite each other by path, and those citations were
the source of the filenames — they are not new names invented at filing time.

---

## Documents — `claude/`

Read in this order.

1. **`claude/scale_field_reading_grammar.md`** — what each shape in the field (trumpet, dipole, merge,
   tilt, banding) means, derived by writing the statistic in closed form and reading its consequences.
   Includes the noise ruler and **three structural problems with the sign-based burst mark**: the sign
   test's lack of discriminating power is caused by the statistic's asymmetric range, not by a Poisson
   reference, so swapping the reference does not fix it.
   *This is the document `claude/scale_field_instrument_gates.md` §1 records as not existing in the
   checkout. It exists now. That blockquote is left standing as the record of what was true when the
   gates were run — see "Standing" below.*
2. **`claude/scale_field_price_layouts.md`** — laying the field out against price: the linked bandwidth
   slider, the order-flow-imbalance field, the log-price curvature field, and the lead–lag surface.
   Mockup: `results/scale_field/charts/mockups/scale_field_price_mockup.html`.
3. **`claude/scale_field_itt_overlay.md`** — a correction to the above: the inter-trade-interval pane is
   **not** redundant with the `s_min` line. Puts both on one log-duration axis and gives a clustering
   statistic with a universal Poisson constant (1.3396 decades).
   Mockup: `results/scale_field/charts/mockups/scale_field_itt_overlay.html`.
4. **`claude/field_feature_extraction_methods.md`** — the algorithms: closed-form derivatives of the
   field to any order, Newton-solving for apexes and merge points, a ridge-first detection pipeline
   validated end to end on synthetic tapes, and a corrected closed-form duration fit. §5.1 is a
   scale-polishing fix found by the tests in document 5. §10 freezes every free parameter.
5. **`claude/field_credibility_and_value_tests.md`** — whether the detector is trustworthy (invariance
   tests, one of which caught a real defect in a day-old deliverable) and, separately, whether it is
   worth anything (the `s*` histogram against matched nulls, the print-count regression, a held-out
   likelihood compression test, and a benchmark ladder against cheaper alternatives). **The two cheapest
   tests in it are both value tests, and that inversion is deliberate.**

Alongside them, from the executed line rather than this arc:
`claude/scale_field_instrument_gates.md` — the gate battery actually run against the cohort on
2026-09-08.

## Scripts — `research/scale_field/derivations/`

Self-contained, numpy only except 07–08 (scipy + plotly). Each runs from any working directory.

| script | what it does |
|---|---|
| `research/scale_field/derivations/01_verify_calculus.py` | the moment machinery `M_0…M_6`; analytic derivatives against central differences |
| `research/scale_field/derivations/02_apex_newton_solve.py` | Newton solve of `{F = 0, F_t = 0}` for apexes and merge points; the tilt readout |
| `research/scale_field/derivations/03_fingerprint_raw_topology.py` | the raw zero-crossing fingerprint — **why filtering AFTER topology fails** |
| `research/scale_field/derivations/04_ridge_pipeline.py` | the corrected ridge-first pipeline: seed → polish → calibrate → group |
| `research/scale_field/derivations/05_scale_polish_fix.py` | the scale-polishing fix that makes the result resolution-independent |
| `research/scale_field/derivations/06_credibility_tests.py` | the four invariance tests, including the one that failed |
| `research/scale_field/derivations/07_price_mockup_generator.py` | generates the price-layout mockup |
| `research/scale_field/derivations/08_itt_mockup_generator.py` | generates the ITT-overlay mockup |

## Mockups — `results/scale_field/charts/mockups/`

HTML is gitignored under the standing `results/scale_field/charts/*/*.html` rule; both files are
regenerable from the generators above, and
`results/scale_field/charts/mockups/chart_manifest.json` is the tracked record of what they contain.

---

## What was verified on relocation

All eight scripts were run from the repo root after filing. **Every number quoted in the five documents
reproduced**, including the ones the documents lean on hardest:

| claim | document | reproduced |
|---|---|---|
| analytic vs central-difference derivatives | 4 §1 | max rel err 2.8e-9 |
| merge scale recovers separation `D` | 4 §3 | −0.9% / +0.8% / −0.2% at `D` = 80 / 160 / 300 |
| raw-topology-first pipeline fails | 4 §5 | 157 apexes → 1 survivor, and it is an edge artifact |
| ridge-first pipeline on 2 and 4 injected bumps | 4 §5 | 2 of 2 and 4 of 4 found; **0 detections on the matched null** |
| the −0.5 duration readout is biased high | 4 §6 | +28% and +85%; the two-parameter fit −2% and +6% |
| **the seed-independence test failed before §5.1** | 5 §1 | max abs(Δ ln s) = 8.6e-2, max abs(Δcal) = 0.665 |
| **and passes after it** | 4 §5.1 | abs(Δt) < 5e-12 s, abs(Δ ln s) < 5e-13, abs(Δcal) < 1.5e-14 |
| time-rescaling, permutation, thinning | 5 §1 | exact to 1e-15; z-ratio 0.700 / 0.694 / 0.722 vs 0.707 predicted; zero new features |
| the ITT clustering readouts | 3 §2.1, §2.2, §4 | ribbon 2.818 vs 1.304 (Poisson 1.340); `s_min` gap 1.903 vs 0.515 (identity 0.513); 29.3% of cells kept |

**Three defects in the delivered bundle were repaired in the move**, all of them packaging rather than
mathematics: scripts 02, 04, 05 and 06 sourced siblings by names the bundling had renamed away
(`verify_calculus.py`, `fingerprint.py`, `ridgepipe.py`) and so could not run at all; and 07–08 wrote to
an authoring-sandbox output directory that does not exist in this checkout. Sibling sourcing now resolves
through `Path(__file__)`, which also makes every script working-directory independent.

## Standing

- **Nothing here is a finding about the tape.** Every validation is synthetic and Poisson-based, which is
  the easy case. This tape sits ~1.3 decades from Poisson, so a zero false-positive rate on a matched
  Poisson null says nothing about the false-positive rate here — that is what
  `claude/field_feature_extraction_methods.md` §4.3 and the injection–recovery build in
  `claude/field_credibility_and_value_tests.md` §2C are for.
- **The detector's global threshold must come from the matched null, not from the Poisson constant
  0.87.** Deriving a free parameter from a Poisson reference is the failure this arc has already had
  twice (`docs/Universe-Decisions.md` D21–D23).
- **`claude/scale_field_instrument_gates.md` §1's note that the reading grammar "does not exist in this
  checkout" is now stale but is deliberately left unedited** — it was true when the gates were run, and
  the gates re-derived every result they needed from `research/scale_field/scale_field.py`
  independently. Two independent derivations of those results is a stronger position than one, and
  rewriting a report to match later state is not a habit worth starting.
- **This does not close the open item on `claude/scale_space_lessons.md`**
  (`docs/Open-Items-Register.md`). That document is still not in this checkout. What this filing does
  settle is the precedent the item was waiting on: chat-layer documents land in `claude/`, under the
  names the repo already cites them by.
