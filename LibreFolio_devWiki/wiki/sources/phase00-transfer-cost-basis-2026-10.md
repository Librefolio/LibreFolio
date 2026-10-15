---
title: "Phase 0 / 40 — the cost of transfers in Auto and of promotes (workstream P)"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/phases/40_transferCostBasis/plan-phase00TransferCostBasis.prompt.md
tags: [phase0, release2, workstream-p, wac, cost-basis, transfer, promote]
related:
  - decisions/transfer-auto-cost-from-sending-broker
  - problems/promote-skipped-cost-basis-check
---

# Source: Phase 0 / 40 — the cost of transfers in Auto and of promotes

## Summary

Plan 40 of workstream P (261 lines) fixed three defects of the average cost that workstream Q had read in the code
without trying them. On 2026-10-09 P proved them with red tests; all three were already in v1.1.0. The developer chose
one backend fix for the first two and a cost check on promotes for the third. The receiving side of a TRANSFER in Auto
now averages the sending broker as it was when the units left — a date the developer confirmed when a transfer is in
transit. A promote now asks for a missing cost like any other transaction. Commit `d7c148564` entered with train 28
(merge `2a5c15c3c`). The folder was archived on 2026-10-10, after the 09/10 archive ingest, which is why the audit of
step B found it never ingested.

## Key Takeaways

- The rule and the date: [[decisions/transfer-auto-cost-from-sending-broker]].
- The promote's cost check: [[problems/promote-skipped-cost-basis-check]].
- Red first: P30–P34 and R3a, R3b before the code; P35 after it, for the in-transit case shown by calculation.
- The docs-writer found three more pages describing the old behaviour. The coordinator approved the drafts, and an
  older error in the data-model page was corrected on the way.
- The only residue was the theory page's translation, since done in all four languages.

## Wiki Pages Updated

- Created: the two pages above.
- Updated: [[entities/transaction-batch-pipeline]], [[features/F-048]], [[features/F-097]],
  [[decisions/financial-math-single-average-cost]], [[decisions/bulk-pairs-new-with-saved]].

## Source files

| Role | Path |
|------|------|
| Plan 40 | `LibreFolio_developer_journal/Release_2/phases/40_transferCostBasis/plan-phase00TransferCostBasis.prompt.md` |
| The fixes | `backend/app/services/transactions/transaction_service.py`, `backend/app/services/transactions/transaction_batch_stages.py` |
| The tests | `backend/test_scripts/test_api/test_wac_inline.py`, `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` |
