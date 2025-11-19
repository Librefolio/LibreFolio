# Phase 5.1: FA Metadata & Classification + Provider Integration - Implementation Checklist

**Reference**: `specifiche_fase_5-1.md`  
**Project**: LibreFolio - Asset Metadata Management  
**Start Date**: November 19, 2025  
**Estimated Duration**: 4-6 days  
**Status**: 🔴 **NOT STARTED**

---

## 📌 High-Level Overview

**Goal**: Implement comprehensive asset metadata management with:
- Classification parameters (geographic_area, investment_type)
- Provider metadata auto-populate on assignment
- Bulk-first API pattern with partial success support
- Pydantic schema validation (NO inline models)
- Normalization utilities (pycountry, Decimal quantization)

**Key Principles**:
- ✅ Reuse existing code before creating new (schemas, services, utilities)
- ✅ Bulk-first: Primary endpoints are bulk, singles call bulk with 1 item
- ✅ Partial success: Independent operations report per-item results
- ✅ Block validation: classification_params.geographic_area is indivisible
- ✅ Pydantic v2: All schemas in `backend/app/schemas/`, FA prefix convention

---

## Phase 0: Pre-Implementation Analysis (1 day)

### 0.1 Code Audit & Reuse Identification

- [ ] **Audit existing Pydantic schemas** (`backend/app/schemas/`)
  - File: Check `assets.py`, `provider.py`, `prices.py`, `common.py`
  - Look for: Bulk request/response patterns, asset ID lists, result per-item structures
  - Document: List reusable schemas and where they're used
  - **Action**: Create `SCHEMA_REUSE_ANALYSIS.md` in dev journal

- [ ] **Audit decimal/numeric utilities** (`backend/app/utils/`)
  - File: Check `decimal_utils.py`, `financial_math.py`
  - Look for: `parse_decimal_value()`, `truncate_to_db_precision()`, quantization logic
  - Document: Available utility functions and their signatures
  - **Action**: Note in `SCHEMA_REUSE_ANALYSIS.md`

- [ ] **Audit normalization patterns**
  - Files: Check services (`asset_source.py`, `fx.py`) for existing normalization
  - Look for: Country mapping, currency normalization, weight distributions
  - Document: Patterns that can be extended for geographic_area
  - **Action**: Note reusable patterns

- [ ] **Check pycountry availability**
  - Command: `pipenv graph | grep pycountry`
  - If missing: Add to Pipfile: `pycountry = "*"`
  - Test import: `python -c "import pycountry; print(pycountry.countries.get(alpha_2='IT'))"`

---

## Phase 1: Database Schema Updates (1 day)

### 1.1 Asset Model Extensions

- [ ] **Add classification_params field to Asset model**
  - File: `backend/app/db/models.py` (class Asset, ~line 328)
  - Add after `interest_schedule`:
    ```python
    # Classification and metadata (JSON TEXT)
    # Structure: {
    #   "investment_type": "stock" | "etf" | "bond" | etc.,
    #   "short_description": "Brief asset description",
    #   "geographic_area": {"USA": 0.60, "EUR": 0.30, "GBR": 0.10},  # ISO-3166-A3, sum=1.0
    #   "sector": "Technology" | "Healthcare" | etc.  # Optional
    # }
    classification_params: Optional[str] = Field(default=None, sa_column=Column(Text))
    ```
  - **Note**: JSON as TEXT for flexibility, validated via Pydantic when loaded

- [ ] **Update Asset docstring**
  - Add section documenting `classification_params` structure
  - Note: geographic_area uses ISO-3166-A3 codes, weights must sum to 1.0
  - Note: Validation via Pydantic schemas (to be created in Phase 2)

### 1.2 Direct Schema Update (Pre-Beta: No Alembic Migration)

**Note**: Since we're in pre-beta phase, we modify `001_initial.py` directly instead of creating a new migration.

- [ ] **Update 001_initial.py to add classification_params column**
  - File: `backend/alembic/versions/001_initial.py`
  - Find the `op.create_table('assets', ...)` section
  - Add column after `interest_schedule`:
    ```python
    sa.Column('classification_params', sa.Text(), nullable=True),
    ```
  - **Location**: After line with `interest_schedule` column definition

