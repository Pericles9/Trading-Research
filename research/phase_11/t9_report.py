"""T9 - digest, REPORT.md, and the cross-phase copy.

Assembles from the committed artifacts. Adds no new measurement.

Escalation rows that bind this file:
  18   no evaluative sentence. Measurements with n, descriptions of what a named
       chart shows, and selections from a pre-registered reading rule only.
  18a  the T3 reading-rule row must be named.
  27   no spread or cost in one unit alone; no T-1/T-3 spread used as a proxy
       for detection-time cost.
  29   the standing qualifier verbatim in the T7 section.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil

A = pathlib.Path("results/phase_11/artifacts")
R = pathlib.Path("results/phase_11")
CFG = json.loads(pathlib.Path("config/phase_11.json").read_text())
QUAL = CFG["standing_qualifier"]["text"]

BANNED = ["good", "bad", "strong", "weak", "promising", "disappointing", "encouraging",
          "viable", "unviable", "sufficient", "insufficient", "supports", "undermines",
          "confirms the thesis", "recommend", "should adopt", "we should"]


def load(name):
    p = A / name
    return json.loads(p.read_text()) if p.exists() else None


def cfg_hash() -> str:
    b = pathlib.Path("config/phase_11.json").read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def check_row_18(text: str) -> list[str]:
    """Row 18 guard. Runs on the generated report before it is written."""
    low = text.lower()
    hits = []
    for w in BANNED:
        i = low.find(w)
        while i != -1:
            ctx = text[max(0, i - 70):i + 70].replace("\n", " ")
            # allow the words where they name the RULE or the escalation row itself
            if not any(k in ctx.lower() for k in
                       ("escalation row", "banned", "reading rule", "row 18",
                        "no evaluative", "forbid")):
                hits.append(f"{w!r} :: ...{ctx}...")
            i = low.find(w, i + 1)
    return hits


def main() -> None:
    t1, t2 = load("t1_quote_table_identity.json"), load("t2_state_census.json")
    t2e, t3 = load("t2e_i_implied_price.json"), load("t3_alignment_sweep.json")
    t4b, t5 = load("t4b_ordering_audit.json"), load("t5_cache_integrity.json")
    t6, t7, t8 = load("t6_effective_spread.json"), load("t7_cost_vs_capture.json"), load("t8_impact.json")

    digest = {
        "phase": "11", "date": "2026-08-18", "config_hash": cfg_hash(),
        "governing_spec": CFG["spec"]["governing"],
        "escalation_rows_enumerated": CFG["spec"]["escalation_rows"],
        "passes_spent": (t5 or {}).get("pass", {}).get("passes_spent", 0),
        "stage_a": {
            "t1_identity": (t1 or {}).get("t1a_consolidated_best_quote", {}).get("reading"),
            "t2_row_5": (t2 or {}).get("escalation_row_5"),
            "t3_reading_rule_row": (t3 or {}).get("t3b_reading_rule_selection", {}).get("row_selected"),
        },
        "stage_b": {
            "t5": (t5 or {}).get("pass"), "filter_waterfall": (t5 or {}).get("filter_waterfall"),
            "t5c": (t5 or {}).get("t5c_integrity"), "t4c": (t5 or {}).get("t4c_tie_audit"),
            "t6_by_segment_latency": (t6 or {}).get("by_segment_latency"),
            "t7_named_cell": (t7 or {}).get("named_cell"),
            "t7_reading_rule_row": (t7 or {}).get("t7e_i_reading_rule_row"),
            "t8_unclassifiable": (t8 or {}).get("classification", {}).get("unclassifiable_overall_share"),
        },
        "standing_qualifier": QUAL,
        "deviations_on_record": [
            "Tick rule is the SIMPLE TICK TEST (immediately preceding trade price), not "
            "Lee & Ready's walk-back to the last differing price. Conservative: it can "
            "only raise the unclassifiable share, which is reported per cell and never "
            "dropped.",
            "Charts 05 and 09 ship as stacked bp/cents panels, not twin axes (A3-1, "
            "Phase 9 chart 06 precedent).",
            "T6e participant-basis robustness is DEV-TIER only - a full-tier recompute "
            "would need a second pass, which escalation row 12 forbids.",
            "T5a's dev-tier extrapolation (2,271 s) did not predict the full-tier pass. "
            "Dev v4 is a small dedicated table and never exercised the query plan the "
            "full tier takes.",
        ],
    }
    (R / "digest.json").write_text(json.dumps(digest, indent=2, default=str), encoding="utf-8")

    nc = (t7 or {}).get("named_cell", {})
    fw = (t5 or {}).get("filter_waterfall", {})
    md = f"""# Phase 11 — Instrument Validation and the Cost Stack on the Detection Cell

