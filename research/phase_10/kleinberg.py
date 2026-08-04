"""
Arm A -- Kleinberg's two-state burst automaton for CONTINUOUS streams.

Reference: J. Kleinberg, "Bursty and Hierarchical Structure in Streams",
KDD 2002, section 2 -- the infinite-state automaton over inter-arrival gaps,
restricted here to k = 2 states per config.arm_a.n_states.

This is the continuous-stream half of the paper, NOT the batched-data
variant of section 4: trade arrivals have no natural per-period denominator
(no "r of d documents"), so the batched proportion model does not apply.

Model, verbatim from the paper's construction:

  n     = number of arrivals, T = span of the stream (last - first)
  g     = T / n, the mean gap
  a_i   = (1/g) * s^i, the arrival rate in state i, i in {0, ..., k-1}
  f_i(x)= a_i * exp(-a_i * x), the state-i gap density

  sigma(i, x) = -ln f_i(x) = a_i * x - ln a_i    (cost of emitting gap x in state i)
  tau(i, j)   = (j - i) * gamma * ln(n) for j > i, else 0   (state-change cost)

The optimal state sequence minimises sum_t [ sigma(q_t, x_t) ] + sum_t [ tau(q_{t-1}, q_t) ],
found by Viterbi. With k = 2 this is a two-column DP, vectorised over the
whole gap sequence in a single pass.

gamma is the only thing preventing single-gap state flips -- Arm A has no
explicit minimum-dwell floor. That is the point of the arm contrast and is
recorded in config.arm_a.gamma_desc.

No spine numeric column is read anywhere in this module (D4): the only
inputs are tick arrival timestamps.
"""
from __future__ import annotations

import numpy as np

__all__ = ["kleinberg_two_state", "bursts_from_states", "state_costs"]


def state_costs(gaps: np.ndarray, s: float, n: int, span_seconds: float) -> tuple[np.ndarray, float]:
    """Per-gap emission cost sigma(i, x) for i in {0, 1}, plus the transition cost.

    Returns (cost, tau) where cost has shape (2, len(gaps)) and tau is the
    scalar 0 -> 1 transition cost. 1 -> 0 is free, per the paper.
    """
    g = span_seconds / n
    a0 = 1.0 / g
    a1 = a0 * s
    # sigma(i, x) = a_i * x - ln a_i
    cost = np.empty((2, gaps.size), dtype=np.float64)
    cost[0] = a0 * gaps - np.log(a0)
    cost[1] = a1 * gaps - np.log(a1)
    tau = 1.0 * 1.0 * np.log(n)  # (j - i) = 1, gamma applied by caller
    return cost, tau


def kleinberg_two_state(
    timestamps_ns: np.ndarray,
    s: float,
    gamma: float,
    zero_gap_floor_seconds: float = 1e-9,
) -> dict:
    """Optimal two-state sequence over the inter-arrival gaps of `timestamps_ns`.

    `timestamps_ns` must be sorted ascending. Returns a dict with the per-gap
    state path (length n-1), the number of gaps floored, and the model scalars.
    """
    ts = np.asarray(timestamps_ns, dtype=np.float64)
    n = ts.size
    if n < 2:
        return {
            "states": np.zeros(0, dtype=np.int8), "n_arrivals": int(n), "n_gaps": 0,
            "n_gaps_floored": 0, "span_seconds": 0.0, "alpha_0": None, "alpha_1": None,
            "transition_cost": None,
        }

    gaps = np.diff(ts) / 1e9  # ns -> seconds
    n_floored = int((gaps < zero_gap_floor_seconds).sum())
    np.maximum(gaps, zero_gap_floor_seconds, out=gaps)

    span = float(ts[-1] - ts[0]) / 1e9
    if span <= 0.0:
        # every print at the same instant: no time structure to segment
        return {
            "states": np.zeros(gaps.size, dtype=np.int8), "n_arrivals": int(n),
            "n_gaps": int(gaps.size), "n_gaps_floored": n_floored, "span_seconds": 0.0,
            "alpha_0": None, "alpha_1": None, "transition_cost": None,
        }

    cost, tau_unit = state_costs(gaps, s, n, span)
    tau = gamma * tau_unit  # cost of 0 -> 1; 1 -> 0 is free

    m = gaps.size
    # Viterbi, two states. C[i] = best cost of paths ending in state i.
    # back[i, t] = predecessor state of state i at step t.
    back = np.empty((2, m), dtype=np.int8)
    c0 = cost[0, 0]
    c1 = cost[1, 0] + tau  # the automaton starts in state 0
    back[0, 0] = 0
    back[1, 0] = 0
    for t in range(1, m):
        # into state 0: from 0 (free) or from 1 (free, j < i)
        if c0 <= c1:
            n0, b0 = c0, 0
        else:
            n0, b0 = c1, 1
        # into state 1: from 0 (pay tau) or from 1 (free)
        if c0 + tau <= c1:
            n1, b1 = c0 + tau, 0
        else:
            n1, b1 = c1, 1
        c0 = n0 + cost[0, t]
        c1 = n1 + cost[1, t]
        back[0, t] = b0
        back[1, t] = b1

    states = np.empty(m, dtype=np.int8)
    states[-1] = 0 if c0 <= c1 else 1
    for t in range(m - 1, 0, -1):
        states[t - 1] = back[states[t], t]

    g = span / n
    return {
        "states": states,
        "n_arrivals": int(n),
        "n_gaps": int(m),
        "n_gaps_floored": n_floored,
        "span_seconds": span,
        "alpha_0": 1.0 / g,
        "alpha_1": s / g,
        "transition_cost": float(tau),
    }


