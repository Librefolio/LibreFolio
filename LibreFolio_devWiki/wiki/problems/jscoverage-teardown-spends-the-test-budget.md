---
title: "Under coverage and load, collecting the JS coverage at teardown ran out the after-hooks slot: the fixture had no budget of its own (V-28)"
category: problem
status: resolved
date: 2026-10-13
tags: [testing, e2e, playwright, coverage, fixtures, timeout, load, workstream-r, workstream-v, release-1.2]
related:
  - sources/r-full-run-coverage-2026-10-12
---

# Problem: the coverage collection inside the test's budget

## Symptom

In R's full run with coverage ([[sources/r-full-run-coverage-2026-10-12]]), 15 of the 29 E2E reds were tests that had passed their steps and timed
out while their JS coverage was being collected. They exist only with `--coverage js` and under load; run alone, they
pass.

## Root Cause

The `jsCoverage` fixture collects the coverage in its teardown and has no `timeout` of its own. *Corrected on
2026-10-13* (V, checked in Playwright 1.61's source): such a teardown does not count against the 30 s of the test's
body, but against the after-hooks slot — also 30 s, and shared with `afterEach`. That is why R's failing durations
read as the body plus 30 s. Under load, the collection runs that slot out.

The slot is also shared with the other fixtures' teardowns.

## Solution

V-28 (`d1a149afa`, 2026-10-13, train 87): the fixture declares its own budget, `{scope: 'test', auto: true,
timeout: JS_COVERAGE_TIMEOUT_MS}` with `JS_COVERAGE_TIMEOUT_MS = 120_000`. Its teardown now has a slot of its own: a
collection that is really too slow fails by name, «Fixture "jsCoverage" timeout of 120000ms», instead of eating the
after-hooks.

The proof, at one worker with a delay injected into the collection and then removed: without the cure
«Tearing down "jsCoverage" exceeded the test timeout of 30000ms»; with it, green, and the delay ran its full 35.0 s.
Under load, `--fresh-run --coverage js --workers 4 front-fx all` was green: 103 E2E, no teardown timeout, the longest
test 9.6 s.

## Prevention

A fixture that does slow work in its teardown needs its own `timeout`: without one it borrows a slot that belongs to
every after-hook of the test, and fails in someone else's name.

## Source files

| Role | Path |
|------|------|
| The `jsCoverage` fixture | `frontend/e2e/fixtures/playwright.ts` |
| The test timeout | `frontend/playwright.config.ts` |
| R's report (§3.2) | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
| V's lot (V-28) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
| Developer docs | `mkdocs_src/docs/developer/test-walkthrough/coverage-model.md` |
