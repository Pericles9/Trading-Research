"""
Phase 10c Stage 1, T7a -- Row 0 tape review. THE gate. Cooper's alone; this script
produces the chart set and evaluates nothing.

"Row 0 is Cooper's, and it overrides the numeric rows in either direction. It has
been the only criterion that fired correctly across all Phase 10 method families --
numeric criteria passed in every version while both arms were wrong." (prompt S7)

Reference cell for the primary 5-panel chart: kernel=8min (D5, the first/primary
kernel), threshold=1.25 (the reference variant) -- the same single-reference-
parameter-set convention Phase 10 v4's own tape review used. Other kernels/variants
are on record in s1_t1_cells.parquet / s1_t1_subbursts.parquet and noted in each
chart's caption, not re-plotted 9x per event.

Panels (adapted from research/phase_10/v4_t7b_tape.py's proven grammar):
  1  full session: price, sub-burst LOCATION ticks (durations here run ms-to-s,
     not v4's 348ns, but are still typically sub-pixel on an hours-long axis)
  2  full session: inter-trade time, log
  3  full session: normalized log10 interval, with the chosen threshold
  4  ZOOM on the densest sub-burst region, intervals shaded to true extent
  5  ZOOM on a typical busy sub-burst, intervals shaded to true extent

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t7_tape_review.py
"""
from __future__ import annotations

import html
import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
import chartlib as C  # noqa: E402
from common import ns_to_et, rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
_s6 = ilu.spec_from_file_location("s1t6", os.path.join(HERE, "s1_t6_animation.py"))
s1t6 = ilu.module_from_spec(_s6); _s6.loader.exec_module(s1t6)

ART = "results/phase_10c/artifacts"
OUT_SUB = "results/phase_10c/charts/s1_07_tape_review"
REF_KERNEL, REF_VARIANT = 8.0, 1.25
ZOOM_WIDE_S = 2.0
ZOOM_TIGHT_MIN_S = 5e-6


