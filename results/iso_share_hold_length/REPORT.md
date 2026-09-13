# ISO share as a hold-length state variable — dev tier, controls fail; full-tier precheck resolves why

**Governing prompt:** `prompts/iso_share_hold_length.md`. **Branch:** `iso-share-hold-length` (cut
from `master`, current as of 2026-09-12). **Scope executed:** T0–T3 (dev tier, read-only against
frozen Phase 8/10e artifacts and 49 raw per-event parquet reads), then **T4, a full-tier noise-band
precheck** added after review — read-only against an already-committed, already-full-universe
artifact, zero new tick reads, zero full-tier query. **T4 as originally scoped (compare T3's real
result against Sec 1's threshold) still does not run** — that comparison would report on data T3's
own controls showed was not trustworthy. T5 (the actual full-tier ISO-share build) remains blocked
on Cooper's explicit review of this report, per the Approval Gate — this update does not authorise
it, and its statistical case being strong is a different question from Cooper choosing to spend the
per-event read budget it costs.

**Bottom line, stated once at the top:** the raw, uncontrolled dev-tier result looked like a
promising finding — a 795 bp median-markout separation between high- and low-ISO-share events at
the longest horizon (`t3_close`). **It was not trustworthy at n=49** — a negative-control placebo,
run through the identical procedure, produced separations up to 2,258 bp, larger than the real
result. **The added T4 precheck now explains why, precisely, and shows the problem is resolved by
sample size, not by the statistic or the covariate.** A bootstrap of pure-random 50/50 splits over
the already-committed full-universe markout grid (~15,330 events, not 49) shows the required
separation clearing the null distribution's **5,000-repetition maximum by 12–19× the null's own
standard deviation at every horizon** — `P(null ≥ required) = 0/5000` everywhere. **The dev-tier
failure was a power problem, not a validity problem**, and full tier is capable of telling a real
ISO-share effect from noise if one exists. No claim is made here about whether one does — that is
exactly what T5 would measure, and T5 has not run. No interpretation beyond this follows (Evidence
Standard).

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

**Diagnosis, corrected after review (not interpretation).** An earlier version of this section
attributed the failure to "outlier events dominating the median" — imprecise, since a median is
outlier-resistant by construction and a single event (however extreme) barely moves it. The real
mechanism is that the **bulk** of `t3_close` markout is itself enormously dispersed at n=49 — IQR ≈
3,100 bp, std = 7,121 bp (two genuinely extreme events, UCAR +44,768 bp and IMTE −9,640 bp, sit
outside even that IQR and confirm the tail is real, but are not what is driving the control
failure). The standard error of a *difference of two medians* at roughly 25 events per group scales
as `≈0.93 × IQR / sqrt(n)` ≈ 575 bp — so the negative control's observed 2,258 bp maximum across 30
swept cells is about 2.8 such standard errors, which is exactly the shape of ordinary sampling noise
at this n, not a special artifact of any single print. **This is precisely the failure mode the
Control Standard's four controls exist to catch before a real-looking number is trusted, and T4
below turns the diagnosis into a design input rather than leaving it as a post-hoc explanation.**

**T3d — sustained vs. momentary.** Not meaningfully answerable while the controls fail — the
apparent separation's horizon profile (416 → 361 → 575 → 495 → 767 → 795 bp) is not reported as a
"sustained continuation" finding, because the negative control shows a comparably-shaped and
comparably-sized artifact from pure noise.

Chart 02 (real / negative-control / positive-control / required-separation, overlaid, by horizon):
`charts/02_markout_by_iso_group_and_horizon.html`. Full sweep, both controls, all cells:
`artifacts/t3_separation.json`.

---

## 5. T4 — full-tier noise-band precheck, added after review

T3's diagnosis (§4) explains the dev-tier control failure but was computed after the measurement,
which is a process gap: the same negative control, calibrated at the sample size any full-tier
promotion would actually use, is a design input for the promotion decision, not only a post-hoc
explanation for why dev tier failed. This task adds that calibration — **read-only against
`results/phase_8/artifacts/a102_detection_markout_grid.parquet`, which already carries the full
~15,330-event candidate universe at every (latency, horizon) cell (confirmed live, not assumed).
Zero new tick reads, zero new full-tier query — this is a bootstrap over an already-committed
artifact**, and does not itself constitute or require full-tier promotion.

**Method.** 5,000 repetitions of a pure-random 50/50 split of the real event population (no
`iso_share` involved — this is what full-tier noise looks like, not what full-tier ISO share looks
like), difference of group medians in bp each time, at latency=5 across the same six horizons.

**Sanity check first.** Re-running the identical bootstrap restricted to the 49 dev events T3 used
reproduces T3's actual finding closely: null-separation maximum of 2,507 bp at `t3_close` (5,000
reps) against T3's own reported 2,258 bp (30 swept cells) — same mechanism, same order of magnitude,
confirming the bootstrap's methodology before trusting its full-tier answer.

