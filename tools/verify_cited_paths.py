#!/usr/bin/env python
"""
Resolve every repo path cited in docs/ and prompts/ against the checkout.

WHY THIS EXISTS. Five separate times a path was cited as authority and did not resolve:
`research/scale_space/scale_field.py` (invented), `claude/scale_space_lessons.md` (cited three
times, twice by the architect and once by the agent that had already established it was
absent), and `results/scope_universe_scan/frozen_input_baseline.json` (the agent's own
register entry, pointing at a file it had written to a different path). The pattern is not
carelessness. Two structural causes: **a document the repo's decisions depend on does not live
in the repo**, and **a path typed from memory is never checked against disk**. If it is
load-bearing enough to cite, it is load-bearing enough to be inside the audit trail; if it is
not inside the audit trail, it is not citable.

This is the same move that turned the D:\\ hardcode enumeration from a stale hand-maintained
list into a gate: **make the class checkable rather than patching the instance.**

DESIGN, deliberately matching tools/verify_claude_md_indices.py:
  * READ-ONLY. It never edits a citation. A tool that silently repaired a reference would hide
    exactly the drift it exists to surface.
  * Exit 1 on any unresolved citation, so it can gate a phase start.
  * Conservative extraction. A verifier that cries wolf gets ignored.

    .venv/Scripts/python.exe tools/verify_cited_paths.py
    .venv/Scripts/python.exe tools/verify_cited_paths.py --json

WHY THE SCOPING BELOW IS AS TIGHT AS IT IS. A first pass accepted every path-shaped token and
reported 266 unresolved; a second, root-anchored, reported 92. Both were dominated by false
positives, which is the failure this tool's own design note warns about. Inspecting all 92
showed the residue sorts into exactly three structural classes plus a genuine one, so each
class gets a rule with a stated reason rather than a growing exception list:

  1. PLACEHOLDERS -- `config/[name].json`, `data/filtered/<event>/trades.parquet`,
     `charts/NN_name.html`. Templates, not citations. Dropped in the matcher.
  2. SELF-REFERENTIAL DELIVERABLES -- `prompts/phase_10b.md` naming `results/phase_10b/...`
     is an Output Files table specifying what the phase will produce, not a citation of
     existing authority. Out of scope by construction. This deliberately keeps the case that
     matters: a CROSS-file citation of another phase's output is checked, which is how the
     `results/phase_6/` -> `results/phase_6_rth_only/` rename was caught.
  3. DECLARED ABSENT -- whole subtrees this repo documents as not present (`src/models/`,
     `src/signals/`, `src/backtest/`, `src/utils/`: companion docs for a codebase that is not
     in this checkout, stated at docs/Research-Library-Map.md:425). Each root carries the
     in-repo line that declares it.
  4. Everything else is UNRESOLVED and exits 1.

DELIBERATE NON-EXISTENCE. Beyond those subtrees, individual citations name a path precisely
BECAUSE it does not exist -- a defect record naming an invented path, a correction note naming
the filename it corrected, a narrative saying a directory was renamed away. Those live in
EXPECTED_ABSENT, each with the reason. That list cannot be generated (it is a record of
intent), so every entry is REPORTED rather than silently swallowed, and a reviewer can see the
list growing if the tool is being appeased instead of obeyed.

WHAT THIS TOOL CANNOT DO. It cannot distinguish a narrative mention ("`results/phase_6/` was
renamed") from a live citation ("enumerated in `results/phase_6/artifacts/...`"). Both are
unresolvable strings. The disposition of each is a human judgement recorded in EXPECTED_ABSENT,
and that is the tool's boundary, not a defect in it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

SCAN_DIRS = ["docs", "prompts"]
SCAN_FILES = ["CLAUDE.md", "README_HANDOFF.md"]

# ---------------------------------------------------------------------------
# Class 3: subtrees this repo documents as absent. Each carries its declaring line.
# ---------------------------------------------------------------------------
DECLARED_ABSENT_ROOTS = {
    "src/models/": "docs/Research-Library-Map.md:425 -- companion docs for a src/ codebase "
                   "that does not exist anywhere in this checkout",
    "src/signals/": "docs/Research-Library-Map.md:425 -- same",
    "src/backtest/": "docs/Research-Library-Map.md:425 -- same",
    "src/utils/": "docs/Research-Library-Map.md:425 -- same",
}

# ---------------------------------------------------------------------------
# Class 4 exceptions: exact paths cited on purpose as ABSENT. Each carries why.
# ---------------------------------------------------------------------------
EXPECTED_ABSENT = {
    "research/scale_space/scale_field.py":
        "the invented path, named in landing notes and defect records as the thing that was "
        "wrong; the real module is research/scale_field/scale_field.py",
    "claude/scale_space_lessons.md":
        "a claude.ai Project doc, not a repo file. Cited as authority for a closed item and "
        "repeatedly found absent. THIS IS THE OPEN DEFECT this tool exists to surface, not a "
        "benign exception -- either the doc moves into the repo or the citations are replaced "
        "by restated content. Tracked in docs/Open-Items-Register.md.",
    # -- the three src/data companion docs, same finding as DECLARED_ABSENT_ROOTS but under a
    #    directory that does exist, so they cannot be covered by a root prefix.
    "src/data/luld_halt_detection.py":
        "same finding as the src/ roots above (Research-Library-Map.md:425): a companion doc "
        "describes it; the file is not in this checkout. src/data/ exists, so no root covers it.",
    "src/data/pandas_loader.py": "same as src/data/luld_halt_detection.py",
    "src/data/polars_loader.py": "same as src/data/luld_halt_detection.py",
    # -- historical narrative: the directory was renamed away, and saying so requires the old name.
    "results/phase_6/":
        "renamed to results/phase_6_rth_only/ (D3). Universe-Decisions.md:104 and :594 cite the "
        "old name inside the sentence recording the rename, and prompts/phase_7.md:13 inside its "
        "narrative of the same event. Correct as written -- a rename cannot be described without "
        "naming what was renamed.",
    "results/phase_6/artifacts/t3_excluded_t0_rows.parquet":
        "prompts/phase_7.md:15, written before the rename landed in that prompt's text. The file "
        "exists at results/phase_6_rth_only/artifacts/. The prompt is an executed historical "
        "record and is not rewritten; Universe-Decisions.md:409, which was a LIVE instruction "
        "using the dead name, was corrected instead.",
    # -- corrections and conditionals that must name a path that does not exist.
    #    (prompts/phase_10b_closeout.md's filename-correction note names two more, SUMMARY.md
    #    and phase_10b_summary.md; both are absorbed by the self-referential rule and so are
    #    NOT listed here -- see the staleness check in main().)
    "research/legacy/":
        "prompts/phase_0a.md:46 -- a CONDITIONAL destination in a reorganisation proposal "
        "('research/legacy/ if their phase is unknowable'). The condition never fired.",
    "data/trade_data/high_momentum/":
        "prompts/phase_2.md:14 -- a scoped quarantine lift citing Schema.md's stated location, "
        "with an explicit instruction to post what was found if it differed. It differed. The "
        "dangling reference is itself a Phase 2 finding "
        "(results/data_inventory/inventory_summary.md).",
    "data/minute/trades/":
        "deleted 2026-07-11 after its 1,303 unique events were migrated into filtered/; "
        "documented in results/data_inventory/minute_trades_cleanup_report.md. Every citation "
        "in Research-Library-Map.md is a description of that record.",
    # -- repaired drifts, named in the record OF the repair. This tool found all three; the
    #    entry describing each fix must quote the wrong path to say what was wrong, which
    #    makes the fix itself trip the gate. Recorded rather than reworded, because a repair
    #    note that cannot name what it repaired is not a record.
    "results/scope_universe_scan/frozen_input_baseline.json":
        "docs/Open-Items-Register.md -- the agent's own miscited path, now quoted inside the "
        "entry recording that the file it wrote is results/phase_10e/artifacts/"
        "frozen_baseline.json. The live citation was corrected 2026-09-04.",
    "docs/decisions_draft_D24_D27.md":
        "docs/Open-Items-Register.md -- quoted inside the same entry as the repo-map citation "
        "that was off by one; the file is docs/decisions_draft_D24_D26.md. Corrected 2026-09-04.",
    "data/metadata/massive_trade_conditions.json":
        "prompts/phase_10c_amendment_6.md:87 -- the location a retrieved dictionary WOULD be "
        "written to, explicitly 'subject to C below' and not acted on.",
    # -- Build F1, pre-flight only (2026-09-11): planned deliverables of tasks that have not run
    #    yet, cited in the work order and its companion doc as WHAT WILL be written there. A
    #    different category from every entry above (nothing invented, nothing renamed, nothing
    #    historical) -- self-resolving, not permanent. Remove each entry the moment F1-T2/F1-T5
    #    actually create it; the staleness check below will flag "path now exists on disk" as
    #    the signal to do so, which is exactly what that check is for.
    "claude/fundamental_data_float_scoping_note.md":
        "prompts/fundamentals_f1.md's own reconciliation note and digest contract (§7 item 10) -- "
        "cited to record that the original work order's companion doc does not exist in this "
        "checkout, not asserted as present. The original draft's own text says no task depends on "
        "it (numbers are restated inline), so this is documented rather than treated as a blocker.",
    "data/fundamentals/":
        "docs/Research-Library-Map.md and docs/data/fundamentals_sources.md -- the normalized-facts "
        "layer F1-T2/F1-T4 write to. Does not exist until those tasks run; under the wholly-"
        "gitignored /data/ root regardless.",
    "data/fundamentals/event_fundamentals.parquet":
        "prompts/fundamentals_f1.md §2 -- the event-join layer F1-T5 assembles. Does not exist "
        "until that task runs.",
    "prompts/fundamentals_build_f1.md":
        "prompts/fundamentals_f1_amendment_a1.md's own integration note and §6 -- Cooper's amendment "
        "was drafted referencing this filename; the actual committed file is "
        "prompts/fundamentals_f1.md (the stem used since pre-flight). Kept verbatim as the record of "
        "the amendment as given, with the correction noted inline rather than silently rewriting "
        "Cooper's text.",
}

# ---------------------------------------------------------------------------
# Class 1: the matcher. Root-anchored, no placeholders, no commands.
# ---------------------------------------------------------------------------
ROOTS = ("docs/", "prompts/", "research/", "results/", "src/", "config/", "data/", "tools/",
         "notebooks/", "archive/", "claude/", "hawkes-ofi-impact/", "scanner-epg-momentum/")
EXT = (".py", ".md", ".json", ".parquet", ".ipynb", ".html", ".sh", ".txt", ".csv", ".yml",
       ".yaml", ".toml", ".duckdb")
TOKEN = re.compile(r"`([^`\n]+)`")
# not a concrete path: URLs, {templates}, [placeholders], <placeholders>, globs, ellipses,
# NN_ stand-ins, and commands (which contain whitespace)
SKIP = re.compile(r"https?://|[{}\[\]<>*|]|\.\.\.|\u2026|\s|/NN_")

PHASE_SEG = re.compile(r"^(?:results|research)/(phase_[A-Za-z0-9]+)(?:/|$)")
# Not every prompt names a numbered phase -- scale_field (prompts/scale_field_brief.md) and
# impact_by_participation established a second, unnumbered convention this tool's own class-2
# reasoning already covers in spirit ("an Output Files table specifying what the phase will
# produce") but PHASE_SEG's "phase_" literal never matched. Exact-stem only, deliberately
# narrower than PHASE_SEG's prefix+underscore allowance: a bare word (unlike "phase_NN") is
# common enough elsewhere in the tree (results/hardware/, config/scale_field.json) that a
# prefix match would risk masking a real cross-file citation, which is the case this tool
# exists to keep catching.
BARE_SEG = re.compile(r"^(?:results|research)/([A-Za-z][A-Za-z0-9_]*)(?:/|$)")


def looks_like_path(tok: str) -> bool:
    if SKIP.search(tok):
        return False
    if not tok.startswith(ROOTS):
        return False
    if tok.endswith("/"):
        return True
    return tok.lower().endswith(EXT)


def is_self_referential(src_rel: str, tok: str) -> bool:
    """Class 2. A phase prompt naming its own deliverables is specifying, not citing.

    True when src is prompts/<name>.md and tok points into results/<phase>/ or
    research/<phase>/ (or results/reports/<phase>_*) where <phase> and <name> share a
    phase prefix on a segment boundary -- so phase_1 does NOT match phase_10b.

    Also true, exact-stem only (no prefix allowance -- see BARE_SEG's comment), for the
    unnumbered-work-unit convention: prompts/<name>.md citing results/<name>/, research/<name>/,
    or config/<name>.json.
    """
    if not src_rel.startswith("prompts/") or not src_rel.endswith(".md"):
        return False
    name = os.path.basename(src_rel)[:-3]          # e.g. phase_10b_amendment_2
    m = PHASE_SEG.match(tok)
    if m:
        seg = m.group(1)                            # e.g. phase_10b
    elif tok.startswith("results/reports/"):
        # the standing cross-phase copy: results/reports/phase_10b_report.md
        seg = os.path.basename(tok).split(".")[0]
        seg = re.sub(r"_(report|summary)$", "", seg)
    elif tok.startswith("config/") and tok.endswith(".json"):
        seg = os.path.basename(tok)[:-5]            # e.g. impact_by_participation
        return seg == name
    else:
        bm = BARE_SEG.match(tok)
        if not bm:
            return False
        return bm.group(1) == name
    for a, b in ((seg, name), (name, seg)):
        if b == a or (b.startswith(a) and b[len(a):].startswith("_")):
            return True
    return False


def scan():
    """Return {token: [citation sites]} for non-self-referential citations."""
    cites = {}
    targets = [os.path.join(ROOT, f) for f in SCAN_FILES]
    for d in SCAN_DIRS:
        for dp, _, fns in os.walk(os.path.join(ROOT, d)):
            targets += [os.path.join(dp, f) for f in fns if f.endswith(".md")]
    n_selfref = 0
    for path in sorted(targets):
        if not os.path.isfile(path):
            continue
        rel_src = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            text = open(path, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for tok in TOKEN.findall(line):
                tok = tok.strip()
                if not looks_like_path(tok):
                    continue
                if is_self_referential(rel_src, tok):
                    n_selfref += 1
                    continue
                cites.setdefault(tok, []).append(f"{rel_src}:{i}")
    return cites, n_selfref


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cites, n_selfref = scan()
    resolved, missing, expected, declared = {}, {}, {}, {}
    for tok, where in sorted(cites.items()):
        if os.path.exists(os.path.join(ROOT, tok)):
            resolved[tok] = where
        elif tok in EXPECTED_ABSENT:
            expected[tok] = where
        elif any(tok.startswith(r) for r in DECLARED_ABSENT_ROOTS):
            declared[tok] = where
        else:
            missing[tok] = where

    # STALENESS. EXPECTED_ABSENT and DECLARED_ABSENT_ROOTS are the only hand-maintained lists
    # here, and CLAUDE.md records three separate times a hand-maintained index in this repo
    # went stale. So they are checked against reality on every run: an entry that no longer
    # matches any citation, or whose path has since appeared on disk, is drift and fails the
    # gate. The disposition list can only shrink by being noticed.
    stale = {}
    for k in EXPECTED_ABSENT:
        if k not in expected:
            stale[k] = ("path now exists on disk" if os.path.exists(os.path.join(ROOT, k))
                        else "no longer cited anywhere in scope")
    for r in DECLARED_ABSENT_ROOTS:
        if not any(t.startswith(r) for t in declared):
            stale[r] = ("root now exists on disk" if os.path.exists(os.path.join(ROOT, r))
                        else "no path under this root is cited any more")

    out = {
        "task": "resolve every repo path cited in docs/ and prompts/ against the checkout",
        "scanned": SCAN_DIRS + SCAN_FILES,
        "stale_disposition_entries": stale,
        "n_distinct_paths_cited": len(cites),
        "n_resolved": len(resolved),
        "n_selfref_citations_skipped": n_selfref,
        "n_declared_absent": len(declared),
        "n_expected_absent": len(expected),
        "n_unresolved": len(missing),
        "unresolved": missing,
        "declared_absent_roots": DECLARED_ABSENT_ROOTS,
        "expected_absent": {k: {"reason": EXPECTED_ABSENT[k], "cited_at": v}
                            for k, v in expected.items()},
        "verdict": ("CLEAN" if not missing and not stale else "; ".join(
            ([f"{len(missing)} unresolved citation(s)"] if missing else [])
            + ([f"{len(stale)} stale disposition entry(ies)"] if stale else []))),
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return 1 if (missing or stale) else 0

    print("=== cited-path verification ===\n")
    print(f"  distinct repo paths cited     : {out['n_distinct_paths_cited']}")
    print(f"  resolved                      : {out['n_resolved']}")
    print(f"  self-referential, out of scope: {n_selfref} citation(s)")
    print(f"  declared absent (in-repo note): {out['n_declared_absent']}")
    print(f"  expected absent (dispositions): {out['n_expected_absent']}")
    print(f"  UNRESOLVED                    : {out['n_unresolved']}")
    print(f"  STALE disposition entries     : {len(stale)}\n")
    for k, why in stale.items():
        print(f"  STALE    {k}\n           {why} -- remove it, or say why it stays")
    for k, v in missing.items():
        print(f"  MISSING  {k}")
        for w in v[:8]:
            print(f"           cited at {w}")
    if expected:
        print("  expected-absent, reported so the list stays visible:")
        for k, v in expected.items():
            print(f"    {k}  ({len(v)} citation(s))")
    if declared:
        print(f"\n  declared-absent subtrees: {len(declared)} path(s) under "
              f"{', '.join(sorted(DECLARED_ABSENT_ROOTS))}")
    print(f"\n{out['verdict']}")
    return 1 if (missing or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
