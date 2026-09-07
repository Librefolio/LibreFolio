---
title: "Test isolation classes — what a unit may share with a concurrent one"
category: concept
date: 2026-08-31
tags: [testing, test-runner, parallelism, infrastructure, isolation]
related: [concepts/derived-test-inventory, concepts/playwright-run-consolidation, concepts/backend-test-isolation, decisions/test-runner-package-split]
related_problems: [conftest-autouse-write-breaks-pure-class, playwright-route-stub-is-per-context, registered-but-unreachable-test-actions]
---

# Concept: the four isolation classes

## Definition

Every runnable test unit — one spec file, one pytest path, one vitest file —
declares **what it needs in order not to disturb anyone else**. That declaration
is its isolation class, and it is the single rule that governs both backend and
frontend parallelism.

| Class | Meaning | May run beside… | Dedicated resource |
|---|---|---|---|
| `PURE` | touches neither DB nor server | anything, unbounded | only `COVERAGE_FILE` |
| `READ` | reads shared data, writes nothing | any number of other `READ`, **on the same backend** | none |
| `WRITE_SCOPED` | writes **only** rows belonging to its own user/broker | other `WRITE_SCOPED` **with a different user** | one E2E user |
| `WRITE_GLOBAL` | writes shared surfaces (assets, FX, prices, settings) | **nothing** | a whole database |

## Why these four, and not some other set

The classes are not invented taxonomy — they are read off the **actual data
model**. Of the twelve tables, only **two carry a `user_id`**: `UserSettings`
and `BrokerUserAccess`. `Asset`, `Transaction`, `PriceHistory`, `FxRate`,
`Broker`, `GlobalSetting`, `AssetEvent`, `FxConversionRoute` and
`AssetProviderAssignment` are all global.

`Transaction` is the instructive case: it *looks* per-user, but it has no
`user_id` at all. It hangs off `broker_id`, and the scoping happens at service
level (`transaction_service._get_accessible_broker_ids(user_id)`). So
*"writes only its own data"* is a far narrower category than it first appears —
which is exactly why the safe default is the strictest class.

This is also the point where two apparently separate problems turn out to be
one. The frontend flakiness under consolidation and the backend
`UNIQUE constraint failed: fx_rates…` were both "writes to a shared surface".
One rule governs both.

## The asymmetric default

```
PURE is proven statically. Everything not proven is WRITE_GLOBAL.
```

The asymmetry is deliberate and is written into `classify()`:

> A wrong `PURE` produces flaky parallel runs; a wrong `WRITE_GLOBAL` only costs
> speed.

`READ` and `WRITE_SCOPED` must be **declared**, never inferred: the textual
heuristic tried for them was wrong often enough to be useless.

`PURE` for pytest is proven by scanning the test file **and three helpers**
(`test_utils`, `test_db_config`, `test_server_helper`) for a broad marker list
(`get_async_engine`, `AsyncSession`, `httpx`, `TEST_PORT`, `app.db`, …). Vitest
is `PURE` by construction — in-process, no DB, no server.

> ⚠️ That proof has a hole that cost real reds: **`conftest.py` is not read**.
> See [[problems/conftest-autouse-write-breaks-pure-class]].

## `exclusive_because` — the class and its justification are one statement

```python
if entry.get("exclusive_because"):
    declared = WRITE_GLOBAL
else:
    declared = entry.get("isolation") or category_meta.get("default_isolation")
```

Declaring *why* a unit stays exclusive **is** declaring the class. Written this
way, a category-wide `default_isolation` cannot silently promote a unit somebody
has already explained must not be promoted.

The empty string is a distinct claim from an explanation:

> Empty means *"nobody has looked yet"*, which is not the same as
> *"this is safe"*, and must not be treated as one.

That distinction is what makes `default_isolation` on a category safe at all —
it is a promise made on behalf of 85 units, and the escape hatch has to be
stronger than the promise.

## What actually runs in parallel today

- **151 backend units** run in parallel — `services` 80, `api` 51, `utils` 12,
  `schemas` 8.
- **3 actions stay serial**: `api auth` (writes global users and tokens) and the
  two `e2e` ones (`brim-e2e`, `search-to-prices`).
- **Categories are serial with respect to each other, on purpose**: the suite
  swings the database deliberately — `db` populates, `services` empties, `api`
  repopulates — so there is no instant at which every category's precondition
  holds at once.
- Under `all` / `all-backend`, `_parallel_classes` returns **`(PURE,)` only**:
  `READ` and `WRITE_SCOPED` require naming a single category, because only then
  is the precondition stable.
- `db create` and `db populate` are in `SIDE_EFFECTING` and are excluded from
  the dry run entirely — they do work rather than compose a command.

## The resource broker

A worker does not receive "permission to run"; it receives a **lot of exclusive
resources**.

| Resource | Before | After | Needed by |
|---|---|---|---|
| `COVERAGE_FILE` | one global file, copied in/out of `.coverage` | `.coverage_data/parts/.coverage.wN` | **every** worker |
| `DATABASE_URL` | one shared `app.db` | `app_wN.db` | `WRITE_GLOBAL` |
| `TEST_PORT` | fixed `settings.TEST_PORT` | `TEST_PORT + N` | in-process backend workers |
| E2E user | everyone used `e2e_test_user` | one of the eight, per worker | `WRITE_SCOPED` |

The global mutable `.coverage` copy-in/copy-out was **the** forced
serialisation point of the old design: two processes cannot share a mutable
file. Replacing it with a per-worker `COVERAGE_FILE` plus a final
`coverage combine` is the single change that unlocked parallel coverage.

## Measured, not assumed

| Check | Result |
|---|---|
| 2 pytest-cov processes, separate `COVERAGE_FILE` | exit `[0,0]`, two intact 110 KB files |
| `coverage combine` over the two | "Combined 2 files", coherent report |
| `.coveragerc` | already had `parallel = true` and `sigterm = true` |
| JS coverage in parallel | monocart writes `coverage-<random>.json` per `add()` → **workers cannot collide by construction** |
| 4 read-only specs, 1 → 4 workers `--fully-parallel` | 108,7 s → **74,1 s**, 22 passed |
| 4 read-only specs, `fullyParallel: false` | 1,13× only — the slowest file is the floor |

## The finding that reframed everything

Four **writing** specs consolidated into one invocation produced **1 red at one
worker**, and the same 1 red at four workers.

> The pollution is not caused by parallelism. It is caused by **consolidation**.
> Parallelism at 4 ways added zero failures; it added 1,62×.

Which means the isolation work had to be done anyway, even if the decision had
been never to parallelise anything.

## Source files

| Role | Path |
|------|------|
| Class constants, `classify()`, `TestUnit`, `exclusive_because` | `scripts/test_runner/_inventory.py` |
| Scheduler / parallel class selection | `scripts/test_runner/_scheduler.py` |
| Worker pool and resource lots | `scripts/test_runner/_executor.py` |
| Consolidated frontend pass | `scripts/test_runner/_consolidate.py` |
| Consolidated backend pass | `scripts/test_runner/_consolidate_backend.py` |
| Coverage combine | `scripts/test_runner/_coverage.py`, `.coveragerc` |
| Service-level transaction scoping | `backend/app/services/transaction_service.py` — `_get_accessible_broker_ids` |
