# Plan: Schema Cleanup - Remove Wrapper Classes and Consolidate Duplicates

**Context**: During code review, multiple wrapper classes were identified that contain only a single `List[...]` field, violating DRY principle and adding unnecessary nesting. Additionally, some classes are nearly identical and can be consolidated.

**Approach**: Remove wrapper classes and use `List[ItemType]` directly in endpoints. Consolidate duplicate/similar classes where appropriate. Use `DateRangeModel` consistently across all schemas.

**Impact**: This is a breaking API change but acceptable since we're in pre-alpha. All affected endpoints and tests must be updated.

---

## 🎯 Identified Issues

### A. Wrapper Classes (Single `List[...]` Field)

These classes serve no purpose except wrapping a list:

1. **FAProvidersResponse** → Use `List[FAProviderInfo]`
2. **FXProvidersResponse** (provider.py) → Use `List[FXProviderInfo]`
3. **FXProvidersResponse** (fx.py) → DUPLICATE, remove entirely
4. **FABulkAssignRequest** → Use `List[FAProviderAssignmentItem]`
5. **FABulkRemoveRequest** → Use `List[int]` (just asset_ids)
6. **FABulkAssetCreateRequest** → Use `List[FAAssetCreateItem]`
7. **FABulkPatchMetadataRequest** → Use `List[FAMetadataPatchItem]`
8. **FXConvertRequest** → Use `List[FXConversionRequest]`
9. **FXBulkUpsertRequest** → Use `List[FXUpsertItem]`
10. **FXBulkDeleteRequest** → Use `List[FXDeleteItem]`
11. **FXCreatePairSourcesRequest** → Use `List[FXPairSourceItem]`
12. **FXDeletePairSourcesRequest** → Use `List[FXDeletePairSourceItem]`
13. **FABulkUpsertRequest** → Use `List[FAUpsert]`
14. **FAPriceBulkDeleteRequest** → Use `List[FAAssetDelete]`
15. **FABulkRefreshRequest** → Use `List[FARefreshItem]` + optional `timeout` query param

### B. Classes That Should Use DateRangeModel

These classes have `start_date` + `end_date` fields that should use `DateRangeModel`:

1. **FXConversionRequest** - Has `start_date` + `end_date` (optional)
2. **FXDeleteItem** - Has `start_date` + `end_date` (optional)
3. **FXDeleteResult** - Has `start_date` + `end_date` (optional)
4. **FXSyncResponse** - Has `date_range: tuple[date_type, date_type]` → Use `DateRangeModel`
5. **FARefreshItem** - Has `start_date` + `end_date` → Use `DateRangeModel`

### C. Duplicate/Similar Classes

These classes have significant overlap and could be consolidated:

1. **FAPricePoint** vs **FAUpsertItem**
   - Both represent OHLC price data
   - FAPricePoint has `backward_fill_info` (for queries)
   - FAUpsertItem is for writes (no backward_fill_info)
   - **Solution**: Merge into single `FAPricePoint` class, make `backward_fill_info` optional
   
2. **FAProviderAssignmentItem** vs **FAProviderAssignmentReadItem**
   - AssignmentItem: For POST (write) - has validator
   - ReadItem: For GET (read) - has `last_fetch_at`
   - **Difference**: ReadItem has `last_fetch_at: Optional[str]`, Item has validator
   - **Solution**: Make `last_fetch_at` optional in single class, use `model_validator` only for write operations

### D. Response Classes That Could Be Simplified

Some response classes are inconsistent in structure:

1. **FABulkRefreshResponse** - Has only `results`, missing `success_count`/`failed_count`
2. **FXConvertResponse** - Has `results` + `errors`
3. **FXBulkUpsertResponse** - Has `results` + `success_count` + `errors`
4. **FXBulkDeleteResponse** - Has `results` + `total_deleted` + `errors`

**Recommendation**: Standardize response pattern across all bulk operations.

---

## 📋 Implementation Steps

### Step 1: Remove Wrapper Request Classes - Provider Schemas

**File**: `backend/app/schemas/provider.py`

**Changes**:
- ✅ Remove `FAProvidersResponse` class
- ✅ Remove `FXProvidersResponse` class (duplicate exists in fx.py)
- ✅ Remove `FABulkAssignRequest` class
- ✅ Remove `FABulkRemoveRequest` class
- ✅ Update `__all__` exports

