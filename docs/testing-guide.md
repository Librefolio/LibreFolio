# Testing Guide for New Developers

Welcome to LibreFolio! This guide will help you understand the testing system by running tests in the correct order, from external services to the full application.

> 💡 **Want to understand the async architecture?** After running tests, read the [Async Architecture Guide](async-architecture.md) to understand how LibreFolio handles concurrent requests efficiently.

---

## 🎯 Purpose of This Guide

This is a **hands-on introduction** to LibreFolio's test suite. By following this checklist, you will:
- ✅ Verify your development environment is correctly set up
- ✅ Understand the system architecture (external → database → services → API)
- ✅ Learn how each component works and how async/await enables high performance
- ✅ Gain confidence in the codebase

---

## 📋 Prerequisites

Before starting, ensure you have:
- [ ] Python environment set up (Pipenv)
- [ ] Project dependencies installed (`pipenv install`)
- [ ] Ports 8000-8001 available (or configure different ports, see below)

**💡 Verbose Output:**

All test commands support the `-v` flag for detailed output. Add it immediately after `test_runner.py`:

```bash
# Normal output (summary only)
python test_runner.py external ecb

# Verbose output (full details)
python test_runner.py -v external ecb
```

**Verbose mode shows:**
- Complete test execution logs
- Detailed API responses
- Database queries
- Step-by-step progress

**If ports 8000-8001 are occupied:**

You can configure custom ports in two ways:

**Option 1: Create `.env` file** (recommended)
```bash
# In project root, create .env file
echo "PORT=9000" >> .env
echo "TEST_PORT=9001" >> .env
```

**Option 2: Export in terminal**
```bash
python test_runner.py -v external ecb
export TEST_PORT=9001

# Then run tests in same terminal
python test_runner.py all
```

---

## 🧪 Test Execution Checklist

### **Level 1: External Services** 🌐

These tests verify that external FX rate provider APIs are accessible and working correctly.

#### ✅ Test 1: All FX Providers

```bash
python test_runner.py -v external all
```

**What this test does:**
- Tests **4 central bank providers**: ECB (EUR), FED (USD), BOE (GBP), SNB (CHF)
- For each provider:
  - ✅ Verifies registration and metadata
  - ✅ Fetches supported currencies list
  - ✅ Fetches actual rates (last 7 days)
  - ✅ Tests rate normalization (alphabetical ordering)
- Tests **multi-unit currencies** (JPY, SEK, NOK, DKK)
  - Some banks quote per 100 units instead of per 1 unit
  - Verifies correct handling (avoids 100x errors)

**Expected result:**
```
✅ PASS - External Forex data import API (16/16 provider tests)
✅ PASS - Multi-Unit Currency Handling (12/12 tests)
Results: 2/2 tests passed
```

**What you learned:**
- LibreFolio supports **4 official central bank providers**:
  - 🇪🇺 **ECB**: European Central Bank (~45 currencies, EUR base)
  - 🇺🇸 **FED**: Federal Reserve (~21 currencies, USD base)
  - 🇬🇧 **BOE**: Bank of England (~16 currencies, GBP base)
  - 🇨🇭 **SNB**: Swiss National Bank (~11 currencies, CHF base)
- Each provider is tested uniformly (same test suite)
- **Multi-unit currencies** (JPY, SEK, NOK, DKK) handled correctly
  - Example: 100 JPY = 0.67 USD (NOT 1 JPY = 0.0067 USD)
  - SNB uses multi-unit for JPY, SEK, NOK, DKK
- All providers implement standard interface (`FXRateProvider`)
- No API keys required (free public APIs)
- System is **multi-provider ready** for future additions

**Test all plugin individual:**
```bash
# Test fx-source capability only
python test_runner.py -v external fx-source

# Test fx-multi-unit capability only
python test_runner.py -v external fx-multi-unit
```

