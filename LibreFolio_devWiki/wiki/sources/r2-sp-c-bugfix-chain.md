# Source: SP-C Bugfix Chain (11 plans) — BulkModal + Suggest + WAC Preview

> **Ingested**: 2026-06-02 | **Anchor**: `84f8bd07`
> **Status**: ALL ✅ COMPLETED (2026-05-18 → 2026-06-01)
> **Parent plan**: [[sources/r2-sp-c-bulkmodal-suggest-ux]]

---

## Overview

This batch covers 11 completed plans forming the SP-C sub-plan of the D2-Round2 walktest feedback. These plans fixed 40+ bugs in the BulkModal suggest/promote UX and built the WAC (Weighted Average Cost) preview system from scratch.

### Plan Dependency Chain

```
plan-SP-C-BugfixRound1 (12 bugs: commit, suggest, UX)
  └── plan-SP-C-BugfixRound2-WacPreview (13 bugs + WAC preview architecture)
        ├── plan-SP-C-FxImpliedRateSpread (FX enrichment in banner)
        └── WacPreview/ (8 deep WAC plans)
              ├── plan-BugfixRound3-UnifiedPartnerArch (pairedWith architecture)
              ├── plan-ReactiveWacBulkModal (auto-recalc, fingerprint invalidation)
              │     ├── plan-FixCloneLinkUuid (clone generates link_uuid)
              │     └── plan-FixWacFeedbackLoop (cost_basis_mode field)
              │           └── plan-WacInlineValidateCommit (WAC in /validate + /commit)
              │                 └── plan-FixWacPartnerRows (wac_results remapping)
              ├── plan-StatelessWacPreview (controlled component, mode persistence)
              └── plan-WacBackendCleanup (schema consolidation, dead code removal)
```

---

## Plan Summaries

### 1. BugfixRound1 (2026-05-24) — 12 bugs

Fixed 12 bugs from SP-C walktest. Key fixes:
- **BUG-C3** (P0): Commit lost edits on split-queued rows — fixed skip condition to check `deriveStatus(d) !== 'edited'`
- **BUG-C7**: Suggest showed DB candidates as direct actions — redesigned to open PromoteMergeModal
- **BUG-C10**: Suggest didn't detect local pairs after edit
- **BUG-C12** (P0): Promote-suggest `$effect` sent unsigned amounts → `cash_amount=opposite` constraint failed

### 2. BugfixRound2-WacPreview (2026-05-26) — 13 bugs + WAC architecture

Introduced the WAC Preview system:
- New `POST /transactions/wac-preview` endpoint (inventory-aware PMC calculation)
- `WacPreviewSection.svelte` component with Auto/Manual toggle
- FormModal integration with live WAC preview
- Eliminated old `POST /recalc-wac` endpoint
- Bug 8 → spawned UnifiedPartnerArch plan
- Bug 9-10-11 → spawned ReactiveWacBulkModal plan

### 3. FxImpliedRateSpread (2026-05-18) — FX enrichment

Frontend-only plan adding:
- `lookupFxRate()` utility in `fxStoreRegistry.ts` — self-fetching spot lookup with cache
- `fxMarketCache` Map in BulkModal — reactive market rate display
- Implied rate (from TX amounts), market rate (from FX system), spread calculation
- Tooltip with stale-rate warning in suggest banner

### 4. UnifiedPartnerArch (2026-05-26) — pairedWith architecture

Unified partner architecture refactor:
- `pairedWith: string` field on PendingOp (tempId reference)
- `getPartnerOp(ops, tempId)` — O(1) partner lookup
- `visibleOps` derived — filters out hidden partners (inaccessible broker)
- `resolveFormItems()` — builds FormModal items from visible ops
- Fixed Bug 8: partner broker lost on edit paired TX

### 5. ReactiveWacBulkModal (2026-05-30) — auto-recalc

Reactive WAC calculation in BulkModal:
- **Fingerprint invalidation**: serializes WAC-relevant fields → triggers recalc only on material change
- **fxMarketCache**: caches FX rates for WAC calculations
- **CostBasisFieldMode**: `'auto' | 'manual' | 'auto-detail'` state machine per row
- **wacResults Map**: `Map<tempId, WACPreviewResultItem>` for cell display
- Multiple architectural iterations (v4→v6) before stable design

