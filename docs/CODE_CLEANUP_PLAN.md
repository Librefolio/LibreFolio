# 🧹 Code Cleanup Plan - Rimozione Single Endpoints & Refactor Pydantic

**Data**: 26 Novembre 2025  
**Prerequisito**: Test E2E manuale completato  
**Tempo stimato totale**: 5-7 ore

---

## 🎯 Obiettivi

1. **Rimuovere tutti gli endpoint single** (mantieni solo bulk)
2. **Refactorare service layer**: dict → Pydantic models
3. **Mantenere 100% backward compatibility** per bulk API
4. **Validare con test suite esistente** (nessun test deve fallire)

---

## Task A: Remove Single Endpoints (2-3 ore)

### 📋 Checklist Endpoint da Rimuovere

**File**: `backend/app/api/v1/assets.py`

#### 1. ❌ `POST /assets/{asset_id}/provider`
```python
# Line ~280-320 (circa)
@router.post("/{asset_id}/provider", response_model=FAProviderAssignmentResult)
async def assign_provider_single(...)
```
**Replacement**: `POST /assets/provider/bulk` con `assignments: [{ asset_id: X, ... }]`

---

#### 2. ❌ `DELETE /assets/{asset_id}/provider`
```python
# Line ~330-370 (circa)
@router.delete("/{asset_id}/provider", response_model=FAProviderRemovalResult)
async def remove_provider_single(...)
```
**Replacement**: `DELETE /assets/provider/bulk` con `asset_ids: [X]`

---

#### 3. ❌ `POST /assets/{asset_id}/metadata/refresh`
```python
# Line ~696-750 (circa)
@router.post("/{asset_id}/metadata/refresh", response_model=FAMetadataRefreshResult)
async def refresh_metadata_single(...)
```
**Replacement**: `POST /assets/metadata/refresh/bulk` con `asset_ids: [X]`

---

#### 4. ❌ `POST /assets/{asset_id}/prices/refresh`
```python
# Line ~780-820 (circa)
@router.post("/{asset_id}/prices/refresh", response_model=FAPriceRefreshResult)
async def refresh_prices_single(...)
```
**Replacement**: `POST /assets/prices/refresh/bulk` con `refresh_requests: [{ asset_id: X, ... }]`

---

#### 5. ❌ `DELETE /assets/{asset_id}/prices`
```python
# Line ~750-780 (circa)
@router.delete("/{asset_id}/prices", response_model=FAPriceDeleteResponse)
async def delete_prices_single(...)
```
**Replacement**: `DELETE /assets/prices/bulk` con `deletions: [{ asset_id: X, ... }]`

---

### 🔧 Step-by-Step Execution

#### Step 1: search all single endpoints
Verificare che tutti gli endpoint single siano stati identificati, e che per ciascuno esista un equivalente bulk.

#### Step 2: Remove Endpoints
Per ogni endpoint single:
1. Trova la funzione in `backend/app/api/v1/assets.py`, `backend/app/api/v1/fx.py` se FX
2. Verifica che il bulk equivalent esista
3. Rimuovi l'intera funzione (decorator + body)

#### Step 3: Update Tests
```bash
# Trova test che usano endpoint single
grep -r "/{asset_id}/provider" backend/test_scripts/test_api/
grep -r "/{asset_id}/metadata/refresh" backend/test_scripts/test_api/
grep -r "/{asset_id}/prices" backend/test_scripts/test_api/

# Opzioni:
# A) Rimuovi test per single endpoint (se bulk test già esistono)
# B) Converti test single → bulk con array di 1 item
```

#### Step 4: Validate
```bash
# Run all API tests
./test_runner.py api all

# Verify no errors
# Expected: All tests pass (some might be skipped if removed)
```

#### Step 5: Update Documentation
```bash
# File: docs/api-development-guide.md
# - Rimuovi esempi single endpoint
# - Aggiungi sezione "Migration Guide: Single → Bulk"
# - Esempi curl per bulk con 1 item
```

**Migration Guide Example**:
````markdown
### Migration: Single → Bulk Endpoints

**Before** (REMOVED):
```bash
POST /api/v1/assets/1/provider
{
  "provider_code": "yfinance",
  "provider_params": null
}
```

**After** (USE THIS):
```bash
POST /api/v1/assets/provider/bulk
{
  "assignments": [{
    "asset_id": 1,
    "provider_code": "yfinance",
    "provider_params": null
  }]
}
```
````