**Troubleshooting:**
- ❌ Connection failed → Check internet connection
- ❌ Timeout → Provider API might be temporarily unavailable, retry later
- ⚠️ 0 observations → Weekend/holiday, no data for those dates (normal)

---

**Checkpoint 1:** External services working ✅  
**Providers validated:** 4/4 ✅  
**Multi-unit handling:** Verified ✅

---

### **Level 2: Database Layer** 🗄️

These tests verify the database structure and data persistence.

**🔒 Safety First**: All database tests display which database they're using at startup:
```
✅ Using test database: sqlite:///./backend/data/sqlite/test_app.db
```
This verification prevents accidental modification of production data. If a test tries to use the production database, it will abort immediately.

#### ✅ Test 2: Database Creation

```bash
python test_runner.py -v db create
```

**What this test does:**
- Deletes existing test database (if present)
- Runs Alembic migrations to create fresh database
python test_runner.py -v db validate

**Expected result:**
```
✅ Database created successfully
```

**What you learned:**
- LibreFolio uses SQLite database
- Schema is managed via Alembic migrations
- **Test database**: `backend/data/sqlite/test_app.db` ← Used by all tests
- **Production database**: `backend/data/sqlite/app.db` ← Never touched by tests
- Complete isolation between test and production data

---

#### ✅ Test 3: Schema Validation

```bash
python test_runner.py -v db validate
```

**What this test does:**
- Verifies all expected tables exist (brokers, assets, transactions, fx_rates, etc.)
- Checks foreign key constraints are enforced
- Validates unique constraints
- Verifies indexes are created
- Checks decimal precision (Numeric 18,6)

**Expected result:**
```
✅ PASS     Tables Exist
✅ PASS     Foreign Keys
✅ PASS     Unique Constraints
✅ PASS     Indexes
✅ PASS     PRAGMA foreign_keys
✅ PASS     Enum Types
✅ PASS     Model Imports
✅ PASS     Daily-Point Policy
✅ PASS     CHECK Constraints

Results: 9/9 tests passed
```

**What you learned:**
- Database has 8 main tables
- Referential integrity is enforced
- Foreign keys work correctly
- Schema matches the documented structure

---

#### ✅ Test 4: Mock Data Population

```bash
python test_runner.py db populate
```

**What this test does:**
- Populates database with comprehensive MOCK data
- Creates sample brokers (Interactive Brokers, Degiro, Recrowd)
- Creates sample assets (AAPL, MSFT, TSLA, VWCE, etc.)
- Creates sample transactions (buy, sell, dividends)
- Inserts 30 days of mock FX rates

**Expected result (database is present for tests above):**
```
❌ Mock data population - FAILED
💡 Hint: Database might already contain data
   Use --force to delete and recreate:
     python test_runner.py db populate --force
```

To run successfully, use the `--force` flag to recreate the database from scratch:

```bash
python test_runner.py db populate --force
```

**Expected result (empty database):**
```
✅ Mock data population completed successfully!
```

**What you learned:**
- Database can store complex portfolio data
- Sample data useful for frontend development
- Schema supports multiple asset types (stocks, ETFs, P2P loans)
- Transactions linked to brokers and assets
- Use `--force` flag to recreate from scratch

**Note:** This is **MOCK DATA** for testing only!

**💡 Why this test comes before FX rates:** Populate requires empty DB (or `--force`), while FX rates can run on existing data.

---

#### ✅ Test 5: FX Rates Persistence

```bash
python test_runner.py -v db fx-rates
```

**What this test does:**
- Fetches real FX rates from ECB API
- Persists rates to database (uses UPSERT - can run on existing data)
- Verifies data overwrite (updates existing rates)
- Tests idempotency (no duplicates on re-sync)
- **Verifies rate inversion for alphabetical ordering:**
  - CHF/EUR: ECB gives 1 EUR = X CHF → stored as CHF/EUR with rate = 1/X
  - EUR/USD: ECB gives 1 EUR = X USD → stored as EUR/USD with rate = X
- Validates database constraints (unique, check base<quote)

