"""
Brief 2, T0 -- escalation row 4: the config diff against Brief 1's frozen config contains exactly the
section 1 items and nothing else.

Compares config/attention_excursion_b2.json with Brief 1's config as committed at 99431b8 (read from git,
hash 658071fbe27f asserted). Every Brief 1 key must be present and equal in b2; the only added top-level
keys may be `brief2_diff` (whose items must be exactly R1-R5) and `brief2` (this brief's own task
parameters, listed separately -- they change no Brief 1 instrument). Writes artifacts/t0_config_diff.json
and exits 1 when row 4 fires.

Usage: .venv/Scripts/python.exe research/attention_excursion_b2/config_diff.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2common as B  # noqa: E402

B1_COMMIT, B1_PATH, B1_HASH = "99431b8", "config/attention_excursion_b1.json", "658071fbe27f"


def diff_paths(a, b, path="") -> list[str]:
    """Every JSON path where a and b differ (a = Brief 1, b = Brief 2)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else k
            if k not in b:
                out.append(f"REMOVED {p}")
            elif k not in a:
                out.append(f"ADDED {p}")
            else:
                out += diff_paths(a[k], b[k], p)
        return out
    return [] if a == b else [f"CHANGED {path}"]


def main() -> int:
    raw = subprocess.check_output(["git", "show", f"{B1_COMMIT}:{B1_PATH}"], cwd=B.REPO).replace(b"\r\n", b"\n")
    h1 = hashlib.sha256(raw).hexdigest()[:12]
    assert h1 == B1_HASH, f"Brief 1 config at {B1_COMMIT} hashes to {h1}, not {B1_HASH}"
    b1 = json.loads(raw.decode("utf-8"))
    b2 = B.load_cfg()
    paths = diff_paths(b1, b2)
    allowed_top = {"ADDED brief2_diff", "ADDED brief2"}
    outside = [p for p in paths if p not in allowed_top]
    rulings = sorted(k for k in b2.get("brief2_diff", {}) if not k.startswith("_"))
    rulings_ok = rulings == ["R1", "R2", "R3", "R4", "R5"]
    fires = bool(outside) or not rulings_ok
    out = {
        "brief1_config": {"commit": B1_COMMIT, "path": B1_PATH, "hash": h1},
        "brief2_config": {"path": B.CFG, "hash": B.cfg_hash()},
        "brief1_keys_checked": len(b1),
        "diff_paths": paths,
        "outside_section_1": outside,
        "section_1_items": {k: b2["brief2_diff"][k].get("supersedes", b2["brief2_diff"][k].get("ruling"))
                            for k in rulings},
        "section_1_items_exactly_R1_R5": rulings_ok,
        "brief2_task_parameters": sorted(k for k in b2.get("brief2", {}) if not k.startswith("_")),
        "brief2_task_parameters_note": b2.get("brief2", {}).get("_rule"),
        "row_4": {"criterion": b2["brief2"]["escalation"]["row_4"]["criterion"], "tier": "HARD STOP", "fires": fires,
                  "observed": ("no Brief 1 key changed, added or removed; the only additions are brief2_diff (exactly R1-R5) "
                               "and brief2 (task parameters)") if not fires else f"outside section 1: {outside}; rulings {rulings}"},
    }
    B.write_json("t0_config_diff.json", out)
    print(json.dumps(out["row_4"], indent=1))
    return 1 if fires else 0


if __name__ == "__main__":
    raise SystemExit(main())