**Affected Endpoints**:
- `GET /assets/provider` → Return `List[FAProviderInfo]`
- `POST /assets/provider` → Accept `List[FAProviderAssignmentItem]`
- `DELETE /assets/provider` → Accept `List[int]` (asset_ids as query params or body)

**Affected Files**:
- `backend/app/api/v1/assets.py` (list_providers, assign_providers_bulk, remove_providers_bulk)

---

### Step 2: Remove Wrapper Request Classes - Asset Schemas

**File**: `backend/app/schemas/assets.py`

**Changes**:
- ✅ Remove `FABulkAssetCreateRequest` class
- ✅ Remove `FABulkPatchMetadataRequest` class
- ✅ Update `__all__` exports

**Affected Endpoints**:
- `POST /assets` → Accept `List[FAAssetCreateItem]`
- `PATCH /metadata` → Accept `List[FAMetadataPatchItem]`

**Affected Files**:
- `backend/app/api/v1/assets.py` (create_assets_bulk, update_assets_metadata_bulk)

---

### Step 3: Remove Wrapper Request Classes - FX Schemas

**File**: `backend/app/schemas/fx.py`

**Changes**:
- ✅ Remove duplicate `FXProvidersResponse` class (keep only in provider.py)
- ✅ Remove `FXConvertRequest` class
- ✅ Remove `FXBulkUpsertRequest` class
- ✅ Remove `FXBulkDeleteRequest` class
- ✅ Remove `FXCreatePairSourcesRequest` class
- ✅ Remove `FXDeletePairSourcesRequest` class
- ✅ Update `__all__` exports

**Affected Endpoints**:
- `GET /fx/providers` → Return `List[FXProviderInfo]` (use from provider.py, delete duplicate)
- `POST /fx/convert` → Accept `List[FXConversionRequest]`
- `POST /fx/rates` → Accept `List[FXUpsertItem]`
- `DELETE /fx/rates` → Accept `List[FXDeleteItem]`
- `POST /fx/pair-sources` → Accept `List[FXPairSourceItem]`
- `DELETE /fx/pair-sources` → Accept `List[FXDeletePairSourceItem]`

**Affected Files**:
- `backend/app/api/v1/fx.py` (convert, upsert_rates, delete_rates, create_pair_sources, delete_pair_sources)

---

### Step 4: Remove Wrapper Request Classes - Price Schemas

**File**: `backend/app/schemas/prices.py`

**Changes**:
- ✅ Remove `FABulkUpsertRequest` class
- ✅ Remove `FAPriceBulkDeleteRequest` class
- ✅ Update `__all__` exports

**Affected Endpoints**:
- `POST /prices` → Accept `List[FAUpsert]`
- `DELETE /prices` → Accept `List[FAAssetDelete]`

**Affected Files**:
- `backend/app/api/v1/assets.py` (upsert_prices_bulk, delete_prices_bulk)

---

### Step 5: Remove Wrapper Request Classes - Refresh Schemas

**File**: `backend/app/schemas/refresh.py`

**Changes**:
- ✅ Remove `FABulkRefreshRequest` class
- ✅ Move `timeout` to query parameter in endpoint
- ✅ Update `__all__` exports

**Affected Endpoints**:
- `POST /prices/refresh` → Accept `List[FARefreshItem]` + `timeout: int = Query(60)`

**Affected Files**:
- `backend/app/api/v1/assets.py` (refresh_prices_bulk)

---

### Step 6: Integrate DateRangeModel in FX Schemas

**File**: `backend/app/schemas/fx.py`

**Changes for FXConversionRequest**:
```python
class FXConversionRequest(BaseModel):
    """Single conversion request with optional date range."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    amount: Decimal = Field(..., gt=0, description="Amount to convert")
    from_currency: str = Field(..., alias="from", description="Source currency")
    to_currency: str = Field(..., alias="to", description="Target currency")
    date_range: DateRangeModel = Field(..., description="Date range for conversion (start required, end optional)")

    # Keep validators for amount and currencies
```

**Changes for FXDeleteItem**:
```python
class FXDeleteItem(BaseModel):
    """Single rate deletion request."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    from_currency: str = Field(..., alias="from", description="Source currency")
    to_currency: str = Field(..., alias="to", description="Target currency")
    date_range: DateRangeModel = Field(..., description="Date range to delete (start required, end optional)")

    # Keep validators for currencies
```

