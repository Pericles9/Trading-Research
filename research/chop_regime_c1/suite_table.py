"""
Chop regime C1 -- the suite's per-moment table: which columns are embedded, in what type, and the build-time assertions
(brief section 12; Amendment 1). Shared by T7 (sizing the embedded sample) and T8 (writing the page).

Rows: every non-auction moment of the embedded events (auction-minute moments are not entry moments, brief section 3; their
moment-minutes are stated in the header). Columns:

  ev, j, seg, flags      event index, grid index, t's segment, bit flags (quote at t, no print since the last moment, halt
                         label, halt gap proxy, vwap_fallback, g1, g2, g3, context fallback, tcs_state (2 bits), at segment
                         start)
  c_*  conditions        causal measures only (CONDITION_SOURCES); cost_noise is embedded at w5 and v025 and the page scales
                         it to the other rungs of each ladder by the exact factor sqrt(h0 / h) (asserted here)
  o_*  override          leg_s, giveback, act_ratio (causal)
  er_k0..er_k6, er_all   the efficiency ratio per rung and at every valid rung (causal; Amendment 1 row 3b may remove it from
                         the conditions -- it stays as a column and a reference panel)
  y_*  hindsight         entry price, forward return and MFE per horizon (gross bp; cents = bp x entry / 100; net = gross -
                         the round trip at t), and a 2-bit state per horizon. Never a condition (asserted).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import c1common as C
import suitedata as SD

TYPES = ["runaway", "burst", "slow_climb", "exhausted", "fade", "chop"]
TIERS = ["<$1", "$1-3", "$3-10", ">=$10"]
TAU_SEGS = ["premarket", "auction_open", "regular", "auction_close", "after_hours"]
TCS = {"false": 0, "true": 1, "not_settled": 2}
CONDITION_SOURCES = {
    "c_trade_rate": "trade_rate", "c_dollar_flow": "dollar_flow", "c_spread_bp": "spread_bp_t", "c_spread_c": "spread_c_t", "c_quote_age": "quote_age_s",
    "c_depth_ask": "depth_ask_usd", "c_cn_w5": "cost_noise_w5", "c_cn_v025": "cost_noise_v025",
    "c_turnover_rate": "turnover_rate", "c_n_eff": "n_eff", "c_top3": "top3_share", "c_move_per_trade": "move_per_trade",
}
OVERRIDE_SOURCES = {"o_leg_s": "leg_s", "o_giveback": "giveback", "o_act_ratio": "act_ratio"}
HINDSIGHT_PREFIXES = tuple(f"{h}_" for h in C.HORIZONS) + ("g3_fwd_max_px", "rem_type", "rem_state")
FORBIDDEN = ("flag_cross_session_extreme", "a12", "pct", "percentile", "rank")


def check_cost_noise_scaling(m: pd.DataFrame) -> dict:
    """cost_noise_h = spread / (1e4 sigma_h) with sigma_h = sqrt(sum r^2 / W x h) (wall) or sqrt(sum r^2 / V x m V_pre) (volume),
    so within a ladder the rungs differ by sqrt(h0 / h) exactly; the page relies on it."""
    out = {}
    for base, others, unit in (("cost_noise_w5", {"cost_noise_w15": 15, "cost_noise_w60": 60}, 5), ("cost_noise_v025", {"cost_noise_v05": 0.5, "cost_noise_v1": 1.0}, 0.25)):
        b = m[base].astype(float)
        for c, h in others.items():
            x = m[c].astype(float)
            ok = np.isfinite(b) & np.isfinite(x)
            assert np.allclose(x[ok], b[ok] * math.sqrt(unit / h), rtol=1e-9, atol=1e-12), f"{c} is not {base} x sqrt({unit}/{h})"
            assert (np.isinf(b) == np.isinf(x)).all() and (b.isna() == x.isna()).all()
            out[c] = int(ok.sum())
    return out


def build(m: pd.DataFrame, pop: pd.DataFrame, sf: pd.DataFrame | None = None) -> tuple[dict, dict]:
    """(encoded arrays, event table) for the moments `m` (development-slice moments of the embedded events)."""
    for c in list(CONDITION_SOURCES.values()) + list(OVERRIDE_SOURCES.values()):
        assert not c.startswith(HINDSIGHT_PREFIXES), f"hindsight column {c} wired to a condition"
        assert not any(z in c.lower() for z in FORBIDDEN), f"forbidden column {c} wired to a condition"
    assert m["dev_slice"].all(), "a non-development row reached the suite"
    dev_ids = set(pop.loc[pop["slice"] == "development", "event_id"])
    assert set(m["event_id"]) <= dev_ids, "an embedded event outside the development slice"
    m = m[m["segment"].isin(C.SEGS)]
    evs = sorted(m["event_id"].unique())
    eix = {e: i for i, e in enumerate(evs)}
    m = m.assign(_e=m["event_id"].map(eix)).sort_values(["_e", "j"]).reset_index(drop=True)
    n = len(m)
    tab = {}

    def put(name, arr, dt):
        tab[name] = SD.encode(np.asarray(arr), dt)

    put("ev", m["_e"].to_numpy(), "u2")
    put("j", m["j"].to_numpy(), "u1")
    put("seg", m["segment"].map({s: i for i, s in enumerate(C.SEGS)}).to_numpy(), "u1")
    b = lambda s: s.fillna(False).astype(bool).to_numpy().astype(np.uint16)  # noqa: E731
    fl = (b(m["quote_at_t"]) | b(m["no_print_since_last_moment"]) << 1 | b(m["halt_state"] == "label") << 2 | b(m["halt_state"] == "gap_proxy") << 3
          | b(m["price_basis"] == "vwap_fallback") << 4 | b(m["g1"]) << 5 | b(m["g2"]) << 6 | b(m["g3"]) << 7 | b(m["context_basis"] == "vwap_fallback") << 8
          | (m["tcs_state"].map(TCS).fillna(2).astype(np.uint16).to_numpy() << 9) | b(m["measure_state"] != "ok") << 11)
    put("flags", fl, "u2")
    for k, c in {**CONDITION_SOURCES, **OVERRIDE_SOURCES}.items():
        put(k, m[c].astype(float).to_numpy(), "f4")
    if sf is not None:
        e = sf[sf["k"] <= 6].pivot_table(index="moment_uid", columns="k", values="er", aggfunc="first")
        for k in range(7):
            put(f"er_k{k}", m["moment_uid"].map(e[k]) if k in e else np.full(n, np.nan), "f4")
    else:
        for k in range(7):
            put(f"er_k{k}", np.full(n, np.nan), "f4")
    put("er_all", m["er_allmax"].astype(float).to_numpy(), "f4")
    # hindsight
    entry = np.full(n, np.nan)
    st = np.zeros(n, dtype=np.uint16)
    for i, h in enumerate(C.HORIZONS):
        s = m[f"{h}_state"].astype(object)
        ok = (s == "ok").to_numpy()
        cen = m[f"{h}_censored"].fillna(False).astype(bool).to_numpy()
        code = np.where(ok & ~cen, 0, np.where(ok & cen, 1, np.where((s == "no_print_in_h").to_numpy(), 2, 3))).astype(np.uint16)
        st |= code << (2 * i)
        ep = m[f"{h}_entry_px"].astype(float).to_numpy()
        both = np.isfinite(ep) & np.isfinite(entry)
        assert np.allclose(ep[both], entry[both], rtol=0, atol=0), "entry price differs across horizons"
        entry = np.where(np.isfinite(entry), entry, ep)
        put(f"y_ret_{h}", np.where(ok, m[f"{h}_ret_bp"].astype(float), np.nan), "f4")
        put(f"y_mfe_{h}", np.where(ok, m[f"{h}_mfe_bp"].astype(float), np.nan), "f4")
    put("y_entry", entry, "f4")
    put("y_state", st, "u2")
    # the event table
    em = pop.set_index("event_id").loc[evs]
    rem = m[m["rem_type"].notna()].pivot_table(index="event_id", columns="j", values="rem_type", aggfunc="first")
    tod = ((em["tau_ns"].to_numpy() - np.array([C.B1.et_ns(d, "04:00:00") for d in em["event_date_canonical"]])) / C.MIN_NS)
    evt = {"event_id": evs, "ticker": em["ticker"].tolist(), "date": em["event_date_canonical"].tolist(), "year": em["year"].astype(int).tolist(),
           "tau_tod_min": [round(float(x), 4) for x in tod], "tau_seg": [TAU_SEGS.index(s) for s in em["tau_segment"]],
           "tier": [TIERS.index(t) for t in em["price_tier"]], "dilution": [2 if pd.isna(x) else int(bool(x)) for x in em["dilution"]],
           "quotes_ingested": [int(bool(x)) for x in em["quotes_ingested"]],
           "rem": [[(TYPES.index(rem.loc[e, j]) if (e in rem.index and j in rem.columns and isinstance(rem.loc[e, j], str)) else 255) for j in (0, 1, 2, 5, 10, 20)]
                   for e in evs]}
    tab["_rows"] = {"t": "meta", "n": n, "b": ""}
    return tab, evt
