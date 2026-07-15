---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/complete
created: 2026-07-12
---

# Hardware Investigation — T1/T2: Disk Identity and Error Mapping

## T1 — Definitive physical-disk-to-drive-letter mapping

Cross-referenced by `DiskNumber`/`Index`, confirmed by two independent
commands (`Get-Partition`+`Get-Volume`, and `Get-CimInstance
Win32_DiskDrive`) — not inferred from model name. All three agree exactly,
and match Cooper's confirmed ground truth:

| Disk # | Model | Serial | Bus | Size | Drive Letter | Volume Label |
|---|---|---|---|---|---|---|
| 0 | TOSHIBA DT01ACA100 | 7662G91NS | SATA | 1TB | **E:** | "HDD" |
| 1 | Samsung SSD 870 EVO 500GB | S62ANJ0R243151B | SATA | 500GB | **D:** | "500GB SSD" |
| 2 | CT1000P5SSD8 (Crucial P5) | 0000_...0B77 | NVMe | 1TB | **C:** | (unlabeled) |

**The earlier "Toshiba HDD = almost certainly D:" guess was wrong** — Disk
0 (Toshiba) is E:, Disk 1 (Samsung SATA SSD) is D:. Windows' internal
`\Device\HarddiskN\DRN` device-object naming corresponds directly to
`DiskNumber`/`\\.\PhysicalDriveN` (confirmed via `Win32_DiskDrive`'s
`DeviceID`/`Index` fields matching `Get-Disk`'s `Number` field 1:1 for all
three disks) — so `Harddisk0\DR0` = Disk 0 = E:, `Harddisk1\DR1` = Disk 1 =
**D:**.

## T2 — Error mapping, full itemized export

Re-filtered strictly to `ProviderName -eq 'disk'` (the earlier aggregate
count included 44 unrelated events — WSL NIC init, VBS security notices —
that coincidentally shared Event IDs 7/153 with genuine disk errors; those
are noise, not disk hardware signals). Clean result: **1,061 genuine disk
errors, all Event ID 7** (a true bad-block report — no Event ID 51/153
paging/retry events came from the `disk` provider itself). Full itemized
list: `disk_events_full.csv` (1,061 rows, not sampled).

| Device | Disk # | Drive | Count | Earliest | Latest |
|---|---|---|---|---|---|
| `\Device\Harddisk0\DR0` | 0 | **E:** | 174 | 2026-07-09 20:47:25 | 2026-07-09 20:59:49 |
| `\Device\Harddisk1\DR1` | 1 | **D:** | **887** | 2026-07-11 17:39:58 | 2026-07-12 13:33:46 |

## T2b — Does July 9 mark the start for one disk specifically?

**Yes, but only for E: — and this refines the original baseline.** The
original framing assumed both disks' ~1,061 errors span "July 9 through
present" together. That's not accurate:

- **E: (Toshiba)**: all 174 events fall in a single **12-minute burst** on
  July 9, 8:47–8:59 PM — exactly consistent with the drive's installation.
  **Zero events since** — 3 clean days including through today's heavy
  copy operations onto this same drive.
- **D: (Samsung SSD)**: all 887 events start **July 11, 5:39 PM** — two
  days *after* E:'s install, not on it — and continue through **July 12,
  1:33 PM**, ending right when the quote_data/ robocopy to E: was
  running. D: shows **more** errors than E:, over a longer, more recent,
  and still-active window, not a settled one-time burst.

## Urgent finding, per escalation criteria

**D: is confirmed as one of the two affected disks — and is the more
active of the two right now.** Its error window directly overlaps this
session's heaviest I/O on that drive (the 102GB `main.duckdb` write to
disk-full, and today's `filtered/`+`quote_data/` robocopy reads). Treating
this as urgent per the task's own criteria.
