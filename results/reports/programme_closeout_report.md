# Mom_db — programme close-out

**Date:** 2026-09-02 · **Type:** cross-phase close-out. **Records no decision.** Next free number: **D26**.
**Audience: a reader with no context** — a future session, or Cooper in a year.

**The test this document is written against:** could someone who has never seen this repository read only
this file and correctly decide what to do next? If a claim below cannot be checked from the artifacts it
names, it does not belong here.

**One-line summary.** Thirteen phases measured whether a micro-cap momentum archive contains a tradeable
intraday strategy under a measured cost stack. **It does not — on either side of the trade, at every
horizon tested, by two independent exit rules.** The research apparatus built along the way is the
durable asset and is universe-independent.

---

## 1. The thesis, as originally stated

From `docs/Mom-DB-Strategy-Research-Program.md` §4.1, verbatim:

> "in this universe, the high-participation windows are not merely tradeable — **they are the only windows
> worth trading**. The real risk does not live in volatility; it concentrates in halt exposure."

The premise was that conventional "avoid the frenzy" logic **inverts** in thin gap names, because outside
the burst there is no market at all. **D5** (2026-08-03) selected the surface it implied: *intraday
post-trigger, long-only, burst-scale horizons* — a strong bull impulse traded as short-horizon long
entries gated on regime. D5 explicitly **killed all short-side variants** and **demoted T+1** to one
optional measurement pass.

**Universe:** events selected by a ≥30% completed daily move, then a `q=0.05` power-law volume filter.
20,951 in-scope events, 2,930 tickers, 2020-01-03 to 2025-10-31; the D1 measurement frame is 15,763.

---

## 2. What closed it, and how

**Both sides are now measured. Neither clears.**

### 2.1 The long side — closed by D25, at both ends

**Intraday, by barriers** (Phase 10e Arm 1, 6,322,397 candidate entries across 15,369 events):

| | |
|---|---|
| cells where `p_clear` reaches break-even | **0 of 90** |
| closest gap in either denominator | **−0.210** |
| named cell (RTH, lat 5, H 30, k=3, m=2) | `p_clear` 0.3621 opt / 0.3372 pess against `p_breakeven` 0.6000 |
| against a **censoring-matched** driftless null | below baseline in **0 of 30 cells** |

The last row is the strong form: **not "the path does not pay" but "there is no drift here to pay with."**
The naive `m/(k+m)` comparator was biased by expiry censoring; a null matched on the observed expiry share
per cell settles it. That null reproduces the observed R1 tie rate to 0.4 pp **without being calibrated on
it** — an unfitted check that the bar-discretisation is modelled correctly.

**Day-scale, by hold-to-horizon** (Phase 8 markout grid re-read against Phase 11's cost):

| | |
|---|---|
| cells where a majority clear one round trip | **0 of 29** |
| median markout at det+5 / t0_close / t1_close / **T+3** | −46 / −351 / −642 / **−886 bp** |
| best cell anywhere (lat 30, t0_close) | 42.7% clear, median −96.8 bp, **167.8 bp short** |

**The day-scale end D5 demoted to archive is the worse one, not a refuge.**

**Why the two disagree in direction, which is itself a finding.** `p_clear` *rises* with horizon while the
markout *falls* with horizon — different exit rules on the same paths. A longer hold gives more chance to
**touch** a distant barrier along the way while the price **at** the horizon keeps decaying. **The upside
excursion is real and the terminal value is not.** That is the programme's "the path is the resource",
measured rather than asserted for the first time — and also why it rescues nothing: at all 90 barrier
settings the excursion is neither frequent nor large enough to clear 71 bp.

### 2.2 The short side — closed on structure, not only on numbers

D5's long-only constraint meant direction was never a variable. Reading the same artifacts sign-reversed
makes the median look strong. **The median is the wrong statistic for a position with bounded gain and
unbounded loss**, so the tail was read before any sign-reversed figure was repeated.

| latency | median capture (t0_close) | median adverse path excursion (H=30, entries <14 min) | ratio |
|---|---|---|---|
| 0 | 350.6 bp | 391.2 bp | 0.90 |
| 5 | 249.5 bp | 342.5 bp | **0.73** |

**At every matched latency the adverse excursion exceeds the capture**, and the horizons are mismatched
the same way (`t0_close` averages ~195 min against a 30-min excursion; at H=60 the latency-5 ratio falls
to 0.57).

The tail itself, entries within 14 minutes of the anchor, H=30: **73.6% breach 2× round trip, 48.8% breach
5×, 26.6% breach 10×**, worst observed **+31,905 bp**. Terminal at T+3: p99 **+10,857 bp**, worst
**+44,768 bp — a 448% adverse move**, and **the six worst events carry no cross-session flag**, so the tail
is not a corporate-action artifact.

**The structural reason no refinement works.** The screen selects on a **completed** ≥30% move. That move
is evidence the name *can* move 30%+ in a session, and shorting it bets against the property it was
selected for. **The selection and the risk are the same phenomenon**, which is why the fade and the squeeze
come out the same size — two readings of one distribution. A short needs its median edge to be large
relative to its adverse tail, and this universe is constructed to make that ratio as bad as it can be.
**So the short is not a parameter problem:** later entry, different barriers, a different horizon each move
a number and none change the structure.

### 2.3 Two questions that were never answerable from disk

- **The live false-positive rate.** The archive's selection is a `q=0.05` quantile line **fitted over the
  pooled 2020–2025 population**, so membership depends on events that had not happened yet — no real-time
  screen can reproduce it *even in principle*. The rejected population is on no table (confirmed at the
  spine: all 23,268 rows sit above the line, zero below), so the lookahead is **unmeasurable from disk**.
  What *is* bounded: a line displacement of **6.5×** would be needed to churn 5% of membership, and the
  median survivor sits **926×** above its own threshold — **the line is not stable, it is irrelevant.**
  Blocked on **data acquisition, not method**; no further method will move it.
- **Population coverage.** **31.9%** of T=0 session highs sit outside RTH — post and premarket **equally**
  at 15.9% each. The archive's selection variable is RTH-scoped (verified against ticks, 0.3867 vs 0.3621
  log-distance test), so the population under-samples events whose move lives outside regular hours. **Not
  a premarket story**, which is how the register had framed it.

