---
title: "E2E Python coverage silently reads 0,00 % above two workers"
category: problem
status: resolved
date: 2026-08-28
tags: [testing, coverage, python, multiprocessing, uvicorn, silent-failure]
related: [concepts/coverage-rate-vs-volume, concepts/test-isolation-classes]
---

# Problem: five coverage files written, all empty, no warning

## Symptom

| run | files written | measured |
|---|---|---|
| `--workers 8` (4 uvicorn workers), **whole suite** | 5 | **0,00 %** |
| `--workers 2` (1 uvicorn worker), **one spec** (`tx-tooltips`) | 1 | **35,01 %** |

A single spec measures 35 % of the backend; the entire suite measures zero.

## Root cause

Not deduced — read off the configuration. `.coveragerc` declared
`concurrency = thread,gevent` and **not** `multiprocessing`.

Above two clients, `server_workers_for = ceil(clients / 2)` starts uvicorn with
more than one worker. Uvicorn **forks** them, and `coverage run` measures only
the parent — which serves no requests.

The five files are written normally and are **empty**, so nothing warns. The
count drops and it looks like untested code.

## Why it matters beyond the number

Backend percentages compared throughout the campaign were taken at **different
worker counts**. Part of the movement attributed to new tests was measurement
noise. This is the third time in this project that coverage has been lost
*without failing*:

> A measuring instrument that does not fail when it loses half its data is worse
> than one that breaks.

The two earlier instances: a two-step merge and a `gracefulShutdown` in P7, both
losing data silently. A fourth was then found in the new code itself —
`_run_group()` copied the accumulated coverage database **in** but never copied
it back **out**, unlike `run_command()` which does it in a `finally`. Effect:
pytest-cov writes `.coverage`, the next reader finds `.coverage_data/backend`
unchanged, and **an entire category's measurement disappears without a single
red**. It was found because the verification step was mandatory, not because
anyone suspected it.

## Options considered

1. `concurrency = multiprocessing,thread,gevent` in `.coveragerc` — correct, but
   uvicorn has its own worker supervision, so it needed proving.
2. Force **one** uvicorn worker whenever coverage is on — trivial and safe, but
   slows every coverage run.

**Decision (user): option 1**, plus a full re-run.

## What stays true regardless

The E2E server measurement is a **distinct** artefact (`htmlcov-backend-e2e`)
covering the external server on port 6041 that Playwright drives. It is *not*
the backend test measurement, which runs in-process:

> `test_server_helper.py` starts uvicorn in a **thread of the same pytest
> process**, precisely so that `concurrency = thread` traces it. The API routes
> are therefore measured (75–100 % in `.coverage_data/backend`) regardless.

Merged in, the E2E server measurement is worth **+0,36 points** (90,10 → 90,46
on the mixed scale) — not the +2,23 first assumed
([[problems/coverage-percent-mixed-lines-and-branches]]). Its value is knowing
**which backend paths the E2E tests touch**, not raising the total.

A good capture was archived at 25,78 %; after the fix the full run reported
**28,75 %**.

## Prevention

Any coverage artefact that can be written **empty** needs a non-zero assertion at
the end of the run, or a comparison against the previous capture. Files existing
is not evidence that data was collected.

## Source files

| Role | Path |
|------|------|
| Coverage config | `.coveragerc` |
| Worker-count derivation | `scripts/test_runner/_server.py` — `server_workers_for` |
| In-process test server | `backend/test_scripts/test_server_helper.py` |
| Coverage copy in/out | `scripts/test_runner/_common.py` — `run_command`, `_consolidate_backend.py` — `_run_group` |
| E2E server artefact | `htmlcov-backend-e2e/`, `.coverage_data/frontend` |
