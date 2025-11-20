# Asset CRUD & Code Cleanup - Implementation Checklist

**Created**: November 20, 2025  
**Status**: Ready for Implementation  
**Estimated Duration**: 2-3 days

---

## 📋 Overview

This checklist breaks down the remediation plan into actionable items with detailed test requirements and UX-oriented endpoint analysis.

---

## 🔴 PHASE 1: Asset CRUD Endpoints (CRITICAL - 6 hours)

### 1.1 Create Schema Models (1 hour)

**File**: `backend/app/schemas/assets.py`

- [ ] **Add FAAssetCreateItem**
  - Fields: display_name, identifier, identifier_type, currency, asset_type, valuation_model
  - Optional: face_value, maturity_date, interest_schedule, late_interest
  - Optional: classification_params (reuse existing FAClassificationParams)
  - Validators: currency uppercase, identifier not empty

- [ ] **Add FABulkAssetCreateRequest**
  - Field: assets (List[FAAssetCreateItem], min_length=1)

- [ ] **Add FAAssetCreateResult**
  - Fields: asset_id, success, message, display_name, identifier
  - Used for per-item response in bulk creation

- [ ] **Add FABulkAssetCreateResponse**
  - Fields: results (List[FAAssetCreateResult]), success_count, failed_count
  - Pattern: consistent with other FA bulk responses

- [ ] **Add FAAssetListFilters** (for GET /list query params)
  - Fields: currency, asset_type, valuation_model, active (default=True), search
  - Optional[str] for all filters

- [ ] **Add FAAssetListResponse**
  - Fields: id, display_name, identifier, identifier_type, currency, asset_type, valuation_model, active
  - Computed: has_provider (bool), has_metadata (bool)

- [ ] **Add FABulkAssetDeleteRequest**
  - Field: asset_ids (List[int], min_length=1)

- [ ] **Add FAAssetDeleteResult**
  - Fields: asset_id, success, message

- [ ] **Add FABulkAssetDeleteResponse**
  - Fields: results, success_count, failed_count

- [ ] **Export new models** in `backend/app/schemas/__init__.py`

### 1.2 Implement Service Layer (2 hours)

**File**: `backend/app/services/asset_crud.py` (NEW)

- [ ] **Create AssetCRUDService class**

- [ ] **Implement create_assets_bulk()**
  - Validate: identifier unique per asset (check existing)
  - Create: Asset DB record
  - Handle: classification_params JSON serialization
  - Handle: interest_schedule/late_interest JSON validation
  - Error handling: Per-item try-except (partial success)
  - Return: FABulkAssetCreateResponse with success/failed counts
  - Log: Asset creation events

- [ ] **Implement list_assets()**
  - Query: SELECT from assets with filters
  - Join: LEFT JOIN asset_provider_assignments (to check has_provider)
  - Check: classification_params IS NOT NULL (has_metadata)
  - Filter: Apply currency, asset_type, valuation_model, active
  - Search: LIKE on display_name OR identifier (if search provided)
  - Return: List[FAAssetListResponse]
  - Order: ORDER BY display_name ASC

- [ ] **Implement delete_assets_bulk()**
  - Check: Existing transactions per asset (FK constraint check)
  - Block: Deletion if transactions exist (return error per asset)
  - Delete: Asset record (CASCADE deletes provider_assignments, price_history)
  - Error handling: Per-item try-except
  - Return: FABulkAssetDeleteResponse
  - Log: Deletion events with asset_id

- [ ] **Add comprehensive docstrings** (Google style)

### 1.3 Add API Endpoints (1 hour)

**File**: `backend/app/api/v1/assets.py`

- [ ] **Add POST /assets/bulk endpoint**
  - Handler: create_assets_bulk()
  - Request: FABulkAssetCreateRequest
  - Response: FABulkAssetCreateResponse (201 Created)
  - Description: Comprehensive docstring with example JSON
  - Note: Provider assignment separate (POST /provider/bulk)

- [ ] **Add GET /assets/list endpoint**
  - Handler: list_assets()
  - Query params: currency, asset_type, valuation_model, active, search
  - Response: List[FAAssetListResponse] (200 OK)
  - Description: Filter documentation with examples
  - Default: active=True (only active assets)

- [ ] **Add DELETE /assets/bulk endpoint**
  - Handler: delete_assets_bulk()
  - Request: FABulkAssetDeleteRequest
  - Response: FABulkAssetDeleteResponse (200 OK)
  - Description: CASCADE behavior documented
  - Warning: Transactions block deletion

