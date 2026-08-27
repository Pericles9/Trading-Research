# Phase 10d — Diagnostic 1, Charts Addendum

**Date:** 2026-08-27
**Branch:** `phase/10d-diag1` (continues)
**Type:** Charts. **Not a phase, not new analysis.** The frames already exist from Diag1 T1.
**Objective:** One distribution-and-boundaries-through-time chart for **every event in the
tape-review set**, from the frames already committed.
**Primary success metric:** Cooper can page through the set and compare boundary positions
across events without doing arithmetic.

**Diag1's numbers are committed and correct. This addendum adds no measurement, no table,
no finding.** It exists because Diag1's reporting section asked for nine tables and one
person asked for pictures. The pictures are the deliverable.

---

## 1. Constraints

- **Nothing is recomputed and nothing is decided.** No boundary rule adopted, no parameter
  tuned, no cutoff applied. `docs/` untouched. **10d-R0 stays open.**
- **The window is centered — non-causal.** Every frame reads forward in time by half a
  window. Nothing here is a detector; the chart title says so and that line stays.
- **Offline, per D14.** `--plotlyjs` defaults to `directory`, writing one shared
  `plotly.min.js` beside the charts. **Never a CDN reference — it renders a blank page in
  this environment.**
- **Write scope:** `prompts/`, `config/`, `research/`, `results/`. Append-only nowhere.
- Charts follow 10c's untracked convention with a **committed manifest**.

---

## 2. Coverage

| Set | Kernels | Theme |
|---|---|---|
| **Every event in the 10d tape-review set** | 8 min (D5 primary) | light |
| Every event in that set | 2 and 32 min | light |
| Diag1's pre-registered subset | all three | light **and** dark |
| Contact sheet | each of the three kernels | light |

If the full three-kernel set is too large to be useful, cut the 2 and 32 min per-event
charts and keep their contact sheets — **but do not cut events from the 8-min set.** The
point is that every event in the tape review has one.

---

## 3. Bound the axes together — this is the requirement, not a detail

**Every chart in a run shares one y-range, computed across all events at that kernel.** Both
the per-event figures and every cell of the contact sheet.

`global_bounds()` does this and `main()` prints the range it computed. **Verify that line
appears in the log and that it is identical across all per-event charts in a kernel.**

Why it matters, so nobody "improves" it back: cropping each event to its own data makes
every event look alike and hides the one thing the run is for — whether one event's boundary
sits at a different absolute scale from another's. A per-event crop is a chart that answers
its own question by construction.

Two consequences to respect:

- **Run the script once per kernel with the full frames file.** Bounds are computed after
  the kernel filter and before the `--events` filter, so a subset run still inherits the
  full-set range. **Do not pre-filter the parquet to one event and run it in a loop** — that
  silently restores per-event bounds and is the exact failure this section exists to prevent.
- The time axis is **not** shared and cannot be — different events are different sessions.
  Only the interval-scale axes are bound.

---

## 4. Tasks

- [ ] **C1 — Write the two parquets** from the existing Diag1 frame pipeline. Exact columns:

  **`diag1_frames.parquet`** — one row per (event, kernel, frame, **histogram bin**):
  `event_id` str · `kernel_min` float · `frame_idx` int · `frame_ts_ns` int64 ·
  `local_median_s` float (seconds) · `n_intervals` int · `has_boundary` bool ·
  `bin_center_norm` float (decades) · `density` float

  **`diag1_ladder.parquet`** — one row per (event, kernel, frame, **candidate trough**):
  `event_id` · `kernel_min` · `frame_idx` · `frame_ts_ns` · `rank` int (**0 = argmax
  winner**, then descending void) · `boundary_norm` float · `boundary_abs_s` float
  (`local_median_s * 10**boundary_norm`) · `void` float

  **`diag1_tape.parquet`** — optional, one row per print: `event_id` · `ts_ns` int64 ·
  `price` float. Downsample freely; it is orientation only.

  **Emit thin frames too** — every frame, boundary or not. The chart washes them grey. With
  half the frames thin, that wash is the caveat and hiding it would flatter the picture.

- [ ] **C2 — Install the script** at `research/phase_10d_diag1/plot_boundary_through_time.py`.
  It has been smoke-tested end to end on synthetic data in this schema, in both themes.
  **If it throws, the parquets do not match §4 C1 — fix the parquets, not the script.**

- [ ] **C3 — Run it**, once per kernel:

  ```
  python research/phase_10d_diag1/plot_boundary_through_time.py \
      --frames results/phase_10d_diag1/artifacts/diag1_frames.parquet \
      --ladder results/phase_10d_diag1/artifacts/diag1_ladder.parquet \
      --tape   results/phase_10d_diag1/artifacts/diag1_tape.parquet \
      --out    results/phase_10d_diag1/charts/boundary_through_time \
      --kernel 8 --contact
  ```

  Then `--kernel 2` and `--kernel 32`, and the subset again with `--theme dark`.

- [ ] **C4 — Verify before posting.** Open **three** charts from different events at the same
  kernel and confirm the y-axis ticks are identical. Confirm the shared `plotly.min.js` is
  beside them and a chart renders with no network. Screenshot one and look at it — a file
  that exists is not a chart that reads.

- [ ] **C5 — Manifest and commit.** `t_charts_manifest.json`: every file, its event, kernel,
  theme, byte size, and the global y-range used. Charts untracked per 10c's convention.

---

## 5. Reporting

**Post the file count, the manifest path, the global y-range per kernel, and anything that
failed to render. That is the entire report.**

No tables. No summary statistics. No findings section. No interpretation of any chart. Diag1
already committed its numbers and they do not need restating. **If a sentence in your report
contains a percentage, delete it.**

---

## 6. Escalation

| # | Condition | Action |
|---|---|---|
| CH-R1 | Per-event charts at one kernel do not share a y-range | Hard stop — §3 was not followed |
| CH-R2 | Any chart references plotly from a CDN | Hard stop — blank page offline, D14 |
| CH-R3 | Any boundary rule, cutoff, or parameter applied or changed | Hard stop — this addendum decides nothing |
| CH-R4 | Any event in the tape-review set has no 8-min chart | Hard stop — coverage is the point |

---

## 7. Approval Gate

Post the file list and stop. **10d-R0 remains open and is what these charts are for.**
