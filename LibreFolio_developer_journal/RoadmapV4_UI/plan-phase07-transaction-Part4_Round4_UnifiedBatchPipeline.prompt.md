# Plan — Phase 7 · Part 4 · Round 4 — Unified Batch Pipeline

**Date**: 2026-04-29
**Status**: ✅ COMPLETED (full cleanup + hotfix applied 2026-04-29)
**Priority**: P0 (architectural — fixes W21/W22/W23 Pydantic 422 pre-emption)
**Estimated effort**: ~6–7 h

**Parent**: [`plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md`](./plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md) §"Decisione architetturale: Unified Batch Pipeline"

---

## 🎯 Obiettivo

Merge 4 tx mutation endpoints → 2, sharing single `TXMixedBatch` body with `List[dict]` for creates/updates (lenient parse). Unifies validation pipeline → schema errors + business-rule errors + balance violations coexist in one response. Fixes Pydantic 422 pre-emption (W21–W23).

---

## 🏗️ Endpoints

### Removed

| Endpoint | Body |
|----------|------|
| `POST /api/v1/transactions/bulk` | `List[TXCreateItem]` |
| `PATCH /api/v1/transactions/bulk` | `List[TXUpdateItem]` |
| `DELETE /api/v1/transactions/bulk` | `List[int]` (query) |

### New/refactored

| Endpoint | Body | Semantica |
|----------|------|-----------|
| `POST /api/v1/transactions/validate` | `TXMixedBatch` | Dry-run: always rollback |
| `POST /api/v1/transactions/commit` | `TXMixedBatch` | Commit if no issues |

---

## 📋 Steps

### Step 1 — New schemas (~30 min)

**File**: `backend/app/schemas/transactions.py`

Add after existing `TXValidateBatch`:

```python
class TXMixedBatch(BaseModel):
    """Unified batch body for /validate and /commit."""
    model_config = ConfigDict(extra="forbid")
    creates: List[dict] = Field(default_factory=list, max_length=500)
    updates: List[dict] = Field(default_factory=list, max_length=500)
    deletes: List[int] = Field(default_factory=list, max_length=500)

class TXBatchResultItem(BaseModel):
    """Per-item result for committed rows."""
    operation: Literal["create", "update", "delete"]
    index: int
    id: Optional[int] = None
    link_uuid: Optional[str] = None
    status: TXItemStatus

class TXBatchResponse(BaseModel):
    """Unified response for /validate and /commit."""
    committed: bool
    issues: List[TXValidationIssue] = []
    results: Optional[List[TXBatchResultItem]] = None
```

Mark old schemas (`TXValidateBatch`, `TXBulkCreateResponse`, `TXBulkUpdateResponse`, `TXBulkDeleteResponse`, `TXValidateResponse`) as `# DEPRECATED`.

---

### Step 2 — Service: `_parse_lenient` + `execute_batch` (~2 h)

**File**: `backend/app/services/transaction_service.py`

**2a** — `_parse_lenient(raw_list, model_class, operation)`:
- Per-row `model_validate(raw)` in try/except `ValidationError`
- Handle `multipleBusinessRuleErrors` expansion (same as frontend)
- Returns `(List[Tuple[int, BaseModel]], List[TXValidationIssue])`

**2b** — `execute_batch(creates_raw, updates_raw, deletes, user_id, commit)`:
1. Lenient parse creates + updates
2. Access check (EDITOR) per broker
3. Apply deletes → updates → creates (reuse existing logic)
4. Balance walk per affected broker
5. If issues → rollback. If clean + `commit=False` → rollback (dry-run). If clean + `commit=True` → return `committed=True` (router commits).

**2c** — Keep old methods temporarily for `promote_transfer` migration (Step 3d).

---

### Step 3 — Router: `/validate` + `/commit`, remove old (~45 min)

**File**: `backend/app/api/v1/transactions.py`

**3a** — Refactor `POST /validate`: body `TXMixedBatch`, call `execute_batch(commit=False)`.

**3b** — New `POST /commit`: body `TXMixedBatch`, call `execute_batch(commit=True)`. If `resp.committed` → `session.commit()` else `session.rollback()`.

**3c** — Delete `POST /bulk`, `PATCH /bulk`, `DELETE /bulk`.