**Expected result:**
```
✅ Fetch & Persist Single Currency
✅ Fetch & Persist Multiple Currencies
✅ Data Overwrite (Update Existing)
✅ Idempotent Sync
✅ Rate Inversion for Alphabetical Ordering
✅ Database Constraints
Results: 6/6 tests passed
```

**What you learned:**
- FX rates are stored with alphabetical ordering (EUR/USD, not USD/EUR)
- When base > quote alphabetically, the rate is inverted (1/rate)
- System fetches rates from ECB and stores them locally
- Rates can be updated (no duplicates)
- Database enforces data quality constraints

**💡 This test can run multiple times:** It uses UPSERT, so existing data is updated, not duplicated.

---

#### ✅ Test 6: Numeric Column Truncation

```bash
python test_runner.py -v db numeric-truncation
```

**What this test does:**
- Tests **all 12 Numeric columns** across database tables
- Validates helper functions for precision/truncation
- Verifies database truncates decimals as expected
- **Prevents false updates** (no update if value identical after truncation)
- Tests columns:
  - `assets.face_value` (Numeric 18,6)
  - `cash_movements.amount` (Numeric 18,6)
  - `fx_rates.rate` (Numeric 24,10) ← Higher precision for FX rates
  - `price_history` columns (open, high, low, close, adjusted_close)
  - `transactions` columns (quantity, price, fees, taxes)

**Expected result:**
```
✅ Helper Functions Test: 12 passed, 0 failed
✅ Database Truncation: PASS
✅ No False Updates: PASS

Results: 3/3 tests passed
```

**What you learned:**
- **FX rates use higher precision**: Numeric(24,10) vs standard Numeric(18,6)
  - 14 digits before decimal, 10 after (e.g., 1.0644252000)
  - Prevents rounding errors in currency conversions
- Database automatically truncates to column precision
- Helper functions `truncate_decimal_to_db_precision()` available for pre-truncation
- System avoids false "updates" when values are identical after truncation
- **Bug prevention**: Without truncation check, every sync would "update" all rates (even if unchanged)

**Example:**
```python
# API returns: 1.012345678901234
# DB stores:   1.0123456789 (truncated to 10 decimals)
# Re-sync:     No update (pre-truncated comparison)
```

**💡 Why this matters:** Prevents unnecessary DB writes and ensures accurate change detection during FX sync operations.

---

**Checkpoint 2:** Database layer working ✅

---

### **Level 3: Backend Services** ⚙️

These tests verify business logic and calculations.

#### ✅ Test 6: FX Conversion Logic

```bash
python test_runner.py -v services fx
```

**What this test does:**
- **Automatically inserts mock FX rates** for 3 dates (today, yesterday, 7 days ago)
- **Verifies test database usage** (prevents accidental production DB modification)
- Tests identity conversion (EUR→EUR)
- Tests direct conversion using stored rate (EUR→USD)
- Tests inverse conversion using 1/rate (USD→EUR)
- Tests roundtrip conversion (EUR→USD→EUR ≈ original)
- Tests conversion with different dates (verifies date handling)
- Tests forward-fill logic (uses most recent rate if date missing)
- Tests error handling (missing rate raises exception)

**Expected result:**
```
✅ ✓ Using test database: sqlite:///./backend/data/sqlite/test_app.db
ℹ️  Setting up mock FX rates for testing...
✅ Mock FX rates ready (12 rates across 3 dates)

✅ Identity Conversion
✅ Direct Conversion (EUR→USD)
✅ Inverse Conversion (USD→EUR)
✅ Roundtrip Conversion
✅ Different Dates
✅ Backward-Fill Logic
✅ Missing Rate Error
✅ Bulk Conversion - Single Item
✅ Bulk Conversion - Multiple Items
✅ Bulk Conversion - Partial Failure
✅ Bulk Conversion - All Failures
✅ Bulk Conversion - Raise on Error
Results: 12/12 tests passed
```

