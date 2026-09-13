"""Chart 03 - does a pre-t0 dilution filing associate with worse continuation?

T3a keeps the direction the signed-off proposal pre-registered (events with a
dilution filing before t0 show worse continuation and a faster flip) -- but this
chart draws both sides with no ranking, no reference line, and no shading, exactly
like T3b/T3c, because Cooper's amendment removed the kill-condition margin for
every split, T3a included.

Failure appearance from the contract: a single aggregate bar standing in for the
small multiples -- collapsing the cross-cut hides exactly the heterogeneity T2
exists to control for.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import chart_common as K


def main() -> None:
    K.small_multiples_split_chart(
        split_key="t3a_flg_dilution_form_before_t0",
        split_label="flg_dilution_form_before_t0",
        filename="03_flg_dilution_split",
        title="03 · Dilution filing before t0 — net expectancy by year × price decile",
        caption_extra="248/20,951 events excluded (flg_quality='unavailable' -- a missing "
                      "filing search is not evidence of no filing, it is gated out entirely).",
        direction_note="Direction pre-registered by the architect's signed-off proposal: "
                       "worse continuation and a faster flip when a dilution filing precedes "
                       "t0. No kill-condition margin evaluated (Cooper's 2026-09-13 amendment) "
                       "-- both sides read as distributions, not a verdict.",
    )


if __name__ == "__main__":
    main()
