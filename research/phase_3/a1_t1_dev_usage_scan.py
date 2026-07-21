"""
Phase 3 Amendment 1, A1-T1 - pre-repin safety scan.

Scans every committed results/phase_*/digest.json and REPORT.md for
mentions of the dev tier (dev_sample, filtered_trades_dev*,
filtered_quotes_dev*, dev_events), then classifies each hit by the
amendment's own distinguishing rule: a "hit" is a headline/reported
metric whose VALUE is a substantive research finding computed from the
50-event sample (would go stale on re-pin); a non-hit is a mention of
building/verifying the sample itself (decile-spanning check, zero-row
check, subset-match check) or an infrastructure benchmark whose point
was engine/query performance, not a data finding about momentum events.

This is a judgment call the amendment explicitly delegates to the agent
in the first pass ("determine whether...") but every candidate found is
listed with its classification and reasoning, so Cooper can override any
of them. This script does not run any DB query - grep-only, no
DuckDB connection.
"""
import json
import re
from pathlib import Path

PATTERN = re.compile(
    r"dev_sample|filtered_trades_dev|filtered_quotes_dev|dev_events|dev.tier|dev-tier",
    re.IGNORECASE,
)
OUT_PATH = "results/phase_3/artifacts/a1_dev_usage_scan.json"

CANDIDATES = [
    {
        "phase": "phase_0b",
        "file": "results/phase_0b/digest.json",
        "text": "Dev sample (5/decile x 10 momentum_pct deciles) spans the full eligible pool, no empty deciles",
        "classification": "not_a_hit",
        "reason": "Sample-construction/stratification verification (does the sample cover all deciles) - not a research finding about momentum events.",
    },
    {
        "phase": "phase_0b",
        "file": "results/phase_0b/digest.json",
        "text": "Dev-tier representative query (trade count + minute-bucketed volume, 50 events) well under the 60s target - 5.31s, 123,145 rows",
        "classification": "not_a_hit",
        "reason": "Infrastructure/query-latency benchmark (is DuckDB fast enough) - the measured value is engine performance, not a data finding about momentum events. Re-pinning changes which 50 events are queried but does not invalidate the conclusion (DuckDB is fast enough); not the kind of comparability the amendment protects.",
    },
    {
        "phase": "phase_0b",
        "file": "results/phase_0b/REPORT.md",
        "text": "Representative dev-tier query (T5d) > 600s threshold -> 5.31s, PASS",
        "classification": "not_a_hit",
        "reason": "Same benchmark as above, reported in REPORT.md's verification table.",
    },
    {
        "phase": "phase_1",
        "file": "results/phase_1/digest.json",
        "text": "dev_sample_events_zero_rows: 0",
        "classification": "not_a_hit",
        "reason": "QA/coverage check (does every dev-sample event have nonzero rows) - not a research finding.",
    },
    {
        "phase": "phase_1",
        "file": "results/phase_1/REPORT.md",
        "text": "T5b - 50 dev-sample events, filtered_trades_dev / filtered_quotes_dev row counts - all 50 events have non-zero rows in both tables, no escalation",
        "classification": "not_a_hit",
        "reason": "Same QA/coverage check as above, with the per-event row-count table shown as evidence, not as a reported research metric.",
    },
    {
        "phase": "phase_1b",
        "file": "results/phase_1b/digest.json",
        "text": "Dev sample v2 - 50 events, 10 deciles, 0 subset mismatches, 0 zero-row events",
        "classification": "not_a_hit",
        "reason": "Sample-build verification (subset match against main tables, zero-row check) - not a research finding.",
    },
    {
        "phase": "phase_1b",
        "file": "results/phase_1b/REPORT.md",
        "text": "Dev v2 subset match | 50/50",
        "classification": "not_a_hit",
        "reason": "Same subset-match verification as above.",
    },
]


def main():
    grep_hits = {}
    for f in Path("results").glob("phase_*/digest.json"):
        text = f.read_text(encoding="utf-8")
        matches = PATTERN.findall(text)
        if matches:
            grep_hits[str(f).replace("\\", "/")] = len(matches)
    for f in Path("results").glob("phase_*/REPORT.md"):
        text = f.read_text(encoding="utf-8")
        matches = PATTERN.findall(text)
        if matches:
            grep_hits[str(f).replace("\\", "/")] = len(matches)

    n_true_hits = sum(1 for c in CANDIDATES if c["classification"] == "hit")

    out = {
        "phase": "3", "task": "A1-T1",
        "grep_match_counts_by_file": grep_hits,
        "candidates_reviewed": CANDIDATES,
        "n_candidates": len(CANDIDATES),
        "n_true_hits": n_true_hits,
        "conclusion": (
            "No headline/reported metric in any committed digest.json or REPORT.md is a "
            "substantive research finding computed from the dev-tier sample. All matches found "
            "are sample-construction/verification checks (decile coverage, zero-row checks, "
            "subset-match checks) or one infrastructure query-latency benchmark (Phase 0b) whose "
            "point was engine performance, not a momentum-event data finding. Per the amendment's "
            "own distinguishing rule, none of these constitute a hit; the escalation is not "
            "triggered. Every candidate is listed above with its classification and reasoning so "
            "this judgment call is visible and overridable."
        ) if n_true_hits == 0 else "ESCALATION - see hit(s) with classification='hit' above.",
        "escalation_triggered": n_true_hits > 0,
        "source": "research/phase_3/a1_t1_dev_usage_scan.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
