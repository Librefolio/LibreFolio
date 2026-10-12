---
title: "The PAC solver ran on a 3.5 s fallback while the Tool declared 30 s: nobody claimed the engine window, and plans changed from run to run"
category: problem
status: resolved
date: 2026-09-21
updated: 2026-10-06
tags: [backend, pac-allocator, tools, scip, budget, determinism, timeout, release-1.2, workstream-d]
related:
  - features/F-107
  - features/F-106
  - decisions/pac-scip-searches-exact-replay-certifies
  - decisions/tool-item-runs-in-owned-process
  - sources/phase00-pac-implementation-2026-10
---

# Problem: a budget declared is not a budget applied

## Symptom

The PAC Tool declared an engine budget of 30 s (`engine_timeout_ms = 30_000`, confirmed in the catalogue as the
effective, unclamped value), yet SCIP stopped after 3.5 s — 8.6 times less. With the tighter limit, repeated runs
of the same scenario finished different numbers of cascade stages and published two different candidates. The
Remediation plan (2026-09-21) first blamed missing seeds and thread settings; the budget plan corrected it: the seeds
were already fixed, and SCIP's time limit is wall-clock, so how far the cascade gets depends on the machine.

## Root Cause

`planner.py` called `solve_policy_program(program, checkpoint=checkpoint)` without a budget, so the solver fell back
to `DEFAULT_SOLVER_TIME_BUDGET_SECONDS = 3.5`, a value tuned for the platform's old 4 s envelope. The platform
offered `context.claim_engine_window()` for exactly this — and it had no production caller. The module docstring
stated the rule; the code broke it fifty lines later.

## Solution

`a7cd01b07` (2026-09-22, «propagate the declared engine budget»): the plugin claims the window with
`claim_engine_window(post_engine_reserve_ms=2_000)` and passes `window.timeout_ms / 1000` as
`plan_pac_allocation(solver_time_budget_seconds=…)`, down through `_search` to SCIP. A spy confirmed that SCIP
receives 30.0 s. At 30 s both reference scenarios completed the cascade in 8 runs out of 8, using 0.016 % and
0.009 % of the budget, with one candidate. The reported settings lost a misleading `limits/time` entry, and
`3e513fea2` corrected two measured claims about the solver's cost in the docs.

## Prevention

- The 3.5 s value stays only as the fallback for tests and probes, and its comment says it is «**Not** the product
  budget».
- The 2,000 ms reserve after the engine was re-measured on 2026-10-06 (item 13 of the robustness slice): the work
  after SCIP takes 6.4–12.9 ms, and the reserve was kept. `limits/nodes` waits for a reference machine.
- For the next Tool: the platform's dossier lists «a native solver never calls `checkpoint()`» among the traps, and
  `claim_engine_window()` fails at once on the default operation budgets ([[features/F-106]]).

## Impact

No release shipped with it: `plan` had been wired the day before (`b82e59ffa`, 2026-09-21), and the fix followed on
2026-09-22. In between, repeated runs of one scenario could publish different plans.

## Source files

| Role | Path |
|------|------|
| Engine window claim | `backend/app/services/tool_plugins/pac_allocator.py` |
| Budget passed down | `backend/app/services/pac_allocator/planner.py` |
| Fallback budget and SCIP limits | `backend/app/services/pac_allocator/solver.py` |
| Engine window | `backend/app/services/tools/base.py` |
| Tool API tests | `backend/test_scripts/test_api/test_pac_planner_tool_api.py` |
| Budget plan | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverBudget.prompt.md` |
