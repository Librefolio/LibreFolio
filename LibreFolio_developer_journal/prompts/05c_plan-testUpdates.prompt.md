# Plan: Test Updates for Plans 05 + 05b Combined

**Context**: This plan consolidates all test updates needed for both the main datamodel refactoring (plan 05) and the schema cleanup (plan 05b). By combining test updates, we avoid updating tests twice.

**Execution Order**:
1. Complete Steps 1-11 of Plan 05 ✅ (DONE)
2. Complete Steps 1-11 of Plan 05b ⏳ (IN PROGRESS)
3. **Execute this plan (12)** - Update all tests for both changes
4. Complete Step 12 of Plan 05 (final integration tests)

---

## 🎯 Changes from Plan 05 to Test

### Database Model Changes
- ✅ `Asset` table: Removed `identifier`, `identifier_type`, `valuation_model`, `interest_schedule`
- ✅ `Asset` table: Added `icon_url` field
- ✅ `Asset` table: Added UNIQUE constraint on `display_name`
- ✅ `AssetProviderAssignment` table: Added `identifier`, `identifier_type` fields
- ✅ Removed `ValuationModel` enum entirely

### Schema Changes
- ✅ `FAAssetCreateItem`: Removed identifier fields, added `icon_url`
- ✅ `FAAssetPatchItem`: Added `icon_url`
- ✅ `FAProviderAssignmentItem`: Added `identifier`, `identifier_type` fields
- ✅ `FAAssetPatchItem` now used directly (no wrapper)
- ✅ Provider interfaces: Added `get_icon()` method
- ✅ All providers: Added `identifier_type` parameter to methods

### Service Changes
- ✅ `AssetCRUDService.create_assets_bulk()`: Updated for new Asset structure
- ✅ `AssetCRUDService.patch_assets_bulk()`: New method for bulk PATCH
- ✅ `AssetSourceManager.refresh_assets_from_provider()`: Renamed from `bulk_refresh_metadata`
- ✅ Provider calls: Now pass `identifier_type` to all provider methods

---

## 🎯 Changes from Plan 05b to Test

### Wrapper Classes Removed (16 classes)
- ❌ `FAProvidersResponse` → Use `List[FAProviderInfo]`
- ❌ `FXProvidersResponse` (both duplicates)
- ❌ `FABulkAssignRequest` → Use `List[FAProviderAssignmentItem]`
- ❌ `FABulkRemoveRequest` → Use `List[int]`
- ❌ `FABulkAssetCreateRequest` → Use `List[FAAssetCreateItem]`
- ❌ `FABulkPatchMetadataRequest` → Use `List[FAMetadataPatchItem]`
- ❌ `FXConvertRequest` → Use `List[FXConversionRequest]`
- ❌ `FXBulkUpsertRequest` → Use `List[FXUpsertItem]`
- ❌ `FXBulkDeleteRequest` → Use `List[FXDeleteItem]`
- ❌ `FXCreatePairSourcesRequest` → Use `List[FXPairSourceItem]`
- ❌ `FXDeletePairSourcesRequest` → Use `List[FXDeletePairSourceItem]`
- ❌ `FABulkUpsertRequest` → Use `List[FAUpsert]`
- ❌ `FAPriceBulkDeleteRequest` → Use `List[FAAssetDelete]`
- ❌ `FABulkRefreshRequest` → Use `List[FARefreshItem]`
- ❌ `FAUpsertItem` → Merged into `FAPricePoint`

### DateRangeModel Integration
- ✅ `FXConversionRequest`: Now uses `date_range: DateRangeModel`
- ✅ `FXDeleteItem`: Now uses `date_range: DateRangeModel`
- ✅ `FXDeleteResult`: Now uses `date_range: DateRangeModel`
- ✅ `FXSyncResponse`: Now uses `date_range: DateRangeModel`
- ✅ `FARefreshItem`: Now uses `date_range: DateRangeModel`

### Consolidation
- ✅ `FAUpsertItem` merged into `FAPricePoint` (single class for read/write)

### Standardized Responses
- ✅ All bulk responses now extend `BaseBulkResponse[TResult]`
- ✅ `failed_count` is now a computed property (not stored)
- ✅ Consistent `errors: List[str]` field across all responses

---

## 📋 Test Update Steps

### Step 1: Update Fixture and Setup Code