- [ ] **Update imports** (AssetCRUDService, new schemas)

- [ ] **Verify no endpoint path conflicts**

### 1.4 Write Tests (2 hours)

**File**: `backend/test_scripts/test_api/test_assets_crud.py` (NEW)

- [ ] **Setup: TestServerManager integration**
  - Use existing TestServerManager from test_assets_metadata.py
  - Import get_settings() for dynamic config

- [ ] **Test 1: POST /assets/bulk - Create Single Asset**
  - Request: 1 asset (AAPL, stock)
  - Assert: success=True, asset_id returned
  - Assert: Asset in database with correct fields
  - Verify: display_name, identifier, currency, asset_type

- [ ] **Test 2: POST /assets/bulk - Create Multiple Assets**
  - Request: 3 assets (AAPL, MSFT, GOOGL)
  - Assert: success_count=3, all asset_ids returned
  - Verify: All 3 in database

- [ ] **Test 3: POST /assets/bulk - Partial Success**
  - Request: 3 assets (1 valid, 1 duplicate identifier, 1 invalid)
  - Assert: success_count=1, failed_count=2
  - Verify: Error messages per failed asset
  - Verify: Valid asset created, others not

- [ ] **Test 4: POST /assets/bulk - Duplicate Identifier**
  - Create asset with identifier "TEST1"
  - Try create again with same identifier
  - Assert: success=False, message about duplicate

- [ ] **Test 5: POST /assets/bulk - With classification_params**
  - Request: Asset with classification_params (geographic_area)
  - Assert: success=True
  - Verify: classification_params stored as JSON in DB

- [ ] **Test 6: GET /assets/list - No Filters**
  - Create 3 assets
  - GET /list
  - Assert: Returns 3 assets
  - Verify: has_provider=False (no provider assigned yet)
  - Verify: has_metadata based on classification_params

- [ ] **Test 7: GET /assets/list - Filter by currency**
  - Create 2 USD assets, 1 EUR asset
  - GET /list?currency=USD
  - Assert: Returns only 2 USD assets

- [ ] **Test 8: GET /assets/list - Filter by asset_type**
  - Create 2 STOCK, 1 ETF
  - GET /list?asset_type=STOCK
  - Assert: Returns only 2 STOCK assets

- [ ] **Test 9: GET /assets/list - Search**
  - Create assets: "Apple Inc." (AAPL), "Microsoft" (MSFT)
  - GET /list?search=Apple
  - Assert: Returns only Apple asset

- [ ] **Test 10: GET /assets/list - Active filter**
  - Create 2 assets, set 1 to active=False
  - GET /list?active=True
  - Assert: Returns only 1 active asset
  - GET /list?active=False
  - Assert: Returns only 1 inactive asset

- [ ] **Test 11: GET /assets/list - Has provider**
  - Create asset, assign provider
  - GET /list
  - Assert: has_provider=True for that asset

- [ ] **Test 12: DELETE /assets/bulk - Success**
  - Create 2 assets (no transactions)
  - DELETE /bulk with both asset_ids
  - Assert: success_count=2
  - Verify: Assets deleted from DB

- [ ] **Test 13: DELETE /assets/bulk - Blocked by transactions**
  - Create asset, add transaction (mocked or via test helper)
  - DELETE /bulk
  - Assert: success=False, message about transactions
  - Verify: Asset still in DB

- [ ] **Test 14: DELETE /assets/bulk - CASCADE delete**
  - Create asset, assign provider, add price_history
  - DELETE /bulk
  - Assert: success=True
  - Verify: provider_assignment deleted (CASCADE)
  - Verify: price_history deleted (CASCADE)

- [ ] **Test 15: DELETE /assets/bulk - Partial success**
  - Create 2 assets (1 with transactions, 1 without)
  - DELETE /bulk with both
  - Assert: success_count=1, failed_count=1

**File**: `backend/test_scripts/test_services/test_asset_crud.py` (NEW)

- [ ] **Test create_assets_bulk() - Service layer**
  - Direct service call (no HTTP)
  - Test: Valid input, duplicate, invalid, partial success
  - Assert: Correct DB state

- [ ] **Test list_assets() - Service layer**
  - Direct service call
  - Test: All filters combinations
  - Assert: Correct query results

- [ ] **Test delete_assets_bulk() - Service layer**
  - Direct service call
  - Test: Success, blocked by FK, CASCADE, partial

