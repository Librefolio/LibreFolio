---
title: "Unique test identifiers (unique_id)"
category: concept
tags: [testing, backend, naming, pytest, conventions]
related:
  - concepts/test-isolation-classes
  - concepts/backend-test-isolation
  - entities/test-runner
related_features: [F-068]
---

# Concept: Unique test identifiers

> Split out of [[concepts/backend-test-isolation]] on 2026-09-01. That page bundled
> two claims: a **naming convention** (valid) and an **isolation guarantee** (false).
> This page keeps the convention. The isolation question is answered by
> [[concepts/test-isolation-classes]].

## Definition

Backend tests do not hard-code names for the rows they create. They derive them
from `unique_id()`, so that a test's user, asset, broker or pair never collides
with one left behind by another test or an earlier run.

```python
from backend.test_scripts.test_utils import unique_id

username = unique_id("test")            # -> "test_1756678123456_17"
asset    = f"Test Asset {unique_id()}"
broker   = f"Test Broker {unique_id()}"
```

## What `unique_id()` actually is

`backend/test_scripts/test_utils.py` (~L174-182):

```python
_counter = 0


def unique_id(prefix: str = "TEST") -> str:
    """Generate unique identifier for test data."""
    global _counter
    _counter += 1
    return f"{prefix}_{int(time.time() * 1000)}_{_counter}"
```

**A millisecond timestamp and a process-global counter. No UUID4.** Earlier wiki
text — and the docstring quoted in it — described a `uuid.uuid4().hex[:4]` suffix.
That is not the code and, from the evidence, never was.

## What follows from that, precisely

| Property | Holds? | Why |
|---|---|---|
| Unique **within one process** | ✅ | `_counter` monotonically increases for the life of the interpreter |
| Unique **across processes** | ❌ | `_counter` restarts at `0` in every new process. Two units started in the same millisecond by two workers produce **identical** identifiers |
| Unique **across runs** | ⚠️ | only via the millisecond timestamp — same guarantee as above |
| Protects rows keyed on a **natural key** | ❌ | see below |

The last row is the one that costs time. A unique *name* does nothing for a table
whose uniqueness constraint is on something else. Running `pytest test_services/`
in a **single process** produced three failures with:

```
UNIQUE constraint failed: fx_rates.date, fx_rates.base, fx_rates.quote
```

`fx_rates` is keyed on `(date, base, quote)`. No amount of name-uniqueness reaches
it. The same applies to any row whose identity is a business key rather than a
generated string.

## The convention that remains

- **Never hard-code credentials or entity names** in backend API tests. Derive them.
- **Never assert on global counts** (`len(users) == 3`): the test DB accumulates.
- **Do not read `unique_id()` as a parallelism guarantee.** It is a naming helper.
  What may run next to what is decided by [[concepts/test-isolation-classes]]
  (`pure` / `read` / `write-scoped` / `write-global`), declared per action via
  `add_test(..., isolation=...)`.
- E2E frontend tests are the deliberate exception: Playwright needs stable
  credentials, so it uses `TEST_USER` / `TEST_ADMIN` from `test-users.ts` and
  the deterministic users made by `populate_mock_data.py`.

## If it needs strengthening

The cheap fix, should cross-process collisions ever be observed, is to fold the
PID (or the worker index the executor already injects) into the string:

```python
return f"{prefix}_{os.getpid()}_{int(time.time() * 1000)}_{_counter}"
```

Recorded here as an option, **not** as something that has been done.

## Source files

| Role | Path |
|------|------|
| `unique_id()` | `backend/test_scripts/test_utils.py` (~L174-182) |
| Shared engine used by service tests | `backend/app/db/session.py` — `get_async_engine()` (~L105) |
| Deterministic users (E2E exception) | `backend/test_scripts/test_db/populate_mock_data.py` |
| Frontend stable credentials | `frontend/e2e/fixtures/test-users.ts` |
| Isolation classes / scheduler | `scripts/test_runner/_inventory.py`, `scripts/test_runner/_scheduler.py` |
| Per-worker environment | `scripts/test_runner/_executor.py` — `_worker_env()` |
| Source KB file | `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md` |