def shade(fig, ivals, lo, hi, row, col, name, show, clip=None):
    bx, by = [], []
    for a, b in ivals:
        if clip is not None:
            a, b = max(int(a), clip[0]), min(int(b), clip[1])
            if b <= a:
                a, b = a, a + 1
        A = pd.Timestamp(ns_to_et([a]).iloc[0]); B = pd.Timestamp(ns_to_et([b]).iloc[0])
        bx += [A, B, B, A, A, None]; by += [lo, lo, hi, hi, lo, None]
    if bx:
        fig.add_trace(go.Scatter(x=bx, y=by, fill="toself", mode="lines",
                                 fillcolor="rgba(42,120,214,0.35)",
                                 line=dict(color="rgba(42,120,214,0.9)", width=1),
                                 name=name, showlegend=show, hoverinfo="skip"), row=row, col=col)


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))
    sb = pd.read_parquet(rel(f"{ART}/s1_t1_subbursts.parquet"))
    F = float(c10c.class_m(cfg)["D4_median_precision_factor"])

    os.makedirs(OUT_SUB, exist_ok=True)
    with open(os.path.join(OUT_SUB, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("# Stage 1 T7a tape review: regenerable.\n*\n")

    ref = cells[(cells.kernel_min == REF_KERNEL) & (np.isclose(cells.threshold, REF_VARIANT))] \
        .set_index(["ticker", "event_date_canonical"])

    rows = []
    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts_raw = t0["sip_timestamp"].to_numpy()
        px_raw = t0["price"].to_numpy(dtype=float)
        sz_raw = t0["size"].to_numpy(dtype=float)
        first = np.flatnonzero(np.concatenate(([True], ts_raw[1:] != ts_raw[:-1])))
        cts = ts_raw[first]
        last = np.append(first[1:] - 1, ts_raw.size - 1)
        pxv = px_raw[last]
        csz = np.array([sz_raw[first[j]:(first[j + 1] if j + 1 < len(first) else len(sz_raw))].sum()
                        for j in range(len(first))])
        n = cts.size

        key = (r.ticker, r.event_date_canonical)
        e = ref.loc[key] if key in ref.index else None
        if isinstance(e, pd.DataFrame):
            e = e.iloc[0]
        label = e["label"] if e is not None else "n/a"
        thr_norm = float(e["threshold_norm"]) if e is not None and pd.notna(e.get("threshold_norm")) else None
        void = float(e["void"]) if e is not None and pd.notna(e.get("void")) else None
        seg = e["segment"] if e is not None else None

        ev = s1t6.compute_event(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                REF_KERNEL, F)
        mid, norm = ev["mid"], ev["norm"]

        sbs = sb[(sb.ticker == r.ticker) & (sb.event_date_canonical == r.event_date_canonical)
                & (sb.kernel_min == REF_KERNEL)].sort_values("start_ns")
        iv = list(zip(sbs.start_ns.to_numpy(), sbs.end_ns.to_numpy()))

        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=False, vertical_spacing=0.075,
            row_heights=[0.26, 0.16, 0.16, 0.21, 0.21],
            subplot_titles=[
                f"FULL SESSION -- price. Blue ticks mark sub-burst LOCATIONS (kernel={REF_KERNEL:g}min, "
                f"thr={REF_VARIANT:g}); typical durations run ms-to-s, sub-pixel on this axis",
                "FULL SESSION -- inter-trade time, log",
                "FULL SESSION -- normalized log10 interval (local median removed), with the chosen threshold",
                "ZOOM -- densest sub-burst region, intervals shaded to true extent",
                "ZOOM -- typical busy sub-burst, intervals shaded to true extent"])

        ymin, ymax = float(pxv.min()), float(pxv.max())
        pad = (ymax - ymin) * 0.06 or 0.01
        lo, hi = ymin - pad, ymax + pad

        if iv:
            tx, ty = [], []
            for a, _b in iv:
                A = pd.Timestamp(ns_to_et([a]).iloc[0])
                tx += [A, A, None]; ty += [lo, hi, None]
            fig.add_trace(go.Scattergl(x=tx, y=ty, mode="lines",
                                       line=dict(color="rgba(42,120,214,0.55)", width=1),
                                       name=f"sub-burst locations (n={len(iv)})",
                                       hoverinfo="skip"), row=1, col=1)
        over = n > 20000
        ii = (np.sort(np.random.default_rng(42).choice(n, 20000, replace=False))
             if over else np.arange(n))
        ms = 4 + 9 * (np.log10(np.maximum(csz[ii], 1)) / max(np.log10(max(csz.max(), 10)), 1))
        fig.add_trace(go.Scattergl(x=ns_to_et(cts[ii]), y=pxv[ii], mode="markers",
                                   marker=dict(size=ms, color="#1b1b1a", opacity=0.55),
                                   name=f"prints ({'all ' + format(n, ',') if not over else '20,000 of ' + format(n, ',')})",
                                   customdata=csz[ii],
                                   hovertemplate="%{x|%H:%M:%S}<br>%{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>"),
                      row=1, col=1)

        dt = np.diff(cts).astype(np.float64) / 1e9
        gs = max(1, dt.size // 40000)
        gt = ns_to_et(cts[1:][::gs])
        fig.add_trace(go.Scattergl(x=gt, y=np.maximum(dt[::gs], 1e-12), mode="markers",
                                   marker=dict(size=2.5, color="#1b1b1a", opacity=0.4),
                                   name="inter-trade time", showlegend=False), row=2, col=1)
        # norm/mid come from the D1-aggregated series (compute_event), a different
        # length than the raw tie-collapsed cts/dt above -- plotted on its own time axis
        gs2 = max(1, mid.size // 40000)
        fig.add_trace(go.Scattergl(x=ns_to_et(mid[::gs2].astype(np.int64)), y=norm[::gs2],
                                   mode="markers", marker=dict(size=2.5, color=C.ARM_A, opacity=0.4),
                                   name="normalized log10 interval", showlegend=False), row=3, col=1)
        if thr_norm is not None:
            fig.add_hline(y=thr_norm, line=dict(color="#b03a3a", width=2),
                         annotation_text=f"threshold {thr_norm:+.2f}", annotation_position="right",
                         annotation_font=dict(size=10, color="#b03a3a"), row=3, col=1)

        zoom_note = "no sub-bursts to zoom on"
        zoom_titles = {}
        if iv:
            starts = np.array([a for a, _ in iv], dtype=np.int64)
            binw = int(ZOOM_WIDE_S * 1e9)
            b0 = (starts - starts.min()) // binw
            dense_bin = np.bincount(b0).argmax()
            c_ns = int(starts.min() + dense_bin * binw + binw // 2)
            typ = sbs[sbs.duration_s <= 1e-3]
            big = (typ.iloc[int(np.argmax(typ.n_prints.to_numpy()))] if len(typ)
                  else sbs.iloc[int(np.argmax(sbs.n_prints.to_numpy()))])
            big_c = int((big.start_ns + big.end_ns) // 2)
            big_w = max(ZOOM_TIGHT_MIN_S, 20 * float(big.duration_s))
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
                     f"sub-bursts in view (n={len(sub_iv)})", ri == 4, clip=(a_ns, b_ns))
                zms = 6 + 9 * (np.log10(np.maximum(csz[m], 1)) / max(np.log10(max(csz.max(), 10)), 1))
                fig.add_trace(go.Scattergl(
                    x=ns_to_et(cts[m]), y=pxv[m], mode="markers",
                    marker=dict(size=zms, color="#1b1b1a", opacity=0.8),
                    name=f"prints in view ({int(m.sum()):,})", showlegend=(ri == 4),
                    customdata=csz[m],
                    hovertemplate="%{x|%H:%M:%S.%L}<br>%{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>"),
                    row=ri, col=1)
                fig.update_yaxes(title_text="price", range=[zl - zp, zh + zp], row=ri, col=1)
                fig.update_xaxes(
                    range=[pd.Timestamp(ns_to_et([a_ns]).iloc[0]),
                          pd.Timestamp(ns_to_et([b_ns]).iloc[0])],
                    title_text=None, row=ri, col=1)
                span_txt = (f"{wid*1e3:,.3g} ms" if wid >= 1e-3 else f"{wid*1e6:,.3g} us")
                zoom_titles[ri] = (
                    f"ZOOM -- {'densest sub-burst region' if lab == 'wide' else 'typical busy sub-burst'}"
                    f" - {span_txt} span - {int(m.sum()):,} prints - {len(sub_iv)} sub-burst(s)"
                    " - shaded to true extent")
            zoom_note = (f"wide zoom spans {ZOOM_WIDE_S:g} s on the densest region; tight zoom spans "
                        f"{big_w*1e6:,.1f} us on a typical busy sub-burst "
                        f"({float(big.duration_s)*1e9:,.0f} ns, {int(big.n_prints)} prints)")
        for ri, txt in zoom_titles.items():
            fig.layout.annotations[ri - 1].update(text=txt)

        fig.update_yaxes(title_text="price", range=[lo, hi], row=1, col=1)
        fig.update_yaxes(title_text="inter-trade s (log)", type="log", row=2, col=1)
        fig.update_yaxes(title_text="normalized log10", row=3, col=1)
        for rr in (1, 2, 3):
            fig.update_xaxes(title_text=None, row=rr, col=1)

        lbl = "" if r.cohort_group == "dev_v4_primary" else \
            f" -- <span style='color:#b03a3a'>{r.cohort_group.upper()}</span>"
        C.finish(fig, f"07 -- {r.ticker} {r.event_date_canonical} ({r.momentum_pct:.2f}%){lbl}",
                f"{n:,} raw prints - segment {seg} - label {label} - "
                + (f"void {void:.3f}, threshold {thr_norm:+.2f} - {len(iv)} sub-bursts"
                   if thr_norm is not None else "no threshold at this reference cell"),
                C.caption(f"one event: {r.ticker} {r.event_date_canonical}",
                         f"reference cell kernel={REF_KERNEL:g}min thr={REF_VARIANT:g} "
                         "(other kernels/variants in s1_t1_cells.parquet, not replotted here)",
                         chash,
                         "<b>Scale:</b> sub-burst durations here run ms-to-s (not v4's 348ns) but "
                         "are still typically sub-pixel against an hours-long session axis, so "
                         "panel 1 marks LOCATIONS as ticks; only the zoom panels show true extent. "
                         + zoom_note + ("<br><b>Reads:</b> Row 0 -- Cooper's alone. This script "
                         "describes, it does not evaluate.")),
                height=1560, width=1560)
        name = f"{r.ticker}_{r.event_date_canonical}"
        p = os.path.join(OUT_SUB, f"{name}.html")
        fig.write_html(p, include_plotlyjs="cdn", full_html=True,
                      config={"displaylogo": False, "responsive": True})
        png = os.path.join(OUT_SUB, f"{name}.png")
        fig.write_image(png, scale=2)  # Chart Contract: Kaleido-verified before commit
        kaleido_ok = os.path.exists(png) and os.path.getsize(png) > 5000
        rows.append({"file": f"{name}.html", "ticker": r.ticker,
                    "event_date_canonical": r.event_date_canonical,
                    "cohort_group": r.cohort_group, "segment": str(seg), "label": str(label),
                    "n_subbursts": int(len(iv)), "bytes": os.path.getsize(p),
                    "kaleido_verified": bool(kaleido_ok),
                    "png_bytes": os.path.getsize(png) if kaleido_ok else 0})
        if i % 10 == 0:
            print(f"  {i}/{len(dev)} charts", flush=True)

    hdr = ["ticker", "event_date_canonical", "cohort_group", "segment", "label", "n_subbursts", "chart"]
    body_rows = [{**r, "chart": f'<a href="{r["file"]}">open</a>'} for r in rows]
    body = "\n".join("<tr>" + "".join(
        f"<td data-v='{html.escape(str(x[h]))}'>{x[h] if h == 'chart' else html.escape(str(x[h]))}</td>"
        for h in hdr) + "</tr>" for x in body_rows)
    head = "".join(f"<th onclick='S({i})'>{h}</th>" for i, h in enumerate(hdr))
    doc = f"""<!doctype html><meta charset="utf-8"><title>Phase 10c Stage 1 -- T7 tape review index</title>
<style>body{{font:14px/1.5 Inter,Segoe UI,system-ui,sans-serif;color:#0b0b0b;background:#fcfcfb;margin:28px}}
h1{{font-size:19px;margin:0 0 4px}}p{{color:#52514e;margin:0 0 16px;max-width:82ch}}
table{{border-collapse:collapse;font-size:13px}}th,td{{padding:5px 11px;border-bottom:1px solid #e2e2df;text-align:left}}
th{{cursor:pointer;background:#f2f2ef;position:sticky;top:0}}tr:hover td{{background:#f7f7f4}}
a{{color:#2a78d6}}</style>
<h1>Phase 10c Stage 1 -- T7 tape review index</h1>
<p>All {len(rows)} dev-sample events, reference cell kernel={REF_KERNEL:g}min / threshold={REF_VARIANT:g}.
Row 0 -- Cooper's alone, overrides every numeric row in either direction. This index and the charts
describe; nothing here is evaluated. <b>config_hash:</b> {chash}</p>
<table><thead><tr>{head}</tr></thead><tbody id=b>{body}</tbody></table>
<script>let d={{}};function S(i){{const t=document.getElementById('b');const r=[...t.rows];
d[i]=!d[i];const num=[5].includes(i);r.sort((a,b)=>{{let x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;
if(num){{x=parseFloat(x)||-1;y=parseFloat(y)||-1;return d[i]?x-y:y-x}}
return d[i]?x.localeCompare(y):y.localeCompare(x)}});r.forEach(x=>t.appendChild(x))}}</script>"""
    with open(os.path.join(OUT_SUB, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)

    n_verified = sum(1 for r in rows if r.get("kaleido_verified"))
    c10c.write_json(rel(f"{ART}/s1_t7_tape_manifest.json"), {
        "phase": "10c", "stage": "1", "task": "T7a_tape_review", "config_hash": chash,
        "reference_cell": {"kernel_min": REF_KERNEL, "threshold": REF_VARIANT},
        "n_charts": len(rows), "index_path": f"{OUT_SUB}/index.html",
        "total_megabytes": round(sum(x["bytes"] for x in rows) / 1e6, 1),
        "n_kaleido_verified": n_verified,
        "evaluated": False, "note": "Row 0 is Cooper's. This manifest describes; it evaluates nothing.",
        "charts": rows, "source": "research/phase_10c/s1_t7_tape_review.py:main"})

    print(f"\nwrote {len(rows)} tape-review charts, {sum(x['bytes'] for x in rows)/1e6:.0f} MB, "
         f"kaleido {n_verified}/{len(rows)}")
    print(f"index: {OUT_SUB}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
