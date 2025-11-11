# Asset Pricing System Documentation

Welcome to the LibreFolio Asset Pricing System documentation.

---

## 📚 Documentation Index

### 🏗️ Architecture & Design
- **[Architecture Guide](./architecture.md)** - Complete system architecture, data flow, and design principles
  - Multi-provider system overview
  - Data flow diagrams (refresh, query, manual management)
  - Core components (provider base class, manager, schemas)
  - Database schema
  - Performance optimizations
  - Comparison with FX system

### 👨‍💻 Development Guides
- **[Provider Development Guide](./provider-development.md)** - Step-by-step guide for creating new providers
  - Quick start checklist
  - Minimal provider template
  - Required methods and properties
  - Design patterns (REST API, web scraper, file-based)
  - Error handling best practices
  - Testing strategies
  - Advanced features (caching, rate limiting, retry logic)

### 🔌 Provider Documentation
- **[Scheduled Investment Provider](./scheduled-investment-provider.md)** - Synthetic valuation for fixed-income assets
  - Use cases: crowdfunding loans, bonds, structured products
  - Parameter configuration (face value, interest schedule, late interest)
  - Day count convention (ACT/365) and interest calculation (SIMPLE)
  - API integration examples
  - Best practices and troubleshooting

---

## 🎯 Quick Start

### For Developers Creating New Providers

1. Read the [Provider Development Guide](./provider-development.md)
2. Use the minimal template as a starting point
3. Implement the required methods
4. Test with the provided test scripts
5. Submit a pull request

### For System Architects

1. Start with the [Architecture Guide](./architecture.md)
2. Understand the data flow and design principles
3. Review the comparison with FX system
4. Explore performance optimizations

---

## 🔑 Key Concepts

### Provider System
LibreFolio uses a **plugin-based provider architecture** where each provider:
- Inherits from `AssetSourceProvider` abstract base class
- Auto-registers via `@register_provider(AssetProviderRegistry)` decorator
- Implements methods for fetching current and historical prices
- Can optionally support asset search

### Data Types
- **CurrentValue**: Latest available price with metadata
- **PricePoint**: OHLC data (open/high/low/close) + volume for a single date
- **HistoricalData**: Collection of PricePoints with source information

All schemas are defined as **Pydantic v2 models** in `backend/app/schemas/assets.py`.

### Manager Pattern (Bulk-First)
All operations follow a **bulk-first design**:
- Bulk methods are PRIMARY (optimized for batch operations)
- Single-item methods call bulk internally with 1 element
- Minimizes database queries and maximizes throughput

### Backward-Fill
When price data is missing for a requested date, the system uses the **most recent available price** and adds `backward_fill_info` to indicate:
- `actual_rate_date`: The date of the actual price used
- `days_back`: Number of days back from requested date

### Synthetic Yield
For `SCHEDULED_YIELD` assets (loans, bonds), prices are **calculated at runtime** based on:
- Interest schedule (tiered rates)
- ACT/365 day count convention
- SIMPLE interest calculation
- NOT stored in database (always fresh)

---

## 🧪 Testing

### Service Tests
```bash
# Run all asset source service tests (11 tests)
pipenv run python -m backend.test_scripts.test_services.test_asset_source

# Run refresh smoke test
pipenv run python -m backend.test_scripts.test_services.test_asset_source_refresh
```

### Test Coverage
- Helper functions (precision, truncation, ACT/365)
- Provider assignment (bulk/single assign and remove)
- Price CRUD (bulk/single upsert and delete)
- Backward-fill logic
- Refresh orchestration (concurrency, per-item reporting)

---

## 📊 Current Status (2025-11-10)

### ✅ Completed
- [x] Core service layer (`AssetSourceManager`)
- [x] Pydantic v2 schemas (`CurrentValueModel`, `PricePointModel`, `HistoricalDataModel`)
- [x] Abstract base class (`AssetSourceProvider`)
- [x] Provider registry with auto-discovery
- [x] Backward-fill logic
- [x] Synthetic yield calculation (ACT/365, SIMPLE interest)
- [x] Refresh orchestration with concurrency control
- [x] Test suite (11/11 tests passing)
- [x] Architecture documentation
- [x] Provider development guide
- [x] **Database schema**: Added `fetch_interval` to `asset_provider_assignments` (2025-11-10)
- [x] **API endpoints**: 12 REST endpoints implemented (bulk-first pattern) (2025-11-10)
- [x] **yfinance** - Yahoo Finance (stocks, ETFs) ✅ *Fixed 2025-11-10*

### 🔧 Providers Implemented
- [x] **yfinance** - Yahoo Finance (stocks, ETFs) ⚠️ *Import fix needed*
- None currently
- `yahoo_finance.py` imports deprecated names from `asset_source.py`
  - Should import from `schemas.assets` as `*Model`
- [ ] Advanced refresh tests (provider fallback, per-item errors, concurrency)
  - Price query endpoints
- [ ] CSS Scraper provider
- [ ] Advanced refresh tests

### 📋 Planned Features
- [ ] Provider fallback mechanism
- [ ] Smart scheduling (based on `last_fetch_at` + `fetch_interval`)
- [ ] Caching layer for frequently accessed prices
- [ ] Postgres optimization (JSONB, ON CONFLICT)

---

## 🔗 Related Documentation

### LibreFolio Core Documentation
- [Database Schema](../database-schema.md) - Complete DB schema reference
- [API Development Guide](../api-development-guide.md) - Creating API endpoints
- [Async Architecture](../async-architecture.md) - Understanding async patterns
- [Testing Guide](../testing-guide.md) - Testing strategies and conventions

### FX System Documentation (Similar Patterns)
- [FX Architecture](../fx/architecture.md) - Similar provider system for FX rates
- [FX Provider Development](../fx/provider-development.md) - Provider development patterns
- [FX API Reference](../fx/api-reference.md) - API endpoint examples

---

## 🤝 Contributing

When contributing to the asset pricing system:

1. **Follow the bulk-first pattern** - All operations should have a bulk version
2. **Use Pydantic v2 models** - For all API request/response schemas
3. **Write comprehensive tests** - Cover both success and error cases
4. **Document your provider** - Include usage examples and error codes
5. **Handle errors gracefully** - Use `AssetSourceError` with detailed context

---

## 📞 Support & Questions

- **Issues**: GitHub Issues
- **Documentation**: This folder and linked guides
- **Examples**: See existing providers in `backend/app/services/asset_source_providers/`

---

**Last Updated**: 2025-11-10  
**Documentation Version**: 1.0.0