- [ ] **Recreate databases from scratch**
  - Test DB: 
    ```bash
    rm backend/data/sqlite/test_app.db
    ./dev.sh db:upgrade backend/data/sqlite/test_app.db
    ```
  - Prod DB:
    ```bash
    rm backend/data/sqlite/app.db
    ./dev.sh db:upgrade backend/data/sqlite/app.db
    ```
  - Verify column: `sqlite3 backend/data/sqlite/test_app.db "PRAGMA table_info(assets)"`
  - **Expected**: Column `classification_params` with type TEXT, nullable=1

- [ ] **Update schema validation test**
  - File: `backend/test_scripts/test_db/db_schema_validate.py`
  - Should auto-detect new column (dynamic test)
  - Run: `./test_runner.py db validate`
  - **Expected**: PASS (new column detected and validated)

---

## Phase 2: Pydantic Schemas (2 days)

**Priority**: Define ALL schemas BEFORE implementing API endpoints

### 2.1 Review Existing Schemas (Reuse Analysis)

- [ ] **Document existing bulk patterns**
  - Files: `schemas/provider.py`, `schemas/prices.py`, `schemas/refresh.py`
  - Identify: `FABulkAssignRequest`, `FABulkUpsertRequest`, result structures
  - Pattern: `{ "assets": [...] }` or `{ "asset_ids": [...] }`
  - Pattern: Result = `{ "asset_id": int, "success": bool, "message": str, ... }`
  - **Action**: Create reusable base classes if patterns are identical

### 2.2 Geographic Area & Classification Schemas

- [ ] **Create geographic area utility module**
  - File: `backend/app/utils/geo_normalization.py` (NEW)
  - Functions to implement:
    1. `normalize_country_to_iso3(input: str) -> str` - Use pycountry to map name/ISO2/ISO3 to ISO-3166-A3
    2. `parse_decimal_weight(value: int | float | str | Decimal) -> Decimal` - Convert any numeric to Decimal
    3. `validate_and_normalize_geographic_area(data: dict[str, Any]) -> dict[str, Decimal]` - Full pipeline:
       - Map all countries to ISO-3166-A3
       - Parse all weights to Decimal
       - Check sum tolerance (abs(sum - 1) <= 1e-6)
       - Quantize to 4 decimals (ROUND_HALF_EVEN)
       - Renormalize on smallest weight if sum != 1.0
       - Return validated dict or raise ValueError with details
  - **Imports**: `pycountry`, `decimal.Decimal`, `typing`

- [ ] **Create tests for geo_normalization**
  - File: `backend/test_scripts/test_utilities/test_geo_normalization.py` (NEW)
  - Test cases:
    1. Valid ISO-3166-A3 codes (USA, GBR, ITA)
    2. ISO-2 to ISO-3 conversion (US → USA, GB → GBR)
    3. Country names to ISO-3 (United States → USA, Italy → ITA)
    4. Invalid country → raises ValueError
    5. Weights as strings → converts to Decimal
    6. Sum within tolerance → quantizes correctly
    7. Sum out of tolerance → renormalizes on smallest weight
    8. Sum too far (e.g., 0.5 total) → raises ValueError
  - Run: `./test_runner.py utils geo-normalization`

- [ ] **Create GeographicArea Pydantic model**
  - File: `backend/app/schemas/assets.py` (UPDATE)
  - Model:
    ```python
    class GeographicAreaModel(BaseModel):
        """Geographic area distribution (ISO-3166-A3, weights sum to 1.0).
        
        Example: {"USA": 0.60, "EUR": 0.30, "GBR": 0.10}
        """
        model_config = ConfigDict(extra="forbid")
        
        # Dynamic dict of ISO-3166-A3 codes to Decimal weights
        # Validation happens via root_validator
        __root__: dict[str, Decimal]
        
        @field_validator('__root__')
        @classmethod
        def validate_geographic_area(cls, v):
            from backend.app.utils.geo_normalization import validate_and_normalize_geographic_area
            return validate_and_normalize_geographic_area(v)
    ```

