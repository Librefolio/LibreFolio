---
title: "P8 — test runner migration: isolation classes, derived inventory, resource broker"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p8-runner-migration.md"
tags: [testing, test-runner, parallelism, isolation, tooling, architecture]
related:
  - concepts/test-isolation-classes
  - concepts/derived-test-inventory
  - concepts/run-cache-and-campaign-semantics
  - problems/registered-but-unreachable-test-actions
  - problems/conftest-autouse-write-breaks-pure-class
  - decisions/test-runner-package-split
---

# Source: P8 — runner migration to a parallel execution model

## Summary

P8 turned `./dev.py test` from a sequential dispatcher into a scheduler. The core
move is that **what may run beside what** stops being tribal knowledge and
becomes a computed property of each test unit.

Four isolation classes — `PURE`, `READ`, `WRITE_SCOPED`, `WRITE_GLOBAL` — plus a
resource broker that hands out the DB, the port and the browser. The full model
is documented in [[concepts/test-isolation-classes]].

## Key Takeaways

- **The classes come from the real data model, not from taste.** Only
  `UserSettings` and `BrokerUserAccess` carry a `user_id`; `Transaction` does not
  have one at all. That is why `WRITE_SCOPED` is a small class and
  `WRITE_GLOBAL` is the default.
- **The default is deliberately asymmetric.** `PURE` must be *proved* statically;
  anything unproven falls back to `WRITE_GLOBAL`. A wrong guess then costs time,
  never correctness.
- **`exclusive_because` is a single declaration of class *and* reason.** A unit
  that needs exclusivity says so and says why, in one place, so the scheduler and
  the reader get the same answer.
- **Everything the runner needs is computable from the registry without running
  a test** — see [[concepts/derived-test-inventory]]. That is what made
  `check-orphans` meaningful and exposed
  [[problems/registered-but-unreachable-test-actions]].
- **Three-level contract**: inventory (what exists, what class), scheduler (what
  order, what parallelism), executor + broker (what resources).
- **`--resume` operates on units, not on actions**, and the run cache is written
  only by the parent process — see
  [[concepts/run-cache-and-campaign-semantics]].
- Scheduling is **LPT** (longest processing time first), not round-robin: with
  units of very unequal duration, round-robin leaves a long tail.
- **A spec absent from the report has failed.** Absence is not neutral.

## What it cost and what it bought

Measured fixed costs per invocation (server start, build check, DB create) are
what make consolidation worthwhile at all — see
[[concepts/playwright-run-consolidation]].

The migration also uncovered
[[problems/conftest-autouse-write-breaks-pure-class]]: a static purity proof that
reads only the test module can be defeated by an autouse fixture upstream.

## Relationship to earlier structure

The runner had already been split into a package
([[decisions/test-runner-package-split]], 18 modules / 12 categories / ~115
actions at the time). P8 is the next layer on top of that split: the package made
the code navigable, P8 made the execution model explicit.

## Source files

| Role | Path |
|------|------|
| Classes, classifier, `exclusive_because` | `scripts/test_runner/_inventory.py` |
| Registry assembly | `scripts/test_runner/_registry.py` |
| Scheduler (balance / plan / resolve_workers) | `scripts/test_runner/_scheduler.py` |
| Parallel executor (worker groups, env per worker) | `scripts/test_runner/_executor.py` |
| CLI contract | `scripts/test_runner/_cli.py` |
| Run cache | `scripts/test_runner/_run_cache.py` |
| `check-orphans` action | `scripts/test_runner/_cli.py` — `_check_orphan_tests()` (~L154) |
| Original plan | `LibreFolio_developer_journal/Release_2/Phase_0/07_coverageAndConsolidationCampaign/plan-p8-runner-migration.md` |

> **Path note (2026-09-01)**: three rows here were invented at ingest time —
> `_schedule.py` (the module is `_scheduler.py`), `_resources.py` (**never existed**;
> there is no separate resource-broker module — the worker/group logic lives in
> `_executor.py`), and `_orphans.py` (the orphan check is an action inside `_cli.py`).
> The plan path was also re-pointed from the ephemeral session-state copy to the
> in-repo copy; see `raw/ingest-registry.md`.