---

## Task B: Refactor dict → Pydantic (3-4 ore)

### 🎯 Filosofia del Refactor

**Obiettivo**: Service layer ritorna Pydantic models, non dict

**Benefits**:
- ✅ Type safety completa (mypy)
- ✅ Validation centralizzata
- ✅ No conversion overhead in API
- ✅ Easier mocking in tests

**Impatto**: 
Prima di cambiare la firma di ogni metodo, cercare tutte le usage, segnarsele, e dopo la modifica della firma, andare in quelle usage e aggiornare il codice per usare i modelli Pydantic.
---

### 📋 Files da Refactorare (in ordine)

---

### 1. `backend/app/services/asset_source.py`

**Funzioni da modificare** (8 funzioni):

#### 1.1 `bulk_assign_providers()`
**Before**:
```python
def bulk_assign_providers(...) -> dict:
    results = []
    for assignment in assignments:
        results.append({
            "asset_id": assignment.asset_id,
            "success": True,
            "message": "Provider assigned",
            "metadata_updated": True,
            "metadata_changes": [...]
        })
    return {"results": results, "success_count": len(results)}
```

**After**:
```python
from backend.app.schemas.assets import (
    FAProviderAssignmentResult,
    FABulkProviderAssignmentResponse,
    MetadataChange
)

def bulk_assign_providers(...) -> FABulkProviderAssignmentResponse:
    results = []
    for assignment in assignments:
        changes = [
            MetadataChange(field="...", old=..., new=...)
        ] if metadata_updated else []
        
        results.append(FAProviderAssignmentResult(
            asset_id=assignment.asset_id,
            success=True,
            message="Provider assigned",
            metadata_updated=True,
            metadata_changes=changes
        ))
    
    return FABulkProviderAssignmentResponse(
        results=results,
        success_count=len(results)
    )
```

---

#### 1.2 `bulk_remove_providers()`
**Before**:
```python
def bulk_remove_providers(...) -> dict:
    results = []
    for asset_id in asset_ids:
        results.append({
            "asset_id": asset_id,
            "success": True,
            "message": "Provider removed"
        })
    return {"results": results, "success_count": len(results)}
```

**After**:
```python
from backend.app.schemas.assets import (
    FAProviderRemovalResult,
    FABulkProviderRemovalResponse
)

def bulk_remove_providers(...) -> FABulkProviderRemovalResponse:
    results = []
    for asset_id in asset_ids:
        results.append(FAProviderRemovalResult(
            asset_id=asset_id,
            success=True,
            message="Provider removed"
        ))
    
    return FABulkProviderRemovalResponse(
        results=results,
        success_count=len(results)
    )
```

---

#### 1.3 `bulk_upsert_prices()`
**Before**:
```python
def bulk_upsert_prices(...) -> dict:
    results = []
    for upsert in upserts:
        results.append({
            "asset_id": upsert.asset_id,
            "success": True,
            "inserted": 10,
            "updated": 5,
            "message": "Prices upserted"
        })
    return {"results": results, "success_count": len(results)}
```

**After**:
```python
from backend.app.schemas.prices import (
    FAPriceUpsertResult,
    FABulkPriceUpsertResponse
)

def bulk_upsert_prices(...) -> FABulkPriceUpsertResponse:
    results = []
    for upsert in upserts:
        results.append(FAPriceUpsertResult(
            asset_id=upsert.asset_id,
            success=True,
            inserted=10,
            updated=5,
            message="Prices upserted"
        ))
    
    return FABulkPriceUpsertResponse(
        results=results,
        success_count=len(results)
    )
```

---

#### 1.4 `bulk_delete_prices()`
**Before**:
```python
def bulk_delete_prices(...) -> dict:
    results = []
    for deletion in deletions:
        results.append({
            "asset_id": deletion.asset_id,
            "deleted": 50,
            "message": "Deleted prices in 2 range(s)"
        })
    return {
        "deleted_count": 50,
        "results": results
    }
```

