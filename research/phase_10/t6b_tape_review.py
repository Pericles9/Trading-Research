"""
Phase 10 T6b -- chart 07, the per-event tape review set. This is the gate.

Per selected event, two stacked panels on a shared time axis:

  TOP     individual trade prints, price against time, marker size by share
          count, detected burst intervals shaded -- both arms, visually
          distinguishable (Arm B as full-height shading because it is the coarse
          arm; Arm A as a dense ribbon lane at the top of the panel, because at
          up to ~1,900 bursts per session full-height shading would obliterate
          the price series it is supposed to be checked against).

  BOTTOM  inter-trade time, log scale, same x-axis, with each arm's rate measure
          and its on/off thresholds drawn. Everything on this panel is in
          SECONDS on ONE axis -- Arm B's prints/min rate and its on/off
          multipliers are converted to their equivalent inter-trade time
          (60 / rate), and Arm A's two state rates appear as 1/alpha_0 and
          1/alpha_1. A second y-scale is never used.

Inter-trade time here is a DIAGNOSTIC DISPLAY AXIS and Arm A likelihood input
only (escalation row 8). No inter-trade interval distribution is produced as a
finding, no noise floor is characterised, no burst-vs-quiet interval regime is
defined -- that is Phase 13's deliverable.

Selection is bounded by config.charts.chart_07: the full dev v4 primary cohort,
the sidecar and row-cap census (labeled), plus a stratified draw over the
activity extension by Arm A burst count -- top N, bottom N, seeded random
middle. Escalation row 6 fires before writing if the selection exceeds the cap.
The sortable index covers the FULL cohort, sampled charts or not.

Usage: python research/phase_10/t6b_tape_review.py
"""
from __future__ import annotations

import html
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chartlib as C  # noqa: E402
from arm_b import build_baseline  # noqa: E402
from common import (  # noqa: E402
    config_hash, load_cohort, load_config, ns_to_et, read_event_trades, rel,
    session_window, write_json,
)

KEY = ["ticker", "event_date_canonical", "momentum_pct"]
FLANK = (-3, -2, -1)
SUBDIR = "07_tape_review"


def select_events(cohort, a_events, cfg) -> pd.DataFrame:
    """Bounded selection per config.charts.chart_07.selection_rule."""
    c7 = cfg["charts"]["chart_07"]
    counts = a_events.set_index(KEY)["n_bursts_ref"] if "n_bursts_ref" in a_events else None
    co = cohort.copy()
    co["arm_a_burst_count"] = counts.reindex(pd.MultiIndex.from_frame(co[KEY])).to_numpy() \
        if counts is not None else np.nan

    always = co[co["cohort_group"].isin(["dev_v4_primary", "dev_v4_sidecar", "row_cap_census"])]
    ext = co[co["cohort_group"] == "activity_extension"].sort_values(
        ["arm_a_burst_count"] + KEY, kind="mergesort")
    n_edge = c7["burst_count_edge_n"]
    low, high = ext.head(n_edge), ext.tail(n_edge)
    mid_pool = ext.iloc[n_edge:len(ext) - n_edge]
    rng = np.random.default_rng(c7["middle_seed"])
    take = min(c7["middle_n"], len(mid_pool))
    mid = mid_pool.iloc[np.sort(rng.choice(len(mid_pool), size=take, replace=False))]

    sel = pd.concat([always, low, mid, high], ignore_index=True).drop_duplicates(subset=KEY)
    sel["chart_selection_reason"] = np.where(
        sel["cohort_group"] != "activity_extension", "carried population — all included",
        np.where(sel.set_index(KEY).index.isin(low.set_index(KEY).index), "extension — lowest Arm A burst count",
                 np.where(sel.set_index(KEY).index.isin(high.set_index(KEY).index),
                          "extension — highest Arm A burst count", "extension — seeded random middle")))
    return sel


