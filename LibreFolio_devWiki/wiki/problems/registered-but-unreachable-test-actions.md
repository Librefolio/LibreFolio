---
title: "Six registered test actions that no suite could reach"
category: problem
status: resolved
date: 2026-08-29
tags: [testing, test-runner, orphans, tooling, silent-failure]
related: [concepts/derived-test-inventory, concepts/test-isolation-classes]
---

# Problem: `check-orphans` verified string presence, not reachability

## Symptom

Six actions — roughly **273 tests** — were registered, runnable by name, green
when run, and executed by **no** `all` suite.

| action | what it holds |
|---|---|
| `fx-csv-import` | FX CSV import specs |
| `utilities` | utility specs |
| `core-unit` | core unit tests |
| `tx-unit` | transaction unit tests |
| `user-unit` | user unit tests |
| `store-unit` | store unit tests |

They had passed continuously. Nobody was running them.

## Root cause

Two independent failures that covered for each other.

**1 — the `all` lists were hand-written.** The frontend `all` suites enumerated
their member actions literally instead of deriving them from the registry via
`_get_category_tests_for_all()`. Anything added later had to be added twice, and
the second edit was the one that got forgotten.

**2 — the orphan check asked the wrong question.** It scanned action bodies with

```python
re.finditer(r"([a-z_-]+\.spec\.ts)", content)
```

and reported a spec as covered if the **string appeared anywhere** in the module.
A spec named inside an action that no suite calls satisfies that regex perfectly.
The check verified **presence**, never **reachability**.

## Why it stayed hidden

The failure mode of an unreachable action is *nothing*. No red, no warning, no
missing output — the suite simply runs fewer tests than the reader believes, and
the count is not published anywhere a human compares.

It is the same shape as
[[problems/env-var-injection-point-duplicated]]: an option that travels through a
second, uninstrumented path does not fail — **it goes quiet**.

## Fix

- The `all` lists are now **derived from the registry**, so registering an action
  is the single act that makes it reachable
  ([[concepts/derived-test-inventory]]).
- `check-orphans` was rewritten to resolve **reachability from an `all` suite**,
  not string presence.
- `EXCLUDED_SPECS = {"gallery.spec.ts"}` is the only legitimate exclusion — the
  gallery is a screenshot generator, not a test — and it is now an explicit,
  named exclusion rather than an accident.

## Prevention

> A coverage-of-the-runner check must answer *"can this be reached from an entry
> point?"*. Any check that answers *"is this mentioned?"* will pass on the day it
> matters.

## Source files

| Role | Path |
|------|------|
| `check-orphans` action + implementation | `scripts/test_runner/_cli.py` — registered ~L462/L505, `_check_orphan_tests()` ~L154, dispatched ~L597 |
| Reachability resolution | `scripts/test_runner/_inventory.py` — `reachable_paths()`, `on_disk()`, `is_covered()` |
| `EXCLUDED_SPECS = {"gallery.spec.ts"}` | `scripts/test_runner/_inventory.py` (~L55) |
| `all` derivation from the registry | `scripts/test_runner/_common.py` — `_get_category_tests_for_all()` (~L322) |
| Registry assembly | `scripts/test_runner/_registry.py` |
| Frontend action definitions | `scripts/test_runner/_frontend_transaction.py`, `_frontend_utility.py`, `_frontend_user.py`, `_frontend_fx.py` (one module per category — there is no `actions/` package) |

> **Path note (2026-09-01)**: this table previously cited `scripts/test_runner/_orphans.py`
> and `scripts/test_runner/actions/frontend.py`. Neither has ever existed; both were
> invented at ingest time. `_get_category_tests_for_all` was also misattributed to
> `_inventory.py`. Corrected against the tree.