**Changes for FXDeleteResult**:
```python
class FXDeleteResult(BaseModel):
    """Single rate deletion result."""
    success: bool
    base: str
    quote: str
    date_range: DateRangeModel = Field(..., description="Date range deleted")
    existing_count: int
    deleted_count: int
    message: Optional[str] = None
```

**Changes for FXSyncResponse**:
```python
class FXSyncResponse(BaseModel):
    """Response for FX rate synchronization."""
    model_config = ConfigDict(extra="forbid")

    synced: int
    date_range: DateRangeModel = Field(..., description="Date range synced")
    currencies: List[str]
```

**Affected Files**:
- `backend/app/api/v1/fx.py` (convert, delete_rates, sync)
- `backend/app/services/fx.py` (conversion and deletion logic)

---

### Step 7: Integrate DateRangeModel in Refresh Schemas

**File**: `backend/app/schemas/refresh.py`

**Changes for FARefreshItem**:
```python
class FARefreshItem(BaseModel):
    """Single asset refresh request."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    date_range: DateRangeModel = Field(..., description="Date range for refresh")
```

**Affected Files**:
- `backend/app/api/v1/assets.py` (refresh_prices_bulk)
- `backend/app/services/asset_source.py` (bulk_refresh_prices)

---

### ✅ Step 8: Consolidate FAPricePoint and FAUpsertItem - COMPLETATO

**File**: `backend/app/schemas/prices.py`

**Changes**:
```python
class FAPricePoint(BaseModel):
    """Single price point with OHLC data.
    
    Used for both:
    - Upsert operations (backward_fill_info is None)
    - Query results (backward_fill_info may be present)
    """
    model_config = ConfigDict(extra="forbid")

    date: date_type
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal  # Required
    volume: Optional[Decimal] = None
    currency: str  # Required for upsert, optional for query (from asset)
    backward_fill_info: Optional[BackwardFillInfo] = None  # Only present in query results

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return normalize_currency_code(v)

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))
```

**Remove FAUpsertItem class entirely**:
- Update `FAUpsert.prices` to use `List[FAPricePoint]`
- Update all references from `FAUpsertItem` to `FAPricePoint`

**Affected Files**:
- `backend/app/schemas/prices.py` (schema definitions)
- `backend/app/api/v1/assets.py` (upsert_prices_bulk)
- `backend/app/services/asset_source.py` (bulk_upsert_prices)

---

### ✅ Step 8.1: Standardize Delete/Removal Results with BaseDeleteResult - COMPLETATO

**Goal**: Create a common base class for all delete/removal operation results to ensure consistency.

**Motivation**: All delete/removal operations share common fields (`success`, `deleted_count`, `message`), leading to duplication and inconsistent naming (some used `deleted`, others `deleted_count`).

#### Base Class Implementation

**File**: `backend/app/schemas/common.py`

Added `BaseDeleteResult` class after `BaseBulkResponse`:

```python
class BaseDeleteResult(BaseModel):
    """
    Standardized base class for all delete/removal operation results.
    
    Standard fields:
    - success: bool - Whether the deletion succeeded
    - deleted_count: int - Number of items deleted (always >= 0)
    - message: Optional[str] - Info/warning/error message
    
    Subclasses add identifier fields (asset_id, base/quote, etc.)
    """
    model_config = ConfigDict(extra="forbid")
    
    success: bool = Field(..., description="Whether the deletion succeeded")
    deleted_count: int = Field(..., ge=0, description="Number of items deleted")
    message: Optional[str] = Field(None, description="Info/warning/error message")
```

#### Updated Classes (5 total)

**1. FAAssetDeleteResult** (assets.py):
```python
class FAAssetDeleteResult(BaseDeleteResult):
    """Result of single asset deletion."""
    asset_id: int = Field(..., description="Asset ID")
    # Inherits: success, deleted_count, message
```

**2. FAPriceDeleteResult** (prices.py):
```python
class FAPriceDeleteResult(BaseDeleteResult):
    """Result of price deletion for single asset."""
    asset_id: int = Field(..., description="Asset ID")
    # Inherits: success, deleted_count, message
    # CHANGED: Renamed 'deleted' → 'deleted_count'
```

