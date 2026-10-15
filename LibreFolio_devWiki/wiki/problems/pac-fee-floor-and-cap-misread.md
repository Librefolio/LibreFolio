---
title: "The PAC solver misread broker fees: a minimum fee made the whole model infeasible, and a maximum fee was ignored (499 shares instead of 500)"
category: problem
status: resolved
date: 2026-09-25
tags: [backend, pac-allocator, scip, fees, big-m, modelling, oracle, testing, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/pac-scip-searches-exact-replay-certifies
  - problems/pac-scip-tolerance-misreported-proof
  - sources/phase00-pac-implementation-2026-10
---

# Problem: the SCIP model and the exact fee rules disagreed

## Symptom

Found by workstream D on 2026-09-24/25, while making SCIP's status the proof (D-X1, Round 5, Passo F):

- **X2, the minimum fee** — 10 € per share, a budget of 100 €, a fee of 0.19 % with a minimum of 1.50 €. The exact
  replay accepts 9 shares (90 + 1.50 = 91.50 €); SCIP answered `reported_infeasible`, with every stage unfinished.
  A single route whose largest order value sits below minimum ÷ rate (789 € at 0.19 % with 1.50 €) was enough — a
  small monthly PAC, or a small per-asset cap: a probe with a 10,000 € budget and a cap of 20 shares of 10 € failed
  the same way.
- **QX1-a, the maximum fee** — 50,050 €, an ETF at 100 €, 0.19 % capped at 18 €. The exact rule allows 500 shares
  (50,000 + 18); SCIP computed a 95 € commission, stopped at 499, and finished every stage — with D-X1 that would
  have been published as «optimal».

## Root Cause

- **X2**: the fee variable's upper bound was `rate × notional_upper`, which ignores the minimum, and the Big-M built
  on it. When the minimum exceeded that bound, the `fee_floor` row forced a positive fee even with the order off,
  while the activation row forced it to zero — the model was impossible both ways, and one route sank all of it.
- **QX1-a**: the compiled model did not know `maximum_fee` at all; the constraints declared it a known limit since
  Step 3, and a policy test pinned the gap as an intended regression.
- Neither showed up earlier: on small domains the exhaustive oracle answered first and hid the solver, and no fixture
  of the SCIP-versus-oracle agreement test had a minimum above `rate × notional_upper`.

## Solution

- `f92e5560b` (2026-09-25, «bound the solver fee by its minimum»): the fee's upper bound never falls below the
  minimum.
- `6061affd7` (2026-09-25, «model the solver fee cap exactly»): an exact binary for the capped regime
  (`_fee_clamp_upper`, `_fee_cap_excess`), added only where the cap can actually bind; with it the bound becomes
  `max(floor, min(rate · notional_upper, cap))`. The developer, on QX1-a: «sì, modelliamolo subito».

## Prevention

- `test_fee_epigraph_floor_above_linear_upper_boundary` and solver-gate fixtures with a minimum above the linear
  bound; mutation probes (M1–M4) on the cap.
- Why two commits: the full bound is right only together with the cap binary. With the old linear row still in place,
  a cap in the upper bound would make every order above it infeasible — at most 94 shares in the QX1-a example,
  far worse than 499 — so the minimum went first and the cap came with its binary.
- The lesson of the oracle: an agreement test proves agreement only on the fixtures it has. A fee schedule whose
  minimum or maximum binds belongs in the fixtures of any solver test.

## Source files

| Role | Path |
|------|------|
| Fee rows, bounds and the cap binary | `backend/app/services/pac_allocator/constraints.py` |
| Exact fee rules in the replay | `backend/app/services/pac_allocator/evaluation/economics.py` |
| Policy and fee tests | `backend/test_scripts/test_services/test_pac_planner_policies.py` |
| Round 5 plan (Passo F, X2 and QX1-a) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md` |
