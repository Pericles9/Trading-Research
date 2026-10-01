# Chop regime C1 — Amendment 3: the chart wall

**Date:** 2026-10-01 · **Amends:** `prompts/chop_regime_c1.md` as amended by Amendments 1–2, after the stop at
`89120e1` on `explore/chop-regime-c1`.
**Effect:** adds a second instrument, **`chart_wall.html`**: a grid of 1-minute candlestick charts with volume,
with the filter drawn on each chart as red shading, and one set of controls that drives every chart at once.
The existing suite (`chop_suite.html`, config hash `cdbc5343fba6`, data hash `237f7165c992`) is **kept
unchanged.** The two files share one config format, so a setting made in either can be loaded into the other.
**Ends at a stop** with the wall in Cooper's hands.

---

## A3.0 Why

The suite shows what the filter does in aggregate and in galleries of single moments. **It does not show the
filter laid over the tape**, minute by minute, across a whole day, on many names at once. That is the most
direct way to see whether the filter cuts chop, spares pauses, and leaves the real legs alone (Cooper,
2026-10-01). The wall is where thresholds are set by eye. The suite stays as the place to check the
aggregate, the noise bands and the outcome panels.

**Chart style.** Cooper asked for 1-minute candles with volume histograms for this view. The standing rule
(trade prints as dots on per-event price panels) still applies to the suite's gallery strips. The wall uses
candles.

## A3.1 What gets built (pipeline)

**Events.** A seeded sample from the development slice, stratified by year × τ's segment. Any
development-slice event is eligible, not only the suite's 3,319. Quarantined events are excluded. **The
target is 600 events**, cut to whatever fits the size budget in A3.5 and never below 300. The count is
stated in the header.

**Candles, from ticks (D4).** One-minute OHLC and share volume, built from the same trade table and the same
condition-code handling as every other tick build in the programme. The spine and `event_minute_bars_v2` are
not used. Candles run from the first event-day print to the last print at or before 20:00. A minute with no
trade is drawn as no candle, not a flat one, and its volume bar is 0.

**The filter table, on a full 1-minute grid.** For these events only, the T1–T4 measure code is run **at every
minute from τ to the last minute before 20:00.** This replaces the 5-minute grid after τ + 60 for these
events, so every candle after τ has its own filter state. It is the same code, with the same causality and
segment assertions, and only the condition columns are embedded. The suite's table is not touched.

- Before τ there are no moments. Those candles are drawn unshaded, and a light grey band says "before τ —
  no filter".
- Minutes in an auction minute keep their `unavailable` label, drawn as a grey band.

**Per event, also embedded:** τ (time and price); the segment boundaries; halts (b2's ≥ 300 s regular-hours
rule plus labels); `price_basis` where it fell back to VWAP; S1 type, `g1`, `g2` and `g3` flags per minute.
**These are viewing labels only.** They pick which events to show and appear in captions. They are never
conditions. The build asserts it.

## A3.2 Controls — one panel, pinned at the top, drives every chart

- **The filter**, exactly as the suite's §7b:
  - per-segment values with "copy to the other segments";
  - every chop condition (presence and cost, relative, `er`), each on or off, with a slider in absolute units
    and a numeric box;
  - the combination rule (any, or at least m);
  - the pause override and its three conditions;
  - the `unavailable` choices;
  - the `cost_noise` horizon.
- **Sliders redraw the shading on every visible chart at once.** Only the shading changes; candles are not
  re-rendered. Target: under one second for a full page.
- **Load config / export config.** Same JSON as the suite. Loading the suite's export reproduces its setting
  exactly, and the reverse holds too. The build asserts this with a round-trip test.
- **Defaults:** every condition off, so nothing is shaded on load.

**Which events are shown (viewing only):**

- **Set:** all, or by S1 type (runaway, burst, slow climb, exhausted, fade, chop), or events containing any
  G1, G2 or G3 minute. Facets: year, τ's segment, price tier at τ.