**After**:
```python
from backend.app.schemas.prices import (
    FAPriceDeleteResult,
    FABulkDeletePricesResponse
)

def bulk_delete_prices(...) -> FABulkDeletePricesResponse:
    results = []
    total_deleted = 0
    
    for deletion in deletions:
        deleted = 50  # actual deletion count
        total_deleted += deleted
        
        results.append(FAPriceDeleteResult(
            asset_id=deletion.asset_id,
            deleted=deleted,
            message="Deleted prices in 2 range(s)"
        ))
    
    return FABulkDeletePricesResponse(
        deleted_count=total_deleted,
        results=results
    )
```

---

#### 1.5 `bulk_refresh_prices()`
**Before**:
```python
def bulk_refresh_prices(...) -> dict:
    results = []
    for request in requests:
        results.append({
            "asset_id": request.asset_id,
            "success": True,
            "inserted": 5,
            "updated": 3,
            "message": "Prices refreshed"
        })
    return {
        "results": results,
        "success_count": len(results),
        "error_count": 0
    }
```

**After**:
```python
from backend.app.schemas.refresh import (
    FAPriceRefreshResult,
    FABulkPriceRefreshResponse
)

def bulk_refresh_prices(...) -> FABulkPriceRefreshResponse:
    results = []
    error_count = 0
    
    for request in requests:
        results.append(FAPriceRefreshResult(
            asset_id=request.asset_id,
            success=True,
            inserted=5,
            updated=3,
            message="Prices refreshed"
        ))
    
    return FABulkPriceRefreshResponse(
        results=results,
        success_count=len([r for r in results if r.success]),
        error_count=error_count
    )
```

---

### 2. `backend/app/services/asset_metadata.py`

**Funzioni da modificare** (2 funzioni):

#### 2.1 `apply_partial_update()`
**Before**:
```python
def apply_partial_update(...) -> dict:
    changes = []
    # ... logic ...
    return {
        "asset_id": asset_id,
        "success": True,
        "changes": [
            {"field": "...", "old": ..., "new": ...}
        ]
    }
```

**After**:
```python
from backend.app.schemas.assets import (
    FAMetadataPatchResult,
    MetadataChange
)

def apply_partial_update(...) -> FAMetadataPatchResult:
    changes = []
    # ... logic ...
    changes.append(MetadataChange(
        field="geographic_area",
        old=None,
        new={"USA": "0.7000"}
    ))
    
    return FAMetadataPatchResult(
        asset_id=asset_id,
        success=True,
        changes=changes
    )
```

---

#### 2.2 `merge_provider_metadata()`
**Before**:
```python
def merge_provider_metadata(...) -> tuple[ClassificationParamsModel | None, list[dict]]:
    changes = []
    # ... logic ...
    return (merged_params, [
        {"field": "...", "old": ..., "new": ...}
    ])
```

**After**:
```python
from backend.app.schemas.assets import (
    ClassificationParamsModel,
    MetadataChange
)

def merge_provider_metadata(...) -> tuple[ClassificationParamsModel | None, list[MetadataChange]]:
    changes = []
    # ... logic ...
    changes.append(MetadataChange(
        field="investment_type",
        old=None,
        new="stock"
    ))
    
    return (merged_params, changes)
```

---

### 3. `backend/app/services/asset_crud.py`

**Funzioni da modificare** (2 funzioni):

#### 3.1 `bulk_create_assets()`
**Before**:
```python
def bulk_create_assets(...) -> dict:
    results = []
    for create_request in create_requests:
        results.append({
            "asset_id": new_asset.id,
            "success": True,
            "message": "Asset created successfully"
        })
    return {
        "results": results,
        "success_count": len(results)
    }
```

**After**:
```python
from backend.app.schemas.assets import (
    FAAssetCreationResult,
    FABulkAssetCreationResponse
)

def bulk_create_assets(...) -> FABulkAssetCreationResponse:
    results = []
    for create_request in create_requests:
        results.append(FAAssetCreationResult(
            asset_id=new_asset.id,
            success=True,
            message="Asset created successfully"
        ))
    
    return FABulkAssetCreationResponse(
        results=results,
        success_count=len(results)
    )
```

---

#### 3.2 `bulk_delete_assets()`
**Before**:
```python
def bulk_delete_assets(...) -> dict:
    results = []
    for asset_id in asset_ids:
        results.append({
            "asset_id": asset_id,
            "success": True,
            "message": "Asset deleted"
        })
    return {
        "results": results,
        "success_count": len(results)
    }
```

