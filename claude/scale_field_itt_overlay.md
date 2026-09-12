# Overlaying the ITT chart on the field — amendment to the layout note

**Date:** 2026-09-07 · **Type:** correction + design note. Records no decision, runs on no real data.
**Amends:** `claude/scale_field_price_layouts.md` §1.2, which said pane 4 (log₁₀ Δt per print) is
redundant with the `s_min` line and one of them should be dropped.
**Artifact:** `scale_field_itt_overlay.html` — synthetic tape, three panels, the construction working.

---

## 1. The correction

§1.2 was wrong, and wrong in a way worth naming rather than quietly fixing.

`log s_min = log 2.26 − log λ̂` and the ITT scatter's **centre line** is `−log λ̂` plus a constant. Those
are the same curve, and that much of §1.2 holds. But the scatter is not its centre line. **Its width and
its shape are not redundant with anything on the chart, and they carry precisely the one thing the rate
field is structurally blind to.**

The reading grammar already said this and I did not connect it: the rate channel sees only `λ̂`, so two
tapes with identical `λ̂(t)` — one Poisson, one violently clumped inside — produce **identical fields**.
The interval distribution is the only place that difference lives. Dropping the ITT pane would have
thrown away the one measurement that separates a rate excursion from clustering.

**Keep both panes. Better: put them on one axis.**

---

## 2. The construction — they share a y-axis, and nothing currently exploits that

`log₁₀ Δt` and `log₁₀ s` are **both log₁₀ of a duration in seconds**. They are the same axis. The panels
currently draw them as two separate panes with two separate vertical scales, which hides every relation
below.

Overlay the interval cloud directly on the field heatmap, on the shared axis. Not as a point scatter —
that would obscure the field — but as a **rolling quantile ribbon**: the 10th, 50th and 90th percentile
of `log₁₀ Δt` in a moving window, drawn as a band plus a median line.

Three readouts appear immediately, all parameter-free.

### 2.1 Ribbon width is a clustering measure with a universal constant

Under a locally homogeneous Poisson process, `Δt ~ Exp(λ)`, so `log₁₀ Δt` has a **fixed shape that moves
only in location**. Its 10–90 spread is therefore the same at every rate:

```
q90 − q10  =  log₁₀( ln(1/0.10) / ln(1/0.90) )  =  1.3396 decades      — at any λ, exactly
IQR        =  log₁₀( ln(1/0.25) / ln(1/0.75) )  =  0.6829 decades
sd         =  0.5570 decades                                          — the constant already on record
```

**Wider than 1.340 means over-dispersed: clumped. Narrower means more regular than Poisson.** No fit, no
null simulation, no bandwidth choice. A second panel plotting `q90 − q10` against a horizontal line at
1.340 is a clustering detector that costs one rolling quantile.

This is the interval channel delivered as a picture, without building the covariance field
`Cov_w(z², log Δt)` that the channel would otherwise require.

### 2.2 The gap between `s_min` and the ITT median is itself the clustering statistic

`s_min` comes from a **time-weighted** rate estimate. The ITT median is an **event-weighted** quantity.
Under Poisson they are locked together:

```
log₁₀ s_min − median(log₁₀ Δt)  =  log₁₀(2.26) − log₁₀(ln 2)  =  0.5133 decades
```

So draw the observed `s_min` line and, beside it, `median + 0.5133` — **where `s_min` would sit if the
tape were locally Poisson.** The vertical gap between the two lines *is* the clustering, in decades,
read off the chart at every instant.

On the synthetic tape this checks out exactly: 0.515 measured against 0.513 predicted in the quiet
stretches, opening to **1.90 decades** across the clumping episode.

**A number from this programme is worth putting beside that.** `scale_space_lessons.md` recorded the real
tape sitting **1.29 decades** off the Poisson identity at the read scale. That is the same family of
quantity and roughly the same magnitude as the excess I had to *construct* as a special episode here.
Taken at face value it means **the tape's ordinary baseline state resembles what I built as the hard
case** — and that the two-line gap would be wide over most of the session, not just at events. I am not
claiming that from a synthetic chart; I am saying it is the first thing this overlay would show, and it
is cheap to look at.

### 2.3 Where the ITT cloud sits relative to the rendered band is the resolution-floor result, drawn

On the mockup the interval cloud sits largely **below** the field's scale band. That is not a rendering
problem — it is the resolution floor as a picture: the intervals live at durations the field cannot
measure. A per-event version of that image says at a glance whether the event supports the band being
drawn, which is currently a number in a caption.

---

## 3. The third panel — colour each print by the field value at its own read scale

Plot the ITT scatter, and colour every print by `F` at `(tᵢ, s_read)`, greying the prints where `|F|`
does not clear `2·0.87/√n_eff`.

**If the mark tracks clustering, the coloured prints concentrate at the BOTTOM of the interval cloud —
the short intervals. If they are spread evenly through the cloud's vertical extent, the field is not
tracking interval structure at all**, whatever else it is doing.

That is the "is the field detecting bursts or picking up noise" question answered in one picture, from
committed artifacts, with no null model and no injection grid. It does not replace injection–recovery;
it is the thing to look at before deciding whether injection–recovery is worth building.

---

## 4. What the mockup shows, and one honest correction to my own framing

Three injected features: **A** a real 5 s rate hump · **V** a genuine void · **E** clumping at
**constant mean rate** (measured 6.46/s inside against 6.16/s ambient — matched).

- A and V draw clean trumpets. E does not.
- The ribbon width across E: **2.82 decades** against 1.30 in the quiet stretches and 1.340 under Poisson.
- The `s_min`-to-median gap across E: **1.90 decades** against 0.515 quiet.

**The correction: "the field is blind to clumping" is too strong, and the mockup shows why.** Across E
the field is not silent — it fires as dense **speckle**, incoherent in scale, because clumping does
create curvature at scales comparable to the clumps. Median `|F|` at `s = 8 s` ran 0.225 across E
against 0.135 quiet.

That is arguably worse than blindness for the current build: **a debounced boolean would convert that
speckle into a large number of short marks**, and a burst count would go up across an episode where the
mean rate never changed. Two-line summary of the difference: **a rate hump makes a trumpet, clumping
makes speckle**, and a sign test cannot tell them apart while a person looking at the two panels can
instantly.

Also worth recording from the same render: applying the `±2·0.87/√n_eff` significance mask kept
**29.3%** of the cells that `n_eff ≥ 8` admits. Roughly seven cells in ten inside the current
admissibility boundary are indistinguishable from a null tape.

---

## 5. Revised recommendation for the panel

| pane | content | change |
|---|---|---|
| 1 | price | unchanged |
| 2 | field + ITT quantile ribbon + `s_min` + the Poisson-predicted `s_min`, **one shared log-duration axis** | merges old panes 2 and 4 |
| 3 | `q90 − q10` against the 1.340 line | new, cheap, and it is a clustering detector |
| 4 | ITT scatter coloured by field significance | replaces the plain scatter |

Same pane count. §1.2 of the layout note is superseded: **nothing is dropped, two panes are merged, and
the freed pane goes to the ribbon width.**

Everything here is synthetic. None of it is evidence about the cohort.