**Integration with test_runner.py**:

- [ ] **Add test_assets_crud() function**
  - Command: pipenv run pytest test_api/test_assets_crud.py -v
  - Description: "Asset CRUD endpoints (create, list, delete)"

- [ ] **Add to api_tests() dispatcher**
  - Choice: "assets-crud"
  - Help text in help_api()

### 1.5 Documentation (0.5 hours)

- [ ] **Update docs/api-examples/asset-management.md** (NEW file)
  - Section: Create Assets
  - Section: List Assets with filters
  - Section: Delete Assets
  - Examples: cURL commands for each endpoint

- [ ] **Update FEATURE_COVERAGE_REPORT.md**
  - Add: Phase 5.1 extension - Asset CRUD
  - Stats: 3 new endpoints, 9 new schemas, 15 API tests

---

## 🟡 PHASE 2: Schema Cleanup (MEDIUM - 3 hours)

### 2.1 Rename 13 Models with FA Prefix (1 hour)

**Strategy**: Global find-and-replace with verification

- [ ] **Prepare rename list** (copy from plan)
  ```
  AssetProviderAssignmentModel → FAAssetProviderAssignment
  InterestRatePeriod → FAInterestRatePeriod
  LateInterestConfig → FALateInterestConfig
  ScheduledInvestmentSchedule → FAScheduledInvestmentSchedule
  ScheduledInvestmentParams → FAScheduledInvestmentParams
  ClassificationParamsModel → FAClassificationParams
  PatchAssetMetadataRequest → FAPatchMetadataRequest
  PatchAssetMetadataItem → FAPatchMetadataItem
  BulkPatchAssetMetadataRequest → FABulkPatchMetadataRequest
  AssetMetadataResponse → FAAssetMetadataResponse
  MetadataChangeDetail → FAMetadataChangeDetail
  MetadataRefreshResult → FAMetadataRefreshResult
  BulkAssetReadRequest → FABulkAssetReadRequest
  BulkMetadataRefreshRequest → FABulkMetadataRefreshRequest
  BulkMetadataRefreshResponse → FABulkMetadataRefreshResponse
  ```

- [ ] **Rename in backend/app/schemas/assets.py**
  - Use IDE refactor (preserves references) OR
  - Manual find-replace with case-sensitive match

- [ ] **Update all imports across codebase**
  - Files to check: api/v1/assets.py, services/*.py, test_scripts/**/*.py
  - Command: `grep -r "AssetProviderAssignmentModel" backend/`
  - Update each file

- [ ] **Update schemas/__init__.py exports**
  - Replace old names with new FA-prefixed names

- [ ] **Verify no broken imports**
  - Run: `python -c "from backend.app.schemas import assets; print('OK')"`
  - Run: `python -c "from backend.app.api.v1 import assets; print('OK')"`

- [ ] **Run all tests** to verify no regressions
  - Command: `./test_runner.py all`
  - Must pass 100%

### 2.2 Move Price Models to prices.py (0.5 hours)

**Models to move**: CurrentValueModel, PricePointModel, HistoricalDataModel

- [ ] **Cut from backend/app/schemas/assets.py**
  - Remove class definitions
  - Keep: Compounding enums (asset-specific)

- [ ] **Paste into backend/app/schemas/prices.py**
  - Add to appropriate section
  - Maintain docstrings

- [ ] **Update imports in assets.py**
  - Add: `from .prices import CurrentValueModel, PricePointModel, HistoricalDataModel`
  - Verify: Other files importing from assets.py still work

- [ ] **Update schemas/__init__.py**
  - Export from prices module instead of assets

- [ ] **Find all usages and update imports**
  - Command: `grep -r "from.*assets import.*CurrentValueModel" backend/`
  - Update to: `from backend.app.schemas.prices import CurrentValueModel`

- [ ] **Verify imports**
  - Run: `python -c "from backend.app.schemas.prices import PricePointModel; print('OK')"`

- [ ] **Run tests** - verify no breaks

### 2.3 Remove Duplicate BackwardFillInfo (0.25 hours)

- [ ] **Verify BackwardFillInfo in common.py**
  - File: backend/app/schemas/common.py
  - Confirm: Class exists and is complete

- [ ] **Remove from assets.py**
  - Delete class definition
  - Add import: `from .common import BackwardFillInfo`

- [ ] **Find all usages**
  - Command: `grep -r "BackwardFillInfo" backend/ --include="*.py"`
  - Update imports where needed

