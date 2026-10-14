---
title: "Seven E2E gaps of 1.2 are closed before the release, on real data: the developer's «Tutte e 7 nella 1.2»"
category: decision
status: accepted
date: 2026-10-12
tags: [testing, e2e, release-1.2, coverage, risk, native-cash, pac, yoc, transfer, account-deletion, pdf, workstream-v]
related:
  - decisions/data-quality-proved-on-real-data
  - problems/e2e-writes-leaked-into-shared-state
  - sources/phase00-data-quality-e2e-2026-10
---

# Decision: test the new 1.2 paths end to end before shipping

> **Delivered** (train 76, `56830fc79`, 2026-10-12): the seven gaps have their E2E through the real backend, listed
> under «Delivered». Recorded first on 2026-10-12 from plan 46, §12.4, when no test of the list existed.

## Context

In work 3 of plan 46 the coordinator asked workstream V, besides the isolation audit
([[problems/e2e-writes-leaked-into-shared-state]]), which features new in 1.2 had no end-to-end test through the real
backend. V checked each candidate against the suite and sent a table of eight gaps; six more candidates turned out to be
covered already (Rolling Return, the diagnostics without login, the CLI's `user deactivate`, the broker cards with a
transfer, the data editor's new row, the cost in the promote).

## Options Considered

The eight gaps, as V listed them:

1. Risk L1/L4 with a real `/risk/query` all the way to the screen — today every Risk E2E runs on mocked answers;
2. the «FX on cash» row and the revalued foreign cash — covered by backend tests only;
3. the PAC allocator, in beta;
4. Yield on Cost in the positions;
5. the transfer in Auto, which carries the origin's cost;
6. account deletion;
7. the PDF preview without the CDN;
8. Scalable with a real export.

## Decision

The developer, through the coordinator (2026-10-12): «Tutte e 7 nella 1.2 (circa 3 giorni dopo A1–A7)».

- Order: 2, 1, 6, 4, 7, 5, 3 — after the isolation cures A1–A7.
- One checkpoint every two or three gaps.
- Every test by test-author, on disposable accounts, green at one and at four workers.
- A wrong behaviour found on the way → stop and report to the coordinator.
- Gap 8 stays out until real data exist; C-42 and B9 stay in the backlog.

## Consequences

- Release 1.2 waits for about three more days of tests, on the developer's own estimate.
- The tests follow the rules already set by plan 46: real data through the API, MOCKFX for any rate, disposable
  accounts ([[decisions/data-quality-proved-on-real-data]]).

## Delivered (train 76)

In the developer's order, each on disposable accounts, green at one and at four workers (plan 46, §12.9). The journal
records no red-before run for these gaps: they are new coverage, not cures.

- **2 — FX on cash** (`portfolio/foreign-cash-real.spec.ts`): 1 000 units of a reserved currency (NAD, MZN on mobile)
  at a rate that moves from 1.25 to 1.6 per euro give an «FX on cash» row of 1000 × (1/1.6 − 1/1.25) = −175 EUR, and
  the headline cash is revalued on the day the rate moves.
- **1 — Risk** (`portfolio/risk-real.spec.ts`): levels 1 and 4 from a real `/risk/query` on two seed assets, every
  answer checked against its schema, no stubbed route.
- **6 — account deletion** (`brokers/account-deletion.spec.ts`): the broker the user alone owned goes, the co-owned one
  stays with the other owner; the test ids it needs came in `be3e1ed60`.
- **4 — yield on cost** (`portfolio/yield-on-cost-real.spec.ts`): per asset and broker (30 / 10 ÷ 100 = 3.00 %,
  12 / 8 ÷ 125 = 1.20 %), and no YoC without a cost (P-10).
- **7 — the PDF preview offline** (`files-pdf-offline.spec.ts`): a PDF drawn with every other origin refused, every
  request to the lane.
- **5 — the transfer in Auto** (`transactions/tx-transfer-auto-cost.spec.ts`): 10 at 100 and 10 at 200 give a WAC of
  150 that travels with the units — a gain of 600 at 180, where 1.1 read 3 600 —, for a whole and a partial transfer.
- **3 — the PAC allocator** (`pac-allocator-real.spec.ts`): a plan copied from LibreFolio, solved by the engine,
  printed as the engine answered and within the budget.

Gap 8 (Scalable with a real export) stays out. Left in the backlog: V-24 (the Auto cost cell may flash «0.00» as
ready) and V-25 (tests that use up seed rows) — [[problems/e2e-writes-leaked-into-shared-state]].

## Source files

| Role | Path |
|------|------|
| Journal (§12.4) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
| A Risk E2E on mocked answers | `frontend/e2e/portfolio/risk-lab.spec.ts` |
| Gap 2 | `frontend/e2e/portfolio/foreign-cash-real.spec.ts` |
| Gap 1 | `frontend/e2e/portfolio/risk-real.spec.ts` |
| Gap 6 | `frontend/e2e/brokers/account-deletion.spec.ts` |
| Gap 4 | `frontend/e2e/portfolio/yield-on-cost-real.spec.ts` |
| Gap 7 | `frontend/e2e/files-pdf-offline.spec.ts` |
| Gap 5 | `frontend/e2e/transactions/tx-transfer-auto-cost.spec.ts` |
| Gap 3 | `frontend/e2e/pac-allocator-real.spec.ts` |