### 6. FixCloneLinkUuid (2026-05-27) — clone duplication bug

**Problem**: Clone of paired rows (TRANSFER, FX_CONVERSION, CASH_TRANSFER) from DB rows didn't generate `link_uuid` because condition was `src.op === 'create' && src.link_uuid` (false for edit ops).

**Fix**: Promoted `link_uuid` from create-only to top-level PendingOp field. Clone logic now uses `getTypeRule(type)?.requiresPair ? generateUUID() : null`. Simplified `fetchBatchWac()` linkUuidMap from 30-line 3-branch workaround to direct field read.

### 7. FixWacFeedbackLoop (2026-05-28) — infinite recalculation loop

**Problem**: WAC recalc → writes `cost_basis_override` to cell → triggers fingerprint change → re-triggers WAC recalc → infinite loop.

**Fix**: Added explicit `cost_basis_mode: 'auto' | 'manual'` field to `WACPendingTXItem`. Backend math engine handles `add_at_wac` mode (adds quantity at current WAC, algebraically proven to not change WAC). Frontend sends mode in payload → backend decides what to do, no need to write override value pre-commit.

### 8. WacInlineValidateCommit (2026-05-28) — WAC in validate+commit

Eliminated standalone `/wac-preview` endpoint from editing flow:
- WAC computed server-side during `/validate` (returned in `wac_results[]`)
- WAC applied server-side during `/commit` (post-flush, using DB state)
- Added "Validate Now" button + pending indicator in WacPreviewSection
- Apply/discard flow for WAC values
- `cost_basis_mode` extended: `'auto' | 'manual' | 'auto-detail'`
- `/analytics/wac` endpoint created for historical time-series (Phase 9)

### 9. FixWacPartnerRows (2026-05-30) — partner row WAC display

**Problem**: Partner rows (receiver TRANSFER) didn't show WAC data because `wac_results` array indices didn't match visible row indices after partner filtering.

**Fix**: Remapped `wac_results[].index` to visible operation indices using `operation` field ('create'/'update') + positional matching. Added 9 FormModal E2E tests (FM1-FM9).

### 10. StatelessWacPreview (2026-05-30) — controlled component

**Problem**: Mode state lost on re-open (WacPreviewSection had internal state, initialized at mount with `untrack()`).

**Fix**: Made WacPreviewSection a fully controlled component:
- `variant` prop replaced with `mode` prop (parent-owned)
- No internal state — all mode changes via `onModeChange()` callback
- `_wacCache` added to PendingOp for result persistence across re-opens
- `cost_basis_mode` on PendingOp fields as authoritative source

### 11. WacBackendCleanup (2026-05-19) — schema + tests

Backend consolidation:
- `WACPreviewItem`: removed `as_of_date`, only `DateRangeModel` (required)
- `WACPendingTXItem` extends `TXCreateItem` (inherits validation)
- Eliminated `asset_price_at_date()` → uses `AssetSourceManager.get_prices_bulk`
- Fixed backward-fill to be unlimited (like FX system)
- 12 financial-utils unit tests (FU-1→FU-12)
- 22 WAC API tests (WAC-1→WAC-P9)

---

## Key Technical Patterns Established

### 1. Paired Partner Architecture
- `pairedWith: string` — tempId reference to partner op
- `getPartnerOp(ops, tempId)` — single lookup function
- `visibleOps = ops.filter(o => !isHiddenPartner(o))` — UI rendering layer
- `resolveFormItems(op, ops)` — builds form items respecting partner relationships

### 2. CostBasisFieldMode State Machine
```
auto ←→ manual (user toggles)
auto → auto-detail (user expands qualifying table)
manual → auto (user re-enables auto)
```
Mode persists on `PendingOp.fields.cost_basis_mode`. Not persisted to DB.

### 3. Fingerprint-Based Invalidation
WAC recalc triggered only when material fields change: `(broker_id, asset_id, date, quantity, cash, type)` serialized to string. Prevents unnecessary re-fetches.

### 4. WAC Inline in Validate/Commit
No standalone WAC endpoint in editing flow. WAC is:
- Computed in `/validate` response → frontend displays preview
- Applied in `/commit` post-flush → uses actual DB state for correctness

