---
title: "`login()` returns before the app has started: under load, the next 3–5 s wait for a URL or a control runs out (V-27)"
category: problem
status: open
date: 2026-10-13
tags: [testing, e2e, playwright, auth, waits, load, workstream-r, workstream-v, release-1.2]
related:
  - sources/r-full-run-coverage-2026-10-12
---

# Problem: signed in, but not yet in the app

## Symptom

In R's full run ([[sources/r-full-run-coverage-2026-10-12]]), 9 E2E reds — five in the auth specs, four in AI Export — waited 3–5 s after `login()` for
a URL or a control that, under load, arrived later. Run alone, they pass.

## Root Cause

`login()` returns when the sign-in is done, not when the app has started; each caller then waits on a short fixed
budget for the page it expects. It is the pattern workstream K fixed on 2026-10-07 in the toolbar sweep only.

## Status

Open: V-27, brought forward into 1.2 — workstream V cures it in its next lot (coordinator, 2026-10-13).

## Source files

| Role | Path |
|------|------|
| `login()` | `frontend/e2e/fixtures/auth-helpers.ts` |
| Callers that wait after it | `frontend/e2e/auth.spec.ts`, `frontend/e2e/ai-export/helpers.ts` |
| R's report (§3.3) | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