def bursts_from_states(timestamps_ns: np.ndarray, states: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Maximal runs of state 1 -> burst intervals.

    `states[t]` is the state assigned to the gap between arrival t and t+1, so
    a run of state 1 over gaps [a, b] spans arrivals a .. b+1.

    Returns [(start_idx, end_idx, start_ns, end_ns), ...] with inclusive arrival
    indices into `timestamps_ns`.
    """
    st = np.asarray(states, dtype=np.int8)
    if st.size == 0:
        return []
    padded = np.concatenate(([0], st, [0]))
    edges = np.diff(padded)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1) - 1
    ts = np.asarray(timestamps_ns)
    return [
        (int(a), int(b + 1), int(ts[a]), int(ts[b + 1]))
        for a, b in zip(starts, ends)
    ]


def _selftest() -> None:
    """Exactness check against a directly-enumerated optimum.

    With 6 arrivals the gap sequence has 5 elements and the state space is
    2**5 = 32 paths, so the Viterbi answer can be checked against brute force.
    Also checks the burst-resolution index arithmetic.
    """
    import itertools

    rng = np.random.default_rng(0)
    for trial in range(200):
        # quiet-burst-quiet arrival pattern, jittered
        gaps = np.array([10.0, 9.0, 0.2, 0.1, 8.0]) * (1 + 0.5 * rng.random(5))
        ts = np.concatenate(([0.0], np.cumsum(gaps))) * 1e9
        s, gamma = 2.0, 1.0
        got = kleinberg_two_state(ts, s, gamma)

        n, span = ts.size, float(ts[-1] - ts[0]) / 1e9
        cost, tau_unit = state_costs(np.diff(ts) / 1e9, s, n, span)
        tau = gamma * tau_unit
        best, best_path = np.inf, None
        for path in itertools.product((0, 1), repeat=5):
            c = 0.0
            prev = 0
            for t, q in enumerate(path):
                if q > prev:
                    c += (q - prev) * tau
                c += cost[q, t]
                prev = q
            if c < best:
                best, best_path = c, path
        assert tuple(got["states"]) == best_path, (trial, tuple(got["states"]), best_path)

    # burst resolution: gaps 1 and 2 in state 1 -> arrivals 1..3
    ts = np.arange(6, dtype=np.float64) * 1e9
    assert bursts_from_states(ts, np.array([0, 1, 1, 0, 0], dtype=np.int8)) == [
        (1, 3, 1_000_000_000, 3_000_000_000)
    ]
    assert bursts_from_states(ts, np.array([1, 1, 1, 1, 1], dtype=np.int8)) == [
        (0, 5, 0, 5_000_000_000)
    ]
    assert bursts_from_states(ts, np.zeros(5, dtype=np.int8)) == []
    print("kleinberg selftest OK (200 brute-force trials + burst-resolution cases)")


if __name__ == "__main__":
    _selftest()
