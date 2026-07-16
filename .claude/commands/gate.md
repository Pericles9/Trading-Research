Print the current phase's escalation check table: every criterion from the phase prompt, its current observed value, and pass/fail.

Steps:
1. Determine the current phase from the checked-out branch name (`phase/{x}`) and read `prompts/phase_{x}.md`'s "Escalation Criteria" table.
2. For each row, determine the current observed value — from `results/phase_{x}/artifacts/`, the digest, or a fresh check if neither has it yet. Do not guess; if a criterion can't be evaluated yet because its task hasn't run, say so explicitly rather than marking it pass.
3. Print a table: condition, threshold, observed, pass/fail.
4. If anything is currently failing (an unresolved hard stop), say so plainly at the top — do not bury it. This command is a status check, not a fix — it never modifies anything.