**3. FAProviderRemovalResult** (provider.py):
```python
class FAProviderRemovalResult(BaseDeleteResult):
    """Result of FA provider removal."""
    asset_id: int = Field(..., description="Asset ID")
    # Inherits: success, deleted_count, message
```

**4. FXDeleteResult** (fx.py):
```python
class FXDeleteResult(BaseDeleteResult):
    """Single FX rate deletion result."""
    base: str
    quote: str
    date_range: DateRangeModel
    existing_count: int  # Operation-specific field
    # Inherits: success, deleted_count, message
```

**5. FXDeletePairSourceResult** (fx.py):
```python
class FXDeletePairSourceResult(BaseDeleteResult):
    """Result of pair source deletion."""
    base: str
    quote: str
    priority: Optional[int]
    # Inherits: success, deleted_count, message
```

#### Cleanup Performed

**Removed incomplete wrapper class remnants**:
1. ✅ `FXConvertRequest` (fx.py) - incomplete remnant
2. ✅ `FXBulkUpsertRequest` (fx.py) - incomplete remnant
3. ✅ `FXDeletePairSourcesRequest` (fx.py) - incomplete remnant
4. ✅ `FAPriceBulkDeleteRequest` (prices.py) - incomplete remnant

#### Benefits

1. ✅ **Consistent Naming**: All classes use `deleted_count` (no more `deleted` vs `deleted_count`)
2. ✅ **Less Duplication**: Common fields defined once in base class
3. ✅ **Validation**: `deleted_count >= 0` guaranteed by base class
4. ✅ **API Consistency**: All delete operations have same base structure
5. ✅ **Documentation**: Field descriptions centralized in base class
6. ✅ **Pattern Matching**: Consistent with `BaseBulkResponse[TResult]` approach

#### Breaking Changes

- ⚠️ `FAPriceDeleteResult.deleted` → `FAPriceDeleteResult.deleted_count` (field renamed)
- ⚠️ Service layer must be updated to use `deleted_count` consistently

#### Files Modified (6)

1. ✅ `/backend/app/schemas/common.py` - Added `BaseDeleteResult`
2. ✅ `/backend/app/schemas/assets.py` - Updated `FAAssetDeleteResult` + cleanup __all__
3. ✅ `/backend/app/schemas/prices.py` - Updated `FAPriceDeleteResult` (renamed field)
4. ✅ `/backend/app/schemas/provider.py` - Updated `FAProviderRemovalResult`
5. ✅ `/backend/app/schemas/fx.py` - Updated `FXDeleteResult` + `FXDeletePairSourceResult` + cleanup remnants

**Status**: ✅ All schema changes complete, service layer updates needed

---

### ✅ Step 8.2: Create BaseBulkDeleteResponse for Bulk Delete Operations - COMPLETATO

**Goal**: Combine `BaseBulkResponse` pattern with delete-specific aggregate field for bulk deletion operations.

**Motivation**: Bulk delete responses needed both the list structure from `BaseBulkResponse` and the aggregate `total_deleted` count. Creating `BaseBulkDeleteResponse` avoids field duplication and provides consistent pattern.

#### Base Class Implementation

**File**: `backend/app/schemas/common.py`

Added `BaseBulkDeleteResponse` class after `BaseDeleteResult`:

```python
class BaseBulkDeleteResponse(BaseBulkResponse[TResult]):
    """
    Specialized base class for bulk delete/removal operations.
    
    Combines BaseBulkResponse structure with delete-specific aggregate.
    
    Inherits from BaseBulkResponse:
    - results: List[TResult]
    - success_count: int
    - errors: List[str]
    - failed_count: int (computed property)
    - total_count: int (computed property)
    
    Delete-specific field:
    - total_deleted: int - Total records deleted across all items
    
    Use when bulk operation deletes multiple records per item.
    """
    total_deleted: int = Field(..., ge=0, description="Total records deleted")
```

#### Updated Classes (3 total)

**1. FABulkDeleteResponse** (prices.py):
```python
class FABulkDeleteResponse(BaseBulkDeleteResponse[FAPriceDeleteResult]):
    """Response for bulk price deletion."""
    # Inherits: results, success_count, errors, total_deleted
    pass
```
- **Changed**: Renamed field `deleted_count` → inherits `total_deleted` from base
- **Semantics**: `total_deleted` = sum of all price records deleted across all assets

