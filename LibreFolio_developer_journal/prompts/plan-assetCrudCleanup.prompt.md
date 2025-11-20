# Asset CRUD & Code Cleanup - TODO Remediation Plan

**Date**: November 20, 2025  
**Objective**: Fix schema organization, add missing asset CRUD endpoints, resolve all TODO items
---

## 🎯 Executive Summary

### Critical Issues Identified

1. **Missing Asset CRUD Endpoints** 🔴 HIGH PRIORITY
    - No `POST /assets/bulk` to create assets
    - No `GET /assets/list` to list all assets
    - No `DELETE /assets/bulk` to delete assets
    - Current `POST /assets` is actually a bulk READ (naming confusion)
2. **Schema Organization Problems** 🟡 MEDIUM PRIORITY
    - 13 classes in `assets.py` missing `FA` prefix (naming inconsistency)
    - 4 price-related models in wrong file (`assets.py` instead of `prices.py`)
    - 1 duplicate `BackwardFillInfo` (exists in both `assets.py` and `common.py`)
3. **Single-Asset Wrapper Endpoints** 🟢 LOW PRIORITY
    - 4 convenience endpoints marked for removal (but useful for developer UX)
    - Decision needed: keep or remove?
4. **Minor Issues** 🔵 OPTIONAL
    - Missing validators (DateRangeModel, compound frequency)
    - Provider-specific improvements (cache cleanup, fuzzy search)
    - Test edge cases

---

## 📦 Phase 1: Asset CRUD Endpoints (Priority: 🔴 HIGH)

### Problem Statement

Currently **no way to create, list, or delete assets** via API. This is a critical gap that blocks the E2E test scenario and normal application usage.

### Current State Analysis

**Existing Endpoints**:

- ✅ `POST /assets` - Bulk READ (confusing name, should be `/assets/bulk/read` or similar)
- ✅ `PATCH /assets/metadata` - Bulk metadata update
- ✅ `POST /assets/{id}/metadata/refresh` - Single metadata refresh
- ✅ `POST /assets/metadata/refresh/bulk` - Bulk metadata refresh
  **Missing Endpoints**:
- ❌ `POST /assets/bulk` - Create multiple assets
- ❌ `GET /assets/list` - List all assets (with filters)
- ❌ `DELETE /assets/bulk` - Delete multiple assets
- ❌ `PUT /assets/bulk` - Update asset definition (full replace)

### Solution: Add Asset CRUD Endpoints

#### Step 1.1: Create Schemas (in `assets.py`)

**New Models** (with `FA` prefix):

```python
# CREATE
class FAAssetCreateItem(BaseModel):
    """Single asset to create."""
    display_name: str
    identifier: str
    identifier_type: Optional[str] = None
    currency: str
    asset_type: Optional[str] = None
    valuation_model: Optional[str] = "MARKET_PRICE"
    # Scheduled yield fields (optional)
    face_value: Optional[Decimal] = None
    maturity_date: Optional[date] = None
    interest_schedule: Optional[str] = None  # JSON
    late_interest: Optional[str] = None  # JSON
    # Classification metadata (optional)
    classification_params: Optional[FAClassificationParams] = None


class FABulkAssetCreateRequest(BaseModel):
    """Bulk asset creation request."""
    assets: List[FAAssetCreateItem] = Field(..., min_length=1)


class FAAssetCreateResult(BaseModel):
    """Result of single asset creation."""
    asset_id: Optional[int] = None
    success: bool
    message: str
    display_name: str
    identifier: str


class FABulkAssetCreateResponse(BaseModel):
    """Bulk asset creation response (partial success allowed)."""
    results: List[FAAssetCreateResult]
    success_count: int
    failed_count: int


# LIST/FILTER
class FAAssetListFilters(BaseModel):
    """Filters for asset list query."""
    currency: Optional[str] = None
    asset_type: Optional[str] = None
    valuation_model: Optional[str] = None
    active: Optional[bool] = True  # Default: only active
    search: Optional[str] = None  # Search in display_name, identifier


class FAAssetListResponse(BaseModel):
    """Single asset in list response."""
    id: int
    display_name: str
    identifier: str
    identifier_type: Optional[str]
    currency: str
    asset_type: Optional[str]
    valuation_model: Optional[str]
    active: bool
    has_provider: bool  # True if provider assigned
    has_metadata: bool  # True if classification_params set


# DELETE
class FABulkAssetDeleteRequest(BaseModel):
    """Bulk asset deletion request."""
    asset_ids: List[int] = Field(..., min_length=1)


class FAAssetDeleteResult(BaseModel):
    """Result of single asset deletion."""
    asset_id: int
    success: bool
    message: str


class FABulkAssetDeleteResponse(BaseModel):
    """Bulk asset deletion response."""
    results: List[FAAssetDeleteResult]
    success_count: int
    failed_count: int
```

