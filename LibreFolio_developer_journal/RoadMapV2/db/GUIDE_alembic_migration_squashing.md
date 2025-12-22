# Alembic Migration Squashing Guide - Manual SQL Approach

**Date**: 2025-11-06  
**Context**: DEV environment - consolidating multiple migrations into one  
**Approach**: Manual migration with raw SQL extracted from working database

---

## 🎯 When to Squash Migrations

### ✅ Good Cases (Safe to Squash)
- **DEV environment** with no production deployments
- **Rapid prototyping** phase with many experimental migrations
- **Before initial release** to clean up development history
- **Team agrees** on losing granular history

### ❌ Bad Cases (DON'T Squash)
- **Production databases** already deployed
- **Multiple developers** using different migration states
- **Need rollback capability** to specific intermediate states
- **Audit requirements** demand full history

---

## 📋 Complete Squashing Procedure (Manual SQL Method)

This guide uses **manual SQL extraction** instead of Alembic autogenerate, which proved more reliable for SQLite + SQLModel.

---

## Step 1: Prerequisites & Verification

```bash
# 1. Ensure all databases at same revision
./dev.sh db:current backend/data/sqlite/test_app.db
./dev.sh db:current backend/data/sqlite/app.db
# Should show same revision (e.g., a63a8001e62c)

# 2. Run all tests to ensure database is healthy
./test_runner.py db all
./test_runner.py services all

# 3. Verify CHECK constraints are present
./dev.sh db:check backend/data/sqlite/test_app.db
```

**All must pass** before proceeding.

---

## Step 2: Backup Everything

```bash
# Create timestamped backups
DATE=$(date +%Y%m%d_%H%M%S)

# Backup databases
cp backend/data/sqlite/test_app.db backend/data/sqlite/test_app.db.pre_squash_$DATE
cp backend/data/sqlite/app.db backend/data/sqlite/app.db.pre_squash_$DATE

# Backup migration folder
cp -r backend/alembic/versions backend/alembic/versions.backup_$DATE

echo "✅ Backups created with timestamp: $DATE"
```

**Save the timestamp** - you'll need it for recovery if something goes wrong.

---

## Step 3: Extract Complete Schema from Working Database

This is the **key step** - we get the exact SQL that works:

```bash
# Extract complete schema including CHECK constraints
sqlite3 backend/data/sqlite/test_app.db .schema > /tmp/working_schema.sql

# Verify it contains all tables
grep "CREATE TABLE" /tmp/working_schema.sql

# Should see: assets, brokers, fx_rates, fx_currency_pair_sources,
#             asset_provider_assignments, cash_accounts, price_history,
#             transactions, cash_movements
```

**Why this works**:
- Gets **actual working SQL** from production database
- Includes all CHECK constraints automatically
- Preserves exact column types and constraints
- No Alembic/SQLAlchemy translation issues

---

## Step 4: Document Current State

```bash
# Save current revision
CURRENT_REV=$(sqlite3 backend/data/sqlite/test_app.db "SELECT version_num FROM alembic_version;")
echo "Current revision: $CURRENT_REV"

# List migration files to be squashed
ls -1 backend/alembic/versions/*.py > /tmp/migrations_to_squash.txt
cat /tmp/migrations_to_squash.txt

# Count tables
sqlite3 backend/data/sqlite/test_app.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
# Should be 10 (9 tables + alembic_version)
```

---

## Step 5: Clean Slate

```bash
# Remove migration files (backup exists!)
rm backend/alembic/versions/*.py
touch backend/alembic/versions/.gitkeep

# Delete databases (backup exists!)
rm backend/data/sqlite/test_app.db
rm backend/data/sqlite/app.db

echo "✅ Clean slate ready"
```

---

## Step 6: Create Manual Migration from Extracted Schema

Now we create a **manual migration file** using the extracted SQL.

**File**: `backend/alembic/versions/001_initial.py`

### Structure:

