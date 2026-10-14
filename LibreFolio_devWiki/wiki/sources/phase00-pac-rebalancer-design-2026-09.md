---
title: "Phase 0 / 13 — the PAC and Rebalancer designs (workstream D): the five authoritative designs, the drafts and the review dossier"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md
tags: [phase0, release2, workstream-d, pac, rebalancer, optimization, scip, design, review]
related:
  - features/F-107
  - features/F-108
  - decisions/pac-lexicographic-fixed-l2-objective
  - decisions/pac-scip-searches-exact-replay-certifies
  - decisions/pac-fx-one-rate-map-direct-conversions
  - sources/phase00-pac-implementation-2026-10
---

# Source: Phase 0 / 13 — the PAC and Rebalancer designs

## Summary

The top of `13_pacAllocator/` holds the five designs that rule the PAC allocator ([[features/F-107]]) and the planned
Rebalancer ([[features/F-108]]); `drafts/` keeps fifteen earlier documents, and `review/` the dossier D wrote for the
developer. The implementation bundle is the companion source, [[sources/phase00-pac-implementation-2026-10]].

| File | Dates | What it adds |
|------|-------|--------------|
| `plan-phase00PacRebalancerTargetDesign.prompt.md` | 2026-09-16 → 10-09 | The target master: two Tools, outputs, the nine-step wizard, `F_ref`, the hard constraints, the policy matrix, proof semantics, open gates |
| `plan-phase00PacRebalancerMathematicalCore.prompt.md` | 2026-09-16 → 10-09 | Units, ledger, FX, fees and taxes, fixed L2, the MIQP/MIQCP boundary, no Big-M and no hidden epsilon, the oracle |
| `plan-phase00PacRebalancerPolicies.prompt.md` | 2026-09-16 → 10-02 | What a candidate must satisfy and in which order candidates are compared, with counter-examples |
| `plan-phase00PacRebalancerArchitecture.prompt.md` | 2026-09-16 → 10-02 | Ten principles, the SCIP adapter, the SELL verifier, no planner database in v1, failure boundaries |
| `plan-phase00PacRebalancerUiTarget.prompt.md` | 2026-09-15 → 10-05 | Every approved ASCII screen (reviews A–D), privacy, the 2026-10-02 strike-outs |
| `review/PAC_ALLOCATOR_REVIEW_DOSSIER.md` | 2026-09-19 → 10-09 | D's dossier for the developer's review of merge `3913fe217`, checked at `c25c1e874`: the arc, the mathematics, choices left unauthorised, the DBT register, 907 tests |
| `review/drive_planner.py` | 2026-09-19 | A read-only harness from before `plan` had a route: calls `plan_pac_allocation` directly and prints four outcomes |
| `drafts/` (15 files) | 2026-09-07 → 10-02 | The P1 contract and its evidence, the rejected UI rounds 2–4, the operational rounds 5–7, the first solver draft, the end-to-end design and the decision chronicle — «Nessun file qui è autorità prodotto corrente» (README of the drafts) |

## Key Takeaways

- **From a calculator to a platform in one day.** The backlog of 2026-09-07 described a buy-only PAC calculator in
  whole units; the same day planning broadened it into a Tool platform ([[features/F-106]]), one mathematical model
  for PAC and rebalancing, and a custom UI fed by «authorized domain snapshots rather than Tool-owned portfolio
  lookups» (decision chronicle).
- **Three UI rounds rejected, then an operational redesign.** Rounds 2 and 3 were rejected after manual review; the
  Round 4 prototype worked but was «theoretically descriptive rather than operationally useful» — it did not say which
  source pays how much, through which broker, in which order. A mathematical audit on 2026-09-15 found eight classes
  of blockers; the developer's correction of 2026-09-15 made the valuation currency a visible field and replaced the
  withholding inputs with a capital-gains rate on each asset (pre-filled at 26 %).
- **Reversals, dated.** The decision chronicle records several objectives reversed within two days before the shared
  fixed-reference L2 of 2026-09-16 — [[decisions/pac-lexicographic-fixed-l2-objective]]. Later reversals live in
  dated notes at the head of each design: 2026-09-25 (D-X1, QX1-b — the designs' own rule that a floating status is
  never promoted «non vale più»), 2026-10-02 (multi-hop, per-broker spread, safety margin and conversion fee «❌ non
  più da fare»; the version back to `1.0.0`), 2026-10-09 (rounding against the plan).
- **The architecture in one line**: «solver propone, evaluator Decimal certifica» — the backend owns the economics,
  the worker is pure, there is no P1 compatibility, and a structural test keeps the oracle out of production
  ([[decisions/pac-scip-searches-exact-replay-certifies]]).
- **PAC versus Rebalancer.** The PAC is the designs with `V0 = 0` and no sales; `invest_only`, `invest_and_sell`,
  the SELL verifier, the tax reserve and turnover belong to the Rebalancer. The margin variant was designed for both
  and is in neither.
- **The review dossier's honesty.** D wrote it for the developer's review of the merge: a floating solver result is
  «evidence, never a conclusion»; `plan` was deliberately left unregistered and the dossier said so; the DBT
  register named what was not done. Its proof-form items became moot when those forms were removed on 2026-09-28,
  and its claim that rate inconsistency was «structurally impossible» was corrected on 2026-10-09
  ([[problems/pac-foreign-funding-calculation-failed]]).

## Still open (the designs' gates)

The product-shaped payload under 262,144 bytes and the capacity benchmarks became question (b) of the Rebalancer
analysis; the return of `min_fragmentation`; quantity masking «da confermare» in the UI target; the Rebalancer itself.

## Wiki Pages Updated

Created with the implementation source in step B6b: [[features/F-107]], [[features/F-108]],
[[decisions/pac-lexicographic-fixed-l2-objective]], [[decisions/pac-scip-searches-exact-replay-certifies]],
[[decisions/pac-fx-one-rate-map-direct-conversions]] — see [[sources/phase00-pac-implementation-2026-10]] for the rest.

## Source files

| Role | Path |
|------|------|
| Target master | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md` |
| Mathematical core | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerMathematicalCore.prompt.md` |
| Policies | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerPolicies.prompt.md` |
| Architecture | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerArchitecture.prompt.md` |
| UI target | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerUiTarget.prompt.md` |
| Review dossier | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/review/PAC_ALLOCATOR_REVIEW_DOSSIER.md` |
| Decision chronicle | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/pac-rebalancer-decision-chronicle.md` |
| Engine | `backend/app/services/pac_allocator/planner.py` |
