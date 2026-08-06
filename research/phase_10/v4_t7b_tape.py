"""
Phase 10 v4 chart 06 -- per-event tape review. THE GATE. Produced even though
rows 1 and 6 fired.

Three panels, shared time axis:
  top     prints, price, marker size by share count, sub-burst intervals shaded
  middle  inter-trade time, log, with the per-event threshold as a horizontal rule
  bottom  normalized log interval with the same threshold

Selection puts every `no_threshold` event first -- those are the most
informative charts in the set because they show what the method could not handle.

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
    COHORT_KEY, POOLED, collapse_ties, load_frozen_cohort, read_event_trades, rel,
    session_window, write_json,
)
from v4_pipeline import cfg_hash, load_cfg, moving_median_log  # noqa: E402

SUB = "v4_06_tape_review"


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

    nt = co[co["status"] == "no_threshold"]                      # first: what failed
    prim = co[(co["cohort_group"] == "dev_v4_primary") & (co["status"] != "no_threshold")]
    rest = co[~co.set_index(COHORT_KEY).index.isin(
        pd.concat([nt, prim]).set_index(COHORT_KEY).index)].sort_values(
        ["segment", "n_sub"] + COHORT_KEY)
    room = max(0, c6["max_charts"] - len(nt) - len(prim))
    extra = (rest.iloc[np.linspace(0, len(rest) - 1, min(room, len(rest))).round().astype(int)]
             if room > 0 and len(rest) else rest.head(0))
    sel = pd.concat([nt, prim, extra], ignore_index=True).drop_duplicates(subset=COHORT_KEY)
    if len(sel) > c6["max_charts"]:
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

        over = n > c6["max_scatter_points"]
        ii = (np.sort(np.random.default_rng(c6["over_cap_seed"]).choice(
            n, c6["max_scatter_points"], replace=False)) if over else np.arange(n))
        et = ns_to_et(cts[ii])

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                            row_heights=[0.42, 0.30, 0.28],
                            subplot_titles=[
                                "Trade prints — price (marker size = share count); sub-bursts shaded",
                                "Inter-trade time, log, with the per-event threshold",
                                "Normalized log10 interval, with the same threshold"])
        ymin, ymax = float(pxv.min()), float(pxv.max())
        pad = (ymax - ymin) * 0.06 or 0.01
        lo, hi = ymin - pad, ymax + pad
        sbs = sb[(sb["ticker"] == r.ticker) & (sb["event_date_canonical"] == r.event_date_canonical)
                 & (np.isclose(sb["momentum_pct"], r.momentum_pct))]
        bx, by = [], []
        for s in sbs.itertuples(index=False):
            a = pd.Timestamp(ns_to_et([s.start_ns]).iloc[0]); b = pd.Timestamp(ns_to_et([s.end_ns]).iloc[0])
            bx += [a, b, b, a, a, None]; by += [lo, lo, hi, hi, lo, None]
        if bx:
            fig.add_trace(go.Scatter(x=bx, y=by, fill="toself", mode="lines",
                                     fillcolor="rgba(42,120,214,0.30)", line=dict(width=0),
                                     name=f"sub-bursts (n={len(sbs)})", hoverinfo="skip"),
                          row=1, col=1)
        ms = 4 + 9 * (np.log10(np.maximum(csz[ii], 1)) / max(np.log10(max(csz.max(), 10)), 1))
        fig.add_trace(go.Scattergl(x=et, y=pxv[ii], mode="markers",
                                   marker=dict(size=ms, color="#1b1b1a", opacity=0.55),
                                   name=f"prints ({'all ' + format(n, ',') if not over else format(c6['max_scatter_points'], ',') + f' of {n:,}'})",
                                   customdata=csz[ii],
                                   hovertemplate="%{x|%H:%M:%S}<br>%{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>"),
                      row=1, col=1)
        gs = max(1, dt.size // 40000)
        gt = ns_to_et(cts[1:][::gs])
        fig.add_trace(go.Scattergl(x=gt, y=dt[::gs], mode="markers",
                                   marker=dict(size=2.5, color="#1b1b1a", opacity=0.4),
                                   name="inter-trade time"), row=2, col=1)
        fig.add_trace(go.Scattergl(x=gt, y=yn[::gs], mode="markers",
                                   marker=dict(size=2.5, color=C.ARM_A, opacity=0.4),
                                   name="normalized log10 interval"), row=3, col=1)
        if thr is not None:
            fig.add_hline(y=thr, line=dict(color="#b03a3a", width=2),
                          annotation_text=f"threshold {thr:+.2f} decades",
                          annotation_position="right",
                          annotation_font=dict(size=10, color="#b03a3a"), row=3, col=1)
        for ns_, col, lab in ((det_ns, "#b03a3a", "detection (D7)"),
                              (int(pk_ns) if pk_ns is not None and pd.notna(pk_ns) else None,
                               "#008300", "peak (retrospective)")):
            if ns_ is None:
                continue
            x = pd.Timestamp(ns_to_et([ns_]).iloc[0])
            for rr in (1, 2, 3):
                fig.add_vline(x=x, line=dict(color=col, width=1.8, dash="dash"), row=rr, col=1)
            fig.add_annotation(x=x, y=1.0, yref="paper", text=lab, showarrow=False,
                               font=dict(size=10, color=col), xanchor="left", xshift=4)
        fig.update_yaxes(title_text="price", range=[lo, hi], row=1, col=1)
        fig.update_yaxes(title_text="inter-trade s (log)", type="log", row=2, col=1)
        fig.update_yaxes(title_text="normalized log10 interval", row=3, col=1)
        fig.update_xaxes(title_text="America/New_York (04:00–20:00)", row=3, col=1)
        st = (e["status"] if e is not None else "n/a")
        lbl = "" if r.cohort_group in ("dev_v4_primary", "activity_extension") else \
            f" — <span style='color:#b03a3a'>{r.cohort_group.upper()}</span>"
        nolbl = " — <span style='color:#b03a3a'>NO THRESHOLD</span>" if st == "no_threshold" else ""
        C.finish(fig, f"06 — {r.ticker} {r.event_date_canonical} ({r.momentum_pct:.2f}%){lbl}{nolbl}",
                 f"{n:,} collapsed arrivals · segment {r.segment} · status {st} · "
                 + (f"void {e['void']:.3f}, threshold {thr:+.2f} decades · {len(sbs)} sub-bursts"
                    if thr is not None else "no threshold derived — no sub-bursts declared"),
                 C.caption(f"one event: {r.ticker} {r.event_date_canonical}",
                           f"T=0 only; tie={tie_ref}, window={wref:.0%}, min_prints={mref}", chash,
                           ("all arrivals plotted" if not over else
                            f"top panel: seeded uniform subsample {c6['max_scatter_points']/n:.1%}")
                           + ". Sub-burst intervals come from the full-resolution computation."
                           "<br><b>Reads:</b> shaded intervals not matching visible density changes "
                           "on the tape mean the decomposition does not correspond to what happened."),
                 height=1050, width=1560)
        name = f"{r.ticker}_{r.event_date_canonical}"
        p = os.path.join(out_dir, f"{name}.html")
        fig.write_html(p, include_plotlyjs="cdn", full_html=True,
                       config={"displaylogo": False, "responsive": True})
        rows.append({"file": f"{name}.html", "ticker": r.ticker,
                     "event_date_canonical": r.event_date_canonical,
                     "cohort_group": r.cohort_group, "segment": str(r.segment),
                     "status": str(st), "n_subbursts": int(len(sbs)),
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
        recs.append({"ticker": r.ticker, "date": r.event_date_canonical,
                     "group": r.cohort_group,
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
h1{{font-size:19px;margin:0 0 4px}}p{{color:#52514e;margin:0 0 16px;max-width:80ch}}
table{{border-collapse:collapse;font-size:13px}}th,td{{padding:5px 11px;border-bottom:1px solid #e2e2df;text-align:left}}
th{{cursor:pointer;background:#f2f2ef;position:sticky;top:0}}tr:hover td{{background:#f7f7f4}}
.no{{color:#8a8a84}}a{{color:#2a78d6}}</style>
<h1>Phase 10 v4 — chart 06 tape review index</h1>
<p>All {len(recs)} cohort events. Chart coverage capped at {c6['max_charts']}; index coverage is
complete per §7. Produced under the failure (rows 1, 6). Every <code>no_threshold</code> event is
charted first — those show what the method could not handle. <b>config_hash:</b> {chash}</p>
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
                "produced_under_failure": True, "charts": rows,
                "source": "research/phase_10/v4_t7b_tape.py:main"})
    print(f"  wrote {len(rows)} charts, {sum(x['bytes'] for x in rows)/1e6:.0f} MB; "
          f"index {len(recs)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
