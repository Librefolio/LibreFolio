---
title: "Linked transaction pairs must have identical description and tags"
category: decision
status: resolved
date: 2026-05-10
tags: [backend, transactions, validation, pair, description, tags]
related:
  - decisions/tx-link-uuid-semantics
  - decisions/dual-transaction-form-design
  - features/F-048
  - features/F-046
---

# Decision: Linked Transaction Pairs Must Have Identical Description and Tags

## Context

After the txStore refactor (Plan C), manual testing revealed that `deriveStatus()` reported false-positive "edited" status when editing paired transactions without changes. Root cause: mock data had divergent descriptions between the two sides of each linked pair (e.g., "Transfer AAPL to DEGIRO" vs "Transfer AAPL from IB"). Since a linked pair represents a single logical operation, this inconsistency is semantically incorrect.

## Options Considered

1. **Frontend-only fix**: suppress diff detection when descriptions differ pre-existing. Fragile — just hid the problem.
2. **Backend validation rule**: enforce identical description+tags as an immutable invariant on linked pairs. Prevents future divergence at source.
3. **Auto-sync on save**: always copy "from" description to "to". Loses user intent if they differ intentionally.

## Decision

**Option 2**: Backend validation via `TransactionService._validate_pair_description_tags()`. Two error codes: `pairDescriptionMismatch` and `pairTagsMismatch`. Hooked at:
- Step 6 (create linked pairs): validated after `_validate_linked_pair()`, before assigning `related_transaction_id`
- Step 4b (update): second pass over all updated linked TXs, fetching partner if needed

Frontend handles legacy mismatched data by concatenating descriptions with `[auto-merged]` note and doing tag union — making the change explicit to the user.

## Consequences

- New linked pairs can never have divergent description/tags (400 from backend)
- Legacy mismatched data gets merged visibly on first edit (user sees concatenation)
- Mock data aligned: all 8 pairs now use symmetrical `"↔"` format
- Enables future Promote wizard to require resolution before commit
- 4 backend tests (`TestPairDescriptionTagsValidation`) verify create, update, and bulk scenarios

## Source files

| Role | Path |
|------|------|
| Validation method | `backend/app/services/transaction_service.py` |
| Backend tests | `backend/test_scripts/test_api/test_transactions_api.py` |
| FormModal merge logic | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| Mock data (aligned) | `backend/test_scripts/test_db/populate_mock_data.py` |

