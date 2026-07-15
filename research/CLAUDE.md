# research/

## Purpose

The Obsidian research vault. This folder contains companion documentation for every `src/`
module, formalized alpha hypotheses, phase pipeline summaries, brainstorm notes, and
archived signal forge / alpha hunter work. It is the human-readable layer on top of the
codebase — if you want to understand what a module does without reading code, start here.

The vault is navigable via Obsidian (graph view, backlinks, wikilinks). It is also fully
searchable as plain markdown.

## Key Files

| File | Purpose |
|------|---------|
| `00-Index.md` | Vault map and research pipeline diagram — start here |
| `ReadMe.md` | Vault entry point and orientation |
| `alpha-hypotheses/Scanner-Hawkes-OFI Impact.md` | Active alpha spec (symlink to canonical in `hawkes-ofi-impact/docs/`) |
| `Hawkes Engine.md` | Companion doc for `src/models/hawkes_engine.py` |
| `Signal Processor.md` | Companion doc for `src/signals/signal_processor.py` |
| `V5 Backtest Runner.md` | Companion doc for `src/backtest/v5_runner.py` |
| `DuckDB Connection.md` | Companion doc for `src/data/db.py` |
| `DuckDB Ingest.md` | Companion doc for `src/data/ingest.py` |
| `brainstorm/` | Raw idea dumps, phase summaries, informal working notes |
| `phase_*_*/` | Phase pipeline working directories (parquet + markdown per phase) |

## Relevant Tags

All four tag dimensions apply here. Module companion docs use `type/implementation`.
Brainstorm content uses `type/idea`. Phase summaries use `type/research`.

## Conventions

- All document names: `Title Case With Spaces.md`
- One companion doc per `src/` module (not for calibration scripts or one-off files)
- Wikilinks use `[[Document Name]]` (no path prefix — Obsidian resolves by name)
- Do not create docs here for `hawkes-ofi-impact/` modules — those live in
  `hawkes-ofi-impact/docs/`

## Notes

- `alpha-hypotheses/Scanner-Hawkes-OFI Impact.md` is a symlink — edit the canonical in
  `hawkes-ofi-impact/docs/` instead
- `Tradeable Setup Filter.md` is a symlink — same rule applies
- `brainstorm/v5_Battle_Results.md` and `brainstorm/v5_3_Final_Report.md` are symlinks
  to their canonical copies in `archive/runs/`
- Phase pipeline directories (`phase_1_context/`, `phase_2_signal_forge/`, etc.) contain
  parquet files that are off-limits for reading — work with the markdown docs only
