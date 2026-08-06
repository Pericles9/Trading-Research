"""
Phase 10 v4 chart 06 -- per-event tape review. THE GATE. Produced even though
rows 1 and 6 fired.

SCALE PROBLEM, AND THE FIX. v4's sub-bursts have a median duration of 348 ns and
90.5% are under 1 ms. On a 57,600-second session axis a 348 ns rectangle is
6e-12 of the width -- it is drawn, but it is sub-pixel and therefore invisible.
The first version of this chart shaded them anyway and showed nothing.

This version instead:
  * marks sub-burst LOCATIONS on the full-session panel as full-height ticks,
    explicitly labelled as locations rather than widths;
  * adds two ZOOM panels at scales where the objects actually resolve -- a
    ~2 second window on the densest region, and a ~200 microsecond window on the
    largest single sub-burst -- where the intervals ARE shaded to true extent.

Without the zooms there is nothing to review, which is the point of the gate.

Panels:
  1  full session: prints, price, sub-burst location ticks
  2  full session: inter-trade time, log, with the per-event threshold
  3  full session: normalized log interval, with the same threshold
  4  ZOOM ~2 s on the densest sub-burst region: prints + shaded sub-bursts
  5  ZOOM ~200 us on the largest sub-burst: prints + shaded sub-burst

Usage: .venv/Scripts/python.exe research/phase_10/v4_t7b_tape.py
"""
from __future__ import annotations

import html
import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chartlib as C  # noqa: E402
from common import ns_to_et  # noqa: E402
from v2_common import (  # noqa: E402
    COHORT_KEY, collapse_ties, load_frozen_cohort, read_event_trades, rel,
    session_window, write_json,
)
from v4_pipeline import cfg_hash, load_cfg, moving_median_log  # noqa: E402

SUB = "v4_06_tape_review"
ZOOM_WIDE_S = 2.0
ZOOM_TIGHT_MIN_S = 5e-6


