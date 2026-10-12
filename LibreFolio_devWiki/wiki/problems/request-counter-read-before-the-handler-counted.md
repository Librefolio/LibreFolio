---
title: "A request counter read right after `waitForRequest` could still be one short: the request event fires before the `page.route` handler counts it (lot 49)"
category: problem
status: resolved
date: 2026-10-12
tags: [testing, e2e, playwright, page-route, race-condition, counters, test-triage, workstream-i, release-1.2]
related:
  - sources/phase00-ui-polish-2026-10
  - problems/playwright-route-stub-is-per-context
---

# Problem: waiting for «sent» and reading «counted»

## Symptom

Workstream I met a race in `asset-detail.spec.ts` during lot 48; the coordinator split it off: «(a), ma come lotto 49
separato, subito dopo il checkpoint del lotto 48». The test counts the requests its `page.route` handlers answer, and
reads those counters synchronously — 290 reads in one test — right after waiting for a request.

## Root Cause

`page.waitForRequest` resolves on the browser's `request` event, before the `page.route` handler that increments the
counter has run. The test waited for «the request has left», when the assertion needed «the request has been counted».
The verdict, with the test-triage skill: an assumption of the test, not load and not the product.

## Solution

`6a1d95d85` («test(e2e): count asset-detail requests», train 77): `waitForCountedRequest` resolves only after the
handler has counted the request, through a local registry, so a counter read right after it is fresh; the call sites
stay as they were. A rescan found 12 reads truly at risk, not the 42 first counted. Proof K-B: the old helper fails at
the first risky read, the new one passes the whole test, with 56 of 56 counted waits waiting for the handler. A
read-only scan of the other specs found no real race.

## Prevention

- Wait for the condition you read: when an assertion reads what a route handler records, wait for the handler, not for
  the request event.
- Classify a red before curing it — here «assumption» ([test-triage](../../../.github/skills/devpy-tools/test-triage/SKILL.md)).
- Left in the backlog: 49-1, the lint debt of `_frontend_broker.py`.

## Source files

| Role | Path |
|------|------|
| The spec (`waitForCountedRequest`) | `frontend/e2e/assets/asset-detail.spec.ts` |
| The triage skill | `.github/skills/devpy-tools/test-triage/SKILL.md` |
| Plan 49 | `LibreFolio_developer_journal/Release_2/Phase_0/49_requestCountRace/plan-phase00RequestCountRace.prompt.md` |
