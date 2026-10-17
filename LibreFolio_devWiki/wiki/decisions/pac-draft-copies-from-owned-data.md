---
title: "The PAC planner fills its draft by explicit copies of the user's own saved data — an owner-only, uncached, read-only endpoint — and the Tool never reads the portfolio"
category: decision
status: resolved
date: 2026-09-16
updated: 2026-10-06
tags: [backend, frontend, pac-allocator, tools, authority, privacy, copies, provenance, api, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/tool-calculation-without-authority
  - decisions/pac-p1-prototype-removed
  - decisions/wac-target-currency-last-acquisition
  - sources/phase00-pac-implementation-2026-10
---

# Decision: copies, not lookups

## Context

A useful plan starts from what the user owns — brokers, cash, prices, average costs, saved exchange rates — but a
Tool calculation receives only its scenario ([[decisions/tool-calculation-without-authority]]). The planner had to
fill its draft from LibreFolio without giving the Tool the user's authority, and without letting a stale or
half-loaded copy reach the calculation.

## Decision

The contract frozen on 2026-09-16 (Step 4, «copie dominio»), with the review rounds' refinements:

- **One dedicated endpoint**, `POST /api/v1/portfolio/allocation-source`, answered with `Cache-Control: no-store`:
  a read-only snapshot of selected portfolio, broker, asset, saved-price, average-cost and saved-FX facts. No
  `user_id` or `as_user` in the request; **owner-only**, administrators included in the rule, with no bypass. The
  whole broker selection is checked before any private read: a mixed authorised/unauthorised set gets **403**, never
  a partial answer. The response carries no target, route or order.
- **Saved data only**: the last saved price history, never `/assets/prices/current`, which can fetch from a provider
  and write; saved FX on direct pairs, the latest rate on or before the date, no chains and no provider sync. The
  average cost comes from `compute_wac_iterative()` after the owner check, in the report currency
  ([[decisions/wac-target-currency-last-acquisition]]). Numbers travel as decimal strings; every fact keeps its
  `provenance_id`.
- **Explicit, independent copy actions** in the planner — *Choose existing Broker*, *From your Brokers*, the asset
  search or *Your Assets*, *Copy current distribution* (Q-C0-6, 2026-09-24: «è un ottima idea facciamola»), and the
  **Auto** rates of the FX step. Every value shows **Copied**, **Manual** or **Modified**, a copy shows its date and
  does not follow its source, and the planner works without any copy at all.
- **Fresh at the moment that matters**: pressing **Calculate plan** first re-reads the prices, rates and balances
  the user copied and did not change (`refreshCopiedFacts()`); if that read fails, nothing is calculated until the
  user retries or chooses the earlier copies.
- **The browser computes no result**: «se si tratta di fare percentuali, ovviamente li può fare anche la ui, ma
  devono essere di controllo/informativi, quelli dei risultati stanno nel backend» (Q-C0-2, the developer,
  2026-09-24). A price's age is shown, without a confirmation (Q-C0-3).

## Consequences

- A coupled fix: `POST /api/v1/portfolio/wac`, which the copies reuse, now requires authentication (401/403/200).
- Late answers are dropped by account generation, request sequence and an `AbortController`
  (`sourceLoad.svelte.ts`); the 2026-10-05 mapping note records that this guard has no dedicated unit test.
- Defects found on the way: a copy whose rows were all in conflict was pruned, and «Aggiorna» then stamped rows
  pointing to a copy that no longer existed (`CopyOutcome.copy`, Round 5); the saved distribution parser now
  accepts Pydantic's decimal text and the geographic key `"Other"` (R7.4); the distribution help pointed to an
  «Allocation page» that does not exist and was reworded in four languages (`dbedcc822`, row 13).
- The copies replaced P1's report branch, which the final P1 removal deleted ([[decisions/pac-p1-prototype-removed]]).

## Source files

| Role | Path |
|------|------|
| Endpoint | `backend/app/api/v1/portfolio_api.py` |
| Snapshot service (owner check, saved facts) | `backend/app/services/pac_allocator/source/portfolio_allocation_source.py` |
| Snapshot DTOs | `backend/app/schemas/portfolio.py` |
| Planner client and copy merge | `frontend/src/lib/features/tools/pac-allocator/planner/source.ts`, `frontend/src/lib/features/tools/pac-allocator/planner/copies.ts` |
| Stale-answer guard | `frontend/src/lib/features/tools/pac-allocator/planner/sourceLoad.svelte.ts` |
| Service tests | `backend/test_scripts/test_services/test_portfolio_allocation_source.py` |
| User doc («Copied or typed values») | `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` |
| Step 4 plan | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step4PacRebalancerDomainCopies.prompt.md` |