- **Order:** seeded random (default), date, or time of τ. Never by outcome size.
- **Page size:** 6, 12 (default) or 24 charts. Columns: 1, 2 (default) or 3. Next and previous page.
- **X range:** τ − 30 min → 20:00 (default), full day, or τ ± 2 h. One setting applies to every chart.
- **Click a chart** to open it full width, with zoom and pan. All controls still apply.

## A3.3 Each chart

**Top pane: 1-minute candles.**

- **Red shading, full pane height, over every minute the filter rejects.** Opacity 0.25, so the candles stay
  readable.
- **Rescued minutes**, those the pause override kept, carry a thin amber strip along the top edge. That makes
  the override's work visible on its own.
- Vertical lines at τ and at each segment boundary (09:30, 16:00). Halts are a hatched band.
- A dashed horizontal line at the prior close × 1.30, the crossing level.

**Bottom pane: volume histogram**, one bar per minute, coloured by candle direction. The red shading
continues down through this pane, so the filter can be read against activity directly. Linear or log
toggle, applied to every chart.

**Optional third pane, off by default: the measure behind the shading.** Pick one active condition. Its value
per minute is drawn as a line, with its threshold for each segment as a horizontal step and the `er` null
band where `er` is chosen. One selector sets it for every chart. This shows *why* a minute is red.

**Hover, any minute after τ:** time; segment; filtered, kept or rescued; which conditions fired; the value of
every active condition's measure; minutes since τ.

**Caption:** ticker, date, τ time and segment, price tier, S1 type, and, under the current setting, the
share of the event's post-τ minutes that are filtered. Plus three counts: G1 minutes filtered (x of y), G2
minutes filtered (x of y), and **pause minutes filtered (x of y), in bold.**

## A3.4 Pinned counts — same rule as the suite

Above the grid, for **all embedded wall events**, not just the visible page, per segment first and pooled
last:

- minutes filtered and kept;
- G1 filtered, x of y;
- G2 filtered, x of y;
- **G3 pauses filtered, x of y — the largest figure.**

The readability line at 20 applies. These are counts on the wall's own sample. The suite's counts, on its
sample, stay authoritative for anything committed.

## A3.5 Size and performance

- **Budget ≤ 60 MB** for `chart_wall.html`. Candles take 5 numbers per minute and the filter table only its
  condition columns, both as typed arrays. If 600 events do not fit, reduce the event count, never the
  minute resolution.
- Plotly inlined (D14), dark theme. The shading is a single trace per chart, updated in place, not one shape
  per run of minutes.
- **Page test** (as in the suite), run under Node on the real data:
  - no errors;
  - nothing shaded with every condition off;
  - the config round trip with the suite reproduces the same filter state minute for minute on the events
    both files share;
  - no outcome printed.

## A3.6 Must not do — the suite's §7d applies in full

- No optimiser and no suggested setting.
- No percentile anywhere.
- Development slice only (asserted).
- No A12.
- No hindsight column as a condition. S1 type and the G flags are viewing labels only (asserted).
- No measure recomputed in the browser.
- No ordering of events by outcome.

## A3.7 Tasks

- **W1** — event sample, candles, halts and segment marks.
- **W2** — the 1-minute filter table for the wall events, using the T1–T4 code unchanged, with its
  assertions.
- **W3** — `chart_wall.html` with its build assertions:
  - development slice only;
  - no A12;
  - hindsight and type columns absent from the condition set;
  - the config round trip with the suite.
- **W4** — page test. REPORT.md: add a short wall section with the event count, file size and test results,
  and **no outcome**. Commit, push.

**Then stop.** Post: the event count, file size, page-test result, and the round-trip result.

## A3.8 Escalation

| row | criterion | tier |
|---|---|---|
| W-a | causality or segment assertion fires in W2 | HARD STOP |
| W-b | a non-development row, A12, or a hindsight or type column reaches the condition set | HARD STOP |
| W-c | the config round trip with the suite disagrees on any minute | HARD STOP. The two instruments would show different filters for the same setting |
| W-d | fewer than 300 events fit the size budget | LOG. Post the size per event; do not lower the minute resolution |
| W-e | slider redraw over 1 s for a full page of 12 | LOG, with the measured time |