**2. FXBulkDeleteResponse** (fx.py):
```python
class FXBulkDeleteResponse(BaseBulkDeleteResponse[FXDeleteResult]):
    """Response for bulk FX rate deletion."""
    # Inherits: results, success_count, errors, total_deleted
    pass
```
- **Semantics**: `total_deleted` = sum of all FX rate records deleted

**3. FXDeletePairSourcesResponse** (fx.py):
```python
class FXDeletePairSourcesResponse(BaseBulkDeleteResponse[FXDeletePairSourceResult]):
    """Response for bulk pair source deletion."""
    # Inherits: results, success_count, errors, total_deleted
    pass
```
- **Semantics**: `total_deleted` = sum of all pair source configuration records deleted

#### Design Rationale

**Why not multiple inheritance or just BaseBulkResponse?**
- ❌ Multiple inheritance (BaseBulkResponse + BaseDeleteResult): Semantically wrong - BaseDeleteResult is for single items, not bulk
- ❌ Just BaseBulkResponse with explicit field: Would duplicate `total_deleted` field in 3 places
- ✅ BaseBulkDeleteResponse extends BaseBulkResponse: Clean single inheritance, semantic clarity, zero duplication

**Naming clarity**:
- `success_count`: Number of **items** successfully processed (e.g., assets, pairs)
- `total_deleted`: Number of **records** deleted (e.g., price records, rate records)
- Example: Delete prices for 3 assets → `success_count=3`, `total_deleted=150` (50 prices per asset)

#### Benefits

1. ✅ **No duplication**: `total_deleted` field defined once in base class
2. ✅ **Clear semantics**: Name `BaseBulkDeleteResponse` makes purpose explicit
3. ✅ **Consistent pattern**: Follows same approach as `BaseBulkResponse`
4. ✅ **Type-safe**: Generic[TResult] preserved through inheritance
5. ✅ **Single inheritance**: Clean class hierarchy, no diamond problems

#### Breaking Changes

- ⚠️ FABulkDeleteResponse: Field `deleted_count` → `total_deleted` (inherited from base)
- ⚠️ Service layer must populate `total_deleted` instead of `deleted_count`

#### Files Modified (3)

1. ✅ `/backend/app/schemas/common.py` - Added `BaseBulkDeleteResponse`
2. ✅ `/backend/app/schemas/prices.py` - Updated `FABulkDeleteResponse`, added import
3. ✅ `/backend/app/schemas/fx.py` - Updated `FXBulkDeleteResponse` + `FXDeletePairSourcesResponse`, added import

**Status**: ✅ All schema changes complete

---
### Step 9: Consolidate FAProviderAssignmentItem and FAProviderAssignmentReadItem

**File**: `backend/app/schemas/provider.py`

**Analysis**:
- `FAProviderAssignmentItem`: Used for POST (write), has validator
- `FAProviderAssignmentReadItem`: Used for GET (read), has `last_fetch_at`

**Decision**: Keep both classes separate for now because:
1. Write class has `model_validator` that calls plugin validation
2. Read class includes `last_fetch_at` which is DB-only field
3. Mixing write + read concerns in single class would complicate validation logic

**Action**: Document the difference clearly, no merge.

---

### ✅ Step 10: Standardize Bulk Response Patterns - COMPLETATO

**Goal**: All bulk responses should inherit from `BaseBulkResponse[TResult]` for consistency.

**Base Class Added**: `backend/app/schemas/common.py`

```python
class BaseBulkResponse(BaseModel, Generic[TResult]):
    """
    Standardized base class for all bulk operation responses.
    
    Standard fields:
    - results: List[TResult] - Per-item operation results
    - success_count: int - Number of successful operations
    - errors: List[str] - Operation-level errors (empty list by default)
    
    Computed properties:
    - failed_count: int - Computed as len(results) - success_count
    - total_count: int - Computed as len(results)
    """
    results: List[TResult] = Field(..., description="Per-item operation results")
    success_count: int = Field(..., ge=0, description="Number of successful operations")
    errors: List[str] = Field(default_factory=list, description="Operation-level errors")
    
    @property
    def failed_count(self) -> int:
        return len(self.results) - self.success_count
```

**Files to Update**:

1. **FABulkAssetCreateResponse** (assets.py):
   ```python
   class FABulkAssetCreateResponse(BaseBulkResponse[FAAssetCreateResult]):
       """Response for bulk asset creation."""
       pass  # Inherits all fields from base
   ```

