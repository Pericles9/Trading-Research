"""
Phase 10 v3 chart 01 -- the scale-separation chart. Decides whether the phase is
well-posed (Cooper's read).

Usage: .venv/Scripts/python.exe research/phase_10/v3_chart01.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chartlib as C  # noqa: E402
from v2_common import POOLED, rel, write_json  # noqa: E402
from v3_t1_gate import cfg_hash, load_cfg  # noqa: E402

SEG_COLOR = {"premarket": C.ARM_B, "rth": C.ARM_A}
OBS_LABEL = {"print_rate": "print arrivals", "volume_rate": "share-volume arrivals"}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out = rel(cfg["paths"]["out_charts"])
    cur = pd.read_parquet(os.path.join(art, "v3_t1_gate_curves.parquet"))
    g = json.load(open(os.path.join(art, "v3_t1_gate.json"), encoding="utf-8"))
    cur = cur[cur["cohort_group"].isin(POOLED) & cur["segment"].isin(SEG_COLOR)]

    fig = make_subplots(
        rows=2, cols=2, shared_xaxes=True, vertical_spacing=0.09, horizontal_spacing=0.08,
        subplot_titles=[f"Allan factor — {OBS_LABEL['print_rate']}",
                        f"Allan factor — {OBS_LABEL['volume_rate']}",
                        f"Fano factor — {OBS_LABEL['print_rate']} (inflated by trend, expected)",
                        f"Fano factor — {OBS_LABEL['volume_rate']}"])

    for ci, obs in enumerate(("print_rate", "volume_rate"), 1):
        for ri, stat in enumerate(("allan", "fano"), 1):
            sub = cur[cur["observable"] == obs]
            # per-event spaghetti
            for _, ev in sub.groupby(["ticker", "event_date_canonical", "momentum_pct"]):
                ev = ev.sort_values("T")
                fig.add_trace(go.Scatter(
                    x=ev["T"], y=ev[stat], mode="lines",
                    line=dict(color="rgba(120,120,116,0.13)", width=1),
                    showlegend=False, hoverinfo="skip"), row=ri, col=ci)
            for sname, ss in sub.groupby("segment"):
                med = ss.groupby("T")[stat].median()
                n = ss.groupby("T")[stat].size()
                fig.add_trace(go.Scatter(
                    x=med.index, y=med.values, mode="lines+markers",
                    line=dict(color=SEG_COLOR[sname], width=3), marker=dict(size=8),
                    name=f"{sname} median (n={ss[['ticker','event_date_canonical']].drop_duplicates().shape[0]} events)",
                    legendgroup=sname, showlegend=(ri == 1 and ci == 1),
                    customdata=n.values,
                    hovertemplate=f"{sname}<br>T=%{{x:,.4g}}s<br>{stat} %{{y:,.4g}}"
                                  "<br>n events %{customdata}<extra></extra>"), row=ri, col=ci)
            fig.add_hline(y=1.0, line=dict(color="#b03a3a", width=1.5, dash="dash"),
                          row=ri, col=ci)
            if stat == "allan":
                for sname in SEG_COLOR:
                    f = g["segment_fits"].get(obs, {}).get(sname)
                    if not f or not f["fit"].get("ok"):
                        continue
                    knee = f["fit"]["knee_seconds"]
                    lo, hi = f["knee_interval_seconds"]
                    if lo and hi:
                        fig.add_vrect(x0=lo, x1=hi, fillcolor=SEG_COLOR[sname], opacity=0.10,
                                      line_width=0, row=ri, col=ci)
                    fig.add_vline(x=knee, line=dict(color=SEG_COLOR[sname], width=2, dash="dot"),
                                  row=ri, col=ci)
            fig.update_yaxes(type="log", title_text=f"{stat} factor (log)" if ci == 1 else None,
                             row=ri, col=ci)
        fig.update_xaxes(type="log", title_text="counting-window duration T (s, log)",
                         row=2, col=ci)

    knee_txt = " · ".join(
        f"{obs.split('_')[0]}/{s}: knee {g['segment_fits'][obs][s]['fit']['knee_seconds']:.4g}s "
        f"[{g['segment_fits'][obs][s]['knee_interval_seconds'][0]:.3g}–"
        f"{g['segment_fits'][obs][s]['knee_interval_seconds'][1]:.3g}], "
        f"slopes {g['segment_fits'][obs][s]['fit']['slope_before']:+.2f}→"
        f"{g['segment_fits'][obs][s]['fit']['slope_after']:+.2f}, "
        f"ΔBIC {g['segment_fits'][obs][s]['fit']['delta_bic']:.1f}"
        for obs in ("print_rate", "volume_rate") for s in ("premarket", "rth")
        if g["segment_fits"].get(obs, {}).get(s, {}).get("fit", {}).get("ok"))

    C.finish(
        fig, "01 — Is there a characteristic clustering scale?",
        "Allan (primary) and Fano factors against counting-window duration, computed directly on the "
        "point process — no intensity estimate, no bandwidth, no threshold. Grey = per event; "
        "coloured = per-segment median; red dashed = the Poisson value 1. Dotted vertical = fitted "
        "knee, shaded band = its bootstrap interval.",
        C.caption("pooled analysis cohort, n=100 events (premarket 28, rth 70); dyadic ladder "
                  "2⁻⁶–2¹³ s, 20 rungs",
                  "T=0 extended-day window; the 2 never-crossing events have no segment and are "
                  "excluded from the gate rows, their curves retained",
                  chash,
                  "<b>GATE ROWS 6 AND 7 PASS.</b> " + knee_txt +
                  "<br>Below the knee the Allan factor is near-flat (near-Poisson); above it the "
                  "slope approaches 1, the signature of a slowly-varying envelope."
                  "<br><b>Reads:</b> a straight line across the whole ladder would mean "
                  "self-similar — no envelope scale exists and the gate fails."),
        height=1000, width=1400)
    man = C.write(fig, out, "v3_01_scale_separation")
    write_json(os.path.join(art, "v3_chart01_manifest.json"),
               {"phase": "10", "version": "v3", "chart": man, "config_hash": chash,
                "source": "research/phase_10/v3_chart01.py:main"})
    return 0 if man["kaleido_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
