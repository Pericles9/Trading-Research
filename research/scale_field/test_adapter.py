"""
Adapter acceptance. Order-of-work step 1: load one known event and assert monotone,
positive, in-session timestamps.

These tests read real event folders under data/filtered/. They are skipped, not
failed, where the data root is absent -- but a skip is not a pass, and the
reconciliation script reports whether they ran.

Run: python -m pytest test_adapter.py -q
"""
import os

import numpy as np
import pytest

import adapter
from adapter import (SEGMENTS, load_cohort, load_detection, load_event_prints,
                     load_event_prints_meta, make_event_id, parse_event_id,
                     segment_bounds_ns)
from scale_field import collapse_same_timestamp, intervals, to_seconds

CFG = adapter.load_config()
HAVE_DATA = os.path.isdir(adapter.rel(CFG["paths"]["filtered_root"]))
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="data/filtered not present")


# --- 1. the frozen cohort ------------------------------------------------------
@needs_data
def test_cohort_hash_and_counts_are_the_committed_ones():
    c = load_cohort(CFG)
    assert len(c) == 114
    assert int(c["pooled"].sum()) == 100
    assert (~c["pooled"]).sum() == 14                      # 8 row_cap_census + 6 sidecar
    assert c["event_id"].is_unique


@needs_data
def test_cohort_mismatch_is_an_exception_not_a_warning():
    bad = {**CFG, "cohort": {**CFG["cohort"], "content_hash": "0" * 16}}
    with pytest.raises(adapter.CohortMismatch):
        load_cohort(bad)


# --- 2. event ids round-trip ---------------------------------------------------
@pytest.mark.parametrize("tkr,date,mom", [
    ("ALXO", "2020-08-05", 31.58), ("AACG", "2020-06-11", 50.02),
    ("BRK_B", "2021-01-04", 7.5),          # an underscore in the ticker must survive
])
def test_event_id_round_trips(tkr, date, mom):
    assert parse_event_id(make_event_id(tkr, date, mom)) == (tkr, date, round(mom, 2))


def test_parse_rejects_a_non_id():
    with pytest.raises(ValueError):
        parse_event_id("not-an-id")


# --- 3. the segments tile the extended day, and are ET ------------------------
def test_segments_are_disjoint_and_tile_the_session():
    for date in ("2021-02-19", "2020-07-06", "2024-10-11"):
        b = segment_bounds_ns(date)
        assert b["premarket"][1] == b["rth"][0]
        assert b["rth"][1] == b["post"][0]
        for s in SEGMENTS:
            assert b[s][1] > b[s][0], (date, s)
        assert (b["post"][1] - b["premarket"][0]) / 1e9 == pytest.approx(16 * 3600, abs=1)


def test_early_close_shortens_the_post_segment():
    """2024-11-29 is a 13:00 ET close. post ends 17:00 ET, not 20:00 -- and a
    UTC-cast-to-date convention would not know that."""
    normal = segment_bounds_ns("2024-12-02")
    early = segment_bounds_ns("2024-11-29")
    assert (early["rth"][1] - early["rth"][0]) / 3600e9 == pytest.approx(3.5, abs=0.01)
    assert (early["post"][1] - early["post"][0]) / 3600e9 == pytest.approx(4.0, abs=0.01)
    assert (normal["post"][1] - normal["post"][0]) / 3600e9 == pytest.approx(4.0, abs=0.01)


def test_dst_is_real_not_a_fixed_offset():
    """EST winter vs EDT summer: the same 04:00 ET start is a different UTC hour.
    This is the exact failure the UTC-cast convention makes on post prints."""
    winter = segment_bounds_ns("2021-01-05")["premarket"][0]
    summer = segment_bounds_ns("2021-07-06")["premarket"][0]
    hour = lambda ns: (ns // 3_600_000_000_000) % 24   # noqa: E731
    assert hour(winter) == 9 and hour(summer) == 8


# --- 4. one known event: monotone, positive, in-session -----------------------
KNOWN = "ALXO_2020-08-05_31.58"


@needs_data
def test_known_event_is_monotone_positive_and_in_session():
    ts, meta = load_event_prints_meta(KNOWN)
    assert ts.dtype == np.int64
    assert ts.size == meta["n_prints"] > 0
    assert np.all(np.diff(ts) >= 0), "not sorted ascending"
    assert np.all(ts > 0), "epoch-ns timestamps must be positive"
    assert np.all(np.isfinite(ts.astype(float)))
    lo, hi = meta["window_start_ns"], meta["window_end_ns"]
    assert ts[0] >= lo and ts[-1] < hi, "print outside the D3 extended-day window"


@needs_data
def test_known_event_segments_partition_the_session():
    whole = load_event_prints(KNOWN)
    parts = [load_event_prints(KNOWN, s) for s in SEGMENTS]
    assert sum(p.size for p in parts) == whole.size
    assert np.array_equal(np.concatenate(parts), whole)


@needs_data
def test_a_segment_slice_stays_inside_its_own_wall_clock_bounds():
    b = segment_bounds_ns("2020-08-05")
    for s in SEGMENTS:
        ts = load_event_prints(KNOWN, s)
        if ts.size:
            assert ts.min() >= b[s][0] and ts.max() < b[s][1], s


@needs_data
def test_ties_are_returned_uncollapsed_and_collapse_makes_intervals_positive():
    """The adapter's contract is ties NOT collapsed -- that policy belongs to the
    caller, and the estimator's own function applies it."""
    ts, meta = load_event_prints_meta(KNOWN)
    assert meta["n_tied_prints"] == ts.size - meta["n_unique_timestamps"]
    c = collapse_same_timestamp(ts)
    assert c.size == meta["n_unique_timestamps"]
    tsec, origin = to_seconds(c)
    ev, x = intervals(c, origin_ns=origin)
    assert np.all(np.isfinite(x))
    assert np.all(np.diff(ev) > 0)
    # And the naive conversion this event actually broke, pinned as a real case.
    with pytest.raises(ValueError, match="cannot resolve"):
        intervals(c)


@needs_data
def test_timestamp_resolution_is_above_the_hard_floor():
    """The 2^-20 s scale floor exists because below it you measure quantization.
    Assert the event's own resolution actually sits under that floor."""
    _, meta = load_event_prints_meta(KNOWN)
    assert meta["min_nonzero_gap_ns"] is not None
    assert meta["min_nonzero_gap_ns"] / 1e9 < CFG["scale_axis"]["hard_floor_seconds"]


@needs_data
def test_bad_segment_name_raises():
    with pytest.raises(ValueError):
        load_event_prints(KNOWN, "overnight")


# --- 5. the detection anchor, reused not re-derived ---------------------------
@needs_data
def test_detection_anchor_covers_the_analysis_cohort():
    c = load_cohort(CFG)
    det = load_detection(CFG)
    assert det["event_id"].is_unique
    pooled = set(c.loc[c["pooled"], "event_id"])
    assert pooled <= set(det["event_id"])
    seg = det[det["event_id"].isin(pooled)]["segment"]
    assert set(seg.dropna()) <= set(SEGMENTS)
    # v3's committed split: 70 rth, 28 premarket, 0 post, 2 never-crossing.
    assert (seg == "rth").sum() == 70
    assert (seg == "premarket").sum() == 28
    assert seg.isna().sum() == 2