2. **FABulkAssetDeleteResponse** (assets.py):
   ```python
   class FABulkAssetDeleteResponse(BaseBulkResponse[FAAssetDeleteResult]):
       """Response for bulk asset deletion."""
       pass
   ```

3. **FABulkAssetPatchResponse** (assets.py):
   ```python
   class FABulkAssetPatchResponse(BaseBulkResponse[FAAssetPatchResult]):
       """Response for bulk asset patch."""
       pass
   ```

4. **FABulkMetadataRefreshResponse** (assets.py):
   ```python
   class FABulkMetadataRefreshResponse(BaseBulkResponse[FAMetadataRefreshResult]):
       """Response for bulk metadata refresh."""
       pass
   ```

5. **FABulkAssignResponse** (provider.py):
   ```python
   class FABulkAssignResponse(BaseBulkResponse[FAProviderAssignmentResult]):
       """Response for bulk provider assignment."""
       pass
   ```

6. **FABulkRemoveResponse** (provider.py):
   ```python
   class FABulkRemoveResponse(BaseBulkResponse[FAProviderRemovalResult]):
       """Response for bulk provider removal."""
       pass
   ```

7. **FABulkUpsertResponse** (prices.py):
   ```python
   class FABulkUpsertResponse(BaseBulkResponse[FAUpsertResult]):
       """Response for bulk price upsert."""
       # Add specific fields for upsert operations
       inserted_count: int = Field(..., description="Number of prices inserted")
       updated_count: int = Field(..., description="Number of prices updated")
   ```

8. **FABulkDeleteResponse** (prices.py):
   ```python
   class FABulkDeleteResponse(BaseBulkResponse[FAPriceDeleteResult]):
       """Response for bulk price deletion."""
       # Add specific field for deletion count
       deleted_count: int = Field(..., description="Total number of prices deleted")
   ```

9. **FABulkRefreshResponse** (refresh.py):
   ```python
   class FABulkRefreshResponse(BaseBulkResponse[FARefreshResult]):
       """Response for bulk price refresh."""
       pass
   ```

10. **FXBulkUpsertResponse** (fx.py):
    ```python
    class FXBulkUpsertResponse(BaseBulkResponse[FXUpsertResult]):
        """Response for bulk FX rate upsert."""
        pass  # success_count inherited from base
    ```

11. **FXBulkDeleteResponse** (fx.py):
    ```python
    class FXBulkDeleteResponse(BaseBulkResponse[FXDeleteResult]):
        """Response for bulk FX rate deletion."""
        # Add specific field
        total_deleted: int = Field(..., description="Total rates deleted")
    ```

12. **FXConvertResponse** (fx.py):
    ```python
    class FXConvertResponse(BaseBulkResponse[FXConversionResult]):
        """Response for bulk currency conversion."""
        pass
    ```

13. **FXCreatePairSourcesResponse** (fx.py):
    ```python
    class FXCreatePairSourcesResponse(BaseBulkResponse[FXPairSourceResult]):
        """Response for bulk pair source creation."""
        # Can add error_count as stored field if needed
        error_count: int = Field(0, description="Number of failed operations")
    ```

14. **FXDeletePairSourcesResponse** (fx.py):
    ```python
    class FXDeletePairSourcesResponse(BaseBulkResponse[FXDeletePairSourceResult]):
        """Response for bulk pair source deletion."""
        total_deleted: int = Field(..., description="Total records deleted")
    ```

**Benefits**:
- ✅ Consistent API contracts across all bulk operations
- ✅ `failed_count` always available as computed property
- ✅ Single source of truth for bulk response structure
- ✅ Easy to extend with operation-specific fields
- ✅ Type-safe with Generic[TResult]

**Migration Notes**:
- Existing response classes should extend `BaseBulkResponse[TheirResultType]`
- Remove explicit `failed_count` field declarations (now computed property)
- Keep operation-specific fields (inserted_count, updated_count, deleted_count, etc.)
- Import `BaseBulkResponse` from `backend.app.schemas.common`

---

### ✅ Step 11: Update All API Endpoints - COMPLETATO

**Files modified**: `backend/app/api/v1/assets.py`, `backend/app/api/v1/fx.py`

