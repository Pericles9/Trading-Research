"""Chart 03 - which failure class explains the 6,065?

x=failure class, y=count, bar. Count labeled on each bar; total in title.
Shows all 6 T2b classes, including the zero-count ones, so the escalation-
triggering classes (format_mismatch, duplicate_collision) being empty is
visible, not just implied.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[2]

ALL_CLASSES = ["folder_absent", "missing_quotes", "missing_trades", "missing_both", "format_mismatch", "duplicate_collision"]


def main(out_path: str) -> None:
    recon = json.loads(
        (REPO_ROOT / "results" / "phase_0c" / "artifacts" / "join_reconciliation.json").read_text(encoding="utf-8")
    )
    counts = recon["t2b_class_counts"]
    values = [counts.get(c, 0) for c in ALL_CLASSES]
    total = sum(values)

    colors = ["#E45756" if v > 0 and c in ("format_mismatch", "duplicate_collision") else "#4C78A8" for c, v in zip(ALL_CLASSES, values)]

    fig = go.Figure(
        go.Bar(x=ALL_CLASSES, y=values, text=values, textposition="outside", marker_color=colors)
    )
    fig.update_layout(
        title=f"T2b failure class counts — total 6,065 non-joinable events (total shown: {total})",
        xaxis_title="failure class", yaxis_title="count",
        height=550, template="plotly_white",
    )

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"wrote {out}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/charts/03_failure_class_counts.html"
    main(target)
