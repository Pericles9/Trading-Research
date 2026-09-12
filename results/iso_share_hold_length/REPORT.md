# ISO share as a hold-length state variable — dev tier, controls fail, HARD STOP

**Governing prompt:** `prompts/iso_share_hold_length.md`. **Branch:** `iso-share-hold-length` (cut
from `master`, current as of 2026-09-12). **Scope executed:** T0–T3 (dev tier, read-only against
frozen Phase 8/10e artifacts and 49 raw per-event parquet reads). **T4 as originally scoped did not
run** — the prompt's own Escalation Criteria row 8 fired inside T3 and the prompt requires stopping
before trusting any comparison built on data the controls have not cleared.

**Bottom line, stated once at the top:** the raw, uncontrolled result looked like a promising
finding — a 795 bp median-markout separation between high- and low-ISO-share dev events at the
longest horizon (`t3_close`). **It is not trustworthy.** The negative control (a placebo variable
with no relationship to any real data, run through the identical procedure) produces separations up
to **2,258 bp — larger than the real result** — because `t3_close` markout at n=49 is dominated by a
handful of extreme outlier events (+44,768 bp, −9,640 bp) whose side of any split, real or placebo,
swings the group median by hundreds to thousands of bp. **This is not evidence that ISO share
doesn't matter; it is evidence that this sample size cannot currently tell the difference.** No
interpretation beyond that follows (Evidence Standard).

---

## 1. Why this ran: the gate, and what candidate (a) left in place

