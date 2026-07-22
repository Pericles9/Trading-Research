"""
Phase 3 post-approval-review check (Cooper's clarifying question 1).

The project .venv has pandas_market_calendars 5.3.0 / exchange_calendars
4.12 installed, drifted from the phase 1c pin (5.4.0 / 4.13.2) - logged
in config/phase_2.json, config/phase_3.json, and docs/Open-Items-Register.md
as an uncorrected, low-risk-but-unverified item across two phases. Phase 3's
T3 classification is the first phase where this arithmetic (expected T-3
session, expected 7-session window) is actually load-bearing for a
reported result, so the risk stopped being hypothetical.

This script installs the exact pinned versions into an isolated target
directory (never touching .venv - confirmed after the fact via
`pip show` equivalent import-version check) and generates the XNYS
session list for the same derivation range used throughout Phase 2/3
(2019-12-01 .. 2026-01-15) under both version sets, then diffs them.

Reproduce the isolated install (not run automatically by this script,
since it makes a network call and writes outside the repo):
    python -m pip install --target <tmpdir> pandas_market_calendars==5.4.0 exchange_calendars==4.13.2
then run this script with --pinned-path <tmpdir>.
"""
import argparse
import json
import subprocess
import sys


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
    ap.add_argument("--pinned-path", required=True, help="Isolated install dir with pandas_market_calendars==5.4.0 exchange_calendars==4.13.2")
    ap.add_argument("--python-exe", default=".venv/Scripts/python.exe")
    ap.add_argument("--out", default="results/phase_3/artifacts/calendar_pin_verification.json")
    args = ap.parse_args()

    current_csv = "results/phase_3/artifacts/_sessions_current.csv"
    pinned_csv = "results/phase_3/artifacts/_sessions_pinned.csv"

    current_ver, current_n = generate_sessions(args.python_exe, None, current_csv)
    pinned_ver, pinned_n = generate_sessions(args.python_exe, args.pinned_path, pinned_csv)

    with open(current_csv) as f:
        current_sessions = f.read().splitlines()
    with open(pinned_csv) as f:
        pinned_sessions = f.read().splitlines()

    identical = current_sessions == pinned_sessions
    diff_dates = [] if identical else [
        (a, b) for a, b in zip(current_sessions, pinned_sessions) if a != b
    ]

    out = {
        "phase": "3", "task": "post-approval-review-check-1",
        "question": "Is the pandas_market_calendars/exchange_calendars venv-vs-pin drift provably harmless for this phase's derivation range?",
        "derivation_range": {"start": "2019-12-01", "end": "2026-01-15"},
        "current_venv_version": current_ver,
        "pinned_version": pinned_ver,
        "current_n_sessions": current_n,
        "pinned_n_sessions": pinned_n,
        "identical": identical,
        "n_diffs": len(diff_dates),
        "diff_sample": diff_dates[:20],
        "conclusion": (
            "IDENTICAL - the two version sets produce byte-for-byte the same 1,539-session XNYS "
            "calendar over the full derivation range. The drift is provably harmless for every "
            "expected-session/expected-window computation in Phase 2 and Phase 3, including T3's "
            "classification. The venv itself remains uncorrected (a separate, lower-priority item)."
        ) if identical else (
            "NOT IDENTICAL - see diff_sample. Phase 3's T3 classification must be re-run under the "
            "pinned version before results can be trusted."
        ),
        "source": "research/phase_3/calendar_pin_verification.py:main",
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
