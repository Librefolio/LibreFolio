---
title: "Transaction batch pipeline — `execute_batch` as an orchestrator over ordered stages"
category: entity
type: service
tags: [backend, transactions, batch-pipeline, validate, commit, wac, balance, architecture]
related: [decisions/unified-batch-pipeline, decisions/batch-only-split-promote, decisions/multi-broker-atomic-tx, decisions/end-of-day-balance-check, decisions/wac-inline-validate-commit, features/F-046, problems/pydantic-422-preemption, sources/phase00-transaction-batch-refactor-2026-09]
---

# Transaction batch pipeline

## Role
The one code path behind `POST /transactions/validate` and `POST /transactions/commit`
([[decisions/unified-batch-pipeline]]): it parses a mixed batch of creates, updates, deletes, splits and promotes,
applies them in a fixed order inside the caller's session, recomputes WAC and FX issues, validates cost bases and the
end-of-day balance replay, and builds the response. Since 2026-09-11 (SP16) `TransactionService.execute_batch()` is a
~50-line orchestrator; the work lives in named stages.

## Location
- `backend/app/services/transaction_service.py` — `execute_batch()` (the orchestrator)
- `backend/app/services/transaction_batch_context.py` — `TransactionBatchContext` (`from_inputs()`), the state the
  stages share; `BalanceValidationError`
- `backend/app/services/transaction_batch_stages.py` — the stages

## Key Interfaces — the order
`parse_inputs` (lenient per-row parse, original indices kept — [[problems/pydantic-422-preemption]]) →
`preload_and_authorize` (EDITOR access; may end the batch early) → `apply_deletes` → `apply_splits` →
`apply_updates` → `validate_updated_pairs` → `apply_creates` → `apply_promotes` → `resolve_create_links` →
`compute_wac_and_fx_issues` → `validate_cost_basis` → `validate_balances` → `finalize_response`.

The docstring states it in one line: *parse → access → delete → split → update → create → promote → link → WAC → cost
basis → balance replay → response*.

## Design Notes
- **The caller owns the database transaction.** The stages never commit, roll back or begin (nested) transactions;
  `commit=True/False` selects only the response semantics (`committed`, `success`, `simulated`, `success_count`).
- **Invariants kept by SP16**: the order of issues and results, multi-broker atomicity
  ([[decisions/multi-broker-atomic-tx]]), link UUIDs and pair symmetry, the WAC and balance replay, and the response
  flags. Characterisation tests were written before the extraction; no API, schema, policy or frontend change.
- Since 2026-10-07 the WAC stage reads the single average-cost function
  ([[decisions/financial-math-single-average-cost]]); the cost-basis stage skips Auto rows (backlog P-1).

## History
- 2026-04-29: unified validate/commit pipeline ([[decisions/unified-batch-pipeline]]).
- 2026-09-11 (`846aefb24`): SP16 decomposition — [[sources/phase00-transaction-batch-refactor-2026-09]].

## Source files

| Role | Path |
|------|------|
| Orchestrator `execute_batch` | `backend/app/services/transaction_service.py` |
| Shared context | `backend/app/services/transaction_batch_context.py` |
| Stages | `backend/app/services/transaction_batch_stages.py` |
| Service tests | `backend/test_scripts/test_services/test_transaction_service.py` |
| Validate API tests | `backend/test_scripts/test_api/test_transactions_validate.py` |
| Developer doc (service) | `mkdocs_src/docs/developer/backend/transactions/service.md` |
| Developer doc (balance validation) | `mkdocs_src/docs/developer/backend/transactions/balance_validation.md` |
