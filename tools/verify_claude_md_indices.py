#!/usr/bin/env python
"""
Verify every ENUMERATED LIST in CLAUDE.md against the repo that is supposed to back it.

WHY THIS EXISTS. Three hand-maintained lists in CLAUDE.md have gone stale, and each time
something reasoned from the stale copy:

  1. The decision-pointer list sat at D14 while the register ran to D19. A Phase 10d spec
     drafted its decision as D15 straight into a collision with Phase 11's. Near miss.
  2. The same list said D22 was the last number taken. It was not -- D23 had been appended
     the same day -- and a handoff's four draft decisions landed numbered D23-D26. Actual
     collision, caught only because the handoff told the landing session to read the
     register rather than trust the list.
  3. The "Live D:\\ hardcodes exist in: ..." enumeration omits
     data/collection_scripts/filter_events_power_law.py, which not only reads from D: but
     WRITES a parquet and a CSV there. CLAUDE.md's hard rule is never to write to D:
     (confirmed failing hardware). Anything reasoning from that list concludes the file is
     clean.

CLAUDE.md already states the rule that applies -- "a stale index that specs reason from is
worse than no index" -- and it was written about instance 1.

THE STANDING RULE THIS IMPLEMENTS. Every enumerated list in CLAUDE.md is either generated
and verified by this script, or it is deleted and replaced by the command that produces it.
A list a human maintains by hand in a repo this size will be stale again: three for three
so far.

RUN IT IN T0 OF EVERY PHASE. Exit code 1 on any drift, so it can gate a phase start.

    .venv/Scripts/python.exe tools/verify_claude_md_indices.py
    .venv/Scripts/python.exe tools/verify_claude_md_indices.py --json

This script READS ONLY. It never edits CLAUDE.md -- a script that silently repairs the
index would hide the drift it exists to surface. It prints the corrected list; a human
pastes it, in a commit that says what moved.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

# Directories that are never part of this repo's own source.
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "archive"}
# Independent repos: read-only, never modified from here (CLAUDE.md).
SKIP_TOP = {"hawkes-ofi-impact", "scanner-epg-momentum"}
# The data lake's PAYLOAD directories only. data/collection_scripts/ is SOURCE and must be
# scanned -- the first version of this script skipped all of data/ and therefore missed
# filter_events_power_law.py, the very file whose omission prompted the rule.
SKIP_DATA_PAYLOAD = {"filtered", "daily", "minute", "second10", "quote_data", "trade_data",
                     "duckdb", "metadata", "nautilus_catalog", "momentum_events",
                     "market-hours", "symbol-properties"}
SCAN_EXT = {".py", ".ipynb", ".json", ".sh", ".md"}
# THE LIST IS ABOUT WHAT YOU MIGHT EXECUTE. A REPORT.md that quotes a D: path is a record,
# not a hazard; a .py or .ipynb that names one is. They are counted separately and only the
# executable set is compared against CLAUDE.md's enumeration.
EXECUTABLE_EXT = {".py", ".ipynb", ".sh"}

# A D: path in any form: d:\, D:/, "d:\\" inside JSON/notebook escaping.
D_DRIVE = re.compile(r"[dD]:\s*[\\/]{1,2}")
# A D: path inside a COMMENT is provenance, not a hardcode. src/data/*.py carry
# "Recovered from D:\..." headers written by Phase 0b T2, and CLAUDE.md itself points at
# src/data/paths.py as the live path resolver -- listing it as a hazard would be wrong.
# Handles a plain "#" comment and the escaped form notebooks store source lines in.
COMMENTED = re.compile(r'^\s*(\\?["\'])?\s*#')


def docstring_lines(path: str, text: str) -> set:
    """Line numbers inside a module/class/function DOCSTRING of a .py file.

    A docstring is documentation, exactly like a `#` comment: a tool that explains in prose
    why the D:\\ enumeration matters is not a file that touches D:. This started as a
    special-case skip of this script's own filename; a second tool
    (tools/verify_cited_paths.py) then tripped the same wire, and the corrected list this
    script prints would have told CLAUDE.md to never execute a read-only gate. So the
    special case is generalised. Only genuine DOCSTRINGS count -- a D: path in an ordinary
    string literal is a hardcode and still counts as live.

    Unparseable or non-.py files return the empty set, i.e. nothing is excused.
    """
    if not path.lower().endswith(".py"):
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            out.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return out
# Writes we care about: these turn a stale index into a hazard rather than a doc bug.
WRITE_CALLS = re.compile(r"\.to_parquet\(|\.to_csv\(|\.to_pickle\(|open\([^)]*['\"][wa]",
                         re.I)


def iter_repo_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = os.path.relpath(dirpath, ROOT)
        parts = [] if rel_dir == "." else rel_dir.replace("\\", "/").split("/")
        if parts and parts[0] in SKIP_TOP:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if parts and parts[0] == "data":
            dirnames[:] = [d for d in dirnames if d not in SKIP_DATA_PAYLOAD]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SCAN_EXT:
                yield os.path.join(dirpath, fn)


def is_readonly_gate(rel: str, text: str) -> bool:
    """A tools/*.py that performs no disk write.

    CLAUDE.md mandates running tools/verify_claude_md_indices.py in T0 of every phase. A file
    the same document orders you to execute cannot also sit on its never-execute list -- that
    is a contradiction, and it arose the moment this script's own reporting strings ('Live D:\\
    hardcodes exist in:') were scanned by the generalised docstring rule, which correctly does
    not excuse an ordinary string literal.

    The exemption is EARNED, not asserted: it applies only while the file contains no write
    call, checked with the same WRITE_CALLS pattern used to flag a hardcode as a hazard. Add a
    write to a tools/ script and it returns to the list.
    """
    return rel.startswith("tools/") and rel.endswith(".py") and not WRITE_CALLS.search(text)


def scan_d_drive():
    """-> {relpath: {...}} for every file naming a D: path, classified by why it names one."""
    found = {}
    for path in iter_repo_files():
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if rel == "CLAUDE.md":
            continue                      # the index being checked, not a candidate
        # NOTE: this script no longer skips itself. It used to, to excuse its own docstring;
        # docstring_lines() now handles that generally, so both tools/ gates are scanned
        # like any other file and neither gets an exemption the others do not.
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        doc = docstring_lines(path, text)
        live, commented = [], []
        for i, ln in enumerate(text.splitlines()):
            if D_DRIVE.search(ln):
                n = i + 1
                (commented if (COMMENTED.match(ln) or n in doc) else live).append(n)
        if live or commented:
            in_doc = sorted(n for n in commented if n in doc)
            found[rel] = {"lines": live[:20], "n_lines": len(live),
                          "commented_only_lines": commented[:20],
                          "docstring_lines": in_doc,
                          "live": bool(live),
                          "readonly_gate": is_readonly_gate(rel, text),
                          "writes_to_disk": bool(WRITE_CALLS.search(text)),
                          "executable": os.path.splitext(rel)[1].lower() in EXECUTABLE_EXT}
    return found


def claude_md_text():
    with open(os.path.join(ROOT, "CLAUDE.md"), "r", encoding="utf-8") as fh:
        return fh.read()


def listed_d_drive(text):
    m = re.search(r"Live D:\\ hardcodes exist in:(.+?)Never execute those files", text,
                  re.S)
    if not m:
        return None
    return sorted({p.strip().rstrip(".").replace("\\", "/")
                   for p in m.group(1).split(",") if p.strip()})


def next_free_decision(text):
    m = re.search(r"\*\*Next free number:\s*D(\d+)\.?\*\*", text)
    return int(m.group(1)) if m else None


def highest_decision_in_register():
    p = os.path.join(ROOT, "docs", "Universe-Decisions.md")
    with open(p, "r", encoding="utf-8") as fh:
        nums = [int(m) for m in re.findall(r"^##\s*D(\d+)\b", fh.read(), re.M)]
    return max(nums) if nums else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit machine-readable drift")
    args = ap.parse_args()

    text = claude_md_text()
    drift = []

    # --- index 1: the D:\ hardcode enumeration -----------------------------
    scanned = scan_d_drive()
    actual = {k: v for k, v in scanned.items()
              if v["executable"] and v["live"] and not v["readonly_gate"]}
    references = {k: v for k, v in scanned.items() if not v["executable"]}
    # EXCUSED, SPLIT BY REASON AND NAMED. A count alone hid something that mattered:
    # src/data/prepare_database_split.py's only remaining D: mentions are a docstring USAGE
    # EXAMPLE (--target-root D:/mom_db_storage). That is not a hardcode -- the path is a CLI
    # argument -- but a human copying the example WOULD write to D:. Dropping it from a count
    # makes it invisible; naming it keeps the hazard readable while stating what kind it is.
    provenance_only = {k: v for k, v in scanned.items()
                       if v["executable"] and not v["live"] and not v["docstring_lines"]}
    docstring_only = {k: v for k, v in scanned.items()
                      if v["executable"] and not v["live"] and v["docstring_lines"]}
    readonly_gates = {k: v for k, v in scanned.items()
                      if v["executable"] and v["live"] and v["readonly_gate"]}
    listed = listed_d_drive(text)
    idx1 = {"index": "CLAUDE.md 'Live D:\\ hardcodes exist in'",
            "scope": ("EXECUTABLE files (.py/.ipynb/.sh) carrying a D: path OUTSIDE a "
                      "comment. The list says 'never execute those files', so a doc that "
                      "quotes a path is a record, and a provenance header is not a "
                      "hardcode."),
            "listed_n": None if listed is None else len(listed),
            "actual_n": len(actual),
            "executables_with_provenance_comments_only": sorted(provenance_only),
            "executables_with_docstring_mentions_only": {
                k: {"docstring_lines": v["docstring_lines"],
                    "writes_to_disk": v["writes_to_disk"]}
                for k, v in sorted(docstring_only.items())},
            "readonly_gates_exempt": sorted(readonly_gates),
            "non_executable_mentions_n": len(references)}
    if listed is None:
        idx1["status"] = "NOT FOUND - the enumeration is gone or reworded"
        drift.append(idx1)
    else:
        missing = sorted(set(actual) - set(listed))
        stale = sorted(set(listed) - set(actual))
        idx1["missing_from_claude_md"] = [
            {"path": m, "writes_to_disk": actual[m]["writes_to_disk"],
             "first_lines": actual[m]["lines"][:5]} for m in missing]
        idx1["listed_but_no_longer_matching"] = stale
        idx1["status"] = "OK" if not (missing or stale) else "DRIFTED"
        if missing or stale:
            drift.append(idx1)

    # --- index 2: the decision pointer -------------------------------------
    nxt = next_free_decision(text)
    top = highest_decision_in_register()
    idx2 = {"index": "CLAUDE.md 'Next free number'",
            "claude_md_says_next_free": nxt,
            "highest_in_register": top,
            "register_implies_next_free": None if top is None else top + 1}
    idx2["status"] = ("OK" if nxt is not None and top is not None and nxt == top + 1
                      else "DRIFTED")
    if idx2["status"] != "OK":
        drift.append(idx2)

    result = {"checked": [idx1, idx2], "drift_count": len(drift), "drift": drift}

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("=== CLAUDE.md index verification ===\n")
        print(f"[1] D:\\ hardcode enumeration          {idx1['status']}")
        print(f"    scope: executables with a D: path outside a comment or docstring;"
              f" read-only tools/ gates exempt")
        print(f"    listed {idx1['listed_n']}   live hardcodes found {idx1['actual_n']}"
              f"   (excluded: "
              f"{len(idx1['executables_with_provenance_comments_only'])} executables whose "
              f"only D: mention is a provenance comment, "
              f"{idx1['non_executable_mentions_n']} docs/JSON that quote a path)")
        for m in idx1.get("missing_from_claude_md", []):
            flag = "  <-- AND IT WRITES TO D:" if m["writes_to_disk"] else ""
            print(f"    MISSING: {m['path']} (lines {m['first_lines']}){flag}")
        for s in idx1.get("listed_but_no_longer_matching", []):
            print(f"    LISTED BUT NOT FOUND: {s}")
        for k, v in idx1["executables_with_docstring_mentions_only"].items():
            kind = "  <-- and it can WRITE" if v["writes_to_disk"] else ""
            print(f"    excused, DOCSTRING only: {k} lines {v['docstring_lines']}{kind}")
        for k in idx1["readonly_gates_exempt"]:
            print(f"    excused, read-only tools/ gate (no write call): {k}")
        print(f"\n[2] decision pointer                  {idx2['status']}")
        print(f"    CLAUDE.md next free: D{idx2['claude_md_says_next_free']}   "
              f"register highest: D{idx2['highest_in_register']}   "
              f"implies next free: D{idx2['register_implies_next_free']}")
        if idx1["status"] == "DRIFTED" and idx1.get("missing_from_claude_md"):
            print("\n--- corrected list, to paste into CLAUDE.md (a human pastes it, "
                  "in a commit that says what moved) ---")
            print("Live D:\\ hardcodes exist in: "
                  + ", ".join(sorted(actual)) + ". Never execute those files until a "
                  "remediation phase clears them.")
        print(f"\n{'DRIFT: ' + str(len(drift)) + ' index(es)' if drift else 'ALL INDICES CLEAN'}")

    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
