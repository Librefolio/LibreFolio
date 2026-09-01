---
title: "Frontend parallelism — tappe 7-11, and the removal of sleeps"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-tappe-7-11-parallelismo-COMPLETO.md, tappa9-desleep.md"
tags: [testing, parallelism, playwright, frontend, performance, flakiness]
related:
  - concepts/playwright-run-consolidation
  - concepts/transaction-hygiene-fixture
  - concepts/load-only-red-is-a-product-defect
  - problems/env-var-injection-point-duplicated
  - problems/commit-reported-success-on-rolled-back-batch
  - problems/playwright-route-stub-is-per-context
---

# Source: frontend parallelism, stages 7 to 11

## Summary

The thesis: the frontend suite's wall time was dominated by **fixed per-invocation
cost** — server start, build check, DB creation — repeated once per action, and
by **sleeps** used as synchronisation.

The model already existed in-house: the gallery generator runs many specs in one
invocation and had been doing so for a long time. Stages 7-11 generalised it.

## Key Takeaways

- **Consolidation trades process count for process duration** —
  [[concepts/playwright-run-consolidation]] carries the measured tables and the
  eight-spec ceiling under JS coverage.
- **The rule that makes parallelism possible** is the isolation classification:
  a spec may run beside another only if the writes it performs cannot be observed
  by it. Everything else is serialised by declaration, not by convention.
- **Transaction hygiene is per file, not per test**, and disables itself above
  one worker — [[concepts/transaction-hygiene-fixture]].
- **`E2E_WORKERS` reached only one of the two launch paths.** The symptom was
  nothing at all: green, three times slower.
  [[problems/env-var-injection-point-duplicated]].
- **The commit endpoint answered `success` on a rolled-back batch** —
  [[problems/commit-reported-success-on-rolled-back-batch]] — and the
  over-broad first correction removed the ● pending indicator from the bulk modal
  for a week.
- **The E2E backend was running under `--reload`**, which costs restart latency
  and file watching for no benefit in a test server.
- Removing sleeps (`tappa9-desleep`) replaced elapsed-time waits with
  state-based waits. A sleep is a bet on a machine's speed; under four workers
  every such bet is placed on a slower machine.

## The console question, and its answer

The plan opens with a question worth preserving: *"could a print be sent to the
console — can the test intercept it?"* Yes, and the reason it matters is that it
gives the suite a channel for **diagnostics that survive the process boundary**,
which is what makes a consolidated run debuggable at all. Without it, one process
running forty specs is a black box.

## Numbers

After the fixes, **216 tests in 5,6 minutes**, a 3,0× improvement on the
sequential baseline, with four writing specs producing the **same single red** at
one worker and at four — evidence that consolidation, not concurrency, is the
polluting variable.

## Source files

| Role | Path |
|------|------|
| Consolidated launcher | `scripts/test_runner/_consolidate.py` |
| Worker-count injection | `scripts/test_runner/_common.py` — `apply_e2e_workers` |
| Playwright config | `frontend/playwright.config.ts` |
| Hygiene + coverage fixtures | `frontend/e2e/fixtures/playwright.ts` |
| Test server | `scripts/test_runner/_server.py` |
| Original plans | `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-tappe-7-11-parallelismo-COMPLETO.md`, `tappa9-desleep.md` |
