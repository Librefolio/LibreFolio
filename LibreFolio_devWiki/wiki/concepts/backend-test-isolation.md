---
title: "Backend Test Isolation via unique_id"
category: concept
tags: [testing, backend, isolation, pytest]
related_features: [F-068]
---

# Concept: Backend Test Isolation via unique_id

## Definition

Every backend API test creates its own **temporary user** using `unique_id()` from `test_utils.py` (combines timestamp + UUID4 for guaranteed uniqueness). This ensures **zero cross-test state contamination**: each test is hermetic, order-independent, and can run in parallel (if pytest workers > 1).

## Pattern

```python
from backend.test_scripts.test_utils import unique_id

async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Helper: crea utente temporaneo e loggalo."""
    import uuid, time
    username = f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    await client.post(f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT)
    await client.post(f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"},
        timeout=TIMEOUT)
```

Every test calls `create_user_and_login()` in its setup → fresh user, fresh session, no shared state.

## Why This Approach

1. **No test order dependency**: Test A can't break Test B by polluting user data
2. **Parallel-safe**: multiple pytest workers can run simultaneously without conflicts
3. **Isolated DB state**: each test sees only its own user's data (assets, brokers, FX pairs, etc.)
4. **No cleanup needed**: temporary users accumulate in test DB but don't interfere (test DB is wiped by `./dev.py db create-clean --test` between sessions)
5. **Reproducible failures**: re-running a single test always produces the same result

## Where It Applies

- **All API tests** in `backend/test_scripts/test_api/` (276+ tests)
- **E2E backend flows** in `backend/test_scripts/test_e2e/`
- **NOT service tests**: `test_services/` tests business logic directly, no HTTP layer, no user creation

## Test DB vs Production DB

| Database | Location | Usage |
|----------|----------|-------|
| Production | `backend/data/prod/sqlite/app.db` | Real app data (port 6040) |
| Test | `backend/data/test/sqlite/app.db` | Isolated test data (port 6041) |

`_TestingServerManager` auto-starts backend on TEST_PORT (6041) with test DB. Production server never touched during tests.

## Mock Data Exception

`populate_mock_data.py` creates **deterministic users** (`e2e_test_user`, `e2e_test_admin`) for:
- E2E frontend tests (Playwright) — need stable credentials across test runs
- Gallery screenshots — need reproducible state

But backend API tests use `unique_id()` instead for maximum isolation.

## Relation to unique_id() Function

```python
def unique_id(prefix: str = "test") -> str:
    """
    Generate a unique identifier for test data.
    Uses timestamp + UUID4 to guarantee uniqueness across parallel tests.
    
    Args:
        prefix: Optional prefix (default: "test")
        
    Returns:
        Unique string like "test_1714089234567_a3f2"
    """
    import uuid
    import time
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
```

Used not just for usernames but also for:
- Asset names: `f"Test Asset {unique_id()}"` in `test_assets_crud.py`
- Broker names: `f"Test Broker {unique_id()}"` in `test_brokers_api.py`
- FX pair base/quote: `f"TEST{unique_id()[:4].upper()}"` in `test_fx_api.py`

## Conventions

- **Every test creates its own user**: never hard-code test credentials in API tests
- **No assertions on user count**: test DB accumulates users, but tests must not depend on DB state from previous runs
- **Cleanup not required**: test DB is ephemeral — wipe via `./dev.py db create-clean --test` when needed
- **Use TEST_USER only in E2E**: frontend Playwright tests use `TEST_USER` / `TEST_ADMIN` from `test-users.ts` (stable credentials needed for multi-test sessions)

## Source files

| Role | Path |
|------|------|
| unique_id function | `backend/test_scripts/test_utils.py` |
| Test server manager | `backend/test_scripts/test_server_helper.py` |
| API tests | `backend/test_scripts/test_api/` |
| Mock data (E2E only) | `backend/test_scripts/test_db/populate_mock_data.py` |
| Source KB file | `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md` |
