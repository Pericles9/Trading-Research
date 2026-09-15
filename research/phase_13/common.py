"""Phase 13 shared plumbing: config load, DuckDB connection, cfg hash."""
from __future__ import annotations

import hashlib
import json
import pathlib

from src.data.db import get_connection
from src.data.paths import resolve_data_root

CFG = "config/phase_13.json"
ART = "results/phase_13/artifacts"
CHARTS = "results/phase_13/charts"
# Routed through resolve_data_root(), not a cwd-relative literal -- see Build F1's
# common.py for the bug this class of mistake caused (data written to a worktree-local
# folder instead of the shared canonical root) and its fix, 2026-09-12/13.
FUNDAMENTALS_ROOT = str(pathlib.Path(resolve_data_root()) / "fundamentals").replace("\\", "/")


def load_cfg() -> dict:
    with open(CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    b = pathlib.Path(CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def connect(read_only: bool = True):
    return get_connection(read_only=read_only)


def write_json(path: str, obj: dict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
