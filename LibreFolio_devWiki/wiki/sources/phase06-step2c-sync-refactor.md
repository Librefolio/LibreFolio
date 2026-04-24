---
title: "Phase 06 Step 2c — Sync/Delete Refactor & 3-Phase Pipeline"
category: source
source_type: plan
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/plan-phase06Step2cSyncDeleteRefactor.prompt.md
tags: [phase06, architecture, sync, delete, backend, refactoring]
related_features: [F-027, F-024]
related_decisions: [three-phase-pipeline-pattern, sync-modal-base-pattern]
---

# Source: Phase 06 Step 2c — Asset Sync/Delete Refactor

## Summary

Major refactoring establishing patterns for bulk sync modals, clean delete with result reporting, and most importantly the **3-phase pipeline architecture** for bulk operations (PREPARE → FETCH → PERSIST). This pattern fixed concurrency bugs and became the standard for both FX and Asset bulk operations.

## Key Architectural Decisions

### D1: 3-Phase Pipeline Pattern for Bulk Operations

**Problem**: Original `bulk_refresh_prices` for assets shared a single SQLAlchemy session across N concurrent tasks. Each task did: `READ → FETCH → WRITE → COMMIT`. Concurrent commits on the same session → "This transaction is closed" errors.

**Solution**: Separate database access into 3 distinct phases with session isolation:

```
Phase 1 — PREPARE (shared session, batch queries)
├── SELECT * FROM asset_provider_assignment WHERE asset_id IN (...)
├── SELECT id, display_name, currency FROM asset WHERE id IN (...)
├── Build prepared_items dict: {asset_id → {assignment, asset, provider, params}}
└── Filter: skip assets without provider (→ SKIPPED result)

Phase 2 — FETCH (no database, parallel with semaphore)
├── For each asset with provider:
│   ├── async with semaphore:
│   │   ├── provider.get_history_value(identifier, params, start, end)
│   │   └── provider.get_current_value(identifier, params)
│   └── Store in fetch_results: {asset_id → {prices: [...], source: "..."}}
└── Network errors → store in fetch_errors: {asset_id → str}

Phase 3 — PERSIST (per-task session, parallel)
├── For each asset with fetched data:
│   └── async with AsyncSession(engine) as session:
│       ├── bulk_upsert_prices([...], session)
│       ├── assignment.last_fetch_at = now(); session.add(); session.commit()
│       └── return FARefreshResult(status, elapsed_ms, ...)
└── DB errors isolated per-task, don't corrupt others
```

**Benefits**:
1. **Correctness**: No concurrent commits on shared session
2. **Performance**: Batch queries (IN clause) instead of N sequential queries
3. **Error Isolation**: One asset's DB error doesn't block others
4. **Clarity**: Clean separation of concerns (read/fetch/write)

**Pattern Application**:
- **FX sync**: Already used 3-phase pattern (grouping legs by provider for batch fetch)
- **Asset sync**: Migrated from monolithic to 3-phase in Step 2c
- **Conceptual similarity**: Same pattern but different implementation (FX providers are batch-capable via `fetch_rates([CUR1, CUR2, ...])`, asset providers are per-identifier)

**Why not a generic orchestrator?**: Each phase has domain-specific logic (FX: route chains + multi-step, Asset: per-item + semaphore). The 3-phase **pattern** is the convention, not an abstraction.

**Status**: Documented as architectural pattern, not a base class.

### D2: SyncModalBase Component Pattern

**Problem**: FxSyncModal and AssetSyncModal had 80% duplicate code (table structure, status icons, error display, toast summary).

**Solution**: Extract common logic into `SyncModalBase.svelte` with specialized wrappers:

```
SyncModalBase.svelte (generic)
├── Props: items (array), syncFn (async function), columns (config)
├── State: syncing, results, progress counter
├── UI: modal shell, table with status column, error tooltips, toast summary
└── Logic: parallel sync with concurrency control, result aggregation

FxSyncModal.svelte (wrapper)
├── Imports SyncModalBase
├── Defines FX-specific columns: base/quote flags, provider chain icons
└── Passes fx_service.sync_pairs_bulk as syncFn

AssetSyncModal.svelte (wrapper)
├── Imports SyncModalBase
├── Defines Asset-specific columns: display_name, type badge, provider icon
└── Passes asset_service.bulk_refresh_prices as syncFn
```

**Benefits**:
- Single source of truth for sync modal behavior
- Easy to add new resource-specific sync modals (brokers, transactions)
- Consistent UX across all sync operations

**Implementation**: Located in `frontend/src/lib/components/ui/modals/SyncModalBase.svelte`

### D3: Delete with Result Reporting

**Pattern**: Extend `ConfirmModal` with optional `results` prop to show per-item success/failure after bulk operations.

