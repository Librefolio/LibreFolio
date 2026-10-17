---
title: "The lots failed whenever a transfer crossed the broker scope"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, lots, fifo, transfers, broker-scope, co-owner, ai-export, workstream-j]
related:
  - decisions/fifo-v4-engine-architecture
  - decisions/financial-math-one-home
  - problems/unbounded-date-range-froze-the-instance
---

# Problem: the lots failed whenever a transfer crossed the broker scope

## Symptom

A lots analysis restricted to some brokers came out `FAILED` (`TRANSFER_PAIR_MISSING`) for the whole asset as soon as
one transfer had a leg inside the scope and the other outside it. Both directions failed: the receiving broker opened
no lot, and the sending broker kept its units forever.

- **The lots panel**, on a broker's page or on the Dashboard with a broker filter, for the owner as well.
- **A co-owner** who sees only one of the two brokers, even without a filter.
- **AI Export**: `broker.fifo_summary` asks for the lots of a single broker, so every asset ever moved between brokers
  reached the AI as `FAILED`, with the asset row missing or wrong.

Backlog J-10; fixed by workstream J on 17/10/2026 (night decision N76).

## Root Cause

`LotsAnalysisService` hands the FIFO engine the scope's rows only (`_load_transactions`). The engine pairs a TRANSFER
with its partner by `related_transaction_id` inside that list (`FifoLotEngine._resolve_transfer_pair`). A partner at a
broker outside the scope is not there, so the pair is "missing", a quantitative failure that fails the whole asset.
Only `PERFORMANCE_HISTORY` already re-ran over every accessible broker.

## Solution

`financial_math/lots/scope_boundary.py` (`read_transfers_at_scope_boundary`) reads such a leg the way the scope sees
it, before every reader of the analysis (engine, histories, conversions, average-cost lines):

- **in** → an ADJUSTMENT-in at the leg's own cost basis, the Auto cost a receiving leg carries;
- **out** → an ADJUSTMENT-out at the market value of its own day: the scope realizes market − FIFO cost;
- **out with no observation on or before its day** → each fragment leaves at its own FIFO cost (realized 0), through a
  new engine input flag, `FifoInputTransaction.hands_over_at_own_cost`;
- **performance** → a read leg moves its market value across the scope, as the re-run does for a pair it holds whole.
  A co-owner who sees one broker gets the same series as the owner who filters it.

Choices that matter:

- **Only when the partner really pairs back** (TRANSFER, linked both ways, same asset, opposite sign, same absolute
  quantity). A pair really missing or broken still fails.
- **Only the partner's pairing columns are loaded**, never an amount or a cost: nothing of a broker outside the scope
  enters the figures.
- **Detached copies.** The ORM rows are never mutated; `from_transaction` returns a `FifoInputTransaction` as it is,
  so the flag survives the FEE/TAX path.
- **Consistent with the Dashboard**, broker by broker (lot 41, D2/D5): the cost basis at the leg's cost, the capital at
  market.

## Why not replay every visible broker and filter?

That keeps the true lot identity across the move, but the summaries read lot-level totals, so every builder would have
to recompute them per scope. A co-owner who cannot see the other broker would still need a rule of its own, and the
result would differ from the Dashboard's broker view. The boundary reading is one rule for everyone.

## Left for later

- **J-47**: a transfer still in transit at `date_to` fails the lots even with the full scope (the arrival leg is cut by
  the date). The fix is to load the partner and stop the replay at `date_to`, as the Dashboard keeps the units in
  transit.
- **J-48**: the read legs show as "Adjustment In/Out" in the lots views. J-10 only made the closure label neutral
  ("Value handed over").
- **J-51**: Yield on Cost fails for a co-owner on units received from a broker they cannot see
  (`_include_external_transfer_legs` adds the partner leg alone).
- The private demo copy has no transfers at all, so no AI Export probe on real data can show this change; test R13
  pins the AI Export values on a synthetic ledger.

## Source files

| Role | Path |
|------|------|
| The reading | `backend/app/services/financial_math/lots/scope_boundary.py` |
| Engine flag | `backend/app/services/financial_math/fifo/models.py`, `backend/app/services/financial_math/fifo/engine.py` |
| Performance | `backend/app/services/financial_math/lots/histories.py` |
| Service | `backend/app/services/lots_analysis_service.py` |
| Closure label | `frontend/src/lib/features/brokers/lots/lotCustodyModalHelpers.ts` |
| Tests (pure) | `backend/test_scripts/test_services/test_financial_math/test_lots_scope_boundary.py` |
| Tests (service) | `backend/test_scripts/test_services/test_financial/test_lots_transfer_scope_boundary.py` |
| Tests (AI Export) | `backend/test_scripts/test_services/test_ai_export_broker_fifo_summary_scope_boundary.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/lots_analysis_service.md` |
| Plan | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |
