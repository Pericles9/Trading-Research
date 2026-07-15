---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/needs-review
created: 2026-07-12
---

# Hardware Investigation — T4: SMART Reliability Data

## Blocked — administrator elevation not available in this environment

Two methods attempted, both require admin rights this session doesn't have:

1. **`Get-PhysicalDisk | Get-StorageReliabilityCounter`** — failed for all
   three disks with `Access to a CIM resource was not available to the
   client.` This is the standard Windows Storage Management API for
   reallocated/pending/uncorrectable sector counts, wear level, and
   temperature. Requires elevation.
2. **`chkdsk D: /scan`** (explicitly sanctioned as a safe, read-only check
   per this task's own context) — failed: `Access Denied as you do not
   have sufficient privileges... invoke this utility running in elevated
   mode.`
3. Checked for `smartctl` (smartmontools) as a third-party alternative —
   not installed.
4. Tried the legacy `MSStorageDriver_FailurePredictStatus` WMI class —
   returned no data (also elevation-gated in practice).

## What this means

I cannot get the objective, drive-internal reallocated/pending-sector
counts that would most directly confirm or rule out genuine physical media
degradation on D: or E:, independent of the read-pattern-dependent
kernel event log. The `disk_identity_mapping.md` and
`shared_cause_check.md` findings stand on their own (kernel-level bad-block
events, correctly mapped to drive letters) but aren't corroborated by
SMART-level detail here.

## Recommended, not attempted

This needs to be run by Cooper directly, in an elevated PowerShell session
or via Samsung Magician (for the 870 EVO specifically — Samsung's own tool
reads SMART data reliably and flags failure risk) or CrystalDiskInfo (works
across all three disks, no elevation prompt friction for most builds). Read
those tools' reallocated-sector and pending-sector counts for the Samsung
870 EVO in particular, given it's the more urgent of the two per T2.
