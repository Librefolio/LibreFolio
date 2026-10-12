---
title: "SCIP's floating tolerance let the PAC call a worse plan «Proven optimal», and a feasible scenario with huge amounts «infeasible»"
category: problem
status: resolved
date: 2026-10-06
tags: [backend, pac-allocator, scip, floating-point, tolerance, proof, miqcp, cascade, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/pac-scip-searches-exact-replay-certifies
  - decisions/pac-lexicographic-fixed-l2-objective
  - problems/pac-tool-error-instead-of-plan
  - sources/phase00-pac-implementation-2026-10
---

# Problem: «optimal» on SCIP's numbers is not «optimal» on the exact ones

## Symptom

Once SCIP's status became the proof (D-X1), the robustness slice of 2026-10-05/06 (README row 12) measured four ways
it could mislead:

- **P-a** — scenario «M 5×2» was published as **Proven optimal** with plan (475, 25, 10, 239/40, 7), seven order
  rows, while (475, 25, 9, 239/40, 6) was just as close to the target and used six.
- **P-c** — a finished stage «proved» a value of 11 for a published plan whose exact value was 10.
- **A1** — when time ran out in the middle of the cascade, «M 10×2» published 14 orders with one-unit splits: every
  stage after the limit was simply `not_reached`.
- **False infeasibility** — a scenario of five assets on one broker («5×1») with every amount multiplied by 10⁸ came
  back `ready_infeasible`, `infeasibility_proven`, although the empty plan was exactly feasible.

## Root Cause

- SCIP accepts each nonlinear `fixed_l2` epigraph row (`residual_sq >= residual**2`) with an **absolute** feasibility
  tolerance of 1e-6, so a stage's value can sit up to that much per asset below the exact one — 474.9999988 for an
  exact 475. The cascade pinned the next stage at that value, and the pin cut away equally good plans.
- Nothing compared SCIP's bounds with the exact replay of the plan it returned.
- With amounts near SCIP's infinity (1e20), the expanded squares lost their precision.

## Solution

`8fa96ac28` (2026-10-06, «harden the solver cascade and its proofs»), after a mathematical review and red tests,
with the contract and its fingerprint unchanged:

- **Pin at the exact value**: `max(SCIP primal, exact value)` plus a relative slack of 1e-12
  (`STAGE_PIN_RELATIVE_SLACK`); integer stages are pinned exactly.
- **Bracket check** (`_flag_contradicted_bounds`): if the published plan's exact value falls outside SCIP's bounds for
  any finished stage, the result becomes `not_proven`, and the plan says why («its own numbers do not match the exact
  check of this plan, so the proof does not hold»).
- **Time running out (A1)**: the first stage keeps a reserve, the unfinished stage is pinned at the plan found, and
  the remaining stages still improve the later criteria; the first unfinished stage — tie-breaks included — decides
  the stop reason.
- **A guard against false infeasibility**: when the empty plan is exactly feasible, an «infeasible» from SCIP raises
  `SolverInfeasibilityContradictedError`, and the Tool answers `execution_failed` instead of a false proof.

The developer approved the order on 2026-10-05: «si approvo il piano» — «Prima la correzione del solver, poi la
pulizia P1 (Consigliato)» — «Sì, tutte come raccomanda D (Consigliato)».

## Prevention

- Tests: `test_finished_stage_bounds_bracket_the_exact_replay`,
  `test_an_integral_stage_scip_misreports_is_pinned_exactly_and_never_proven`, the stage-one resume tests,
  `test_huge_amounts_never_turn_a_feasible_zero_plan_into_proven_infeasibility`; the probe
  `pac_solver_robustness_probe.py` reproduces the scenarios.
- The user page states the limit: with amounts of around ten billion units of a currency or more, the tool may stop
  with an error or mark the plan **Optimality not proven**. A scaled model and an amount cap stay in the backlog.
- The same slice's read-only review of the QX1-b rounding bound found it correct.

## Impact

None released. During the review rounds, a plan could carry a stronger claim than its numbers supported.

## Source files

| Role | Path |
|------|------|
| Stage pins and the bracket check | `backend/app/services/pac_allocator/solver.py` |
| The false-infeasibility guard | `backend/app/services/pac_allocator/planner.py` |
| Solver tests | `backend/test_scripts/test_services/test_pac_planner_solver.py` |
| Planner tests | `backend/test_scripts/test_services/test_pac_planner_planner.py` |
| Robustness probe | `backend/test_scripts/diagnostics/pac_solver_robustness_probe.py` |
| User doc («What the calculation engine does») | `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` |
| Robustness plan (row 12) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md` |
