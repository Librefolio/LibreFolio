---
title: "Playwright run consolidation, and why the batch is eight"
category: concept
date: 2026-08-31
tags: [testing, playwright, frontend, coverage, parallelism, performance]
related: [concepts/test-isolation-classes, concepts/transaction-hygiene-fixture, concepts/derived-test-inventory]
related_problems: [env-var-injection-point-duplicated, playwright-route-stub-is-per-context]
---

# Concept: consolidation trades process **count** for process **lifetime**

## The trade

The old runner spawned one Playwright process per spec file. Each paid the full
fixed cost — build check, DB check, browser launch, login — and threw it away.
Consolidation runs many specs in **one** invocation, so a category pays setup a
handful of times instead of once per spec.

Measured across eight frontend categories at `--workers 4`:

| category | after | before |
|---|---|---|
| `front-transaction` | **5,6 min** | 16,7 (runner) / 17,8 (serial) |
| `front-utility` | 2,7 min | — |
| `front-asset` | 2,3 min | — |
| `front-fx` | 1,4 min | 3,2 (serial) |
| `front-broker` | 0,8 min | — |

## The ceiling that consolidation introduces

Fewer processes means **longer-lived** processes, and under JS coverage that has
a hard limit.

`startJSCoverage({ resetOnNavigation: false })` makes every test return the V8
coverage of *every script loaded since the start*, and **each entry carries the
script's full source**. While each spec had its own process, that memory was
reclaimed by the process dying. Consolidated, it is not.

Measured:

| batch | outcome |
|---|---|
| 8 specs / 163 tests / 7,8 min | completes with room to spare |
| 25 specs / 215 tests / 20 min | **dies of heap exhaustion** |

> The growth tracks **how long the worker lives**, not what any single spec does.

Hence `_JS_COVERAGE_CHUNK = 8`: chunking bounds the lifetime without giving up
the win. Plus `NODE_OPTIONS=--max-old-space-size=8192`, because Node's default
old space is not sized for it.

The failure mode is what makes this worth writing down:

> Running out of heap shows up as **an unrelated test dying with `SIGABRT`** — a
> failure that names the victim and never the cause.

## It is test instrumentation, not a product leak

The memory that exploded belonged to the **Node process of Playwright**, not to
the browser and not to the backend. No component in the product accumulates its
own sources, so there is no product equivalent.

*(A genuine product caching defect did surface during the same investigation,
by a different route: [[problems/namedcache-clear-leaves-admission-filter]].)*

## Chunking is off without JS coverage

```python
batches = _chunk(specs, _JS_COVERAGE_CHUNK) if (coverage and _COVERAGE_JS) else [specs]
```

Without JS coverage the accumulator does not exist, so the whole category runs in
one invocation.

## `project=None` means every project

Some actions (the AI Export ones) deliberately pass `project=None`, which runs
**desktop *and* mobile**. Narrowing them to `desktop` when grouping would halve
what runs — silently. The inventory records the project selector per unit
(`ALL_PROJECTS = "*"`) so that grouping cannot lose it.

## A missing spec is a failed spec

The verdict is read back from the Playwright JSON report per spec path. A spec
absent from the report is reported **failed**, on the principle that silence
must never read as success — which is exactly how a run loses units without
anything going red.

## Two things consolidation broke on the way in

**The transaction hygiene fixture.** Its correctness rested on "one worker runs
one file start to finish, alone", which per-test scheduling removes. See
[[concepts/transaction-hygiene-fixture]].

**A half-wired environment variable.** There are **two** paths that launch
Playwright — `_frontend_common._run_playwright` for a unit and
`_consolidate.run_playwright_group` for a consolidated category — and only one
had `--workers` wired. The run stayed green and took three times as long, saying
nothing. See [[problems/env-var-injection-point-duplicated]].

## Source files

| Role | Path |
|------|------|
| Chunking, `run_playwright_group`, verdict parsing | `scripts/test_runner/_consolidate.py` |
| Per-unit Playwright launch | `scripts/test_runner/_frontend_common.py` |
| Single worker-count injection point | `scripts/test_runner/_common.py` — `apply_e2e_workers` |
| Project selector in the inventory | `scripts/test_runner/_inventory.py` — `ALL_PROJECTS` |
| Playwright config | `frontend/playwright.config.ts` |
| Coverage collection | `frontend/e2e/fixtures/` (monocart) |
