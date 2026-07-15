---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/complete
created: 2026-07-12
---

# Hardware Investigation — T3: Shared Root Cause Check

## Timing correlation: does not support a single simultaneous event

E:'s error burst (July 9, 8:47–8:59 PM) and D:'s error window (July 11
5:39 PM – July 12 1:33 PM) **do not overlap at all** — there's a clean
~45-hour gap between E:'s last event and D:'s first. If a single physical
event (e.g. a cable jarred loose or a power-rail glitch during the July 9
install) had disturbed both drives at once, both would be expected to show
errors in the same burst window. They don't. This argues against "one
event, same moment, two symptoms."

It doesn't fully rule out a connection-quality explanation, though: both
drives are SATA, sharing controller/cable/power infrastructure that could
have been *disturbed* (not necessarily fully dislodged) during the July 9
case-opening to install E:. A marginal/partially-reseated connection can
behave fine under light I/O and only start throwing errors once put under
sustained heavy load — which is exactly what happened to D: starting July
11 (the failed 102GB ingestion write, then today's large-scale copy reads).
That timing is at least as consistent with "D: has its own, independent,
newly-active problem that heavy I/O surfaced" as with "the July 9 install
disturbed D:'s connection and it took two days under normal light use to
show up."

## Controller-level and PNP events: no corroborating evidence either way

Searched the System log for `storahci`/`stornvme`/`ataport`/`storport`
provider events (SATA/NVMe controller-level resets, link renegotiation,
timeouts) in the same window — **none found**. Also checked for
`Kernel-PnP` device-disconnect events — the only Event ID 153/129 entries
in the log are routine `Kernel-Boot`/`Hyper-V-Hypervisor` boot-time
notices that appear at every system start, not device removal/reconnection
events.

The absence of controller-level errors is weak evidence, not strong —
marginal connections don't always generate a distinct controller log entry
before the drive itself starts reporting bad blocks — but there's no
positive signal here pointing at a shared cabling/controller cause either.

## Conclusion

**Inconclusive on root cause, but the two disks' problems are temporally
independent, not simultaneous.** The evidence doesn't clearly support "one
shared physical cause" over "two separate issues, one of which (D:) may
have been aggravated or triggered by this session's sustained heavy I/O."
Both remain live possibilities. This can't be resolved further without
physical inspection (reseating cables) or admin-level diagnostics (T4 was
blocked — see `smart_reliability_data.md`), which is why T5's priority is
securing the data rather than further diagnosing cause.
