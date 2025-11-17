# Database Tests

Testing database layer, schema, constraints, and persistence.

> 📖 **Back to**: [Testing Guide](./README.md)

---

## Overview

Database tests operate directly on **SQLite test database** (`backend/data/sqlite/test_app.db`).

**No backend server required.**

**Run**: `./test_runner.py db all`

---

## Test Suites

### 1. Database Creation

**Command**: `./test_runner.py db create`

**What it does**:
- Deletes existing test database
- Creates fresh database from Alembic migrations
- Verifies file exists and is valid

**When to use**: Before running other DB tests, or to reset state

---

### 2. Schema Validation

**File**: `backend/test_scripts/test_db/db_schema_validate.py`

**Command**: `./test_runner.py db validate`

**What it tests** (9 categories):
- Tables exist (10 tables expected)
- Foreign keys present and correct
- Unique constraints
- Indexes
- PRAGMA foreign_keys=ON enforced
- Enum types accessible
- Model imports
- Daily-point policy (unique constraints on date fields)
- CHECK constraints (normalized with sqlglot)

**Coverage**: All database structure elements

---

### 3. Numeric Truncation

**File**: `backend/test_scripts/test_db/test_numeric_truncation.py`

**Command**: `./test_runner.py db numeric-truncation`

**What it tests**:
- Decimal precision handling for prices, FX rates
- Truncation (not rounding) behavior
- No false positive updates
- Edge cases (zero, negative, large values)

**See**: [Decimal Utils](./utils-tests.md#5-decimal-precision)

---

### 4. Populate Mock Data

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

**Command**: `./test_runner.py db populate [--force]`

**What it does**:
- Creates comprehensive sample data
- Assets, brokers, transactions, cash movements
- Price history and FX rates
- Useful for frontend development

**Options**:
- `--force`: Delete existing data and recreate

---

### 5. Transaction-CashMovement Integrity

**File**: `backend/test_scripts/test_db/test_transaction_cash_integrity.py`

**Command**: `./test_runner.py db transaction-cash-integrity`

**What it tests** (7 tests):
- Unidirectional relationship (Transaction → CashMovement)
- ON DELETE CASCADE works correctly
- CHECK constraint enforcement (types requiring CashMovement)
- Only Transaction can delete associated CashMovement
- CashMovement cannot be deleted if Transaction exists
- Proper FK resolution

**Architecture**: Task 1.1b remediation

---

### 6. Transaction Types

**File**: `backend/test_scripts/test_db/test_transaction_types.py`

**Command**: `./test_runner.py db transaction-types`

**What it tests**:
- All TransactionType enum values work
- CashMovement requirement validation per type
- BUY/SELL/DIVIDEND/INTEREST/FEE/TAX require CashMovement
- ADD_HOLDING/REMOVE_HOLDING/TRANSFER do NOT require CashMovement

---

### 7. FX Rates Persistence

**File**: `backend/test_scripts/test_db/test_fx_rates_persistence.py`

**Command**: `./test_runner.py db fx-rates`

**What it tests**:
- Fetch rates from ECB (external API)
- Persist to database
- Overwrite existing rates (UPSERT)
- Idempotency (running twice produces same result)
- Constraints enforced

**Requires**: Internet connection for ECB API

---

## Running Database Tests

```bash
# All database tests (includes creation)
./test_runner.py db all

# Create fresh database
./test_runner.py db create

# Validate schema only
./test_runner.py db validate

# Populate with test data
./test_runner.py db populate --force

# Specific test
./test_runner.py db transaction-cash-integrity
```

---

## Test Database Management

**Location**: `backend/data/sqlite/test_app.db`

**Configuration**: Automatic via `backend/test_scripts/test_db_config.py`

**Isolation**: Completely separate from production database

**Reset**: Run `./test_runner.py db create`

---

## Related Documentation

- **[Database Schema](../database-schema.md)** - Complete schema documentation
- **[Alembic Guide](../alembic-guide.md)** - Migrations
- **[Testing Environment](../testing-environment.md)** - Test vs production isolation

---

**Last Updated**: November 17, 2025