def build_chart(cfg, row, bursts_a, bursts_b, chash, out_dir) -> dict:
    c7 = cfg["charts"]["chart_07"]
    b = cfg["arm_b"]
    cap_pts, seed = c7["max_scatter_points"], c7["over_cap_seed"]

    data = read_event_trades(cfg, row.ticker, row.event_date_canonical, row.momentum_pct,
                             offsets=(*FLANK, 0))
    t0 = data.get(0)
    win = session_window(row.event_date_canonical, 0)
    if t0 is None or len(t0) == 0:
        return {}
    ts = t0["sip_timestamp"].to_numpy()
    px = t0["price"].to_numpy(dtype=float)
    sz = t0["size"].to_numpy(dtype=float)
    n = ts.size

    # ---- baseline, recomputed so panel 2's threshold curves are the real ones
    bm = row.trades_bitmap if isinstance(row.trades_bitmap, str) and len(row.trades_bitmap) == 7 else None
    flank = {}
    for o in FLANK:
        w = session_window(row.event_date_canonical, o)
        sub = data.get(o)
        arr = np.zeros(0, dtype=np.int64) if sub is None else sub["sip_timestamp"].to_numpy()
        coll = (bm[o + 3] == "1") if bm else (arr.size > 0)
        flank[o] = {"ts": arr, "start_ns": w["start_ns"] if w else 0,
                    "span_minutes": w["span_minutes"] if w else 0,
                    "collected": bool(coll) and w is not None}
    base = build_baseline(flank, win["span_minutes"], b["baseline_window_minutes"],
                          b["baseline_floor_per_min"])

    # ---- display sampling (top panel only; all computation used every print)
    over = n > cap_pts
    if over:
        rate = cap_pts / n
        idx = np.sort(np.random.default_rng(seed).choice(n, size=cap_pts, replace=False))
    else:
        rate, idx = 1.0, np.arange(n)
    et = ns_to_et(ts[idx])

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.055, row_heights=[0.60, 0.40],
        subplot_titles=[
            "Trade prints — price vs time (marker size = share count). "
            "Arm B bursts shaded; Arm A bursts in the ribbon lane at the top.",
            "Inter-trade time (log, seconds). LOWER = FASTER. Both arms' rate measures and "
            "thresholds converted to seconds so there is one y-scale.",
        ])

    # ---------- panel 1: Arm B full-height shading
    ymin, ymax = float(px.min()), float(px.max())
    pad = (ymax - ymin) * 0.06 or 0.01
    lo, hi = ymin - pad, ymax + pad
    bx, by = [], []
    for r in bursts_b.itertuples(index=False):
        s, e = pd.Timestamp(ns_to_et([r.start_ns]).iloc[0]), pd.Timestamp(ns_to_et([r.end_ns]).iloc[0])
        bx += [s, e, e, s, s, None]
        by += [lo, lo, hi, hi, lo, None]
    if bx:
        fig.add_trace(go.Scatter(
            x=bx, y=by, fill="toself", mode="lines",
            fillcolor="rgba(235,104,52,0.13)", line=dict(width=0),
            name=f"Arm B bursts (n={len(bursts_b)})", legendgroup="B",
            hoverinfo="skip"), row=1, col=1)

    # ---------- panel 1: Arm A ribbon lane
    lane_lo, lane_hi = hi - (hi - lo) * 0.045, hi
    ax_, ay = [], []
    for r in bursts_a.itertuples(index=False):
        s, e = pd.Timestamp(ns_to_et([r.start_ns]).iloc[0]), pd.Timestamp(ns_to_et([r.end_ns]).iloc[0])
        ax_ += [s, e, e, s, s, None]
        ay += [lane_lo, lane_lo, lane_hi, lane_hi, lane_lo, None]
    if ax_:
        fig.add_trace(go.Scatter(
            x=ax_, y=ay, fill="toself", mode="lines",
            fillcolor="rgba(42,120,214,0.75)", line=dict(width=0),
            name=f"Arm A bursts (n={len(bursts_a)}, ribbon lane)", legendgroup="A",
            hoverinfo="skip"), row=1, col=1)

    # ---------- panel 1: the prints
    s_disp = sz[idx]
    msize = 4 + 10 * (np.log10(np.maximum(s_disp, 1)) / max(np.log10(max(s_disp.max(), 10)), 1))
    fig.add_trace(go.Scattergl(
        x=et, y=px[idx], mode="markers",
        marker=dict(size=msize, color="#1b1b1a", opacity=0.55,
                    line=dict(width=0)),
        name=f"prints ({'all ' + format(n, ',') if not over else format(cap_pts, ',') + f' of {n:,}'})",
        customdata=s_disp,
        hovertemplate="%{x|%H:%M:%S}<br>price %{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>",
    ), row=1, col=1)

    # ---------- panel 2: inter-trade time
    gaps = np.diff(ts) / 1e9
    gaps = np.maximum(gaps, 1e-6)
    g_et = ns_to_et(ts[1:])
    if n - 1 > cap_pts:
        # envelope from ALL prints -- nothing removed from any computation
        bins = pd.Series(gaps).groupby(((ts[1:] - win["start_ns"]) // 10_000_000_000))
        env = bins.agg(["min", "median", "max"])
        env_t = ns_to_et((env.index.to_numpy() * 10_000_000_000 + win["start_ns"]).astype(np.int64))
        fig.add_trace(go.Scatter(
            x=list(env_t) + list(env_t)[::-1], y=list(env["max"]) + list(env["min"])[::-1],
            fill="toself", fillcolor="rgba(27,27,26,0.13)", line=dict(width=0),
            name="inter-trade time min–max per 10 s (all prints)", hoverinfo="skip"), row=2, col=1)
        fig.add_trace(go.Scattergl(
            x=env_t, y=env["median"], mode="lines", line=dict(color="#1b1b1a", width=1),
            name="inter-trade time, median per 10 s",
            hovertemplate="%{x|%H:%M:%S}<br>median gap %{y:,.4g}s<extra></extra>"), row=2, col=1)
        panel2_mode = "envelope (min/median/max per 10 s, computed from every print)"
    else:
        fig.add_trace(go.Scattergl(
            x=g_et, y=gaps, mode="markers",
            marker=dict(size=3.5, color="#1b1b1a", opacity=0.45),
            name=f"inter-trade time (all {n-1:,} gaps)",
            hovertemplate="%{x|%H:%M:%S}<br>gap %{y:,.4g}s<extra></extra>"), row=2, col=1)
        panel2_mode = "every gap plotted"

    # ---------- panel 2: Arm B rate measure + thresholds, in seconds
    step = int(b["grid_seconds"]) * 1_000_000_000
    end_ns = win["start_ns"] + win["span_minutes"] * 60_000_000_000
    grid = np.arange(win["start_ns"], end_ns + step, step, dtype=np.int64)
    half = int(b["rate_window_seconds"]) * 1_000_000_000 // 2
    rate_t0 = (np.searchsorted(ts, grid + half, "left") - np.searchsorted(ts, grid - half, "left")) \
        / (b["rate_window_seconds"] / 60.0)
    minute_of = np.clip((grid - win["start_ns"]) // 60_000_000_000, 0, win["span_minutes"] - 1).astype(int)
    base_g = np.maximum(base["rate_floored"][minute_of], b["baseline_floor_per_min"])
    g_t = ns_to_et(grid)

    def to_sec(r):
        """Rate (prints/min) -> equivalent inter-trade time (s). A rate of exactly
        zero has NO equivalent gap -- 60/0 is undefined, not a very large number.
        Return NaN so the line breaks there. Plotting it as 60/1e-9 = 6e10 s put
        spikes to ~1e10 on a log axis and destroyed the panel's y-range."""
        r = np.asarray(r, dtype=float)
        return np.where(r > 0, 60.0 / np.maximum(r, 1e-12), np.nan)
    fig.add_trace(go.Scatter(
        x=g_t, y=to_sec(rate_t0), mode="lines", line=dict(color=C.ARM_B, width=1.8),
        name="Arm B rate measure (60 / prints-per-min)", legendgroup="B",
        hovertemplate="%{x|%H:%M:%S}<br>equiv. gap %{y:,.4g}s<extra></extra>"), row=2, col=1)
    for mult, dash, lbl in ((b["on_multiplier"], "dash", "on"), (b["off_multiplier"], "dot", "off")):
        fig.add_trace(go.Scatter(
            x=g_t, y=to_sec(base_g * mult), mode="lines",
            line=dict(color=C.ARM_B, width=1.3, dash=dash),
            name=f"Arm B {lbl} threshold ({mult:g}× time-of-day baseline)", legendgroup="B",
            hovertemplate=f"%{{x|%H:%M:%S}}<br>{lbl} at %{{y:,.4g}}s<extra></extra>"), row=2, col=1)

    # ---------- panel 2: Arm A state rates as inter-arrival times
    span = float(ts[-1] - ts[0]) / 1e9
    if span > 0 and n > 1:
        g_mean = span / n
        for a_rate, dash, lbl in ((g_mean, "dash", "α₀ (quiet state)"),
                                  (g_mean / cfg["arm_a"]["s"], "dot", "α₁ (burst state)")):
            fig.add_hline(y=a_rate, line=dict(color=C.ARM_A, width=1.3, dash=dash),
                          annotation_text=f"Arm A {lbl} = {a_rate:,.4g}s",
                          annotation_position="right",
                          annotation_font=dict(size=10, color=C.ARM_A), row=2, col=1)

    # ---------- panel 2: same burst overlays
    if bx:
        y2lo, y2hi = float(np.min(gaps)) * 0.5, float(np.max(gaps)) * 2
        fig.add_trace(go.Scatter(
            x=bx, y=[y2lo if v == lo else (y2hi if v == hi else v) for v in by],
            fill="toself", mode="lines", fillcolor="rgba(235,104,52,0.10)",
            line=dict(width=0), showlegend=False, legendgroup="B", hoverinfo="skip"), row=2, col=1)

    fig.update_yaxes(title_text="trade price", row=1, col=1, range=[lo, hi])
    fig.update_yaxes(title_text="inter-trade time (s, log)", type="log", row=2, col=1)
    fig.update_xaxes(title_text="America/New_York (extended day, 04:00–20:00)", row=2, col=1,
                     rangeslider=dict(visible=False))

    label = "" if row.cohort_group in ("dev_v4_primary", "activity_extension") \
        else f" — <span style='color:#b03a3a'>{row.cohort_group.upper()}</span>"
    C.finish(
        fig,
        f"07 — {row.ticker} {row.event_date_canonical} "
        f"({row.momentum_pct:.2f}%){label}",
        f"{n:,} T=0 prints · Arm A {len(bursts_a)} bursts · Arm B {len(bursts_b)} bursts · "
        f"cohort group {row.cohort_group} · baseline {base['label']}",
        C.caption(
            f"one event: {row.ticker} {row.event_date_canonical}, {n:,} in-window T=0 prints",
            f"T=0 extended-day window only; both arms at their reference parameter point; "
            f"selected because: {row.chart_selection_reason}",
            chash,
            f"<b>Top panel display:</b> "
            f"{'all prints plotted' if not over else f'seeded uniform random subsample, {rate:.3%} of prints — uniform sampling preserves relative density, which is what the tape read depends on'}. "
            f"<b>Bottom panel:</b> {panel2_mode}. "
            "Burst intervals on both panels come from the FULL-resolution segmentation regardless. "
            "<br><b>Reads:</b> shaded intervals that do not correspond to visible density changes in "
            "the print stream, or that miss obvious clusters, mean the segmentation does not "
            "correspond to the tape."),
        height=980, width=1560)

    name = f"{row.ticker}_{row.event_date_canonical}"
    path = os.path.join(out_dir, f"{name}.html")
    fig.write_html(path, include_plotlyjs="cdn", full_html=True,
                   config={"displaylogo": False, "responsive": True})
    return {
        "file": f"{name}.html", "ticker": row.ticker,
        "event_date_canonical": row.event_date_canonical, "momentum_pct": row.momentum_pct,
        "cohort_group": row.cohort_group, "n_prints_t0": int(n),
        "n_bursts_arm_a": int(len(bursts_a)), "n_bursts_arm_b": int(len(bursts_b)),
        "baseline_label": base["label"], "subsampled": bool(over),
        "selection_reason": row.chart_selection_reason,
        "bytes": os.path.getsize(path),
    }


def write_index(rows, cohort, cfg, chash, out_dir) -> str:
    """Sortable index over the FULL cohort -- charted or not (§7: chart coverage
    may be sampled, index coverage may not)."""
    by_file = {(r["ticker"], r["event_date_canonical"]): r for r in rows}
    recs = []
    for r in cohort.itertuples(index=False):
        m = by_file.get((r.ticker, r.event_date_canonical))
        recs.append({
            "ticker": r.ticker, "date": r.event_date_canonical,
            "momentum_pct": f"{r.momentum_pct:.2f}", "group": r.cohort_group,
            "t0_prints": int(r.t0_print_count),
            "arm_a": m["n_bursts_arm_a"] if m else "",
            "arm_b": m["n_bursts_arm_b"] if m else "",
            "baseline": m["baseline_label"] if m else "",
            "chart": f'<a href="{m["file"]}">open</a>' if m else "<span class=no>not charted</span>",
            "why": m["selection_reason"] if m else "not selected (config cap)",
        })
    hdr = ["ticker", "date", "momentum_pct", "group", "t0_prints", "arm_a", "arm_b",
           "baseline", "chart", "why"]
    body = "\n".join(
        "<tr>" + "".join(
            f"<td data-v='{html.escape(str(rec[h]))}'>{rec[h] if h == 'chart' else html.escape(str(rec[h]))}</td>"
            for h in hdr) + "</tr>"
        for rec in recs)
    head = "".join(f"<th onclick='S({i})'>{h}</th>" for i, h in enumerate(hdr))
    doc = f"""<!doctype html><meta charset="utf-8"><title>Phase 10 — chart 07 tape review index</title>
<style>
body{{font:14px/1.5 Inter,Segoe UI,system-ui,sans-serif;color:#0b0b0b;background:#fcfcfb;margin:28px}}
h1{{font-size:19px;margin:0 0 4px}} p{{color:#52514e;margin:0 0 16px;max-width:78ch}}
table{{border-collapse:collapse;font-size:13px}} th,td{{padding:5px 11px;border-bottom:1px solid #e2e2df;text-align:left}}
th{{cursor:pointer;background:#f2f2ef;position:sticky;top:0;user-select:none}} th:hover{{background:#e8e8e4}}
tr:hover td{{background:#f7f7f4}} .no{{color:#8a8a84}} a{{color:#2a78d6}}
</style>
<h1>Phase 10 — chart 07 tape review index</h1>
<p>All {len(recs)} cohort events. Chart coverage is bounded by
<code>config.charts.chart_07.max_charts</code> = {cfg['charts']['chart_07']['max_charts']};
index coverage is complete, per Agent_Prompt_Standard §7. Click any header to sort.
<b>config_hash:</b> {chash}</p>
<table><thead><tr>{head}</tr></thead><tbody id=b>{body}</tbody></table>
<script>
let d={{}};function S(i){{const t=document.getElementById('b');
const r=[...t.rows];d[i]=!d[i];const num=[4,5,6].includes(i)||i==2;
r.sort((a,b)=>{{let x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;
if(num){{x=parseFloat(x)||-1;y=parseFloat(y)||-1;return d[i]?x-y:y-x}}
return d[i]?x.localeCompare(y):y.localeCompare(x)}});r.forEach(x=>t.appendChild(x))}}
</script>"""
    p = os.path.join(out_dir, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(doc)
    return p


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out_dir = os.path.join(rel(cfg["paths"]["out_charts"]), SUBDIR)
    os.makedirs(out_dir, exist_ok=True)

    # Keep the §12 outcome (thousands of multi-MB HTML files stay untracked) while
    # every write stays inside the escalation-row-7 allowlist: a nested .gitignore
    # rather than an edit to the repo-root one.
    with open(os.path.join(out_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("# Phase 10 chart 07: per-event tape review HTML, regenerable from\n"
                "# committed config + code (Agent_Prompt_Standard §12).\n*\n")

    cohort = load_cohort(cfg)
    A = pd.read_parquet(os.path.join(art, "t2_bursts_arm_a.parquet"))
    B = pd.read_parquet(os.path.join(art, "t3_bursts_arm_b.parquet"))
    A, B = A[A["is_ref"]], B[B["is_ref"]]
    for d in (A, B):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)

    a_counts = A.groupby(KEY).size().rename("n_bursts_ref").reset_index()
    sel = select_events(cohort, a_counts, cfg)

    cap = cfg["charts"]["chart_07"]["max_charts"]
    if len(sel) > cap:
        print(f"ESCALATION ROW 6: selection {len(sel)} exceeds config cap {cap}. Nothing written.")
        return 6
    print(f"chart 07: {len(sel)} events selected (cap {cap})")

    rows = []
    for i, r in enumerate(sel.itertuples(index=False), 1):
        ba = A[(A["ticker"] == r.ticker) & (A["event_date_canonical"] == r.event_date_canonical)
               & (np.isclose(A["momentum_pct"], r.momentum_pct))]
        bb = B[(B["ticker"] == r.ticker) & (B["event_date_canonical"] == r.event_date_canonical)
               & (np.isclose(B["momentum_pct"], r.momentum_pct))]
        rec = build_chart(cfg, r, ba, bb, chash, out_dir)
        if rec:
            rows.append(rec)
        if i % 10 == 0:
            print(f"  {i}/{len(sel)} charts written", flush=True)

    idx = write_index(rows, cohort, cfg, chash, out_dir)
    total_mb = sum(r["bytes"] for r in rows) / 1e6
    write_json(os.path.join(art, "t6b_tape_review_manifest.json"), {
        "phase": "10", "task": "T6b", "config_hash": chash,
        "n_charts": len(rows), "cap": cap, "escalation_row_6_triggered": False,
        "index": f"{cfg['paths']['out_charts']}{SUBDIR}/index.html",
        "index_covers_full_cohort": True, "index_n_rows": int(len(cohort)),
        "gitignore": "nested .gitignore inside the chart dir, so the §12 outcome is achieved "
                     "without writing outside the escalation-row-7 allowlist",
        "total_megabytes": round(total_mb, 1),
        "n_subsampled": int(sum(r["subsampled"] for r in rows)),
        "selection_counts": pd.Series([r["selection_reason"] for r in rows]).value_counts().to_dict(),
        "charts": rows,
        "source": "research/phase_10/t6b_tape_review.py:main",
    })
    print(f"  wrote {len(rows)} charts, {total_mb:.0f} MB total, "
          f"{sum(r['subsampled'] for r in rows)} subsampled")
    print(f"  index: {idx} ({len(cohort)} rows, full cohort)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
