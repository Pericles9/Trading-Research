# Reg SHO Rule 201 — trigger check, dev tier (first step only)

**Type:** authorized measurement task, not a numbered phase. Scoped by Cooper's explicit
authorization ("Yes, research Reg SHO 201 as a first step," 2026-09-14) after Phase 12's Stage A
gate fired. **`docs/Universe-Decisions.md` D36** records the authorization's exact scope: a
measurement only, **not** authorization for any short-side strategy work. D5's long-only
constraint stands completely unchanged.

**Rule researched and verified:** `docs/data/reg_sho_201_reference.md`. SEC Regulation SHO Rule
201: a 10%+ intraday decline (measured on traded prices) from the prior day's regular-hours close
triggers a short-sale price-test restriction for the rest of that day and the following day.
Sourced directly from the SEC's own FAQ page, corroborated by a secondary trader-facing explainer.

**Measurement:** for each of the 56 dev events, was Rule 201 triggered on T=0, and what was the
day's maximum intraday decline from the prior close. Previous close computed from tick data (the
last T-1 RTH minute bar's `last_price`), reusing Phase 12's D4-safe construction exactly — never
the spine's quarantined `prev_close` column.

**Result:** 55/56 events had a computable previous close (1 excluded, no T-1 RTH bar — same event
Phase 12's T2b also excluded). **3 of 55 events (5.5%) triggered Rule 201 on T=0.** The median
event's day-low never fell below its own prior close (median max decline: −1.8%, i.e. the low sat
~1.8% *above* prior close) — expected for a momentum-selected cohort whose events are chosen for
sharp upward moves, not declines. The 90th percentile max decline is 4.5%; the single largest
observed decline is 25.2%. Chart: `charts/01_decline_distribution.html`.

**What this does and does not mean, stated because it matters more than usual here.** This is a
factual trigger check, nothing more. It does not evaluate the borrow/locate availability that
would actually be needed to execute a short sale (still unavailable in this checkout — D25's other
named requirement), does not model the restriction's own execution mechanics, and does not
constitute or authorize any short-side strategy work. **No recommendation is made about the short
side.**

## Output files

| File | Status |
|---|---|
| `research/reg_sho_201/t1_trigger_check.py` | committed |
| `research/reg_sho_201/chart_01_decline_distribution.py` | committed |
| `results/reg_sho_201/artifacts/t1_trigger_check.json` | committed |
| `results/reg_sho_201/artifacts/t1_trigger_check.parquet` | gitignored (regenerable) |
| `results/reg_sho_201/charts/01_decline_distribution.html` | committed |
| `results/reg_sho_201/REPORT.md` | this file |
| `results/reports/reg_sho_201_report.md` | copy |
| `docs/data/reg_sho_201_reference.md` | committed (D36) |
| `docs/Universe-Decisions.md`, `CLAUDE.md` | D36 added |
