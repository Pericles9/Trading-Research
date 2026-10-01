"""
Chop regime C1, T8 -- run the suite page's JavaScript test (t8_page_test.js) under node and record the result.

Writes artifacts/t8_page_test.json (exit code, the test's output).

Usage: .venv/Scripts/python.exe research/chop_regime_c1/t8_page_test.py
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402

NODE = r"C:\Program Files\nodejs\node.exe"


def main() -> int:
    page = C.REPO / C.SUITE / "chop_suite.html"
    p = subprocess.run([NODE, "--max-old-space-size=8192", str(C.REPO / "research/chop_regime_c1/t8_page_test.js"), str(page)], capture_output=True, text=True, cwd=C.REPO,
                       timeout=1800)
    out = (p.stdout + p.stderr).strip().splitlines()
    lines = [x for x in out if not x.startswith("(node:")]
    C.write_json("t8_page_test.json", {"exit": p.returncode, "output": lines,
                                       "summary": " ".join(x for x in lines if x.startswith(("init", "states", "noise band", "filtered with", "plot calls", "tab ")))})
    print("\n".join(lines))
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