#### Step 1.2: Implement Service Methods

**Location**: `backend/app/services/asset_crud.py` (NEW FILE)

```python
class AssetCRUDService:
    """Service for asset CRUD operations."""

    @staticmethod
    async def create_assets_bulk(
            assets: List[FAAssetCreateItem],
            session: AsyncSession
            ) -> FABulkAssetCreateResponse:
        """Create multiple assets in bulk (partial success allowed)."""
        results = []
        for item in assets:
            try:
                # Validate identifier unique
                # Create Asset record
                # Optionally create classification_params
                # Return success result
                pass
            except Exception as e:
                results.append(FAAssetCreateResult(
                    success=False,
                    message=str(e),
                    display_name=item.display_name,
                    identifier=item.identifier
                    ))
        success_count = sum(1 for r in results if r.success)
        return FABulkAssetCreateResponse(
            results=results,
            success_count=success_count,
            failed_count=len(results) - success_count
            )

    @staticmethod
    async def list_assets(
            filters: FAAssetListFilters,
            session: AsyncSession
            ) -> List[FAAssetListResponse]:
        """List assets with optional filters."""
        # Build query with filters
        # Join with asset_provider_assignments (check has_provider)
        # Check classification_params IS NOT NULL (has_metadata)
        # Return list
        pass

    @staticmethod
    async def delete_assets_bulk(
            asset_ids: List[int],
            session: AsyncSession
            ) -> FABulkAssetDeleteResponse:
        """Delete multiple assets (partial success allowed).
        Note: CASCADE DELETE handles:
        - asset_provider_assignments
        - price_history
        - transactions (if any - may want to prevent)
        """
        # Check for existing transactions (block deletion if any?)
        # Delete assets
        # Return results
        pass
```

#### Step 1.3: Add API Endpoints (in `assets.py`)

```python
# CREATE
@router.post("/bulk", response_model=FABulkAssetCreateResponse)
async def create_assets_bulk(
        request: FABulkAssetCreateRequest,
        session: AsyncSession = Depends(get_session_generator)
        ):
    """
    Create multiple assets in bulk (partial success allowed).
    Creates asset records with optional classification metadata.
    Provider assignment can be done separately via POST /assets/provider/bulk.
    """
    return await AssetCRUDService.create_assets_bulk(request.assets, session)


# LIST
@router.get("/list", response_model=List[FAAssetListResponse])
async def list_assets(
        currency: Optional[str] = Query(None),
        asset_type: Optional[str] = Query(None),
        valuation_model: Optional[str] = Query(None),
        active: bool = Query(True),
        search: Optional[str] = Query(None),
        session: AsyncSession = Depends(get_session_generator)
        ):
    """
    List all assets with optional filters.
    Query Parameters:
    - currency: Filter by currency (e.g., "USD")
    - asset_type: Filter by type (e.g., "STOCK")
    - valuation_model: Filter by model (e.g., "MARKET_PRICE")
    - active: Include only active assets (default: true)
    - search: Search in display_name or identifier
    """
    filters = FAAssetListFilters(
        currency=currency,
        asset_type=asset_type,
        valuation_model=valuation_model,
        active=active,
        search=search
        )
    return await AssetCRUDService.list_assets(filters, session)


# DELETE
@router.delete("/bulk", response_model=FABulkAssetDeleteResponse)
async def delete_assets_bulk(
        request: FABulkAssetDeleteRequest,
        session: AsyncSession = Depends(get_session_generator)
        ):
    """
    Delete multiple assets in bulk.
    Warning: This will CASCADE DELETE:
    - Provider assignments
    - Price history
    - Transactions will block deletion (integrity constraint)
    """
    return await AssetCRUDService.delete_assets_bulk(request.asset_ids, session)
```