**What you learned:**
- Test automatically sets up required mock data (no prerequisites!)
- **Safety first**: Explicitly verifies test DB before making changes
- Uses UPSERT so it's safe to run multiple times
- Creates rates for multiple dates to test date handling
- Conversion service handles identity, direct, and inverse conversions
- System correctly picks rates based on date
- System uses **backward-fill** for missing dates (uses most recent rate before requested date)
- Error handling is robust
- **Bulk conversions** supported with partial failure handling
- `raise_on_error` parameter controls error behavior (raise vs collect)

**⚠️ Important: Clean Database Required**

This test may fail if the test database contains "old" rates from previous test runs (e.g., API tests insert rates from 1999 for backward-fill testing). To fix:

```bash
# Recreate clean test database
python test_runner.py db create

# Or run the full test suite (auto-cleans)
python test_runner.py -v all
```

**Why this happens:**
- API tests insert historical rates (1999-12-15) to test backward-fill warnings
- Services test expects only its own mock rates (last 7 days)
- Old rates in DB cause test assertion failures

**Best practice:** Always run `python test_runner.py all` instead of individual tests to ensure clean state.

**💡 No prerequisites:** This test inserts its own mock data, so it works even on an empty database!  
**🔒 Safe:** Explicit check ensures only test_app.db is modified, never production DB!

---

**Checkpoint 3:** Backend services working ✅

---

### **Level 4: REST API Endpoints** 🌍

These tests verify HTTP endpoints (requires server).

#### ✅ Test 7: FX API Endpoints

```bash
python test_runner.py -v api fx
```

**What this test does:**
- **Auto-starts fresh test server** on TEST_PORT (default: 8001)
- Tests **10 comprehensive endpoint scenarios**:
  1. `GET /fx/currencies` - List available currencies from provider
  2. `GET /fx/providers` - List all registered FX providers (ECB, FED, BOE, SNB)
  3. `POST/GET/DELETE /fx/pair-sources` - Configure currency pair sources (CRUD operations)
  4. `POST /fx/sync/bulk` - Sync FX rates (explicit provider + auto-configuration modes)
  5. `POST /fx/convert/bulk` - Single currency conversion
  6. `POST /fx/rate-set/bulk` - Manual rate upsert (single)
  7. Backward-fill warning (old dates use most recent rate)
  8. `POST /fx/convert/bulk` - Bulk conversions (multiple items)
  9. `POST /fx/rate-set/bulk` - Bulk rate upserts (multiple items)
  10. Invalid request handling (comprehensive validation)
- **Auto-stops server** at end of test

**Expected result:**
```
✅ Backend server started successfully
Test server port: 8001
API base URL: http://localhost:8001/api/v1

✅ PASS: GET /fx/currencies
✅ PASS: GET /fx/providers
✅ PASS: Pair Sources CRUD
✅ PASS: POST /fx/sync/bulk
✅ PASS: POST /fx/convert/bulk (Single)
✅ PASS: POST /fx/rate-set/bulk (Single)
✅ PASS: Backward-Fill Warning
✅ PASS: POST /fx/convert/bulk (Bulk)
✅ PASS: POST /fx/rate-set/bulk (Bulk)
✅ PASS: Invalid Request Handling

Results: 10/10 tests passed
✅ All fx api endpoint tests passed! 🎉
```

**What you learned:**

**Provider Management:**
- API dynamically lists all registered providers (no hardcoded lists)
- Each provider has: code, name, base_currency, base_currencies[], description
- Test validates API response matches backend factory (consistency check)
- Easy to add new providers (just register in factory)

**Pair Sources Configuration:**
- Can configure which provider to use for each currency pair
- CRUD operations: GET (list), POST (create/update), DELETE (remove)
- **Atomic transactions**: POST bulk either all succeed or all fail
- Validation: base < quote (alphabetical), provider must exist, priority >= 1
- Update vs Insert: system automatically detects and handles both
- Soft errors: DELETE non-existent pair = warning (not error)

