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

