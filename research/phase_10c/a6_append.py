"""Append the A1.4 proposal, the discriminant test, and the float64 finding."""
import importlib.util as ilu
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
p = rel(f"{ART}/a6_conditions_analysis.json")
o = json.load(open(p, encoding="utf-8"))

o["A1_closing_print"]["A1_2_distribution"]["exclusively_after_close_codes"] = {
    "15": 208, "8": 83, "9": 76, "12": 30, "2": 1}
o["A1_closing_print"]["A1_2_distribution"]["straddling_codes"] = {
    "41": 279, "37": 245, "14": 196, "7": 2}

o["A1_closing_print"]["A1_4_proposal"] = {
    "status": "PROPOSED on empirical grounds; Cooper sets it",
    "proposed_code_set": [8, 9, 15],
    "discriminant_test": {
        "method": ("anchor print looked up by NEAREST match, its codes compared against the three "
                   "genuine after-hours anchors"),
        "ACET 2020-09-18 (closing cross)": {"codes": [8, 9, 41], "size": 229769, "price": 21.40},
        "OST 2024-06-13 (after hours)": {"codes": [14, 12, 41], "size": 304, "price": 0.55},
        "CELH 2020-08-06 (after hours)": {"codes": [12], "size": 215, "price": 21.32},
        "BMR 2024-03-13 (after hours)": {"codes": [12, 37], "size": 5, "price": 7.51}},
    "justification": (
        "Codes 8 and 9 occur ONLY after the close in the +/-1 s window (83 and 76 occurrences) and "
        "appear on the ACET auction print but on NONE of the three genuine after-hours anchors. "
        "Code 15 is likewise exclusively after close (208) and carries ACET's twin print -- same "
        "price, same 229,769 shares, 92 microseconds later -- so including it catches the closing "
        "print proper as well as the auction trade."),
    "why_exclusivity_alone_is_not_enough": (
        "Code 12 is ALSO exclusively after close (30 occurrences) but appears on all three "
        "ordinary after-hours anchors and not on ACET. 'Occurs only after the close' therefore "
        "does not by itself mark an auction print; the discriminant is {8, 9, 15}."),
    "size_signature_corroborates": (
        "229,769 shares against 304, 215 and 5 for the after-hours anchors -- consistent with an "
        "auction cross. Reported as corroboration, not as part of the proposed rule."),
    "residual_caveat": (
        "This is an EMPIRICAL identification, not a semantic one. The archive ships no code "
        "dictionary and the environment is offline (D14), so what codes 8, 9 and 15 are called "
        "cannot be confirmed here. The set discriminates correctly on every case in the cohort; "
        "confirming it means the intended thing still needs the dictionary.")}

o["A1_closing_print"]["A1_5_float64_anchor_precision"] = {
    "finding": ("det_ns_poll0 and every det_ns_* column in v2_r13_detection.parquet are stored as "
                "float64. At epoch-nanosecond magnitude float64 spacing is 256 ns, so an anchor "
                "timestamp cannot round-trip exactly to the print that produced it."),
    "consequence": ("An exact join on the anchor timestamp silently returns nothing -- it did, on "
                    "the first run of this discriminant test. Nearest-match within a microsecond "
                    "recovers the print with a 0 ns residual in all four cases."),
    "materiality": ("Immaterial to Phase 10c results, which measure at millisecond scale and use "
                    "the anchor only as an origin. It matters for any exact join on the anchor, "
                    "so it is recorded rather than left to be rediscovered.")}

o["D_migration"]["offsetting_swaps_found"] = {
    "1.25_to_1.30": {
        "n_changed": 2,
        "events": [{"ticker": "VEEE", "date": "2024-06-25", "from": "rth",
                    "to": "unlabelled (lost its anchor)"},
                   {"ticker": "CODX", "date": "2020-03-11", "from": "premarket", "to": "rth"}],
        "reading": ("The rth marginal is 80 under both variants because VEEE left and CODX "
                    "entered. The identical count concealed two changes -- the same error class "
                    "as the segment table concealing the timing deltas.")}}

c10c.write_json(p, o)
print("appended: proposal {8,9,15}, discriminant test, float64 finding, offsetting swaps")
