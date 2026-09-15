"""Chart 05 - does a reverse split in the trailing 365 days associate with the
outcome, in either direction?

Undirected per Cooper's 2026-09-13 amendment ("no pre reg") -- same basis as
chart 04, both tails reported, no reference line.

Failure appearance from the contract: same failure mode as chart 04 -- a
reference line or shading implying a threshold that does not exist for this split.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import chart_common as K


def main() -> None:
    K.small_multiples_split_chart(
        split_key="t3c_spl_reverse_split_365d",
        split_label="spl_reverse_split_365d",
        filename="05_spl_reverse_split",
        title="05 · Reverse split in trailing 365 days — net expectancy by year × price decile",
        caption_extra="12,219/20,951 events excluded (spl_quality='unavailable', 58% of the "
                      "population -- a missing split history is not evidence of no split, it "
                      "is gated out entirely, matching T3a's flg_ treatment).",
        direction_note="Undirected (Cooper's 2026-09-13 amendment, 'no pre reg') -- both tails "
                       "reported without comment, no kill-condition margin evaluated.",
    )


if __name__ == "__main__":
    main()