**Config hash:** `{cfg_hash()}` · **Passes spent:** {digest['passes_spent']} · **Rows enumerated:** {CFG['spec']['escalation_rows']}

Governing spec: {CFG['spec']['governing']}

---

## Stage A — is the instrument usable?

**T1 — identity.** {(t1 or {}).get('t1a_consolidated_best_quote', {}).get('reading', 'n/a')}
RTH median 13 distinct bid venues, share of rows with `bid_exchange != ask_exchange`
median 0.884 (min 0.618), 0 single-venue events, 0 null-exchange rows, n = 50 events.
`sip_timestamp` null-or-zero = 0 on all three denominators. Resolution: min 49 ns,
median 80 ns. Epoch and timezone confirmed against XNYS — quotes/minute step from
2,808 to 12,835 at the open minute and fall from 6,949 to 878 at the close, 0 rows on
non-session dates. Chart 01.

`indicators` is populated on 6,274,517 of 7,061,655 source rows (88.85%), not null —
contradicting the two-row sample the prompt carried in. No condition-code dictionary
exists on disk, so the codes stay opaque (row 20, not a stop). The source parquet is
stored reverse-chronological: `sip_timestamp` decreases across 99.97% of consecutive
file rows at the median event, on all 50 events.

**T2 — state census.** Row 5: `state_hard_unusable` clock-time share on the T=0 RTH
segment, median across 50 events = {(t2 or {}).get('escalation_row_5', {}).get('observed_median', 0):.3g}
(1.3e-08, i.e. zero to 6 dp), threshold 0.25 — {(t2 or {}).get('escalation_row_5', {}).get('verdict', 'n/a')}. The three-way
partition sums to 1.0 to 0.0 deviation. Charts 02, 03.

**T2e / T2e-i — quoted spread and implied price.** RTH median time-weighted quoted
spread 165.0 -> 127.6 -> 83.9 bp across T-3 / T-1 / T=0 (-49.1%); the same cells in
cents 3.64 -> 3.43 -> 3.79 (+4.1%). Median per-event implied price $2.505 -> $2.820 ->
$3.796 (+51.5%). n = 50 at every point. The basis-point figure falls; the cents figure
does not; the implied price rises. Chart 03.

**T3 — alignment.** The curve matches **pre-registered reading-rule row 1**: maximum at
δ = 0 or immediately before it, decaying smoothly either side — the two tables are
aligned and the contemporaneous quote is the reference midpoint. Stated on both
timestamp bases, both sessions, both segments. Chart 04.

---

## Stage B — the cost stack

**Filter waterfall.** Detection universe {fw.get('detection_universe', 0):,} →
`quotes_ingested` {fw.get('quotes_ingested_true', 0):,} → excluded
{fw.get('quotes_ingested_false_excluded', 0):,} ({fw.get('quotes_ingested_false_share', 0):.4%}),
row 10 threshold 20% — {fw.get('row_10_verdict', 'n/a')}. Coverage read from the Phase 4/5 materializations (D15).

**T7 — cost against capture.**

> {QUAL}

Named cell (`fixed_horizon`, RTH, latency 5 min, hold 30 min), n = {nc.get('n', 0):,}:

| cost multiple | median ratio |
|---|---|
| 1× (the sole row-11 trigger) | **{nc.get('median_ratio_1x', 0):.4f}** |
| 1.5× (equal prominence, A2-5) | **{nc.get('median_ratio_1_5x', 0):.4f}** |
| 2× | {nc.get('median_ratio_2x', 0):.4f} |

Share of events where round-trip cost exceeds realized capture outright:
**{nc.get('share_cost_exceeds_capture', 0):.2%}**. Kill threshold
{nc.get('kill_threshold', 0)} — row 11 **{nc.get('escalation_row_11', 'n/a')}**.

**Pre-registered reading rule (T7e-i):** {(t7 or {}).get('t7e_i_reading_rule_row', 'n/a')}