### 5. Stateless Preview Pattern
Components that display computed data should be **controlled** (props-in, callbacks-out). Internal state causes timing bugs with `$effect` + `untrack()`. Cache lives on the data model (PendingOp._wacCache), not the component.

### 6. link_uuid Promotion
`link_uuid` is a top-level field on PendingOp (not create-only). All paired operations (clone, collapse, hidden-partner) generate shared UUID based on type rule, not source op type.

---

## Source Files (primary)

| Role | Path |
|------|------|
| BulkModal (main file, ~2500 LOC) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| FormModal (WAC preview, dual-form) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| WacPreviewSection (controlled) | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
| PromoteMergeModal | `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` |
| FX store registry (lookupFxRate) | `frontend/src/lib/stores/fxStoreRegistry.ts` |
| TX types (PendingOp, DraftFields) | `frontend/src/lib/components/transactions/types.ts` |
| TX schemas (WACPreviewItem, etc.) | `backend/app/schemas/transactions.py` |
| TX service (compute_wac_iterative) | `backend/app/services/transaction_service.py` |
| Financial utils (WAC math) | `backend/app/utils/financial_utils.py` |
| Asset source (get_prices_bulk) | `backend/app/services/asset_source.py` |
| WAC API tests | `backend/test_scripts/test_api/test_transactions_wac.py` |
| Financial utils tests | `backend/test_scripts/test_services/test_financial_utils.py` |
| E2E WAC bulk tests | `frontend/e2e/transactions/tx-wac-bulk.spec.ts` |
| E2E WAC FormModal tests | `frontend/e2e/transactions/tx-wac-formmodal.spec.ts` |
| E2E commit all types | `frontend/e2e/transactions/tx-commit-all-types.spec.ts` |

---

## Original Plan Files

| # | Plan | Path |
|---|------|------|
| 1 | BugfixRound1 | `.../SP-C-Bugfix/plan-SP-C-BugfixRound1.prompt.md` |
| 2 | BugfixRound2-WacPreview | `.../SP-C-Bugfix/plan-SP-C-BugfixRound2-WacPreview.prompt.md` |
| 3 | FxImpliedRateSpread | `.../SP-C-Bugfix/plan-SP-C-FxImpliedRateSpread.prompt.md` |
| 4 | UnifiedPartnerArch | `.../SP-C-Bugfix/WacPreview/plan-BugfixRound3-UnifiedPartnerArch.prompt.md` |
| 5 | ReactiveWacBulkModal | `.../SP-C-Bugfix/WacPreview/plan-ReactiveWacBulkModal.prompt.md` |
| 6 | FixCloneLinkUuid | `.../SP-C-Bugfix/WacPreview/plan-FixCloneLinkUuid.prompt.md` |
| 7 | FixWacFeedbackLoop | `.../SP-C-Bugfix/WacPreview/plan-FixWacFeedbackLoop.prompt.md` |
| 8 | WacInlineValidateCommit | `.../SP-C-Bugfix/WacPreview/plan-WacInlineValidateCommit.prompt.md` |
| 9 | FixWacPartnerRows | `.../SP-C-Bugfix/WacPreview/plan-FixWacPartnerRows.prompt.md` |
| 10 | StatelessWacPreview | `.../SP-C-Bugfix/WacPreview/plan-StatelessWacPreview.prompt.md` |
| 11 | WacBackendCleanup | `.../SP-C-Bugfix/WacPreview/plan-WacBackendCleanup.prompt.md` |

---

## Wiki Pages Created/Updated

- [[problems/wac-feedback-loop]] — WAC recalc → field update → WAC recalc infinite loop
- [[problems/clone-link-uuid-duplication]] — Clone paired rows didn't generate link_uuid
- [[concepts/paired-partner-architecture]] — pairedWith, getPartnerOp, visibleOps pattern
- [[concepts/stateless-preview-pattern]] — Controlled components for computed previews
- [[decisions/wac-inline-validate-commit]] — WAC computed in validate/commit, not standalone endpoint
- [[features/F-097]] — Updated with bugfix chain references
- [[features/F-048]] — Updated with bugfix chain references