- [ ] **Verify no duplicate**
  - Search: `grep -r "class BackwardFillInfo" backend/app/schemas/`
  - Should find only in common.py

- [ ] **Run tests** - verify no breaks

### 2.4 Update All Imports (0.5 hours)

- [ ] **Systematically check each module**
  - api/v1/assets.py
  - services/asset_source.py
  - services/asset_metadata.py
  - test_scripts/test_api/*.py
  - test_scripts/test_services/*.py

- [ ] **Fix import statements**
  - Update to new FA-prefixed names
  - Update prices imports

- [ ] **Run import verification script**
  ```bash
  python -c "
  from backend.app.schemas import assets
  from backend.app.schemas import prices
  from backend.app.schemas import common
  print('All imports OK')
  "
  ```

### 2.5 Final Verification (0.25 hours)

- [ ] **Run full test suite**
  - Command: `./test_runner.py all`
  - Expected: 100% pass rate (no regressions)

- [ ] **Check API endpoints still work**
  - Start server: `./dev.sh server`
  - Run: `./dev.sh info:api`
  - Verify: 33 endpoints listed

- [ ] **Verify OpenAPI spec updated**
  - Visit: http://localhost:8000/api/v1/docs
  - Check: Schema names show FA prefix

---

## 🟢 PHASE 3: Single Endpoint Decision & Implementation (LOW - 0.5 hours)

### 3.1 Document Decision (0.1 hours)

- [ ] **Confirm: Option B - Keep All**
  - Developer UX priority
  - Common REST pattern (single + bulk)

### 3.2 Remove TODO Comments (0.2 hours)

**Files to update**: `backend/app/api/v1/assets.py`

- [ ] **Line 202**: Remove `# TODO: rimuovere e usare solo la bulk`
  - Replace with: `# Convenience wrapper for single-asset price upsert (calls bulk internally)`

- [ ] **Line 244**: Remove `# TODO: rimuovere e usare solo la bulk`
  - Replace with: `# Convenience wrapper for single-asset price deletion (calls bulk internally)`

- [ ] **Line 414**: Remove `# TODO: rimuovere e usare solo la bulk`
  - Replace with: `# Convenience wrapper for single-asset price refresh (calls bulk internally)`

- [ ] **Line 531**: Remove `# TODO: rimuovere endpoint singolo e usare solo il bulk`
  - Replace with: `# Single metadata refresh (frequently used operation)`

### 3.3 Identify Additional Single-Wrapper Candidates (0.2 hours)

**Analysis**: Review all bulk endpoints for single-wrapper opportunities

**Current state** (from grep analysis):

**Assets API** - Already have single wrappers:
- ✅ POST /{asset_id}/provider (wraps /provider/bulk)
- ✅ DELETE /{asset_id}/provider (wraps /provider/bulk)
- ✅ POST /{asset_id}/prices (wraps /prices/bulk)
- ✅ DELETE /{asset_id}/prices (wraps /prices/bulk)
- ✅ POST /{asset_id}/prices-refresh (wraps /prices-refresh/bulk)
- ✅ POST /{asset_id}/metadata/refresh (wraps /metadata/refresh/bulk)

**Assets API** - Missing single wrappers:
- [ ] **POST /assets/bulk** → ❌ No single `POST /assets/{asset_id}` (create not needed as single)
- [ ] **PATCH /assets/metadata** → ✅ Could add `PATCH /assets/{asset_id}/metadata`
- [ ] **DELETE /assets/bulk** → ✅ Could add `DELETE /assets/{asset_id}` (delete single asset)

**FX API** - No single wrappers exist:
- [ ] **POST /fx/sync/bulk** → ✅ Could add `POST /fx/sync` (single date+currencies)
- [ ] **POST /fx/rate-set/bulk** → ✅ Could add `POST /fx/rate-set` (single rate)
- [ ] **DELETE /fx/rate-set/bulk** → ✅ Could add `DELETE /fx/rate-set` (single rate by date+pair)
- [ ] **POST /fx/convert/bulk** → ❌ Already handles single conversion (items list can be length 1)
- [ ] **POST /fx/pair-sources/bulk** → ✅ Could add `POST /fx/pair-sources` (single source)
- [ ] **DELETE /fx/pair-sources/bulk** → ✅ Could add `DELETE /fx/pair-sources/{id}` (single source)

**Recommendation for UX Phase**:

**HIGH Priority** (common operations):
1. [ ] `PATCH /assets/{asset_id}/metadata` - Convenience for metadata update
2. [ ] `DELETE /assets/{asset_id}` - Convenience for asset deletion
3. [ ] `POST /fx/rate-set` - Manual single rate entry (common)
4. [ ] `DELETE /fx/rate-set` - Delete specific rate (common)

**MEDIUM Priority** (occasional use):
5. [ ] `POST /fx/sync` - Sync single currency pair for date range
6. [ ] `POST /fx/pair-sources` - Add single pair source config
7. [ ] `DELETE /fx/pair-sources/{id}` - Remove single pair source

**LOW Priority** (rare operations):
- Asset creation typically bulk import (CSV)
- Most other operations better as bulk

- [ ] **Document recommendations** in TODO file for future UX phase

---

## 🔵 PHASE 4: Minor Fixes (OPTIONAL - 2 hours)

### 4.1 Add DateRangeModel Validator (0.25 hours)

**File**: `backend/app/schemas/common.py`

- [ ] **Add @model_validator to DateRangeModel**
  ```python
  @model_validator(mode='after')
  def validate_end_after_start(self) -> 'DateRangeModel':
      """Ensure end >= start when provided."""
      if self.end is not None and self.end < self.start:
          raise ValueError(f"end date ({self.end}) must be >= start date ({self.start})")
      return self
  ```

- [ ] **Write test** in `test_utilities/test_datetime_utils.py` or create new file
  - Test: end < start → ValueError
  - Test: end = start → OK
  - Test: end > start → OK
  - Test: end = None → OK

- [ ] **Run tests**: `./test_runner.py utils datetime`

### 4.2 Fix Compound Frequency Validation (0.5 hours)

**File**: `backend/app/schemas/assets.py`

- [ ] **Update FAInterestRatePeriod (rename done in Phase 2)**
  ```python
  @model_validator(mode='after')
  def validate_compound_frequency(self) -> 'FAInterestRatePeriod':
      """Ensure COMPOUND has frequency, SIMPLE doesn't."""
      if self.compounding == CompoundingType.COMPOUND:
          if self.compound_frequency is None:
              raise ValueError("compound_frequency required when compounding=COMPOUND")
      elif self.compounding == CompoundingType.SIMPLE:
          if self.compound_frequency is not None:
              raise ValueError("compound_frequency should not be set when compounding=SIMPLE")
      return self
  ```

- [ ] **Apply same fix to FALateInterestConfig**

- [ ] **Update test**: `test_utilities/test_scheduled_investment_schemas.py`
  - Remove: @pytest.mark.skip decorators
  - Update: Test names to use FA prefix
  - Verify: Tests now pass

- [ ] **Run tests**: `./test_runner.py utils scheduled-investment`

### 4.3 Rename CurrenciesResponseModel (0.25 hours)

**File**: `backend/app/schemas/fx.py`

- [ ] **Rename class**: `CurrenciesResponseModel` → `FXCurrenciesResponse`

- [ ] **Update import in api/v1/fx.py**
  - Line ~106: Update response_model

- [ ] **Update schemas/__init__.py** export

- [ ] **Verify no other usages**
  - Command: `grep -r "CurrenciesResponseModel" backend/`

- [ ] **Run FX tests**: `./test_runner.py api fx`

### 4.4 Document Low-Priority TODOs (1 hour)

**Create file**: `docs/TODO_FUTURE.md` (NEW)

- [ ] **Section: Cache Management**
  - Item: Implement cache cleanup system (yfinance, general)
  - Priority: LOW
  - Effort: 4-6 hours
  - Impact: Memory optimization

- [ ] **Section: Search Enhancements**
  - Item: Fuzzy search implementation (yfinance provider)
  - Priority: LOW
  - Effort: 2-3 hours
  - Impact: Better asset discovery

- [ ] **Section: Provider Improvements**
  - Item: CSS scraper Pydantic params class
  - Priority: MEDIUM
  - Effort: 2 hours
  - Impact: Type safety
  
  - Item: CSS scraper HTTP headers via provider_params
  - Priority: LOW
  - Effort: 1 hour
  - Impact: Flexibility

- [ ] **Section: Testing**
  - Item: Timezone handling verification (yfinance)
  - Priority: MEDIUM
  - Effort: 2 hours
  - Impact: Correctness
  
  - Item: Additional test edge cases (various)
  - Priority: LOW
  - Effort: 4-8 hours
  - Impact: Coverage

- [ ] **Section: FX System**
  - Item: FED provider auto-config investigation
  - Priority: MEDIUM
  - Effort: 3-4 hours
  - Impact: Fix existing issue

- [ ] **Section: Documentation**
  - Item: Docker documentation update
  - Priority: HIGH (when Docker implemented)
  - Effort: 2 hours
  - Impact: Deployment

---

## ✅ VERIFICATION CHECKLIST

### After Phase 1

- [ ] All 3 new endpoints return 200/201
- [ ] Assets created via API visible in DB
- [ ] Assets listed with correct filters
- [ ] Assets deleted successfully
- [ ] 15 API tests pass (100%)
- [ ] 15 service tests pass (100%)
- [ ] Existing tests still pass (no regressions)

### After Phase 2

- [ ] All 13 models renamed (verified via grep)
- [ ] All imports updated (no ModuleNotFoundError)
- [ ] 3 price models in prices.py (not assets.py)
- [ ] BackwardFillInfo only in common.py
- [ ] All existing tests pass (100%)
- [ ] OpenAPI spec shows FA prefixes

### After Phase 3

- [ ] 4 TODO comments replaced with documentation
- [ ] Decision documented in code
- [ ] Future single-wrapper endpoints documented

### After Phase 4

- [ ] DateRangeModel validator works (test passes)
- [ ] Compound frequency validation works (skipped tests now pass)
- [ ] CurrenciesResponseModel renamed to FXCurrenciesResponse
- [ ] TODO_FUTURE.md created with 10+ items

---

## 📊 Test Coverage Summary

### New Tests to Write

| Test File | Type | Tests | Purpose |
|-----------|------|-------|---------|
| `test_api/test_assets_crud.py` | API | 15 | Asset CRUD endpoints (create, list, delete) |
| `test_services/test_asset_crud.py` | Service | 12 | AssetCRUDService logic |
| `test_utilities/test_datetime_utils.py` | Utility | 4 | DateRangeModel validator |
| `test_utilities/test_scheduled_investment_schemas.py` | Utility | 2 (fix) | Compound frequency validator |
| **TOTAL** | | **33** | |

### Test Runner Integration

- [ ] **Add api_assets_crud() function** to test_runner.py
- [ ] **Add service_asset_crud() function** to test_runner.py
- [ ] **Update api_tests() dispatcher** with "assets-crud" choice
- [ ] **Update services_tests() dispatcher** with "asset-crud" choice
- [ ] **Update help_api()** with new test description
- [ ] **Update help_services()** with new test description

---

## 🎯 Success Metrics

**Phase 1 Complete**:
- ✅ 3 new endpoints functional
- ✅ 9 new schemas implemented
- ✅ 27 new tests passing (15 API + 12 service)
- ✅ 0 regressions in existing tests
- ✅ E2E test scenario executable

**Phase 2 Complete**:
- ✅ 13 models renamed (100% FA prefix consistency)
- ✅ 0 duplicate classes
- ✅ 3 models relocated to prices.py
- ✅ All imports updated
- ✅ 0 broken tests

**Phase 3 Complete**:
- ✅ 4 TODO comments replaced
- ✅ 7 future endpoints identified
- ✅ Decision documented

**Phase 4 Complete**:
- ✅ 2 validators fixed
- ✅ 1 model renamed
- ✅ 10+ future TODOs documented
- ✅ 0 skipped tests

**Overall Success**:
- ✅ 33 new tests passing
- ✅ 100% existing tests passing
- ✅ API count: 33 → 36 endpoints
- ✅ Schema consistency: 100%
- ✅ Documentation complete

---

## 📝 Notes

**Breaking Changes**: Only Phase 2 (schema rename) - pre-beta acceptable

**Version Bump**: 2.2 → 2.3

**Estimated Time Breakdown**:
- Phase 1: 6 hours (critical path)
- Phase 2: 3 hours (can parallelize with Phase 1 testing)
- Phase 3: 0.5 hours (quick wins)
- Phase 4: 2 hours (optional improvements)
- **Total**: 11.5 hours (~2 days with breaks)

**Priority Order**: 1 → 2 → 3 → 4

**Checkpoint**: After Phase 1, verify E2E test works end-to-end before proceeding.

---

**Checklist Created**: November 20, 2025  
**Ready for Implementation**: ✅ YES  
**Approved by**: [Pending]
