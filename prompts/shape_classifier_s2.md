# Shape classifier — S2: can the six types be predicted, at the crossing and as the path unfolds?

**Date:** 2026-09-28 · **Type:** exploratory modelling build on the tick archive. **Not a phase.**
**Branch:** `explore/shape-classifier-s2`, cut from `explore/shape-atlas-s1` at `b526ab6`.
**Outputs:** `results/shape_classifier/s2/` (artifacts, charts in per-task subfolders, REPORT.md plus
its copy in `results/reports/`). Config: `config/shape_classifier_s2.json`, committed before the run.
**Ends at a stop (T8)** for Cooper's read.

**Why a clean test here, when S1 had none:** S1 described. S2 **fits models**, and a model's only value
is how it does on data it has never seen. Under D38's own scope, fitting brings back the ticker-blocked,
time-ordered test. Everything else stays exploratory.

**What came before, stated so it is not over-read:** Claude ran a rough version on S1's committed
per-event tables. That run had no tick access, no post-crossing features, one split, untuned models and
no timing audit. It found one look-ahead leak: the A12 cross-session flag drove the runaway predictions.
Without that flag, the at-crossing ranking was weak. **That is a prompt for this brief, not a result it
has to reproduce.**

---

## 1. What is being predicted (the output)

**The label** is each event's S1 theory type at N = 100 (runaway, burst, slow climb, exhausted, fade,
chop), exactly as S1 assigned it. The label is hindsight by definition: it describes the whole path
after τ. That is fine, because it is the thing being predicted.

**The model's output**, for each event at each decision time: **six probabilities, one per type, summing
to 1.** Nothing is merged. Each type is scored on its own.

Secondary labels (reported, never used for fitting): the same types at N = 50 and N = 200, to show how
much the rung moves the score.

## 2. When the prediction is made (decision times)

Each decision time has its own set of models. There is no single model across times.

| decision time | definition |
|---|---|
| **τ** | the crossing print |
| **τ + 1, 2, 5, 10, 20 minutes** | wall clock |
| **volume checkpoints** | when shares traded since τ first reach **0.25×, 0.5×, 1× and 2×** the shares traded from the segment start to τ |

An event that does not reach a checkpoint before 20:00 is carried as `not_reached` at that checkpoint.
That is information in itself, never dropped. **No checkpoint may be defined as a share of the rest of
the day's volume**, because that total is not known live.

## 3. What goes in (the inputs), all strictly at or before the decision time

**Group A — known at τ** (from the b2 and S1 artifacts, or recomputed):
- **Timing:** time of day, session segment, auction-minute crossing, τ is the day's first print.
- **Run-up:** `gap_share`, `u_launch`, run-up height, run-up drawdown, pushes, run-up minutes and volume.
- **Attention:** turnover, `accel_k` rungs 0–4 (null where invalid, with a validity indicator),
  absolute trade rate and dollar flow, `a2_ignition`, `live_n` at each liveness, `flow_share` over the
  pre-τ window.
- **Catalyst and fundamentals:** filing within 24 h, last form, dilution flag, reverse split in 365 days,
  short interest share, shares outstanding (as filed).
- **Tape:** price tier, `tau_close_sensitive`.

**Group B — the path since τ, at each checkpoint after τ.** Computed from ticks between τ and the
checkpoint only:
- return since τ;
- highest return since τ and the drawdown from it;
- where in the elapsed time the high came;
- trade rate and dollar flow since τ, and each as a ratio to the event's own pre-τ rate;
- acceleration since τ (second half of elapsed trades vs first half);
- realised volatility since τ;
- halts or long gaps so far.

Any move expressed in noise units uses **pre-τ volatility** (from the run-up) as the scale. It never uses
`σ_path`, because that is built from the whole post-τ path.

**Group C — atlas matching, at each checkpoint after τ.** The path so far, resampled on the elapsed
wall-clock grid, compared with each type's typical path over the same elapsed stretch. The typical paths
are built **from the training years only**. Output: distance to each type's typical path, six numbers.

**Excluded, with the reason recorded in config:**
- `flag_cross_session_extreme` (A12) — pending the T0 audit below;
- `competition_excess` — it uses other names' activity after τ;
- every S1 or b2 post-τ vector component;
- `momentum_pct` (D4).

## 4. The models

| id | model | what it is | runs at |
|---|---|---|---|
| **M0** | base rates | each type's share in the training years. **The floor.** | all |
| **M1** | simple cell rule | type shares in training within cells of turnover band × ignition × segment. The "no machine learning" rival | τ |
| **M2** | multinomial logistic regression | one weight per input per type. Inputs standardised, missing values filled with the training median plus a missing-indicator column | all |
| **M3** | gradient-boosted trees | sklearn `HistGradientBoostingClassifier` (handles missing values natively) | all |
| **M4** | atlas analogs | the k nearest training events by Group C distance; output = type shares among them, k ∈ {25, 50, 100} | checkpoints after τ |

