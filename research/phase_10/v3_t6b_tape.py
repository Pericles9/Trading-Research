"""
Phase 10 v3 chart 07 -- the per-event tape review. THE GATE.

Produced even though rows 2, 3 and 4 fired. v2 skipped its chart 07 on the
reasoning that acceptance was off the table; that removed the only means of
judging WHY the measurement failed. The v3 prompt reverses that explicitly.

Three panels per event on a shared time axis:
  top     trade prints, price, marker size by share count, sub-burst intervals shaded
  middle  fast rate and the gate-derived envelope, log, both observables
  bottom  inter-trade time, log (diagnostic display axis only -- Phase 13 owns
          interval distributions)
Detection and peak marked on all three.

Usage: .venv/Scripts/python.exe research/phase_10/v3_t6b_tape.py
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
    COHORT_KEY, POOLED, knn_rate, load_frozen_cohort, read_event_trades,
    rel, session_window, write_json,
)
from v3_t1_gate import cfg_hash, load_cfg  # noqa: E402

SUB = "v3_07_tape_review"
OBS_COL = {"print_rate": C.ARM_A, "volume_rate": C.ARM_B}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out_dir = os.path.join(rel(cfg["paths"]["out_charts"]), SUB)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("# Phase 10 v3 chart 07: per-event tape review HTML, regenerable\n"
                "# from committed config + code (Agent_Prompt_Standard §12).\n*\n")

    c7 = cfg["charts"]["chart_07"]
    cohort = load_frozen_cohort({"paths": {"cohort_manifest": cfg["paths"]["cohort_manifest"]},
                                 "cohort": {"content_hash": cfg["cohort"]["content_hash"]}})
    ev = pd.read_parquet(os.path.join(art, "v3_t3_event_metrics.parquet"))
    sub = pd.read_parquet(os.path.join(art, "v3_t3_subbursts.parquet"))
    for d in (ev, sub):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    ev["ok"] = ev["ok"].fillna(False).astype(bool)
    det = pd.read_parquet(rel(cfg["paths"]["detection"]))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], cfg["detection_anchor"]["threshold"])].set_index(COHORT_KEY)
    v2m = pd.read_parquet(rel(cfg["paths"]["v2_event_metrics"]))
    v2m["event_date_canonical"] = v2m["event_date_canonical"].astype(str)
    v2m = v2m[(v2m["tie_variant"] == "as_is") & (v2m["k"] == cfg["envelope"]["fast_k"])
              & (v2m["observable"] == "print_rate")].set_index(COHORT_KEY)["peak_ns"]

    pe = ev[(ev["observable"] == "print_rate") & ev["ok"]].set_index(COHORT_KEY)
    co = cohort.copy()
    co["n_sub"] = pe["n_subbursts"].reindex(pd.MultiIndex.from_frame(co[COHORT_KEY])).to_numpy()
    co["segment"] = pe["segment"].reindex(pd.MultiIndex.from_frame(co[COHORT_KEY])).to_numpy()

    always = co[co["cohort_group"] == "dev_v4_primary"]
    rest = co[co["cohort_group"] != "dev_v4_primary"].sort_values(["segment", "n_sub"] + COHORT_KEY)
    take = []
    for _, g in rest.groupby("segment", dropna=False):
        g = g.reset_index(drop=True)
        idx = sorted(set([0, len(g) // 4, len(g) // 2, 3 * len(g) // 4, len(g) - 1]))
        take.append(g.iloc[[i for i in idx if 0 <= i < len(g)]])
    extra = (pd.concat(take, ignore_index=True).drop_duplicates(subset=COHORT_KEY)
             if take else pd.DataFrame(columns=always.columns))
    extra = extra[~extra.set_index(COHORT_KEY).index.isin(always.set_index(COHORT_KEY).index)]
    # Respect the pre-registered cap by TRIMMING the stratified draw, never by
    # raising the cap. dev_v4_primary is kept whole (selection rule); the draw is
    # sorted by (segment, sub-burst count, key) so the trim is deterministic and
    # still spans the count range within each segment.
    room = max(0, c7["max_charts"] - len(always))
    if len(extra) > room:
        extra = extra.sort_values(["segment", "n_sub"] + COHORT_KEY).iloc[
            np.linspace(0, len(extra) - 1, room).round().astype(int)]
    sel = pd.concat([always, extra], ignore_index=True).drop_duplicates(subset=COHORT_KEY)
    if len(sel) > c7["max_charts"]:
        print(f"ESCALATION: selection {len(sel)} > cap {c7['max_charts']}")
        return 6
    print(f"chart 07: {len(sel)} events selected (cap {c7['max_charts']})")

    rows = []
    for i, r in enumerate(sel.itertuples(index=False), 1):
        w = session_window(r.event_date_canonical, 0)
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts = t0["sip_timestamp"].to_numpy()
        px = t0["price"].to_numpy(dtype=float)
        sz = t0["size"].to_numpy(dtype=float)
        n = ts.size
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        erow = pe.loc[key] if key in pe.index else None
        if isinstance(erow, pd.DataFrame):
            erow = erow.iloc[0]
        drow = det.loc[key] if key in det.index else None
        if isinstance(drow, pd.DataFrame):
            drow = drow.iloc[0]
        det_ns = int(drow["det_ns_poll1"]) if drow is not None and pd.notna(drow["det_ns_poll1"]) else None
        pk_ns = v2m.get(key)

        over = n > c7["max_scatter_points"]
        idx = (np.sort(np.random.default_rng(c7["over_cap_seed"]).choice(
            n, c7["max_scatter_points"], replace=False)) if over else np.arange(n))
        et = ns_to_et(ts[idx])

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                            row_heights=[0.42, 0.32, 0.26],
                            subplot_titles=[
                                "Trade prints — price (marker size = share count); sub-burst intervals shaded",
                                "Fast rate (k=50) and gate-derived envelope, log",
                                "Inter-trade time, log (diagnostic axis only)"])
        ymin, ymax = float(px.min()), float(px.max())
        pad = (ymax - ymin) * 0.06 or 0.01
        lo, hi = ymin - pad, ymax + pad
        sbs = sub[(sub["observable"] == "print_rate") & (sub["ticker"] == r.ticker)
                  & (sub["event_date_canonical"] == r.event_date_canonical)
                  & (np.isclose(sub["momentum_pct"], r.momentum_pct))]
        bx, by = [], []
        for s in sbs.itertuples(index=False):
            a = pd.Timestamp(ns_to_et([s.start_ns]).iloc[0]); b = pd.Timestamp(ns_to_et([s.end_ns]).iloc[0])
            bx += [a, b, b, a, a, None]; by += [lo, lo, hi, hi, lo, None]
        if bx:
            fig.add_trace(go.Scatter(x=bx, y=by, fill="toself", mode="lines",
                                     fillcolor="rgba(42,120,214,0.16)", line=dict(width=0),
                                     name=f"sub-bursts, print rate (n={len(sbs)})",
                                     hoverinfo="skip"), row=1, col=1)
        ms = 4 + 9 * (np.log10(np.maximum(sz[idx], 1)) / max(np.log10(max(sz.max(), 10)), 1))
        fig.add_trace(go.Scattergl(x=et, y=px[idx], mode="markers",
                                   marker=dict(size=ms, color="#1b1b1a", opacity=0.55),
                                   name=f"prints ({'all ' + format(n, ',') if not over else format(c7['max_scatter_points'], ',') + f' of {n:,}'})",
                                   customdata=sz[idx],
                                   hovertemplate="%{x|%H:%M:%S}<br>%{y:,.4f}<br>size %{customdata:,.0f}<extra></extra>"),
                      row=1, col=1)

        step = max(1, n // 40000)
        for obs in ("print_rate", "volume_rate"):
            ke = int(erow["k_env"]) if erow is not None and pd.notna(erow["k_env"]) else 200
            if n <= max(ke, cfg["envelope"]["fast_k"]):
                continue
            f = knn_rate(ts, sz, cfg["envelope"]["fast_k"], 1e-9)[obs]
            e = knn_rate(ts, sz, ke, 1e-9)[obs]
            ets = ns_to_et(ts[::step])
            fig.add_trace(go.Scattergl(x=ets, y=f[::step], mode="lines",
                                       line=dict(color=OBS_COL[obs], width=0.7),
                                       opacity=0.45, name=f"{obs} fast"), row=2, col=1)
            fig.add_trace(go.Scattergl(x=ets, y=e[::step], mode="lines",
                                       line=dict(color=OBS_COL[obs], width=2.2),
                                       name=f"{obs} envelope"), row=2, col=1)
        gaps = np.maximum(np.diff(ts) / 1e9, 1e-6)
        gs = max(1, (n - 1) // 40000)
        fig.add_trace(go.Scattergl(x=ns_to_et(ts[1:][::gs]), y=gaps[::gs], mode="markers",
                                   marker=dict(size=2.5, color="#1b1b1a", opacity=0.4),
                                   name="inter-trade time"), row=3, col=1)

        for ns_, col, lab in ((det_ns, "#b03a3a", "detection (D7, 1s poll)"),
                              (int(pk_ns) if pk_ns is not None and pd.notna(pk_ns) else None,
                               "#008300", "peak intensity (retrospective)")):
            if ns_ is None:
                continue
            x = pd.Timestamp(ns_to_et([ns_]).iloc[0])
            for rr in (1, 2, 3):
                fig.add_vline(x=x, line=dict(color=col, width=1.8, dash="dash"), row=rr, col=1)
            fig.add_annotation(x=x, y=1.0, yref="paper", text=lab, showarrow=False,
                               font=dict(size=10, color=col), xanchor="left", xshift=4)

        fig.update_yaxes(title_text="price", range=[lo, hi], row=1, col=1)
        fig.update_yaxes(title_text="rate (log)", type="log", row=2, col=1)
        fig.update_yaxes(title_text="inter-trade s (log)", type="log", row=3, col=1)
        fig.update_xaxes(title_text="America/New_York (04:00–20:00)", row=3, col=1)
        lbl = "" if r.cohort_group in ("dev_v4_primary", "activity_extension") else \
            f" — <span style='color:#b03a3a'>{r.cohort_group.upper()}</span>"
        C.finish(fig, f"07 — {r.ticker} {r.event_date_canonical} ({r.momentum_pct:.2f}%){lbl}",
                 f"{n:,} T=0 prints · segment {erow['segment'] if erow is not None else 'n/a'} · "
                 + (f"knee {erow['knee_seconds']:g}s · k_env "
                    f"{int(erow['k_env']) if pd.notna(erow['k_env']) else 'n/a'} · "
                    if erow is not None else "no envelope (event not decomposed) · ")
                 + f"{len(sbs)} sub-bursts (print rate)",
                 C.caption(f"one event: {r.ticker} {r.event_date_canonical}, {n:,} in-window prints",
                           "T=0 only; sub-bursts are excursions of rate/envelope, gate-derived knee",
                           chash,
                           ("all prints plotted" if not over else
                            f"top panel: seeded uniform subsample {c7['max_scatter_points']/n:.1%} — "
                            "uniform sampling preserves relative density") +
                           ". Sub-burst intervals always come from the full-resolution computation."
                           "<br><b>Reads:</b> shaded intervals not matching visible density changes, "
                           "or an obviously wrong envelope, mean the decomposition does not "
                           "correspond to the tape."),
                 height=1050, width=1560)
        name = f"{r.ticker}_{r.event_date_canonical}"
        p = os.path.join(out_dir, f"{name}.html")
        fig.write_html(p, include_plotlyjs="cdn", full_html=True,
                       config={"displaylogo": False, "responsive": True})
        rows.append({"file": f"{name}.html", "ticker": r.ticker,
                     "event_date_canonical": r.event_date_canonical,
                     "cohort_group": r.cohort_group,
                     "segment": str(erow["segment"]) if erow is not None else None,
                     "n_prints_t0": int(n), "n_subbursts": int(len(sbs)),
                     "bytes": os.path.getsize(p)})
        if i % 10 == 0:
            print(f"  {i}/{len(sel)} charts", flush=True)

    by = {(x["ticker"], x["event_date_canonical"]): x for x in rows}
    recs = []
    for r in cohort.itertuples(index=False):
        m = by.get((r.ticker, r.event_date_canonical))
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        e = pe.loc[key] if key in pe.index else None
        if isinstance(e, pd.DataFrame):
            e = e.iloc[0]
        recs.append({"ticker": r.ticker, "date": r.event_date_canonical,
                     "group": r.cohort_group,
                     "segment": str(e["segment"]) if e is not None else "",
                     "t0_prints": int(r.t0_print_count),
                     "subbursts": int(e["n_subbursts"]) if e is not None else "",
                     "chart": f'<a href="{m["file"]}">open</a>' if m else "<span class=no>not charted</span>"})
    hdr = ["ticker", "date", "group", "segment", "t0_prints", "subbursts", "chart"]
    body = "\n".join("<tr>" + "".join(
        f"<td data-v='{html.escape(str(x[h]))}'>{x[h] if h == 'chart' else html.escape(str(x[h]))}</td>"
        for h in hdr) + "</tr>" for x in recs)
    head = "".join(f"<th onclick='S({i})'>{h}</th>" for i, h in enumerate(hdr))
    doc = f"""<!doctype html><meta charset="utf-8"><title>Phase 10 v3 — chart 07 index</title>
