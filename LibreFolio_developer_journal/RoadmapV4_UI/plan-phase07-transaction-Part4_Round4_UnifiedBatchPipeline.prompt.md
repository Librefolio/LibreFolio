# Plan — Phase 7 · Part 5 — Unified Batch Pipeline

**Date**: 2026-04-29
**Status**: ⏳ IN PROGRESS
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

- [ ] `TXMixedBatch` + `TXBatchResponse` schemas created
- [ ] `_parse_lenient` helper handles per-row validation + `multipleBusinessRuleErrors`
- [ ] `execute_batch` unified pipeline (parse → access → apply → balance → commit/rollback)
- [ ] `POST /validate` → `execute_batch(commit=False)`
- [ ] `POST /commit` → `execute_batch(commit=True)`
- [ ] Old 3 endpoints removed
- [ ] `promote_transfer` migrated
- [ ] `broker_service` migrated
- [ ] Old schemas/methods deleted
- [ ] Frontend types regenerated
- [ ] FormModal migrated
- [ ] BulkModal migrated
- [ ] CashTransactionModal migrated
- [ ] BulkDeleteLinkedPairModal migrated
- [ ] Backend tests pass
- [ ] Frontend 422 fallback → safety net
- [ ] Schema+balance coexistence test (W21 proof)
- [ ] `./dev.py api sync` clean
- [ ] i18n audit clean

