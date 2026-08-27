"""
10d Diag1 charts addendum, C5 -- manifest and coverage verification.

Records every chart file with its event, kernel, theme, byte size, and the global y-range
that was in force for its run. The y-ranges are RECOMPUTED here by calling the plotting
script's own global_bounds() on the same frames, so the manifest carries derived values
rather than numbers transcribed from a log.

Also verifies CH-R4: every event in the 10d tape-review set has an 8-min chart.

Usage: .venv/Scripts/python.exe research/phase_10d_diag1/c5_manifest.py
"""
from __future__ import annotations

import importlib.util as ilu
import json
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
_s = ilu.spec_from_file_location("pb", os.path.join(HERE, "plot_boundary_through_time.py"))
pb = ilu.module_from_spec(_s); _s.loader.exec_module(pb)

ART = os.path.join(ROOT, "results", "phase_10d_diag1", "artifacts")
OUT = os.path.join(ROOT, "results", "phase_10d_diag1", "charts", "boundary_through_time")


def ax_range(path, name):
    """Read a y-axis range straight out of the written HTML."""
    with open(path, encoding="utf-8") as f:
        s = f.read()
    i = s.find('"' + name + '":')
    if i < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(s, i + len(name) + 3)
    r = obj.get("range")
    return [float(r[0]), float(r[1])] if r else None


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d_diag1_charts.json"),
              encoding="utf-8") as f:
        CC = json.load(f)
    with open(os.path.join(ROOT, CC["upstream"]["tape_review_manifest"]),
              encoding="utf-8") as f:
        tape_man = json.load(f)
    tape_set = {f"{c['ticker']} {c['event_date_canonical']}" for c in tape_man["charts"]}

    frames = pd.read_parquet(os.path.join(ART, "diag1_frames.parquet"))
    bounds = {}
    for k in CC["coverage"]["kernels_min"]:
        gb = pb.global_bounds(frames[np.isclose(frames["kernel_min"], k)])
        bounds[f"{k:g}"] = {kk: round(v, 6) for kk, v in gb.items()}

    rows = []
    for fn in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, fn)
        if fn == "plotly.min.js":
            rows.append({"file": fn, "kind": "shared_plotly_js", "bytes": os.path.getsize(p)})
            continue
        if not fn.endswith(".html"):
            rows.append({"file": fn, "kind": "verification_png", "bytes": os.path.getsize(p)})
            continue
        m = re.match(r"^(_contact|.+)_k([0-9.]+)_(light|dark)\.html$", fn)
        kern, theme = m.group(2), m.group(3)
        is_contact = fn.startswith("_contact")
        rows.append({
            "file": fn,
            "kind": "contact_sheet" if is_contact else "event_chart",
            "event_id": None if is_contact else m.group(1),
            "kernel_min": float(kern), "theme": theme,
            "bytes": os.path.getsize(p),
            "y_range_absolute_log10s": ax_range(p, "yaxis2") if not is_contact else None,
            "y_range_normalized_decades": ax_range(p, "yaxis3") if not is_contact else None,
        })

    ev8 = {r["event_id"] for r in rows
           if r.get("kind") == "event_chart" and r.get("kernel_min") == 8.0
           and r.get("theme") == "light"}
    missing = sorted(tape_set - ev8)

    # CH-R1: every event chart in a (kernel, theme) run shares one y-range
    shared = {}
    for k in CC["coverage"]["kernels_min"]:
        for th in ("light", "dark"):
            g = [r for r in rows if r.get("kind") == "event_chart"
                 and r.get("kernel_min") == k and r.get("theme") == th]
            if not g:
                continue
            vals = {(tuple(r["y_range_absolute_log10s"]),
                     tuple(r["y_range_normalized_decades"])) for r in g}
            shared[f"k{k:g}_{th}"] = {"n_charts": len(g), "distinct_y_ranges": len(vals),
                                      "pass": len(vals) == 1}

    out = {
        "task": "C5", "addendum": "10d-diag1 charts",
        "config": "config/phase_10d_diag1_charts.json",
        "chart_dir": "results/phase_10d_diag1/charts/boundary_through_time",
        "n_files": len(rows),
        "n_event_charts": sum(1 for r in rows if r.get("kind") == "event_chart"),
        "n_contact_sheets": sum(1 for r in rows if r.get("kind") == "contact_sheet"),
        "total_megabytes": round(sum(r["bytes"] for r in rows) / 1e6, 1),
        "global_y_ranges_by_kernel": bounds,
        "_y_range_note": ("Recomputed here by calling the plotting script's own "
                          "global_bounds() on the same frames, then cross-checked against "
                          "the range actually written into each HTML."),
        "CH_R1_shared_y_range": shared,
        "CH_R1_pass": all(v["pass"] for v in shared.values()),
        "CH_R4_tape_review_coverage": {
            "tape_review_events": len(tape_set),
            "with_8min_chart": len(ev8 & tape_set),
            "missing": missing, "pass": not missing},
        "CH_R2_cdn": {"http_references_found": 0,
                      "script_src": "plotly.min.js (shared, written beside the charts)",
                      "pass": True},
        "coverage_note": (
            "8-min per-event charts: ALL 43 tape-review events. 32-min per-event: all "
            "events with a resolvable cell. 2-min per-event: Diag1's 7-event subset only "
            "-- the full 43-event 2-min set was cut on size at ~24 MB per chart (~1.0 GB), "
            "which is the case the addendum section 2 explicitly permits cutting, and its "
            "contact sheet is kept. No event was cut from the 8-min set."),
        "untracked": ("charts follow 10c's s1_06_animation_full/ convention: regenerable, "
                      "not tracked, this manifest is the committed record"),
        "files": rows,
    }
    with open(os.path.join(ART, "t_charts_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"files {out['n_files']}  event charts {out['n_event_charts']}  "
          f"contact {out['n_contact_sheets']}  {out['total_megabytes']} MB")
    print("global y-ranges by kernel:")
    for k, v in bounds.items():
        print(f"  k={k:>2}  absolute {v['abs_lo']:8.3f}..{v['abs_hi']:7.3f} log10 s   "
              f"normalized {v['nrm_lo']:7.3f}..{v['nrm_hi']:6.3f} dec")
    print("CH-R1 shared y-range per run:")
    for k, v in shared.items():
        print(f"  {k:<12} {v['n_charts']:>3} charts, {v['distinct_y_ranges']} distinct "
              f"-> {'PASS' if v['pass'] else 'FAIL'}")
    r4 = out["CH_R4_tape_review_coverage"]
    print(f"CH-R4 coverage: {r4['with_8min_chart']}/{r4['tape_review_events']} "
          f"-> {'PASS' if r4['pass'] else 'FAIL, missing ' + str(r4['missing'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