**Files**: `backend/test_scripts/conftest.py`, fixture files

**Changes**:

1. **Remove identifier/identifier_type from Asset creation**:
   ```python
   # OLD
   asset = Asset(
       display_name="Apple Inc.",
       identifier="AAPL",
       identifier_type=IdentifierType.TICKER,
       currency="USD",
       valuation_model=ValuationModel.MARKET_PRICE
   )
   
   # NEW
   asset = Asset(
       display_name="Apple Inc.",
       currency="USD",
       asset_type=AssetType.STOCK,
       icon_url=None  # Optional
   )
   ```

2. **Create AssetProviderAssignment with identifier**:
   ```python
   # NEW: Create provider assignment separately
   assignment = AssetProviderAssignment(
       asset_id=asset.id,
       provider_code="yfinance",
       identifier="AAPL",
       identifier_type=IdentifierType.TICKER,
       provider_params=None,
       fetch_interval=1440
   )
   session.add(assignment)
   await session.flush()
   ```

3. **Remove ValuationModel references**:
   ```python
   # OLD
   from backend.app.db.models import ValuationModel
   
   # NEW
   # Remove import, enum no longer exists
   ```

4. **Ensure display_name uniqueness**:
   ```python
   # Add unique suffixes to test assets if needed
   asset1 = Asset(display_name="Test Asset 1", ...)
   asset2 = Asset(display_name="Test Asset 2", ...)  # Not duplicate
   ```

---

### Step 2: Update Asset CRUD Tests

**Files**: `backend/test_scripts/test_api/test_assets_crud.py`

**Changes**:

1. **Update POST /assets request format**:
   ```python
   # OLD
   request = FABulkAssetCreateRequest(assets=[
       FAAssetCreateItem(
           display_name="Apple Inc.",
           identifier="AAPL",
           identifier_type="TICKER",
           currency="USD",
           asset_type="STOCK"
       )
   ])
   response = client.post("/api/v1/assets", json=request.model_dump())
   
   # NEW
   assets = [
       FAAssetCreateItem(
           display_name="Apple Inc.",
           currency="USD",
           asset_type=AssetType.STOCK,
           icon_url="https://example.com/aapl.png"  # Optional
       )
   ]
   response = client.post("/api/v1/assets", json=[a.model_dump() for a in assets])
   ```

2. **Update PATCH /assets request format**:
   ```python
   # NEW (no wrapper)
   patches = [
       FAAssetPatchItem(
           asset_id=1,
           display_name="Updated Name",
           icon_url="https://new-icon.png"
       )
   ]
   response = client.patch("/api/v1/assets", json=[p.model_dump() for p in patches])
   ```

3. **Update response assertions**:
   ```python
   # OLD
   assert response.json()["failed_count"] == 0
   
   # NEW (failed_count is computed, not in JSON)
   response_data = response.json()
   assert len(response_data["results"]) - response_data["success_count"] == 0
   # Or just check success_count
   assert response_data["success_count"] == len(assets)
   ```

4. **Remove identifier from response validation**:
   ```python
   # OLD
   assert asset["identifier"] == "AAPL"
   
   # NEW
   # identifier is not in asset, it's in provider assignment
   ```

---

### Step 3: Update Provider Assignment Tests

**Files**: `backend/test_scripts/test_api/test_provider_assignment.py`

**Changes**:

1. **Update POST /assets/provider request format**:
   ```python
   # OLD
   request = FABulkAssignRequest(assignments=[
       FAProviderAssignmentItem(
           asset_id=1,
           provider_code="yfinance",
           provider_params={}
       )
   ])
   response = client.post("/api/v1/assets/provider", json=request.model_dump())
   
   # NEW
   assignments = [
       FAProviderAssignmentItem(
           asset_id=1,
           provider_code="yfinance",
           identifier="AAPL",
           identifier_type=IdentifierType.TICKER,
           provider_params={},
           fetch_interval=1440
       )
   ]
   response = client.post("/api/v1/assets/provider", json=[a.model_dump() for a in assignments])
   ```

2. **Update DELETE /assets/provider request format**:
   ```python
   # OLD
   request = FABulkRemoveRequest(asset_ids=[1, 2, 3])
   response = client.delete("/api/v1/assets/provider", json=request.model_dump())
   
   # NEW (list of ints directly)
   asset_ids = [1, 2, 3]
   response = client.delete("/api/v1/assets/provider", json=asset_ids)
   ```

