---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
last_reviewed: 2026-04-04
linked_code: "[[prepare_database_split.py]]"
---

# prepare_database_split.py

## Purpose
CLI tool for migrating storage out of the research repo into an external database root. Creates the target directory scaffold, writes a `migration_manifest.json` with dataset sizes and source/target mapping, emits an `env.example` for environment variable configuration, and optionally copies all datasets.

## Key Functions / Classes
| Name | Type | Description |
|------|------|-------------|
| `main()` | function | CLI entry point — parses args and orchestrates the migration |
| `_size_bytes(path)` | function | Recursively computes bytes for a file or directory |
| `_copy_path(src, dst)` | function | Copies a file or directory tree to target |

## Inputs / Outputs
**CLI arguments:**
- `--target-root PATH` (required) — destination storage root
- `--data-root PATH` (optional) — source data root; defaults to resolved `MOM_DB_DATA_ROOT`
- `--include DATASET` (repeatable) — limit to specific dataset dirs
- `--copy` — physically copy files; without this, only scaffolding + manifest are created

**Outputs written:**
- `{target-root}/data/{dataset}/` — directory scaffold for each dataset
- `{target-root}/migration_manifest.json` — JSON manifest with sizes and copy status
- `{target-root}/env.example` — ready-to-use env var template

## Dependencies
- stdlib: `argparse`, `json`, `shutil`, `pathlib`
- `src/data/paths.resolve_data_root`

## Usage Example
```bash
# Plan only (no copy)
python -m src.data.prepare_database_split --target-root D:/mom_db_storage

# Plan + copy all data
python -m src.data.prepare_database_split --target-root D:/mom_db_storage --copy

# Copy only specific datasets
python -m src.data.prepare_database_split --target-root D:/mom_db_storage --copy --include filtered --include daily
```

## Notes
- After migration, set the three env vars from `env.example` — the rest of the codebase uses `src/data/paths.py` for all resolution and will pick them up automatically.
- `DATASET_DIRS` constant lists all 12 known dataset subdirectories.

## Related
- [[Data Paths]] — path resolution used during migration
- [[data/Schema.md]] — documents the structure being migrated
