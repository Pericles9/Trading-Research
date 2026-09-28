> **Filing note (Claude Code, 2026-09-27).** Filed verbatim as pasted, on branch `explore/shape-atlas-s1` (cut from
> `explore/attention-excursion-b2` at `259e811`). Config: `config/shape_atlas_s1.json`; code: `research/shape_atlas_s1/`;
> outputs: `results/shape_atlas/s1/`. Two rulings Cooper gave before the build (2026-09-27): section 6's fundamental
> columns are included under a logged exception to D32 (D39, `docs/Universe-Decisions.md`), and section 4c's across-time
> check runs as written and also ticker-blocked.

# Shape atlas — S1: what kinds of path do momentum events actually make?

**Date:** 2026-09-27 · **Type:** exploratory build. **Not a phase, not a test.**
**Hindsight is allowed on purpose (Cooper, 2026-09-27).** The purpose is to find out whether events come
in distinct path types, what those types look like, and what goes with each one. Look-ahead, outcome
conditioning and reading every slice are all permitted. D38 slices are ignored here. The report header
says so in one line: *exploratory, hindsight used by design; nothing here is a tested result.*
**Branch:** `explore/shape-atlas-s1`, cut from `explore/attention-excursion-b2` at `259e811`. It reuses
b2's τ, excursion vectors, attention axes and competition artifacts as they are.
**Outputs:** `results/shape_atlas/s1/` (artifacts, charts in per-task subfolders, REPORT.md plus its copy
in `results/reports/`). Config: `config/shape_atlas_s1.json`, committed before the run, for
reproducibility only.
**Ends at a stop (T8)** for Cooper to read the atlas.

---

## 0. Why, in five lines

1. Step zero's post-τ rise matched noise at every quantile, but only as a marginal.
2. Peak timing and rise size read **together** did not match noise. There was about 2.5× the noise
   share of early, big rises (25% vs 10%), and half the noise share of late peaks (30% vs 50%). This held
   in every year from 2020 to 2024.
3. So the average may be hiding several distinct shapes that cancel out.
4. This brief maps those shapes properly, with the checks that were missing from that first look: a null
   that keeps each event's fat tails, clustering judged against that null, and stability across years.
5. It then describes everything that goes with each type, including attention and fundamentals, without
   restriction.

---

## 1. Three views of each event's path

All three use the programme's instrument: equal-volume buckets, bucket VWAP, heights over
`σ_path = sqrt(Σ r²)` of that view's own bucket log returns. D4 tick-derived. The spike guard applies.

| view | span | why |
|---|---|---|
| **post-τ** | τ → last print ≤ 20:00 ET | b2's vector, reused unchanged at N ∈ {50, 100, 200} |
| **run-up** | segment start (04:00 / 09:31 / 16:01) → τ, **plus** the overnight gap as its own number | how the stock got to +30% |
| **whole day** | first event-day print → last print ≤ 20:00, with τ marked on the volume clock | the full rise and fall in one shape |

For the run-up and whole-day views, also carry the price axis as `log(price ÷ prior close)`, so the +30%
line is the same height for every event. Carry `gap_share = log(first print ÷ prior close) ÷ log(1.30)`.
It is the share of the +30% already done overnight, with 1.0 meaning the stock opened at the threshold.

**Resampling for shape work:** each view's normalised path is resampled to **G = 100 points** on its own
volume clock. That gives one fixed-length vector per event per view, which is what the clustering reads.

## 2. The null — each event's own returns, shuffled

For every event, view and rung: **200 seeded free walks drawn with replacement from that event's own
demeaned bucket log returns**, re-integrated and put through the identical pipeline. This keeps the
event's fat tails, jumps and tick-size effects, and removes only the ordering and the drift. It replaces
the Gaussian reference for everything in this brief. The Gaussian reference was the stated weakness of
the first look.

Per event, carry `rise_pct` and `fall_pct`: where the event's `rise_s` and `fall_s` sit within its own
200 null draws, from 0 to 100.

## 3. Theory types — declared here, before the run

Assigned from the post-τ vector at N = 100, in this order (first match wins), using the event's own null
percentiles. "Beyond noise" means above the 90th percentile of the event's own null. That cut comes from
the null, not from the data's distribution.

| type | rule | what the theory calls it |
|---|---|---|
| **runaway** | `rise_pct ≥ 90` and `u_peak ≥ 0.9` | still going at the close |
| **burst** | `rise_pct ≥ 90` and `u_peak < 0.5` | fast continuation, then give-back |
| **slow climb** | `rise_pct ≥ 90` and 0.5 ≤ `u_peak` < 0.9 | continuation that takes most of the day |
| **exhausted** | `u_peak < 0.05` and `rise_pct < 50` | the move was over at τ |
| **fade** | `fall_pct ≥ 90` (and none of the above) | a decline beyond noise without a real rise |
| **chop** | everything else | nothing beyond noise either way |

Report each type's share overall, by year, by segment, by price tier (< $1 · $1–3 · $3–10 · ≥ $10), and
by rung (the same rules applied at N = 50 and 200, to show how much the rung moves the assignment). Run the
same rules on the null draws too: **the share of each type that noise alone produces** goes beside every
real share.

## 4. Data-driven types — and whether they beat noise

Run each method on the **post-τ** and **whole-day** resampled paths separately, and on the null paths
through the identical pipeline.

