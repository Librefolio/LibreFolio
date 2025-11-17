# API Tests

Testing REST API endpoints.

> 📖 **Back to**: [Testing Guide](./README.md)

---

## Overview

API tests verify **REST API endpoints** with HTTP requests/responses.

**Server**: Auto-starts test server on port 8001 if not running

**Run**: `./test_runner.py api all`

---

## Test Suites

### 1. FX API

**File**: `backend/test_scripts/test_api/test_fx_api.py`

**Coverage**: 15+ tests

**What it tests**:
- `GET /api/v1/currencies` - List available currencies
- `POST /api/v1/fx/sync` - Sync rates from ECB
- `GET /api/v1/fx/convert` - Currency conversion
- Error handling (invalid currencies, missing rates)
- Validation (request/response schemas)

**Server management**: Auto-starts and stops test server

**Run**: `./test_runner.py api fx`

**See**: [FX API Reference](../fx/api-reference.md)

---

## Running API Tests

```bash
# All API tests
./test_runner.py api all

# Specific test
./test_runner.py api fx

# Manual server control
./dev.sh server  # Start in terminal 1
./test_runner.py api fx  # Run in terminal 2
```

---

## Test Server Configuration

**Port**: 8001 (configurable via `TEST_PORT` env var)

**Auto-start**: Test runner starts server if not running

**Auto-stop**: Test runner stops server after tests complete

**Troubleshooting**: If port 8001 occupied, you'll see helpful instructions

---

## Related Documentation

- **[API Development Guide](../api-development-guide.md)** - How to add endpoints
- **[FX API Reference](../fx/api-reference.md)** - FX endpoints documentation
- **[Testing Guide](./README.md)** - Main testing documentation

---

**Last Updated**: November 17, 2025