<style>body{{font:14px/1.5 Inter,Segoe UI,system-ui,sans-serif;color:#0b0b0b;background:#fcfcfb;margin:28px}}
h1{{font-size:19px;margin:0 0 4px}}p{{color:#52514e;margin:0 0 16px;max-width:78ch}}
table{{border-collapse:collapse;font-size:13px}}th,td{{padding:5px 11px;border-bottom:1px solid #e2e2df;text-align:left}}
th{{cursor:pointer;background:#f2f2ef;position:sticky;top:0}}tr:hover td{{background:#f7f7f4}}
.no{{color:#8a8a84}}a{{color:#2a78d6}}</style>
<h1>Phase 10 v3 — chart 07 tape review index</h1>
<p>All {len(recs)} cohort events. Chart coverage capped at {c7['max_charts']}; index coverage is
complete per Agent_Prompt_Standard §7. Produced under the partial failure (rows 2, 3, 4) — the v3
prompt requires chart 07 regardless, so the failure can be judged rather than only counted.
<b>config_hash:</b> {chash}</p>
<table><thead><tr>{head}</tr></thead><tbody id=b>{body}</tbody></table>
<script>let d={{}};function S(i){{const t=document.getElementById('b');const r=[...t.rows];
d[i]=!d[i];const num=[4,5].includes(i);r.sort((a,b)=>{{let x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;
if(num){{x=parseFloat(x)||-1;y=parseFloat(y)||-1;return d[i]?x-y:y-x}}
return d[i]?x.localeCompare(y):y.localeCompare(x)}});r.forEach(x=>t.appendChild(x))}}</script>"""
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)

    write_json(os.path.join(art, "v3_t6b_tape_manifest.json"),
               {"phase": "10", "version": "v3", "task": "T6b", "config_hash": chash,
                "n_charts": len(rows), "cap": c7["max_charts"],
                "index_n_rows": len(recs), "index_covers_full_cohort": True,
                "total_megabytes": round(sum(x["bytes"] for x in rows) / 1e6, 1),
                "produced_under_failure": True, "charts": rows,
                "source": "research/phase_10/v3_t6b_tape.py:main"})
    print(f"  wrote {len(rows)} charts, {sum(x['bytes'] for x in rows)/1e6:.0f} MB; "
          f"index {len(recs)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