Per `claude/what_would_change_a_decision.md` §2(b) and §3: candidate (a) (impact by participation,
closed negative, `results/impact_by_participation/REPORT.md`) achieved only a 28.5% cost reduction
(50.71 bp) against the 84.5% reduction (~11.0 bp) that would have reopened the barrier arithmetic —
**far too small to relax candidate (b)'s own cost floor**, which therefore stays at the original
70.98 bp round trip. §1 of this phase's prompt derives, from the already-committed
`results/phase_10e/artifacts/t5_costed_markouts.json`, the exact separation a high-ISO-share
subgroup would need over the pooled median to clear that floor at each horizon (fixed 5-minute entry
latency — Phase 11's cost of record — varying only hold length, per the source document's own "not
entry-timing" instruction):

| horizon | required separation |
|---|---|
| det+15 | 133.9 bp |
| det+30 | 200.5 bp |
| det+60 | 260.7 bp |
| t0_close | 320.5 bp |
| t1_close | 646.1 bp |
| t3_close | 861.8 bp |

---

## 2. T0 — the read path, confirmed live

`conditions` (the SIP condition-code list ISO share needs) is absent from both `filtered_trades` and
`filtered_trades_dev_v4` — checked live, not assumed from the prompt's note. ISO share must read raw
per-event parquet directly. `results/phase_8/artifacts/a102_detection_anchors.parquet` supplies
`det_minute` (15,763 events, 394 `det_undefined` and excluded, matching
`research/phase_10e/t1_candidate_entries.py`'s own filter); `event_minute_bars_v2.first_trade_ts` /
`.last_trade_ts` resolve the entry-anchor window to a concrete `[start_ns, end_ns]` pair per event
without inventing a new anchor. `trade_files()` / `session_window()`
(`research/phase_10/common.py`) are reused for file discovery and the D3 session clock; `conditions`
itself is read directly, mirroring `research/scale_field/fragmentation_identity.py`'s pattern, since
`read_event_trades()` in the same module does not request that column.
Full findings: `results/iso_share_hold_length/artifacts/t0_audit.json`.

---

## 3. T2 — the ISO-share variable

`iso_share(event) = SUM(size WHERE 14 IN conditions) / SUM(size)`, over trades in
`[T=0 session start, last_trade_ts @ minute_index = det_minute + 5]` (nearest prior non-empty bar
where the exact bar has no trades) — 49 of the 50 dev `primary` events resolved (1 `det_undefined`,
coverage 98%, well above the 50% `LOG` threshold). **T2a finding, stated because it was not
assumed:** the distribution is **not** zero-inflated as expected going in — median 19.2%, IQR
[13.9%, 36.4%], **0% of events at exactly zero**. Chart 01:
`charts/01_iso_share_distribution.html`. Full distribution: `artifacts/t2_iso_share.json`.

---

## 4. T3 — the four controls, and why two of them fail

Joined `iso_share` to `results/phase_8/artifacts/a102_detection_markout_grid.parquet` at latency=5
across the six horizons in §1's table (49 events matched, 1 row per event per horizon, confirmed).

**T3c — null-parameter sweep.** Split at 5 quantile cuts (30/40/50/60/70th percentile of
`iso_share`), boundary never chosen by which cut maximizes separation (fixed before any number was
computed). At the median cut, the real separation (high-ISO median minus low-ISO median) ranges from
361 bp (`det+30`) to 795 bp (`t3_close`) — on its face, larger than every one of §1's required
thresholds at every horizon.

**T3a — negative control, FAILS.** A deterministic pseudo-random placebo (no relationship to any
real data), run through the identical split-and-compare code, produces separations up to **2,258
bp** — larger than the real iso_share result at 4 of 6 horizons and larger than every required
threshold in §1. **Escalation row 8 fires: max |placebo separation| (2,258 bp) ≥ smallest required
separation (133.9 bp).**

**T3b — positive control, FAILS (and deviates from the prompt as written).** The prompt named
candidate (a)'s `participation_rate` as the positive control; that variable is print-level while
this phase's join is event-level, so reusing it as written would require new plumbing that
duplicates candidate (a)'s own scope rather than reusing it — recorded here as a disclosed
deviation, not a silent substitution. Instead, a synthetic separation of 133.9 bp (§1's smallest
requirement) was planted directly on a fresh synthetic covariate and run through the identical code.
**It was not cleanly recovered** — several horizons detected a *negative* apparent separation
against a purely additive positive planted effect. **Escalation row 9 also fires.**

**Diagnosis (not interpretation).** `t3_close` markout at n=49 has **std = 7,121 bp**, driven by
single outlier events — UCAR (+44,768 bp, 2024-03-28) and IMTE (−9,640 bp, 2022-09-16) — roughly
50–60× the magnitude of a typical event's markout. At this n, the median of either group is not a
stable statistic: which side of any cut a handful of extreme events land on, real or placebo,
dominates the result. **This is exactly the failure mode the Control Standard's four controls exist
to catch before a real-looking number is trusted**, and it caught it here on the first pass.

**T3d — sustained vs. momentary.** Not meaningfully answerable while the controls fail — the
apparent separation's horizon profile (416 → 361 → 575 → 495 → 767 → 795 bp) is not reported as a
"sustained continuation" finding, because the negative control shows a comparably-shaped and
comparably-sized artifact from pure noise.

Chart 02 (real / negative-control / positive-control / required-separation, overlaid, by horizon):
`charts/02_markout_by_iso_group_and_horizon.html`. Full sweep, both controls, all cells:
`artifacts/t3_separation.json`.

---

## 5. Escalation check

| # | Condition | Observed | Verdict |
|---|---|---|---|
| 1 | Working tree dirty at T0 | clean at every task boundary | pass |
| 2 | Full-tier pass before Cooper approval | none — T0/T2/T3 are dev-tier per-event reads (49 events) and frozen-artifact re-reads only | pass |
| 3 | Write to `results/phase_8\|10e\|11/`, `results/impact_by_participation/`, or `src/` | none | pass |
| 4 | Spine numeric column enters a computed quantity | none — `conditions`, `size`, timestamps are tick-derived | pass |
| 5 | Short-side/fade execution construct | none — "fade" used only as a markout-outcome label | pass |
| 6 | T2's definition changed after T3 computed against it | no — T2 ran once, unchanged | pass, not triggered |
| 7 | Per-group `n < 100` in a headline split | yes, by construction (n=49 total; per-cut groups 15–35) — **this is exactly why T3a/T3b were required, and exactly why they failed** | LOG, superseded by rows 8/9 below |
| 8 | T3's negative control shows separation ≥ smallest required value (133.9 bp) | **2,258 bp** | **HARD STOP — fired** |
| 9 | T3's positive control fails to detect the planted effect at ≥90% of its magnitude | planted 133.9 bp; several horizons detected negative separation | **HARD STOP — fired** |
| 10 | `iso_share` window coverage below 50% | 98% (49/50, excluding 1 `det_undefined`) | pass, not triggered |
| 11 | No horizon clears §1's threshold | not evaluated — controls failed first, so T4's comparison does not run | not reached |
| 12 | Write outside authorised paths | none | pass |

---

## 6. Output files

| File | Status |
|---|---|
| `prompts/iso_share_hold_length.md` | committed |
| `research/iso_share_hold_length/{t0_audit,t2_iso_share,t3_separation}.py` | committed |
| `research/iso_share_hold_length/chart_{01,02}_*.py` | committed |
| `results/iso_share_hold_length/artifacts/{t0_audit,t2_iso_share,t3_separation}.json` | committed |
| `results/iso_share_hold_length/artifacts/t2_iso_share.parquet` | gitignored (regenerable), present locally |
| `results/iso_share_hold_length/charts/{01,02}_*.html` | committed |
| `results/iso_share_hold_length/REPORT.md` | this file |
| `results/reports/iso_share_hold_length_report.md` | copy |
| `results/iso_share_hold_length/digest.json` | machine-readable return path |
| `docs/Open-Items-Register.md` | candidate (b) entry, this dev-tier finding recorded |
| `docs/Claude-Code-Operating-Plan.md` | annotated against row 18/19's price/size channel |

`config/iso_share_hold_length.json` was not needed — every parameter used (latency, cut quantiles,
ISO code, cost constant) is either a fixed literal stated in this prompt/report or read from a
frozen upstream config (`config/phase_10e.json`, `config/phase_11.json`), matching candidate (a)'s
own T1 finding that no new tunables were introduced.

---

## 7. What Cooper is being asked to review

**This is a HARD STOP per the prompt's own Escalation Criteria rows 8 and 9 — not a closed result
either way.** Unlike candidate (a), this is not "closed, negative"; it is "not yet measurable at
this sample size, on this statistic." Three things follow from that, in order:

1. **Is full-tier promotion (the ~15,337-candidate-event universe) worth authorising?** A much
   larger n would give the median far more resistance to single-outlier domination, and is the most
   direct way to find out whether §4's real iso_share separation is signal or the same noise the
   negative control demonstrated. This phase does not authorise that itself (Approval Gate).
2. **Is the statistic itself the problem, independent of n?** The median-split-by-quantile
   comparison may simply be a poor match for a markout distribution this fat-tailed regardless of
   sample size — a trimmed statistic, a rank-based test, or winsorizing before comparing are
   alternatives this phase did not try and does not recommend one of (Evidence Standard; that
   judgment is Cooper's).
3. **`what_would_change_a_decision.md` §4's "run nothing" criterion still cannot be invoked.** It
   requires both candidates to fail; candidate (a) failed by a clear margin, but candidate (b) has
   not yet produced a trustworthy result in either direction — an inconclusive dev-tier read is not
   the same as a failed one, and this report does not treat it as such.

**No recommendation is made on any of these three.**