**After**:
```python
from backend.app.schemas.assets import (
    FAAssetDeletionResult,
    FABulkAssetDeletionResponse
)

def bulk_delete_assets(...) -> FABulkAssetDeletionResponse:
    results = []
    for asset_id in asset_ids:
        results.append(FAAssetDeletionResult(
            asset_id=asset_id,
            success=True,
            message="Asset deleted"
        ))
    
    return FABulkAssetDeletionResponse(
        results=results,
        success_count=len(results)
    )
```

---

### 4. `backend/app/services/fx.py`

**Funzioni da modificare** (4 funzioni):

#### 4.1 `ensure_rates_multi_source()`
**Before**:
```python
def ensure_rates_multi_source(...) -> dict:
    # ... logic ...
    return {
        "total_changed": 50,
        "currencies_synced": ["USD", "GBP"]
    }
```

**After**:
```python
from backend.app.schemas.fx import FXSyncResponse

def ensure_rates_multi_source(...) -> FXSyncResponse:
    # ... logic ...
    return FXSyncResponse(
        synced=50,
        date_range=(start_date, end_date),
        currencies=["USD", "GBP"]
    )
```

---

#### 4.2 `bulk_upsert_rates()`
**Before**:
```python
def bulk_upsert_rates(...) -> dict:
    results = []
    for upsert in upserts:
        results.append({
            "success": True,
            "inserted": 1,
            "updated": 0,
            "message": "Rate upserted"
        })
    return {
        "results": results,
        "success_count": len(results)
    }
```

**After**:
```python
from backend.app.schemas.fx import (
    FXRateUpsertResult,
    FXRateUpsertResponse
)

def bulk_upsert_rates(...) -> FXRateUpsertResponse:
    results = []
    for upsert in upserts:
        results.append(FXRateUpsertResult(
            success=True,
            inserted=1,
            updated=0,
            message="Rate upserted"
        ))
    
    return FXRateUpsertResponse(
        results=results,
        success_count=len(results)
    )
```

---

#### 4.3 `bulk_delete_rates()`
**Before**:
```python
def bulk_delete_rates(...) -> dict:
    results = []
    for deletion in deletions:
        results.append({
            "success": True,
            "deleted": 10,
            "message": "Rates deleted"
        })
    return {
        "results": results,
        "total_deleted": 10
    }
```

**After**:
```python
from backend.app.schemas.fx import (
    FXRateDeleteResult,
    FXRateDeleteResponse
)

def bulk_delete_rates(...) -> FXRateDeleteResponse:
    results = []
    total = 0
    
    for deletion in deletions:
        deleted = 10
        total += deleted
        
        results.append(FXRateDeleteResult(
            success=True,
            deleted=deleted,
            message="Rates deleted"
        ))
    
    return FXRateDeleteResponse(
        results=results,
        total_deleted=total
    )
```

---

#### 4.4 `convert_bulk()`
**Before**:
```python
def convert_bulk(...) -> dict:
    results = []
    errors = []
    for conversion in conversions:
        results.append(converted_amount)  # or None
        if error:
            errors.append(error_message)
    return {
        "results": results,
        "errors": errors
    }
```

**After**:
```python
from backend.app.schemas.fx import FXBulkConversionResponse

def convert_bulk(...) -> FXBulkConversionResponse:
    results = []
    errors = []
    
    for conversion in conversions:
        results.append(converted_amount)  # Decimal or None
        if error:
            errors.append(error_message)
    
    return FXBulkConversionResponse(
        results=results,
        errors=errors
    )
```

---

### 🧪 Testing Strategy

#### Step 1: Refactor One Function at a Time
```bash
# Esempio: bulk_assign_providers()
# 1. Modifica signature e return type
# 2. Modifica body per costruire Pydantic model
# 3. Run tests
./test_runner.py services asset-source

# Se pass → continue
# Se fail → debug and fix
```

#### Step 2: Update API Endpoint (remove conversion)
**Before**:
```python
# api/v1/assets.py
result = bulk_assign_providers(...)  # dict
return FABulkProviderAssignmentResponse(**result)  # wrap dict
```

**After**:
```python
# api/v1/assets.py
return bulk_assign_providers(...)  # già Pydantic!
```

#### Step 3: Run Full Test Suite
```bash
./test_runner.py --coverage all

# Expected:
# - All tests pass
# - Coverage ~62% (unchanged)
# - No breaking changes
```

