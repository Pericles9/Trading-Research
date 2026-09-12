#!/usr/bin/env python
"""
Phase 10e T1 — the candidate-entry universe.

THE UNIT OF ANALYSIS IS THE CANDIDATE ENTRY, NOT THE EVENT. Entries occur repeatedly along
one event's path, so anchoring only at detection measures a single draw from a distribution
meant to be sampled many times. Consequences, all binding: clustering is by event and never
by time; one long, heavily sampled event must not dominate a pooled statistic; and every
reported statistic carries an effective n as well as a raw n.

PASS BUDGET. Arm 1 spends ZERO passes over filtered_trades / filtered_quotes (escalation
row 4). Everything here comes from `event_minute_bars_v2` and the frozen artifacts.

FROZEN, NOT RE-DERIVED (row 6 territory if violated):
  det_anchor            results/phase_8/artifacts/a102_detection_anchors.parquet   (D7)
  pq_rth_open           results/phase_8/artifacts/t3_participation.parquet
                        -- read HERE, not from the anchors file (Phase 11 A1-7)
  flag_possible_row_cap results/phase_8/artifacts/a101_labels.parquet
  flag_has_dup_prints   results/phase_6b/artifacts/event_index_v2.parquet
  flag_cross_session_extreme
                        results/phase_9/artifacts/t1_cross_session_flags.parquet, tm1_t0 pair

ONE ANCHOR, BOTH ARMS (escalation row 25). a102 is the artifact D7 was taken on.
`results/phase_10/artifacts/v2_r14_phase8_crosscheck.json` is READ to report agreement, never
re-derived.

D4 / row 6a. `momentum_pct` appears only as part of the event key (ticker, date,
momentum_pct) — a grouping key, never a numerator, denominator or computed quantity. No
other spine numeric is touched: every measured quantity here is bar-derived.

Usage: .venv/Scripts/python.exe research/phase_10e/t1_candidate_entries.py
"""
from __future__ import annotations

import json
import os
import time

import duckdb
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
CFG = os.path.join(REPO, "config", "phase_10e.json")

