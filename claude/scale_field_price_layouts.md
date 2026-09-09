# Putting the scale field next to price — layout options

**Date:** 2026-09-07 · **Type:** design note + mockup. Records no decision, applies no gate, runs on no
real data. Companion to `claude/scale_field_reading_grammar.md`, which derives what the shapes mean.
**Artifact:** `scale_field_price_mockup.html` — synthetic tape, four injected features, all three field
panels and the scale slider working. Nothing in it is from your cohort.

---

## 0. The framing problem, and it is not a plotting problem

The field lives in `(t, log s)`. Price lives in `(t, price)`. Stacking them on a shared x-axis is the
obvious move and it is what the panels already do — but it does not actually connect them, because
**a reader has no way to know which row of the field corresponds to the wiggle they are looking at on
the price line.** Every idea below is a way of closing that specific gap.

There is also a substantive problem that no layout fixes, and it should be settled first:

> **The field as built is direction-blind.** It runs on trade *arrivals*. A 200-print sweep that lifts
> every offer and a 200-print two-sided churn at the same rate produce **identical fields**. For a
> momentum strategy only the first is the object of interest. Pairing a direction-blind field with a
> price chart will show you coincidences without showing you why any of them happened.

That is §3.1 below, and I think it is worth more than the rest of this document combined.

---

## 1. Fixes to the panel as it stands — hours, no new statistic

**1.1 The colour scale is almost certainly wrong, and it is derivable that it is.** `F` has a hard floor
at −1 and no ceiling; deep voids reach +8 routinely. A symmetric diverging map on raw `F` therefore
spends its whole dynamic range on voids and renders **every burst pale**. Fix: colour on
`F/(1+|F|)`, which maps `[−1, ∞)` onto `[−0.5, 1)`, and label the colourbar ticks with the original `F`
values. The mockup does this; without it the trumpets are invisible.

**1.2 Pane 4 is redundant with the `s_min` line.** `log s_min = log 2.26 − log λ̂`, and log inter-trade
interval is `−log λ̂` plus noise. The two panes are the same curve. Keep one — I would keep the ITT
scatter, because it also shows the dispersion the line cannot — and stop drawing four panes where
three carry information.

**1.3 Masked cells need their own colour, not white.** White reads as zero on a diverging map, so the
sub-`s_min` region currently reads as "nothing happening" when it means "no estimate exists." A flat
neutral grey with a note in the legend.

**1.4 Draw the noise floor as a contour.** `±2 × 0.87/√n_eff(t,s)`. Everything inside it is
indistinguishable from a null tape. This is the single highest-value overlay available and it costs one
line.

---

## 2. The interaction that does the most work — pair the field with the family of smooths

**This is the SiZer construction and it is the reason the method exists.** Chaudhuri & Marron's whole
point was that the 2-D map and the family of smooths are two views of one object and must be read
together.

**Hovering (or a slider over) a row of the field sets the Gaussian bandwidth used to smooth the price
line above it.** Move to `s = 5 s` and the price line resolves individual pushes; move to `s = 200 s`
and it resolves the session's shape. **The reader learns what "scale" means on the price axis by moving
the control**, which is a thing no static caption can teach.

Implemented in the mockup as a slider (a discrete slider is more reproducible than hover for a committed
artifact, and it can be screenshotted at a stated scale).

The same control drives a horizontal read line across every field panel, so "which row am I looking at"
is never ambiguous. **A horizontal cut is also a cleaner object than the boundary-following cut the
current mark uses** — it asks one question everywhere, where `s ∝ 1/λ̂` asks a different question every
second.

---

## 3. The three additions worth building, in order

### 3.1 An order-flow imbalance scale field — the one that matters

Same machinery, different carrier. Sign the prints (tick rule at minimum), split the intensity, and plot

```
I(t, s) = (λ̂_buy − λ̂_sell) / (λ̂_buy + λ̂_sell)     ∈ [−1, 1]
```

at every `(t, log s)`. **This is "which side is pressing, measured at every horizon at once."**

Why it is better suited to this programme than the curvature field:

- **It is signed**, so it maps onto price direction without an argument.
- **Its zero is arithmetic**, not a Poisson reference — the lesson from this arc's two failures applies
  and it passes: the reference is "equal counts", which does not depend on the process being anything.
- **It is not a curvature statistic**, so it does not inherit the blindness in the reading grammar:
  it sees a sustained one-sided plateau, which the curvature field reads as zero.
- **Its scale axis has a direct trading meaning.** Imbalance strong at `s = 5 s` and gone by `s = 60 s`
  is a fill-and-fade. Imbalance persisting up to `s = 300 s` is accumulation. **The scale at which the
  imbalance column dies is a holding-period estimate**, which is the number the momentum system needs
  and the curvature field has never produced.

In the mockup this is what separates feature **B** — a 40 s churn, a loud trumpet on the rate panel and
dead grey on the imbalance panel — from feature **A**, a 5 s sweep that lights up both. **B is exactly
the false positive the current mark cannot avoid.**