3. **Update GET /assets/provider/assignments tests**:
   ```python
   # NEW endpoint, add tests
   response = client.get("/api/v1/assets/provider/assignments?asset_ids=1&asset_ids=2")
   assert response.status_code == 200
   assignments = response.json()  # List[FAProviderAssignmentReadItem]
   assert isinstance(assignments, list)
   assert assignments[0]["identifier"] == "AAPL"
   assert assignments[0]["identifier_type"] == "TICKER"
   ```

---

### Step 4: Update Price Operation Tests

**Files**: `backend/test_scripts/test_api/test_prices.py`

**Changes**:

1. **Update POST /prices request format**:
   ```python
   # OLD
   request = FABulkUpsertRequest(assets=[
       FAUpsert(
           asset_id=1,
           prices=[
               FAUpsertItem(date="2025-01-01", close=100, currency="USD")
           ]
       )
   ])
   response = client.post("/api/v1/prices", json=request.model_dump())
   
   # NEW (no wrapper, FAUpsertItem → FAPricePoint)
   upserts = [
       FAUpsert(
           asset_id=1,
           prices=[
               FAPricePoint(date="2025-01-01", close=100, currency="USD")
           ]
       )
   ]
   response = client.post("/api/v1/prices", json=[u.model_dump() for u in upserts])
   ```

2. **Update DELETE /prices request format**:
   ```python
   # OLD
   request = FAPriceBulkDeleteRequest(assets=[
       FAAssetDelete(
           asset_id=1,
           date_ranges=[{"start": "2025-01-01", "end": "2025-01-31"}]
       )
   ])
   response = client.delete("/api/v1/prices", json=request.model_dump())
   
   # NEW (no wrapper, uses DateRangeModel)
   deletions = [
       FAAssetDelete(
           asset_id=1,
           date_ranges=[DateRangeModel(start="2025-01-01", end="2025-01-31")]
       )
   ]
   response = client.delete("/api/v1/prices", json=[d.model_dump() for d in deletions])
   ```

3. **Update POST /prices/refresh request format**:
   ```python
   # OLD
   request = FABulkRefreshRequest(requests=[
       FARefreshItem(asset_id=1, start_date="2025-01-01", end_date="2025-01-31")
   ])
   response = client.post("/api/v1/prices/refresh", json=request.model_dump())
   
   # NEW (no wrapper, uses DateRangeModel, timeout as query param)
   refresh_items = [
       FARefreshItem(
           asset_id=1,
           date_range=DateRangeModel(start="2025-01-01", end="2025-01-31")
       )
   ]
   response = client.post(
       "/api/v1/prices/refresh?timeout=60",
       json=[r.model_dump() for r in refresh_items]
   )
   ```

---

### Step 5: Update FX Operation Tests

**Files**: `backend/test_scripts/test_api/test_fx_api.py`

**Changes**:

1. **Update POST /fx/convert request format**:
   ```python
   # OLD
   request = FXConvertRequest(conversions=[
       FXConversionRequest(
           amount=100,
           from_currency="USD",
           to_currency="EUR",
           start_date="2025-01-01",
           end_date="2025-01-31"
       )
   ])
   response = client.post("/api/v1/fx/convert", json=request.model_dump())
   
   # NEW (no wrapper, uses DateRangeModel)
   conversions = [
       FXConversionRequest(
           amount=100,
           from_currency="USD",
           to_currency="EUR",
           date_range=DateRangeModel(start="2025-01-01", end="2025-01-31")
       )
   ]
   response = client.post("/api/v1/fx/convert", json=[c.model_dump(by_alias=True) for c in conversions])
   ```

2. **Update POST /fx/rates request format**:
   ```python
   # OLD
   request = FXBulkUpsertRequest(rates=[
       FXUpsertItem(date="2025-01-01", base="USD", quote="EUR", rate=0.85)
   ])
   response = client.post("/api/v1/fx/rates", json=request.model_dump())
   
   # NEW (no wrapper)
   rates = [
       FXUpsertItem(date="2025-01-01", base="USD", quote="EUR", rate=0.85)
   ]
   response = client.post("/api/v1/fx/rates", json=[r.model_dump(by_alias=True) for r in rates])
   ```

