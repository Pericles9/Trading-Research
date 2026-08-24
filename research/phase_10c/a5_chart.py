"""Amendment 3 chart: anchor-timing deltas per variant pair, and post-close anchor offsets."""
from __future__ import annotations
import importlib.util as ilu, json, os, sys
import numpy as np, pandas as pd, plotly.graph_objects as go
from plotly.subplots import make_subplots
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C
from common import rel
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
ART, CH = "results/phase_10c/artifacts", "results/phase_10c/charts"

def main() -> int:
    chash = c10c.cfg_hash()
    r = json.load(open(rel(f"{ART}/a5_variant_analysis.json"), encoding="utf-8"))
    a1 = r["A1_anchor_timing_deltas"]
    off = pd.read_parquet(rel(f"{ART}/a5_post_close_offsets.parquet"))
    cols = {"1.25_vs_1.3": C.ARM_A, "1.25_vs_1.35": C.ARM_B, "1.3_vs_1.35": C.INK2}
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10, subplot_titles=[
        "Anchor-timing delta per variant pair (every event, not a summary)",
        "Anchor offset from session close (all variants)"])
    for k, col in cols.items():
        d = np.abs(np.array(a1[k]["_deltas"]))
        d = np.where(d <= 0, 1e-3, d)
        fig.add_trace(go.Box(x=d, name=f"{k.replace('_vs_',' vs ')} (n={a1[k]['n_both_anchored']})",
                             orientation="h", marker_color=col, boxpoints="all", jitter=0.5,
                             pointpos=0, marker=dict(size=5), showlegend=False), row=1, col=1)
    fig.add_vline(x=60, line=dict(color="#C23531", width=2, dash="dash"), row=1, col=1,
                  annotation_text="1 minute", annotation_position="top")
    o = off[off.seconds_after_close > 0]
    fig.add_trace(go.Scatter(x=o.seconds_after_close, y=o.threshold.astype(str), mode="markers",
                             marker=dict(size=13, color=C.ARM_A, symbol="diamond",
                                         line=dict(width=1, color=C.SURFACE)),
                             text=o.ticker + " " + o.event_date_canonical,
                             hovertemplate="%{text}<br>%{x:.4g} s after close<extra></extra>",
                             showlegend=False), row=1, col=2)
    fig.update_xaxes(type="log", title_text="|anchor delta| (s, log)", row=1, col=1)
    fig.update_xaxes(type="log", title_text="seconds after session close (log)", row=1, col=2)
    fig.update_yaxes(title_text="momentum threshold", type="category", row=1, col=2)
    p = a1["1.25_vs_1.3"]
    C.finish(fig, "A3-1 — The threshold variant moves T=0, and segment counts hide it",
             "Left: absolute anchor-timing delta for every event where both variants of a pair "
             "produce an anchor, plotted as raw points behind the box. Zero deltas are drawn at "
             "1 ms so they remain visible on a log axis. Right: every anchor falling after its "
             "session close, across all three variants.",
             C.caption(f"Phase 10 cohort, 114 events; pairs share {p['n_both_anchored']}, "
                       f"{a1['1.25_vs_1.35']['n_both_anchored']} and "
                       f"{a1['1.3_vs_1.35']['n_both_anchored']} anchored events",
                       "det_ns_poll0 per momentum threshold variant; session close from XNYS",
                       chash,
                       f"<b>1.25 vs 1.30 differ by a median of {p['median_s']:.1f} s</b> "
                       f"(IQR {p['iqr_s'][0]:.1f} to {p['iqr_s'][1]:.1f} s), with "
                       f"{p['n_exceeding_60s']} of {p['n_both_anchored']} events "
                       f"({p['share_exceeding_60s']:.1%}) more than a minute apart and only "
                       f"{p['n_identical']} identical. The segment-count table showed these two "
                       "variants differing by a single event.<br>"
                       "Right panel: one anchor sits 7.8 ms after the close (ACET, a closing "
                       "cross) and three sit between 31 s and 88 minutes after it, all at "
                       "threshold 1.35. The two groups are four orders of magnitude apart."),
             height=640, width=1560)
    m = C.write(fig, rel(CH), "a3_1_variant_anchor_deltas")
    c10c.write_json(rel(f"{ART}/a5_chart_manifest.json"), {"chart": m, "config_hash": chash})
    return 0 if m["kaleido_verified"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
