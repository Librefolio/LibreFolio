---
title: "Broker detail tests went over 30 s under load: they reloaded the broker list each time, and one probe passed without clicking (C-58)"
category: problem
status: resolved
date: 2026-10-13
tags: [testing, e2e, playwright, brokers, budgets, load, probes, workstream-i, release-1.2]
related:
  - sources/r-full-run-coverage-2026-10-12
  - problems/request-counter-read-before-the-handler-counted
---

# Problem: a detail suite that did its setup twice

## Symptom

C-58: under load, a test of `brokers-detail.spec.ts` went over its 30 s.

## Root Cause and Solution

`c58d48a6a` (workstream I's lot 50, train 81):

- 25 tests reloaded the broker list that their `beforeEach` had just loaded; they now reuse it;
- the FIFO lots block, which walks login, the list and the lots, gets an explicit budget of 60 s;
- an `if (count > 0)` counted the cards before the list had arrived, found none and passed without clicking: it is
  now an assertion — assert, do not probe.

Proved with a probe that slows the APIs down: red on the base, green with the cure. C-58 is closed.

## Prevention

- A setup done in `beforeEach` is not done again in the test.
- A conditional on what is on screen can pass on nothing: assert the state instead.

## Source files

| Role | Path |
|------|------|
| The spec | `frontend/e2e/brokers/brokers-detail.spec.ts` |
| Plan 50 | `LibreFolio_developer_journal/Release_2/Phase_0/50_brokerDetailBudget/plan-phase00BrokerDetailBudget.prompt.md` |
