---
title: "R's full run with coverage (2026-10-12, on train 68): 29 E2E reds, 27 of them load; backend 91.51 %, JS 71.24 %"
category: source
source_type: report
date_ingested: 2026-10-13
original_path: LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md
tags: [testing, coverage, full-run, triage, load, e2e, playwright, release-1.2, workstream-r]
related:
  - problems/jscoverage-teardown-spends-the-test-budget
  - problems/login-returns-before-the-app-has-started
  - problems/toolbar-measurements-differed-by-the-scrollbar-gutter
  - problems/broker-detail-tests-over-budget-under-load
---

# Source: the full run with coverage, and the triage of its reds

## Summary

Workstream R ran the whole suite with coverage on train 68 (`a5653f9ef`), at two workers, from 19:40 to 00:02 —
4 h 21 min, at a load between 9.6 and 151. Ten of fifteen categories were green; pytest 12 627 passed and vitest
10 760, with no red; Playwright 1 163 passed and **29 failed**, all on desktop.

## Key takeaways

- **Coverage**: backend from its tests 91.51 % (lines 93.53 %, branches 84.78 %), from the E2E 29.32 %; frontend
  71.24 % of statements (62.82 % of branches). The drop since 2026-09-03 is the PAC planner alone — 7 008 statements
  at 14 % (C-69); without `features/tools` the frontend is at 78.4 %.
- **The 29 reds**: 27 are load — the eleven actions re-run alone gave 142 of 142 —, two are V-19's Spanish toolbar,
  already cured in train 72 ([[problems/toolbar-measurements-differed-by-the-scrollbar-gutter]]); none is environment
  or interference between tests.
- **Under the load reds, two budgets that the load can exceed**, to be cured by V in its next lot:
  [[problems/jscoverage-teardown-spends-the-test-budget]] (15 reds) and
  [[problems/login-returns-before-the-app-has-started]] (9 reds). The other three: an FX detail after a click (2) and
  the transaction table over 10 s (1).
- **Backlog**: C-67 (each JS-coverage invocation rebuilds the frontend twice), C-68 (Playwright's artefacts vanish at
  the next category), C-69 (the PAC planner's JS coverage).
- Also closed on the same day, in I's lot 50: C-58 — [[problems/broker-detail-tests-over-budget-under-load]].

The release page cites this run among the checks of 1.2.0, next to the final run: [[sources/release-1.2.0]]. *Update
(2026-10-14)*: R's final run, on `10e646f79`, had **0 reds** — pytest 12 936, vitest 11 515, Playwright 1 221 — at a
much lower load (8.9 on average against 37.9), so the load cures are proven at normal load only (C-82); its report
is `report-R-final-run-coverage-20261013.md` in the same folder.

## Source files

| Role | Path |
|------|------|
| The report | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
| Playwright's budgets | `frontend/playwright.config.ts` |
| The PAC planner (C-69) | `frontend/src/lib/features/tools/pac-allocator/planner/` |
