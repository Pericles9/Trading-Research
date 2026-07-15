"""Diff two Phase 0a inventory manifests (before/after) and classify every
path as unmoved, moved (matched by identical size when the path disappears
from one side and a same-size file appears on the other), new, or missing.

Verification Block repro command for prompts/phase_0a.md T5.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def diff(before: dict, after: dict) -> dict:
    before_by_path = {f["path"]: f for f in before["files"]}
    after_by_path = {f["path"]: f for f in after["files"]}

    unmoved = []
    changed = []
    missing_paths = []
    new_paths = []

    for path, rec in before_by_path.items():
        if path in after_by_path:
            after_rec = after_by_path[path]
            if after_rec["size_bytes"] == rec["size_bytes"]:
                unmoved.append(path)
            else:
                changed.append({"path": path, "before_size": rec["size_bytes"], "after_size": after_rec["size_bytes"]})
        else:
            missing_paths.append(rec)

    for path, rec in after_by_path.items():
        if path not in before_by_path:
            new_paths.append(rec)

    # Attempt to match missing/new pairs by identical size as candidate moves.
    moved = []
    unexplained_missing = []
    new_by_size: dict[int, list[dict]] = {}
    for rec in new_paths:
        new_by_size.setdefault(rec["size_bytes"], []).append(rec)

    matched_new_paths = set()
    for rec in missing_paths:
        candidates = [c for c in new_by_size.get(rec["size_bytes"], []) if c["path"] not in matched_new_paths]
        if candidates:
            match = candidates[0]
            matched_new_paths.add(match["path"])
            moved.append({"from": rec["path"], "to": match["path"], "size_bytes": rec["size_bytes"]})
        else:
            unexplained_missing.append(rec["path"])

    truly_new = [r["path"] for r in new_paths if r["path"] not in matched_new_paths]

    return {
        "before_count": before["count"],
        "after_count": after["count"],
        "unmoved_count": len(unmoved),
        "moved_count": len(moved),
        "moved": moved,
        "new_count": len(truly_new),
        "new_paths": sorted(truly_new),
        "changed_in_place_count": len(changed),
        "changed_in_place": changed,
        "unexplained_missing_count": len(unexplained_missing),
        "unexplained_missing": sorted(unexplained_missing),
    }


def main(before_path: str, after_path: str, out_path: str) -> None:
    before = load(before_path)
    after = load(after_path)
    result = diff(before, after)
    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if not isinstance(v, list)}, indent=2))
    if result["unexplained_missing_count"]:
        print("HARD STOP: unexplained missing files:", result["unexplained_missing"])
        sys.exit(1)


if __name__ == "__main__":
    b = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0a/artifacts/inventory_before.json"
    a = sys.argv[2] if len(sys.argv) > 2 else "results/phase_0a/artifacts/inventory_after.json"
    o = sys.argv[3] if len(sys.argv) > 3 else "results/phase_0a/artifacts/inventory_diff.json"
    main(b, a, o)