**Changes completed in previous steps**:
1. ✅ All endpoints now accept `List[ItemType]` directly (Steps 1-5)
2. ✅ Wrapper class imports removed
3. ✅ Request body documentation updated
4. ✅ Response models updated to use BaseBulkResponse (Step 10)

**Note**: Service layer calls may need adjustments for:
- DateRangeModel handling (FX operations)
- success_count population (FXConvertResponse now requires it)
- deleted_count consistency (FAPriceDeleteResult)

These will be addressed in Step 12 (Service Layer Updates).

---

### Step 12: Update Service Layer
```python
# OLD
@asset_router.post("", response_model=FABulkAssetCreateResponse)
async def create_assets_bulk(
    request: FABulkAssetCreateRequest,
    session: AsyncSession = Depends(get_session_generator)
):
    return await AssetCRUDService.create_assets_bulk(request.assets, session)

# NEW
@asset_router.post("", response_model=FABulkAssetCreateResponse)
async def create_assets_bulk(
    assets: List[FAAssetCreateItem],
    session: AsyncSession = Depends(get_session_generator)
):
    return await AssetCRUDService.create_assets_bulk(assets, session)
```

---

### ✅ Step 12: Update Service Layer - COMPLETATO (con TODO per implementazione futura)

**Files to modify**:
- `backend/app/services/asset_crud.py`
- `backend/app/services/asset_source.py`  
- `backend/app/services/fx.py`
- `backend/app/services/asset_metadata.py`

**Status**: Schema changes complete, service implementations will be updated during testing phase.

**TODO for Service Layer** (to be done during test updates - Step 13):

**✅ TODO comments added to service files** for tracking during implementation:
- ✅ `backend/app/services/fx.py` - 6 TODO items documented
- ✅ `backend/app/services/asset_crud.py` - 3 TODO items documented
- ✅ `backend/app/services/asset_source.py` - 6 TODO items documented
- ✅ `backend/app/services/asset_metadata.py` - 1 TODO item documented

1. **FX Service** (`fx.py`):
   - Update `convert_currency` to handle `FXConversionRequest.date_range: DateRangeModel`
   - Update `delete_rates_bulk` to handle `FXDeleteItem.date_range: DateRangeModel`
   - Update all methods constructing `FXDeleteResult` to use `date_range: DateRangeModel`
   - Update `FXSyncResponse` construction to use `DateRangeModel` instead of tuple
   - Update `FXConvertResponse`: Add success_count calculation (required by BaseBulkResponse)
   - Update `FXBulkDeleteResponse`: Use 'total_deleted' instead of 'deleted_count'

2. **Price Service** (`asset_source.py` or price operations):
   - **CRITICAL**: Update `FAPriceDeleteResult` construction: rename `deleted` → `deleted_count`
   - Ensure `success` field is always populated
   - Handle optional `message` field
   - Update `FABulkDeleteResponse`: Use 'total_deleted' (from BaseBulkDeleteResponse)

3. **Asset CRUD Service** (`asset_crud.py`):
   - Update `FAAssetDeleteResult` construction: ensure `deleted_count` is 0 or 1
   - Populate `success_count` in all bulk responses (now required by BaseBulkResponse)

4. **Provider Service** (`asset_source.py`):
   - Update `FAProviderRemovalResult` construction: ensure `deleted_count` is 0 or 1
   - Populate `success_count` in FABulkAssignResponse and FABulkRemoveResponse

5. **Metadata Service** (`asset_metadata.py`):
   - Update `FABulkMetadataRefreshResponse`: Populate success_count

6. **Refresh Service** (`asset_source.py`):
   - Update `FARefreshItem` to use `date_range: DateRangeModel` instead of start_date/end_date
   - Populate `success_count` in `FABulkRefreshResponse`

**Approach**: These changes will be validated and fixed when running tests (Step 13), allowing test failures to guide the exact service changes needed.

---

### Step 13: Update All Tests - VEDERE PIANO UNIFICATO

**⚠️ IMPORTANTE**: I test vanno aggiornati usando il piano unificato che include tutti i cambi di piano 05 + 05b.

📄 **Piano Unificato Test**: `05c_plan-testUpdates.prompt.md`

**Perché un piano separato?**
- Consolida test updates per piano 05 (datamodel refactoring) + piano 05b (schema cleanup)
- Evita di dover aggiornare i test due volte
- Fornisce checklist completa e ordinata

