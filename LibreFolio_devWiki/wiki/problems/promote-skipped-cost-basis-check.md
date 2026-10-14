---
title: "A promote skipped the cost check: a transfer's receiving side without a cost was saved, then counted at zero"
category: problem
status: resolved
date: 2026-10-09
tags: [backend, cost-basis, promote, transfer, validation, batch-pipeline, workstream-p, release-1.2]
related:
  - decisions/transfer-auto-cost-from-sending-broker
  - decisions/bulk-pairs-new-with-saved
  - decisions/cash-transfer-split-promote
  - entities/transaction-batch-pipeline
  - sources/phase00-transfer-cost-basis-2026-10
---

# Problem: a promote skipped the cost check

## Symptom

A pair promoted into a TRANSFER whose receiving side had no cost basis, and was not in Auto, was saved anyway — and its
units then counted at zero cost. A lone ADJUSTMENT +5 without a cost was refused with `costBasisRequired` (check C0),
but the same row through a promote was not. Two ways in, both proved red by workstream P on 2026-10-09:

- **R3a**: two saved rows and a cost resolved to null — reachable only from the API, since the merge modal has sent no
  cost since 15 May;
- **R3b**: a saved −5 and a new +5 without a cost — reachable from the bulk editor.

The developer doc said the opposite of the code. The defect was already in v1.1.0.

## Root Cause

In the batch pipeline, `validate_cost_basis` skipped the creations consumed by a promote and never looked at the saved
rows being promoted; and `_apply_promote_cost_basis` set the receiving side's cost to None when the resolved fields
carried a null cost.

## Solution

Commit `d7c148564` (train 28), on the developer's choice «3 facendo chiedere il costo anche col promote» ("ask for the
cost on a promote too"):

- `_check_result_create_cost_basis` checks the promoted creations like any other creation — only Auto rows stay
  exempt;
- `_check_promoted_saved_cost_basis` checks, for every successful promote, the saved rows of the pair that need a cost
  and lack one, except those already checked as updates. The issue is a `costBasisRequired` on the `promote` operation,
  with the promote's index and `ref_id` = the row;
- the same issue shape and the same message as today: no schema, no i18n key.

## Prevention

- R3a and R3b green; C0 still green; two green controls: a promote of two saved ADJUSTMENTs where the receiving side
  keeps its cost (G1), and a saved + new pair with a cost (G2). B2.2, which promoted a new +3 without a cost, now gives
  it one.
- In the bulk editor, workstream S's spec `tx-bulk-promote-cost-basis.spec.ts` checks that the refusal lands on the
  right row — a new receiving side, a saved one, and «Merge all» ([[decisions/bulk-pairs-new-with-saved]]).

## Impact

A promoted transfer could enter the portfolio with no cost, its whole value then counting as gain.

## Links

- [[decisions/transfer-auto-cost-from-sending-broker]] — the lot's other fix
- [[entities/transaction-batch-pipeline]] — `validate_cost_basis` in the stage order
- [[decisions/promote-respects-asset-event-link]] — this check once refused a promote of a split-linked row in Auto, but only by chance;
  lot 42 refuses it for its own reason
- Source: [[sources/phase00-transfer-cost-basis-2026-10]]

## Source files

| Role | Path |
|------|------|
| `validate_cost_basis`, `_check_result_create_cost_basis`, `_check_promoted_saved_cost_basis`, `_apply_promote_cost_basis` | `backend/app/services/transactions/batch_costs.py`, `backend/app/services/transactions/batch_creates.py` (`_apply_promote_cost_basis`) |
| R3a, R3b, C0, G1, G2, B2.2 | `backend/test_scripts/test_api/test_transactions_batch_split_promote.py` |
| The editor's E2E | `frontend/e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` |
| Developer doc, «Promote boundary» | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
