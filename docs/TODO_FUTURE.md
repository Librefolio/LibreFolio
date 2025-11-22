# LibreFolio - Future Improvements TODO

**Last Updated**: November 22, 2025  
**Status**: Pre-Beta Development  
**Priority Scale**: HIGH (critical), MEDIUM (important), LOW (nice-to-have)

---

## 📋 Overview

This document tracks low-priority improvements, optimizations, and enhancements that are not blocking for beta release but would improve code quality, performance, or developer experience.

**Purpose**:
- Document TODOs removed from code during cleanup
- Track technical debt for future refactoring
- Plan performance optimizations
- Collect UX improvements for post-beta phases

---

## 🧹 Cache Management

### Implement Cache Cleanup System

**Priority**: LOW  
**Effort**: 4-6 hours  
**Impact**: Memory optimization

**Description**:
- yfinance provider caches ticker objects indefinitely
- General cache cleanup strategy needed for long-running instances
- Consider TTL-based eviction or LRU cache with size limits

**Related Files**:
- `backend/app/providers/asset/yfinance_provider.py`
- Consider adding `backend/app/utils/cache_utils.py`

**Implementation Ideas**:
- Add `@lru_cache(maxsize=1000)` with TTL
- Periodic cleanup task (e.g., every 24 hours)
- Manual cache clear endpoint for admin use

---

## 🔍 Search Enhancements

### Fuzzy Search for Asset Discovery

**Priority**: LOW  
**Effort**: 2-3 hours  
**Impact**: Better asset discovery UX

**Description**:
- yfinance provider could support fuzzy ticker search
- Help users find assets when exact ticker unknown
- Leverage yfinance's built-in search functionality

**Related Files**:
- `backend/app/providers/asset/yfinance_provider.py`

**Implementation Ideas**:
- Add `search_assets(query: str, limit: int = 10)` method
- New endpoint `GET /api/v1/assets/search?q=apple`
- Return list of potential matches with metadata

---

## 🔌 Provider Improvements

### CSS Scraper Pydantic Params Class

**Priority**: MEDIUM  
**Effort**: 2 hours  
**Impact**: Type safety and validation

**Description**:
- CSS scraper uses untyped `provider_params` dict
- Create Pydantic model for validation and documentation
- Improve IDE autocomplete and error messages

**Related Files**:
- `backend/app/providers/asset/css_scraper.py`
- `backend/app/schemas/provider.py` (new CSSScraperParams class)

**Implementation**:
```python
class CSSScraperParams(BaseModel):
    url: str = Field(..., description="URL to scrape")
    price_selector: str = Field(..., description="CSS selector for price")
    date_selector: Optional[str] = Field(None, description="CSS selector for date")
    date_format: str = Field("%Y-%m-%d", description="Date format string")
    headers: Optional[dict[str, str]] = Field(None, description="HTTP headers")
```

### CSS Scraper HTTP Headers via provider_params

**Priority**: LOW  
**Effort**: 1 hour  
**Impact**: Flexibility for scraping edge cases

**Description**:
- Allow custom HTTP headers per asset (e.g., User-Agent, cookies)
- Some sites block default scraper headers
- Pass headers through provider_params

**Related Files**:
- `backend/app/providers/asset/css_scraper.py`

**Implementation**:
- Add `headers` field to CSSScraperParams (see above)
- Pass headers to requests.get() call
- Document header usage in API examples

---

## 🧪 Testing

### Timezone Handling Verification

**Priority**: MEDIUM  
**Effort**: 2 hours  
**Impact**: Correctness for international users

**Description**:
- yfinance returns prices in market timezone (NYSE, NASDAQ, etc.)
- Verify correct conversion to UTC or user timezone
- Test edge cases (daylight saving time transitions)

**Related Files**:
- `backend/app/providers/asset/yfinance_provider.py`
- `backend/app/utils/datetime_utils.py`
- `backend/test_scripts/test_external/test_yfinance_live.py`

**Test Cases**:
- Fetch price at market close (16:00 EST) → verify UTC timestamp
- Fetch during DST transition → verify no date shift
- Multi-timezone assets (e.g., US + European stocks)

### Additional Test Edge Cases

**Priority**: LOW  
**Effort**: 4-8 hours  
**Impact**: Test coverage completeness

**Description**:
- Stress test bulk operations (1000+ items)
- Test concurrent requests (race conditions)
- Test network failures and retries
- Test partial success scenarios
- Test FX rate backward-fill across leap years

**Related Files**:
- All test files in `backend/test_scripts/`

---

## 💱 FX System

### FED Provider Auto-Config Investigation

**Priority**: MEDIUM  
**Effort**: 3-4 hours  
**Impact**: Fix existing issue or document limitation

**Description**:
- FED provider currently requires manual pair source configuration
- ECB provider auto-discovers pairs from API
- Investigate if FED API supports pair discovery
- If not, document manual configuration requirement

**Related Files**:
- `backend/app/providers/fx/fed_provider.py`
- `docs/fx-implementation.md`

**Investigation Steps**:
1. Review FED API documentation for available pairs endpoint
2. Test if pair discovery is possible programmatically
3. If yes: Implement auto-config like ECB
4. If no: Document manual setup workflow with examples

---

## 📚 Documentation

### Docker Documentation Update

**Priority**: HIGH (when Docker implemented)  
**Effort**: 2 hours  
**Impact**: Deployment ease for users

