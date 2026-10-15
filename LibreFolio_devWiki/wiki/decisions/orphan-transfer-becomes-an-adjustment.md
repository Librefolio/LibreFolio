---
title: "A TRANSFER left without its other half becomes a plain ADJUSTMENT, with the same quantity and the same per-unit cost basis (V-3, decided 13/10, after 1.2)"
category: decision
status: accepted
date: 2026-10-13
tags: [backend, transactions, transfer, adjustment, fifo, lots, broker-delete, cost-basis, release-1.2]
related:
  - decisions/transfer-pair-same-asset-opposite-quantity
  - decisions/transfer-auto-cost-from-sending-broker
  - concepts/paired-partner-architecture
  - decisions/data-quality-proved-on-real-data
---

# Decision: an orphan TRANSFER is an adjustment

## Context

A TRANSFER moves securities between two brokers as a linked pair ([[decisions/transfer-pair-same-asset-opposite-quantity]]).
When one of the two brokers is deleted, `delete_by_broker` (`transaction_service.py`) deletes its transactions and
clears `related_transaction_id` on the rows that pointed at them: the half on the other broker stays, a TRANSFER
without its pair. It already worked this way in `v1.1.0`.

Workstream V's test-author found what follows (backlog V-3, 12/10; [[decisions/data-quality-proved-on-real-data]]):

- the lots analysis answers `FAILED` with `TRANSFER_PAIR_MISSING`;
- the Dashboard counts the orphan as capital in kind: the classifier treats an unlinked TRANSFER as a normal
  transaction, and `DailyStateBuilder._transfer_leg_capital` books it as capital;
- no test pins either behaviour.

## Decision

The developer, on 13/10, as recorded in the backlog: «il TRANSFER rimasto senza la sua metà torna a essere un semplice
ADJUSTMENT, con la stessa quantità e lo stesso `cost_basis_override`». The cost basis is per unit (the column holds a
frozen per-unit cost), so the adjustment carries the shares at the cost they had.

The FIFO lots then read it as an adjustment — the engine's `ADJUSTMENT_IN` and `ADJUSTMENT_OUT` branches — and no
longer fail.

## Status

**Not in the code yet**: V-3 stays in the backlog, low weight, after 1.2. Still to design:

- the Dashboard, which today books the orphan as capital in kind;
- the orphans already in existing databases: a migration, or a conversion on read;
- the tests of the broker deletion.

## Source files

| Role | Path |
|------|------|
| Where the orphan is born | `backend/app/services/transactions/transaction_service.py` (`delete_by_broker`) |
| The Dashboard's reading today | `backend/app/services/financial_math/portfolio/classifier.py` |
| The in-kind capital booking | `backend/app/services/financial_math/portfolio/daily_state.py` (`_transfer_leg_capital`) |
| The lots' failure code | `backend/app/services/financial_math/fifo/models.py` (`TRANSFER_PAIR_MISSING`) |
| The FIFO adjustment branches | `backend/app/services/financial_math/fifo/engine.py` |
| `cost_basis_override` (per unit) | `backend/app/db/models.py` |
| Backlog V-3 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