**The full-tier result.**

| horizon | required separation (bp) | null p95 (bp) | null max, 5000 reps (bp) | required ÷ null std |
|---|---|---|---|---|
| det+15 | 133.9 | 16.4 | 30.2 | 16.2× |
| det+30 | 200.5 | 21.5 | 44.6 | 17.9× |
| det+60 | 260.7 | 32.3 | 57.5 | 16.0× |
| t0_close | 320.5 | 50.7 | 90.1 | 12.7× |
| t1_close | 646.1 | 67.4 | 171.6 | 17.9× |
| t3_close | 861.8 | 84.1 | 146.9 | 19.2× |

At every horizon, the required separation clears the null distribution's **5,000-repetition maximum**
by 12.7–19.2× the null's own standard deviation; `P(null ≥ required) = 0/5000` at every horizon.
**The dev-tier control failure was a sample-size problem, not a problem with the statistic, the
covariate, or the join** — full tier is a fundamentally different, well-powered regime for this
exact test. Chart 03 (full-tier vs. dev-tier null band against the required-separation line, log
scale): `charts/03_noise_band_precheck.html`. Full results: `artifacts/t4_bootstrap_precheck.json`.

**What this precheck does not do.** It does not measure whether `iso_share` has a real effect — only
whether full tier is *capable* of measuring one if it exists, which T5 (blocked) would actually do.
It also does not, by itself, authorise T5: T5 still requires reading `conditions` from ~15,337
events' raw per-event parquet files, with no DuckDB shortcut (T0), a real if bounded cost this
precheck was designed specifically to avoid spending before the statistical case was established.

**A caveat for whoever reviews this, raised in discussion and not resolved here.** Chakravarty, Jain,
Upson & Wood (2012) document ISO's forward content over price-discovery timescales of seconds to
minutes — the same timescale D24 already closed on cost-scaling grounds, which is exactly why
`what_would_change_a_decision.md` §2(b) required this candidate to be posed as a hold-length question
instead. That reframing may have moved the day-scale horizons (`t1_close`, `t3_close`, requiring
646–862 bp separation) past anything the cited literature actually reports, independent of sample
size — a literature-based ceiling this report does not evaluate. It does not obviously reach
`det+15`'s 134 bp requirement, which sits closer to the timescale the literature does address. Left
for Cooper's judgment, not decided here (Evidence Standard).

---

## 6. Escalation check

| # | Condition | Observed | Verdict |
|---|---|---|---|
| 1 | Working tree dirty at T0 | clean at every task boundary | pass |
| 2 | Full-tier pass before Cooper approval | none — T0/T2/T3 are dev-tier per-event reads (49 events); T4 is a bootstrap over an already-committed, already-full-universe artifact, no new query | pass |
| 3 | Write to `results/phase_8\|10e\|11/`, `results/impact_by_participation/`, or `src/` | none | pass |
| 4 | Spine numeric column enters a computed quantity | none — `conditions`, `size`, timestamps are tick-derived | pass |
| 5 | Short-side/fade execution construct | none — "fade" used only as a markout-outcome label | pass |
| 6 | T2's definition changed after T3 computed against it | no — T2 ran once, unchanged | pass, not triggered |
| 7 | Per-group `n < 100` in a headline split | yes, by construction (n=49 total; per-cut groups 15–35) — **this is exactly why T3a/T3b were required, and exactly why they failed; T4 confirms it's an n problem, not a validity problem** | LOG, superseded by rows 8/9 below |
| 8 | T3's negative control shows separation ≥ smallest required value (133.9 bp) | **2,258 bp** | **HARD STOP — fired** |
| 9 | T3's positive control fails to detect the planted effect at ≥90% of its magnitude | planted 133.9 bp; several horizons detected negative separation | **HARD STOP — fired** |
| 10 | `iso_share` window coverage below 50% | 98% (49/50, excluding 1 `det_undefined`) | pass, not triggered |
| 11 | No horizon clears §1's threshold | not evaluated — controls failed first, so T4's original framing (compare against threshold) does not run; T4 was rescoped to a noise-band precheck instead | not reached as originally scoped |
| 12 | Write outside authorised paths | none | pass |

