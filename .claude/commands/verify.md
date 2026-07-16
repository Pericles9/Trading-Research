Re-run every reproduction command recorded in the current phase's digest/report and diff the numbers against what was recorded.

Steps:
1. Determine the current phase from the checked-out branch name (`phase/{x}`).
2. Read `results/phase_{x}/digest.json` and `results/phase_{x}/REPORT.md`. Collect every repro command (Verification Block rows, `Repro` columns, explicit `python -m ...` invocations tied to a specific claimed number).
3. Re-run each command exactly as recorded — do not "improve" it, do not change flags.
4. For each one, compare the freshly observed value against the recorded value. Report a table: claim, recorded value, observed value, match (yes/no).
5. If anything doesn't match: this is a finding, not something to silently reconcile. State which command, what changed, and both values. Do not edit the digest to make it match without being asked — a stale digest is itself the finding.
6. If the underlying data changed since the phase ran (e.g. a table grew), say so explicitly rather than implying the original number was wrong.