**3d** — Migrate `promote_transfer` internal calls → `execute_batch`.

**3e** — Migrate `broker_service` internal call → `execute_batch`.

Both endpoints use `openapi_extra` with `TXCreateItem.model_json_schema()` / `TXUpdateItem.model_json_schema()` for docs.

---

### Step 4 — Delete deprecated schemas + service methods (~15 min)

Remove old response types, old service methods.

---

### Step 5 — Regen frontend types (~15 min)

`./dev.py api sync` → regenerate TypeScript client.

---

### Step 6 — Frontend migration (~1.5 h)

**6a** — `TransactionFormModal.svelte`: validate + commit → unified calls.

**6b** — `TransactionBulkModal.svelte`: same.

**6c** — `CashTransactionModal.svelte`: `POST /bulk` → `/commit` with `{creates: [...]}`.

**6d** — `BulkDeleteLinkedPairModal.svelte`: `DELETE /bulk` → `/commit` with `{deletes: [...]}`.

**Response mapping**: `rolled_back` → `!committed`, `errors` → `issues`, `results[].transaction_id` → `results[].id`.

---

### Step 7 — Frontend cleanup: 422 fallback → safety net (~15 min)

`extractValidationIssues` becomes defensive-only. Docstring update.

---

### Step 8 — Backend tests (~1 h)

- Migrate all existing tests to new endpoints
- New: schema+balance coexistence (W21 fix)
- New: mixed operations in one request
- New: commit vs validate same batch
- New: lenient parse partial failure

---

### Step 9 — Quick fixes W16/W17/W19 (~15 min)

Already applied in parent plan.

---

## ✅ Checklist

- [x] `TXMixedBatch` + `TXBatchResponse` schemas created
- [x] `_parse_lenient` helper handles per-row validation + `multipleBusinessRuleErrors`
- [x] `execute_batch` unified pipeline (parse → access → apply → balance → commit/rollback)
- [x] `POST /validate` → `execute_batch(commit=False)`
- [x] `POST /commit` → `execute_batch(commit=True)`
- [x] Old 3 endpoints removed
- [x] `promote_transfer` migrated → now uses `execute_batch` (delete originals + create new pair atomically)
- [x] `broker_service` — uses `execute_batch` for initial deposits; `delete_by_broker` is independent (keeps working)
- [x] Old schemas marked DEPRECATED
- [x] **Deprecated schemas deleted** (`TXBulkDeleteResponse`, `TXCreateResultItem`, `TXBulkCreateResponse`, `TXUpdateResultItem`, `TXBulkUpdateResponse`, `TXValidateBatch`, `TXValidateResponse`) — unused imports cleaned
- [x] **Deprecated service methods deleted** — `create_bulk`, `update_bulk`, `delete_bulk` removed from `TransactionService`; trailing `CREATE OPERATIONS (DEPRECATED)` section removed
- [x] **No DEPRECATED markers remain** in schemas or service (verified grep)
- [x] Frontend types regenerated
- [x] FormModal migrated
- [x] BulkModal migrated
- [x] CashTransactionModal migrated
- [x] BulkDeleteLinkedPairModal migrated
- [x] Backend tests migrated
- [x] **Backend test `test_transactions_validate.py` fixed** — adapted to `TXBatchResponse` contract (`committed`/`issues`/`results` instead of `would_rollback`/`balance_preview`/`holdings_preview`); fixed `_create_broker`/`_create_asset` payload format; fixed `_post_tx` status check
- [x] Frontend 422 fallback → safety net
- [ ] Schema+balance coexistence test (W21 proof) — needs manual E2E verification
- [x] `./dev.py api sync` clean
- [x] `transaction.ts` types fixed
- [x] **HOTFIX**: legacy `create_bulk` compat with `_validate_linked_pair` i18n tuple return (extract `[0]` for string)

---

## 🧹 Final Cleanup (2026-04-29)

Cleanup pass after all steps completed. Verified codebase state:

