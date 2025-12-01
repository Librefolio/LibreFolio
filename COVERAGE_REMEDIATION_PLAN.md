# API Test Coverage Remediation Plan

**Date**: November 28, 2025  
**Goal**: Increase API test coverage and improve endpoint organization

---

## 1. Assets API - Uncovered Endpoints

### 1.1 GET `/api/v1/assets/providers` ✅ TESTED
**Status**: Never called in tests  
**Action**: Add test in `test_assets_crud.py`
```python
async def test_list_asset_providers():
    """Test GET /assets/providers - List all available asset pricing providers."""
    # Should return list of providers (yfinance, cssscraper, mockprov, scheduled_investment)
    # Verify: provider code, name, description, supports_search
```

**Priority**: Medium (discovery endpoint)

---

### 1.2 DELETE `/api/v1/assets/provider/bulk` ✅ TESTED
**Status**: Never called in tests  
**Action**: Add test in `test_assets_crud.py`
```python
async def test_bulk_remove_providers():
    """Test DELETE /assets/provider/bulk - Remove provider assignments."""
    # 1. Create assets
    # 2. Assign providers
    # 3. Remove providers (bulk)
    # 4. Verify providers removed from DB
```

**Priority**: High (CRUD completeness)

---

### 1.3 DELETE `/api/v1/assets/prices/bulk` ✅ TESTED
**Status**: Never called in tests  
**Action**: Add test in new `test_assets_crud.py`
```python
async def test_bulk_delete_prices():
    """Test DELETE /assets/prices/bulk - Delete price ranges."""
    # 1. Create asset
    # 2. Insert prices
    # 3. Delete price ranges (bulk)
    # 4. Verify prices deleted
```

**Priority**: High (CRUD completeness)

---

### 1.4 POST `/api/v1/assets/{asset_id}/prices` ✅ removed
**Status**: Never called + Single endpoint (should be removed)  
**Action**: **DELETE THIS ENDPOINT**
- Reason: We have bulk endpoint `/prices/bulk`, single is redundant
- Migration: All clients should use bulk with 1 item

**Priority**: High (cleanup)

---


### 1.5 POST `/api/v1/assets/prices-refresh/bulk` ⚠️ TESTED, but need reorganization for return information
**Status**: Never called in tests  
**Action**: Add test in `test_assets_crud.py`
```python
async def test_bulk_refresh_prices():
    """Test POST /assets/prices-refresh/bulk - Refresh prices from providers."""
    # 1. Create assets
    # 2. Assign providers (use mockprov for deterministic results)
    # 3. Refresh prices (bulk)
    # 4. Verify prices inserted
    # 5. Test partial failure (asset without provider)
```

**Priority**: High (provider integration)

---

## 2. FX API - Uncovered Scenarios

### 2.1 POST `/api/v1/fx/sync/bulk` - Auto-config branch ❌ NOT TESTED
**Status**: Only manual config tested, auto-config branch never executed  
**Current test**: Passes explicit `pair_sources` list inside test_fx_api.py
**Missing test**: Call without `pair_sources` → should use auto-discovery

```python
async def test_fx_sync_auto_config():
    """Test POST /fx/sync/bulk with auto-config (no pair_sources)."""
    # 1. Don't pass pair_sources in request body
    # 2. System should auto-discover from registered FX providers
    # 3. Verify rates synced from all providers
```

**Code branch**:
```python
# Line ~200 in fx.py
if not request.pair_sources:
    # Auto-discover from all registered providers
    pair_sources = FXRateProviderRegistry.get_auto_config()
else:
    # Manual config
    pair_sources = request.pair_sources
```

**Priority**: High (default behavior coverage)

---