- [ ] **Create ClassificationParams Pydantic model**
  - File: `backend/app/schemas/assets.py` (UPDATE)
  - Model:
    ```python
    class ClassificationParamsModel(BaseModel):
        """Asset classification metadata.
        
        All fields optional (partial updates supported).
        geographic_area is indivisible block (full replace on update).
        """
        model_config = ConfigDict(extra="forbid")
        
        investment_type: Optional[str] = Field(None, description="Investment type (stock, etf, bond, etc.)")
        short_description: Optional[str] = Field(None, max_length=500, description="Brief description")
        geographic_area: Optional[dict[str, Decimal]] = Field(None, description="Geographic distribution (ISO-3166-A3, sum=1.0)")
        sector: Optional[str] = Field(None, max_length=100, description="Sector classification")
        
        @field_validator('geographic_area')
        @classmethod
        def validate_geo_area(cls, v):
            if v is None:
                return None
            from backend.app.utils.geo_normalization import validate_and_normalize_geographic_area
            return validate_and_normalize_geographic_area(v)
    ```

### 2.3 Metadata PATCH Request/Response Schemas

- [ ] **Create PATCH metadata request schema**
  - File: `backend/app/schemas/assets.py` (UPDATE)
  - Model:
    ```python
    class PatchAssetMetadataRequest(BaseModel):
        """PATCH metadata request (partial update).
        
        Rules:
        - Absent fields: ignored (no update)
        - null/"": clear field
        - geographic_area: full block replace (no merge)
        """
        model_config = ConfigDict(extra="forbid")
        
        investment_type: Optional[str] = None
        short_description: Optional[str] = None
        geographic_area: Optional[dict[str, Decimal] | None] = None  # None = ignore, null in JSON = clear
        sector: Optional[str] = None
    ```

- [ ] **Create metadata response schemas**
  - File: `backend/app/schemas/assets.py` (UPDATE)
  - Models:
    ```python
    class AssetMetadataResponse(BaseModel):
        """Asset with metadata fields."""
        asset_id: int
        display_name: str
        identifier: str
        currency: str
        classification_params: Optional[ClassificationParamsModel] = None
        
    class MetadataChangeDetail(BaseModel):
        """Single field change."""
        field: str
        old_value: Any
        new_value: Any
        
    class MetadataRefreshResult(BaseModel):
        """Result of metadata refresh for single asset."""
        asset_id: int
        success: bool
        message: str
        changes: Optional[list[MetadataChangeDetail]] = None
        warnings: Optional[list[str]] = None
    ```

### 2.4 Bulk Read Schemas

- [ ] **Create bulk asset read request**
  - File: `backend/app/schemas/assets.py` (UPDATE)
  - Check if `BulkAssetIdsRequest` already exists in provider.py or prices.py
  - If exists: **REUSE**, add to assets.py imports
  - If not: Create:
    ```python
    class BulkAssetReadRequest(BaseModel):
        """Request to read multiple assets by IDs."""
        model_config = ConfigDict(extra="forbid")
        
        asset_ids: list[int] = Field(..., min_length=1, max_length=1000, description="Asset IDs to fetch")
    ```

- [ ] **Create bulk metadata refresh request/response**
  - File: `backend/app/schemas/assets.py` (UPDATE)
  - Models:
    ```python
    class BulkMetadataRefreshRequest(BaseModel):
        """Bulk metadata refresh request."""
        model_config = ConfigDict(extra="forbid")
        
        asset_ids: list[int] = Field(..., min_length=1, max_length=100, description="Assets to refresh")
        
    class BulkMetadataRefreshResponse(BaseModel):
        """Bulk metadata refresh response (partial success)."""
        results: list[MetadataRefreshResult]
        success_count: int
        failed_count: int
    ```

### 2.5 Provider Metadata Fetch Schema

- [ ] **Define provider metadata return structure**
  - File: Add docstring to `AssetSourceProvider` abstract class
  - New method signature (to be implemented by providers):
    ```python
    async def fetch_asset_metadata(
        self,
        identifier: str,
        provider_params: dict | None = None
    ) -> dict | None:
        """Fetch metadata from provider (optional, not all providers support this).
        
        Returns:
            dict with keys: investment_type, short_description, geographic_area, sector
            Or None if provider doesn't support metadata or asset not found
            
        Note: 
        - Plugin returns RAW data (no normalization side effects)
        - Core handles normalization/validation/persistence
        """
        return None  # Default: no metadata support
    ```

