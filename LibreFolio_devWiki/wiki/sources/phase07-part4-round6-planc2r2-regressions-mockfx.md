---
title: "Phase 07 Part 4 Round 6 Plan C2 Round 2 — Fix Regressions + MockFX + Auto-populate Removal"
category: source
source_type: plan
date_ingested: 2026-05-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md
tags: [phase07, transactions, mockfx, auto-populate, fx-fallback, distribution-editor, balance-walk, contextual-validate, docker, e2e, testing]
related:
  - sources/phase07-part4-round6-planc2-bugfix-pair-validation
  - sources/phase07-part4-round6-planc3-pendingop-refactor
  - decisions/auto-populate-removal
  - decisions/formmodal-contextual-validate
  - decisions/end-of-day-balance-check
  - features/F-048
  - features/F-015
---

# Source: Plan C2 Round 2 — Fix Regressions + MockFX + Auto-populate Removal + Tests

## Summary

Plan C2 Round 2 addresses regressions from C2, establishes MockFX infrastructure for deterministic FX testing, removes the implicit auto-populate from `bulk_assign_providers()` (metadata flow becomes frontend-driven: probe → diff modal → PATCH), adds FormModal context-aware validation (sends entire bulk to `/validate`), confirms end-of-day balance walk algorithm correctness, and adds 8 backend balance walk tests + 3 E2E asset classification tests + 3 FX fallback tests. Three sessions of execution with additional fixes (RotateCcw icon, FX auto-sync on edit, reloadMetadata gate).

## Key Takeaways

- **MockFX providers** (Step 1): `MockFXProvider` (code `MOCKFX`, deterministic rates via hash) + `MockFXFailProvider` (code `MOCKFX_FAIL`, always raises). Both registered via `@register_provider(FXProviderRegistry)`. Hidden from user API via filter in `fx.py`
- **Auto-populate removal** (Step 2): Entire auto-populate block (righe 980-1062) removed from `bulk_assign_providers()`. Metadata flow is now exclusively frontend-driven: provider probe → diff display → explicit user PATCH. See [[decisions/auto-populate-removal]]
- **DistributionEditor fix** (Step 3): Removed `Math.min(100, ...)` cap and `max: 100` HTML attribute — percentages can exceed 100 during editing (validated only at save time)
- **FX auto-sync removal** (Step 4): Removed `await handleSync()` from `handleProviderModalCreated` in FX detail page — user controls sync timing
- **Pydantic errors=None** (Step 5): `FXSyncPairResult.errors` schema is `List[str]` not `Optional[List[str]]` — fixed 3 occurrences of `None` → `[]`
- **Build order** (Step 6): Font download (`update_js_cache`) moved before frontend build in both `_docker_ensure_assets_built()` and `cmd_fe_build()` — SvelteKit prerender requires fonts to exist
- **FormModal contextual validate** (Pending section): FormModal now sends entire bulk context to `/validate` via `getBulkContext()` callback from BulkModal. Issues filtered to show only current row. Contextual i18n banner header when errors come from batch inter-dependencies. See [[decisions/formmodal-contextual-validate]]
- **End-of-day balance algorithm confirmed**: `_validate_broker_balances()` already processes all transactions of a day before checking — order within day is irrelevant. The observed FormModal issue was context (missing bulk), not algorithm. See [[decisions/end-of-day-balance-check]]
- **Balance walk tests** (8 tests): `test_tx_balance_walk.py` — same-day deposit+buy (both orders pass), net negative fail, multi-day cumulative, edit move date cascade, delete cascade, compensating ops, single vs batch validate
- **Toast i18n keys** (Session 3): 3 keys added (`transactions.toast.{created,updated,deleted}`), contextual banner key (`transactions.validate.contextualIssuesHeader`), asset hint key (`transactions.toast.assetCreatedHint`)

## Execution Sessions (3)

### Session 1 (pre-context-break)
All 10 steps implemented. Review found: `pair_routes_map` type correction, MockFX reworked with `MOCKFX_FIXED_RATE = Decimal("1.234500")`, DistributionEditor `max` removed from HTML.

### Session 2 (2026-05-11)
5 additional fixes:
- **A**: Auto-populate block still present (missed in session 1) → removed
- **B**: Third `errors=None` occurrence in `_compute_single_step` → fixed
- **C**: `RotateCcw` icon → `RotateCw` in FxPairAddModal (visual rotation direction)
- **D**: FX detail auto-sync on edit → gated with `if (!editMode)`
- **E**: FX global toast after sync at pair creation → added

All test suites pass: API 35/35, Services 543/543, Frontend 6/6 categories (including new `asset-classification`).

### Session 3 (2026-05-11)
i18n keys + balance walk tests (8/8 pass) + FormModal context-aware validate + Docker gosu entrypoint + translate-diff LaTeX validation.

## Test Results Summary

| Suite | Count | Status |
|-------|-------|--------|
| API groups | 35 | ✅ (includes 3 FX fallback MOCKFX tests) |
| Services | 543 | ✅ (includes 6 assign/refresh metadata tests) |
| Schemas | 231 | ✅ |
| Frontend categories | 6 | ✅ (includes new asset-classification E2E) |
| Balance walk | 8 | ✅ (confirms end-of-day algorithm) |

## Decisions Captured

1. [[decisions/auto-populate-removal]] — metadata flow now frontend-driven (probe → diff → PATCH)
2. [[decisions/formmodal-contextual-validate]] — FormModal sends entire bulk to /validate
3. [[decisions/end-of-day-balance-check]] — same-day order irrelevant; algorithm confirmed correct

## Wiki Pages Updated

- [[features/F-048]] — contextual validate, bulk context passing, balance walk confirmation
- [[features/F-015]] — MockFX providers for deterministic testing
- [[decisions/auto-populate-removal]] — new
- [[decisions/formmodal-contextual-validate]] — new
- [[decisions/end-of-day-balance-check]] — new

## Source files

| Role | Path |
|------|------|
| MockFX providers | `backend/app/services/fx_providers/mockfx.py` |
| FX API (filter MOCKFX) | `backend/app/api/v1/fx.py` |
| Asset source (auto-populate removed) | `backend/app/services/asset_source.py` |
| DistributionEditor | `frontend/src/lib/components/ui/input/DistributionEditor.svelte` |
| FX pair page | `frontend/src/routes/(app)/fx/[pair]/+page.svelte` |
| FX service (errors fix) | `backend/app/services/fx.py` |
| dev.py (build order) | `dev.py` |
| AssetModal (data-testid) | `frontend/src/lib/components/assets/AssetModal.svelte` |
| Test asset source | `backend/test_scripts/test_services/test_asset_source.py` |
| Test FX sync (MOCKFX) | `backend/test_scripts/test_api/test_fx_sync.py` |
| E2E asset classification | `frontend/e2e/assets/asset-classification.spec.ts` |
| Balance walk tests | `backend/test_scripts/test_api/test_tx_balance_walk.py` |
| FormModal (contextual validate) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| BulkModal (getBulkContext) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| FxPairAddModal (RotateCw fix) | `frontend/src/lib/components/fx/FxPairAddModal.svelte` |
| Dockerfile + entrypoint.sh | `Dockerfile`, `entrypoint.sh` |
| Test runner frontend asset | `scripts/test_runner/_frontend_asset.py` |
| Test runner frontend tx | `scripts/test_runner/_frontend_transaction.py` |

