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

> **Planned, not delivered.** Recorded on 2026-10-12 from plan 46, §12.4; no test of this list is in the code yet.
> Each gap's page will be linked here when its checkpoint enters `dev_release2`.

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

## Source files

| Role | Path |
|------|------|
| Journal (§12.4) | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` |
| A Risk E2E today | `frontend/e2e/portfolio/risk-lab.spec.ts` |
