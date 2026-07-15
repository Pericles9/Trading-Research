"""For every .py file in the Phase 0a scope, record its imports and any
hardcoded path strings pointing at other repo files, including drive-letter
paths (cross-checked against the workspace's dead-drive hardware rule).

Safety net for T3: a file cannot be moved until every reference to it is
known. Also the formal log location for the dead-drive escalation finding.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCOPE_DIRS = ["archive", "docs", "notebooks", "prompts", "research", "results"]
EXCLUDE_DIR_NAMES = {".git", "__pycache__", "node_modules", ".pytest_cache"}

DRIVE_PATH_RE = re.compile(r"[A-Za-z]:\\[^\"'\s]*")
REPO_RELATIVE_RE = re.compile(
    r"(?:archive|notebooks|research|results|data|src)/[^\"'\s]*"
)


def iter_py_files():
    for name in SCOPE_DIRS:
        base = REPO_ROOT / name
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part in EXCLUDE_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts):
                continue
            yield path
    for path in REPO_ROOT.glob("*.py"):
        yield path


def extract_imports(tree: ast.Module) -> list[str]:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ("." * node.level)
            imports.append(module)
    return sorted(set(imports))


def extract_path_strings(source: str) -> dict:
    drive_paths = sorted(set(DRIVE_PATH_RE.findall(source)))
    repo_relative = sorted(set(REPO_RELATIVE_RE.findall(source)))
    return {"drive_letter_paths": drive_paths, "repo_relative_paths": repo_relative}


def main(out_path: str) -> None:
    records = []
    drive_path_files = []

    for path in sorted(iter_py_files()):
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")

        try:
            tree = ast.parse(source, filename=rel)
            imports = extract_imports(tree)
            parse_error = None
        except SyntaxError as exc:
            imports = []
            parse_error = str(exc)

        paths = extract_path_strings(source)
        record = {
            "path": rel,
            "imports": imports,
            "parse_error": parse_error,
            **paths,
        }
        records.append(record)
        if paths["drive_letter_paths"]:
            drive_path_files.append({"path": rel, "matches": paths["drive_letter_paths"]})

    manifest = {
        "count_py_files": len(records),
        "drive_letter_path_finding": {
            "description": (
                "Hardware-rule escalation (prompts/phase_0a.md escalation table): "
                "files referencing a drive-letter path other than the workspace root E:. "
                "Not fixed in this phase - flagged only."
            ),
            "count_files": len(drive_path_files),
            "files": drive_path_files,
        },
        "files": records,
    }
    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(records)} py-file records ({len(drive_path_files)} with drive-letter paths) to {out}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0a/artifacts/reference_map.json"
    main(target)
