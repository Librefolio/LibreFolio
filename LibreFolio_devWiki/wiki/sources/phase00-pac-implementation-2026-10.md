---
title: "Phase 0 / 13 — the PAC implementation bundle (workstream D): Steps 1–6, Round 5 and the review rounds, rows 7–16 after integration"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/README.md
tags: [phase0, release2, workstream-d, pac, scip, exact-arithmetic, contract, review, testing]
related:
  - features/F-107
  - features/F-108
  - decisions/pac-scip-searches-exact-replay-certifies
  - decisions/pac-p1-prototype-removed
  - decisions/pac-contract-compacted-before-release
  - decisions/pac-draft-copies-from-owned-data
  - sources/phase00-pac-rebalancer-design-2026-09
---

# Source: Phase 0 / 13 — the PAC implementation bundle

## Summary

`13_pacAllocator/implementation/` holds nineteen files: a README that indexes and restarts the work, the master plan
and Steps 1–6 written for PAC and Rebalancer together (with mapping notes of 2026-10-05 saying, item by item, where
each gate was delivered for the PAC and what is left for the Rebalancer), and the plans of the rows that followed the
merge of the planner. Step 1, Round 1 — the platform's capacity round — is ingested with the Tool platform,
[[sources/phase00-tool-platform-2026-09]].

| Rows | Plans | What happened |
|------|-------|---------------|
| 0–6 | Master, Steps 1–6 (2026-09-16 → 10-05) | Contracts, the exact core and the oracle, the SCIP compiler and policies, the domain copies, the planner UI, integration — PySCIPOpt pinned (`941834237`), exact primitives (`22cb18d1d`), FX redesign (`0088748a8`), the plan service (`c25c1e874`) |
| 7 | Remediation (2026-09-21) | ~9,100 lines unreachable, 23 of 80 boxes ticked; phases and seven open questions — [[decisions/pac-p1-prototype-removed]] |
| 8 | P1 residue removal (2026-09-21) | `b82e59ffa`: P1 out, `plan` wired; the orphan count from 83 to 0 |
| 9 | Solver budget (2026-09-21/22) | `a7cd01b07` — [[problems/pac-solver-ran-on-default-budget]] |
| 10 | Round 5 post-merge, with its C0 delta (2026-09-24 → 10-05) | Docs aligned, the UI in the build (`0210f9848`), Passo F (D-X1, fees, top-ups), review rounds 1–14 (`6f29ec1cf`), the developer's OK |
| 11 | Contract compaction (2026-10-05) | `ac18ce097` — [[decisions/pac-contract-compacted-before-release]] |
| 12 | Solver robustness (2026-10-05/06) | `8fa96ac28` — [[problems/pac-scip-tolerance-misreported-proof]] |
| 13 | Final P1 removal (2026-10-06) | `6ebad820b`, then R7 (`dbedcc822`): plurals counted on the displayed digits, the distribution help reworded |
| 14 | Rebalancer analysis | To be defined, after 1.2 — [[features/F-108]] |
| 15 | FX conversions (2026-10-08/09) | `bffc634b0` — [[problems/pac-foreign-funding-calculation-failed]] |
| 16 | Rounding against the plan (2026-10-09) | `96283eaa5` — [[decisions/pac-rounding-against-the-plan]] |

## Key Takeaways

- **The developer's decisions, in order**: the capacity envelope instead of a scenario cap (2026-09-16); the
  normalizer, not the schema, judges economic values — zero and negative reach it (G3, option B); Q-C0-1…7 on
  2026-09-24 (babel minor units, control percentages only in the UI, a price's age without confirmation, only
  `proportional`, a high route cap later made optional, «Copy current distribution», an `invalid` issue for exposures
  above 100 %); D-X1 and QX1-a on 2026-09-24, QX1-b on 2026-09-25; the unused proof forms deleted on 2026-09-28; the
  OK of Round 14 on 2026-10-02 — «è tutto perfetto… procedi con l'integrazione»; the compaction on 2026-10-04; the PAC
  E2E tests after the Rebalancer, and no MCP server for now («prematuro oltre ogni misura», 2026-10-05); the folder
  stays active (2026-10-10).
- **A mistake of D's own**: the brief put the exhaustive oracle among the tests; Step 3 promoted it to the production
  proof, and the first ordinary plans hit the time limit (X1) — [[decisions/pac-scip-searches-exact-replay-certifies]].