#### Step 1.4: Rename Confusing Endpoint

**Current**: `POST /assets` (bulk READ)  
**Problem**: Confusing - POST usually creates, not reads  
**Options**:

1. Keep as-is (POST for bulk read is common pattern)
2. Rename to `POST /assets/read/bulk`
3. Add convenient single wrapper `GET /assets/{id}/read` for single read

---

## 🏗️ Phase 2: Schema Organization & Naming (Priority: 🟡 MEDIUM)

### Problem Statement

13 models in `assets.py` don't follow FA prefix convention, 4 price models in wrong file, 1 duplicate model.

### Step 2.1: Rename Models with FA Prefix

**File**: `backend/app/schemas/assets.py`
| Current Name | New Name | Used By |
|-------------|----------|---------|
| `AssetProviderAssignmentModel` | `FAAssetProviderAssignment` | Provider endpoints |
| `InterestRatePeriod` | `FAInterestRatePeriod` | Scheduled investment |
| `LateInterestConfig` | `FALateInterestConfig` | Scheduled investment |
| `ScheduledInvestmentSchedule` | `FAScheduledInvestmentSchedule` | Scheduled investment |
| `ScheduledInvestmentParams` | `FAScheduledInvestmentParams` | Provider params |
| `ClassificationParamsModel` | `FAClassificationParams` | Metadata system |
| `PatchAssetMetadataRequest` | `FAPatchMetadataRequest` | PATCH endpoint |
| `PatchAssetMetadataItem` | `FAPatchMetadataItem` | Bulk PATCH |
| `BulkPatchAssetMetadataRequest` | `FABulkPatchMetadataRequest` | Bulk PATCH |
| `AssetMetadataResponse` | `FAAssetMetadataResponse` | Read endpoint |
| `MetadataChangeDetail` | `FAMetadataChangeDetail` | Metadata refresh |
| `MetadataRefreshResult` | `FAMetadataRefreshResult` | Metadata refresh |
| `BulkAssetReadRequest` | `FABulkAssetReadRequest` | Bulk read |
| `BulkMetadataRefreshRequest` | `FABulkMetadataRefreshRequest` | Bulk refresh |
| `BulkMetadataRefreshResponse` | `FABulkMetadataRefreshResponse` | Bulk refresh |
**Action**: Global find-and-replace in all files (schemas, API, services, tests)

### Step 2.2: Move Price Models to `prices.py`

**File**: `backend/app/schemas/assets.py` → `backend/app/schemas/prices.py`
| Model | Reason |
|-------|--------|
| `CurrentValueModel` | Price-related |
| `PricePointModel` | Price structure |
| `HistoricalDataModel` | Price history |
**Keep in `assets.py`**: Models directly related to asset definition (not prices)

### Step 2.3: Remove Duplicate `BackwardFillInfo`

**Current State**:

- `backend/app/schemas/common.py` - `BackwardFillInfo` ✅ (keep this)
- `backend/app/schemas/assets.py` - `BackwardFillInfo` ❌ (remove, import from common)
  **Action**: Delete from `assets.py`, import from `common.py`, check other usage in codebase and fix everywhere.

### Step 2.4: Financial Calculation Enums - Keep in assets.py

