Regenerate the current phase's `digest.json` from its artifacts.

Steps:
1. Determine the current phase from the checked-out branch name (`phase/{x}`) or, if ambiguous, ask.
2. Read every file under `results/phase_{x}/artifacts/` and `results/phase_{x}/charts/`, plus `results/phase_{x}/REPORT.md`.
3. Rebuild `results/phase_{x}/digest.json` with these required fields (per `research/phase_0b/validate_digest.py`, the best-available reconstruction of the digest contract — no canonical standard document was found; see `CLAUDE.md`'s Pointers section):
   - `phase`, `status`, `summary` — short, factual.
   - `headline_metrics` — a list; every entry needs a `chart` field pointing at the chart file that backs it (Evidence Standard: no metric without a chart).
   - `decisions_log` — every judgment call made this phase, with a reason.
   - `surprises` — anything found that no prior doc mentioned. Empty is suspicious on a phase with real investigation — double check before leaving it empty.
   - `output_files` — every deliverable this phase produced, with a status.
4. Run `python -m research.phase_0b.validate_digest results/phase_{x}/digest.json` and report the result. Do not silently fix a failing check by weakening the validator — report the failure.
5. Do not edit a *different* phase's digest.json under any circumstance.