### 2.6 Schema Export Updates

- [ ] **Update schemas/__init__.py**
  - File: `backend/app/schemas/__init__.py`
  - Add exports:
    ```python
    from backend.app.schemas.assets import (
        # ...existing...
        GeographicAreaModel,
        ClassificationParamsModel,
        PatchAssetMetadataRequest,
        AssetMetadataResponse,
        MetadataChangeDetail,
        MetadataRefreshResult,
        BulkAssetReadRequest,
        BulkMetadataRefreshRequest,
        BulkMetadataRefreshResponse,
    )
    ```
  - Update `__all__` list

---

## Phase 3: Core Service Layer (2 days)

### 3.1 Metadata Normalization Service

- [ ] **Create metadata service module**
  - File: `backend/app/services/asset_metadata.py` (NEW)
  - Class: `AssetMetadataService` (static methods)

- [ ] **Implement parse_classification_params()**
  - Signature: `@staticmethod def parse_classification_params(json_str: Optional[str]) -> ClassificationParamsModel | None`
  - Logic:
    1. If `json_str` is None or empty → return None
    2. Parse JSON → dict
    3. Validate with `ClassificationParamsModel(**data)`
    4. Return validated model
  - **Reuse**: Import geo_normalization utilities
  - Raises: ValueError with details if validation fails

- [ ] **Implement serialize_classification_params()**
  - Signature: `@staticmethod def serialize_classification_params(model: ClassificationParamsModel | None) -> str | None`
  - Logic:
    1. If model is None → return None
    2. Convert to dict: `model.model_dump(exclude_none=True)`
    3. Serialize to JSON: `json.dumps(data)`
    4. Return JSON string

- [ ] **Implement compute_metadata_diff()**
  - Signature: `@staticmethod def compute_metadata_diff(old: ClassificationParamsModel | None, new: ClassificationParamsModel | None) -> list[MetadataChangeDetail]`
  - Logic:
    1. Compare old vs new field by field
    2. Track changes: `{ field, old_value, new_value }`
    3. Return list of changes
  - Special handling for geographic_area (dict comparison)

- [ ] **Implement apply_partial_update()**
  - Signature: `@staticmethod def apply_partial_update(current: ClassificationParamsModel | None, patch: PatchAssetMetadataRequest) -> ClassificationParamsModel`
  - Logic (PATCH semantics):
    1. Start with current params (or empty if None)
    2. For each field in patch:
       - **Not present** in patch dict (absent key) → **ignore**, keep current
       - **null in JSON** (None in Python) → **clear** field
       - **Value present** → **update** field
    3. Special: geographic_area is **full replace** (no merge)
    4. Validate result with `ClassificationParamsModel`
    5. Return updated model
  - **Note**: Use `patch.model_dump(exclude_unset=True)` to distinguish absent vs null

### 3.2 Provider Integration in AssetSourceManager

- [ ] **Update bulk_assign_providers() for auto-populate**
  - File: `backend/app/services/asset_source.py` (UPDATE, ~line 250)
  - After each successful assignment:
    1. Call `provider.fetch_asset_metadata(identifier, provider_params)`
    2. If metadata returned:
       - Normalize via `AssetMetadataService`
       - Compute diff
       - Persist to `asset.classification_params`
       - Add `metadata_changes` to result dict
    3. If metadata is None or provider doesn't support → skip (no error)
  - **Logging**: Use structlog to log metadata auto-populate events
  - **Reuse**: Import `AssetMetadataService` methods

- [ ] **Create manual refresh method**
  - File: `backend/app/services/asset_source.py` (UPDATE)
  - Method: `@staticmethod async def refresh_asset_metadata(asset_id: int, session: AsyncSession) -> dict`
  - Logic:
    1. Load asset + provider assignment
    2. If no provider → return `{ success: False, message: "No provider assigned" }`
    3. Get provider instance
    4. Call `fetch_asset_metadata()`
    5. If None → return `{ success: False, message: "Provider doesn't support metadata" }`
    6. Normalize, compute diff, persist
    7. Return `{ success: True, message: "...", changes: [...] }`

