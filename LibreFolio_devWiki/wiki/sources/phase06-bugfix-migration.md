---
title: "Phase 06 Bugfix Migration Steps 1-3"
category: source
source_type: plan
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/
tags: [phase06, assets, fx, responsive, i18n, ui, bugfix]
related_features: [F-024, F-032, F-021]
related_decisions: [responsive-layout-strategy]
---

# Source: Phase 06 Bugfix Migration (Steps 1-3)

## Summary

Three-part plan covering UI/UX fixes and responsive layout improvements during Phase 06 Assets implementation. Part 1 focuses on initial bug identification. Part 2 (plan-phase06BugfixMigration-part2.md) covers responsive layout modes including the new `tablet-s` breakpoint (500-770px). Part 3 (plan-phase06BugfixMigration-part3.md) covers TypeScript error fixes and i18n migration.

## Key Decisions Extracted

### D1: Responsive Layout Strategy — 4-Mode System

**Decision**: Use 4 breakpoint modes instead of 3 for better adaptation to intermediate screen sizes.

**Breakpoints**:
```
wide:     ≥1100px — all filters and actions in single row
tablet:   770-1100px — filters on 2 rows, actions in 2×2 grid
tablet-s: 500-770px — filters stacked below datepicker, actions in vertical column (icon-only)
mobile:   <500px — everything stacked and centered
```

**Rationale**: The 500-770px range was too wide for `tablet` layout (filters and buttons didn't fit in row) but too large for `mobile` (wasted space with everything stacked). The `tablet-s` mode provides an intermediate layout with:
- Datepicker and filters aligned left, stacked vertically
- Action buttons in a right-aligned vertical column
- Icon-only buttons (no labels) to save space

**Affected pages**: `/assets/+page.svelte`, `/fx/+page.svelte`

**Implementation**: ResizeObserver watches container width and sets `layoutMode` state, CSS classes conditional on mode.

**Pattern**: This became the standard responsive pattern for list pages with filter bars.

### D2: i18n Key Migration — `sharedResource.*` Namespace

**Decision**: Create `sharedResource.*` namespace for actions used across multiple resource types (assets, FX).

**Migrated keys**:
- `fx.actions.syncAll` → `sharedResource.syncAll` ("Sync All" / "Sinc. Tutto")
- `fx.actions.refreshAll` → `sharedResource.refreshAll` ("Refresh All" / "Aggiorna Tutto")
- `fx.actions.settings` → `sharedResource.settings` ("Settings" / "Impostazioni")

**Rationale**: The FX page initially had these keys but the Assets page reused the same actions. Having them under `fx.*` namespace was semantically incorrect. The distinction between `common.sync` (singular, used in bulk action toolbar) and `sharedResource.syncAll` (explicit "all" wording for filter bar buttons) was intentional.

**Related**: [[decisions/i18n-key-rationalization]] — intentional duplicates strategy.

## Problems Documented

### P1: TypeScript `getUserStorage` Return Type Too Narrow

**Problem**: `getUserStorage<T extends string>(baseKey: string, defaultValue: T): T` inferred literal types (e.g., `'false'`) from string literals, causing false-positive "unintentional comparison" errors when checking `saved === 'true'`.

**Solution**: Changed return type from `T` to `string` — localStorage can return any string, not just the type of the default value.

**File**: `frontend/src/lib/utils/storage.ts`

**Affected**: Sidebar collapse state, files page view mode

### P2: DataTable `EditableNumberCell` Missing `min`/`max` Properties

**Problem**: `DataTable.svelte` used `cellContent.min` and `cellContent.max` on editable-number cells, but the `EditableNumberCell` interface didn't declare these properties → 14 TypeScript errors.

**Solution**: Added `min?: number` and `max?: number` optional properties to `EditableNumberCell` interface.

**File**: `frontend/src/lib/components/table/types.ts`

### P3: lucide-svelte Icon Type Incompatible with Svelte 5 `Component<>`

**Problem**: `BulkActionInfo.icon: Component` in DataTableToolbar required Svelte 5's `Component<{}, {}, string>` signature, but lucide-svelte icons (Svelte 4-style classes) didn't match → 8 TypeScript errors.

**Solution**: Used `icon: any` with eslint-disable comment (same approach already used in `table/types.ts` for `AnyComponent`).

**File**: `frontend/src/lib/components/table/DataTableToolbar.svelte`

**Note**: Lucide-svelte incompatibility is a known issue tracked in [[problems/tanstack-svelte5-incompatibility]] (similar root cause).

### P4: FxTable Provider Chain Missing Icons on First Render

**Problem**: `providerIconHtml()` called `getCachedFxProviders()` which returned `[]` if currency graph wasn't built yet → fallback to text provider names instead of icons.

**Solution**: Preload `getCurrencyGraph()` in FX page `onMount` before passing data to FxTable, ensuring provider cache is populated.

**File**: `frontend/src/routes/(app)/fx/+page.svelte`

### P5: Bulk Delete FX — Only Deletes Last Item

**Problem**: `handleBulkDeleteFx()` iterated `selectedFxRows` and called `handleDeletePair()` for each, but `handleDeletePair()` set `deletingPair = detail` (single) and opened a modal — each iteration overwrote the previous, so only the last pair was queued for deletion.

**Solution**: Created dedicated bulk delete flow:
1. New state `deletingPairs: Array<{base, quote, slug}>` (list, not single)
2. Bulk-specific modal showing list of all pairs with flag icons
3. `confirmBulkDelete()` iterates and deletes sequentially

**Pattern**: Same pattern applied to Assets bulk delete.

## UX Improvements Documented

### Filter Bar Layout Behavior (non-wide modes)

**Issue**: In `tablet` mode, the filters block used `flex-row flex-wrap`, so when there was enough space, filters would return to a single row — inconsistent with the 2-row design intention.

**Fix**: Changed CSS logic to **always use 2 rows in `tablet` and `tablet-s`** (datepicker above, filters below), only `wide` mode uses single-row flex-wrap.

### Action Button Label Visibility (`showActionLabels`)

**Logic**: 
- `wide` and `tablet`: labels visible (sufficient horizontal space)
- `tablet-s`: icon-only (space constrained, vertical layout)
- `mobile`: icon-only

**Implementation**: Conditional `<span>` rendering based on `showActionLabels` derived from `layoutMode`.

### Type Filter Dropdown — Badge Counts

**Enhancement**: Type filter dropdown shows asset count per type — e.g., "ETF (5)" — calculated from current filtered asset list. Types with 0 assets are hidden from dropdown.

## Testing Notes

**svelte-check**: 25 errors → 0 errors after G3/G4/G5 fixes.

**Backend E2E tests**: 401 errors fixed by adding auth to `test_complete_e2e_flow_yfinance` and `test_search_provides_all_required_fields`.

**Build a11y warnings**: All resolved (mainly redundant `@const` with type annotations).

## Source Files

| Role | Path |
|------|------|
| Source plans | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/` |
| Part 2 | `plan-phase06BugfixMigration-part2.md` |
| Part 3 | `plan-phase06BugfixMigration-part3.md` |
| Assets page | `frontend/src/routes/(app)/assets/+page.svelte` |
| FX page | `frontend/src/routes/(app)/fx/+page.svelte` |
| DataTable types | `frontend/src/lib/components/table/types.ts` |
| DataTableToolbar | `frontend/src/lib/components/table/DataTableToolbar.svelte` |
| Storage utils | `frontend/src/lib/utils/storage.ts` |
| i18n files | `frontend/src/lib/i18n/{en,it,fr,es}.json` |
