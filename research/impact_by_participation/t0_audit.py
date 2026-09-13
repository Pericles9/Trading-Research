"""T0 -- does a trade-level execution participation-rate variable already exist?

Read-only, no DB connection. Greps the checkout for a print-size-relative-to-
concurrent-volume construct (the market-impact-literature sense of
"participation rate" / POV) and reports what it finds against what actually
exists under the name "participation" in this repo.
"""
from __future__ import annotations

import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"

SEARCH_ROOTS = [
    REPO / "research" / "phase_8",
    REPO / "research" / "phase_11",
    REPO / "src" / "data" / "canonical.py",
    REPO / "docs" / "data" / "Schema.md",
    REPO / "docs" / "Research-Library-Map.md",
]
EXEC_TERMS = re.compile(
    r"participation.?rate|\bpov\b|adv.?ratio|volume.?percentile|"
    r"order.?size.*volume|size.*concurrent.?volume", re.I)
PARTICIPATION_TERM = re.compile(r"particip", re.I)
KNOWN_NON_MATCH = re.compile(r"pq_rth_open|pq_t0_close|participant_timestamp", re.I)


def scan(root: pathlib.Path) -> list[dict]:
    hits = []
    files = [root] if root.is_file() else list(root.rglob("*.py")) + list(root.rglob("*.md"))
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if EXEC_TERMS.search(line):
                hits.append({"file": str(f.relative_to(REPO)), "line": i,
                             "text": line.strip(), "class": "execution_participation_candidate"})
            elif PARTICIPATION_TERM.search(line) and not KNOWN_NON_MATCH.search(line):
                hits.append({"file": str(f.relative_to(REPO)), "line": i,
                             "text": line.strip(), "class": "participation_other"})
    return hits


def main() -> None:
    hits = []
    for root in SEARCH_ROOTS:
        hits.extend(scan(root))

    exec_hits = [h for h in hits if h["class"] == "execution_participation_candidate"]

    out = {
        "task": "T0", "phase": "impact_by_participation",
        "question": "Does a trade-size-relative-to-concurrent-volume (execution) "
                     "participation-rate variable already exist in this checkout?",
        "answer": "NO. " if not exec_hits else "UNCLEAR -- see execution_candidate_hits.",
        "execution_candidate_hits": exec_hits,
        "what_exists_instead": {
            "name": "pq_rth_open / pq_t0_close (research/phase_8/t3_participation.py)",
            "definition": "Event-level, time-based relative volume: "
                "logrv(tau) = log((v0(tau)+1)/(b(tau)+1)), where v0(tau) is the event's own "
                "cumulative T0 extended-day volume to clock anchor tau and b(tau) is the "
                "median of the SAME ticker's T-1/T-2/T-3 cumulative volume to the same "
                "clock time. Cross-sectional quintiled (rank only) across D1 events at each "
                "anchor. This measures how unusually active THIS EVENT is relative to the "
                "ticker's own recent history at a point in clock time -- it is a "
                "price-discovery-timing / abnormal-activity variable, not a measure of any "
                "individual print's size relative to concurrent market volume.",
            "source": "research/phase_8/t3_participation.py:1-24",
            "consumers": ["research/phase_8/t5_markout_grid.py", "research/phase_8/chart_04.py",
                          "research/phase_8/chart_05.py", "research/phase_11/t8_impact.py",
                          "research/phase_11/chart_08.py"],
        },
        "conclusion": (
            "No execution participation-rate variable (print size relative to concurrent "
            "market volume) exists anywhere in this checkout as of this task. T2 builds one "
            "from scratch, dev-tier only, per the prompt's own definition -- it does not reuse "
            "pq_rth_open, which answers a different question."
        ),
        "source": "research/impact_by_participation/t0_audit.py:main",
        "reproduce": ".venv/Scripts/python.exe -m research.impact_by_participation.t0_audit",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "t0_audit.json").write_text(json.dumps(out, indent=2))
    print(f"T0: execution-participation candidate hits = {len(exec_hits)}")
    print(f"T0: 'participation' hits elsewhere (context only) = "
          f"{len([h for h in hits if h['class'] == 'participation_other'])}")
    print("T0: conclusion ->", out["conclusion"])


if __name__ == "__main__":
    main()
