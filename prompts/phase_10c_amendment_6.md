# Phase 10c — Amendment 6: Auction Rule Closure and Stream Composition Record

**Status:** Formal amendment. Closes the two items left outstanding by Amendment 5. Short by
design — both are settled, nothing here blocks Stage 1.

---

## A — Auction rule scope: all trades

**Decision:** the closing-auction rule keys on codes **{8, 15}** and applies to **all trades**, not
anchor classification alone. Any print carrying code 8 (Closing Prints) or code 15 (Market Center
Official Close) is assigned to the session whose close it settles, regardless of timestamp.

**Rationale.** Anchor-only scope is internally inconsistent, not merely narrower. Under it, ACET's
anchor would sit in day T while its own twin — the official-close record 92 µs later — stayed
attributed to day T+1. The tick stream and the anchor would disagree about which session the
closing cross belongs to.

**Affected population:** 291 near-close prints carrying 8 or 15, against 25,218,726 prints in the
cohort — 0.001%. The cost of consistency is nil.

**Standing limitation, unchanged from Amendment 5:** the dictionary confirms what codes 8 and 15
mean. It does not establish that {8, 15} captures every closing auction in the archive, or that no
non-auction print carries them. Empirical plus semantic, not validated.

### Code 9 — final note

Zero prints in the 877-print near-close census carry code 9 without 8 or 15 (76 carry 9; 291 carry
8 or 15). **On this cohort {8, 15} and {8, 9, 15} are identical in effect**, so the data does not
independently support dropping 9. The decision rests entirely on the semantic argument: Cross
Trade carries no session or auction meaning, and its after-close exclusivity here is a property of
these 114 events rather than of the code. Recorded this way rather than letting the zero read as
corroboration.

---

## B — Stream composition: recorded descriptively, no further work

**Decision: the census is recorded as a descriptive fact. No exclusion, no filter, no follow-on
diagnostic in Phase 10c.**

Cohort: 25,218,726 prints across 114 events. No exclusion applied anywhere.

| Class | Codes | Count | Share |
|---|---|---|---|
| Non-volume-updating | 15, 16, 38 | 3,868 | 0.0153% |
| Volume-updating, not last-sale | 2, 7, 12, 13, 21, 37, 52, 53 | 13,005,055 | 51.57% |

By segment:

| Class | evening | premarket | rth |
|---|---|---|---|
| Non-volume-updating | 0.0242% | 0.0165% | 0.0032% |
| Volume, not last-sale | 52.02% | 57.66% | 42.41% |

**What this establishes:** more than half the interval stream carries a code the vendor marks as
not updating last sale. These are real executions and real volume — not exclusion candidates. What
changes is that "what the stream is made of" is now a measured majority-share fact rather than an
assumption.

**Nothing in Phase 10c is altered by this.** Stage 0b measured on the current print definition and
that definition stands.

### B1 — Dissenting note, recorded

Claude (analysis) recommended two follow-on measurements and Cooper declined them. Recording the
reasoning on both sides so a future phase inherits the argument rather than the conclusion alone.

**The case for measuring:** Form T cannot account for RTH's 42.41%, since RTH trades are not
extended-hours by definition. That share is therefore likely dominated by **code 37, Odd Lot**.
Runs of sub-100-share fills microseconds apart are the signature of order fragmentation — the
phenomenon that produced v4's 349 ns median sub-burst and motivated this phase. If fragmentation
is identifiable by a flag the vendor already publishes, that is a better instrument than any size
or interval cutoff this program has ruled out, and it costs two queries.

**The case against, as decided:** Phase 10c's premise is that a clock-time normalization window
resolves the scale problem without separately identifying fragmentation, and the multi-kernel grid
exists to let scales separate on their own. Opening a second investigative thread mid-phase is
scope creep against a phase that already carries five amendments.

### B2 — Recorded to the Open Items Register

Per the Phase 11 T1c-iii precedent — where recording the opaque condition codes is what made this
phase's dictionary retrieval possible — the following goes to `docs/Open-Items-Register.md`
without being acted on:

- The retrieved dictionary location (`data/metadata/massive_trade_conditions.json`, subject to C
  below).
- The census tables above, with cohort size and the no-exclusion note.
- The odd-lot hypothesis: RTH's 42.41% volume-not-last share is unexplainable by Form T and is
  likely code 37 dominated; whether odd-lot prints show materially shorter inter-trade intervals
  than round-lot prints is **unmeasured**.
- The two unrun measurements, stated precisely enough that a future phase starts from them rather
  than rediscovering the question: (1) per-code breakdown of the 51.57% by segment, (2) interval
  distribution split by odd-lot flag.

---

## C — Dictionary file location: move it

The dictionary was force-added (`git add -f`) into `data/`, which is fully gitignored. The
instinct is right — a file that vanishes on a fresh clone defeats the purpose of storing it — but
the location is wrong.

**Problem:** force-adding into a fully-ignored tree leaves a trap. Anyone reading `.gitignore`
will conclude `data/` is untracked; this one file silently is not. Future `git add` on sibling
paths will behave differently from this one with no visible reason.

**Decision: move it to a normally-tracked path** — `docs/` or `config/` — and leave `data/`
genuinely ignored. Same durability, no surprise, no precedent for force-adding into ignored trees.
The file is 2 KB of vendor reference text; it is not data and does not belong under a data root
regardless of tracking.

Not modifying `.gitignore` was the correct restraint.

---

## D — Amendment 5 items closed

- **5.A (dictionary stored)** — done, subject to the move in C. Partial-by-design marking is
  correct: nine codes with full attributes, six named with only the stated attribute, and codes
  absent from the file carry no offline meaning and must not be inferred.
- **5.B (code set)** — {8, 15}, scope all trades, per A above.
- **5.C (code 15 is not a trade)** — confirmed at 0.0153% cohort-wide. As anticipated, immaterial
  to the aggregate interval distribution; recorded, not acted on.
- **5.D (census)** — delivered; recorded per B.
- **5.E (BMR 5-share odd-lot anchor)** — carried to D7, unchanged.
- **5.F (per-event floor)** — confirmed by code path: `t1_subbursts.py` computes
  `sigma = np.std(li, ddof=1)` on each event's own log intervals, then
  `median_se_min_count(sigma, F)`. Nothing segment-level enters. **A4 dissolves; no evening σ
  exists to set and none is needed.** The 1.363 / 1.758 figures are medians of per-event σ, for
  reporting only.
- **5.H (float64 / timestamp resolution)** — resolved. The resolution chain is int64 end to end:
  `sip_timestamp` int64 on disk → `.to_numpy()` int64 → `np.diff` int64 → `min_nonzero_gap_ns`
  int64. T1's median 80.5 ns and minimum 49 ns stand as reported, and **the fragmentation-floor
  reasoning built on them is unaffected.** The 256 ns quantization is confined to `det_ns_*`, a
  different column on a different chain that never enters a resolution measurement. The int64
  repair of `det_ns_*` remains outstanding as a source-data fix.

---

## E — Carried forward

- **`det_ns_*` int64 repair** — before anything depends on exact anchor round-tripping. Phase 10c
  is unaffected (nearest-match recovers all four post-close anchors at 0 ns residual).
- **Eligible-pool gap** — 15,299 eligible against D14's 20,951 canonical in-scope events; 5,652
  events (27%) unexplained. Required before any full-population run.
- **A2.7.D17_burst_envelope_boundary** — delivered in a3fe68b, still pending Cooper's read.
- **Auction rule validation** — empirical plus semantic, not validated. Standing.

**Nothing in this amendment blocks Stage 1.**