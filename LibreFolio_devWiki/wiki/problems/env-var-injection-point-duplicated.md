---
title: "Two launch paths, one wired: the option that goes quiet instead of failing"
category: problem
status: resolved
date: 2026-08-29
tags: [test-runner, env-vars, parallelism, silent-failure, tooling]
related: [concepts/silent-no-op-option, concepts/playwright-run-consolidation, concepts/derived-test-inventory]
---

# Problem: `E2E_WORKERS` reached one of the two Playwright launchers

## Symptom

**Nothing.** The suite was green. It took three times longer than it should have.

## Root cause

Two code paths invoke Playwright — the ordinary per-action run and the
consolidated run. `E2E_WORKERS` was injected into the environment in one of them.
The other launched Playwright with the default worker count and no complaint.

An environment variable that fails to arrive produces a **default**, not an
error. So the second path did not break; it went quiet, and the only evidence was
a wall-clock time nobody had a baseline for.

## Fix

Extracted `_common.apply_e2e_workers(env)` and made **both** paths call it. The
injection point is now singular by construction.

## The rule

> When an option travels by environment variable, the injection point must be
> made unique. Otherwise the second path does not fail — **it goes silent**, and
> silence is indistinguishable from correct behaviour.

The same shape, in a different subsystem, is
[[problems/registered-but-unreachable-test-actions]]: a check that verified
string presence rather than reachability. Both are "the mechanism reports no
problem because it was never asked the right question".

## Re-measurement after the fix

**216 tests in 5,6 minutes — 3,0× the previous throughput.**

That figure is the whole point of the page: the fix bought nothing in
correctness and a factor of three in time, and it would never have been found by
a failing test.

## Prevention

Any environment-carried option should either

- be injected in exactly one function that every launcher must call, or
- be **asserted on the receiving side** — the runner reads the value back and
  fails loudly when it is missing.

## The pattern this belongs to

This is one of four incidents with the same shape, named at
[[concepts/silent-no-op-option]] — *accepted is not arrived*: an option is declared,
the parser accepts it, and the mechanism it was meant to reach never receives it.
The failure mode is a **default**, not an error. Siblings:
[[problems/resume-mode-stale-import]], [[problems/coverage-mode-stale-import]],
[[problems/coverage-report-category-dest-collision]],
[[problems/env-var-injection-point-duplicated]].

## Source files

| Role | Path |
|------|------|
| Single injection point | `scripts/test_runner/_common.py` — `apply_e2e_workers()` (~L89) |
| Consolidated launcher | `scripts/test_runner/_consolidate.py` (~L186) |
| Per-action launcher | `scripts/test_runner/_frontend_common.py` (~L332) |
| Playwright worker config | `frontend/playwright.config.ts` |

> **Path note (2026-09-01)**: the per-action launcher row previously read
> `scripts/test_runner/actions/frontend.py`. That file — and the whole `actions/`
> package — has never existed; the path was invented at ingest time. The runner
> package has a **flat** layout (`_frontend_*.py`), see [[entities/test-runner]].
