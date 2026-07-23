"""
Phase 6 T5 - Chart 02: move concentration. Same encoding as chart 01,
cum path-length share instead of cum volume share.
"""
from research.phase_6.build_chart_01 import build

OUT_HTML = "results/phase_6/charts/02_move_concentration.html"

if __name__ == "__main__":
    build(value_col="move_share", title="Move (path-length) concentration", out_html=OUT_HTML)