---

## 3. What survives, independent of the thesis

These are results, not consolation. Each is checkable from a named artifact.

| finding | value | where |
|---|---|---|
| **`s ≥ 2.26/λ`** — the first applicability criterion in the programme that is **derived, not adopted** | `n_eff = 2√π·s·λ ≥ 8` rearranged | D22, `results/scale_field/` |
| its **causal form** `s ≥ 4.51/λ` — exactly double, because a one-sided kernel keeps half the mass | coefficient 4.5135, test-pinned | D23 |
| **`s_min` relates to forward excursion** — the first connection between a timing statistic and price in this programme | `p_clear` 0.3778 → 0.3003 across bands, non-overlapping CIs | 10e §7, chart 05 |
| **path position moves `p_clear` monotonically** | 0.4268 → 0.3417 across six bands | 10e §7, chart 04 |
| **the cost stack, and its horizon-invariance** | 70.98 bp / 2.512 cents, fixed while movement scales as √H | Phase 11; 10e §17 |
| **later entry is monotonically better** (long side) and carries a **lighter adverse tail** (short side) | 0.3640 → 0.4270; 342 → 214 bp | 10e §18.3, §19.2 |
| the causal re-derivation **reversed** D22's lead result | 3/19 → 19/19 paired, Wilcoxon p = 1.9e−05 | D23 |

The last one is worth its own line: **D22 closed the field as a detector partly because it "necessarily
lags." D23 showed the lag was a property of the centred kernel, not of the statistic.** Fact 1
(saturation) survived; fact 2 did not.

---

## 4. Specification defects, in full

Recorded as defects, not as limitations of findings.

1. **The horizon mismatch in Phase 10e.** Arm 1's finest horizon and latency are both **one minute**;
   the strategy class holds for seconds and acts in 1–3 seconds; Arm 2's grid is in **seconds**. The
   second-scale question was gated behind a minute-scale null, and such a gate is only valid if the cheap
   arm's negative implies the expensive arm's. **It was then argued that this ran in the strategy's
   favour — and the arithmetic says the opposite:** cost is fixed while movement scales as √H, so a
   10-second hold carries **13.4×** the drag of the 30-minute hold that failed. The measured gradient
   agrees in **6 of 6 barrier pairs**. The defect was real; its consequence pointed the other way.
2. **Escalation row 1a was unsatisfiable as written** — it compared frozen inputs against a state at
   `phase-11-approved` that was never recorded, because the inputs are gitignored parquet and **no digest
   stored artifact content hashes**. Caught in pre-flight; would have fired at T0d after the branch and
   config commits.
3. **Three escalation rows failed the T0d satisfiability audit on its first run** — row 2 unscoped, row 6
   missing the `momentum_pct` and A13 carve-outs and therefore firing on the phase's own tasks, and row
   20's inline path list narrower than the config allowlist it duplicated, so the phase could not have
   completed T8b without firing its own row.
