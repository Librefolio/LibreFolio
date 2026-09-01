---
title: "Backend Test Isolation via unique_id (RETIRED)"
category: concept
status: retired
retired: 2026-09-01
superseded_by:
  - concepts/test-isolation-classes
  - concepts/unique-test-identifiers
tags: [testing, backend, isolation, pytest, retired]
related:
  - concepts/test-isolation-classes
  - concepts/unique-test-identifiers
  - entities/test-runner
related_features: [F-068]
---

# ⛔ RETIRED — Backend Test Isolation via `unique_id`

> **Retired 2026-09-01, not amended.** Its central claim — that `unique_id()`
> makes backend tests hermetic, order-independent and parallel-safe — is false,
> and the false part cannot be edited out without leaving a page that argues with
> itself. Nothing below should be relied on.
>
> | If you came here for | Read |
> |---|---|
> | *Can these two tests run in parallel?* | [[concepts/test-isolation-classes]] — the real answer, and the one the runner acts on |
> | *How do I name test data?* | [[concepts/unique-test-identifiers]] — the convention, which is still correct |
> | *How does the runner schedule?* | [[entities/test-runner]] |
>
> **Why it was wrong.** `unique_id()` is a millisecond timestamp plus a
> **process-global counter** — no UUID4, despite what this page said twice.
> The counter restarts at `0` in every process, so two units launched in the same
> millisecond by two workers generate the *same* identifier. And even within one
> process a unique *name* does not protect a row keyed on a natural key:
> `pytest test_services/`, single process, failed three times on
> `UNIQUE constraint failed: fx_rates.date, fx_rates.base, fx_rates.quote`.
>
> The page is kept, rather than deleted, because it is cited from older sources
> and because the shape of the error — *"we named things uniquely, therefore we
> are isolated"* — is worth being able to point at.

---

## ⚠️ Historical content below — retained for provenance only

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


## ⚠️ 2026-08 caveat — itself corrected 2026-09-01

The original caveat was right in substance and **wrong in every figure it cited**.
It claimed "56 files use the shared file; only 16 use `:memory:`". Counted against
the tree on 2026-09-01:

| Measure | Claimed 2026-08 | Actual | How counted |
|---|---|---|---|
| Test files using `:memory:` | 16 | **7** | `grep -rl ":memory:" backend/test_scripts --include=*.py` — all 7 are `test_services/test_ai_export_*` |
| Test files reaching the shared engine | 56 | **36** | `grep -rl "get_async_engine" backend/test_scripts --include=*.py` |
| Test files in total (`test_*.py`) | — | **195** | `find backend/test_scripts -name "test_*.py"` |
| `test_` functions in `test_api/` | "276+ tests" | **645** | `grep -rhE "^\s*(async )?def test_" backend/test_scripts/test_api/` |

### There is no single `session` fixture

The 2026-08 note spoke of "**the** `session` fixture" as if one object existed
that somebody owned. There are **ten**, each redefined locally, each in a different
file under `test_services/`, all `@pytest_asyncio.fixture` with **no scope
argument** — that is, all function-scoped:

```
test_services/test_ai_export_components_fx.py:86
test_services/test_user_profile.py:39
test_services/test_transaction_service.py:58
test_services/test_transaction_edge_cases.py:52
test_services/test_ai_export_components_drawdown_context.py:134
test_services/test_financial/test_portfolio_service.py:55
test_services/test_financial/test_lots_analysis_service.py:90
test_services/test_ai_export_components_asset_fx_integration.py:105
test_services/test_broker_service.py:66
test_services/test_date_sentinel.py:36
```

Nine of them take an `engine` fixture; one (`..._drawdown_context.py`) takes
nothing and builds its own.

The old note closed with *"needs to be reconciled by whoever owns the fixture"*.
**Nobody owns it, because it does not exist as a single thing.** Centralising the
session fixture is work that has to be **built** — ten local definitions collapsed
into one shared, explicitly scoped fixture — not a question to be routed to an
owner. Recorded here as an open task, unclaimed.

## Source files

| Role | Path |
|------|------|
| `unique_id()` (real implementation) | `backend/test_scripts/test_utils.py` (~L174-182) |
| Shared engine singleton | `backend/app/db/session.py` — `get_async_engine()` (~L105) |
| Test server manager | `backend/test_scripts/test_server_helper.py` |
| API tests | `backend/test_scripts/test_api/` |
| Mock data (E2E only) | `backend/test_scripts/test_db/populate_mock_data.py` |
| Source KB file | `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md` |
| Replacement — isolation | `LibreFolio_devWiki/wiki/concepts/test-isolation-classes.md` |
| Replacement — naming | `LibreFolio_devWiki/wiki/concepts/unique-test-identifiers.md` |
