---
title: "PAC allocator: «closest to target» is a lexicographic cascade — fixed-reference L2 first, then unspent cash, route priority, cost and order rows; no weighted sum"
category: decision
status: resolved
date: 2026-09-16
tags: [backend, pac-allocator, optimization, objective, lexicographic, l2, miqcp, policy, release-1.2, workstream-d]
related:
  - features/F-107
  - features/F-108
  - decisions/pac-scip-searches-exact-replay-certifies
  - decisions/pac-rounding-against-the-plan
  - sources/phase00-pac-rebalancer-design-2026-09
---

# Decision: the PAC optimises a fixed-reference L2, then breaks ties in a fixed order

## Context

«As close as possible to the target» has many readings: final percentages, the largest deviation, the money left
unspent, a weighted mix of them. Between 2026-09-14 and 2026-09-16 the design went through several of them, each
reversed by the next (the decision chronicle of `13_pacAllocator/drafts/`): a two-stage PAC — a deterministic
target-to-floor base, then a residual BUY optimisation (2026-09-15); for the Rebalancer an objective on final
percentages, D∞ → D1 → U → turnover → cost → rows (2026-09-15); then, on 2026-09-16, one shared objective for both
Tools.

## Decision

The developer's decision of 2026-09-16, written in the Policies and MathematicalCore designs:

- **A fixed reference, not a moving one.** `F_ref = V0 + K_reachable` — for the PAC, `V0 = 0`: the money the plan can
  actually reach, trapped funding excluded. Each asset's target is `T_a = w_a · F_ref`.
- **The primary objective** is `L2_fixed = Σ (V_a_final − T_a)²`, the squared distance of the final values from those
  targets: «Non è un'identità matematica obbligatoria: è la policy prodotto approvata» (MathematicalCore).
- **Then, lexicographically**, only among the plans tied on every previous stage: `U = F_ref − F_final` (the
  money left unspent) → route priority → explicit cost (fees and spread) → active order rows → a canonical tie-break.
  In the code: `fixed_l2 -> shortfall -> route_priority -> explicit_cost -> active_order_rows`
  (`objectives.py`). The arrow is not a weighted sum.
- **Percentages and the largest deviation are diagnostics**, shown but never optimised.
- **One policy on the wire**: `proportional` (Q-C0-4, 2026-09-24). `min_fragmentation` (fewer split assets right
  after L2) and the margin variant (`U` first) are designed but wait for their own SCIP cascade.

## Why L2 before U

The Policies design: if `U` came first, «il solver potrebbe saturare il cash con un Asset molto sovrappesato; un
quantum economico ma allocativamente distruttivo batterebbe un piano molto più vicino al target; la variante
margine non avrebbe più una funzione distinta». Among plans equally close to the target, the one that spends more
wins.

## Options Considered

| Option | Outcome |
|--------|---------|
| Final percentages as the objective | Rejected: a decision-dependent denominator, percentages improved by spending less, a fractional (MINLP) structure |
| D∞ → D1 (largest deviation first) | Reversed on 2026-09-16 in favour of the fixed-reference L2 |
| The weighted scalar «percentage error + λ × idle cash» | Rejected on 2026-09-15 because «its hidden coefficient would decide the trade-off» (decision chronicle); «nessuna somma weighted» (Policies) |
| A deterministic target-to-floor base plus residual buying | Reversed on 2026-09-16 |
| Rounding a continuous solution | Rejected: «Il floor/rounding di quel risultato non è autorevole» (MathematicalCore); the problem is solved over integer quanta |
| Fixed-reference L2, then a lexicographic cascade | **Chosen** |

## Consequences

- Each later stage is a convex MIQCP: SCIP re-solves with the previous optimum pinned (`Σ r² ≤ L2*`), which is
  exactly where its floating tolerance needed care — [[problems/pac-scip-tolerance-misreported-proof]].
- The planner's help text for L2 first said «value bought»; the formula uses each asset's value **after** the plan,
  and the text was corrected in the review rounds (R10.3).
- The Rebalancer ([[features/F-108]]) keeps the same primary with `V0 > 0`, and adds turnover and the SELL rules.

## Source files

| Role | Path |
|------|------|
| Objective stages | `backend/app/services/pac_allocator/objectives.py` |
| Constraints and the L2 epigraph | `backend/app/services/pac_allocator/constraints.py` |
| Cascade | `backend/app/services/pac_allocator/solver.py` |
| Policy literal on the wire | `backend/app/schemas/pac_allocator/request.py` |
| Policy tests | `backend/test_scripts/test_services/test_pac_planner_policies.py` |
| Policies design (§4) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerPolicies.prompt.md` |
| MathematicalCore design | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerMathematicalCore.prompt.md` |
| Decision chronicle | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-rebalancer-decision-chronicle.md` |
