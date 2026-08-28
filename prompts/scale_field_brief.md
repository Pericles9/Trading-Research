# Scale-space field on the momentum cohort — build brief

> Committed verbatim as received (2026-08-28), per the standing practice of committing
> the prompt itself before the run. Mojibake in the delivered copy was repaired to the
> intended characters (em dashes, arrows, ×, ≥, ⁻); no wording was changed. Deviations
> taken during the build are recorded in `results/scale_field/REPORT.md` §Deviations and
> in `results/scale_field/digest.json`, not here.

**This is not a phase prompt and does not want to become one.** The method has ~one free
parameter, so there is nothing to pre-register. Correctness is enforced by
`test_scale_field.py`, which is the specification: **if it passes, the estimator is right.**

## What is already done

| File | State |
|---|---|
| `scale_field.py` | Written, tested. Both channels, exact + fast paths, Allan factor. |
| `test_scale_field.py` | 16 assertions, all passing. Poisson-null constants, analytic-derivative vs finite difference (1e-4), sign convention, fast-vs-exact accuracy, duration recovery, time-rescaling invariance, Allan on Poisson, degenerate input. |
| `adapter.py` | **Stub. This is the only thing to write.** |

## What to write

`load_event_prints(event_id, segment) -> int64[ns]`. Its docstring carries every
constraint. Nothing else in the pipeline knows the data layout.

Then a runner that loops the cohort and writes one parquet per event.

## The correction that matters most

**Do not standardise against the analytic Poisson null on this data.** The constant
`SIGMA_POISSON_DECADES = 0.557` is exact for a Poisson process and this tape is nowhere
near Poisson: Phase 10 v3 measured the **Allan factor at 5.99 at T = 15.6 ms, rising
monotonically to 1,245 at T = 4,096 s** — clustering at every scale on the ladder, never
near the Poisson value of 1. A z-score against Poisson would be inflated by roughly
`sqrt(A(T))`: about 2.4x at milliseconds and ~35x at the hour scale. Every threshold would
be meaningless.

**Get the threshold from a matched null instead** — rate-matched inhomogeneous Poisson
realisations simulated from each event's own intensity estimate, with that event's duration
and timestamp quantisation. That machinery was already specified in `prompts/phase_10b.md`
T3c (200 draws, 2.5/97.5 percentile band, reported as a family over the bandwidth rather
than one band). Reuse it; do not rebuild it. The Poisson constant stays in the code as a
**unit-test fixture only**.

## The one gate worth keeping

A reconciliation gate, in the spirit of Diag1's T1d — reproduce a committed prior result or
hard stop:

- `allan_factor()` in `scale_field.py` must reproduce v3's committed curve rung for rung on
  the same dyadic ladder (2⁻⁶…2¹³ s). Any divergence means the point-process handling
  differs from v3's and everything after it is uninterpretable.
- v3's knees — **print rate: 128.0 s regular hours, 16.0 s premarket; volume rate: 64.0 s
  and 16.0 s** — are a prediction for the continuous field. The scale axis should show a
  change of character near them. If it does not, one of the two measurements is wrong and
  that is the finding.

Segments are not poolable: v3 measured 0.903 decades of separation between premarket and
regular hours, already recorded as failure row 5.

## Scale range, and it is bounded at both ends

- **Fine end** — bounded by data, not by choice. Below the local inter-trade interval the
  effective sample size collapses; `field()` returns NaN under `n_eff >= 8` and must never
  be given a fallback. Same treatment as `insufficient_context`. Timestamp resolution is
  ~80.5 ns median (49 ns min), so 2⁻²⁰ s (0.95 µs) is the hard floor; below that you are
  measuring quantisation.
- **Coarse end** — bounded by session length. At s = 4,096 s a regular-hours session
  (~23,400 s) holds ~2 independent windows. v3's headline A = 1,245 sits in exactly that
  low-power zone. Cap the scale axis at roughly `session_span / 8` and state the cap.

## Run plan and cost (measured here, 2M prints, one session)

| Band | Cost / event | 100 events |
|---|---|---|
| coarse, 1 s – 2048 s, whole session, 89 scales | 1.7 s | **~3 min** |
| fine, 15.6 ms – 1 s, ±15 min around the detection anchor | 7.0 s | ~12 min |
| fine, same band, whole session | > 110 s | impractical |

So: **run the coarse band session-wide and the fine band only in a window around the D7
detection anchor** (threshold 1.3, poll interval 1 s, from
`results/phase_10/artifacts/v2_r13_detection.parquet`). The fine end is where the
fragmentation scale lives and it does not need session-wide coverage; the coarse end is
cheap and does.

## Order of work

1. `adapter.py`, plus a test that loads one known event and asserts monotone, positive,
   in-session timestamps.
2. Allan reconciliation against v3. **Hard stop on divergence.**
3. One event, both bands, both channels. **Chart it and stop.** Extend Diag1's chart
   grammar — `plot_boundary_through_time.py` was recorded as reusable for exactly this —
   with the kernel-scale axis replacing the boundary track. Plotly, offline,
   `--plotlyjs directory`, never a CDN (D14).
4. Cooper reads it. This is 10d-R0, moved to the front where it is cheap.
5. Only then: matched-null thresholds, then the cohort.

## What stays from the standard

Numbered decisions, append-only. The evidence standard — no finding without its chart,
every statistic with its n. Frozen cohort with the hash asserted. Segment stratification.
D4. "The artifact wins; discrepancies are reported, not silently fixed." And the rule that
evidence survives the method being closed.

## What is deliberately absent

No T0/T1/T2 task tree. No escalation table beyond the reconciliation stop. No parameter
grid — there is no parameter to grid. No counterfactual-gate reporting.

**And the line for when this comes back:** the moment anything here touches forward
returns, the full standard applies again, pre-registered, no exceptions. Ground truth is
what makes light process safe, and forward returns are where it runs out.