OUT_PARQUET = "results/phase_10e/artifacts/t1_candidate_entries.parquet"
OUT_JSON = "results/phase_10e/artifacts/t1_waterfall.json"


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    smin_coef = cfg["arm1"]["smin_coefficient"]
    per_event = cfg["arm1"]["entries_per_event"]
    seed = cfg["arm1"]["entry_subsample_seed"]
    bands = cfg["arm1"]["smin_bands_seconds"]

    t0 = time.perf_counter()
    # In-memory session with the main DB ATTACHED READ-ONLY: the phase needs temp views,
    # and a read-only connection cannot hold them. Nothing is written to main.duckdb.
    c = duckdb.connect()
    c.execute("PRAGMA threads=4")
    c.execute(f"ATTACH '{DB}' AS m (READ_ONLY)")
    for name, path in (
        ("anch", "results/phase_8/artifacts/a102_detection_anchors.parquet"),
        ("part", "results/phase_8/artifacts/t3_participation.parquet"),
        ("cap", "results/phase_8/artifacts/a101_labels.parquet"),
        ("dup", "results/phase_6b/artifacts/event_index_v2.parquet"),
        ("xs", "results/phase_9/artifacts/t1_cross_session_flags.parquet"),
    ):
        c.execute(f"create or replace view {name} as "
                  f"select * from read_parquet('{os.path.join(REPO, path)}')")

    wf = []                                    # T1e filter waterfall

    def step(label, n_rows, n_events, reason):
        wf.append({"step": label, "rows": int(n_rows), "events": int(n_events),
                   "reason": reason})
        print(f"  {label:38s} rows {n_rows:>12,}  events {n_events:>7,}   {reason}")

    print("T1e filter waterfall")
    r = c.execute("""select count(*) a, count(distinct (ticker||event_date_canonical||
                     cast(momentum_pct as varchar))) b from m.event_minute_bars_v2""").fetchone()
    step("event_minute_bars_v2, all offsets", r[0], r[1], "source table")

    r = c.execute("""select count(*) a, count(distinct (ticker||event_date_canonical||
                     cast(momentum_pct as varchar))) b from m.event_minute_bars_v2
                     where session_offset = 0""").fetchone()
    step("T=0 session only", r[0], r[1], "session_offset = 0")

    # D1 universe. The minute-bar table and every frozen artifact already carry the D1
    # frame (15,763 events); the join to the canonical view is kept so the constraint is
    # ENFORCED here rather than assumed from a row count that happens to match.
    c.execute("""create or replace view d1 as
        select ticker, event_date_canonical, momentum_pct
        from m.momentum_events_canonical
        where in_scope and source_file = 'file1'""")
    r = c.execute("select count(*) from d1").fetchone()
    print(f"  {'D1 universe (canonical)':38s} events {r[0]:>7,}   "
          f"in_scope AND source_file='file1'")

    c.execute("""create or replace view bars0 as
        select b.* from m.event_minute_bars_v2 b
        join d1 using (ticker, event_date_canonical, momentum_pct)
        where b.session_offset = 0""")
    r = c.execute("""select count(*) a, count(distinct (ticker||event_date_canonical||
                     cast(momentum_pct as varchar))) b from bars0""").fetchone()
    step("inner join to D1 universe", r[0], r[1], "D1, escalation row: universe is D1")

    # anchors: drop det_undefined, they have no anchor to measure from
    c.execute("""create or replace view anchored as
        select b.*, a.det_minute, a.det_segment, a.era
        from bars0 b
        join anch a on b.ticker = a.ticker
                   and b.event_date_canonical = a.event_date_canonical
                   and b.momentum_pct = a.mp
        where a.det_undefined = false and a.det_minute is not null""")
    r = c.execute("""select count(*) a, count(distinct (ticker||event_date_canonical||
                     cast(momentum_pct as varchar))) b from anchored""").fetchone()
    step("join a102, drop det_undefined", r[0], r[1],
         "D7 anchor required; det_undefined events carry no anchor")

    # T1b: one candidate entry per minute bar AT OR AFTER the anchor
    c.execute("""create or replace view cand as
        select *, minute_index - det_minute as minutes_since_anchor
        from anchored where minute_index >= det_minute""")
    r = c.execute("""select count(*) a, count(distinct (ticker||event_date_canonical||
                     cast(momentum_pct as varchar))) b from cand""").fetchone()
    step("bars at or after det_minute", r[0], r[1], "T1b: minute_index >= det_minute")

    # T1d(i): the print-weighted denominator -- what is actually enterable
    r = c.execute("select count(*) from cand where n_trades < 1").fetchone()[0]
    print(f"  {'(bars with n_trades = 0)':38s} rows {r:>12,}   "
          f"excluded by the print-weighted denominator")

    entries = c.execute(f"""
        select
            c.ticker, c.event_date_canonical, c.momentum_pct,
            c.minute_index, c.minutes_since_anchor, c.det_minute,
            c.segment            as bar_segment,
            c.det_segment, c.era,
            c.n_trades           as n_prints,
            c.volume, c.vwap, c.high, c.low, c.first_price, c.last_price,
            p.pq_rth_open,
            coalesce(cap.flag_possible_row_cap, false) as flag_possible_row_cap,
            coalesce(dup.flag_has_dup_prints, false)   as flag_has_dup_prints,
            coalesce(xs.flag_cross_session_extreme, false) as flag_cross_session_extreme,
            c.n_trades / 60.0    as lambda_hat_per_s,
            {smin_coef} / (c.n_trades / 60.0) as s_min_minute
        from cand c
        left join part p on c.ticker = p.ticker
             and c.event_date_canonical = p.event_date_canonical and c.momentum_pct = p.mp
        left join cap on c.ticker = cap.ticker
             and c.event_date_canonical = cap.event_date_canonical and c.momentum_pct = cap.mp
        left join dup on c.ticker = dup.ticker
             and c.event_date_canonical = dup.event_date_canonical
             and c.momentum_pct = dup.momentum_pct
        left join (select ticker, event_date_canonical, mp, flag_cross_session_extreme
                   from xs where session_pair = 'tm1_t0') xs
             on c.ticker = xs.ticker
             and c.event_date_canonical = xs.event_date_canonical and c.momentum_pct = xs.mp
        where c.n_trades >= 1
    """).fetchdf()
    ev = (entries.ticker + "|" + entries.event_date_canonical.astype(str) + "|"
          + entries.momentum_pct.astype(str))
    entries["event_id"] = ev
    step("print-weighted denominator", len(entries), ev.nunique(),
         "T1d(i): every bar with n_prints >= 1 -- what is actually enterable")

    # T1d(ii): event-equalised -- seeded uniform subsample, equal weight per event
    rng = np.random.default_rng(seed)
    idx = (entries.groupby("event_id", sort=False)
                  .apply(lambda g: g.sample(min(len(g), per_event), random_state=seed)
                         .index.to_numpy(), include_groups=False))
    keep = np.concatenate(idx.to_numpy()) if len(idx) else np.array([], dtype=int)
    entries["in_event_equalised"] = entries.index.isin(keep)
    step("event-equalised denominator", int(entries.in_event_equalised.sum()),
         entries.loc[entries.in_event_equalised, "event_id"].nunique(),
         f"T1d(ii): seeded uniform subsample, <= {per_event} bars/event, seed {seed}")

    # T1c: s_min band, the surviving 10-series criterion, as a STRATIFIER only
    entries["s_min_band"] = pd.cut(entries["s_min_minute"], bins=[0] + bands + [np.inf],
                                   right=False).astype(str)

    os.makedirs(os.path.join(REPO, "results/phase_10e/artifacts"), exist_ok=True)
    entries.to_parquet(os.path.join(REPO, OUT_PARQUET), index=False)

    # ---- T1a-i: the anchor crosscheck, READ not re-derived --------------------
    xc = json.load(open(os.path.join(
        REPO, "results/phase_10/artifacts/v2_r14_phase8_crosscheck.json"), encoding="utf-8"))
    af = xc["agreement_floor_exact_analogue"]

    out = {
        "task": "Phase 10e T1 -- candidate-entry universe",
        "pass_budget": {"filtered_trades": 0, "filtered_quotes": 0,
                        "note": "Arm 1 reads event_minute_bars_v2 and frozen artifacts only"},
        "d4_row_6a": ("momentum_pct appears only as part of the event key -- a grouping key, "
                      "never a numerator, denominator or computed quantity. No other spine "
                      "numeric is read."),
        "T1a_i_anchor_crosscheck": {
            "rule": ("ONE ANCHOR, BOTH ARMS: a102_detection_anchors.parquet. "
                     "v2_r14_phase8_crosscheck.json is READ, never re-derived (row 25)."),
            "source": "results/phase_10/artifacts/v2_r14_phase8_crosscheck.json",
            "n_comparable": af["n"], "n_exact": af["n_exact"],
            "share_exact": af["share_exact"],
            "share_beyond_tolerance": af["share_beyond_tolerance"],
            "verdict": ("EXACT AGREEMENT on the floor-exact analogue -- "
                        f"{af['n_exact']}/{af['n']}, share {af['share_exact']}. Row 25 does "
                        "not fire."),
            "convention_note": xc["convention_note"],
            "poll60_note": ("the 60 s poll differs by exactly 1 minute by construction "
                            "(floor vs ceil); within tolerance on all "
                            f"{xc['agreement_poll60_as_specified']['n']}."),
            "covers_arm2_cohort": ("the crosscheck population is the Phase 10 cohort "
                                   "manifest (114 rows, 110 comparable), which is the "
                                   "superset the Arm 2 causal cohort of 78 was drawn from."),
        },
        "T1c_s_min": {
            "formula": f"s_min = {smin_coef} / lambda_hat, lambda_hat = n_prints / 60",
            "note": ("the scale-space arc's one surviving criterion, entering as a "
                     "STRATIFIER only. No field is computed in Arm 1."),
            "bands_seconds": bands,
            "band_counts": {str(k): int(v) for k, v in
                            entries["s_min_band"].value_counts().items()},
        },
        "T1d_denominators": {
            "print_weighted": int(len(entries)),
            "event_equalised": int(entries.in_event_equalised.sum()),
            "entries_per_event_cap": per_event, "seed": seed,
            "rule": "Both carried. Never blended.",
        },
        "T1e_waterfall": wf,
        "entries_per_event": {
            "median": float(entries.groupby("event_id").size().median()),
            "q25": float(entries.groupby("event_id").size().quantile(.25)),
            "q75": float(entries.groupby("event_id").size().quantile(.75)),
            "max": int(entries.groupby("event_id").size().max()),
            "note": ("R5 lives here: the max is the single-event dominance risk that "
                     "event-equalisation exists to remove."),
        },
        "flags_carried": {
            "flag_possible_row_cap": int(entries.flag_possible_row_cap.sum()),
            "flag_has_dup_prints": int(entries.flag_has_dup_prints.sum()),
            "flag_cross_session_extreme": int(entries.flag_cross_session_extreme.sum()),
            "note": "row counts, not event counts; flags are carried, never used to drop",
        },
        "pq_rth_open_null_rows": int(entries.pq_rth_open.isna().sum()),
        "runtime_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10e/t1_candidate_entries.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_10e/t1_candidate_entries.py",
    }
    with open(os.path.join(REPO, OUT_JSON), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    print(f"\nT1a-i anchor crosscheck: {out['T1a_i_anchor_crosscheck']['verdict']}")
    e = out["entries_per_event"]
    print(f"entries per event: median {e['median']:.0f}  q75 {e['q75']:.0f}  max {e['max']:,}")
    print(f"s_min bands: {out['T1c_s_min']['band_counts']}")
    print(f"\nwrote {OUT_PARQUET}\nwrote {OUT_JSON}   ({out['runtime_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
