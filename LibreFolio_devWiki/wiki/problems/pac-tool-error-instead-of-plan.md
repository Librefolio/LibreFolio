---
title: "The PAC answered «Calculation failed» where a plan or a clear issue was due: four disagreements between the engine and its own result validation"
category: problem
status: resolved
date: 2026-09-24
updated: 2026-10-06
tags: [backend, pac-allocator, validation, fail-closed, execution-failed, floating-point, exact-arithmetic, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/pac-scip-searches-exact-replay-certifies
  - problems/pac-scip-tolerance-misreported-proof
  - problems/pac-foreign-funding-calculation-failed
  - sources/phase00-pac-implementation-2026-10
---

# Problem: a strict result turned engine slips into tool errors

## Symptom

Four times between 2026-09-24 and 2026-10-06 a legitimate scenario produced no plan: the user saw **Calculation
failed** (`execution_failed`, or a platform error), where the right answer was a plan or a domain issue explaining
what to change.

## Root Cause — one pattern, four instances

The result models validate their own invariants exactly, and the planner refuses to publish what it cannot verify
(«publishing an unverified plan is the one outcome this package exists to prevent», `planner.py`). That is
fail-closed by design — but in each case the engine had produced something its own validation could not accept:

| Instance | What happened | Cause |
|----------|---------------|-------|
| **N22** — exposures above 100 % (2026-09-24) | `ValidationError` in `PacExposurePlanRow` | The report computed the «uncategorised» share as `1 − declared` without a limit, and it went negative |
| **R13** — a manual conversion on a half-unit tie (2026-10-02) | `LedgerPostingScopeError`, and no log said where | A guard, `_require_credit_tie_free`, rejected an FX credit landing exactly on a half unit (1.1298 at 30 €) |
| **R10** — a tie-break stage stopped by the time limit (2026-10-05) | `ValidationError` on the published result | Tie-break stages are filtered out of the wire, so the stop reason and the evidence disagreed |
| **The published gap** (2026-10-06) | Scenarios «M 10×2» and «10×3» published nothing | The absolute gap was computed in float and printed as the shortest decimal; the validator recomputes the exact difference of the printed numbers, and the printed gap was 3.7e-16 too small |

## Solution

- **N22**: the normalizer rejects the scenario first, with the `invalid` issue `allocation.exposure_total_exceeds_one`
  (Q-C0-7, the developer: «il codice invalid è la scelta giusta»).
- **R13**: the guard was shown unnecessary — the posted-unit variable's bounds already contain the true rounded value —
  and removed with the code it left unused (option A, chosen by the developer on 2026-10-02; a probe against the oracle
  agreed). The plugin now logs the frames of an engine failure (R13.5; since `b3843e2f8` the callers too, never the
  message). Test: `test_manual_conversion_reaching_an_exact_credit_tie_still_plans`. Since 2026-10-09 credits round
  down ([[decisions/pac-rounding-against-the-plan]]), so an exact half unit no longer needs a tie rule.
- **R10**: the last objective row is marked `unfinished` (option α; `8fa96ac28`). Tests:
  `test_an_unfinished_tie_stage_marks_the_last_objective_row_unfinished`,
  `test_unfinished_tie_stage_reaches_the_wire_as_an_unfinished_objective_row`.
- **The gap**: `_published_gap` takes the exact difference of the two **printed** decimals (`8fa96ac28`); tests
  `test_published_absolute_gap_*`.

## Prevention

- Turn an invalid input into a domain issue in the normalizer, before the engine runs.
- Derive every published number from the same text the validator will read.
- When a strict validator rejects the engine's output, treat it as an engine defect and find it — the log of the
  callers exists for that. The design stays fail-closed: no unverified plan is published.

## Source files

| Role | Path |
|------|------|
| Exposure issue | `backend/app/services/pac_allocator/normalize.py` |
| Result models and their validators | `backend/app/schemas/pac_allocator/results.py` |
| Published gap, objective rows | `backend/app/services/pac_allocator/planner_report.py` |
| Posting scope | `backend/app/services/pac_allocator/constraints.py` |
| Engine-failure log | `backend/app/services/tool_plugins/pac_allocator/plugin.py` |
| Report tests | `backend/test_scripts/test_services/test_pac_planner_report.py` |
| Planner tests | `backend/test_scripts/test_services/test_pac_planner_planner.py` |
| Round 5 plan (N22, R13) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md` |
| Robustness plan (R10, the gap) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md` |