**Modifiche da piano 05b da riflettere nei test**:
- ✅ Rimozione wrapper classes (16 classi)
- ✅ DateRangeModel integration (5 schema)
- ✅ FAPricePoint consolidation
- ✅ BaseBulkResponse structure validation

**Modifiche da piano 05 da riflettere nei test**:
- ✅ Asset model changes (removed identifier, added icon_url)
- ✅ AssetProviderAssignment model (added identifier/identifier_type)
- ✅ Provider method signatures (identifier_type parameter)
- ✅ Endpoint changes (PATCH /assets, provider/refresh)

**Step nel piano test**:
1. Update Fixture and Setup Code
2. Update Asset CRUD Tests
3. Update Provider Assignment Tests
4. Update Price Operation Tests
5. Update FX Operation Tests
6. Update Provider List Tests
7. Update Scheduled Investment Tests
8. Update Metadata/Refresh Tests
9. Update Response Validation
10. Update Mock Data and Factories

**Non procedere** con questo step senza aver consultato il piano unificato `12_plan-testUpdates.prompt.md`.

---

## 📊 Summary of Changes

### Classes to Remove (16 total):
1. FAProvidersResponse
2. FXProvidersResponse (provider.py)
3. FXProvidersResponse (fx.py - duplicate)
4. FABulkAssignRequest
5. FABulkRemoveRequest
6. FABulkAssetCreateRequest
7. FABulkPatchMetadataRequest
8. FXConvertRequest
9. FXBulkUpsertRequest
10. FXBulkDeleteRequest
11. FXCreatePairSourcesRequest
12. FXDeletePairSourcesRequest
13. FABulkUpsertRequest
14. FAPriceBulkDeleteRequest
15. FABulkRefreshRequest
16. FAUpsertItem (merged into FAPricePoint)

### Classes to Modify with DateRangeModel (5 total):
1. FXConversionRequest
2. FXDeleteItem
3. FXDeleteResult
4. FXSyncResponse
5. FARefreshItem

### Classes to Keep (with documentation update):
- FAProviderAssignmentItem (write)
- FAProviderAssignmentReadItem (read)
- Rationale documented in Step 9

### Files to Modify:
- **Schemas**: 6 files (provider.py, assets.py, fx.py, prices.py, refresh.py, common.py)
- **API**: 2 files (assets.py, fx.py)
- **Services**: 3 files (asset_crud.py, asset_source.py, fx.py)
- **Tests**: ~20+ test files

### Breaking Changes:
- ✅ All POST/DELETE endpoints accepting wrapper classes
- ✅ All GET endpoints returning wrapper classes
- ✅ Request/response JSON structure changes

### Benefits:
- 🎯 Reduced code duplication
- 🎯 Simpler API contracts
- 🎯 Consistent use of DateRangeModel
- 🎯 Fewer classes to maintain
- 🎯 More Pythonic (direct list parameters)

---

## 🔗 Integration with Main Plan

**This plan should be executed BEFORE Step 12** of the main plan (`05_plan-datamodelProviderRefactoring.prompt.md`).

**Reason**: Test updates (Step 12) should work with the cleaned-up schema structure, avoiding double work.

**Suggested Order**:
1. Complete Steps 1-11 of main plan ✅
2. **Execute this cleanup plan (05b)** 
3. Continue with Step 12 of main plan (test updates)

---

## ⚠️ Important Notes

1. **No Retrocompatibility**: As agreed, we're in pre-alpha, direct breaking changes are acceptable
2. **Database**: No migration needed, these are schema-only changes
3. **Documentation**: Update OpenAPI docs will happen automatically via FastAPI
4. **Frontend**: Frontend will need updates if already consuming these endpoints
5. **DateRangeModel Validation**: Already has `end >= start` validation built-in

---

## 🚀 Execution Priority

**High Priority** (Most Impact):
- Steps 1-5: Remove wrapper request classes (major simplification)
- Step 8: Consolidate FAPricePoint and FAUpsertItem (removes duplication)

**Medium Priority**:
- Steps 6-7: DateRangeModel integration (consistency)
- Steps 11-12: Update endpoints and services

**Low Priority** (Nice to Have):
- Step 10: Standardize response patterns (consistency, not functionality)

**Final Step**:
- Step 13: Update all tests (must be done last)

