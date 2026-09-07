---
title: "An autouse conftest fixture wrote to the shared DB and broke the PURE class"
category: problem
status: resolved
date: 2026-08-29
tags: [testing, pytest, isolation, sqlite, backend, parallelism]
related: [concepts/test-isolation-classes, concepts/derived-test-inventory]
---

# Problem: `classify()` proves purity from test files it does not fully read

## Symptom

Tests classified `PURE` — allowed to run alongside anything, on no dedicated
resource — were nevertheless touching `app.db`.

## Root cause

`backend/test_scripts/conftest.py` declares a fixture with
`scope="session", autouse=True` that opens `app.db` with raw `sqlite3` and
**writes**.

`classify()` reaches its verdict by scanning the **test module** for impurity
markers (`_IMPURE_MARKERS`). It does not read `conftest.py`, so a side effect
injected by an autouse fixture is invisible to the static proof. The default is
asymmetric by design — `PURE` must be *proved*, everything else falls back to
`WRITE_GLOBAL` — and here the proof was being granted on incomplete evidence.

## Three sharp edges found in that fixture

| edge | detail |
|---|---|
| **No `busy_timeout`** | raw `sqlite3.connect()` uses the stdlib default of **5 000 ms**, against the **30 000 ms** the app configures in `session.py`. Under a parallel run, the fixture is the first thing to give up. |
| **Connection never closed** | `with sqlite3.connect(...)` commits on exit but does **not** close. The handle is released by GC, at an unpredictable moment, holding a lock nobody can attribute. |
| **`except sqlite3.Error: pass`** | swallows everything, including the lock errors the first two edges produce. |

## Fix

```python
with contextlib.closing(sqlite3.connect(db_path, timeout=30)) as conn:
    ...
```

plus splitting the error branch: `no such table` stays silent (legitimate on a
fresh database), everything else goes through `warnings.warn`.

Explicitly rejected: making the fixture's writes invisible by pointing it at a
temp database. The fixture exists to touch the real one; hiding that would have
solved the classification and broken the fixture.

## The general rule

> Purity is a property of everything that runs, not of the file you read. A
> static classifier that stops at the test module will over-promise the moment
> an autouse fixture is added upstream.

`conftest.py` files are now treated as an explicit exception to the `PURE`
proof — a test module cannot be `PURE` if a `conftest.py` in its path performs a
side effect.

## Source files

| Role | Path |
|------|------|
| Offending fixture | `backend/test_scripts/conftest.py` |
| Classifier | `scripts/test_runner/_inventory.py` — `classify`, `_IMPURE_MARKERS` |
| App-side timeout for comparison | `backend/app/db/session.py` |