```python
"""initial schema - squashed

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-06

SQUASHED from N migrations (XXX..YYY)
Manual migration created from working database schema.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables using raw SQL from working database."""
    conn = op.get_bind()
    
    print("🔧 Starting migration 001_initial...")
    print("=" * 60)

    # Table 1: assets (no dependencies)
    print("📦 Creating table: assets...")
    conn.execute(sa.text("""CREATE TABLE assets (
        id INTEGER PRIMARY KEY,
        display_name VARCHAR NOT NULL,
        identifier VARCHAR NOT NULL,
        identifier_type VARCHAR(6) NOT NULL,
        currency VARCHAR NOT NULL,
        asset_type VARCHAR(14) NOT NULL,
        valuation_model VARCHAR(15) NOT NULL,
        face_value NUMERIC(18, 6),
        maturity_date DATE,
        interest_schedule TEXT,
        late_interest TEXT,
        active BOOLEAN NOT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX ix_assets_identifier ON assets (identifier)"))
    print("  ✓ Index created")

    # Table 2: brokers (no dependencies)
    print("📦 Creating table: brokers...")
    conn.execute(sa.text("""CREATE TABLE brokers (
        id INTEGER PRIMARY KEY,
        name VARCHAR NOT NULL,
        description TEXT,
        portal_url VARCHAR,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE UNIQUE INDEX ix_brokers_name ON brokers (name)"))
    print("  ✓ Index created")

    # ... Continue for all tables ...
    
    print("=" * 60)
    print("✅ Migration 001_initial completed successfully!")
    print("📊 Created 9 tables with all indexes and constraints")


def downgrade() -> None:
    """Drop all tables in reverse order."""
    conn = op.get_bind()
    for table in ['cash_movements', 'transactions', 'price_history', 
                  'cash_accounts', 'asset_provider_assignments', 
                  'fx_currency_pair_sources', 'fx_rates', 'brokers', 'assets']:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
```

### Key Points:

1. **Use `conn.execute(sa.text(...))`** instead of `op.create_table()`
2. **One statement per table** - don't combine CREATE TABLE + CREATE INDEX
3. **Add logging** with `print()` to track progress
4. **Correct order**: parent tables before child tables
   - assets, brokers, fx_rates, fx_currency_pair_sources (no dependencies)
   - asset_provider_assignments, cash_accounts (depend on assets/brokers)
   - price_history, transactions (depend on assets/brokers)
   - cash_movements (depends on cash_accounts, transactions)

5. **Copy SQL directly** from `/tmp/working_schema.sql`
   - CHECK constraints included automatically
   - UNIQUE constraints included
   - Foreign keys included

---

## Step 7: Table Creation Order (IMPORTANT!)

**Order matters** due to foreign key dependencies:

```python
# Phase 1: Tables with no dependencies
1. assets
2. brokers  
3. fx_rates
4. fx_currency_pair_sources

# Phase 2: Tables depending on Phase 1
5. asset_provider_assignments (FK → assets)
6. cash_accounts (FK → brokers)
7. price_history (FK → assets)

# Phase 3: Tables depending on Phase 2
8. transactions (FK → assets, brokers)

# Phase 4: Tables depending on Phase 3
9. cash_movements (FK → cash_accounts, transactions)
```

**Wrong order = foreign key errors!**

---

## Step 8: Apply Migration and Verify

```bash
# Apply to test database
./dev.sh db:upgrade backend/data/sqlite/test_app.db

# You should see:
# 🔧 Starting migration 001_initial...
# ============================================================
# 📦 Creating table: assets...
#   ✓ Table created
#   ✓ Index created
# ... (all 9 tables) ...
# ============================================================
# ✅ Migration 001_initial completed successfully!
```

**If migration completes without "✅ Migration completed"** = something failed silently!

---

## Step 9: Verify All Tables Created

```bash
# List tables
sqlite3 backend/data/sqlite/test_app.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

# Should show:
# alembic_version
# asset_provider_assignments
# assets
# brokers
# cash_accounts
# cash_movements
# fx_currency_pair_sources
# fx_rates
# price_history
# transactions

# Count (should be 10 including alembic_version)
sqlite3 backend/data/sqlite/test_app.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
```

---

## Step 10: Run Schema Validation

