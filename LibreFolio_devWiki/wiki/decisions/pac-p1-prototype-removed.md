---
title: "The P1 prototype was deleted, not migrated: `plan` wired in place of `analyze`, then P1's report branch and 285 keys removed — a clean break at 1.0.0"
category: decision
status: resolved
date: 2026-09-21
updated: 2026-10-06
tags: [backend, frontend, pac-allocator, tools, prototype, cleanup, i18n, api, release-1.2, workstream-d]
related:
  - features/F-107
  - features/F-108
  - features/F-106
  - decisions/pac-contract-compacted-before-release
  - sources/phase00-pac-implementation-2026-10
---

# Decision: delete P1, wire the planner, keep no legacy path

## Context

**P1** was the first pilot on the Tool platform (2026-09-08 → 10): a narrow `operation="analyze"` that valued the
initial state and reported the gaps from the targets — by its own docstring, «never buy or sell instructions». One
plugin published it twice, as `pac_allocator` and `portfolio_rebalancer`, with their cards in the Tools hub.

The real planner (`plan`, the «v2») grew beside it, but on 2026-09-21 the Remediation plan counted about 9,100 lines
that nothing in the app could reach: `plan_pac_allocation` had no production caller. The review dossier of
2026-09-19 had left `plan` unregistered on purpose — its timeout envelope had never been measured. Remediation
proposed to wire `plan` late (phase 5), after determinism and capacity, and to retire P1 one Tool at a time.

## Decision

The developer had already answered: «possiamo cancellare il vecchio p1 che non era manco ben testato e non
funzionava e collegarlo **prima di metterci a fare le prove**», and the instruction recorded in the hand-off is
«togli p1 e poi lavora su v2».

1. **`b82e59ffa`** (2026-09-21, «drop P1 prototype, wire planner v2», 33 files, +193/−11,877): the P1 wiring, UI and
   tests go; `plan` is the one operation of the one service `pac_allocator`. The Rebalancer card and its user page go
   too, and the PAC page is rewritten because it was «inverted», not merely stale. A residue pass the same day took
   the orphan count from 83 to 0 (`154182295` for the pages).
2. **The final removal, row 13** (`6ebad820b`, 2026-10-06): P1's data side — the `allocation_source` branch of
   `POST /api/v1/portfolio/report`, its seven schemas, `allocationSource.ts` and 285 i18n keys in each language (from
   4,508 to 4,223; the `tools.allocation` and `tools.portfolioRebalancer` namespaces disappear). The report goes from
   13 to 12 sections, and a request that still sends the field gets 422.
3. **No legacy track**: the contract starts clean at `1.0.0`, with no `analyze` compatibility (decision D12 of the
   chronicle), and no CHANGELOG entry, because P1 was never released.

## Options Considered

| Option | Outcome |
|--------|---------|
| Keep P1 until `plan` is measured, retire it one Tool at a time (Remediation §3) | Rejected by the developer: wire `plan` before the tests |
| Keep the Rebalancer on P1 in the meantime | Not kept: its card, page and keys went with P1 |
| A compatibility layer between P1 and v2 | Rejected: P1 and v2 do different jobs — gaps versus executable orders |

## Consequences

- The copies the planner needs come from a dedicated endpoint, `POST /api/v1/portfolio/allocation-source`, not from
  the report ([[decisions/pac-draft-copies-from-owned-data]]); the report is P1-free.
- Removing code is measured, not assumed: P1's residue pass lists nine ways its own checks misled it — a
  `grep -v "evaluator.py"` that silently dropped `test_pac_planner_evaluator.py`, an AST walker blind to PEP 695
  `type` aliases (12 false orphans), a `declare -A` on bash 3.2 — the same family as
  [[problems/testid-grep-false-negative]].
- `dev.py lint --dead-code` still finds Rebalancer entry points reachable only from tests
  (`normalize_rebalancer_plan`): they are kept for [[features/F-108]].

## Source files

| Role | Path |
|------|------|
| The plugin with one service and one operation | `backend/app/services/tool_plugins/pac_allocator/plugin.py` |
| The report without P1's branch | `backend/app/services/portfolio_service.py` |
| Report tests (twelve sections, 422 on the old field) | `backend/test_scripts/test_api/test_portfolio_api.py` |
| Tools user page (the withdrawn Rebalancer) | `mkdocs_src/docs/user/tools/index.en.md` |
| Remediation plan (§3, §5) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRebalancerRemediation.prompt.md` |
| Residue removal | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacP1ResidueRemoval.prompt.md` |
| Final removal (row 13) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacP1FinalRemoval.prompt.md` |