- [ ] **Create bulk refresh method**
  - File: `backend/app/services/asset_source.py` (UPDATE)
  - Method: `@staticmethod async def bulk_refresh_metadata(asset_ids: list[int], session: AsyncSession) -> dict`
  - Logic:
    1. For each asset_id: call `refresh_asset_metadata()`
    2. Collect results (partial success)
    3. Return `{ results: [...], success_count: N, failed_count: M }`
  - **Optimization**: Can be parallelized with `asyncio.gather()`

### 3.3 PATCH Metadata Service Method

- [ ] **Create update_asset_metadata() method**
  - File: `backend/app/services/asset_metadata.py` (UPDATE)
  - Method: `@staticmethod async def update_asset_metadata(asset_id: int, patch: PatchAssetMetadataRequest, session: AsyncSession) -> AssetMetadataResponse`
  - Logic:
    1. Load asset from DB
    2. Parse current `classification_params`
    3. Apply patch via `apply_partial_update()`
    4. Validate result (geographic_area block validation)
    5. Serialize back to JSON
    6. Update asset.classification_params
    7. Commit transaction
    8. Return `AssetMetadataResponse`
  - Error handling: 422 if geographic_area validation fails

---

## Phase 4: Provider Plugin Updates (1 day)

### 4.1 Update Existing Providers (Optional Metadata Support)

**Note**: Metadata fetch is OPTIONAL. Not all providers need to implement it.

- [ ] **YahooFinance: Add fetch_asset_metadata()**
  - File: `backend/app/services/asset_source_providers/yahoo_finance.py`
  - Implementation:
    ```python
    async def fetch_asset_metadata(self, identifier: str, provider_params: dict | None = None) -> dict | None:
        """Fetch metadata from Yahoo Finance (sector, description, etc.)."""
        try:
            ticker = yf.Ticker(identifier)
            info = ticker.info
            
            return {
                "investment_type": "stock",  # Could map from info.get('quoteType')
                "short_description": info.get('longBusinessSummary', '')[:500],
                "sector": info.get('sector'),
                # geographic_area: Not available from yfinance
            }
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier}: {e}")
            return None
    ```

- [ ] **CSS Scraper: Add fetch_asset_metadata() stub**
  - File: `backend/app/services/asset_source_providers/css_scraper.py`
  - Return None (not supported for manual/CSV providers)

- [ ] **ScheduledInvestment: Add fetch_asset_metadata() stub**
  - File: `backend/app/services/asset_source_providers/scheduled_investment.py`
  - Return None (synthetic provider, no external metadata)

- [ ] **MockProv: Add fetch_asset_metadata() for testing**
  - File: `backend/app/services/asset_source_providers/mockprov.py`
  - Return mock data for test cases:
    ```python
    {
        "investment_type": "stock",
        "short_description": "Mock test asset",
        "geographic_area": {"USA": "0.6", "ITA": "0.4"},  # Test string parsing
        "sector": "Technology"
    }
    ```

---

## Phase 5: API Endpoints Implementation (2 days)

### 5.1 Metadata Management Endpoints

- [ ] **PATCH /api/v1/assets/{asset_id}/metadata (NEW)**
  - File: `backend/app/api/v1/assets.py` (UPDATE)
  - Endpoint:
    ```python
    @router.patch("/{asset_id}/metadata", response_model=AssetMetadataResponse)
    async def update_asset_metadata(
        asset_id: int,
        patch: PatchAssetMetadataRequest,
        session: AsyncSession = Depends(get_session_generator)
    ):
        """Update asset metadata (partial update, PATCH semantics).
        
        Rules:
        - Absent fields: ignored
        - null: clear field
        - geographic_area: full block replace (validated as unit)
        """
        try:
            result = await AssetMetadataService.update_asset_metadata(asset_id, patch, session)
            return result
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating metadata for asset {asset_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    ```

