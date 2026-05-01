---
name: testing-backend
description: "Use this skill when creating, modifying, or running backend Python tests with pytest, including API tests, service tests, provider tests, coverage analysis, and test database population."
---

# Backend Testing Reference

## Test Structure

```text
backend/test_scripts/
├── test_api/               # 276+ tests — REST endpoints via httpx
├── test_db/                # Database layer
├── test_services/          # Business logic
├── test_e2e/               # End-to-end backend flows
├── test_external/          # Provider + network tests
├── test_schemas/           # Pydantic validation
├── test_utilities/         # Utility functions
├── test_server_helper.py   # Auto-start server for API tests
└── test_utils.py           # Output formatting, helpers
```

## How to Run

```bash
# All backend tests (800+)
./dev.py test all-backend

# Single category
./dev.py test api all
./dev.py test db all
./dev.py test services all
./dev.py test external all    # needs network

# With coverage
./dev.py test --coverage api all

# With verbose output
./dev.py test --verbose api all


# Filter external providers (useful when a service is down)
./dev.py test --exclude-providers yfinance external asset-providers 
./dev.py test --exclude-providers yfinance all 

# Single file (bypass dev.py)
pipenv run pytest backend/test_scripts/test_api/test_assets_crud.py -v

# Single test
pipenv run pytest backend/test_scripts/test_api/test_assets_crud.py::test_create_single_asset -v
```

## API Test Architecture

API tests use `_TestingServerManager` from `test_server_helper.py`:

1. **Server as thread**: uvicorn runs in a thread within pytest process → enables `pytest-cov` coverage tracking
2. **Test port**: `TEST_PORT` (default 8001)
3. **Isolated test DB**: `backend/data/test/sqlite/app.db`
4. **HTTP Client**: `httpx.AsyncClient`

### Pattern for an API test

```python
import httpx
import pytest
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

async def create_user_and_login(client: httpx.AsyncClient) -> None:
    import uuid, time
    username = f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    await client.post(f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT)
    await client.post(f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)

@pytest.mark.asyncio
class TestFeatureX:
    @pytest.fixture(autouse=True)
    def server(self):
        mgr = _TestingServerManager()
        mgr.ensure_started()
        yield

    async def test_create_something(self):
        print_section("Create Something")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            resp = await client.post(f"{API_BASE}/something", json={...}, timeout=TIMEOUT)
            assert resp.status_code == 201
```

## Mock Data

`populate_mock_data.py` creates deterministic data:
- Users: `e2e_test_user` and `e2e_test_admin`
- Brokers: 3 brokers with shared access
- Assets: AAPL (yfinance), iShares MSCI World (JustETF), BTP (CSS Scraper), Scheduled Investment
- FX Pairs: EUR/USD, GBP/EUR, USD/CHF with mock rates
- Transactions: 10+ associated transactions

```bash
./dev.py db create-clean --test
./dev.py test db populate --force
./dev.py test db populate --force --clean --with-static --with-reports  # for gallery
```

## Coverage

```bash
./dev.py test --coverage api all
./dev.py test coverage show backend
./dev.py test coverage show combined
./dev.py test coverage-report --priority high  # uncovered functions analysis
```

## Provider Filtering (--providers / --exclude-providers)

```bash
./dev.py test external -h  # shows available provider codes
./dev.py test external asset-providers --exclude-providers yfinance
./dev.py test all --providers justetf ECB
```

## Conventions

- **Naming**: `test_*.py` for files, `test_*` for functions, `Test*` for classes
- **Isolation**: each test creates its own temporary user (`unique_id`)
- **No side effects**: tests must not depend on execution order
- **Formatted output**: use `print_section()`, `print_success()`, `print_error()` from `test_utils.py`
- **Timeout**: `TIMEOUT = 30` seconds for API calls