def shade(fig, ivals, lo, hi, row, col, name, show, clip=None):
    """Shade intervals. `clip` = (a_ns, b_ns): rects are CLIPPED to it, so a long
    sub-burst overlapping a tight zoom cannot stretch the axis out of the window."""
    bx, by = [], []
    for a, b in ivals:
        if clip is not None:
            a, b = max(int(a), clip[0]), min(int(b), clip[1])
            if b <= a:
                a, b = a, a + 1  # keep a hairline so a clipped burst is still visible
        A = pd.Timestamp(ns_to_et([a]).iloc[0]); B = pd.Timestamp(ns_to_et([b]).iloc[0])
        bx += [A, B, B, A, A, None]; by += [lo, lo, hi, hi, lo, None]
    if bx:
        fig.add_trace(go.Scatter(x=bx, y=by, fill="toself", mode="lines",
                                 fillcolor="rgba(42,120,214,0.35)",
                                 line=dict(color="rgba(42,120,214,0.9)", width=1),
                                 name=name, showlegend=show, hoverinfo="skip"), row=row, col=col)


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out_dir = os.path.join(rel(cfg["paths"]["out_charts"]), SUB)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("# Phase 10 v4 chart 06: per-event tape review, regenerable.\n*\n")

    c6 = cfg["charts"]["chart_06"]
    tie_ref = cfg["ties"]["reference_variant"]
    wref = cfg["normalization"]["window_fraction_reference"]
    mref = cfg["subbursts"]["min_prints_reference"]
    cohort = load_frozen_cohort({"paths": {"cohort_manifest": cfg["paths"]["cohort_manifest"]},
                                 "cohort": {"content_hash": cfg["cohort"]["content_hash"]}})
    ev = pd.read_parquet(os.path.join(art, "v4_event_metrics.parquet"))
    sb = pd.read_parquet(os.path.join(art, "v4_subbursts.parquet"))
    for d in (ev, sb):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    ref = ev[(ev["tie_variant"] == tie_ref) & (ev["window_fraction"] == wref)
             & (ev["min_prints"].fillna(mref) == mref)].set_index(COHORT_KEY)
    det = pd.read_parquet(rel(cfg["paths"]["detection"]))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], cfg["detection_anchor"]["threshold"])].set_index(COHORT_KEY)
    v2m = pd.read_parquet(rel(cfg["paths"]["v2_event_metrics"]))
    v2m["event_date_canonical"] = v2m["event_date_canonical"].astype(str)
    v2m = v2m[(v2m["tie_variant"] == "as_is") & (v2m["k"] == 50)
              & (v2m["observable"] == "print_rate")].set_index(COHORT_KEY)["peak_ns"]

    co = cohort.copy()
    idx = pd.MultiIndex.from_frame(co[COHORT_KEY])
    co["status"] = ref["status"].reindex(idx).to_numpy()
    co["n_sub"] = ref["n_subbursts"].reindex(idx).to_numpy()
    co["segment"] = ref["segment"].reindex(idx).to_numpy()

    nt = co[co["status"] == "no_threshold"]
    prim = co[(co["cohort_group"] == "dev_v4_primary") & (co["status"] != "no_threshold")]
    rest = co[~co.set_index(COHORT_KEY).index.isin(
        pd.concat([nt, prim]).set_index(COHORT_KEY).index)].sort_values(
        ["segment", "n_sub"] + COHORT_KEY)
    room = max(0, c6["max_charts"] - len(nt) - len(prim))
    extra = (rest.iloc[np.linspace(0, len(rest) - 1, min(room, len(rest))).round().astype(int)]
             if room > 0 and len(rest) else rest.head(0))
    sel = pd.concat([nt, prim, extra], ignore_index=True).drop_duplicates(subset=COHORT_KEY)
    sel = sel.head(c6["max_charts"])
    print(f"chart 06: {len(sel)} events ({len(nt)} no_threshold first), cap {c6['max_charts']}")

    rows = []
    for i, r in enumerate(sel.itertuples(index=False), 1):
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts_raw = t0["sip_timestamp"].to_numpy()
        px_raw = t0["price"].to_numpy(dtype=float)
        sz_raw = t0["size"].to_numpy(dtype=float)
        cts, csz, _ = collapse_ties(ts_raw, sz_raw)
        first = np.flatnonzero(np.concatenate(([True], ts_raw[1:] != ts_raw[:-1])))
        last = np.append(first[1:] - 1, ts_raw.size - 1)
        pxv = px_raw[last]
        n = cts.size
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        e = ref.loc[key] if key in ref.index else None
        if isinstance(e, pd.DataFrame):
            e = e.iloc[0]
        drow = det.loc[key] if key in det.index else None
        if isinstance(drow, pd.DataFrame):
            drow = drow.iloc[0]
        det_ns = int(drow["det_ns_poll1"]) if drow is not None and pd.notna(drow["det_ns_poll1"]) else None
        pk_ns = v2m.get(key)
        thr = e["threshold_decades"] if e is not None and pd.notna(e.get("threshold_decades")) else None

        dt = np.diff(cts).astype(np.float64) / 1e9
        ly = np.log10(np.maximum(dt, 1e-12))
        yn = ly - moving_median_log(ly, wref) if dt.size >= 10 else ly

        sbs = sb[(sb["ticker"] == r.ticker) & (sb["event_date_canonical"] == r.event_date_canonical)
                 & (np.isclose(sb["momentum_pct"], r.momentum_pct))].sort_values("start_ns")
        iv = list(zip(sbs["start_ns"].to_numpy(), sbs["end_ns"].to_numpy()))

        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=False, vertical_spacing=0.075,
            row_heights=[0.26, 0.16, 0.16, 0.21, 0.21],
            subplot_titles=[
                "FULL SESSION — price. Blue ticks mark sub-burst LOCATIONS, not widths "
                "(median duration 348 ns is sub-pixel on this axis)",
                "FULL SESSION — inter-trade time, log, with the per-event threshold",
                "FULL SESSION — normalized log10 interval, with the same threshold",
                f"ZOOM — densest sub-burst region, intervals shaded to true extent",
                "ZOOM — typical busy sub-burst, intervals shaded to true extent"])

        ymin, ymax = float(pxv.min()), float(pxv.max())
        pad = (ymax - ymin) * 0.06 or 0.01
        lo, hi = ymin - pad, ymax + pad

        # ---- panel 1: location ticks (a 348 ns rect cannot be seen; a tick can)
        if iv:
            tx, ty = [], []
            for a, _b in iv:
                A = pd.Timestamp(ns_to_et([a]).iloc[0])
                tx += [A, A, None]; ty += [lo, hi, None]
            fig.add_trace(go.Scattergl(x=tx, y=ty, mode="lines",
                                       line=dict(color="rgba(42,120,214,0.55)", width=1),
                                       name=f"sub-burst locations (n={len(iv)})",
                                       hoverinfo="skip"), row=1, col=1)
        over = n > c6["max_scatter_points"]
        ii = (np.sort(np.random.default_rng(c6["over_cap_seed"]).choice(
            n, c6["max_scatter_points"], replace=False)) if over else np.arange(n))
        ms = 4 + 9 * (np.log10(np.maximum(csz[ii], 1)) / max(np.log10(max(csz.max(), 10)), 1))
        fig.add_trace(go.Scattergl(x=ns_to_et(cts[ii]), y=pxv[ii], mode="markers",
                                   marker=dict(size=ms, color="#1b1b1a", opacity=0.55),
                                   name=f"prints ({'all ' + format(n, ',') if not over else format(c6['max_scatter_points'], ',') + f' of {n:,}'})",
                                   customdata=csz[ii],
                                   hovertemplate="%{x|%H:%M:%S}<br>%{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>"),
                      row=1, col=1)

        gs = max(1, dt.size // 40000)
        gt = ns_to_et(cts[1:][::gs])
        fig.add_trace(go.Scattergl(x=gt, y=dt[::gs], mode="markers",
                                   marker=dict(size=2.5, color="#1b1b1a", opacity=0.4),
                                   name="inter-trade time", showlegend=False), row=2, col=1)
        fig.add_trace(go.Scattergl(x=gt, y=yn[::gs], mode="markers",
                                   marker=dict(size=2.5, color=C.ARM_A, opacity=0.4),
                                   name="normalized log10 interval", showlegend=False), row=3, col=1)
        if thr is not None:
            fig.add_hline(y=thr, line=dict(color="#b03a3a", width=2),
                          annotation_text=f"threshold {thr:+.2f}", annotation_position="right",
                          annotation_font=dict(size=10, color="#b03a3a"), row=3, col=1)

        # ---- zoom windows
        zoom_note = "no sub-bursts to zoom on"
        zoom_titles = {}
        if iv:
            starts = np.array([a for a, _ in iv], dtype=np.int64)
            # densest 2 s window by sub-burst starts
            binw = int(ZOOM_WIDE_S * 1e9)
            b0 = (starts - starts.min()) // binw
            dense_bin = np.bincount(b0).argmax()
            c_ns = int(starts.min() + dense_bin * binw + binw // 2)
            # Pick the busiest sub-burst among the TYPICAL ones (under 1 ms, which is
            # 90.5% of them). The single longest is a 1.9 s outlier and would make
            # the "tight" zoom meaningless.
            typ = sbs[sbs["duration_seconds"] <= 1e-3]
            big = (typ.iloc[int(np.argmax(typ["n_prints"].to_numpy()))] if len(typ)
                   else sbs.iloc[int(np.argmax(sbs["n_prints"].to_numpy()))])
            big_c = int((big["start_ns"] + big["end_ns"]) // 2)
            big_w = max(ZOOM_TIGHT_MIN_S, 20 * float(big["duration_seconds"]))
            for ri, (cen, wid, lab) in enumerate(
                    ((c_ns, ZOOM_WIDE_S, "wide"), (big_c, big_w, "tight")), 4):
                a_ns, b_ns = int(cen - wid / 2 * 1e9), int(cen + wid / 2 * 1e9)
                m = (cts >= a_ns) & (cts <= b_ns)
                if m.sum() == 0:
                    continue
                sub_iv = [(a, b) for a, b in iv if b >= a_ns and a <= b_ns]
                zl, zh = float(pxv[m].min()), float(pxv[m].max())
                zp = (zh - zl) * 0.08 or 0.01
                shade(fig, sub_iv, zl - zp, zh + zp, ri, 1,
                      f"sub-bursts in view (n={len(sub_iv)})", ri == 4,
                      clip=(a_ns, b_ns))
                zms = 6 + 9 * (np.log10(np.maximum(csz[m], 1)) / max(np.log10(max(csz.max(), 10)), 1))
                fig.add_trace(go.Scattergl(
                    x=ns_to_et(cts[m]), y=pxv[m], mode="markers",
                    marker=dict(size=zms, color="#1b1b1a", opacity=0.8),
                    name=f"prints in view ({int(m.sum()):,})", showlegend=(ri == 4),
                    customdata=csz[m],
                    hovertemplate="%{x|%H:%M:%S.%L}<br>%{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>"),
                    row=ri, col=1)
                fig.update_yaxes(title_text="price", range=[zl - zp, zh + zp], row=ri, col=1)
                # explicit range: without it a clipped rect or a stray marker re-ranges the axis
                fig.update_xaxes(
                    range=[pd.Timestamp(ns_to_et([a_ns]).iloc[0]),
                           pd.Timestamp(ns_to_et([b_ns]).iloc[0])],
                    title_text=None, row=ri, col=1)
                span_txt = (f"{wid*1e3:,.3g} ms" if wid >= 1e-3 else f"{wid*1e6:,.3g} µs")
                zoom_titles[ri] = (
                    f"ZOOM — {'densest sub-burst region' if lab == 'wide' else 'typical busy sub-burst'}"
                    f" · {span_txt} span · {int(m.sum()):,} prints · {len(sub_iv)} sub-burst(s)"
                    " · shaded to true extent")
            zoom_note = (f"wide zoom spans {ZOOM_WIDE_S:g} s on the densest region; tight zoom spans "
                         f"{big_w*1e6:,.1f} µs on a typical busy sub-burst "
                         f"({float(big['duration_seconds'])*1e9:,.0f} ns, {int(big['n_prints'])} prints)")

        for ri, txt in zoom_titles.items():
            fig.layout.annotations[ri - 1].update(text=txt)

        for ns_, col, lab in ((det_ns, "#b03a3a", "detection (D7)"),
                              (int(pk_ns) if pk_ns is not None and pd.notna(pk_ns) else None,
                               "#008300", "peak (retrospective)")):
            if ns_ is None:
                continue
            x = pd.Timestamp(ns_to_et([ns_]).iloc[0])
            for rr in (1, 2, 3):
                fig.add_vline(x=x, line=dict(color=col, width=1.8, dash="dash"), row=rr, col=1)
            fig.add_annotation(x=x, y=(1.0 if col == "#b03a3a" else 0.965), yref="paper",
                               text=lab, showarrow=False, font=dict(size=10, color=col),
                               xanchor="left", xshift=4)

        fig.update_yaxes(title_text="price", range=[lo, hi], row=1, col=1)
        fig.update_yaxes(title_text="inter-trade s (log)", type="log", row=2, col=1)
        fig.update_yaxes(title_text="normalized log10", row=3, col=1)
        for rr in (1, 2, 3):
            fig.update_xaxes(title_text=None, row=rr, col=1)

        st = (e["status"] if e is not None else "n/a")
        lbl = "" if r.cohort_group in ("dev_v4_primary", "activity_extension") else \
            f" — <span style='color:#b03a3a'>{r.cohort_group.upper()}</span>"
        nolbl = " — <span style='color:#b03a3a'>NO THRESHOLD</span>" if st == "no_threshold" else ""
        C.finish(fig, f"06 — {r.ticker} {r.event_date_canonical} ({r.momentum_pct:.2f}%){lbl}{nolbl}",
                 f"{n:,} collapsed arrivals · segment {r.segment} · status {st} · "
                 + (f"void {e['void']:.3f}, threshold {thr:+.2f} decades · {len(iv)} sub-bursts"
                    if thr is not None else "no threshold derived — no sub-bursts declared"),
                 C.caption(f"one event: {r.ticker} {r.event_date_canonical}",
                           f"T=0 only; tie={tie_ref}, window={wref:.0%}, min_prints={mref}", chash,
                           "<b>Scale:</b> v4 sub-bursts have a median duration of 348 ns and 90.5% "
                           "are under 1 ms. On the full-session axis that is ~1e-11 of the width, so "
                           "panel 1 marks LOCATIONS as ticks; only the zoom panels show true extent. "
                           + zoom_note + ". "
                           + ("all arrivals plotted" if not over else
                              f"Panel 1 subsampled to {c6['max_scatter_points']:,} of {n:,}; zooms "
                              "always plot every print in view.")
                           + "<br><b>Reads:</b> if the shaded intervals in the zooms sit on "
                           "multi-print bursts that are a single order sweeping the book rather than "
                           "market-wide activity, the decomposition is measuring microstructure."),
                 height=1560, width=1560)
        name = f"{r.ticker}_{r.event_date_canonical}"
        p = os.path.join(out_dir, f"{name}.html")
        fig.write_html(p, include_plotlyjs="cdn", full_html=True,
                       config={"displaylogo": False, "responsive": True})
        rows.append({"file": f"{name}.html", "ticker": r.ticker,
                     "event_date_canonical": r.event_date_canonical,
                     "cohort_group": r.cohort_group, "segment": str(r.segment),
                     "status": str(st), "n_subbursts": int(len(iv)),
                     "bytes": os.path.getsize(p)})
        if i % 10 == 0:
            print(f"  {i}/{len(sel)} charts", flush=True)

    by = {(x["ticker"], x["event_date_canonical"]): x for x in rows}
    recs = []
    for r in cohort.itertuples(index=False):
        m = by.get((r.ticker, r.event_date_canonical))
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        e = ref.loc[key] if key in ref.index else None
        if isinstance(e, pd.DataFrame):
            e = e.iloc[0]
        recs.append({"ticker": r.ticker, "date": r.event_date_canonical, "group": r.cohort_group,
                     "segment": str(e["segment"]) if e is not None else "",
                     "status": str(e["status"]) if e is not None else "",
                     "t0_prints": int(r.t0_print_count),
                     "subbursts": int(e["n_subbursts"]) if e is not None else "",
                     "chart": f'<a href="{m["file"]}">open</a>' if m else "<span class=no>not charted</span>"})
    hdr = ["ticker", "date", "group", "segment", "status", "t0_prints", "subbursts", "chart"]
    body = "\n".join("<tr>" + "".join(
        f"<td data-v='{html.escape(str(x[h]))}'>{x[h] if h == 'chart' else html.escape(str(x[h]))}</td>"
        for h in hdr) + "</tr>" for x in recs)
    head = "".join(f"<th onclick='S({i})'>{h}</th>" for i, h in enumerate(hdr))
    doc = f"""<!doctype html><meta charset="utf-8"><title>Phase 10 v4 — chart 06 index</title>
<style>body{{font:14px/1.5 Inter,Segoe UI,system-ui,sans-serif;color:#0b0b0b;background:#fcfcfb;margin:28px}}
h1{{font-size:19px;margin:0 0 4px}}p{{color:#52514e;margin:0 0 16px;max-width:82ch}}
table{{border-collapse:collapse;font-size:13px}}th,td{{padding:5px 11px;border-bottom:1px solid #e2e2df;text-align:left}}
th{{cursor:pointer;background:#f2f2ef;position:sticky;top:0}}tr:hover td{{background:#f7f7f4}}
.no{{color:#8a8a84}}a{{color:#2a78d6}}</style>
<h1>Phase 10 v4 — chart 06 tape review index</h1>
<p>All {len(recs)} cohort events. Chart coverage capped at {c6['max_charts']}; index coverage complete
per §7. Produced under the failure (rows 1, 6); every <code>no_threshold</code> event charted first.
<b>Each chart has five panels:</b> three at full-session scale, then two zooms — v4's sub-bursts have
a median duration of 348 ns, which is sub-pixel on a 16-hour axis, so only the zooms show their true
extent. <b>config_hash:</b> {chash}</p>
<table><thead><tr>{head}</tr></thead><tbody id=b>{body}</tbody></table>
<script>let d={{}};function S(i){{const t=document.getElementById('b');const r=[...t.rows];
d[i]=!d[i];const num=[5,6].includes(i);r.sort((a,b)=>{{let x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;
if(num){{x=parseFloat(x)||-1;y=parseFloat(y)||-1;return d[i]?x-y:y-x}}
return d[i]?x.localeCompare(y):y.localeCompare(x)}});r.forEach(x=>t.appendChild(x))}}</script>"""
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    write_json(os.path.join(art, "v4_t7b_tape_manifest.json"),
               {"phase": "10", "version": "v4", "task": "T7b", "config_hash": chash,
                "n_charts": len(rows), "cap": c6["max_charts"],
                "n_no_threshold_charted": int(sum(x["status"] == "no_threshold" for x in rows)),
                "index_n_rows": len(recs), "index_covers_full_cohort": True,
                "total_megabytes": round(sum(x["bytes"] for x in rows) / 1e6, 1),
                "produced_under_failure": True,
                "panels": 5,
                "scale_fix": ("v4 sub-bursts median 348 ns, 90.5% under 1 ms -- sub-pixel on a "
                              "57,600 s axis. Full-session panel marks locations as ticks; two zoom "
                              "panels (~2 s and ~200 us) show true extent."),
                "charts": rows,
                "source": "research/phase_10/v4_t7b_tape.py:main"})
    print(f"  wrote {len(rows)} charts, {sum(x['bytes'] for x in rows)/1e6:.0f} MB; "
          f"index {len(recs)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