- [ ] **POST /api/v1/assets (bulk read) (MODIFY EXISTING or NEW)**
  - File: `backend/app/api/v1/assets.py` (UPDATE)
  - Check if `GET /api/v1/assets/{asset_id}` exists
  - Create new bulk endpoint:
    ```python
    @router.post("", response_model=list[AssetMetadataResponse])  # Note: POST to /api/v1/assets (no trailing slash)
    async def read_assets_bulk(
        request: BulkAssetReadRequest,
        session: AsyncSession = Depends(get_session_generator)
    ):
        """Read multiple assets with metadata (bulk-first pattern)."""
        try:
            assets = await session.execute(
                select(Asset).where(Asset.id.in_(request.asset_ids))
            )
            assets = assets.scalars().all()
            
            return [
                AssetMetadataResponse(
                    asset_id=asset.id,
                    display_name=asset.display_name,
                    identifier=asset.identifier,
                    currency=asset.currency,
                    classification_params=AssetMetadataService.parse_classification_params(
                        asset.classification_params
                    )
                )
                for asset in assets
            ]
        except Exception as e:
            logger.error(f"Error reading assets bulk: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    ```

- [ ] **POST /api/v1/assets/{asset_id}/metadata/refresh (NEW)**
  - File: `backend/app/api/v1/assets.py` (UPDATE)
  - Endpoint:
    ```python
    @router.post("/{asset_id}/metadata/refresh", response_model=MetadataRefreshResult)
    async def refresh_asset_metadata_single(
        asset_id: int,
        session: AsyncSession = Depends(get_session_generator)
    ):
        """Force refresh metadata from provider (single asset)."""
        try:
            result = await AssetSourceManager.refresh_asset_metadata(asset_id, session)
            return MetadataRefreshResult(**result)
        except Exception as e:
            logger.error(f"Error refreshing metadata for asset {asset_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    ```

- [ ] **POST /api/v1/assets/metadata/refresh/bulk (NEW, optional but recommended)**
  - File: `backend/app/api/v1/assets.py` (UPDATE)
  - Endpoint:
    ```python
    @router.post("/metadata/refresh/bulk", response_model=BulkMetadataRefreshResponse)
    async def refresh_asset_metadata_bulk(
        request: BulkMetadataRefreshRequest,
        session: AsyncSession = Depends(get_session_generator)
    ):
        """Bulk metadata refresh (PRIMARY bulk endpoint, partial success)."""
        try:
            result = await AssetSourceManager.bulk_refresh_metadata(request.asset_ids, session)
            return BulkMetadataRefreshResponse(**result)
        except Exception as e:
            logger.error(f"Error in bulk metadata refresh: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    ```

### 5.2 Provider Assignment Bulk Read Endpoint

- [ ] **POST /api/v1/assets/scraper (NEW - bulk read provider assignments)**
  - File: `backend/app/api/v1/assets.py` (UPDATE)
  - Endpoint:
    ```python
    @router.post("/scraper", response_model=list[dict])
    async def read_provider_assignments_bulk(
        request: BulkAssetReadRequest,
        session: AsyncSession = Depends(get_session_generator)
    ):
        """Read provider assignments for multiple assets."""
        try:
            assignments = await session.execute(
                select(AssetProviderAssignment).where(
                    AssetProviderAssignment.asset_id.in_(request.asset_ids)
                )
            )
            assignments = assignments.scalars().all()
            
            return [
                {
                    "asset_id": a.asset_id,
                    "provider_code": a.provider_code,
                    "provider_params": json.loads(a.provider_params) if a.provider_params else None
                }
                for a in assignments
            ]
        except Exception as e:
            logger.error(f"Error reading provider assignments: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    ```

---

## Phase 6: Testing (2 days)

### 6.1 Unit Tests - Utilities

- [ ] **Test geo_normalization utilities**
  - File: `backend/test_scripts/test_utilities/test_geo_normalization.py`
  - Already created in Phase 2.2
  - Run: `./test_runner.py utils geo-normalization`
  - **Expected**: All tests pass

### 6.2 Unit Tests - Service Layer

- [ ] **Test AssetMetadataService**
  - File: `backend/test_scripts/test_services/test_asset_metadata.py` (NEW)
  - Test cases:
    1. parse_classification_params(): valid JSON → model
    2. parse_classification_params(): None → None
    3. serialize_classification_params(): model → JSON
    4. compute_metadata_diff(): old vs new → changes list
    5. apply_partial_update(): absent fields ignored
    6. apply_partial_update(): null clears field
    7. apply_partial_update(): geographic_area full replace
    8. apply_partial_update(): invalid geographic_area → raises ValueError
  - Run: `./test_runner.py services asset-metadata`