---

## 7. Output files

| File | Status |
|---|---|
| `prompts/iso_share_hold_length.md` | committed |
| `research/iso_share_hold_length/{t0_audit,t2_iso_share,t3_separation,t4_bootstrap_precheck}.py` | committed |
| `research/iso_share_hold_length/chart_{01,02,03}_*.py` | committed |
| `results/iso_share_hold_length/artifacts/{t0_audit,t2_iso_share,t3_separation,t4_bootstrap_precheck}.json` | committed |
| `results/iso_share_hold_length/artifacts/t2_iso_share.parquet` | gitignored (regenerable), present locally |
| `results/iso_share_hold_length/charts/{01,02,03}_*.html` | committed |
| `results/iso_share_hold_length/REPORT.md` | this file |
| `results/reports/iso_share_hold_length_report.md` | copy |
| `results/iso_share_hold_length/digest.json` | machine-readable return path |
| `docs/Open-Items-Register.md` | candidate (b) entry, this dev-tier finding recorded |
| `docs/Claude-Code-Operating-Plan.md` | annotated against row 18/19's price/size channel |

`config/iso_share_hold_length.json` was not needed — every parameter used (latency, cut quantiles,
ISO code, cost constant, bootstrap reps/seed) is either a fixed literal stated in this prompt/report
or read from a frozen upstream config (`config/phase_10e.json`, `config/phase_11.json`), matching
candidate (a)'s own T1 finding that no new tunables were introduced.

---

## 8. What Cooper is being asked to review

**This is a HARD STOP per the prompt's own Escalation Criteria rows 8 and 9 — not a closed result
either way.** Unlike candidate (a), this is not "closed, negative"; it is "not yet measurable at
n=49, and now shown to be measurable at full tier if a real effect exists." Three things follow,
in order:

1. **Full-tier promotion's statistical case is now established, not a judgment call — T5 itself
   still needs Cooper's authorisation.** §5's precheck shows the required separation clears the
   full-tier noise band by 12.7–19.2× at every horizon, at zero cost (no new tick reads). What T5
   would cost is real: ~15,337 events' worth of raw per-event `conditions` reads, with no DuckDB
   shortcut (T0). This report recommends running the precheck was worth it; it does not recommend
   spending T5's budget — that weighing is Cooper's.
2. **The literature-ceiling caveat (§5) may bear on which horizons are worth promoting.** `det+15`'s
   134 bp requirement sits closer to the timescale Chakravarty et al. (2012) actually document;
   `t1_close`/`t3_close`'s 646–862 bp requirements may already exceed what that literature supports,
   independent of sample size. This report does not evaluate that ceiling quantitatively and does
   not choose a subset of horizons to promote.
3. **The statistic itself was not changed, and should not be tuned now that a full-tier path looks
   promising.** Reaching for a trimmed or rank-based statistic after seeing an unfavorable dev-tier
   result would be exactly the tune-until-it-fires pattern the Control Standard exists to prevent.
   If full tier is authorised, T5 uses the same median-split procedure T3 specified, with the same
   controls, at the sample size §5 shows can support them.
4. **`what_would_change_a_decision.md` §4's "run nothing" criterion still cannot be invoked.** It
   requires both candidates to fail; candidate (a) failed by a clear margin, but candidate (b) has
   not yet produced a trustworthy result in either direction — an inconclusive-but-now-well-powered
   read is not the same as a failed one, and this report does not treat it as such.

**No recommendation is made on any of these three.**
