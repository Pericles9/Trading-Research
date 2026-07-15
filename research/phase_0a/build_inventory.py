"""Walk the Phase 0a in-scope directories and write a per-file inventory manifest.

Scope: archive/, notebooks/, research/, results/, and top-level loose files.
Excluded: data/, .venv/, hawkes-ofi-impact/, scanner-epg-momentum/, .git,
__pycache__, node_modules, .pytest_cache (per prompts/phase_0a.md T1).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCOPE_DIRS = ["archive", "docs", "notebooks", "prompts", "research", "results"]
EXCLUDE_DIR_NAMES = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "data"}
EXCLUDE_TOP_LEVEL = {"data", ".venv", "hawkes-ofi-impact", "scanner-epg-momentum"}


def iter_scope_files():
    for name in SCOPE_DIRS:
        base = REPO_ROOT / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts):
                continue
            yield path

    for path in REPO_ROOT.iterdir():
        if path.is_file():
            yield path


def build_record(path: Path) -> dict:
    stat = path.stat()
    rel = path.relative_to(REPO_ROOT).as_posix()
    return {
        "path": rel,
        "size_bytes": stat.st_size,
        "extension": path.suffix,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def main(out_path: str) -> None:
    records = sorted((build_record(p) for p in iter_scope_files()), key=lambda r: r["path"])
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": current_commit(),
        "scope_dirs": SCOPE_DIRS,
        "excluded_top_level": sorted(EXCLUDE_TOP_LEVEL),
        "excluded_dir_names": sorted(EXCLUDE_DIR_NAMES - {".venv", "data"}),
        "count": len(records),
        "files": records,
    }
    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(records)} records to {out}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0a/artifacts/inventory_before.json"
    main(target)