Of the {nc.get('n', 0):,} rows in the named cell, {nc.get('n_ratio_defined', 0):,} have a
defined ratio; realized capture is non-positive on
{nc.get('share_capture_nonpositive', 0):.2%} of the cell, and the median ratio above is
computed only on the complement. Median round-trip cost in the named cell is
{nc.get('median_rt_cost_bp', 0):.2f} bp and {nc.get('median_rt_cost_cents', 0):.3f} cents
(D19: both units, never one alone). Charts 06, 07.

**T6 — effective spread at the detection anchor.** RTH, at the T4-selected offset
(δ = 0, sip basis, D16), size-weighted per bar:

| latency | n | bp | cents | share of detection price |
|---|---|---|---|---|
| 0 (impossible upper bound) | 10,408 | 97.07 | 3.060 | 0.956% |
| 1 | 10,292 | 90.29 | 2.803 | 0.904% |
| 5 | 10,087 | 75.80 | 2.385 | 0.757% |
| 15 | 9,669 | 65.69 | 2.096 | 0.656% |
| 30 | 9,384 | 60.50 | 1.958 | 0.605% |

Latency 0 is a physical impossibility and is the upper bound, not an operating point
(Phase 8 / D7). Premarket and post are in the artifact and on chart 05; the decision
rests on the RTH cell alone (D18). Chart 05.

**T8 — impact and classification.** Overall unclassifiable share
{(t8 or {}).get('classification', {}).get('unclassifiable_overall_share', 0):.4%},
reported per cell and never dropped. Distributions only — no regression and no fitted
impact exponent. Charts 08, 09.

**T4c — tie dependence (escalation row 30, FIRED).**
{CFG['t4c_tie_audit']['row_30_resolution']['caveat_required_in_report']}
Cooper accepted option (a) on 2026-08-18: proceed carrying this as a stated caveat, with
no frozen artifact rebuilt (row 32 respected).

---

## Escalation check

| row | quantity | observed | threshold | verdict |
|---|---|---|---|---|
| 1 | working tree dirty at T0a | dirty, then clean | any | fired once, resolved |
| 2 | T0c audit failure | fired on the pass-budget contradiction, resolved by option (ii) | any | resolved |
| 3 | consolidated vs per-venue | established | any | does not fire |
| 4a | sip null-or-zero | 0.0 | > 1% | does not fire |
| 5 | hard_unusable RTH median | 0.000000 | > 0.25 | does not fire |
| 6 | alignment curve flat | peak−min 0.1902 | any | does not fire |
| 7 | premarket vs RTH peak rung | 7 rungs | any | fired, not a stop |
| 10 | quotes_ingested FALSE | 0.7613% | > 20% | does not fire |
| 11 | kill threshold, named cell 1× | 0.1608 | ≥ 0.50 | does not fire |
| 20 | condition-code dictionary | none on disk | any | fired, not a stop |
| 21 | era null-pattern gap | 6.21 pp | > 20 pp | does not fire |
| 24 | cache required columns | none missing | any | does not fire |
| 25 | ordering class (b)/(c) | 0 of 15 | any | does not fire |
| 26 | pass exceeds ceiling | projected 8.10 h vs 6.00 h | > ceiling | **fired**, one-off exception accepted |
| 30 | tie price error p95 | **123.047 bp** | > 25 bp | **fired**, option (a) accepted |
| 31 | aggregate-function class (b)/(c) | 0 of 5 | any | does not fire |

---

## Deviations on record

""" + "\n".join(f"- {x}" for x in digest["deviations_on_record"]) + """

---

## Verification

Every number above is reproducible from the committed artifacts in
`results/phase_11/artifacts/` at the config hash printed at the top.
"""
    hits = check_row_18(md)
    if hits:
        print("ROW 18 GUARD FIRED - report not written:")
        for h in hits[:10]:
            print("  ", h)
        raise SystemExit("escalation row 18")
    (R / "REPORT.md").write_text(md, encoding="utf-8")
    pathlib.Path("results/reports").mkdir(parents=True, exist_ok=True)
    shutil.copy(R / "REPORT.md", "results/reports/phase_11_report.md")
    print("wrote digest.json, REPORT.md, results/reports/phase_11_report.md")
    print("row 18 guard: clean")


if __name__ == "__main__":
    main()