**4a. Shape components.** Functional principal components (FPCA) on the resampled paths. Report the
variance spectrum (share of variance per component) for real vs null, and draw the first five components
as shapes. **Structure exists only where the real spectrum is steeper than the null's.**

**4b. Clusters.** Two methods, read side by side, neither privileged:
- Gaussian mixture on the FPC scores (components that explain 90% of variance), k = 2 … 8.
- k-means on the resampled paths themselves, k = 2 … 8.

For each k, report BIC (mixture), silhouette (both), and **the same statistics on the null**. The
decision-relevant picture is **real minus null** across k, not the best k. Also report agreement between
the two methods (adjusted Rand index) at each k. **No k is chosen by the brief.** Assignments are carried
for every k so Cooper can read any of them.

**4c. Stability.** For each method and k:
- **Across time:** fit on 2020–22, assign 2023–24 events to the nearest centroid. Compare centroid shapes
  (correlation between matched centroids) and type shares. Then fit on 2023–24 and assign 2020–22.
- **Across resamples:** 50 bootstrap refits resampling tickers, not events, since tickers repeat. Report
  each event's co-assignment rate (how often it lands with the same neighbours).

A type that appears in real data, beats the null, and reproduces across the two periods counts as a
structure in this atlas. Anything else is labelled as not distinguishable from noise or not stable.

**4d. Theory vs data.** Cross-tab the §3 theory types against the data-driven clusters at every k.

## 5. Run-up shapes, and how they lead into post-τ shapes

Using the run-up view (§1):

- **Run-up descriptors:** `gap_share`; launch point `u_launch` (volume-clock position of the lowest
  bucket before τ); run-up height (log τ-price ÷ run-up low, over run-up `σ_path`); largest drawdown
  inside the run-up, over `σ_path`; number of pushes (drawdowns of at least 1 `σ_b` that are recovered
  before τ); run-up duration in minutes and in volume; `a2_ignition` from b2.
- **Run-up types:** the same §4 pipeline (FPCA, both clusterings, null, stability) on the resampled
  run-up paths. Also three declared descriptive classes: **gap** (`gap_share ≥ 0.8`), **late spike**
  (`u_launch ≥ 0.8`), **grind** (neither).
- **The transition table:** run-up type → post-τ type (theory types and data clusters), with counts and
  row shares, overall and by segment. **This is the table that shows whether how a stock got to +30%
  goes with what it does after.**

## 6. The atlas — everything that goes with each type

For each post-τ theory type, and each data cluster at every k:

- **Centroid path** with its IQR band on the volume clock, at the selected rung, with the null centroid
  drawn beside it.
- **Gallery:** the 12 members closest to the centroid and 12 drawn at random (seeded). Each shows its
  actual bucketed path with τ, peak and end marked, ticker and date.
- **Vector and money:** medians and IQR of every excursion component, plus `rise_bp`, `rise_cents`,
  `fall_bp`, minutes from τ to peak, and **excess rise in bp** (`rise_bp` minus the event's own null
  median rise in bp). The last one is the honest money figure.
- **Everything else, described (hindsight fine):**
  - attention: turnover, the `accel_k` curve, the absolute trade-rate and dollar-flow levels,
    `a2_ignition`, `flow_share`, `live_n`, the competition excess;
  - catalyst: filing within 24 h, last form, dilution flag;
  - fundamentals: shares outstanding, reverse split in 365 days, short interest;
  - tape: `jump_share`, halts, `tau_close_sensitive`, A12 flag, time of day, segment, year, price tier;
  - the run-up descriptors and run-up type.

  Each is shown as its full distribution per type, with n, never a lone median.
- **Type share by date:** how many of each type occur per session, and whether types cluster on the
  same days. This bears directly on the competition check's same-day confound.

## 7. Charts

One file per chart with selectors, never 100 files. Plotly inlined (D14), dark theme, n on every panel.

- `atlas.html`: pick a view, method, k and type → centroid, band, null centroid, gallery, descriptor
  distributions.
- `null_comparison.html`: FPC spectra and BIC/silhouette across k, real vs null, per view.
- `stability.html`: centroid matching across the two periods, co-assignment distributions.
- `theory_types.html`: type shares, real vs null, by facet and rung.
- `transitions.html`: run-up type → post-τ type.
- `joint_peak_rise.html`: the 2D peak position × rise size density, real vs each event's own null.
  This is the picture that started this brief.

## 8. Report and stop

REPORT.md describes the pictures. **No interpretation, no findings section.** It opens with coverage and
the assertions, then §3–§6 in order. All numbers are read from artifacts by code. Commit, push, post:

- the theory-type shares, real vs null;
- the real-minus-null curves for both clustering methods, per view;
- the stability numbers;
- the transition table.

Then stop.

## 9. Housekeeping

- **Assertions (a failure is a stop):** bucket volume conservation in every view; every resampled path
  has exactly G points; `tau_ns` int64; null paths go through the identical code path as real ones (a
  test feeds one real path through both and requires identical output when the shuffle is the identity).
- **Coverage:** report per view. The run-up view is expected to be unavailable or thin for some
  auction-minute and early-premarket crossers. Carry those as their own class, never drop them.
- **Named paths staged, push at each task boundary.**
- **Nothing in `scanner-epg-momentum` or `hawkes-ofi-impact` is touched.**