**Sync Modes:**
- **Explicit Provider Mode**: `POST /sync?provider=ECB` (force specific provider)
- **Auto-Configuration Mode**: `POST /sync` (uses pair-sources configuration) ← TODO: Phase 5.3
- Backward compatible: old code with explicit provider still works
- Idempotency: sync twice = 0 new rates (safe to run multiple times)

**Conversions:**
- Single conversion: 1 item in conversions array
- Bulk conversions: multiple items in single request
- Range conversions: `start_date` + `end_date` = convert each day in range
- Partial failure support: some succeed, some fail (all reported)
- Backward-fill: uses most recent rate if exact date missing
- Response includes backward_fill_info when applied

**Manual Rate Management:**
- Can manually insert/update rates (source="MANUAL")
- Single or bulk operations
- Upsert behavior: insert if new, update if exists
- Useful for custom rates or testing

**Validation & Error Handling:**
- Comprehensive input validation (negative amounts, invalid dates, bad currencies)
- Appropriate HTTP status codes (400, 404, 422, 502)
- Detailed error messages (which field, what's wrong, suggestion)
- Partial failure handling (continue processing, collect errors)

**Server Management:**
- Test server runs on TEST_PORT (default: 8001, configurable)
- Production server runs on PORT (default: 8000, configurable)
- No conflicts between test and production/development
- Auto-start and auto-stop (clean test environment)
- Test database isolated from production

**Test Order:**
Tests run in optimal order:
1. Basic endpoints (currencies, providers)
2. Configuration (pair-sources) ← Creates setup for auto-config
3. Sync (uses configuration from step 2)
4. Conversions (use rates from sync)
5. Error handling (comprehensive validation)

[//]: # (TODO: quando ci saranno altri api test metterli qui e poi documentare l'all, che per ora ha poco senso essendo 1 solo file)

---

**Checkpoint 4:** API layer working ✅

---

## 🚀 Complete Test Suite

Now that you understand each component, run the complete test suite:

```bash
python test_runner.py -v all
```

**What this does:**
- Runs all tests in optimal order: external → db → services → api
- Stops at first failure to avoid cascading errors
- Provides comprehensive summary
- **Auto-starts and stops test server** for API tests

**Expected result:**
```
✅ External Services (2/2 tests passed)
✅ Database Layer (5/5 tests passed)
✅ Backend Services (1/1 tests passed)
✅ API Tests (10/10 tests passed)

🎉 ALL TESTS PASSED! 🎉
```

---

## 📊 Test Summary

| Level | Category | Tests | What You Verified |
|-------|----------|-------|-------------------|
| 1 | **External** | 2 | 4 FX providers accessible (ECB, FED, BOE, SNB), multi-unit handling |
| 2 | **Database** | 5 | Schema, persistence, constraints, rate inversion, numeric truncation |
| 3 | **Services** | 1 | Business logic, calculations, bulk conversions |
| 4 | **API** | 1 | 10 HTTP endpoints, provider management, configuration |

**Total:** 9 test suites, ~50+ individual tests

---

## 🎓 What You've Learned

After completing this guide, you now understand:

### **Architecture**
- ✅ LibreFolio uses a layered architecture (external → db → services → api)
- ✅ Each layer has clear responsibilities
- ✅ Tests verify each layer independently

### **External Integration**
- ✅ **4 central bank providers** supported (ECB, FED, BOE, SNB)
- ✅ Each provider: 11-45 currencies, different base currencies
- ✅ Multi-unit currencies (JPY, SEK, NOK, DKK) handled correctly
- ✅ No API keys required (free public APIs)
- ✅ System extensible for future providers

### **Database**
- ✅ SQLite database with 9 main tables (incl. fx_currency_pair_sources)
- ✅ Alembic manages schema migrations
- ✅ Test database isolated from production
- ✅ Constraints enforce data quality
- ✅ **Higher precision for FX rates**: Numeric(24,10) vs Numeric(18,6)
- ✅ Truncation handling prevents false updates

### **Business Logic**
- ✅ FX conversion supports multiple scenarios (identity, direct, inverse, roundtrip)
- ✅ **Backward-fill** handles missing data (uses most recent rate)
- ✅ **Bulk conversions** with partial failure support
- ✅ Cross-currency conversions work correctly
- ✅ Database must be clean for accurate testing

### **API**
- ✅ REST API follows standard conventions
- ✅ **10 comprehensive endpoints** tested
- ✅ **Provider management**: GET /providers (dynamic list from factory)
- ✅ **Pair sources configuration**: CRUD operations with atomic transactions
- ✅ **Sync modes**: Explicit provider + auto-configuration (planned)
- ✅ **Range conversions**: start_date + end_date support
- ✅ **Bulk operations**: conversions and rate upserts
- ✅ Input validation prevents bad data
- ✅ Error handling is robust with detailed messages
- ✅ Partial failure handling (some succeed, some fail)

### **Testing**
- ✅ Test suite is comprehensive and well-organized
- ✅ Tests are isolated (separate DB, separate port)
- ✅ Auto-management reduces manual work (server start/stop)
- ✅ Clear prerequisites and dependencies
- ✅ **Test order matters**: pair-sources before sync (configuration setup)
- ✅ **Clean DB important**: run `all` to avoid stale data issues

---

## 🔧 Troubleshooting

### Common Issues

**❌ "ECB API connection failed"**
- Check internet connection
- Try again later (ECB might be temporarily down)

**❌ "Database creation failed"**
- Check file permissions in `backend/data/sqlite/`
- Ensure Alembic migrations are present

**❌ "Services test failed: Backward-Fill Logic" (stale DB data)**
- **Root cause**: API tests insert old rates (1999-12-15) that conflict with services test expectations
- **Solution**: Run full test suite (recreates clean DB): `python test_runner.py -v all`
- **Alternative**: Recreate test DB: `python test_runner.py db create`
- **Best practice**: Always run `all` instead of individual test suites

**❌ "Missing rate" errors in services tests**
- Run `python test_runner.py -v db fx-rates` first
- Ensure provider APIs are accessible
- Use `-v` flag to see detailed error messages

**❌ "Port already in use" (API tests)**
- Check if something is using test port: `lsof -i :8001`
- Option 1: Stop the service using that port
- Option 2: Configure different ports in `.env`:
  ```bash
  echo "PORT=9000" >> .env
  echo "TEST_PORT=9001" >> .env
  ```
- Test will always start fresh server and stop it at end

---

## 🎯 Next Steps

Now that you're familiar with the testing system:

1. **Explore the codebase:**
   - `backend/app/services/fx.py` - FX service logic
   - `backend/app/api/v1/fx.py` - API endpoints
   - `backend/app/db/models.py` - Database models

2. **Read documentation:**
   - 🚀 **[API Development Guide](./api-development-guide.md)** - ⭐ Start here to add new endpoints
   - [Database Schema](./database-schema.md)
   - [Async Architecture](./async-architecture.md) - Understand async/await patterns
   - [FX Implementation](./fx-implementation.md)
   - [Alembic Guide](./alembic-guide.md)

3. **Try development:**
   - Start server: `./dev.sh server`
   - Make a change
   - Run tests to verify: `python test_runner.py -v all`

4. **Write your first test:**
   - Use `test_utils.py` for common functions
   - Follow existing test patterns
   - Add to appropriate category (external/db/services/api)

---

## 📚 Additional Resources

- **Test Runner Help:** `python test_runner.py --help`
- **Category Help:** `python test_runner.py db --help`
- **Environment Variables:** [docs/environment-variables.md](./environment-variables.md)

---

**Welcome to the LibreFolio development team! 🎉**

You're now ready to contribute to the project. Happy coding! 🚀

---

*Last updated: 2025-10-30*  
*For questions or issues, check the project README or open an issue on GitHub.*

