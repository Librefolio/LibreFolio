---
title: "FxSyncModal reuse: parent owns modal, child calls onOpenFxSync prop"
category: decision
status: resolved
date: 2026-06-04
tags: [frontend, transactions, fx, modal, architecture, svelte5]
related_features: [F-097, F-048]
related_decisions:
  - decisions/wac-inline-validate-commit
---

# FxSyncModal: Parent Owns Modal, Child Calls Prop

## Context

WAC calculation may fail when FX pairs are missing. The user needs to sync FX rates without leaving the FormModal. Initially, `WacPreviewSection` had its own FxSyncModal instance, but this caused z-index issues (modal behind FormModal) and duplicated state.

## Decision

**Single FxSyncModal instance in FormModal parent. Children call `onOpenFxSync` prop to request modal opening.**

Pattern:
```
FormModal (owns FxSyncModal, zIndex = parentZ + 10)
  └─ WacPreviewSection (prop: onOpenFxSync)
       └─ calls onOpenFxSync({pairs, dates}) when user clicks "Sync FX"
```

## Behavior

1. `WacPreviewSection` and the validation banner both call `handleSyncFx()` in FormModal
2. `handleSyncFx()` prepares pairs + date range → sets `showFxSyncModal = true`
3. FxSyncModal opens with `zIndex = parentZ + 10` (guaranteed above FormModal)
4. On sync complete: `onsynced` callback triggers re-validate; modal stays open for user to see results
5. On close: user clicks X or outside

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| FxSyncModal inside WacPreviewSection | z-index below FormModal, duplicate instances possible |
| Inline sync (no modal) | No progress feedback, no per-pair result visibility |
| Navigate to /fx page | Loses form context entirely |

## Consequences

- Single source of truth for sync state
- z-index stacking guaranteed correct
- Re-validate after sync happens automatically
- Pattern reusable for BulkModal (same `handleSyncFx` approach)

## Source files

| Role | Path |
|------|------|
| FormModal (owns modal) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| WacPreviewSection (prop consumer) | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
| FxSyncModal | `frontend/src/lib/components/fx/FxSyncModal.svelte` |
| SyncModalBase (zIndex prop) | `frontend/src/lib/components/fx/SyncModalBase.svelte` |
| Plan | `…/Bugfix-SPD/plan-R3-SP-D-WacFxEnrich.prompt.md` |