4. **A miscalibrated null.** The driftless baseline was first calibrated on raw Parkinson σ, giving a null
   that **expired 23.70% against the tape's 11.34%** — too quiet, which would have reported *drift in 30
   of 30 cells*. Caught by its own diagnostic, recalibrated on the censoring itself.
5. **Four lists drifted from their sources** — the decision pointer (near-collision at D20, real collision
   at D23), the `D:\` hardcode enumeration (11 listed against 24 live, **7 of them writing to D:**), the
   commit staging scope (`git add -A` swept an uncommitted human draft into an unrelated commit), and
   escalation row 20.
6. **References carried forward without re-checking their context** — a config key retained after the
   row it belonged to changed shape; two numbers put in a ratio without checking they sat on the same
   latency; and **five separate unresolvable path citations**: an invented module path asserted as fact
   (`research/scale_space/scale_field.py`), a Project doc cited as repo authority three times
   (`claude/scale_space_lessons.md`), and one register entry pointing at a file the same agent had
   written to a different path. **Same failure as a stale index, at the scale of a single value.**
   **This class is now gated** — `tools/verify_cited_paths.py` resolves every root-anchored path cited
   in `docs/` and `prompts/` against the checkout and exits 1 on any that does not resolve. It was built
   after the fifth instance, it found the fifth instance, and it additionally caught a directory rename
   (`results/phase_6/` → `results/phase_6_rth_only/`) still being cited as a live instruction, and a
   draft-decision filename off by one. Each was repaired. The residual is **one open defect it cannot
   fix**: §6 item 5.
7. **A caveat that pointed the wrong way.** Delisting censoring was recorded as making the adverse tail
   "a lower bound." Asserted, not shown — the censored set contains both the maximum-gain case (delisting
   to zero) and the catastrophic-loss case (an acquisition gap). **Withdrawn and recorded as
   direction-unknown.**

---

## 5. The apparatus — the transferable asset

None of this is universe-specific.

- **`docs/Agent_Prompt_Standard.md`** — the Evidence Standard (no claim without its distribution, no
  statistic without n), the Chart Contract with a *failure appearance* per chart, the Verification Block,
  the Digest Contract. A v1.4 draft is uncommitted and carries three additions: artifact **sha256** in
  digests, **every list has one home**, and **run the check that can come back against you**.
- **Pre-registered kill conditions with tiered escalation rows**, and a **satisfiability audit** that
  gates the phase on whether its own criteria are reachable in both directions.
- **`tools/verify_claude_md_indices.py`** — read-only, exit 1 on drift, run in T0 of every phase. A script
  that silently repaired the index would hide the drift it exists to surface.
- **The sensitivity-versus-counterfactual rule** — on an archive retaining only selected records,
  sensitivity analyses are runnable and counterfactual re-selection analyses are not. Applied at
  specification time it is one line, and it would have re-aimed a whole design.
- **Cost-stack methodology** — effective spread, always cross, both units always (D19), and the finding
  that cost does not scale with horizon.
- **A12/A13 discipline** — cross-session ratios carry a magnitude flag and report with and without it;
  spine numerics may be *read* to audit the selection function under a **write boundary**, never an
  intent test.

**Three times in the final stretch a check ran against the argument that motivated it and changed what got
written.** That is the practice, not luck: keep the check cheaper than the thing it gates, and run it
before the conclusion is committed to.

---

## 6. What a reader should do next

**Nothing further should be measured on this universe before a programme-level decision is taken.** The
thesis is closed on both sides and the two remaining threads are precondition-shaped, not research-shaped.

| # | item | status |
|---|---|---|
| 1 | **The programme-level decision** — does work continue on this universe? | **Cooper's, open.** The line quoted at programme scale — *if the research needs it, the answer is a different universe, not a better method* — comes from **Cooper's read of 2026-08-31**, not from a repo file. `claude/scale_space_lessons.md` is a Project doc and **does not exist in this checkout**; citing it as a source is the defect §4.6 names, so the attribution is stated instead. |
| 2 | **Locate availability** | Precondition on **one thin branch only** (late-entry multi-day short), no longer the gating question. Answered outside the repo. |
| 3 | **Phase 12 (halts/LULD)** | **Reverted to optional.** Promoted while a short thesis was live; that promotion lapsed with §2.2. Specified, drafted, blocked on its `[Cooper]` band table. |
| 4 | **The one variant not excluded** | Late-entry, multi-day short. Capture t1→t3 is 244 bp less 71 bp = **173 bp before borrow**, with unbounded upside risk and Reg SHO live. **No tail read exists at that entry point** — and the tail read is what closed the near-anchor version. If pursued: **that test first, not the markout**, as a phase with a kill condition. |

| 5 | **A load-bearing document does not live in the repo** | **Open, and only Cooper can close it.** See §6.1. |

**What must not happen:** re-running the barrier grid or extending the horizon axis to find a cell that
clears. Ninety barrier cells and twenty-nine markout cells are already a wide sweep; the closest either
comes is 21 points and 168 bp.

### 6.1 The open defect item 5 names

`claude/scale_space_lessons.md` is cited four times across `docs/` and `prompts/` as authority for a
closed item. It is a claude.ai Project doc and **has never existed in this checkout**. The chat layer and
the repo look the same through one interface and different through the other; the executor sees only the
repo, so a Project doc cited in a spec is unresolvable **to the only party that has to act on it**.

Two closures exist and **the agent can perform neither**:

1. **Move the content into `docs/`.** Requires Cooper to supply it — the agent has never seen the
   document, and writing a file under that name from inference would manufacture the authority the
   citation claims. That is a worse defect than the missing file.
2. **Replace each citation with restated content**, attributing it to the read it came from. Also
   requires the content.

Until one happens the path stays in `EXPECTED_ABSENT` in `tools/verify_cited_paths.py`, flagged in the
tool's source as *"the open defect this tool exists to surface, not a benign exception."* It is reported
on every run rather than suppressed, so it cannot quietly become permanent.

### 6.2 If the answer to item 1 is a different universe — five criteria

Each is a **generalisation of a specific failure recorded above**, not a wish list. A candidate universe
that fails any one of them reproduces a failure this programme has already paid for.

| # | criterion | the failure it generalises |
|---|---|---|
| 1 | **The population is reproducible from a written rule.** | The q05 volume screen was recovered only by *fitting* it — `log10(min_volume_threshold) = b0 + b1·log10(momentum_pct)`, R² = 1.0, under D4 Amendment A13. The rule itself was never written down. Recovering a selection function by regression is a rescue, not a standard. |
| 2 | **Rejected candidates are retained, not only survivors.** | A13's first use produced a **hard stop**: `min_volume_threshold` is non-null on all 23,268 rows and every one is above the line, so the rejected population is on no table and the selection lookahead is **unmeasurable from disk**. This is the standing methodology rule in operational form — sensitivity analyses run on an archive of survivors, counterfactual re-selection analyses cannot. |
| 3 | **The round-trip cost is small relative to the move being traded.** | Phase 11 measured **70.98 bp** round trip. Against it, `p_clear` reaches break-even in **0 of 90** barrier cells and the markout clears on a majority in **0 of 29**. D5 chose the horizon class *before that number existed*. The cost stack is a screening input, not a closing check. |
| 4 | **The tape resolves the timescales the strategy trades.** | D22's resolution floor `s ≥ 2.26/λ` (causal: `4.51/λ`) is the first applicability criterion in this programme that was **derived rather than adopted**. Where the event rate cannot resolve the scale, no detector on that tape can, and no amount of method fixes it. |
| 5 | **The selection criterion is not adversarial to the trade direction.** | `momentum_pct` selects on the session high. Every event is therefore at or near its own extreme *by construction* — a long enters after the move it was selected for, and a short is selected into precisely the names that just ran. This is why no refinement of either side works, and it is the one criterion that would have been cheapest to check first and was checked last. |

Criterion 5 is the load-bearing one. Criteria 1–4 are satisfiable by better data collection; **5 is a
property of the selection rule, and no downstream method can repair it.**

---

## 7. The record

**25 decisions** (D1–D25) in `docs/Universe-Decisions.md`, plus three D4 amendments (A9, A12, A13).
**31 phase reports** in `results/reports/`. Open items in `docs/Open-Items-Register.md`. Repo map in
`docs/Research-Library-Map.md`.

The decisions that close things, in dependency order: **D4** (spine numerics quarantined) → **D13/D21**
(the burst object closes) → **D22** (the scale-space field closes as a detector) → **D23** (D22's second
structural fact does not survive a causal kernel) → **D24** (Arm 2 declined on a derived cost argument
and an observed gradient) → **D25** (the long thesis closed at both ends, measured).

**Evidence for everything in this document:** `results/phase_10e/` (REPORT.md §§1–20, digest, charts
01–05, fourteen artifacts with sha256), `results/scale_field/`, `results/scope_universe_scan/`,
`results/reports/phase_{8,9,11}_report.md`.