**Decision**: Keep `CompoundingType`, `CompoundFrequency`, `DayCountConvention` in `assets.py`
**Reason**: Used primarily in scheduled investment schemas (asset-specific), not general price calculations
---

## 🧹 Phase 3: Single-Asset Endpoints (Priority: 🟢 LOW)

### Problem Statement

4 single-asset endpoints marked with TODO for removal, but they provide good developer UX.
**Endpoints**:

1. `POST /{asset_id}/prices` - Convenience wrapper for bulk upsert
2. `DELETE /{asset_id}/prices` - Convenience wrapper for bulk delete
3. `POST /{asset_id}/prices-refresh` - Convenience wrapper for bulk refresh
4. `POST /{asset_id}/metadata/refresh` - Single metadata refresh

More: identify and save as TODO, other single-element endpoints to implement as Convenience wrapper for bulk operation, if any.

### Decision Options

**Option A: Remove All** (strict bulk-only)

- ✅ Consistent API (bulk-only)
- ✅ Less code to maintain
- ❌ Worse developer UX (must use bulk for single operation)
  **Option B: Keep All** (convenience wrappers)
- ✅ Better developer UX
- ✅ Common pattern (single + bulk)
- ❌ More code to maintain
- ❌ Endpoint proliferation
  **Option C: Keep Some** (hybrid)
- Keep: `POST /{asset_id}/metadata/refresh` (frequently used single operation)
- Remove: Price endpoints (usually bulk operations anyway)
  **Recommendation**: **Option B - Keep All**
- Developer UX is important
- Wrappers are thin (just call bulk internally)
- Common REST pattern (single + bulk)
- Remove TODO comments, document as "convenience wrappers"

Scelta utente: Confermo la scelta dell'opzione b

---

## 🔧 Phase 4: Minor Fixes (Priority: 🔵 OPTIONAL)

### Step 4.1: Add DateRangeModel Validator

**File**: `backend/app/schemas/common.py`

```python
class DateRangeModel(BaseModel):
    start: date = Field(..., description="Start date (inclusive)")
    end: Optional[date] = Field(None, description="End date (inclusive, optional)")

    @model_validator(mode='after')
    def validate_end_after_start(self) -> 'DateRangeModel':
        """Ensure end >= start when provided."""
        if self.end is not None and self.end < self.start:
            raise ValueError(f"end date ({self.end}) must be >= start date ({self.start})")
        return self
```

### Step 4.2: Fix Compound Frequency Validation

**File**: `backend/app/schemas/assets.py`
**Problem**: `field_validator` runs before defaults, can't catch COMPOUND without frequency
**Solution**: Use `model_validator(mode='after')`

