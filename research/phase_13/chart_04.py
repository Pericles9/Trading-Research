"""Chart 04 - does share turnover (split-adjusted) associate with the outcome, in
either direction?

Undirected per Cooper's 2026-09-13 amendment ("no pre reg") -- both tails reported,
no reference line, no threshold implying a direction was expected.

Failure appearance from the contract: a reference line or shading implying a
threshold -- this split has no pre-registered direction and no kill condition.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import chart_common as K


def main() -> None:
    K.small_multiples_split_chart(
        split_key="t3b_high_turnover_above_median",
        split_label="share turnover above population median",
        filename="04_shs_turnover_split",
        title="04 · Share turnover (split-adjusted) — net expectancy by year × price decile",
        caption_extra="Turnover = event-day tick volume / shs_shares_outstanding, split-adjusted "
                      "via spl_ history (1,741/20,951 events needed the adjustment). "
                      "8,980/20,951 events excluded (no defined turnover value); split at the "
                      "population median among the remainder.",
        direction_note="Undirected (Cooper's 2026-09-13 amendment, 'no pre reg') -- both tails "
                       "reported without comment, no kill-condition margin evaluated.",
    )


if __name__ == "__main__":
    main()
