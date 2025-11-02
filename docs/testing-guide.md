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

These tests verify that external APIs (like ECB for currency rates) are accessible.

#### ✅ Test 1: ECB API Connection

```bash
python test_runner.py -v external ecb
```

**What this test does:**
- Connects to the European Central Bank API
- Fetches list of available currencies (~45 currencies)
- Verifies common currencies are available (USD, GBP, CHF, JPY, etc.)

**Expected result:**
```
✅ ECB API Connection
✅ Currency List Validation
Results: 2/2 tests passed
```

**What you learned:**
- LibreFolio uses ECB as the external data source for FX rates
- The system supports 45+ currencies
**Troubleshooting:**
- ❌ Connection failed → Check internet connection
- ❌ Timeout → ECB API might be temporarily unavailable, retry later

---

**Checkpoint 1:** External services working ✅

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
✅ Forward-Fill Logic
✅ Missing Rate Error
Results: 7/7 tests passed
```

**What you learned:**
- Test automatically sets up required mock data (no prerequisites!)
- **Safety first**: Explicitly verifies test DB before making changes
- Uses UPSERT so it's safe to run multiple times
- Creates rates for multiple dates to test date handling
- Conversion service handles identity, direct, and inverse conversions
- System correctly picks rates based on date
- System uses forward-fill for missing dates (weekend/holidays)
- Error handling is robust
- Cross-currency conversions (USD→GBP) will be handled by future FX plugins

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
- Tests `GET /api/v1/fx/currencies` - List available currencies
- Tests `POST /api/v1/fx/sync` - Sync FX rates from ECB
- Tests `GET /api/v1/fx/convert` - Convert amounts between currencies
- Tests error handling (404 for missing rates, 422 for invalid input)
- Tests validation (negative amounts, invalid date ranges)
- **Auto-stops server** at end of test

**Expected result:**
```
✅ Backend server started successfully
✅ GET /fx/currencies
✅ POST /fx/sync
✅ GET /fx/convert
✅ Missing Rate Error
✅ Invalid Request Handling
Results: 5/5 tests passed
```

**What you learned:**
- REST API exposes FX functionality to frontend
- Server auto-management: test always starts fresh server and stops it at end
- Test server runs on TEST_PORT (default: 8001, configurable)
- Production server runs on PORT (default: 8000, configurable)
- No conflicts between test and production/development
- API validates input and returns appropriate errors
- Endpoints follow REST conventions


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

**Expected result:**
```
✅ External Services
✅ Database Layer
✅ Backend Services
⚠️  API Tests (skipped - requires manual server start)

🎉 ALL TESTS PASSED! 🎉
```

---

## 📊 Test Summary

| Level | Category | Tests | What You Verified |
|-------|----------|-------|-------------------|
| 1 | **External** | 1 | ECB API accessible |
| 2 | **Database** | 4 | Schema, persistence, constraints, rate inversion |
| 3 | **Services** | 1 | Business logic, calculations |
| 4 | **API** | 1 | HTTP endpoints, validation |

**Total:** 7 test suites, ~35+ individual tests

---

## 🎓 What You've Learned

After completing this guide, you now understand:

### **Architecture**
- ✅ LibreFolio uses a layered architecture (external → db → services → api)
- ✅ Each layer has clear responsibilities
- ✅ Tests verify each layer independently

### **External Integration**
- ✅ ECB provides FX rates for 45+ currencies
- ✅ No API key required (free public API)

### **Database**
- ✅ SQLite database with 8 main tables
- ✅ Alembic manages schema migrations
- ✅ Test database isolated from production
- ✅ Constraints enforce data quality

### **Business Logic**
- ✅ FX conversion supports multiple scenarios
- ✅ Forward-fill handles missing data
- ✅ Cross-currency conversions work correctly

### **API**
- ✅ REST API follows standard conventions
- ✅ Input validation prevents bad data
- ✅ Error handling is robust

### **Testing**
- ✅ Test suite is comprehensive and well-organized
- ✅ Tests are isolated (separate DB, separate port)
- ✅ Auto-management reduces manual work
- ✅ Clear prerequisites and dependencies

---

## 🔧 Troubleshooting

### Common Issues

**❌ "ECB API connection failed"**
- Check internet connection
- Try again later (ECB might be temporarily down)

**❌ "Database creation failed"**
- Check file permissions in `backend/data/sqlite/`
- Ensure Alembic migrations are present

**❌ "Missing rate" errors in services tests**
- Run `python test_runner.py -v db fx-rates` first
- Ensure ECB API is accessible
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
   - [Database Schema](./database-schema.md)
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