- **The ancestor of rule (a)**: on 2026-09-18 the SCIP-versus-oracle smoke found a real ranking error — the solver
  returned (buy 2, funding 9, fx 9) at an explicit cost of 9/100 where the oracle's (2, 8, 8) cost 2/25 — because the
  constraints used unrounded amounts while the ledger rounded each posting. One integer variable per rounded posting
  fixed it; three weeks later the rounding direction itself became the rule of
  [[decisions/pac-rounding-against-the-plan]].
- **Three PySCIPOpt traps** (6.2.1 / SCIP 10.0, found by experiment and written into `solver.py`): `getVal()` after
  `freeTransform()` silently returns the previous stage's value; `getObjVal()` can return a meaningless finite number
  when a stage stops on a limit with no solution, so the only gate is `getNSols() > 0`; missing bounds arrive as
  ±1e20, not `None`. And a bug that every static check missed: `compiler.py` imported `pyscipopt` under
  `TYPE_CHECKING` but called `Model(...)` at runtime — Ruff, Black and `py_compile` were green; the first smoke run
  raised `NameError`.
- **Gates learned the hard way**: the shared test backend did not answer within the runner's 120 s, because test
  mode builds the frontend (88 s) and the MkDocs site (42 s) before binding the port — build first, then run the
  gates; a merge with no textual conflict still failed K's HTML-sink gates on two planner files (`0900f11fa`,
  [[decisions/html-escape-at-the-source]]); no CI workflow checks the planner's formatting, so the README adds a
  Prettier gate, and after any Prettier pass the 35 test files that read sources as text (1,415 tests) must run again,
  because a moved line break can make a site appear or vanish.
- **The rule on dead i18n keys** — «Le chiavi verranno decretate morte solo alla vera fine del round di sviluppo» —
  was broken in Rounds 1–3 and the eight keys were restored; the final P1 removal then deleted 285 keys per language
  in one reviewed step.
- **What R7 left behind**: a plural must be chosen from the digits on screen, not from `Number()` of the value, and a
  masked quantity is always plural (`pluralCountSites.test.ts`); on the way the planner found that svelte-i18n
  caches formatters across locales — [[problems/svelte-i18n-formatter-cache-ignores-locale]].

## Still open (README, 2026-10-11)

Row 14, the Rebalancer analysis; the PAC E2E tests with it; batch-9 defects 1, 2 and 5 —
[[problems/datatable-actions-column-on-mobile]]; option (e), one conversion per broker and pair; `limits/nodes` on a
reference machine; a developer page on the engine; `fx_cost` per route.

## Wiki Pages Updated

Created: [[features/F-107]], [[features/F-108]]; [[decisions/pac-scip-searches-exact-replay-certifies]],
[[decisions/pac-lexicographic-fixed-l2-objective]], [[decisions/pac-fx-one-rate-map-direct-conversions]],
[[decisions/pac-draft-copies-from-owned-data]], [[decisions/pac-contract-compacted-before-release]],
[[decisions/pac-p1-prototype-removed]]; [[problems/pac-solver-ran-on-default-budget]],
[[problems/pac-scip-tolerance-misreported-proof]], [[problems/pac-fee-floor-and-cap-misread]],
[[problems/pac-foreign-funding-calculation-failed]], [[problems/pac-tool-error-instead-of-plan]],
[[problems/svelte5-trims-leading-space-in-tag]], [[problems/datatable-actions-column-on-mobile]];
[[sources/phase00-pac-rebalancer-design-2026-09]].

Updated: [[features/registry]], [[domains/calculations]], [[features/F-106]], [[features/F-097]],
[[decisions/pac-rounding-against-the-plan]], [[decisions/tool-calculation-without-authority]],
[[concepts/backend-only-calculations]], [[concepts/svelte5-runes]], [[decisions/html-escape-at-the-source]],
[[problems/svelte-i18n-formatter-cache-ignores-locale]].

## Source files

| Role | Path |
|------|------|
| Bundle index and restart note | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/README.md` |
| Round 5 and the review rounds | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md` |
| Solver robustness | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md` |
| Plugin | `backend/app/services/tool_plugins/pac_allocator.py` |
| Solver (the PySCIPOpt traps in its docstring) | `backend/app/services/pac_allocator/solver.py` |
| Planner frontend | `frontend/src/lib/features/tools/pac-allocator/planner/PacPlannerTool.svelte` |
