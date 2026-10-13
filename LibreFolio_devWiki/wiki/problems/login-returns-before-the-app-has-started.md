---
title: "`login()` returns before the app has started: under load, the next 3–5 s wait for a URL or a control runs out (V-27)"
category: problem
status: resolved
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

## Solution

V-27 in `BACKLOG_POST_1.2.md`, written by V on 2026-10-13 — «`login()` ritorna appena sparisce il form, prima
dell'arrivo». V-26 (`c1a42bf4a`, train 82) had moved the auth and AI Export setups off the test's clock; V-27 cured the
early return itself (`4ebbaab20`, train 87):

- `login()` returns only when the app has **arrived**: one of `app-shell`, `welcome-shell` or
  `onboarding-bootstrap-blocked` is visible, within 30 s; if none comes, the failure names the screen on view;
- the budgets of the specs that sign in follow one rule — `login()`'s worst case (70 s), plus the test's longest wait,
  plus the rest at a loaded pace: `auth.spec` 60 → 120 s, `app-start-auth` 60 → 150 s, `ai-export-contract`
  180 → 240 s. 76 files keep a smaller budget, each for a reason;
- a scan of 273 calls found no test that holds the bootstrap around `login()`.

Verified at one worker: six rounds, 102 of 102 green, the database back at the seed after each.

## Prevention

A helper that signs in must return in the state its callers expect, the app on screen, not halfway there; otherwise
every caller compensates on its own short budget, and under load one of them does not. The same family was open for
`setLanguage`, which waited the default 3 s for `<html lang>` while the chosen dictionary, a chunk of about 290 KB,
loaded: under load it gave the French toolbar sweep a red on 2026-10-13 (M's lot 37). V-36 closed it the same day
(`fccf0bee1`, train 92): the three waits of `setLanguage` share a 15 s budget, a deadline and never a delay; with the
dictionary held back 5 s the red was deterministic, and it is green with the cure.

## Source files

| Role | Path |
|------|------|
| `login()` | `frontend/e2e/fixtures/auth-helpers.ts` |
| Callers that wait after it | `frontend/e2e/auth.spec.ts`, `frontend/e2e/ai-export/helpers.ts` |
| R's report (§3.3) | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
| V's lot (V-27) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