**Description**:
- Update README.md with Docker setup instructions
- Document environment variable configuration
- Add docker-compose examples
- Document volume mounts for database persistence

**Related Files**:
- `README.md`
- `docs/environment-variables.md` (update)
- `Dockerfile` (to be created)
- `docker-compose.yml` (to be created)

**Wait Until**: Docker image implementation is complete

---

## 🎨 UX Improvements (Post-Phase 4)

### Additional Single-Wrapper Endpoints

**Priority**: HIGH (common operations), MEDIUM (occasional), LOW (rare)  
**Effort**: 2-3 hours total  
**Impact**: Developer UX

**Description**:
Add convenience single-item endpoints for common bulk operations (see Phase 3 analysis).

**HIGH Priority** (implement next):
1. `PATCH /api/v1/assets/{asset_id}/metadata` - Metadata update for single asset
2. `DELETE /api/v1/assets/{asset_id}` - Delete single asset
3. `POST /api/v1/fx/rate-set` - Manual single rate entry
4. `DELETE /api/v1/fx/rate-set` - Delete specific rate by date+pair

**MEDIUM Priority**:
5. `POST /api/v1/fx/sync` - Sync single currency pair for date range
6. `POST /api/v1/fx/pair-sources` - Add single pair source config
7. `DELETE /api/v1/fx/pair-sources/{id}` - Remove single pair source

**Related Files**:
- `backend/app/api/v1/assets.py`
- `backend/app/api/v1/fx.py`

---

## 🏗️ Architecture Improvements

### Standardize Bulk Response Format

**Priority**: LOW  
**Effort**: 3-4 hours  
**Impact**: API consistency

**Description**:
- Most bulk endpoints return `{results: [], success_count, failed_count}`
- Some use different patterns (e.g., FX convert returns flat list)
- Standardize all bulk responses to same structure

**Related Files**:
- All `*Response` models in `backend/app/schemas/`

**Breaking Change**: Yes (requires version bump to v2.0)

---

## 📊 Performance Optimizations

### Database Indexing Review

**Priority**: MEDIUM  
**Effort**: 2-3 hours  
**Impact**: Query performance

**Description**:
- Review all common query patterns
- Add missing indexes on frequently filtered columns
- Test query performance with large datasets (10K+ assets, 1M+ prices)

**Related Files**:
- `backend/app/db/models.py`
- `backend/alembic/versions/*.py` (new migration)

**Columns to Index**:
- `price_history.asset_id, date` (composite for range queries)
- `fx_rates.from_currency, to_currency, date` (composite)
- `assets.currency` (filter queries)
- `assets.active` (filter queries)

---

## 🔐 Security Enhancements

### API Rate Limiting

**Priority**: MEDIUM (before public deployment)  
**Effort**: 3-4 hours  
**Impact**: Prevent abuse

**Description**:
- Add rate limiting middleware (e.g., slowapi)
- Protect bulk endpoints (max 100 items per request)
- Protect external provider calls (respect provider rate limits)

**Related Files**:
- `backend/app/main.py` (add middleware)
- `backend/app/config.py` (rate limit settings)

**Implementation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/v1/assets/list")
@limiter.limit("100/minute")
async def list_assets(...):
    ...
```

---

## 📝 Code Quality

### Centralize Validation Logic (DONE ✅)

**Priority**: MEDIUM  
**Effort**: 1.5 hours  
**Impact**: DRY principle, consistency  
**Status**: ✅ COMPLETED in Phase 4

**Description**:
- Created `backend/app/utils/validation_utils.py` with reusable validators
- Implemented `normalize_currency_code()` for currency uppercase
- Implemented `validate_date_range_order()` for DateRangeModel
- Implemented `validate_compound_frequency()` for interest rate configs

**Completed Actions**:
- ✅ Created validation_utils.py with 3 utility functions
- ✅ Refactored 9 currency validators across 4 schema files
- ✅ Added DateRangeModel validator using utility
- ✅ Refactored 2 compound frequency validators using utility
- ✅ All schemas compile and pass tests

---

## 🔄 Future Phases

### Phase 5: Transaction System

**Priority**: HIGH (core feature)  
**Effort**: 2-3 weeks  
**Planned**: Q1 2026

**Description**:
- Implement transaction CRUD (BUY, SELL, DIVIDEND, etc.)
- FIFO lot matching at runtime
- Cost basis calculation
- Gain/loss tracking
- Portfolio valuation

### Phase 6: Frontend Development

**Priority**: HIGH (user-facing)  
**Effort**: 4-6 weeks  
**Planned**: Q2 2026

**Description**:
- React + TypeScript + MUI
- i18n support (EN, IT, FR, ES)
- Dashboard with charts
- Asset management UI
- Transaction entry forms
- Reports and exports

---

## 📌 Notes

**When to Update This Document**:
- When removing TODO comments from code
- When discovering optimization opportunities
- When users request features (post-beta)
- After each major phase completion

**How to Prioritize**:
- HIGH: Blocking bugs, security, or critical features
- MEDIUM: Quality improvements, user-facing enhancements
- LOW: Optimizations, edge cases, nice-to-haves

**Before Implementing**:
- Review if priority has changed
- Check if dependencies are met
- Estimate current effort (may have changed)
- Create GitHub issue for tracking

---

**End of Document**

