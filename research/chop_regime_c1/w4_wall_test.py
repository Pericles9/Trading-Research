"""
Chop regime C1, Amendment 3 W4 -- run the wall's tests and record them.

  1. w4_wall_test.js under node: the page test on the real data, and the config round trip with the unchanged suite on
     every shared (event, t) -- row W-c (HARD STOP on any minute that disagrees).
  2. w4_wall_timing.js: the slider redraw for a page of 12 in headless Chrome through the DevTools protocol -- row W-e
     (LOG above 1 s).

Writes artifacts/w4_tests.json. Exit 1 if W-c fires or the page test fails.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/w4_wall_test.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402

NODE = r"C:\Program Files\nodejs\node.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CFG = C.load_cfg()
A3 = CFG["amendment_3"]


def last_json(text: str) -> dict | None:
    for line in reversed(text.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    return None


def main() -> int:
    wall, suite = C.REPO / A3["W3_page"]["path"], C.REPO / C.SUITE / "chop_suite.html"
    seed = A3["W1_sample"]["seed"]
    p = subprocess.run([NODE, "--max-old-space-size=8192", str(C.REPO / "research/chop_regime_c1/w4_wall_test.js"), str(wall), str(suite), str(seed)],
                       capture_output=True, text=True, encoding="utf-8", cwd=C.REPO, timeout=3600)
    test = last_json(p.stdout)
    errs = [x for x in p.stderr.splitlines() if not x.startswith(("(node:", "["))]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as prof:          # Chrome may still hold its profile at exit
        q = subprocess.run([NODE, str(C.REPO / "research/chop_regime_c1/w4_wall_timing.js"), str(wall), CHROME, prof], capture_output=True, text=True, encoding="utf-8", cwd=C.REPO,
                           timeout=900)
    timing = last_json(q.stdout)
    st = (timing or {}).get("selftest") or {}
    out = {"config_hash": C.cfg_hash(), "wall": A3["W3_page"]["path"], "suite": f"{C.SUITE}/chop_suite.html", "seed": seed,
           "node_exit": p.returncode, "node_errors": errs, "test": test, "timing_exit": q.returncode, "timing": timing,
           "rowWc_fires": not (test or {}).get("round_trip_pass", False),
           "rowWe_fires": (st.get("median") is None) or st["median"] > 1000,
           "page_test_pass": bool((test or {}).get("page_test_pass", False)) and not (timing or {}).get("page_exceptions")}
    C.write_json("w4_tests.json", out)
    print(json.dumps({k: out[k] for k in ("node_exit", "rowWc_fires", "rowWe_fires", "page_test_pass")}, indent=1))
    print(json.dumps(test))
    print(json.dumps(timing))
    return 1 if out["rowWc_fires"] or not out["page_test_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