3. **Update DELETE /fx/rates request format**:
   ```python
   # OLD
   request = FXBulkDeleteRequest(deletions=[
       FXDeleteItem(
           from_currency="USD",
           to_currency="EUR",
           start_date="2025-01-01",
           end_date="2025-01-31"
       )
   ])
   response = client.delete("/api/v1/fx/rates", json=request.model_dump())
   
   # NEW (no wrapper, uses DateRangeModel)
   deletions = [
       FXDeleteItem(
           from_currency="USD",
           to_currency="EUR",
           date_range=DateRangeModel(start="2025-01-01", end="2025-01-31")
       )
   ]
   response = client.delete("/api/v1/fx/rates", json=[d.model_dump(by_alias=True) for d in deletions])
   ```

4. **Update pair sources tests**:
   ```python
   # OLD
   request = FXCreatePairSourcesRequest(sources=[...])
   
   # NEW (no wrapper)
   sources = [FXPairSourceItem(...)]
   response = client.post("/api/v1/fx/pair-sources", json=[s.model_dump() for s in sources])
   ```

---

### Step 6: Update Provider List Tests

**Files**: `backend/test_scripts/test_api/test_provider_list.py`

**Changes**:

1. **Update GET /assets/provider response format**:
   ```python
   # OLD
   response = client.get("/api/v1/assets/provider")
   data = FAProvidersResponse(**response.json())
   assert len(data.providers) > 0
   
   # NEW (direct list)
   response = client.get("/api/v1/assets/provider")
   providers = response.json()  # List[FAProviderInfo]
   assert isinstance(providers, list)
   assert len(providers) > 0
   # Check icon_url field
   assert "icon_url" in providers[0]
   ```

2. **Update GET /fx/providers response format**:
   ```python
   # OLD
   response = client.get("/api/v1/fx/providers")
   data = FXProvidersResponse(**response.json())
   
   # NEW (direct list)
   response = client.get("/api/v1/fx/providers")
   providers = response.json()  # List[FXProviderInfo]
   assert isinstance(providers, list)
   # Check icon_url field
   assert "icon_url" in providers[0]
   ```

---

### Step 7: Update Scheduled Investment Tests

**Files**: `backend/test_scripts/test_service/test_scheduled_investment.py`

**Changes**:

1. **Update _transaction_override format**:
   ```python
   # OLD
   provider_params = {
       "schedule": [...],
       "_transaction_override": [
           {
               "type": "BUY",
               "quantity": 1,
               "price": "10000",
               "identifier": "...",  # REMOVE
               "valuation_model": "..."  # REMOVE
           }
       ]
   }
   
   # NEW
   provider_params = {
       "schedule": [...],
       "_transaction_override": [
           {
               "type": "BUY",
               "quantity": 1,
               "price": "10000",
               "trade_date": "2025-01-01",
               "settlement_date": "2025-01-01",
               "currency": "EUR",
               "asset_id": 1,
               "broker_id": 1
           }
       ]
   }
   ```

2. **Update provider calls with identifier_type**:
   ```python
   # OLD
   result = await provider.get_current_value(
       identifier="1",
       provider_params=provider_params
   )
   
   # NEW
   result = await provider.get_current_value(
       identifier="1",
       identifier_type=IdentifierType.UUID,
       provider_params=provider_params
   )
   ```

---

### Step 8: Update Metadata/Refresh Tests

**Files**: `backend/test_scripts/test_api/test_assets_metadata.py`

**Changes**:

1. **Update PATCH /metadata request format**:
   ```python
   # OLD
   request = FABulkPatchMetadataRequest(assets=[
       FAMetadataPatchItem(asset_id=1, patch={"sector": "Technology"})
   ])
   response = client.patch("/api/v1/metadata", json=request.model_dump())
   
   # NEW (no wrapper)
   patches = [
       FAMetadataPatchItem(asset_id=1, patch={"sector": "Technology"})
   ]
   response = client.patch("/api/v1/metadata", json=[p.model_dump() for p in patches])
   ```

2. **Update POST /assets/provider/refresh tests**:
   ```python
   # OLD
   response = client.get("/api/v1/metadata/refresh?asset_ids=1&asset_ids=2")
   
   # NEW (changed to POST, different path)
   response = client.post("/api/v1/assets/provider/refresh?asset_ids=1&asset_ids=2")
   assert response.status_code == 200
   data = response.json()
   # Check for fields_detail in results
   assert "fields_detail" in data["results"][0]
   ```