### Backend — what was removed
| Removed | From |
|---------|------|
| `create_bulk()`, `update_bulk()`, `delete_bulk()` methods | `transaction_service.py` |
| `TXBulkCreateResponse`, `TXBulkUpdateResponse`, `TXBulkDeleteResponse` | `schemas/transactions.py` |
| `TXCreateResultItem`, `TXUpdateResultItem` | `schemas/transactions.py` |
| `TXValidateBatch`, `TXValidateResponse` | `schemas/transactions.py` |
| `POST /bulk`, `PATCH /bulk`, `DELETE /bulk` endpoints | `api/v1/transactions.py` |
| All `# DEPRECATED` markers | schemas + service |

### Backend — what remains (final state)
| Component | State |
|-----------|-------|
| `_parse_lenient()` | ✅ module-level helper |
| `execute_batch()` | ✅ single entry point for all tx mutations |
| `delete_by_broker()` | ✅ independent utility (broker cascade delete) |
| `promote_transfer()` | ✅ migrated → calls `execute_batch` |
| `POST /validate` | ✅ `TXMixedBatch` → `execute_batch(commit=False)` |
| `POST /commit` | ✅ `TXMixedBatch` → `execute_batch(commit=True)` |
| `broker_service` initial deposits | ✅ calls `execute_batch` |

### Frontend — migrated components
| Component | Old call | New call |
|-----------|----------|----------|
| `TransactionFormModal` | `POST /bulk` + `PATCH /bulk` | `/validate` + `/commit` |
| `TransactionBulkModal` | `POST /bulk` + `PATCH /bulk` | `/validate` + `/commit` |
| `CashTransactionModal` | `POST /bulk` | `/commit` with `{creates:[…]}` |
| `BulkDeleteLinkedPairModal` | `DELETE /bulk` | `/commit` with `{deletes:[…]}` |
| `saveWithRetry.ts` | handled `rolled_back` | handles `committed`/`issues` |
| `transaction.ts` | old response types | `TXBatchResponse` type |

### Diff stats (22 files, net −113 lines)
```
backend:    366 ins, 656 del (net −290 lines — major simplification)
frontend:   164 ins, 182 del (net −18 lines)
tests:      465 ins, 270 del (net +195 lines — better coverage)
```

---

## 🐛 Post-completion Hotfix (2026-04-29)

**Problem**: `_validate_linked_pair` was changed to return `tuple[str, str, dict]` (i18n format) during the i18n validation errors refactor (Round 3). The new `execute_batch` correctly unpacks the tuple, but the legacy `create_bulk` method (still used by `promote_transfer` and service-level tests) was appending the raw tuple to `errors: List[str]` → Pydantic `ValidationError` on `TXBulkCreateResponse`.

**Fix**: In `create_bulk` Phase 2 link resolution, extract `pair_error[0]` (the message string) instead of the full tuple.

**Affected tests** (now passing):
- `TestLinkedPairValidation::test_pairing_rejects_mixed_types_in_link_uuid`
- `TestLinkedPairValidation::test_pairing_rejects_transfer_same_broker`

**Note**: this hotfix is now moot — `create_bulk` was subsequently deleted during the final cleanup. The fix is documented for historical completeness only.

---

## 🐛 Frontend Issues Found (manual E2E 2026-04-29)

### W24 — Balance error `index` always 0 (backend)

**Severity**: P1 (misleading)
**Where**: `transaction_service.py` L835 — `BalanceValidationError` catch uses hardcoded `index=0`
**Problem**: Balance violations (`balanceAssetNegative`, `balanceCashNegative`) are broker-wide — they don't originate from a single row. But the code reports `index: 0`, making the frontend display "Riga 1:" even when the offending tx is row 2+.
**Fix**: Use `index=-1` (or `null`) as sentinel for "broker-level, no specific row". Frontend `resolveIssueMessage` should skip the row prefix when `index < 0` or `null`. BulkModal `jumpToIssue` should not scroll when index is sentinel.

### W25 — Commit banner shows only first raw error, not translated

