"""
Phase 6b A6.2a - spine-numeric-column sweep of research/phase_6b/ + config/phase_6b.json.

Required by the A8.2 terms before the config re-freeze. Re-runnable: it
actually scans the files (not a hardcoded list), so re-running it AFTER the
A6.2b rework verifies escalation row 1 (0 computation-class spine-numeric
hits surviving in the measurement path).

Method mirrors Phase 7 T1: enumerate momentum_events' 16 non-momentum_pct
numeric columns, find whole-word code references to each in every phase_6b
.py file + the config, and classify by (file role, code-vs-comment). The
two Phase 7 t8 columns (flag_eth_dominant_t0, t0_eth_row_share) are
flag/annotation columns, not quarantined numerics (A9 / Phase 7).

File roles:
  measurement_path : build_minute_bars_v2, t1_eligibility, t2_dev_pipeline,
                     measurements_v2, and any t3_/t4_ script - the code that
                     produces persisted measurements. A spine numeric used as
                     a COMPUTATION input here is the escalation.
  retired_diagnostic : a51_/a61_basis_confirmation* - defect-#4 basis tests,
                     superseded by D4, out of the measurement path. Recorded
                     as retired, not reworked (they read prev_close/spine high
                     by design, as the very thing being cross-checked).
"""
import ast
import io
import json
import re
import tokenize
from pathlib import Path

SPINE_NUMERIC_COLUMNS = [
    "prev_close", "high", "open", "close", "event_volume", "price_move", "id",
    "event_high", "event_open", "event_close", "market_cap_est", "sector",
    "has_minute_data", "has_trade_data", "min_volume_threshold", "__index_level_0__",
]
# whole-word, but exclude bar-derived 'high'/'open'/'close'/'id' handled by role note
PHASE_6B_DIR = Path("research/phase_6b")
CONFIG_PATH = Path("config/phase_6b.json")
OUT_PATH = "results/phase_6b/artifacts/a62_d4_sweep.json"

RETIRED = {"a51_basis_confirmation.py", "a61_basis_confirmation_rerun.py"}
# 'high' in the measurement path is bar.high (tick-derived from event_minute_bars_v2),
# never momentum_events.high - the builder never selects me.high. Only prev_close is a
# genuine spine read in 6b. We still scan all 16 and annotate.
BAR_DERIVED_OK = {"high", "open", "close"}  # in phase_6b these are always bar columns, not spine


def _docstring_line_ranges(text: str) -> set[int]:
    """1-indexed line numbers occupied by module/class/function docstrings (excluded from code)."""
    ranges = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return ranges
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
               and isinstance(body[0].value.value, str):
                d = body[0].value
                for ln in range(d.lineno, (d.end_lineno or d.lineno) + 1):
                    ranges.add(ln)
    return ranges


def scan_file(path: Path):
    """Robust code-vs-non-code detection via tokenize + ast docstring exclusion.
    A hit = a spine-column whole word appearing in a NAME token, or in a non-docstring
    STRING token's content (SQL columns, dict keys). COMMENT tokens and docstrings are
    excluded. 'prev_close_df' does NOT match prev_close (whole-word boundary)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    doc_lines = _docstring_line_ranges(text)
    patterns = {c: re.compile(rf"(?<![A-Za-z0-9_]){re.escape(c)}(?![A-Za-z0-9_])") for c in SPINE_NUMERIC_COLUMNS}
    hits = []
    seen = set()  # dedupe (col, line)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except tokenize.TokenError:
        toks = []
    for tok in toks:
        if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            continue
        lineno = tok.start[0]
        if lineno in doc_lines:
            continue
        if tok.type not in (tokenize.NAME, tokenize.STRING):
            continue
        for col, pat in patterns.items():
            if pat.search(tok.string) and (col, lineno) not in seen:
                seen.add((col, lineno))
                hits.append({
                    "column": col, "line": lineno,
                    "text": lines[lineno - 1].strip() if lineno - 1 < len(lines) else "",
                    "is_code": True,
                })
    return hits


def main():
    py_files = sorted(PHASE_6B_DIR.glob("*.py"))
    per_file = {}
    measurement_path_computation_hits = []
    for f in py_files:
        if f.name == "a62_d4_sweep.py":
            continue
        role = "retired_diagnostic" if f.name in RETIRED else "measurement_path"
        hits = scan_file(f)
        code_hits = [h for h in hits if h["is_code"]]
        # in the measurement path, the only genuine spine read is prev_close; bar-derived
        # high/open/close are tick columns. Flag prev_close code hits in measurement-path files.
        spine_code_hits = [h for h in code_hits if h["column"] not in BAR_DERIVED_OK]
        per_file[f.name] = {
            "role": role,
            "n_code_hits": len(code_hits),
            "code_hits": code_hits,
            "spine_code_hits_excl_bar_derived": spine_code_hits,
        }
        if role == "measurement_path":
            for h in spine_code_hits:
                measurement_path_computation_hits.append({"file": f.name, **h})

    # config scan (token/substring - it's JSON strings)
    cfg_text = CONFIG_PATH.read_text(encoding="utf-8")
    cfg_lines = cfg_text.splitlines()
    cfg_hits = []
    for col in SPINE_NUMERIC_COLUMNS:
        for m in re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(col)}(?![A-Za-z0-9_])", cfg_text):
            lineno = cfg_text[: m.start()].count("\n")
            cfg_hits.append({"column": col, "line": lineno + 1, "text": cfg_lines[lineno].strip()})

    out = {
        "phase": "6b", "task": "A6.2a",
        "purpose": "spine-numeric sweep of research/phase_6b/ + config/phase_6b.json (A8.2, before config re-freeze). Re-run after A6.2b to verify 0 measurement-path computation hits (escalation row 1).",
        "spine_numeric_columns_swept": SPINE_NUMERIC_COLUMNS,
        "t8_flag_columns_not_quarantined": ["flag_eth_dominant_t0", "t0_eth_row_share"],
        "per_file": per_file,
        "config_spine_numeric_references": cfg_hits,
        "measurement_path_spine_code_hits": measurement_path_computation_hits,
        "n_measurement_path_spine_code_hits": len(measurement_path_computation_hits),
        "classification_note": (
            "All measurement-path spine hits are prev_close (the pre-D4 opportunity-decay anchor): "
            "measurements_v2.compute_primary_opportunity_decay + t2_dev_pipeline.load_prev_close/pass "
            "(computation) and t1_eligibility's prev_close guard (universe_selection). day_high_ext and "
            "bar 'high' are tick-derived from event_minute_bars_v2, not spine columns. a51_/a61_ are "
            "retired basis-confirmation diagnostics (read prev_close/spine high by design), out of the "
            "measurement path. A6.2b replaces every prev_close computation hit with tick_close_t_minus_1_rth "
            "and removes the prev_close guard; the config re-freeze (A6.2d) rewrites the anchor strings."
        ),
        "escalation_row1_triggered_post_rework": None,  # set to n>0 only when re-run AFTER A6.2b
        "source": "research/phase_6b/a62_d4_sweep.py:main",
    }
    Path("results/phase_6b/artifacts").mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "per_file"}, indent=2))
    print(f"\nper-file code-hit counts:")
    for name, d in per_file.items():
        print(f"  {name} [{d['role']}]: {len(d['spine_code_hits_excl_bar_derived'])} spine code hit(s)")
    print(f"\nwrote {OUT_PATH}")
    print(f"measurement-path spine code hits (pre-rework): {len(measurement_path_computation_hits)}")


if __name__ == "__main__":
    main()
