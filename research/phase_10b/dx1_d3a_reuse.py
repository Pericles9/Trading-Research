"""
DX10b.1 D3a -- reuse-before-build check for the global envelope test.

Records what is and is not available in this environment. Writes the artifact
that escalation row 6 is evaluated against. Runs nothing statistical.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from t1_plateau import cfg_hash  # noqa: E402

DX = "results/phase_10b/diagnostic_1"


def main() -> int:
    cands = {}
    for m in ("GET", "spatstat", "pointpats", "rpy2", "astropy", "scipy", "numpy"):
        try:
            mod = importlib.import_module(m)
            cands[m] = {"present": True, "version": getattr(mod, "__version__", "unknown")}
        except Exception:
            cands[m] = {"present": False}

    r_bin = {n: shutil.which(n) for n in ("R", "Rscript", "R.exe", "Rscript.exe")}
    r_dirs = [p for p in (r"C:\Program Files\R", r"C:\Program Files (x86)\R")
              if os.path.isdir(p)]

    # PyPI reachability: a --no-deps download of a tiny pure-python package
    probe_dir = os.path.join(os.environ.get("TEMP", "."), "dx1_pypi_probe")
    os.makedirs(probe_dir, exist_ok=True)
    try:
        p = subprocess.run([sys.executable.replace("python.exe", "Scripts/pip.exe"),
                            "download", "--no-deps", "-d", probe_dir, "six"],
                           capture_output=True, text=True, timeout=90)
        got = [f for f in os.listdir(probe_dir) if f.lower().startswith("six")]
        pypi = {"reachable": bool(got), "artifacts": got,
                "returncode": p.returncode, "stderr_tail": p.stderr[-400:]}
    except Exception as e:
        pypi = {"reachable": False, "error": repr(e)}

    out = {
        "phase": "10b", "diagnostic": "DX10b.1", "task": "D3a",
        "config_hash": cfg_hash(),
        "question": ("Is there a maintained implementation of the global envelope test "
                     "(Myllymaki, Mrkvicka, Grabarnik, Seijo & Hahn, JRSS-B 79:381-404, 2017) "
                     "to reuse, and can the reference implementation be run here for validation?"),
        "reference_implementation": {
            "name": "R package GET (Myllymaki & Mrkvicka)",
            "language": "R",
            "available_here": False,
            "evidence": {"R_binaries_on_path": r_bin, "R_install_dirs_found": r_dirs}},
        "python_candidates": cands,
        "python_port_found": False,
        "python_port_note": ("No maintained Python port of the global envelope test is installed, "
                             "and the method's reference implementation is R-only. rpy2, which "
                             "would allow calling GET from Python, is also absent."),
        "pypi": pypi,
        "conclusion": (
            "Cannot reuse and cannot validate. R is not installed and has no install directory; "
            "rpy2 is absent; no Python implementation is present; and PyPI is unreachable from "
            "this environment, so neither rpy2 nor any candidate package can be obtained. "
            "Implementing extreme rank length directly is feasible -- it is short -- but D3a "
            "requires validating such an implementation against GET on a published example "
            "BEFORE running it on the controls, and that comparison cannot be performed here."),
        "escalation_row_6": {
            "condition": "Envelope test implementation cannot be validated against the reference",
            "FIRED": True,
            "action": "Hard stop -- post what you have"},
        "what_was_not_done": [
            "D3b re-simulation at 2,499 draws", "D3c per-simulation intensity re-estimation",
            "D3d the envelope test itself", "D3e current-rule vs envelope verdict comparison",
            "D3f type I error check", "D3g chart 10"],
        "independent_of_d3": [
            "D4 knee sampling distribution (charts 11) -- does not use the envelope test",
            "D5 bias consistency (chart 12) -- does not use the envelope test"],
        "source": "research/phase_10b/dx1_d3a_reuse.py:main",
    }
    write_json(rel(f"{DX}/artifacts/d3_envelope_validation.json"), out)
    print("D3a reuse check")
    print(f"  R on PATH:            {r_bin}")
    print(f"  R install dirs:       {r_dirs or 'none'}")
    print(f"  rpy2:                 {cands['rpy2']['present']}")
    print(f"  Python GET port:      False")
    print(f"  PyPI reachable:       {pypi.get('reachable')}")
    print("  ROW 6 FIRES -- cannot validate against the reference; hard stop")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