---

### Step 9: Update Response Validation

**All test files**

**Changes**:

1. **Update BaseBulkResponse validation**:
   ```python
   # OLD
   assert response_data["failed_count"] == 0
   
   # NEW (failed_count not in JSON, it's computed)
   assert response_data["success_count"] == expected_count
   # Or validate via results
   failed = len([r for r in response_data["results"] if not r["success"]])
   assert failed == 0
   ```

2. **Check for errors field**:
   ```python
   # NEW (all responses have errors field)
   assert "errors" in response_data
   assert isinstance(response_data["errors"], list)
   ```

3. **Validate operation-specific fields**:
   ```python
   # For upsert operations
   assert "inserted_count" in response_data
   assert "updated_count" in response_data
   
   # For delete operations
   assert "deleted_count" in response_data or "total_deleted" in response_data
   ```

---

### Step 10: Update Mock Data and Factories

**Files**: `backend/test_scripts/factories.py`, mock data files

**Changes**:

1. **Update Asset factory**:
   ```python
   class AssetFactory:
       @staticmethod
       def create(
           display_name: str = "Test Asset",
           currency: str = "USD",
           asset_type: AssetType = AssetType.STOCK,
           icon_url: Optional[str] = None
       ) -> Asset:
           return Asset(
               display_name=display_name,
               currency=currency,
               asset_type=asset_type,
               icon_url=icon_url,
               active=True
           )
   ```

2. **Add AssetProviderAssignment factory**:
   ```python
   class ProviderAssignmentFactory:
       @staticmethod
       def create(
           asset_id: int,
           provider_code: str = "yfinance",
           identifier: str = "AAPL",
           identifier_type: IdentifierType = IdentifierType.TICKER
       ) -> AssetProviderAssignment:
           return AssetProviderAssignment(
               asset_id=asset_id,
               provider_code=provider_code,
               identifier=identifier,
               identifier_type=identifier_type,
               provider_params=None,
               fetch_interval=1440
           )
   ```

---

## 📊 Test Execution Order

### Phase 1: Unit Tests (No API calls)
1. ✅ Update model tests (Asset, AssetProviderAssignment)
2. ✅ Update schema validation tests
3. ✅ Update utility function tests

### Phase 2: Service Layer Tests
1. ✅ Update AssetCRUDService tests
2. ✅ Update AssetSourceManager tests
3. ✅ Update provider tests (yfinance, scheduled_investment)
4. ✅ Update FX service tests

### Phase 3: API Integration Tests
1. ✅ Update asset CRUD API tests
2. ✅ Update provider assignment API tests
3. ✅ Update price operation API tests
4. ✅ Update FX operation API tests
5. ✅ Update metadata/refresh API tests

### Phase 4: End-to-End Tests
1. ✅ Update complete workflow tests
2. ✅ Update integration tests

---

## 🔍 Validation Checklist

After updating all tests, verify:

- [ ] All fixtures create Assets without identifier/identifier_type/valuation_model
- [ ] All provider assignments include identifier/identifier_type
- [ ] No wrapper classes used in test requests (FABulkAssignRequest, etc.)
- [ ] All date range operations use DateRangeModel
- [ ] FAPricePoint used instead of FAUpsertItem
- [ ] All response validations check BaseBulkResponse structure
- [ ] failed_count validated as computed (not in JSON)
- [ ] icon_url included in asset creation/validation where relevant
- [ ] All provider method calls include identifier_type parameter
- [ ] _transaction_override in scheduled investment tests updated
- [ ] display_name uniqueness respected in all test data
- [ ] All imports updated (removed ValuationModel, wrapper classes)

---

## 🚀 Summary

**Total Test Files to Update**: ~25-30 files

**Major Changes**:
- Remove all wrapper class instantiation (16 classes)
- Use DateRangeModel for date ranges (5 schema classes)
- Update Asset creation (remove identifier fields)
- Add AssetProviderAssignment creation (new pattern)
- Update all request/response formats (no wrappers)
- Validate BaseBulkResponse structure
- Update provider method calls (identifier_type)

**Execution Time Estimate**: 3-4 hours

**Benefits**:
- ✅ Tests aligned with new architecture
- ✅ Cleaner test code (no wrappers)
- ✅ Consistent patterns across all tests
- ✅ Better validation coverage