- [ ] **Test provider metadata auto-populate**
  - File: `backend/test_scripts/test_services/test_asset_source.py` (UPDATE)
  - Add test: `test_bulk_assign_providers_with_metadata_autopopulate()`
  - Mock: Use mockprov provider with metadata support
  - Verify: After assignment, asset.classification_params is populated
  - Verify: Metadata changes in result dict
  - Run: `./test_runner.py services asset-source`

### 6.3 Integration Tests - API

- [ ] **Test PATCH metadata endpoint**
  - File: `backend/test_scripts/test_api/test_assets_metadata.py` (NEW)
  - Test cases:
    1. PATCH with valid geographic_area → 200, updated
    2. PATCH with invalid geographic_area → 422, error details
    3. PATCH with absent fields → 200, fields unchanged
    4. PATCH with null → 200, fields cleared
    5. PATCH empty payload → 200, no changes
  - Run: `./test_runner.py api assets-metadata`

- [ ] **Test bulk read assets**
  - File: `backend/test_scripts/test_api/test_assets_metadata.py` (UPDATE)
  - Test: POST /api/v1/assets with asset_ids list
  - Verify: Returns array of AssetMetadataResponse
  - Run: `./test_runner.py api assets-metadata`

- [ ] **Test metadata refresh endpoints**
  - File: `backend/test_scripts/test_api/test_assets_metadata.py` (UPDATE)
  - Test cases:
    1. Single refresh: POST /{asset_id}/metadata/refresh → MetadataRefreshResult
    2. Bulk refresh: POST /metadata/refresh/bulk → partial success
    3. No provider assigned → success=false, appropriate message
    4. Provider doesn't support metadata → success=false
  - Run: `./test_runner.py api assets-metadata`

- [ ] **Test provider assignment bulk read**
  - File: `backend/test_scripts/test_api/test_assets_metadata.py` (UPDATE)
  - Test: POST /api/v1/assets/scraper with asset_ids
  - Verify: Returns provider assignments
  - Run: `./test_runner.py api assets-metadata`

### 6.4 Edge Cases & Error Handling

- [ ] **Test geographic_area edge cases**
  - File: `backend/test_scripts/test_utilities/test_geo_normalization.py` (UPDATE)
  - Cases:
    1. Sum = 0.999999 (within tolerance) → normalized to 1.0
    2. Sum = 1.000001 (within tolerance) → normalized to 1.0
    3. Sum = 0.95 (out of tolerance) → ValueError
    4. Sum = 1.05 (out of tolerance) → ValueError
    5. Single country weight = 1.0 → valid
    6. Empty dict → ValueError (no countries)
    7. Negative weight → ValueError
    8. Zero weight → valid (country with 0% allocation)

- [ ] **Test PATCH semantic edge cases**
  - File: `backend/test_scripts/test_services/test_asset_metadata.py` (UPDATE)
  - Cases:
    1. PATCH with only geographic_area → other fields unchanged
    2. PATCH geographic_area=null → clears existing geographic_area
    3. Multiple PATCHes in sequence → final state correct
    4. Concurrent PATCHes (optimistic locking) → last write wins

---

## Phase 7: Documentation (1 day)

### 7.1 API Documentation

- [ ] **Update OpenAPI/Swagger documentation**
  - Files: Docstrings in `api/v1/assets.py` endpoints
  - Ensure: All new endpoints have comprehensive docstrings
  - Include: Request/response examples with geographic_area

- [ ] **Create API examples document**
  - File: `docs/api-examples/metadata-management.md` (NEW)
  - Sections:
    1. PATCH metadata with geographic_area
    2. Bulk read assets with metadata
    3. Refresh metadata from provider
    4. Read provider assignments
  - Include: cURL examples and expected responses

### 7.2 Developer Documentation

- [ ] **Update database schema documentation**
  - File: `docs/database-schema.md`
  - Add: classification_params field description
  - Add: JSON structure example
  - Add: Validation rules (geographic_area sum=1.0)

- [ ] **Create metadata management guide**
  - File: `docs/metadata-management.md` (NEW)
  - Sections:
    1. Overview (classification_params structure)
    2. Geographic area validation rules
    3. PATCH semantics (absent vs null)
    4. Provider metadata auto-populate
    5. Normalization process (pycountry, Decimal quantization)
    6. Troubleshooting common validation errors

