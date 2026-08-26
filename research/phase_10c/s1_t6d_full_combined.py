"""
Phase 10c Stage 1, T6d -- full 56-event dev sample, COMBINED comparative layout
(Cooper's choice, T6c). One file per event, 3 synced panels (kernel=2/8/32min side
by side, same time slider), each frame a real recomputation over its own window.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t6d_full_combined.py
"""
from __future__ import annotations

import html
import importlib.util as ilu
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
_s6 = ilu.spec_from_file_location("s1t6", os.path.join(HERE, "s1_t6_animation.py"))
s1t6 = ilu.module_from_spec(_s6); _s6.loader.exec_module(s1t6)

ART = "results/phase_10c/artifacts"
OUT_SUB = "results/phase_10c/charts/s1_06_animation_full"
KERNELS = s1t6.KERNELS


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))
    F = float(c10c.class_m(cfg)["D4_median_precision_factor"])

    os.makedirs(OUT_SUB, exist_ok=True)
    with open(os.path.join(OUT_SUB, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("# Stage 1 T6d combined animations: regenerable.\n*\n")

    seg_by_125 = cells[(cells.kernel_min == 8.0) & (cells.threshold.round(2) == 1.25)] \
        .set_index(["ticker", "event_date_canonical"]).segment

    rows = []
    for i, r in enumerate(dev.itertuples(index=False), 1):
        try:
            evs_by_kernel = {k: s1t6.compute_event(cfg, r.ticker, r.event_date_canonical,
                                                   r.momentum_pct, k, F) for k in KERNELS}
        except Exception as e:
            print(f"  SKIP {r.ticker} {r.event_date_canonical}: {e}")
            continue
        seg = seg_by_125.get((r.ticker, r.event_date_canonical), None)
        note = f"segment={seg}" if seg else "unlabelled at thr=1.25"
        fig = s1t6.make_combined_animation(evs_by_kernel, r.ticker, r.event_date_canonical,
                                           note, chash)
        name = f"{r.ticker}_{r.event_date_canonical}"
        p = os.path.join(OUT_SUB, f"{name}.html")
        fig.write_html(p, include_plotlyjs="cdn", full_html=True,
                      config={"displaylogo": False, "responsive": True})
        labels = {k: evs_by_kernel[k].get("label", "n/a") for k in KERNELS}
        rows.append({"file": f"{name}.html", "ticker": r.ticker,
                    "event_date_canonical": r.event_date_canonical,
                    "cohort_group": r.cohort_group, "segment": str(seg),
                    "label_k2": labels[2.0], "label_k8": labels[8.0], "label_k32": labels[32.0],
                    "bytes": os.path.getsize(p)})
        if i % 10 == 0:
            print(f"  {i}/{len(dev)}", flush=True)

    hdr = ["ticker", "event_date_canonical", "cohort_group", "segment",
          "label_k2", "label_k8", "label_k32", "chart"]
    body_rows = [{**r, "chart": f'<a href="{r["file"]}">open</a>'} for r in rows]
    body = "\n".join("<tr>" + "".join(
        f"<td data-v='{html.escape(str(x[h]))}'>{x[h] if h == 'chart' else html.escape(str(x[h]))}</td>"
        for h in hdr) + "</tr>" for x in body_rows)
    head = "".join(f"<th onclick='S({i})'>{h}</th>" for i, h in enumerate(hdr))
    doc = f"""<!doctype html><meta charset="utf-8"><title>Phase 10c Stage 1 -- T6d combined animation index</title>
<style>body{{font:14px/1.5 Inter,Segoe UI,system-ui,sans-serif;color:#0b0b0b;background:#fcfcfb;margin:28px}}
h1{{font-size:19px;margin:0 0 4px}}p{{color:#52514e;margin:0 0 16px;max-width:82ch}}
table{{border-collapse:collapse;font-size:13px}}th,td{{padding:5px 11px;border-bottom:1px solid #e2e2df;text-align:left}}
th{{cursor:pointer;background:#f2f2ef;position:sticky;top:0}}tr:hover td{{background:#f7f7f4}}
a{{color:#2a78d6}}</style>
<h1>Phase 10c Stage 1 -- T6d combined animation index</h1>
<p>All {len(rows)} dev-sample events, combined comparative layout (Cooper's T6c choice): 3 synced
panels, kernel=2/8/32min, same time slider per event. Each frame is a real recomputation over its
own window, not an interpolation. <b>config_hash:</b> {chash}</p>
<table><thead><tr>{head}</tr></thead><tbody id=b>{body}</tbody></table>
<script>let d={{}};function S(i){{const t=document.getElementById('b');const r=[...t.rows];
d[i]=!d[i];r.sort((a,b)=>{{let x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;
return d[i]?x.localeCompare(y):y.localeCompare(x)}});r.forEach(x=>t.appendChild(x))}}</script>"""
    with open(os.path.join(OUT_SUB, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)

    c10c.write_json(rel(f"{ART}/s1_t6d_manifest.json"), {
        "phase": "10c", "stage": "1", "task": "T6d_full_combined_animation", "config_hash": chash,
        "layout": "combined_comparative_3_panel", "layout_chosen_by": "Cooper (T6c)",
        "n_events": len(rows), "index_path": f"{OUT_SUB}/index.html",
        "total_megabytes": round(sum(x["bytes"] for x in rows) / 1e6, 1),
        "charts": rows, "source": "research/phase_10c/s1_t6d_full_combined.py:main"})
    print(f"\nwrote {len(rows)} combined animations, {sum(x['bytes'] for x in rows)/1e6:.0f} MB")
    print(f"index: {OUT_SUB}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