#### Step 4: Check Type Hints (mypy)
```bash
pipenv run mypy backend/app/services/asset_source.py
pipenv run mypy backend/app/services/asset_metadata.py
pipenv run mypy backend/app/services/asset_crud.py
pipenv run mypy backend/app/services/fx.py

# Expected: No type errors
```

---

### 📝 Checklist per File

#### `backend/app/services/asset_source.py`
- [ ] `bulk_assign_providers()` → `FABulkProviderAssignmentResponse`
- [ ] `bulk_remove_providers()` → `FABulkProviderRemovalResponse`
- [ ] `bulk_upsert_prices()` → `FABulkPriceUpsertResponse`
- [ ] `bulk_delete_prices()` → `FABulkDeletePricesResponse`
- [ ] `bulk_refresh_prices()` → `FABulkPriceRefreshResponse`
- [ ] Tests pass: `./test_runner.py services asset-source`

#### `backend/app/services/asset_metadata.py`
- [ ] `apply_partial_update()` → `FAMetadataPatchResult`
- [ ] `merge_provider_metadata()` → `tuple[ClassificationParamsModel, list[MetadataChange]]`
- [ ] Tests pass: `./test_runner.py services asset-metadata`

#### `backend/app/services/asset_crud.py`
- [ ] `bulk_create_assets()` → `FABulkAssetCreationResponse`
- [ ] `bulk_delete_assets()` → `FABulkAssetDeletionResponse`
- [ ] Tests pass: `./test_runner.py services asset-crud`

#### `backend/app/services/fx.py`
- [ ] `ensure_rates_multi_source()` → `FXSyncResponse`
- [ ] `bulk_upsert_rates()` → `FXRateUpsertResponse`
- [ ] `bulk_delete_rates()` → `FXRateDeleteResponse`
- [ ] `convert_bulk()` → `FXBulkConversionResponse`
- [ ] Tests pass: `./test_runner.py services fx`

#### `backend/app/api/v1/assets.py`
- [ ] Remove `**dict` wrapping in all endpoints
- [ ] Direct return Pydantic from service
- [ ] Tests pass: `./test_runner.py api assets`

#### `backend/app/api/v1/fx.py`
- [ ] Remove `**dict` wrapping in all endpoints
- [ ] Direct return Pydantic from service
- [ ] Tests pass: `./test_runner.py api fx`

---

## ✅ Final Validation

### Checklist Before Commit
- [ ] All tests pass: `./test_runner.py all`
- [ ] Coverage unchanged (~62%): `./test_runner.py --coverage all`
- [ ] No mypy errors: `pipenv run mypy backend/app/`
- [ ] Single endpoints removed (5 endpoints)
- [ ] All service functions return Pydantic (12 functions)
- [ ] API endpoints use direct Pydantic return
- [ ] Documentation updated (`docs/api-development-guide.md`)
- [ ] Git commit with clear message

### Git Commit Messages
```bash
# Task A
git add backend/app/api/v1/assets.py backend/test_scripts/test_api/
git commit -m "refactor(api): Remove single endpoints, keep bulk-only

- Removed 5 single endpoints (provider, metadata, prices)
- All operations now via bulk endpoints
- Updated tests to use bulk patterns
- Migration guide in docs/api-development-guide.md"

# Task B
git add backend/app/services/ backend/app/api/
git commit -m "refactor(services): Return Pydantic models instead of dict

- asset_source.py: 5 functions return Pydantic
- asset_metadata.py: 2 functions return Pydantic
- asset_crud.py: 2 functions return Pydantic
- fx.py: 4 functions return Pydantic
- API endpoints: removed dict wrapping
- Type safety improved (mypy passes)
- All tests pass, coverage unchanged"
```

---

## 🎯 Success Criteria

**Definizione di "Done"**:
1. ✅ 5 single endpoints rimossi
2. ✅ 12 service functions ritornano Pydantic
3. ✅ Tutti i test passano (100% green)
4. ✅ Coverage invariato (~62%)
5. ✅ mypy passa senza errori
6. ✅ Documentazione aggiornata
7. ✅ Git commits puliti e descrittivi

**Dopo questo cleanup**:
- ✅ Codebase più pulita e type-safe
- ✅ Pronto per sviluppo nuove feature
- ✅ Testing più facile (Pydantic mocking)
- ✅ API più consistente (bulk-only)

---

*Questo piano è pronto per essere eseguito immediatamente dopo il test E2E manuale.*

