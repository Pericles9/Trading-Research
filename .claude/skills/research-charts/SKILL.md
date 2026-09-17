# Research charts

Charts are a deliverable spec, not something you invent at the end. Every chart is specified **before any code runs**, and every finding in a report must point at the chart that supports it.

## 0. Before writing chart code

Ask two things:

1. **Does a chart module already exist for this?** If a plotting function in the repo already takes this shape of array or dataframe, call it — twice if you need two panels. Do not write a parallel renderer. A second code path is how two generations of charts end up in the tree and someone reads the wrong one.
2. **Is this chart in the contract?** If the phase prompt has a Chart Contract table, build exactly what it specifies. If it doesn't, write the contract rows first (below), then build.

## 1. Chart contract

Every chart gets five fields, written before the code:

| Field | Meaning |
|---|---|
| **Filename** | `results/phase_{x}/charts/NN_name.html` |
| **Question** | The single question this chart answers |
| **Encoding** | x, y, color, facet, marks |
| **n annotation** | Where per-bucket n appears on the chart — required, not optional |
| **Failure appearance** | What this chart looks like if the hypothesis is **wrong** |

The last field is the one that matters. If you can't write down what failure looks like, the chart can only look like success and the hypothesis isn't ready. Template:

```
| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|------|----------|----------|---------|--------------------------|
| 01 | `charts/01_spread_by_participation.html` | Does spread compress as participation rises? | x=participation decile, y=effective spread (log), violin + strip, n label per decile | Per-decile count above each violin | Violins overlap across deciles; no monotonic shift in medians |
```

Analysis-only phases are **not** exempt. A measurement phase produces no trades and is the phase where seeing the data matters most.

## 2. Standing encoding rules

These apply to every chart and never need restating per phase.

- **Plotly, standalone HTML, one chart per file.**
- **n annotated per bucket, always.**
- **Show the distribution, not just the center.** Violin, box, ECDF, or strip overlay. A bar chart of means is not an acceptable primary chart. If a bar-of-means is genuinely the clearest view, it ships *alongside* the distribution view, never instead of it.
- **Raw scatter or strip overlay behind any aggregate** wherever the point count permits. Sub-sample the overlay if it doesn't, and say so in the caption.
- **No dual y-axes. Ever.** This is the one encoding the standard forbids outright — a reader can see one line, read a slope, and believe they've seen both units. When two units need to share a time axis, use **two vertically stacked panels sharing the x-axis**, identical faceting and identical n annotations on both, one file. Record the deviation in the chart caption.
- **No smoothing or interpolation** unless the prompt asks for it.
- **Axes labeled with units.** Log scale where the data is multiplicative — in this universe it usually is.
- **Outliers shown, never clipped.** If a panel is heavy-tailed, open on a zoomed view, state the out-of-view count in the caption, and leave every point in the figure so double-click autoranges to the full data. Zoom with a range slider; don't delete points.
- **Every chart carries a caption stating:** sample, filters applied, config hash. For synthetic or validation charts, say so explicitly in the caption.

### Color

Run the categorical palette through the accessibility validator before shipping, and state in the report how many slots the phase actually uses. If the full palette fails an adjacent-pair check but the phase caps series below the failing pair, say that explicitly rather than shipping silently.

## 3. Offline / environment

The environment is offline. Never reference a CDN.

- Standalone Plotly HTML with `--plotlyjs directory` (or `include_plotlyjs='directory'`), one shared `plotly.min.js` next to the charts.
- Verify every PNG export with kaleido before claiming the chart shipped.
- Use `heatmapgl` if file size binds on dense heatmaps.

## 4. Per-event charts (any phase producing trade records)

One standalone multi-panel Plotly HTML per traded event, shared x-axis, vertical shading for regime windows:

| Panel | Content |
|---|---|
| 1 — Price | 10s candlesticks + entry markers (green ▲) + exit markers (green ▼ win, red ▼ loss) |
| 2+ — Indicators | Signal/feature values over time, thresholds, regime bands — adapts per phase |

Output paths:

```
results/phase_{x}/event_charts/{TICKER}_{DATE}.html
results/phase_{x}/event_charts/index.html
```

The index is sortable by ticker, date, session, n_trades, n_reentries, event_pf, with each row linking to its event chart. **Chart coverage may be sampled; index coverage may not** — the index always covers every event in the sample.

## 5. Regenerating

**Delete the old output charts before regenerating.** Never leave two generations in the tree. Regenerate the full set from the new path, not a patched subset.

When replacing a working renderer, run a **reference test first**: render one event through the old path and the new path over the same window and post both images side by side. They must match. Do not extend scope until that test passes.

## 6. Reporting

- Every claim in prose carries the chart filename that supports it. A finding stated without a chart reference is incomplete and gets sent back.
- Every posted table carries n per row.
- **Describe the picture; do not interpret it.** State what the chart shows — shape, location, spread, where the groups separate or don't. Cooper decides what it means. Do not assert a mechanism, a verdict, or a next step from a chart.
- Record any deviation from the contract's encoding in the chart docstring **and** the report, with the reason.