```bash
./test_runner.py db validate

# Expected output:
# ✅ PASS: Tables Exist
# ✅ PASS: Foreign Keys
# ✅ PASS: Unique Constraints
# ✅ PASS: Indexes
# ✅ PASS: CHECK Constraints
# ... (all 9 tests pass)
```

**If any test fails** = migration incomplete!

---

## Step 11: Test Downgrade/Upgrade Cycle

```bash
# Test downgrade (should drop all tables)
./dev.sh db:downgrade backend/data/sqlite/test_app.db

# Verify only alembic_version remains
sqlite3 backend/data/sqlite/test_app.db "SELECT name FROM sqlite_master WHERE type='table';"
# Output: alembic_version

# Re-upgrade
./dev.sh db:upgrade backend/data/sqlite/test_app.db

# Verify again
./test_runner.py db validate
# Should pass
```

---

## Step 12: Apply to Production Database

```bash
# Apply migration
./dev.sh db:upgrade backend/data/sqlite/app.db

# Verify both databases at same revision
./dev.sh db:current backend/data/sqlite/test_app.db
./dev.sh db:current backend/data/sqlite/app.db
# Both should show: 001_initial (head)
```

---

## Step 13: Full Test Suite

```bash
# Populate mock data
./test_runner.py db populate --force

# Run all tests
./test_runner.py db all
./test_runner.py services all
./test_runner.py api all
```

**All must pass** before considering squash complete.

---

## ⚠️ Common Issues & Solutions

### Issue 1: Only Some Tables Created

**Symptom**: Migration says "SUCCESS" but only 4-5 tables exist.

**Cause**: Silent failure in table creation (wrong order, SQL error).

**Solution**:
- Check logging output - did all "✓ Table created" appear?
- Verify table order (parent tables first)
- Check for typos in SQL

### Issue 2: Foreign Key Constraint Failed

**Symptom**: Error like `FOREIGN KEY constraint failed`.

**Cause**: Child table created before parent table.

**Solution**:
- Review table order in `upgrade()`
- Ensure assets/brokers created before tables that reference them

### Issue 3: CHECK Constraint Missing

**Symptom**: `./dev.sh db:check` fails.

**Cause**: CHECK constraint not copied from schema.

**Solution**:
- Check `/tmp/working_schema.sql` for CHECK constraints
- Ensure they're in CREATE TABLE statement
- Example: `CONSTRAINT ck_fx_rates_base_less_than_quote CHECK (base < quote)`

### Issue 4: Migration Runs But No Output

**Symptom**: No `print()` statements appear.

**Cause**: Using `./dev.sh db:upgrade` hides output.

**Solution**:
- Run directly: `pipenv run alembic -c backend/alembic.ini upgrade head`
- This shows all print() output

---

## 🔄 Emergency Rollback

If something goes wrong:

```bash
# 1. Stop all services
pkill -f uvicorn

# 2. Find backup timestamp
ls -1 backend/data/sqlite/*.pre_squash_*

# 3. Restore databases (replace TIMESTAMP with actual timestamp)
cp backend/data/sqlite/test_app.db.pre_squash_TIMESTAMP backend/data/sqlite/test_app.db
cp backend/data/sqlite/app.db.pre_squash_TIMESTAMP backend/data/sqlite/app.db

# 4. Restore migrations (replace TIMESTAMP with actual timestamp)
rm backend/alembic/versions/*.py
cp backend/alembic/versions.backup_TIMESTAMP/*.py backend/alembic/versions/

# 5. Verify
./dev.sh db:current backend/data/sqlite/test_app.db
./test_runner.py db validate

# 6. If OK, system restored
```

---

## 📝 Git Commit Message Template

```
chore: squash alembic migrations into single initial schema

Consolidated N migrations (FIRST_REV..LAST_REV) into single initial schema.

Method: Manual migration with raw SQL extracted from working database.

Previous migrations (squashed):
- FIRST_REV: First migration description
- ...
- LAST_REV: Last migration description

New migration:
- 001_initial: initial schema (squashed, manual SQL)

Approach:
- Extracted schema: sqlite3 test_app.db .schema
- Manual migration: conn.execute(sa.text(...)) per table
- Correct dependency order preserved
- All CHECK constraints included
- Detailed logging added for debugging

Verification:
- Schema validation: PASSED
- All tests: PASSED
- Both databases: APPLIED

Backup location: 
- Migrations: backend/alembic/versions.backup_TIMESTAMP/
- Databases: backend/data/sqlite/*.pre_squash_TIMESTAMP
```