**Flow**:
```
1. User selects N items → click "Delete"
2. ConfirmModal opens with:
   - message: "Delete N items?"
   - items: [{label: "Asset 1", ...}, {label: "Asset 2", ...}]
   - confirmText: "Delete"
3. User confirms → backend deletes (parallel or sequential)
4. Backend returns: [{success: true, ...}, {success: false, error_code: "HAS_TRANSACTIONS"}]
5. ConfirmModal updates (same instance, no close):
   - results: [{label: "Asset 1", success: true}, {label: "Asset 2", success: false, detail: "has transactions"}]
   - Confirm button changes to "Close"
   - Body shows ✅/❌ list instead of original message
6. User clicks "Close" → toast summary
```

**Backend Schema Enhancement**: `FAAssetDeleteResult` now includes:
- `display_name` (for UI display, avoiding extra query)
- `error_code` ("HAS_TRANSACTIONS" | "NOT_FOUND" | null) — structured for i18n lookup

**FX Delete Enhancement**: Similar pattern, includes `count` (number of rates deleted) in result and toast.

**Related**: [[decisions/i18n-key-rationalization]] for toast message keys.

### D4: Helper Module Refactoring

**Created**:
- `syncHelpers.ts`: Shared logic for sync result aggregation, status mapping
- `providerHelpers.ts`: Provider icon URL lookup (renamed from `fxSync.ts`, now handles both FX and Asset providers)
- `responsiveLayout.svelte.ts`: Runes-based layout mode detection (ResizeObserver wrapper)

**Rationale**: Reduce duplication between FX and Asset pages, establish reusable patterns.

## Problems Solved

### P1: Asset Sync "Transaction Closed" Error

**Root Cause**: N concurrent async tasks shared 1 session, each doing `select → fetch → upsert → commit`. SQLAlchemy session is not thread-safe for concurrent writes.

**Solution**: 3-phase pipeline with per-task sessions in Phase 3 (see D1).

**Evidence**: Step G1 test suite grew from 1 smoke test → 7 robust tests covering concurrent multi-asset refresh.

### P2: FX Sync Result Message/Errors Redundancy

**Issue**: `FXSyncPairResult` had both `message` (human string) and `errors` (array) populated with overlapping info when sync failed.

**Cleanup**:
- **FAILED (exception)**: `errors = [str(e)]`, `message = None`
- **FAILED (no route)**: `errors = ["No route configuration..."]`, `message = None`
- **PARTIAL with leg errors**: `errors` from `chain_leg_details[].error`, `message` = informational note
- **OK/PARTIAL no errors**: `errors = []`, `message` = optional note

**Rationale**: Errors belong in structured `errors` array for frontend parsing. `message` is for human-friendly context, not error detail.

### P3: Delete Single Asset — Error Message Not Translated

**Before**: Toast showed generic error string from backend.

**After**: Backend returns `error_code`, frontend maps to i18n key:
```typescript
if (result.error_code === "HAS_TRANSACTIONS") {
  toast.error($t('assets.delete.hasTransactions', {name: result.display_name}))
}
```

**Keys added**: `assets.delete.hasTransactions` (4 languages).

## Testing Improvements

**Backend** (`test_asset_source_refresh.py`):
- 1 smoke test → 7 tests: single status, multi-asset concurrent (5 assets), SKIPPED, FAILED, mixed, currency fallback

**Frontend**: SyncModalBase integration tested via FX and Asset sync in E2E tests.

**Coverage debt**: Crypto assets (BTC/ETH) return PARTIAL (current value only, no history) — this is correct behavior but needs better documentation. Deferred to Phase 6 Step 4 (Asset detail page) for investigation.

## Source Files

| Role | Path |
|------|------|
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step2/plan-phase06Step2cSyncDeleteRefactor.prompt.md` |
| Asset sync backend | `backend/app/services/asset_source.py` (bulk_refresh_prices) |
| FX sync backend | `backend/app/services/fx.py` (sync_pairs_bulk) |
| SyncModalBase | `frontend/src/lib/components/ui/modals/SyncModalBase.svelte` |
| FxSyncModal | `frontend/src/lib/components/fx/FxSyncModal.svelte` |
| AssetSyncModal | `frontend/src/lib/components/assets/AssetSyncModal.svelte` |
| ConfirmModal | `frontend/src/lib/components/ui/modals/ConfirmModal.svelte` |
| syncHelpers | `frontend/src/lib/utils/syncHelpers.ts` |
| providerHelpers | `frontend/src/lib/utils/providerHelpers.ts` |
| responsiveLayout | `frontend/src/lib/utils/responsiveLayout.svelte.ts` |
| Asset sync tests | `backend/test_scripts/test_services/test_asset_source_refresh.py` |
