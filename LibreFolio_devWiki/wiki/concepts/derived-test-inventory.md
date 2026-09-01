---
title: "The test inventory is derived, never written by hand"
category: concept
date: 2026-08-31
tags: [testing, test-runner, infrastructure, invariants]
related: [concepts/test-isolation-classes, decisions/test-runner-package-split]
related_problems: [registered-but-unreachable-test-actions]
---

# Concept: derive the inventory, do not maintain it

## Definition

The runner needs to know **what exists** before it can decide what to run:
for each unit, its path, category, isolation class, historical duration and
required resources. That knowledge used to be scattered across 219 action
functions and, for the frontend, duplicated by hand into nine `all` lists.

The rule that replaced it:

> **Anything the runner needs to know about a test must be computable from the
> registry, without executing a single test.**

## Why it is possible

The action functions are **almost-pure command producers**. Substituting
`run_command` and `_run_playwright` with collectors makes the whole registry
introspectable: all fifteen `all` categories were walked **in under a second,
running nothing**.

`SIDE_EFFECTING` names the two exceptions — `db create` and `db populate` —
which do real work instead of composing a command. Neither executes a test file,
so skipping them in the dry run loses nothing.

## What it bought immediately

The dry run is how the reachability bug was found: **six registered actions,
~273 tests, that no `all` list reached**. See
[[problems/registered-but-unreachable-test-actions]].

The structural half of that fix is this concept: derive the `all` lists from the
inventory, so that *"registered but unreachable"* stops being an expressible
state. Without it, the immediate fix re-degrades at the next hand-added action.

## The three-layer contract

```
┌─ INVENTORY ─────────────────────────────────────────────┐
│  What exists. Derived, not written.                     │
│  unit → {path, category, isolation, duration, resources}│
└──────────────────────┬──────────────────────────────────┘
┌─ POLICY / SCHEDULER ─▼──────────────────────────────────┐
│  How to group it. In: inventory + --workers N.          │
│  Out: an execution plan. Respects isolation classes.    │
│  Balances by duration.                                  │
└──────────────────────┬──────────────────────────────────┘
┌─ EXECUTOR + RESOURCE BROKER ─▼──────────────────────────┐
│  How to run it. Each worker gets a resource lot:        │
│  {COVERAGE_FILE, DATABASE_URL, TEST_PORT, E2E user}.    │
│  Returns structured outcomes per unit, not per action.  │
└─────────────────────────────────────────────────────────┘
```

The 219 action functions were **not** rewritten. They stopped being *process
launchers* and became **selectors over the inventory**:
`./dev.py test front-fx fx-list` behaves identically; it now asks the scheduler
to run a unit instead of calling `subprocess.run` itself.

## Per unit, not per action

Two consequences fall out of the same change:

- **`--resume` keys on the unit**, not the action. Previously an action holding
  20 tests re-ran all 20 when one failed. Outcomes now come from structured
  reporters (`--junit-xml` for pytest, JSON reporter for Playwright).
- **The run cache is written only by the parent.** `mark_passed`/`mark_failed`
  do read-modify-write on the whole `.run_cache.json`; two workers finishing
  together overwrite each other. Workers return outcomes; the parent persists
  them. See [[concepts/run-cache-and-campaign-semantics]].

## Balancing

Round-robin distribution lost **half the theoretical gain** (83,7 s against
32,2 s across groups). Durations are persisted from the junit XML and
distributed *longest-processing-time first*.

## Silence must never read as success

The same principle applies at the reporting boundary:

> A spec missing from the Playwright JSON report is recorded as **failed**.

That is precisely how a run can lose units without anything going red — and it
is the same failure mode as the silently-lost coverage
([[problems/e2e-python-coverage-lost-above-two-workers]]) and the half-wired
environment variable ([[problems/env-var-injection-point-duplicated]]).

## Fixed cost, measured

The reason consolidation is worth the isolation work at all:

| Comparison | Result |
|---|---|
| `utils all` (12 invocations) vs one `pytest test_utilities/` | 32,6 s → **16,7 s**, same tests |
| 8 vitest invocations vs one `npx vitest run` | 630 tests / 56 files in **4,5 s** |
| pytest cold start (`--collect-only`) | **2,21 s** × 148 invocations |

The comparable quantity is not total time — that changes when the tests change —
but the **fixed cost per invocation**, which does not depend on what is inside.

## Source files

| Role | Path |
|------|------|
| Inventory derivation, `collect_launches`, `reachable_paths` | `scripts/test_runner/_inventory.py` |
| Registry assembler | `scripts/test_runner/_registry.py` |
| Suite lists derived from the registry | `scripts/test_runner/_suites.py` |
| Scheduler | `scripts/test_runner/_scheduler.py` |
| Executor | `scripts/test_runner/_executor.py` |
| Orphan check | `scripts/test_runner/_cli.py` — `check-orphans` |
