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

**In the code for 1.3** (workstream W, lot N1b-1, 15/10), with the refinements decided while building it:

- `delete_by_broker` converts the surviving half **in place**, as a split of the pair leaves it, through the split's
  own helpers (`pair_sides()`, `make_standalone()` in `batch_edits.py`): a received TRANSFER becomes an ADJUSTMENT
  with the same quantity and cost basis; a CASH_TRANSFER or an FX_CONVERSION becomes a WITHDRAWAL or a DEPOSIT by its
  sign (coordinator, 15/10). The row keeps its id, and its `updated_at` moves, so the caches keyed on it recompute.
- A received leg **without** a cost basis (older data: one is required now) first takes the sending broker's Auto
  cost, computed while the sender's rows still exist (workstream J, 15/10, option b;
  [[decisions/transfer-auto-cost-from-sending-broker]]). Every cost is computed before any row changes, so a failure
  leaves every row as it was.
- The **giving** leg of a TRANSFER (its receiver deleted) becomes an ADJUSTMENT-out **at the Auto cost of its own
  broker** — decision 47 of release 1.3 (16/10, workstream W on J's CP-16). Before it, as an ADJUSTMENT-out without a
  cost, the units it moved would have read as destroyed (P&L −20 instead of +80 in the test scenario), so it only lost
  its link. J's CP-16 (`fifo/engine.py`, `335fb89cf`) makes a negative ADJUSTMENT that carries `cost_basis_override`
  hand its units over at that per-unit cost (proceeds; an outflow for performance). W prices the leg with
  `_handover_cost()` (`auto_cost.py`): the average of its **own** broker up to its date without itself — not
  `_auto_cost_source`, which names the partner's broker for a TRANSFER still linked. Without a cost (a missing
  conversion) the leg stays a TRANSFER without its link (night decision of 16/10, to review).
- The same rule in the batch: the **split** of a TRANSFER pair prices its giving leg in the WAC stage
  (`compute_wac_and_fx_issues`, after the batch's other rows), keeps a cost an update of the same batch gave it, and
  is refused with `WAC_FX_UNAVAILABLE` when the cost needs a missing conversion; a **promote** back into a TRANSFER
  drops the cost from the giving side (`cost_basis_allowed()` False there).
- **Interplay, pending the developer** (J-17, morning list of 16/10): price marks read every ADJUSTMENT with a cost
  as an observed TRADE price (`financial_math/price_marks.py`), so each converted giving leg would mark the asset at
  its average cost on that day, where the TRANSFER marked nothing. Decision 47 enters only after J-17.
- What the figures do (J, 15/10): the receiving broker's capital takes the units **at their cost** instead of their
  market value at arrival, so its gain also counts what they gained before the transfer — for a co-owner too, once
  the sending broker is gone. Declared in the deletion confirmation, the user guide and the CHANGELOG. Its lots open a
  new lot on the transfer date, so the holding period restarts. For cash halves capital and P&L do not move (an orphan
  cash leg already counted as an external flow); the purchases' funding pools and the deposits series do.
- The orphans **already in databases**: the post-migration fix `orphan_pair_halves` (point 46, approved) converts
  the received and cash halves (a log line per row, a dry run; received legs without a cost basis stay without one,
  with MISSING_COST_BASIS). It cannot price a giving leg — it runs on a synchronous `sqlite3` connection and the Auto
  cost is the async WAC — so it only counts them; the step that runs right after the fixes converts them
  (`lone_transfer_legs.py`: `lone-transfer-legs` at startup, never blocking it, and `python -m
  backend.app.db.post_migration`, whose `--dry-run` lists each leg with the cost it would take). A leg whose cost
  cannot be computed stays a TRANSFER and the others go on.

## Source files

| Role | Path |
|------|------|
| Where the orphan is born | `backend/app/services/transactions/transaction_service.py` (`delete_by_broker`) |
| The Dashboard's reading today | `backend/app/services/financial_math/portfolio/classifier.py` |
| The in-kind capital booking | `backend/app/services/financial_math/portfolio/daily_state.py` (`_transfer_leg_capital`) |
| The lots' failure code | `backend/app/services/financial_math/fifo/models.py` (`TRANSFER_PAIR_MISSING`) |
| The FIFO adjustment branches | `backend/app/services/financial_math/fifo/engine.py` |
| `cost_basis_override` (per unit) | `backend/app/db/models.py` |
| The split's helpers the conversion reuses | `backend/app/services/transactions/batch_edits.py` (`pair_sides`, `make_standalone`) |
| The Auto cost of a received leg without one | `backend/app/services/transactions/auto_cost.py` (`_auto_cost`, `_write_auto_cost`) |
| The deletion's tests | `backend/test_scripts/test_services/test_broker_service.py` (`TestDeleteBulkCrossBrokerPair`) |
| The lots and Dashboard after a deletion | `backend/test_scripts/test_services/test_financial/test_orphan_transfer_after_broker_delete.py` |
| Decision 47: the handover cost | `backend/app/services/transactions/auto_cost.py` (`_handover_cost`) |
| Decision 47: the split's giving leg priced in the WAC stage | `backend/app/services/transactions/batch_costs.py` |
| Decision 47: the promote drops the giving side's cost | `backend/app/services/transactions/batch_creates.py` |
| Decision 47: the lone legs already in a database | `backend/app/services/transactions/lone_transfer_legs.py` |
| Decision 47: the startup step | `backend/app/services/platform/app_lifespan.py` |
| Decision 47: the offline run and its dry run | `backend/app/db/post_migration/__main__.py` |
| The post-migration fix for the other halves | `backend/app/db/post_migration/orphan_pair_halves.py` |
| Decision 47: tests of the split and the promote | `backend/test_scripts/test_services/test_transaction_cost_basis_rule.py` |
| Decision 47: tests of the lone legs | `backend/test_scripts/test_services/test_lone_transfer_legs.py` |
| The plan of the lot | `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md` |
| Backlog V-3 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