```python
class FAInterestRatePeriod(BaseModel):  # Renamed from InterestRatePeriod
    # ...existing fields...
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

**Apply same fix to**: `FALateInterestConfig` (renamed from LateInterestConfig)

### Step 4.3: Rename `CurrenciesResponseModel`

**File**: `backend/app/schemas/fx.py`
**Current**: `CurrenciesResponseModel`  
**Target**: `FXCurrenciesResponse`
**Action**: Rename + update imports in `fx.py`

### Step 4.4: Document Remaining TODOs

**Low-priority TODOs to document (not implement now)**:

- Cache cleanup system (yfinance, general)
- Fuzzy search implementation (yfinance)
- CSS scraper Pydantic params class
- CSS scraper HTTP headers via provider_params
- Timezone handling verification (yfinance)
- Additional test edge cases
- FED provider auto-config investigation
- Docker documentation update

---

## 📊 Implementation Priority Matrix

| Phase                         | Priority    | Effort    | Impact                   | Dependencies              |
|-------------------------------|-------------|-----------|--------------------------|---------------------------|
| **Phase 1: Asset CRUD**       | 🔴 HIGH     | 4-6 hours | 🔴 Critical (blocks E2E) | None                      |
| **Phase 2: Schema Cleanup**   | 🟡 MEDIUM   | 2-3 hours | 🟡 Medium (consistency)  | Phase 1 (avoid conflicts) |
| **Phase 3: Single Endpoints** | 🟢 LOW      | 0.5 hours | 🟢 Low (just decision)   | None                      |
| **Phase 4: Minor Fixes**      | 🔵 OPTIONAL | 1-2 hours | 🔵 Low (nice-to-have)    | None                      |

---

## 🎯 Recommended Execution Order

### Sprint 1: Asset CRUD (1 day)

1. ✅ Create schemas (1 hour)
2. ✅ Implement service (2 hours)
3. ✅ Add API endpoints (1 hour)
4. ✅ Write tests (2 hours)
5. ✅ Update documentation (0.5 hours)

### Sprint 2: Schema Cleanup (0.5 day)

1. ✅ Rename 13 models with FA prefix (1 hour)
2. ✅ Move 3 price models to `prices.py` (0.5 hours)
3. ✅ Remove duplicate `BackwardFillInfo` (0.25 hours)
4. ✅ Update all imports (0.5 hours)
5. ✅ Verify tests still pass (0.25 hours)

### Sprint 3: Decisions & Minor Fixes (0.5 day)

1. ✅ Decide on single endpoints (keep/remove)
2. ✅ Remove TODO comments or implement fixes
3. ✅ Add validators (DateRange, CompoundFrequency)
4. ✅ Final verification

---

## 🚨 Breaking Changes Warning

### Phase 2 (Schema Renaming)

**Impact**: All API responses will have different model names in OpenAPI spec
**Mitigation**:

- ✅ This is pre-beta, acceptable
- ✅ Version bump to 2.3
- ✅ Document in changelog

### Phase 1 (New Endpoints)

**Impact**: None (additive only)
---

## ✅ Success Criteria

**Phase 1 Complete**:

- ✅ Can create assets via `POST /assets/bulk`
- ✅ Can list assets via `GET /assets/list`
- ✅ Can delete assets via `DELETE /assets/bulk`
- ✅ E2E test scenario works end-to-end
- ✅ All tests passing
  **Phase 2 Complete**:
- ✅ All 13 models renamed with FA prefix
- ✅ No duplicate models across files
- ✅ Price models in `prices.py`
- ✅ 100% naming consistency
- ✅ All tests passing
  **Phase 3 Complete**:
- ✅ Decision documented
- ✅ TODO comments resolved
  **Phase 4 Complete**:
- ✅ Validators working correctly
- ✅ No skipped tests
- ✅ Low-priority TODOs documented

---

## 📝 TODO Items Summary

### Critical (Fix Now)

1. ✅ Missing Asset CRUD endpoints (Phase 1)
2. ✅ Schema naming inconsistency - 13 models (Phase 2.1)
3. ✅ Duplicate `BackwardFillInfo` (Phase 2.3)
4. ✅ Price models in wrong file (Phase 2.2)

### Important (Fix Soon)

5. ✅ Single-endpoint decision (Phase 3)
6. ✅ DateRangeModel validator (Phase 4.1)
7. ✅ Compound frequency validation (Phase 4.2)
8. ✅ `CurrenciesResponseModel` rename (Phase 4.3)

### Optional (Document/Future)

9. 📝 Cache cleanup system
10. 📝 Fuzzy search implementation
11. 📝 CSS scraper params class
12. 📝 Timezone handling verification
13. 📝 Additional test edge cases
14. 📝 FED provider auto-config investigation
15. 📝 Docker documentation

---

## 📈 Estimated Timeline

**Total Time**: 2-3 days

- **Day 1**: Phase 1 (Asset CRUD) - 6 hours
- **Day 2 Morning**: Phase 2 (Schema Cleanup) - 3 hours
- **Day 2 Afternoon**: Phase 3 (Decisions) + Phase 4 (Fixes) - 2 hours
- **Day 3**: Testing, documentation, verification - 4 hours

---
**Plan Created**: November 20, 2025  
**Status**: Ready for Execution  
**Next Action**: Begin Phase 1 - Asset CRUD Endpoints
