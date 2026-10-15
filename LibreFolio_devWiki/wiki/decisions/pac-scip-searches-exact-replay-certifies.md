---
title: "PAC allocator: SCIP searches and its status is the proof (D-X1); an exact Decimal replay certifies every published number; the exhaustive oracle is test-only"
category: decision
status: resolved
date: 2026-09-24
updated: 2026-10-06
tags: [backend, pac-allocator, tools, scip, optimization, proof, exact-arithmetic, oracle, testing, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/pac-lexicographic-fixed-l2-objective
  - decisions/pac-rounding-against-the-plan
  - problems/pac-scip-tolerance-misreported-proof
  - problems/pac-solver-ran-on-default-budget
  - sources/phase00-pac-implementation-2026-10
---

# Decision: SCIP proposes and proves; the exact replay certifies

## Context

The designs of 2026-09-15/16 treated a floating-point solver result as «evidence, never a conclusion» (review
dossier §1): «uno status floating non viene mai promosso: la prova viene solo da oracolo, witness o score-lattice»
(MathematicalCore, the rule the note of 2026-09-25 voids). In Step 3 workstream D went further and put the
**exhaustive oracle** — an enumeration of every candidate — into the production path, ahead of SCIP. The brief had
placed the oracle among the tests; promoting it was D's own reading, recorded later as a detour.

The smoke test of 2026-09-24 showed the cost (**X1**): 100 € on two ETFs failed with `execution_limit`. The oracle
enumerated domains of up to 200,000 candidates with no sub-budget, at about 3.3 ms each, and hit the 44 s soft
deadline at about 13,000.

## Decision

**D-X1, the developer, 2026-09-24**: «scip come libreria dovrebbe già ritornare gli ottimi rispetto a vincoli e
funzione obiettivo, avere un oracolo può essere utile in fase di test, su set piccoli, per testare funzione obiettivo
e vincoli, ma in produzione oracolo non deve MAI essere usato e si assume che la matematica di scip sia corretta» …
«in prod deve girare solo l'ottimizzatore con l'assunzione che l'output che dà sarà corretto o andrà in timeout».

- **SCIP's status is the proof**: `optimal` on every stage of the cascade means proven optimal; `infeasible` on the
  first stage means proven infeasible; a time or node limit publishes the best plan found as **Optimality not
  proven**.
- **The exhaustive oracle is test-only** (`b48b3cec9`, 2026-09-28): moved to
  `backend/test_scripts/test_services/_pac_exhaustive_oracle.py` as an agreement gate on small domains
  (`test_solver_incumbent_equals_exhaustive_oracle_optimum`); `test_exhaustive_oracle_is_test_only` fails if a
  production module imports it.
- **The proof forms nobody used go too** — `deterministic_conflict`, `gap_bounded`, `score_lattice_closure`,
  `describe_conclusion`. The developer, 2026-09-28: «se non sono più nei piani e sono stati prodotti per un piano
  precedente e ormai superato è inutile lasciarli, eliminali».
- **The Decimal replay keeps its role**: `evaluate_exact_candidate()` replays the candidate in exact arithmetic,
  without repairing it and without a tolerance; it is the only source of the published numbers and of feasibility.
  Every published plan carries `validation: "decimal_verified"`, which, in the words of the target master, «prova il
  candidato, non che sia il migliore globale». A candidate the replay rejects raises
  `ExactReplayRejectedError` and the Tool reports `execution_failed` — never a plan nobody verified.

## Options Considered

| Option | Outcome |
|--------|---------|
| The exhaustive oracle as the production proof | Rejected by D-X1: it exhausts the time budget on ordinary plans (X1) |
| A floating status never promoted (proof only from the oracle, a witness or a lattice closure) | Superseded on 2026-09-24 |
| SCIP's status as the proof, the exact replay as the referee of every number | **Chosen** |

## Consequences

- SCIP is the one engine (PySCIPOpt `6.2.1`, SCIP 10, pinned by the developer, «nessun fallback SciPy/HiGHS»), and
  its floating tolerance became a risk to the honesty of «Proven optimal»: the solver-robustness slice of 2026-10-06
  pins every stage at the exact value and cross-checks SCIP's bounds against the replay —
  [[problems/pac-scip-tolerance-misreported-proof]].
- A plan whose exact check disagrees with the solver's own numbers is shown, but its proof does not hold
  (`floatingFinished`: «The solver finished its search, but its own numbers do not match the exact check of this
  plan, so the proof does not hold»).
- A rounding overshoot of at most N minor units is published with the amount to add (QX1-b, 2026-09-25) — see
  [[decisions/pac-rounding-against-the-plan]].
- `SellIrreducibilityCheck.closure_kind` still names `exhaustive_oracle`: the Rebalancer ([[features/F-108]]) must
  revise it.

## Source files

| Role | Path |
|------|------|
| Exact replay | `backend/app/services/pac_allocator/evaluation/evaluator.py` |
| Solver cascade and stage statuses | `backend/app/services/pac_allocator/solver.py` |
| Proof objects | `backend/app/services/pac_allocator/proof.py` |
| Replay rejection → `execution_failed` | `backend/app/services/pac_allocator/planner.py` |
| Test-only oracle | `backend/test_scripts/test_services/_pac_exhaustive_oracle.py` |
| Oracle agreement and the import guard | `backend/test_scripts/test_services/test_pac_planner_solver.py`, `backend/test_scripts/test_services/test_pac_planner_planner.py` |
| Round 5 plan (§2, D-X1; Passo F) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md` |
