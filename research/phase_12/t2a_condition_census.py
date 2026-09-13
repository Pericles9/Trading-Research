#!/usr/bin/env python
"""Phase 12 T2a -- route 2: condition-code census, dev tier.

Full census of `conditions` (trades, on the prints immediately before/after each route-1
candidate gap) and `indicators` (quotes, on any quote inside the gap window itself) -- and the
identical census on a matched sample of non-candidate gaps, as a comparison population.

Per config.route_2_condition_codes and Escalation row 5: codes are reported as opaque integers.
No meaning is inferred from their distribution. dictionary_path=NONE (D34), so this task produces
a census only and identifies nothing -- per config.route_2_condition_codes.census_only_if_no_dictionary.

Usage: .venv/Scripts/python.exe research/phase_12/t2a_condition_census.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "results", "phase_12", "artifacts", "t2_code_census.json")
SEED = 20260913

sys.path.insert(0, os.path.join(REPO, "research", "phase_10"))
import common  # noqa: E402


def code_counts(codes_iterable) -> Counter:
    c = Counter()
    for codes in codes_iterable:
        if codes is None:
            c["NULL"] += 1
            continue
        lst = list(codes)
        if len(lst) == 0:
            c["EMPTY_LIST"] += 1
        for code in lst:
            c[int(code)] += 1
    return c


def main() -> int:
    cfg = json.load(open(os.path.join(REPO, "config", "phase_10.json"), encoding="utf-8"))
    gaps = pd.read_parquet(os.path.join(REPO, "results", "phase_12", "artifacts",
                                         "t1_gap_census.parquet"))
    candidates = gaps[gaps.is_candidate].copy()
    non_candidates = gaps[~gaps.is_candidate].copy()

    rng = np.random.default_rng(SEED)
    n_match = min(len(candidates), len(non_candidates))
    matched_idx = rng.choice(len(non_candidates), size=n_match, replace=False)
    matched = non_candidates.iloc[matched_idx].copy()

    def census_for(df: pd.DataFrame, label: str) -> dict:
        trade_before_codes, trade_after_codes = [], []
        quote_indicator_codes, quote_condition_codes = [], []
        n_events_touched = 0
        cache: dict = {}
        for ev, grp in df.groupby(["ticker", "event_date", "momentum_pct"]):
            ticker, date_str, mp = ev
            n_events_touched += 1
            if ev not in cache:
                tfiles = common.trade_files(cfg, ticker, date_str, mp)
                tdf = None
                if tfiles:
                    frames = [pd.read_parquet(f, columns=["sip_timestamp", "conditions"])
                              for f in tfiles]
                    tdf = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
                    tdf = tdf.set_index("sip_timestamp")
                folder = common.event_folder(cfg, ticker, date_str, mp)
                qpath = os.path.join(folder, "quotes.parquet")
                qdf = None
                if os.path.exists(qpath):
                    qdf = pd.read_parquet(qpath, columns=["sip_timestamp", "conditions",
                                                            "indicators"])
                cache[ev] = (tdf, qdf)
            tdf, qdf = cache[ev]

            for r in grp.itertuples(index=False):
                if tdf is not None:
                    if r.gap_start_ns in tdf.index:
                        v = tdf.loc[r.gap_start_ns, "conditions"]
                        trade_before_codes.append(v.iloc[0] if hasattr(v, "iloc") else v)
                    if r.gap_end_ns in tdf.index:
                        v = tdf.loc[r.gap_end_ns, "conditions"]
                        trade_after_codes.append(v.iloc[0] if hasattr(v, "iloc") else v)
                if qdf is not None:
                    win = qdf[(qdf.sip_timestamp >= r.gap_start_ns) &
                              (qdf.sip_timestamp <= r.gap_end_ns)]
                    quote_indicator_codes.extend(win["indicators"].tolist())
                    quote_condition_codes.extend(win["conditions"].tolist())

        return {
            "label": label, "n_gaps": int(len(df)), "n_events_touched": n_events_touched,
            "trade_conditions_before": dict(code_counts(trade_before_codes)),
            "trade_conditions_after": dict(code_counts(trade_after_codes)),
            "quote_indicators_in_window": dict(code_counts(quote_indicator_codes)),
            "quote_conditions_in_window": dict(code_counts(quote_condition_codes)),
            "n_quote_rows_seen_in_window": len(quote_indicator_codes),
        }

    cand_census = census_for(candidates, "candidates (>=60s gaps)")
    matched_census = census_for(matched, "matched non-candidates (<60s gaps, random draw)")

    out = {
        "task": "T2a -- route 2 condition-code census, dev tier",
        "dictionary_path": "NONE",
        "census_only_note": ("No meaning is inferred from any code (Escalation row 5). Codes "
                              "are opaque integers, reported as frequency counts only."),
        "n_match": n_match,
        "match_seed": SEED,
        "candidates": cand_census,
        "matched_non_candidates": matched_census,
        "source": "research/phase_12/t2a_condition_census.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_12/t2a_condition_census.py",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"n_match={n_match}")
    print("\nCANDIDATES:")
    print(json.dumps(cand_census, indent=2, default=str)[:2000])
    print("\nMATCHED NON-CANDIDATES:")
    print(json.dumps(matched_census, indent=2, default=str)[:2000])
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
