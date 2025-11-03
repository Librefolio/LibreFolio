# Testing Environment

This document explains how LibreFolio manages test vs production databases to ensure tests don't corrupt production data.

## Overview

LibreFolio uses **separate databases** for testing and production:

- **Production**: `backend/data/sqlite/app.db` (port 8000)
- **Test**: `backend/data/sqlite/test_app.db` (port 8001)

The test environment is automatically activated when running tests, ensuring complete isolation.

## How It Works

### Test Mode Flag

LibreFolio supports a **test mode** that can be activated in two ways:

1. **Environment Variable**: `LIBREFOLIO_TEST_MODE=1`
2. **Command Line Flag**: `--test` (processed by main.py before uvicorn starts)

When test mode is enabled:
- `DATABASE_URL` is automatically overridden to use `TEST_DATABASE_URL`
- Server uses port 8001 instead of 8000
- All database operations use `test_app.db`

### Implementation Details

The test mode system consists of:

1. **`backend/app/config.py`**:
   - `set_test_mode(enabled: bool)` - Enable/disable test mode
   - `is_test_mode() -> bool` - Check if test mode is active
   - `get_settings()` - Automatically returns test database URL when in test mode

2. **`backend/app/main.py`**:
   - Checks for `--test` flag or `LIBREFOLIO_TEST_MODE` env var on startup
   - Sets test mode before any database initialization
   - Logs test mode status in startup message

3. **`backend/test_scripts/test_server_helper.py`**:
   - `TestServerManager` automatically sets `LIBREFOLIO_TEST_MODE=1`
   - Starts server on TEST_PORT (8001) with test database

## Running Tests

### Automated Test Runner

The easiest way to run tests:

```bash
# Run all tests (automatically uses test database)
./test_runner.py all

# Run specific test categories
./test_runner.py external all
./test_runner.py db all
./test_runner.py services all
./test_runner.py api all
```

**The test runner automatically:**
- Sets up test database
- Runs migrations on test database
- Cleans up after tests
- Never touches production database

### Manual Test Execution

You can also run individual test scripts:

```bash
# External service tests (no database required)
pipenv run python -m backend.test_scripts.test_external.test_fx_providers

# Database tests (uses test_app.db)
pipenv run python -m backend.test_scripts.test_db.db_schema_validate

# API tests (starts test server automatically)
pipenv run python -m backend.test_scripts.test_api.test_fx_api
```

## Development Server in Test Mode

You can start the development server in test mode to manually test features without affecting production data:

```bash
# Start server in TEST MODE (port 8001, test_app.db)
./dev.sh server:test
```

This is useful for:
- Manual API testing with test data
- Debugging with realistic data without risk
- Frontend development against test backend

Access the test server at:
- API docs: http://localhost:8001/api/v1/docs
- Redoc: http://localhost:8001/api/v1/redoc

## Production Server

To start the production server (port 8000, app.db):

```bash
# Start server in PRODUCTION MODE
./dev.sh server
```

## Database Management

### Working with Test Database

You can run database operations on the test database by passing the path:

```bash
# Check test database schema
./dev.sh db:check backend/data/sqlite/test_app.db

# View current migration
./dev.sh db:current backend/data/sqlite/test_app.db

# Apply migrations
./dev.sh db:upgrade backend/data/sqlite/test_app.db

# Rollback migration
./dev.sh db:downgrade backend/data/sqlite/test_app.db
```

### Working with Production Database

For production database (default if no path specified):

```bash
# Check production database schema
./dev.sh db:check

# View current migration
./dev.sh db:current

# Apply migrations
./dev.sh db:upgrade
```

## Environment Variables

LibreFolio respects the following environment variables:

- `DATABASE_URL` - Override default database path
- `TEST_DATABASE_URL` - Override default test database path  
- `LIBREFOLIO_TEST_MODE` - Enable test mode (1, true, yes)
- `PORT` - Production server port (default: 8000)
- `TEST_PORT` - Test server port (default: 8001)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING, ERROR)

## .env File

The `.env` file contains default configuration:

```bash
# Database
DATABASE_URL=sqlite:///./backend/data/sqlite/app.db

# Logging
LOG_LEVEL=INFO

# API
API_V1_PREFIX=/api/v1
```

**Important**: Environment variables take precedence over `.env` file values, but when in test mode, `DATABASE_URL` is automatically overridden regardless of `.env` content.

## Architecture Notes

### Lazy Engine Initialization

To support test mode, database engines are created lazily:

```python
# backend/app/db/session.py
def get_or_create_sync_engine():
    """Creates engine on first call, respecting test mode."""
    global _sync_engine_cache
    if _sync_engine_cache is None:
        _sync_engine_cache = get_sync_engine()
    return _sync_engine_cache
```

This ensures:
1. Test mode can be set before engine creation
2. Environment variables are respected
3. Settings are read at the right time

### Settings Override

When test mode is enabled, `get_settings()` automatically overrides the database URL:

```python
# backend/app/config.py
def get_settings() -> Settings:
    settings = Settings()
    if is_test_mode():
        settings.DATABASE_URL = settings.TEST_DATABASE_URL
    return settings
```

This ensures **all** database operations use the test database when in test mode, even if `.env` specifies production database.

## Troubleshooting

### Problem: app.db is created during tests

**Solution**: This should not happen with the current implementation. If it does:

1. Check that `LIBREFOLIO_TEST_MODE` is set in test scripts
2. Verify test mode is enabled in startup logs
3. Check `get_settings()` is called after test mode is set

### Problem: Tests fail with "port already in use"

**Solution**: Kill the process using the test port:

```bash
# Find and kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Or use the helper in test output
pkill -f 'uvicorn.*8001'
```

### Problem: Test database has wrong schema

**Solution**: Delete test database and re-run tests:

```bash
# Remove test database
rm backend/data/sqlite/test_app.db

# Re-run tests (will recreate database)
./test_runner.py all
```

## Best Practices

1. **Always use test runner** for running tests
2. **Never manually modify** production database during development
3. **Use `./dev.sh server:test`** for manual testing with test data
4. **Commit test database** to git is optional (usually in .gitignore)
5. **Document test data requirements** in test docstrings

## Related Documentation

- [Testing Guide](testing-guide.md) - How to write and run tests
- [Database Schema](database-schema.md) - Database structure
- [Environment Variables](environment-variables.md) - Configuration options

