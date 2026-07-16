"""Schema-validate a digest.json.

This validates against the best available reconstruction of "the §11
Digest Contract," not the contract document itself - no copy of it was
found anywhere on E: or D: despite an exhaustive search (see CLAUDE.md's
Pointers section and results/phase_0b/REPORT.md). Two sources were
combined:

  1. Explicit clues in prompts/phase_0b.md's own T6a task text: "required
     fields, headline_metrics[].chart present, <=100 lines" - taken
     literally, since it's the only concrete spec fragment that exists
     anywhere in this checkout.
  2. The fields results/phase_0a/digest.json actually used (phase, status,
     summary, decisions_log, surprises, output_files) - the only real
     precedent, referenced by name in prompts/phase_0a.md's T6 task text.

Phase 0a's digest predates this reconstruction and does not have
headline_metrics - expect it to fail that one check. Per
prompts/phase_0b.md's escalation table, that failure is reported as a
finding, not silently patched into Phase 0a's digest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["phase", "status", "summary", "decisions_log", "surprises", "output_files"]
MAX_LINES = 100


def validate(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    line_count = text.count("\n") + 1
    data = json.loads(text)

    checks = []

    for field in REQUIRED_FIELDS:
        checks.append({
            "check": f"required_field:{field}",
            "passed": field in data,
        })

    checks.append({
        "check": "decisions_log_is_list",
        "passed": isinstance(data.get("decisions_log"), list),
    })
    checks.append({
        "check": "surprises_is_list",
        "passed": isinstance(data.get("surprises"), list),
    })

    has_headline_metrics = isinstance(data.get("headline_metrics"), list) and len(data.get("headline_metrics", [])) > 0
    checks.append({
        "check": "headline_metrics_present",
        "passed": has_headline_metrics,
    })
    if has_headline_metrics:
        all_have_chart = all("chart" in m for m in data["headline_metrics"])
        checks.append({
            "check": "headline_metrics[].chart_present",
            "passed": all_have_chart,
        })

    checks.append({
        "check": f"line_count<={MAX_LINES}",
        "passed": line_count <= MAX_LINES,
        "observed": line_count,
    })

    all_passed = all(c["passed"] for c in checks)
    return {
        "path": str(path),
        "line_count": line_count,
        "checks": checks,
        "all_passed": all_passed,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: validate_digest.py <path-to-digest.json> [...]")
        sys.exit(2)

    results = [validate(Path(p)) for p in sys.argv[1:]]
    print(json.dumps(results, indent=2))

    if not all(r["all_passed"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
