# archive/

## Purpose

Read-only historical records. Contains output artifacts from completed or superseded
research runs: parameter files, backtest results, calibration outputs, validation reports,
and an inventory of what's here and why.

Nothing in `archive/` should be edited. If an archived result needs to be referenced,
cite it by path. If an archived approach needs to be revived, copy the relevant files
to the active project and work from there.

## Key Files

| File | Purpose |
|------|---------|
| `INVENTORY.md` | Full catalog of archived run artifacts — what's here, sizes, what produced it |
| `runs/v5_battle/battle_20260209_214309/v5_Battle_Results.md` | Canonical v5 Battle Royale results (200-event full run) |
| `runs/v53_temporal_beta/batch_20260210_185257/v5_3_Final_Report.md` | v5.3 Temporal Beta final report |
| `runs/stat_validation/` | Statistical validation reports (4 runs) |
| `misc/` | One-off scripts, audit reports, lead-lag config |

## Relevant Tags

- `type/results`, `type/research`
- `project/v5-strategy`, `project/src-core`
- `status/complete`, `status/abandoned`

## Conventions

- Never modify files in `archive/` — treat as immutable
- `runs/` directories are named `{run_type}_{YYYYMMDD_HHMMSS}` or `{batch_YYYYMMDD_HHMMSS}`
- Results files inside run directories use whatever naming the script produced
- `misc/` is for non-run artifacts (configs, audit files, one-offs)

## Notes

- `research/brainstorm/v5_Battle_Results.md` is a symlink to the canonical in
  `archive/runs/v5_battle/battle_20260209_214309/` — edit the archive copy if needed
- `research/brainstorm/v5_3_Final_Report.md` is similarly a symlink to `archive/runs/`
- The archive holds ~685 artifacts (~1.5 GB) — most are parquet/pkl and off-limits
- `INVENTORY.md` is the index — check it before searching the archive manually