**Tuning is small and declared.**
- **M2:** regularisation strength C ∈ {0.1, 1, 10}.
- **M3:** learning rate {0.03, 0.1} × leaf count {15, 31} × iterations {200, 500}.
- **M4:** the k ladder above.
- Class weights: none, and "balanced" (inverse frequency). Both are reported.
- Each setting is chosen by validation log loss inside the training window, **never on a test fold**.
- The grid is declared in config and not extended after results are seen.

**Deferred, not built here:** a two-stage model (engage or not, then which type); predicting the
components (rise, peak timing, fall) and applying the type rules; sequential updating of the
at-crossing probabilities. Each waits until S2 shows whether there is signal to combine.

## 5. How it is tested

**Rolling-origin folds, time-ordered, ticker-blocked:**

| fold | train | test |
|---|---|---|
| 1 | 2020–2021 | 2022 |
| 2 | 2020–2022 | 2023 |
| 3 | 2020–2023 | 2024 |

- **Primary read:** test events whose ticker never appears in that fold's training years.
- **Secondary read:** all test events, reported beside the primary.
- The 50 dev events and 6 sidecar events are excluded from every fold.

**Scores, per type, per model, per decision time, per fold:**
- **AUC** (one type against the rest), with a 95% interval from bootstrapping **tickers**, not events.
- **Top-10% lift:** how much more often the type appears in the model's top decile for it than in the
  whole test set.
- **Calibration:** predicted probability against observed frequency, in bins with n shown.
- **Multiclass log loss** against M0 on the same test set.
- **Confusion table** at the most-probable type, with counts.

**Money relevance, without designing a strategy.** For events in each type's top predicted decile at
each decision time: the forward return **from that decision time** to +10, +30 and +60 minutes and to
20:00, priced from actual prints (the next print after the decision time as entry), net of 70.98 bp
flat and 2.512 ¢ per share. Shown against the same figure for all test events at that decision time.
This says whether a better-than-base prediction points at events that move. It does not say how to
trade them.

**The key chart:** AUC by type against decision time, one line per model. **It shows how quickly each
type becomes predictable as the path unfolds**, and whether anything is predictable at τ itself.

## 6. Controls

| control | construction | must show |
|---|---|---|
| **negative** | labels shuffled within each training fold, same pipeline | AUC within 0.45–0.55 for every type |
| **positive** | a deliberately leaky extra input (`terminal_log`, the path's own end) added in a separate run | near-perfect AUC. This proves the pipeline can see a leak when one exists |
| **baseline** | M1 against M0 | reported, so M2–M4 are judged against a simple rule, not only base rates |

## 7. Tasks

- **T0 — timing audit.**
  - For every input, record the latest data timestamp it uses, and assert it is at or before the
    decision time, per event. A violation is a HARD STOP.
  - **Document exactly how `flag_cross_session_extreme` is built.** If it uses the event day's close, say
    so, and list every earlier artifact or brief that used it as an input rather than a facet.
- **T1** — Group A table, one row per event.
- **T2** — Group B and C at every checkpoint, including `not_reached`. Atlas typical paths built per
  fold from that fold's training years.
- **T3** — the folds and ticker-blocked test sets. Counts per fold, type and checkpoint.
- **T4** — fit and score M0–M4, with the tuning inside training windows only.
- **T5** — the §6 controls.
- **T6** — money relevance (§5).
- **T7** — importance: permutation importance per type on each test fold for M3. **Any single input
  carrying most of a type's AUC is a LOG row, plus a manual timing re-check of that input.** That is
  exactly how the A12 leak looked.
- **T8** — REPORT.md, charts, stop.

## 8. Charts

Dark theme, Plotly inlined, n on every panel. Where there are many cases, use one file with selectors.

- `auc_by_time.html` — AUC with intervals, type × decision time, one line per model (primary read,
  secondary toggle).
- `lift_by_time.html`
- `calibration.html` — per type, model and decision time.
- `confusion.html`
- `forward_returns.html` — top-decile events against all events, per type, decision time and horizon,
  both cost units.
- `importance.html`
- `controls.html`

## 9. Escalation

| row | criterion | tier |
|---|---|---|
| 1 | any input uses data after its decision time (T0) | HARD STOP |
| 2 | negative control AUC outside 0.45–0.55 for any type | HARD STOP |
| 3 | positive control AUC below 0.95 for any type | HARD STOP |
| 4 | a single input carries more than half of a type's permutation importance | LOG, plus manual timing check |
| 5 | any fold's primary test set has fewer than 20 events of a type | LOG. That type is shown and not read in that fold |
| 6 | sklearn, or `HistGradientBoostingClassifier`, unavailable offline | HARD STOP. Report what is installed |

## 10. Report

Describes the pictures, no interpretation, all numbers read from artifacts by code. It opens with the
timing audit and the A12 finding, then the controls, then results per type in the order runaway, burst,
slow climb, exhausted, fade, chop. Commit, push, post the AUC-by-time table for the primary read. Stop.

## 11. Constraints

D4 tick-derived · D5 long-only (forward returns reported long-side only) · D14 offline, no installs ·
D19 both units · flag and carry · named paths staged · nothing in `scanner-epg-momentum` or
`hawkes-ofi-impact` is touched.