---

## 📊 Why Manual SQL Works Better Than Autogenerate

| Aspect | Alembic Autogenerate | Manual SQL |
|--------|---------------------|------------|
| **Reliability** | ⚠️ Partial (4/9 tables) | ✅ Complete (9/9 tables) |
| **CHECK constraints** | ❌ Not detected | ✅ Included automatically |
| **SQLModel compatibility** | ❌ Import issues | ✅ No dependencies |
| **Debugging** | ❌ Silent failures | ✅ Explicit logging |
| **Control** | ⚠️ Alembic decides | ✅ Full control |
| **Error visibility** | ❌ Hidden | ✅ Clear print output |

---

## 🎓 Lessons Learned (LibreFolio Experience)

### What We Tried:

1. **Alembic autogenerate** (`alembic revision --autogenerate`)
   - Generated migration file
   - Added `import sqlmodel` manually
   - Applied migration
   - **Result**: Only 4/9 tables created ❌

2. **Multi-statement SQL block**
   - One `conn.exec_driver_sql()` with all CREATE TABLEs
   - **Result**: Empty database ❌

3. **Manual SQL with individual statements** ✅
   - One `conn.execute(sa.text(...))` per table
   - Detailed logging with `print()`
   - **Result**: All 9 tables created successfully! ✅

### Why Manual SQL Won:

- **No abstraction layer**: Direct SQL to SQLite
- **Predictable behavior**: Exactly what you write is executed
- **Easy debugging**: print() shows progress
- **Schema fidelity**: Copied from working database
- **SQLite native**: No translation issues

---

## 📅 Squash History

### 2025-11-06 - First Successful Squash

**Project**: LibreFolio  
**Status**: ✅ SUCCESS  
**Method**: Manual SQL migration  
**Duration**: 44 minutes (including failed autogenerate attempt)

**Old migrations**: 9 files (37d14b3d7a82 through a63a8001e62c)  
**New migration**: 1 file (001_initial)  
**Tables**: 9 (assets, brokers, fx_rates, fx_currency_pair_sources, asset_provider_assignments, cash_accounts, price_history, transactions, cash_movements)

**Timeline**:
1. ❌ Alembic autogenerate attempt failed
2. ✅ Extracted schema: `sqlite3 test_app.db .schema`
3. ✅ Created manual migration with raw SQL
4. ✅ Added logging for visibility
5. ✅ Applied to test_app.db - all tables created
6. ✅ Schema validation passed
7. ✅ Applied to app.db
8. ✅ All tests passed

**Files**:
- Migration: `backend/alembic/versions/001_initial.py`
- Backup migrations: `backend/alembic/versions.backup_20251106_152012/`
- Backup databases: `backend/data/sqlite/*.pre_squash_20251106_152000`

**Key learnings**:
- Manual SQL > autogenerate for SQLite + SQLModel
- Logging essential for debugging
- Schema extraction gives exact working SQL
- Individual statements > multi-statement blocks

---

## 📚 Quick Reference

### Extract Schema
```bash
sqlite3 database.db .schema > schema.sql
```

### Create Migration Template
```python
def upgrade() -> None:
    conn = op.get_bind()
    print("🔧 Starting migration...")
    
    conn.execute(sa.text("""CREATE TABLE ..."""))
    print("  ✓ Table created")
```

### Apply Migration
```bash
# With output
pipenv run alembic -c backend/alembic.ini upgrade head

# Silent
./dev.sh db:upgrade backend/data/sqlite/test_app.db
```

### Verify
```bash
sqlite3 database.db "SELECT name FROM sqlite_master WHERE type='table';"
./test_runner.py db validate
```

---

**Last Updated**: 2025-11-06  
**Maintainer**: LibreFolio Development Team  
**Success Rate**: 100% with manual SQL method

