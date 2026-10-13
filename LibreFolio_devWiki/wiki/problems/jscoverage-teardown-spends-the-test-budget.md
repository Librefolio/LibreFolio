---
title: "Under coverage and load, collecting the JS coverage at teardown spends the test's own 30 s: the fixture has no budget of its own"
category: problem
status: open
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

## Status

Open: V-28 — a `timeout` on the fixture, which gives its teardown a slot of its own; workstream V's next lot.

## Source files

| Role | Path |
|------|------|
| The `jsCoverage` fixture | `frontend/e2e/fixtures/playwright.ts` |
| The test timeout | `frontend/playwright.config.ts` |
| R's report (§3.2) | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
