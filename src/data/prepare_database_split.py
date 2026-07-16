# --- Provenance (Phase 0b T2) ---
# Recovered from D:\Trading Research\src\data\prepare_database_split.py
# (untracked on D: - never git-added in that repo; no commit hash applies).
# Source mtime: 2026-03-14. Content unmodified from the D: copy. Note: the
# docstring's usage example below still shows a D:-based --target-root path;
# that is example text only, not a live default (actual defaults come from
# paths.py, which is already E:-correct).
# ---------------------------------
"""Prepare data relocation into a dedicated database directory.

This command creates a migration manifest and optional copy plan for moving
storage out of the research/project repo and into an external database root.

Examples:
    python -m src.data.prepare_database_split --target-root D:/mom_db_storage
    python -m src.data.prepare_database_split --target-root D:/mom_db_storage --copy
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from src.data.paths import resolve_data_root

DATASET_DIRS = [
    "duckdb",
    "filtered",
    "daily",
    "minute",
    "second10",
    "quote_data",
    "trade_data",
    "momentum_events",
    "metadata",
    "market-hours",
    "symbol-properties",
    "nautilus_catalog",
]


def _size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def _copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare data migration to external database root")
    parser.add_argument("--target-root", type=Path, required=True, help="Destination storage root")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=resolve_data_root(),
        help="Source data root (default: resolved MOM_DB_DATA_ROOT or repo data/)",
    )
    parser.add_argument(
        "--include",
        action="append",
        choices=DATASET_DIRS,
        help="Limit migration prep to specific dataset dirs (repeatable)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files now; without this flag, only directories + manifest are created",
    )
    args = parser.parse_args()

    data_root = args.data_root.expanduser().resolve()
    target_root = args.target_root.expanduser().resolve()
    target_data_root = target_root / "data"

    includes = args.include or DATASET_DIRS

    target_data_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "source_data_root": str(data_root),
        "target_data_root": str(target_data_root),
        "copied": bool(args.copy),
        "datasets": [],
    }

    for name in includes:
        src = data_root / name
        dst = target_data_root / name
        src_exists = src.exists()
        size_bytes = _size_bytes(src)
        entry = {
            "dataset": name,
            "source": str(src),
            "target": str(dst),
            "exists": src_exists,
            "size_bytes": size_bytes,
        }

        if src_exists:
            dst.mkdir(parents=True, exist_ok=True)
            if args.copy:
                _copy_path(src, dst)
                entry["copied"] = True
            else:
                entry["copied"] = False
        else:
            entry["copied"] = False

        manifest["datasets"].append(entry)

    manifest_path = target_root / "migration_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    env_example = target_root / "env.example"
    env_example.write_text(
        "\n".join(
            [
                f"MOM_DB_DATA_ROOT={target_data_root.as_posix()}",
                f"MOM_DB_DATABASE_ROOT={(target_data_root / 'duckdb').as_posix()}",
                f"MOM_DB_DUCKDB_PATH={(target_data_root / 'duckdb' / 'main.duckdb').as_posix()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Prepared migration target: {target_root}")
    print(f"Manifest: {manifest_path}")
    print(f"Env template: {env_example}")


if __name__ == "__main__":
    main()
