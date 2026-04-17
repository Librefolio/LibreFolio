---
applyTo: "backend/test_scripts/**"
---

# Backend Testing Reference

## Structure

```text
backend/test_scripts/
├── test_api/               # 276+ tests — REST endpoints via httpx
├── test_db/                # Database layer + populate_mock_data.py
├── test_services/          # Business logic
├── test_e2e/               # End-to-end backend flows
├── test_external/          # Provider + network tests
├── test_schemas/           # Pydantic validation
├── test_utilities/         # Utility functions
├── test_server_helper.py   # _TestingServerManager (server-in-thread)
└── test_utils.py           # print_section(), print_success(), unique_id()
```

## Run Commands

```bash
./dev.py test api all              # REST endpoint tests
./dev.py test db all               # Database tests
./dev.py test services all         # Service layer
./dev.py test external all         # Provider tests (needs network)
./dev.py test e2e all              # Backend end-to-end
./dev.py test all-backend          # All backend categories
./dev.py test --coverage api all   # With coverage tracking
```

See skill `testing-backend` for full details on patterns, fixtures, coverage, and provider filtering.

## API Test Pattern

```python
import httpx, pytest
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

@pytest.mark.asyncio
class TestFeatureX:
    @pytest.fixture(autouse=True)
    def server(self):
        _TestingServerManager().ensure_started()
        yield

    async def test_something(self):
        async with httpx.AsyncClient() as client:
            # create_user_and_login(client) → then test
            ...
```

## Conventions

- **Naming**: `test_*.py` files, `test_*` functions, `Test*` classes
- **Isolation**: each test creates its own temporary user (`unique_id`)
- **No side effects**: tests must not depend on execution order
- **Formatted output**: use `print_section()`, `print_success()` from `test_utils.py`
- **Timeout**: `TIMEOUT = 30` for API calls

