---
title: "DataTable net columns hidden despite real costs (visibility snapshot bug)"
category: "problem"
status: resolved
date: 2026-07-22
tags: ["frontend", "datatable", "fifo", "net-metrics"]
related: ["decisions/fifo-v4-gross-net-status-model", "entities/fifo-lot-engine"]
---

# Problem: DataTable net columns hidden despite real costs

## Symptom
A production asset had a correct net breakdown visible in the lot detail modal, but the corresponding net
columns in the lots table stayed hidden by default, and clicking "reset" on the table did not reveal them
either.

## Root Cause
`DataTable.svelte` stored a **single visibility snapshot** per column set. That snapshot could not distinguish
between "hidden because the dynamic default (`hasNetCosts`) currently says hide" and "hidden because the user
explicitly hid it" — and critically, it never re-evaluated when `hiddenByDefault` flipped after the async data
load finished (net columns should default to hidden only when *no* row has costs, but the snapshot was taken
before that was knowable).

## Solution
Switched `DataTable.svelte` from a single snapshot to an **override model**:
`columnVisibilityOverrides` (explicit user choices) plus a derived *effective* visibility that combines the
current dynamic default with any override. "Reset" now clears overrides and re-applies whatever the current
dynamic default is, instead of restoring a stale snapshot.

## Prevention
Any column whose default visibility depends on data that isn't known until after an async load (i.e. any
`hasX`-style dynamic default) needs the override model, not a one-time snapshot, or it will silently freeze
the wrong default the moment data quality/shape actually changes it. This DataTable component is shared —
future dynamic-default columns anywhere in the app inherit the fix, but the same pre-fix pattern would
reproduce this exact class of bug in *any* component that keeps its own ad-hoc visibility snapshot.

## Impact
UI-only bug, no data was ever wrong or lost — the net breakdown was correct in the modal the whole time; only
the table's default column visibility was stuck. Found during manual post-implementation testing of the FIFO
v4 FEE/TAX work (see [[decisions/fifo-v4-gross-net-status-model]]), fixed in the same pass before release.

## Source files
| File |
|------|
| `frontend/src/lib/components/table/DataTable.svelte` |
| `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/post-implementation-review-v5.md` §2.1-2.6 |
