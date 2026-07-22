"""
Phase 4 T0b - venv calendar pin correction (register item, approved Phase 3 gate).

Phase 3 found the .venv's pandas_market_calendars/exchange_calendars drifted from
the Phase 1c pin (5.4.0/4.13.2 pinned vs. 5.3.0/4.12 installed) and verified the
drift was harmless for the 2019-12-01..2026-01-15 XNYS derivation range using an
isolated install (results/phase_3/artifacts/calendar_pin_verification.json:
identical=true, n_diffs=0, 1,539/1,539 sessions), without correcting the shared
venv itself.

This script performs the sanctioned correction: the shared .venv now has the
pinned versions installed directly (see T0b commit - `pip install
pandas_market_calendars==5.4.0 exchange_calendars==4.13.2`). To re-verify
harmlessness with fresh evidence (not just trusting the Phase 3 artifact), this
script regenerates the XNYS session list under the now-corrected .venv and diffs
it against a fresh isolated install of the old drifted versions (5.3.0/4.12).

Reproduce the isolated install of the old versions (not run automatically -
network call, writes outside the repo):
    python -m pip install --target <tmpdir> pandas_market_calendars==5.3.0 exchange_calendars==4.12
then run this script with --old-path <tmpdir>.
"""
import argparse
import json
import subprocess


def generate_sessions(python_exe, extra_syspath, out_csv):
    code = f"""
import sys
{'sys.path.insert(0, ' + repr(extra_syspath) + ')' if extra_syspath else ''}
import pandas_market_calendars as mcal
import pandas as pd
xnys = mcal.get_calendar('XNYS')
sessions = pd.DatetimeIndex(xnys.schedule(start_date='2019-12-01', end_date='2026-01-15').index).normalize()
pd.Series(sessions).to_csv({out_csv!r}, index=False, header=False)
print(mcal.__version__)
print(len(sessions))
"""
    result = subprocess.run([python_exe, "-c", code], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    return lines[0], int(lines[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-path", required=True, help="Isolated install dir with pandas_market_calendars==5.3.0 exchange_calendars==4.12 (the pre-correction drifted versions)")
    ap.add_argument("--python-exe", default=".venv/Scripts/python.exe")
    ap.add_argument("--out", default="results/phase_4/artifacts/t0b_versions.json")
    args = ap.parse_args()

    pinned_csv = "results/phase_4/artifacts/_sessions_pinned_venv.csv"
    old_csv = "results/phase_4/artifacts/_sessions_old_isolated.csv"

    pinned_ver_pmc, pinned_n = generate_sessions(args.python_exe, None, pinned_csv)
    old_ver_pmc, old_n = generate_sessions(args.python_exe, args.old_path, old_csv)

    import importlib
    import exchange_calendars as xc
    pinned_ver_xc = xc.__version__

    with open(pinned_csv) as f:
        pinned_sessions = f.read().splitlines()
    with open(old_csv) as f:
        old_sessions = f.read().splitlines()

    identical = pinned_sessions == old_sessions
    diff_dates = [] if identical else [
        (a, b) for a, b in zip(pinned_sessions, old_sessions) if a != b
    ]

    out = {
        "phase": "4", "task": "T0b - venv calendar pin correction",
        "question": "Post-correction: does the now-pinned shared .venv (5.4.0/4.13.2) still produce the same XNYS session list as the pre-correction drifted versions (5.3.0/4.12) that Phase 3 shipped results under?",
        "derivation_range": {"start": "2019-12-01", "end": "2026-01-15"},
        "venv_state": "corrected - pip install pandas_market_calendars==5.4.0 exchange_calendars==4.13.2 into the shared .venv",
        "pinned_venv_version_pandas_market_calendars": pinned_ver_pmc,
        "pinned_venv_version_exchange_calendars": pinned_ver_xc,
        "old_isolated_version_pandas_market_calendars": old_ver_pmc,
        "pinned_venv_n_sessions": pinned_n,
        "old_isolated_n_sessions": old_n,
        "identical": identical,
        "n_diffs": len(diff_dates),
        "diff_sample": diff_dates[:20],
        "phase_3_reference": {
            "path": "results/phase_3/artifacts/calendar_pin_verification.json",
            "recorded_current_venv_version": "5.3.0",
            "recorded_pinned_version": "5.4.0",
            "recorded_identical": True,
            "recorded_n_diffs": 0,
        },
        "conclusion": (
            "IDENTICAL - 1,539/1,539 XNYS sessions, 0 diffs, over the same derivation range used "
            "throughout Phase 2/3/4. Confirms Phase 3's isolated-install finding with fresh evidence "
            "from the now-corrected shared .venv. The venv correction is confirmed harmless; T4's "
            "expected-session bitmap arithmetic may proceed under the corrected .venv."
        ) if identical and pinned_n == 1539 and old_n == 1539 else (
            "NOT IDENTICAL or session count mismatch - see diff_sample. Escalation row 5 triggers."
        ),
        "source": "research/phase_4/t0b_calendar_pin_correction.py:main",
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