**Severity**: P1 (UX regression — validate shows proper i18n but commit doesn't)
**Where**: `TransactionFormModal.svelte` L485/L500, `TransactionBulkModal.svelte` L511/L527
**Problem**: On `committed: false`, both modals do `formError = resp.issues?.[0]?.error` — takes only the first issue's raw English string. The validate banner (green/warning) correctly uses `resolveIssueMessage()` + shows all issues as a list.
**Fix**: On commit failure, set `issues = resp.issues` and show the same styled warning banner as validate does (with all issues, translated, clickable in bulk). `formError` should only be used for HTTP/network errors from `saveWithRetry`. This unifies the error display and avoids duplication.

### W26 — Validate button style inconsistency (Form vs Bulk)

**Severity**: P2 (cosmetic)
**Where**: `TransactionFormModal.svelte` L906, `TransactionBulkModal.svelte` L1007
**Problem**: FormModal validate button is plain text (`⚡ Verifica ora`), positioned right-side alongside Cancel/Save. BulkModal has a proper `<Zap>` icon button on the left side of the footer.
**Desiderata**: Both modals should use the BulkModal's style — `<Zap>` icon + button on the **left** side of the footer, with Cancel/Save on the right. FormModal footer should mirror BulkModal's layout.

### W27 — HTTP 200 for validation failures (by design)

**Severity**: P3 (design question — no change needed)
**Where**: `POST /validate` and `POST /commit` return 200 even with `committed: false`
**Rationale**: 200 is correct — the server successfully processed the request and returned a structured response. The `committed` boolean is the semantic indicator. Using 422 would conflict with Pydantic's own 422 format and break the "lenient parse" design (schema errors coexist with business-rule errors in `issues[]`). A hypothetical 409 (Conflict) could work but adds complexity with no benefit since the client already checks `committed`. **Decision: keep 200.**

---

## 📋 Round 5 Plan — Frontend Error Display Unification

**Goal**: Unify error display in Form+Bulk modals so commit failures use the same translated, categorized issue list as validation.

### Step R5-1 — Backend: sentinel index for balance errors ✅

**File**: `backend/app/services/transaction_service.py` L835
- Changed `index=0` → `index=-1` for `BalanceValidationError` catch
- Updated `TXValidationIssue.index` schema: `ge=0` → `ge=-1`
- All 87 backend tx tests pass (7 validate + 80 api/service)

### Step R5-2 — Frontend: commit failure → red ⛔ banner with categorized issues ✅

**Files**: `TransactionFormModal.svelte`, `TransactionBulkModal.svelte`
- Added `commitFailed` state flag (reset on open, on draft change, on new commit)
- On `committed: false`: sets `issues = resp.issues` + `commitFailed = true`
- **Commit failure**: RED ⛔ banner (variant="error") with `rolledBackTitle`, then two sections:
  - **Field errors** (index ≥ 0): labeled `issuesHeader`, clickable "Riga N:" in bulk
  - **Balance errors** (index < 0): labeled `balanceIssuesHeader`, no row prefix, with `{@html}` for bold
- **Validate issues**: YELLOW banner (variant="warning"), same two-section layout
- `formError` reserved for HTTP/network errors only
- Banner auto-clears when user edits a draft (`commitFailed = false` in change $effect)

### Step R5-3 — Frontend: restore emoji ⚡ validate button ✅

**Files**: `TransactionFormModal.svelte`, `TransactionBulkModal.svelte`
- Reverted Zap SVG → emoji ⚡ in both footer validate buttons
- Removed unused `Zap` import from both files
- Layout kept: ⚡ button on LEFT side, Cancel+Save on RIGHT (mirrors BulkModal)

### Step R5-3b — i18n: balance error messages with `<strong>` ✅

**Files**: `en.json`, `it.json`, `fr.json`, `es.json`
- `balanceAssetNegative`: `<strong>` around asset name + balance amount
- `balanceCashNegative`: `<strong>` around currency + formatted balance
- New key `balanceIssuesHeader`: "This configuration causes data inconsistencies" (4 locales)

### Step R5-4 — Frontend: row prefix for index=-1 ✅

**File**: `TransactionBulkModal.svelte`
- `jumpToIssue()`: early return when `issue.index < 0` (no row to scroll to)
- Banner: `{#if issue.index >= 0}` → clickable button with "Riga N:"; else plain `<span>` without prefix

### Step R5-5 — Anti-bounce 10s for validate + commit ✅

**Problem**: Clicking validate/commit multiple times without editing sends duplicate network requests.
**Fix**: Three-layer anti-bounce:

1. **Validate scheduler** (`useValidateScheduler.svelte.ts`):
   - Added `draftKey` option + `antiBounceMs` (default 10s)
   - `runValidate()` checks: if `draftKey()` unchanged AND < 10s since last validate → skip
   - Tracks `lastValidatedDraftKey` internally

2. **Commit function** (both modals):
   - Added `lastCommitDraftKey` + `lastCommitAt` state tracking
   - At start of `commit()`: if `lastDraftKey === lastCommitDraftKey` AND < 10s → skip (no-op)
   - Updated in `finally` block after every commit attempt

3. **Wiring**: both modals pass `draftKey: () => lastDraftKey` to the scheduler

### Step R5-6 — Manual test

- Manual test: commit a bad batch → see red ⛔ banner with categorized issues
- Manual test: click commit again without editing → no network request for 10s
- Manual test: click ⚡ validate again without editing → no network request for 10s
- Manual test: edit a field → anti-bounce resets, next click fires immediately

---

## 🐛 Frontend Issues Found (manual E2E 2026-04-30)

### W28 — Balance errors not attributed to the offending row

**Severity**: P1 (misleading)
**Where**: BulkModal banner — balance issues (`index: -1`) shown without "Riga N:" prefix, but the user expects to see WHICH row caused the violation.
**Example**: 3 rows in batch, row 2 is a SELL that causes Bitcoin to go negative → banner shows the error without any row reference. User expects "Riga 2: Le posizioni di Bitcoin vanno in negativo…"
**Root cause**: Backend `BalanceValidationError` is broker-level (`index: -1`). It knows `brokerId` + `assetId` (or `currency`) but not which specific batch row triggered it.
**Proposed fix**: Frontend-side row attribution. When rendering a balance issue with `index < 0`, scan the draft rows for the last match on `brokerId + assetId` (for asset errors) or `brokerId + cash.code` (for cash errors) using the issue's `params`. Show "Riga N:" with the matched row, clickable for scroll. If no match → show without prefix (current behavior).
**Scope**: BulkModal only (FormModal has a single row, no prefix needed).

### W29 — Server-driven type rules + auto-sign for quantity/cash

**Severity**: P2 (UX improvement + future-proofing)
**Where**: Frontend type rules are hardcoded in `transactionTypeRules.ts`. Backend already exposes `GET /api/v1/transactions/types` with full metadata per type.
**Current state**: The endpoint returns `allowed_quantity_sign` and `allowed_cash_sign` (`"+"`, `"-"`, `"0"`, `"+/-"`) plus `asset_mode`, `requires_cash`, `requires_link`, `event_compatible`. Frontend duplicates these rules locally.
**Problem**: User must enter negative numbers for SELL quantity and BUY cash — counter-intuitive. Rules are duplicated between backend response and frontend `transactionTypeRules.ts`.

**Proposed change — 2 parts**:

#### W29a — Auto-sign negation (UX)
When a type has `allowed_quantity_sign: "-"` or `allowed_cash_sign: "-"`, the frontend should:
1. Accept **positive** input from the user (more intuitive)
2. Auto-negate the value before sending to the backend (`collectCreate()` / `collectUpdate()`)
3. Show a visual hint (e.g. "−" prefix or label like "Amount to pay") so the user knows the value will be negated
4. For `"+/-"` signs, no auto-negation — user enters the sign explicitly (as today)
5. For `"0"`, force `quantity = 0` or hide the field (as today)

#### W29b — Server-driven rules (architecture)
Replace `transactionTypeRules.ts` hardcoded rules with data from `GET /transactions/types`:
1. Fetch types on app init (or lazy on first modal open), cache in a store
2. Map `asset_mode` → field visibility (`REQUIRED` = show + required, `OPTIONAL` = show, `FORBIDDEN` = hide)
3. Map `requires_cash` → cash field visibility
4. Map `allowed_quantity_sign` / `allowed_cash_sign` → sign behavior (positive-only input + auto-negate, or free sign)
5. Update `icon` field to return the correct asset path (currently emoji, should be `/icons/transactions/sell.png` etc.)
6. `isDraftReadyForValidation()` derives from the fetched rules instead of local switch/case

**Benefits**: Single source of truth in backend. Adding a new transaction type only requires backend changes — frontend auto-adapts.

**Estimated effort**: ~3–4 h (W29a auto-sign) + ~2 h (W29b server-driven rules) = ~5–6 h total.
**Prerequisite**: W28 (row attribution) should be done first as it's a quick win.

**→ Full implementation plan**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md)