### 7.3 Code Documentation

- [ ] **Add comprehensive docstrings**
  - Files: All new modules/classes/methods
  - Standard: Google-style docstrings
  - Include: Args, Returns, Raises, Examples

- [ ] **Update FEATURE_COVERAGE_REPORT**
  - File: `LibreFolio_developer_journal/FEATURE_COVERAGE_REPORT.md`
  - Add section: Phase 5.1 - Asset Metadata & Classification
  - Include: Features implemented, test coverage, endpoints added

---

## Phase 8: Final Validation & Cleanup (1 day)

### 8.1 End-to-End Testing

- [ ] **Manual E2E test scenario**
  - Start server: `./dev.sh backend`
  - Create asset with yfinance provider
  - Verify metadata auto-populated
  - PATCH metadata with geographic_area
  - Verify changes persisted
  - Bulk read assets → verify metadata returned
  - Refresh metadata → verify updates

- [ ] **Run full test suite**
  - Command: `./test_runner.py all`
  - **Expected**: All tests pass (including new metadata tests)
  - Fix any regressions

### 8.2 Code Quality Checks

- [ ] **Check for inline Pydantic models**
  - Command: `grep -rn "class.*BaseModel" backend/app/api/v1/*.py`
  - **Expected**: 0 results (all schemas in schemas/)

- [ ] **Check import cycles**
  - Test: `python -c "from backend.app.api.v1.assets import router"`
  - **Expected**: No import errors

- [ ] **Check unused imports**
  - Tool: PyCharm inspections or `pylint`
  - **Action**: Remove any unused imports

### 8.3 Performance Validation

- [ ] **Benchmark bulk operations**
  - Test: Bulk read 100 assets with metadata
  - Test: Bulk metadata refresh 50 assets
  - **Target**: < 5 seconds for bulk operations

- [ ] **Check database query count**
  - Enable SQLAlchemy logging
  - Test: Bulk operations should use ≤ 3 queries
  - **Optimization**: Ensure no N+1 query patterns

### 8.4 Documentation Review

- [ ] **Review all new documentation**
  - Check: Spelling, grammar, technical accuracy
  - Check: Examples are executable and correct
  - Check: Links between documents work

- [ ] **Update main README if needed**
  - Add: Mention of metadata management features
  - Add: Link to metadata-management.md guide

---

## Completion Checklist

### Code Completeness
- [ ] All schemas defined in `backend/app/schemas/` (NO inline models)
- [ ] All utilities in `backend/app/utils/`
- [ ] All services in `backend/app/services/`
- [ ] All endpoints in `backend/app/api/v1/`
- [ ] All tests in `backend/test_scripts/`

### Quality Gates
- [ ] All tests passing (utils, services, API)
- [ ] No import cycles
- [ ] No inline Pydantic models in API layer
- [ ] Database migration applied and tested
- [ ] Documentation complete and accurate

### Functional Requirements
- [ ] PATCH metadata with partial update semantics
- [ ] Geographic area validation (ISO-3166-A3, sum=1.0)
- [ ] Provider metadata auto-populate on assignment
- [ ] Bulk operations with partial success support
- [ ] Metadata refresh from provider
- [ ] Bulk read assets and provider assignments

### Non-Functional Requirements
- [ ] Bulk-first API pattern
- [ ] Pydantic v2 with FA prefix
- [ ] Code reuse maximized
- [ ] Performance acceptable (< 5s for bulk ops)
- [ ] Logging comprehensive (structlog)

---

## Success Metrics

**Time Estimate**: 4-6 days (32-48 hours)

**Completion Criteria**:
1. ✅ All 80+ checklist items completed
2. ✅ All tests passing (100% of new tests)
3. ✅ Documentation complete
4. ✅ E2E scenario works end-to-end
5. ✅ Code quality gates passed

**Deliverables**:
- Database schema updated (classification_params column)
- 10+ new Pydantic schemas (reusing existing patterns)
- 3+ utility modules (geo_normalization, metadata service)
- 5+ new API endpoints (PATCH, POST bulk, refresh)
- 50+ test cases (utilities, services, API)
- 5+ documentation files (API examples, guides)

---

**Next Phase**: Phase 5.2 - Advanced Provider Implementations with metadata fetch