**The honest cost:** it needs trade signing, and the tick rule on fragmented micro-cap tape is not free
of error. That error is worth measuring before the field is built on top of it, not after.

### 3.2 A log-price curvature field — the same grammar applied to price

`s²·(ln p)″` at every `(t, log s)`. Identical operator, identical reading grammar: **orange where price
is rounding over at that scale, blue where it is basing, trumpets whose apex height is the duration of
the swing, merges that read the separation between swings.** It also inherits the causality theorem, so
the same "nothing appears from below" correctness check applies.

Two things it gives you that a price line does not:

- **The scale at which price stops being a random walk.** In the mockup the bottom of that panel is a
  dense alternating carpet — that is what a random walk looks like under this operator, and it is a
  useful calibration image to have in front of you. **The height at which the carpet gives way to
  coherent structure is the shortest horizon at which the price path has any shape at all.** For a
  system with a ~10 s holding period that is a directly relevant number, and I am not aware of it having
  been measured here.
- **Alignment against the trade field, row by row.** Both panels are in the same coordinates, so "does
  the activity structure at 20 s line up with the price structure at 20 s" becomes a question you can
  answer by looking, per scale, rather than at one arbitrary horizon.

Display note: the raw statistic's noise level falls as `s^{-1/2}` under a random walk, so per-row
normalisation manufactures the carpet at every scale equally. Normalise, but then show `±1σ` as
near-neutral so real structure is what stands out.

### 3.3 The lead-lag surface — the object all of this is actually pointing at

Once 3.1 and 3.2 exist in matching coordinates, the question stops being "do they look aligned" and
becomes measurable without any forward-return machinery:

**Cross-correlate the imbalance field and the price-curvature field along `t`, one row at a time. Plot
the lag of peak correlation against scale.** One curve. It answers: *at which timescale, if any, does
order-flow structure lead price structure, and by how long?*

- A lag that is positive and roughly constant in seconds → a fixed reaction delay.
- A lag proportional to `s` → the two fields are the same object seen at different resolutions, and
  there is nothing to trade.
- A lag that is zero everywhere → contemporaneous, no edge.

**This is the first construction in the arc that produces a horizon estimate rather than assuming one**,
and it uses no forward returns, so it stays outside the heavy standard. The moment it is turned into a
signal, it is inside it.

---

## 4. Two readouts drawn on the price axis itself

**4.1 The measured duration, as a band.** For each feature, find the scale where the field crosses −0.5
over its centre; that scale is the burst's width. Draw `±σ` as a shaded band on the price panel. The
reader immediately sees *which piece of the price move the feature actually spans* — which is the
question the panels were built to answer and currently answer only by eye.

**A caveat the mockup itself produced, and it should be recorded:** the readout is biased high by
background. Injected `σ = 5 s` read back as 6.5 s; injected `σ = 40 s` read back as 56 s. That is the
`b/A` drag term in the closed form, and it means the readout is an upper bound, not an estimate, unless
the feature clearly dominates its local background. Two of the four injected features never reached −0.5
at all.

**4.2 Cone outlines rather than block shading.** The current shading is a rectangle from a boolean. The
feature's actual footprint is a trumpet — `±√(σ² + s²)` — so its edges are curved and scale-dependent.
Drawing the outline instead of a rectangle makes the read-scale dependence visible rather than hidden
inside a debounce parameter.

---

## 5. Things I would not do

- **No dual y-axis.** The temptation is to put "characteristic scale" on a right-hand axis over price.
  Two measures on two scales in one frame is the most reliable way to manufacture a relationship that
  is not there. Separate panel, shared x.
- **No colouring the field by forward return.** It is the obvious "make it about price" move and it is
  exactly the line the standard draws — the moment forward returns enter, the full pre-registered
  standard applies. Do it deliberately inside that standard or not at all; do not do it as a chart.
- **No rainbow, no viridis on a signed field.** The statistic is signed with a meaningful zero, so it
  needs a two-hue diverging map with a neutral midpoint. A sequential map hides the sign, which is the
  only thing the mark currently uses.
- **Do not stack more panels.** Four is already at the limit of what a person tracks across a shared
  axis. If 3.1 and 3.2 go in, something comes out — pane 4 is the candidate (§1.2).

---

## 6. What the mockup is and is not

It is four synthetic features on a synthetic tape, built so the layout's claims are checkable:
**A** 5 s bought sweep · **B** 40 s two-sided churn · **C** 300 s sold accumulation · **D** a 40 s
pressure episode with no rate signature at all.

**B is loud on the rate panel and silent on the imbalance panel. D is invisible on the rate panel and
obvious on the imbalance panel.** Those two facts are the argument for §3.1, and they are the reason I
would build the imbalance field before doing anything else on this chart.

It is **not** evidence about your tape, it contains no real prints, and the specific numbers in it are
properties of the synthetic construction.
